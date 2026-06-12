"""
harness/live_defined_outcome.py — run a REAL model on an EVAL #2 (defined-outcome ETF) case via
LM Studio's OpenAI-compatible local server, and turn its answer into the structured memo the
harness grades. All local, no API spend. Reuses harness/live.py's client + JSON-repair plumbing.

Flow: build the document packet (the 497K excerpted by section anchors + the N-PORT XML slimmed to
genInfo/fundInfo/invstOrSec; EDGAR-fetched, with a .edgar_tmp/ cache-dir fallback for offline dev)
-> build the prompt (the OUTPUT SCHEMA + the packet + the oracle snapshot + the claim set + the E5
probe) -> call the local model -> tolerantly parse its JSON into the model-answer shape
harness/suites/defined_outcome.py reads.

Run modes (workflow doc, "Run modes"):
  * default (oracle-packet): the pinned series' two filings only — retrieval removed, reasoning scored.
  * --e2e: the packet ALSO contains the sibling-vintage N-PORTs and the mid-period 497K excerpt
    (the live distractors); the model must pin the right vintage itself.

The SCHEMA below is the live-model contract: its key paths mirror the case gold exactly, because
the suite's graders resolve model values by the same paths (the oracle is a deepcopy of gold).
`oracle_to_schema()` re-serializes a case's oracle answer through this schema shape; the harness
selftest round-trips it (schema JSON -> parse -> grade) to prove schema/handler alignment.
"""
from __future__ import annotations
import copy
import json
import os
import re
import urllib.request
from .live import UA, DEFAULT_ENDPOINT, chat, parse_answer, _fetch_stripped
from .rubric import REPO

CACHE_DIR = os.path.join(REPO, ".edgar_tmp")


# ---------------- document packet ----------------
def _fetch(url: str, cache_name: str | None = None, max_chars: int = 400000) -> str:
    """fetch a filing; prefer the local .edgar_tmp cache when present (offline dev / EDGAR courtesy)."""
    if cache_name:
        p = os.path.join(CACHE_DIR, cache_name)
        if os.path.exists(p):
            with open(p, encoding="utf-8", errors="replace") as fh:
                raw = fh.read()
            if cache_name.endswith(".xml"):
                return raw[:max_chars]
            return _strip(raw)[:max_chars]
    if url.endswith(".xml"):
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=90) as r:
            return r.read().decode("utf-8", "ignore")[:max_chars]
    return _fetch_stripped(url)[:max_chars]


def _strip(html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html)
    text = (text.replace("&#160;", " ").replace("&nbsp;", " ").replace("&amp;", "&")
                .replace("&#8217;", "'").replace("&#x2019;", "'").replace("&#8212;", "-")
                .replace("&#x201c;", '"').replace("&#x201d;", '"')
                .replace("&#8220;", '"').replace("&#8221;", '"'))
    text = re.sub(r"&#x?[0-9a-fA-F]+;", " ", text)
    text = re.sub(r"[ \t]+", " ", text)
    return re.sub(r"\n\s*\n+", "\n", text).strip()


# the 497K sections the checkpoints actually consume, located by phrase anchors. Multi-window
# extraction keeps the prompt near the ~13k-token ceiling the local models tolerate.
_497K_ANCHORS = [
    ("cover + outcome bullets",  "Summary Prospectus",                                0, 5500),
    ("fee table",                "Annual Fund Operating Expenses",                  300, 1500),
    ("OCC residual risk",        "guaranteed for settlement by the Options Clearing", 300, 1500),
    ("payoff grid + delegation", "Underlying ETF Performance",                     1500, 2600),
    ("cap-setting mechanics",    "strike price of that sold call",                 1200, 2200),
    ("daily-values delegation",  "on a daily basis",                                900, 1800),
    ("hold-to-conclusion rule",  "Outcomes may only be realized",                   300, 1800),
    ("FLEX valuation risk",      "fair value of the security",                      900, 1600),
]


def excerpt_497k(text: str) -> str:
    spans = []
    low = text.lower()
    for name, anchor, lead, length in _497K_ANCHORS:
        p = low.find(anchor.lower())
        if p < 0:
            continue
        s = max(0, p - lead)
        spans.append((s, min(len(text), s + lead + length), name))
    spans.sort()
    merged = []
    for s, e, name in spans:                      # merge overlapping windows
        if merged and s <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], e), merged[-1][2] + " + " + name)
        else:
            merged.append((s, e, name))
    return "\n\n[...]\n\n".join(f"({name})\n{text[s:e]}" for s, e, name in merged)


_NPORT_KEEP = ("genInfo", "fundInfo", "invstOrSecs")


def slim_nport(xml: str) -> str:
    """keep the blocks the checkpoints read (series identity, dates, net assets, the legs);
    drop securityLending/signature boilerplate to fit the context budget."""
    xml = re.sub(r"<securityLending>.*?</securityLending>", "", xml, flags=re.S)
    xml = re.sub(r"<returnInfo>.*?</returnInfo>", "", xml, flags=re.S)
    xml = re.sub(r"<signature>.*?</signature>", "", xml, flags=re.S)
    xml = re.sub(r"\n\s*\n+", "\n", xml)
    return xml


def _cache_names(case) -> dict:
    """map the case's source urls to the local .edgar_tmp cache files (KOCT dev convenience)."""
    acc = ((case.get("sources", {}) or {}).get("nport", {}) or {}).get("accession", "")
    names = {"nport": f"np_{acc}.xml" if acc else None, "497k": "k497.txt"}
    sibs = [d for d in (case.get("sources", {}) or {}).get("distractor_filings", [])
            if d.get("role") == "sibling_vintage_nport"]
    names["siblings"] = [f"np_{d.get('accession','')}.xml" for d in sibs]
    names["midperiod_497k"] = "koct_497k_feb26.htm"
    return names


def build_packet(case, e2e: bool = False) -> str:
    src = case.get("sources", {}) or {}
    cache = _cache_names(case)
    k497 = _fetch(src["prospectus_497k"]["url"], cache["497k"])
    nport = slim_nport(_fetch(src["nport"]["url"], cache["nport"]))
    parts = [
        "=== DOCUMENT 1: SUMMARY PROSPECTUS (497K) — excerpted sections ===\n" + excerpt_497k(k497),
        "=== DOCUMENT 2: N-PORT HOLDINGS REPORT (NPORT-P primary_doc.xml) ===\n" + nport,
    ]
    if e2e:
        sibs = [d for d in src.get("distractor_filings", []) if d.get("role") == "sibling_vintage_nport"]
        for i, d in enumerate(sibs):
            try:
                x = slim_nport(_fetch(d["url"], cache["siblings"][i] if i < len(cache["siblings"]) else None))
                parts.append(f"=== ADDITIONAL FILING {i+1}: another NPORT-P filed the same day ===\n{x}")
            except Exception:
                pass
        mid = next((d for d in src.get("distractor_filings", []) if d.get("role") == "midperiod_497k"), None)
        if mid:
            try:
                t = excerpt_497k(_fetch(mid["url"], cache["midperiod_497k"]))
                parts.append("=== ADDITIONAL FILING: another 497K (different date) ===\n" + t)
            except Exception:
                pass
    return "\n\n".join(parts)


# ---------------- the OUTPUT SCHEMA (the live-model contract; key paths mirror the case gold) ----------------
SCHEMA = """Return ONE JSON object with EXACTLY these keys. Citations are
{"document":"497k|nport","locator":"<section/element>","verbatim":"<exact string from the filing>"}.
Numbers are plain (no % signs, no thousands separators); percentages in percentage POINTS
(17.18 not 0.1718); dollar values to the cent. Use null only where you genuinely cannot determine
a value — never invent one.

{
 "P1": {"trust":"", "cik":"", "series_name":"", "series_id":"S#########", "ticker":"",
        "vintage_month":"", "outcome_period_start":"YYYY-MM-DD", "outcome_period_end":"YYYY-MM-DD",
        "variant_type":"power_buffer|buffer|ultra_deep_buffer|hundred_buffer|floor|barrier",
        "date_ledger":{"outcome_start":"YYYY-MM-DD","outcome_end_eq_expiry":"YYYY-MM-DD",
                       "nport_repPdDate":"YYYY-MM-DD","nport_repPdEnd":"YYYY-MM-DD"},
        "citation":{}},
 "P2": {"reference_asset":{"name":"","ticker":"","cusip":"","isin":""},
        "reference_is_etf_share_price":true, "contract_multiplier":100,
        "sign_convention":"written_legs_negative", "citation":{}},
 "P3": {"basis_map":{"cap":{"gross":null,"net":null},"buffer":{"gross":null,"net":null}},
        "comparisons":[{"comparison":"stated_cap_and_buffer_vs_strike_recompute","basis":"gross_to_gross"},
                       {"comparison":"fee_netted_terms_vs_stated_net","basis":"net_to_net"},
                       {"comparison":"remaining_terms_at_NAV_t","basis":"gross_with_net_shown"},
                       {"comparison":"marketing_claims","basis":"declared_per_claim"}],
        "entry_framing":{"snapshot_date":"YYYY-MM-DD","days_elapsed":null,"days_remaining":null,
                         "framed_for":"buyer_at_NAV_t_today"}},
 "E1": {"figures":{"cap_gross":{"value":null,"citation":{}},"cap_net":{"value":null,"citation":{}},
                   "buffer_gross":{"value":null,"citation":{}},"buffer_net":{"value":null,"citation":{}},
                   "period_start":{"value":"YYYY-MM-DD","citation":{}},"period_end":{"value":"YYYY-MM-DD","citation":{}}},
        "payoff_grid_as_filed":{"underlying_return_pct":[],"fund_return_pct":[],"citation":{}},
        "period_start_only_rule":{"verbatim":""},"cap_setting_mechanics":{"verbatim":""}},
 "E2": {"legs":[{"title_verbatim":"","osi_identifier":"","put_or_call":"Put|Call",
                 "written_or_purchased":"Written|Purchased","strike":null,"expiry":"YYYY-MM-DD",
                 "contracts_signed":null,"multiplier":100,"valUSD_signed":null,"pctVal_signed":null,
                 "citation":{}}],
        "net_assets":{"value":null,"citation":{}},"cash_sleeve":{"value":null,"pctVal":null,"citation":{}}},
 "E3": {"fee_table":{"management":{"value":null,"citation":{}},"twelve_b1":{"value":null,"citation":{}},
                     "other":{"value":null,"citation":{}},"total":{"value":null,"citation":{}}},
        "price_return_basis":{"verbatim":""},"occ_clearing":{"verbatim":""},
        "occ_residual_risk":{"verbatim":""},"flex_liquidity_valuation":{"verbatim":""},
        "website_delegation":{"verbatim":""}},
 "E4": {"snapshot_echo":{"snapshot_date":"YYYY-MM-DD","NAV_0":null,"NAV_t":null,"S_t":null,"source":"oracle"},
        "ledger":{"terms":{"fields":["strikes","expiry","multiplier"],"as_of":"filing"},
                  "state":{"fields":["valUSD","pctVal","net_assets"],"as_of":"YYYY-MM-DD","staleness_days":null}},
        "days_remaining":null,"citation":{}},
 "E5": {"probe":{"label":"COMPUTED|NOT_DISCLOSED","value":null,
                 "derivation":"name the inputs (NAV_0, NAV_t, stated cap) and the fixed-price-level convention; for NOT_DISCLOSED name exactly which inputs are missing from the filings and cite the website-delegation sentence"},
        "twins":[{"id":"TW1","value":null,"citation":{}},{"id":"TW2","value":null,"citation":{}}]},
 "C1": {"roles":{"K_synth":null,"K_top":null,"K_bot":null,"K_cap":null},
        "structure_class":"buffer|floor|barrier","Ref0":{"value":null,"recovery_rule":"","identity_checks":["",""]}},
 "C2": {"grid_points":[{"underlying_return_pct":null,"S_T":null,"V_usd":null,"regime":""}],
        "signature_values":{"max_per_unit_K_cap_minus_K_synth":null,
                            "buffer_zone_per_unit_K_top_minus_K_synth":null,
                            "structural_floor_K_top_minus_K_bot":null},
        "idealized_grid_check":"","max_gross_loss_pct":null},
 "C3": {"cap_gross_recomputed":{"value":null,"formula":"K_cap/Ref0 - 1","evidence":[{},{}]},
        "buffer_gross_recomputed":{"value":null,"formula":"1 - K_bot/Ref0","evidence":[{},{}]},
        "buffer_bottom_identity":{"value":null},"max_loss_gross":{"value":null},"synth_sanity":{"value":null}},
 "C4": {"cap_net":{"value":null},"buffer_net":{"value":null}},
 "C5": {"units_per_leg":null,"notional_synth":{"value":null,"labeled":"derived"},
        "coverage_ratio":null,"pctval_sum":{"value_exact":null},
        "package_value_per_unit_at_repPdDate":{"value":null,"labeled":"stale_state"}},
 "C6": {"price_levels":{"cap_price":{"value":null},"buffer_top_price":{"value":null},"buffer_bottom_price":{"value":null}},
        "remaining_cap_gross":{"value":null},"remaining_cap_net":{"value":null},"fee_proration_pp":null,
        "downside_before_buffer":{"value":null},"remaining_buffer_depth":{"value":null},
        "buffer_status":{"label":"intact|partially_consumed|below_band","S_t_vs_Ref0_pct":null,"consumed_fraction_pct":null},
        "remaining_upside_sign":"positive|~zero|negative",
        "leg_form_crosscheck":{"value":null,"labeled":"stale_secondary"}},
 "C7": {"verdicts":[{"id":"CL1","verdict":"ACCURATE|ACCURATE_AT_PERIOD_START_ONLY|WRONG_BASIS|FALSE|NOT_VERIFIABLE",
                     "deciding_figure":"","deciding_value":null,"basis_one_line":""}]},
 "S1": {"labels":{"remaining_upside_net":"positive|~zero|negative",
                  "downside_before_buffer":"none or '[X]% gap'",
                  "buffer_status":"intact|partially_consumed|below_band",
                  "stated_terms_apply_to_this_buyer":"no"},
        "framing":"2-3 sentences"},
 "S2": {"cost_block":{"capped_upside":{"cap_value_cited":null,"note":""},
                      "forgone_dividends":{"note":""},"fee_drag":{"er_pct":null,"note":""},
                      "path_exit_risk":{"note":""}},
        "credit_read":"the OCC/counterparty paragraph — right in BOTH directions"},
 "S3": {"bottom_line_reference":"4-8 sentences","not_determinable_items":[""]}
}"""


def build_messages(case, packet: str):
    snap = case.get("snapshot", {}) or {}
    claims = case.get("claims", []) or []
    probe = case.get("probe", {}) or {}
    twins = probe.get("answerable_twin", []) or []
    system = (
        "You are a buy-side derivatives/ETF analyst doing pre-recommendation diligence on a "
        "defined-outcome (buffer) ETF for a client who would buy TODAY, mid-period. Work ONLY from "
        "the filings provided plus the oracle market snapshot. The prospectus states the percentages "
        "and dates; the N-PORT holds the option legs — they share no figure and tie only through the "
        "options math, so RECOMPUTE every stated term from the strikes. Strikes are quoted on the "
        "UNDERLYING ETF'S SHARE PRICE, not the index level. Written legs carry negative balances. "
        "The stated cap/buffer apply only to a period-start buyer: compute the REMAINING terms for "
        "today's buyer from the snapshot (fixed price levels pinned to day-1 NAV: cap_price = "
        "NAV_0 x (1 + stated gross cap); remaining cap = cap_price/NAV_t - 1; net = gross - "
        "ER x days_remaining/365, ACT/365). Downside protection always has a cost — name it (capped "
        "upside, forgone dividends, fee drag, path/exit risk). DO NOT invent numbers; cite verbatim "
        "strings for every extracted figure. Return ONLY the JSON object, no prose."
    )
    claim_lines = "\n".join(f"  {c.get('id')}: \"{c.get('text')}\"" for c in claims)
    twin_lines = "\n".join(f"  {t.get('id')}: {t.get('question')}" for t in twins)
    user = (
        f"{SCHEMA}\n\n"
        f"ORACLE MARKET SNAPSHOT (not in any filing; daily NAV is an issuer-website item):\n"
        f"  snapshot_date={snap.get('snapshot_date')}  NAV_0={snap.get('NAV_0')} (outcome-period start)  "
        f"NAV_t={snap.get('NAV_t')} (today)  S_t={snap.get('S_t')} (reference ETF share price today)\n\n"
        f"MARKETING CLAIMS to verify (C7, one verdict per claim id):\n{claim_lines}\n\n"
        f"E5 PROBE (typed answer: COMPUTED with derivation, or NOT_DISCLOSED with the missing inputs "
        f"named):\n  {probe.get('question')}\n"
        f"E5 ANSWERABLE TWINS (these ARE in the filings — find and cite them):\n{twin_lines}\n\n"
        f"{packet}"
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


# ---------------- live answer ----------------
def answer(case, *, endpoint=DEFAULT_ENDPOINT, model_id=None, max_tokens=16000, e2e=False,
           deadline=900):
    """max_tokens/deadline are sized for REASONING models (Qwen3.6 etc.): the think phase streams
    as reasoning_content and can run thousands of tokens before the first content token — the
    structured JSON itself is ~3-4k tokens on top. Non-thinking models just finish early."""
    packet = build_packet(case, e2e=e2e)
    msgs = build_messages(case, packet)
    approx_tok = sum(len(m["content"]) for m in msgs) // 4
    stats = {}
    # timeout=300: a queued request (or the think->content handoff) can stall the SSE stream for
    # minutes without a byte; the wall-clock `deadline` still hard-caps the whole call.
    content, used = chat(msgs, endpoint=endpoint, model_id=model_id, max_tokens=max_tokens,
                         deadline=deadline, timeout=300, stats=stats)
    if not content.strip():
        if stats.get("reasoning_chars"):
            raise RuntimeError(
                f"Model spent its whole budget THINKING ({stats['reasoning_chars']:,} reasoning "
                f"chars, no content; prompt ~{approx_tok:,} tokens). Raise --max-tokens (currently "
                f"{max_tokens}) / deadline, or use a non-reasoning model.")
        raise RuntimeError(
            f"Model returned an EMPTY completion (prompt ~{approx_tok:,} tokens). This almost always "
            f"means the prompt exceeded the model's loaded context window in LM Studio. Reload the "
            f"model with a larger context length (>= {((approx_tok + max_tokens)//1024 + 4):d}k)"
            + (" or drop --e2e." if e2e else "."))
    try:
        out = parse_answer(content)
    except json.JSONDecodeError:
        msgs.append({"role": "assistant", "content": content[:2000]})
        msgs.append({"role": "user", "content": "That was not valid JSON. Return ONLY the JSON object."})
        content, used = chat(msgs, endpoint=endpoint, model_id=model_id, max_tokens=max_tokens,
                             deadline=deadline)
        out = parse_answer(content)
    out["_model_id"] = used
    out["_raw"] = content
    out["_prompt_tokens_approx"] = approx_tok
    out["_reasoning_chars"] = stats.get("reasoning_chars", 0)
    return out


# ---------------- schema round-trip (the offline alignment proof) ----------------
_SCHEMA_DROP = {            # gold-only fields a live model never emits, per section
    "P1": {"sibling_note"},
    "P2": {"strike_scale_sanity", "index_distractor", "deep_itm_strike_is_real", "index_distractor_citation"},
    "P3": {"comparison_plan", "stated_terms_period_start_only", "unitary_er_pct"},
    "E1": {"no_strikes_in_prospectus"},
    "E2": {"cusip_rule", "deep_itm_pctVal_note"},
    "E5": {"probe_gold", "twin_gold"},
    "C1": {"strike_order_check", "not_floor_not_barrier"},
    "C2": {"payoff_formula", "convention_note"},
    "C3": {"reconciliation_status"},
    "C4": {"stated_net_is_gold", "hundred_buffer_note"},
    "C6": {},
    "C7": {"deciding_kind_note", "both_directions_note"},
    "S1": {"label_rule_note", "must_name_gap_before_buffer_talk", "hold_to_period_end_required", "contingent_on_C6"},
    "S2": {"credit_rubric", "comparator_rule"},
    "S3": {"diligence_floor"},
}


def oracle_to_schema(case) -> dict:
    """re-serialize the case's oracle answer through the live SCHEMA shape: drop the gold-only
    fields, keep everything a schema-following live model would emit. The selftest grades this
    round-trip to prove the SCHEMA's key paths align with the suite handlers."""
    from .suites import defined_outcome as do
    m = copy.deepcopy(do.oracle(case))
    for cp, drops in _SCHEMA_DROP.items():
        sect = m.get(cp)
        if isinstance(sect, dict):
            for k in drops:
                sect.pop(k, None)
    # C7 rows: the model emits deciding_figure/value, never the gold-side deciding_kind tag
    for row in (m.get("C7", {}) or {}).get("verdicts", []) or []:
        row.pop("deciding_kind", None)
    # the JSON wire format loses YAML date objects -> strings (exactly what a live model sends)
    return json.loads(json.dumps(m, default=str))
