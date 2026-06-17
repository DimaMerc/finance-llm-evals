"""
harness/live_dcf.py — run a REAL model on an EVAL #3 (DCF valuation) case via an OpenAI-compatible
endpoint (a frontier API: set OPENAI_API_KEY + --endpoint/--model-id; or a local LM Studio server),
and turn its answer into the structured memo harness/suites/dcf.py grades. Reuses harness/live.py's
client + JSON-repair plumbing.

Flow: build the filing packet (the 10-K's three financial statements — income / balance sheet /
cash flows — rendered from EDGAR, with a .edgar_tmp/ cache fallback) -> build the prompt (the OUTPUT
SCHEMA + the statements + the ORACLE assumption set + the dated market snapshot + the claim set +
the E5 WACC probe) -> call the model -> tolerantly parse its JSON into the model-answer shape.

A DCF is a MODEL: its forecast + WACC components + terminal are NOT in any filing, so they are fed
as the oracle assumption set in both run modes (exactly like eval #1's consensus / eval #2's
snapshot). The base lines and the EV->equity bridge are the filing's job — that is what the packet
is for. The model must NOT invent assumptions and must NOT discount unlevered FCFF at the cost of
equity or divide enterprise value by shares without the net-debt bridge.

The SCHEMA below is the live-model contract: its key paths mirror the case gold exactly, because the
suite's graders resolve model values by the same paths (the oracle is a deepcopy of gold).
`oracle_to_schema()` re-serializes a case's oracle answer through this shape; the harness selftest
round-trips it (schema JSON -> parse -> grade -> 1.000/AllPass) to prove schema/handler alignment.
"""
from __future__ import annotations
import copy
import json
import os
import re
import urllib.request
from .live import UA, DEFAULT_ENDPOINT, chat, parse_answer
from .rubric import REPO

CACHE_DIR = os.path.join(REPO, ".edgar_tmp")


# ---------------- filing packet: the three financial statements ----------------
def _accession_path(case) -> tuple[str, str]:
    """(cik, accession-no-dashes) for the EDGAR Archives R-file URLs."""
    tenk = (case.get("sources", {}) or {}).get("tenk", {}) or {}
    acc = (tenk.get("accession") or "").replace("-", "")
    cik = str(int((case.get("manifest", {}) or {}).get("cik") or "0"))
    return cik, acc


def _fetch_rfile(cik: str, acc: str, rfile: str) -> str:
    """fetch a rendered statement R-file; prefer the .edgar_tmp cache (offline dev / EDGAR courtesy)."""
    cache_name = f"dcf_{acc}_{rfile}"
    p = os.path.join(CACHE_DIR, cache_name)
    if os.path.exists(p):
        with open(p, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc}/{rfile}"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=90) as r:
        raw = r.read().decode("utf-8", "ignore")
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(raw)
    except OSError:
        pass
    return raw


def _statement_text(html: str, max_rows: int = 80) -> str:
    """pull a rendered statement R-file down to clean `label | val1 | val2 | val3` rows (the
    XBRL-definition tooltips at the foot are dropped)."""
    import html as _h
    rows = re.findall(r"(?is)<tr[^>]*>(.*?)</tr>", html)
    out = []
    for r in rows:
        cells = re.findall(r"(?is)<t[dh][^>]*>(.*?)</t[dh]>", r)
        clean = [re.sub(r"\s+", " ", _h.unescape(re.sub(r"(?s)<[^>]+>", " ", c))).strip() for c in cells]
        clean = [c for c in clean if c and c not in ("$", "%")]
        if not clean:
            continue
        if clean[0].startswith("- Definition") or "us-gaap_" in clean[0] or "Reference 1:" in r:
            continue
        out.append(" | ".join(clean[:4]))
        if len(out) >= max_rows:
            break
    return "\n".join(out)


def build_packet(case) -> str:
    cik, acc = _accession_path(case)
    # R3 income, R7 balance sheet, R9 cash flows (the standard MCD ordering)
    rmap = {"income": "R3.htm", "balance": "R7.htm", "cash_flow": "R9.htm"}
    titles = {"income": "CONSOLIDATED STATEMENT OF INCOME",
              "balance": "CONSOLIDATED BALANCE SHEET",
              "cash_flow": "CONSOLIDATED STATEMENT OF CASH FLOWS"}
    parts = []
    for key in ("income", "balance", "cash_flow"):
        rfile = rmap[key]
        try:
            text = _statement_text(_fetch_rfile(cik, acc, rfile))
        except Exception as e:                                  # offline / network: name the gap, don't crash
            text = f"[could not fetch {rfile}: {e}]"
        parts.append(f"=== {titles[key]} (10-K {rfile}; columns are the three most recent fiscal years, "
                     f"latest FIRST) ===\n{text}")
    return "\n\n".join(parts)


# ---------------- the OUTPUT SCHEMA (the live-model contract; key paths mirror the case gold) ----------------
SCHEMA = """Return ONE JSON object with EXACTLY these keys. Citations are
{"document":"10K","locator":"<statement + line caption>","verbatim":"<exact printed string incl. the figure>"}.
Numbers are plain (no $ signs, no thousands separators); rates/percentages in percentage POINTS
(7.15 not 0.0715; 21.4 not 0.214); the terminal g as a FRACTION (0.025). Dollar figures in the
filing's reporting units (millions). Use null only where you genuinely cannot determine a value.

{
 "P1": {"ticker":"","cik":"","fiscal_year":0,"valuation_date":"YYYY-MM-DD","currency":"USD",
        "units":"millions","fcf_basis":"unlevered_FCFF","discount_rate_for_fcff":"WACC",
        "output_chain":"FCFF -> WACC -> EV -> bridge -> equity -> per_share",
        "horizon_years":0,"terminal_method":"gordon","consistency":"","citation":{}},
 "P2": {"units":"millions","wacc_basis":{"weights":"market","cost_of_debt":"after_tax","capm":"rf + beta*ERP"},
        "discounting_convention":"year_end|mid_year","nominal_consistency":"nominal_cashflows_nominal_wacc_nominal_g",
        "lease_treatment":"operating","citation":{}},
 "P3": {"terminal_method":"gordon","terminal_param_g":null,
        "consistency_rules":["g < WACC strictly","g <= long-run nominal GDP","terminal-year FCFF normalized"],
        "input_map":{"filed":["revenue","ebit","dep_amort","capex","total_debt","cash","diluted_shares"],
                     "oracle":["revenue_growth","cash_tax_rate","wacc_components","terminal_g","convention"]}},
 "E1": {"figures":{"revenue":{"value":null,"citation":{}},"ebit":{"value":null,"citation":{}},
                   "tax_provision":{"value":null,"citation":{}},"effective_tax_rate":{"value":null,"citation":{}},
                   "dep_amort":{"value":null,"citation":{}},"capex":{"value":null,"citation":{}}}},
 "E2": {"figures":{"total_debt":{"value":null,"citation":{}},"cash_and_equiv":{"value":null,"citation":{}},
                   "net_debt":{"value":null},"minority_interest":{"value":null},"preferred":{"value":null},
                   "non_op_assets":{"value":null,"citation":{}},"diluted_shares":{"value":null,"citation":{}}},
        "lease_exclusion":"operating-lease liabilities excluded from net debt (rent stays in EBIT)",
        "negative_book_equity_note":""},
 "E3": {"intake_complete":true,
        "wacc_components_present":["risk_free","beta","equity_risk_premium","pre_tax_cost_of_debt","target_debt_weight"],
        "not_filed":"the discount rate and the forecast are oracle inputs, in no filing"},
 "E4": {"snapshot_echo":{"valuation_date":"YYYY-MM-DD","share_price":null,"diluted_shares_asof":null,
                         "net_debt_asof":null,"source":"oracle"},
        "staleness":{"filed_balance_date":"YYYY-MM-DD","staleness_days":null},
        "price_not_from_filing":true,"citation":{}},
 "E5": {"probe":{"label":"COMPUTED|NOT_DISCLOSED","value":null,
                 "derivation":"name the CAPM inputs (rf, beta, ERP), the after-tax Kd, and the market weights; for NOT_DISCLOSED state that no 10-K discloses a WACC and that it is built from market inputs"},
        "twins":[{"id":"TW1","value":null,"citation":{}},{"id":"TW2","value":null,"citation":{}}]},
 "C1": {"tax_rate_used":null,
        "per_year":[{"t":1,"revenue":null,"ebit":null,"nopat":null,"da":null,"capex":null,"dnwc":null,"fcff":null}]},
 "C2": {"ke":{"value":null},"kd_after":{"value":null},"wacc":{"value":null},
        "weights":"market weights; after-tax Kd; no rf/ERP double-count"},
 "C3": {"convention":"year_end|mid_year","rate_is_c2_wacc":true,
        "per_year":[{"t":1,"discount_factor":null,"pv_fcff":null}],"sum_pv_explicit":{"value":null}},
 "C4": {"tv_undiscounted":{"value":null},"pv_tv":{"value":null},"implied_exit_ev_ebit":{"value":null},
        "terminal_normalized":true},
 "C5": {"ev":{"value":null},"consistency":"enterprise (unlevered) value, FCFF discounted at WACC",
        "tv_share_of_ev":{"value":null}},
 "C6": {"equity":{"value":null,"formula":"EV - net_debt - minority - preferred + non_op_assets"},
        "per_share":{"value":null,"formula":"equity / diluted_shares"}},
 "C7": {"grid":[{"wacc":null,"g":null,"per_share":null}],
        "tv_share_of_ev":{"value":null},"implied_exit_ev_ebit":{"value":null},
        "upside_vs_price":{"value":null},"upside_sign":"downside|upside",
        "verdicts":[{"id":"CL1","verdict":"ACCURATE|ACCURATE_ON_BASE_CASE_ONLY|WRONG_BASIS|FALSE|NOT_VERIFIABLE",
                     "deciding_figure":"","deciding_value":null,"basis_one_line":""}]},
 "S1": {"labels":{"fair_value_per_share":null,"vs_price":"undervalued|~fairly_valued|overvalued",
                  "upside_pct":null,"basis":"equity_value_per_share"},
        "hold_to_thesis_required":true},
 "S2": {"sensitivity_block":{"terminal_value_share_of_ev":null,
                             "wacc_sensitivity_per_share":{"down_50bp":null,"base":null,"up_50bp":null},
                             "g_sensitivity_per_share":{"g_low":null,"base":null,"g_high":null},
                             "key_value_driver":""},
        "risk_read":["cyclicality","discount-rate sensitivity","terminal dominance"]},
 "S3": {"bottom_line_reference":"4-8 sentences","assumption_conditional":true,
        "diligence_floor":["cyclicality","leverage","capex normalization","trading-multiple cross-check"],
        "not_determinable_items":["the company's own WACC (constructed from market inputs, not filed)"]}
}"""


def build_messages(case, packet: str):
    asm = case.get("assumptions", {}) or {}
    snap = case.get("snapshot", {}) or {}
    claims = case.get("claims", []) or []
    probe = case.get("probe", {}) or {}
    twins = probe.get("answerable_twin", []) or []
    wc = asm.get("wacc_components", {}) or {}
    term = asm.get("terminal", {}) or {}
    system = (
        "You are an equity-research analyst building a discounted-cash-flow valuation. The BASE lines "
        "(revenue, operating income/EBIT, the tax provision, D&A and capex from the cash-flow "
        "statement, and the EV->equity bridge items: total debt, cash, minority, preferred, "
        "equity-method investments, diluted shares) come ONLY from the 10-K provided — extract them and "
        "cite the verbatim line. The forecast, the WACC components, and the terminal growth are the "
        "ORACLE assumption set below; they are in NO filing — use them exactly, never invent or alter "
        "them, and never attribute them to the filing. Project UNLEVERED free cash flow "
        "(FCFF = EBIT*(1-cash_tax_rate) + D&A - Capex - dNWC), discount at WACC (NOT the cost of "
        "equity), capitalize a Gordon terminal value (g < WACC strictly), sum to ENTERPRISE value, "
        "then BRIDGE to equity (subtract net debt, minority, preferred; add non-operating/equity-method "
        "assets) and divide by diluted shares — never divide enterprise value by shares directly. "
        "Treat leases as operating (rent stays in EBIT; lease liabilities excluded from net debt). "
        "Report the fair value as a RANGE over a +-50bp WACC band with the terminal-value share of EV, "
        "not a single decimal-precise target. Return ONLY the JSON object, no prose."
    )
    margin = asm.get("operating_margin")
    growth = asm.get("revenue_growth")
    claim_lines = "\n".join(f"  {c.get('id')}: \"{c.get('text')}\"" for c in claims)
    twin_lines = "\n".join(f"  {t.get('id')}: {t.get('question')}" for t in twins)
    user = (
        f"{SCHEMA}\n\n"
        f"ORACLE ASSUMPTION SET (a DCF is a model; these are in NO filing — use them exactly):\n"
        f"  horizon_years={asm.get('horizon_years')}  revenue_growth={growth}  operating_margin={margin}\n"
        f"  cash_tax_rate={asm.get('cash_tax_rate')}  da_pct_of_revenue={asm.get('da_pct_of_revenue')}  "
        f"capex_pct_of_revenue={asm.get('capex_pct_of_revenue')}  delta_nwc_per_year={asm.get('delta_nwc_per_year')}\n"
        f"  WACC components: risk_free={wc.get('risk_free')}  beta={wc.get('beta')}  "
        f"equity_risk_premium={wc.get('equity_risk_premium')}  pre_tax_cost_of_debt={wc.get('pre_tax_cost_of_debt')}  "
        f"target_debt_weight={wc.get('target_debt_weight')}\n"
        f"  terminal: method={term.get('method')}  g={term.get('g')}   discounting_convention={asm.get('discounting_convention')}\n\n"
        f"ORACLE MARKET SNAPSHOT (the price the valuation is judged against; not in any filing):\n"
        f"  valuation_date={snap.get('valuation_date')}  share_price={snap.get('share_price')}  "
        f"diluted_shares_asof={snap.get('diluted_shares_asof')}  net_debt_asof={snap.get('net_debt_asof')}\n\n"
        f"VALUATION CLAIMS to verify (C7, one verdict per claim id):\n{claim_lines}\n\n"
        f"E5 PROBE (typed answer: COMPUTED with the CAPM derivation, or NOT_DISCLOSED naming why it is "
        f"not in the filing):\n  {probe.get('question')}\n"
        f"E5 ANSWERABLE TWINS (these ARE in the 10-K — find and cite them):\n{twin_lines}\n\n"
        f"{packet}"
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


# ---------------- live answer ----------------
def answer(case, *, endpoint=DEFAULT_ENDPOINT, model_id=None, api_key=None, max_tokens=12000,
           deadline=600):
    # the full DCF JSON (18 checkpoints, the per-year build, the grid, the verdicts, the synthesis)
    # runs ~5-7k tokens; a verbose model truncates mid-synthesis at 8k -> an empty S2 sensitivity block
    # spuriously fires GATE.FALSEPRECISION. 12k is the safe floor (raise it for a reasoning model).
    packet = build_packet(case)
    msgs = build_messages(case, packet)
    approx_tok = sum(len(m["content"]) for m in msgs) // 4
    stats = {}
    key = api_key or os.environ.get("OPENAI_API_KEY") or os.environ.get("OPENROUTER_API_KEY")
    content, used = chat(msgs, endpoint=endpoint, model_id=model_id, max_tokens=max_tokens,
                         deadline=deadline, timeout=300, stats=stats, api_key=key)
    if not content.strip():
        if stats.get("reasoning_chars"):
            raise RuntimeError(
                f"Model spent its whole budget THINKING ({stats['reasoning_chars']:,} reasoning chars, "
                f"no content; prompt ~{approx_tok:,} tokens). Raise --max-tokens (currently {max_tokens}).")
        raise RuntimeError(f"Model returned an EMPTY completion (prompt ~{approx_tok:,} tokens).")
    try:
        out = parse_answer(content)
    except json.JSONDecodeError:
        first_raw = content
        msgs.append({"role": "assistant", "content": content[:2000]})
        msgs.append({"role": "user", "content": "That was not valid JSON. Return ONLY the JSON object."})
        try:
            content, used = chat(msgs, endpoint=endpoint, model_id=model_id, max_tokens=max_tokens,
                                 deadline=deadline, timeout=300, api_key=key)
            out = parse_answer(content)
        except Exception as e:
            err = RuntimeError(f"unparseable model JSON and the retry failed too: {e}")
            err.raw = first_raw
            raise err from e
    out["_model_id"] = used
    out["_raw"] = content
    out["_prompt_tokens_approx"] = approx_tok
    out["_reasoning_chars"] = stats.get("reasoning_chars", 0)
    return out


# ---------------- schema round-trip (the offline alignment proof) ----------------
_SCHEMA_DROP = {            # gold-only fields a schema-following live model never emits, per section
    "P1": {"consistency_note"},
    "P2": {"scale_lock", "lease_exclusion_note", "negative_book_equity_note"},
    "P3": {},
    "E1": {"ebit_not_ni_note", "da_capex_source", "tax_for_fcff", "no_assumption_from_filing"},
    "E2": {},
    "E5": {"probe_gold", "twin_gold"},
    "C1": {"fcff_formula", "definition_check"},
    "C4": {"g_lt_wacc", "tv_discount_exponent"},
    "C5": {},
    "C6": {"bridge_complete", "ev_per_share_blunder"},
    "C7": {"both_directions_note"},
    "S1": {"direction_matches_c7", "contingent_on_C6"},
    "S2": {"no_false_precision", "sensitivity_block_gold"},   # the live model emits sensitivity_block
    "S3": {},
}


def oracle_to_schema(case) -> dict:
    """re-serialize the case's oracle answer through the live SCHEMA shape: drop the gold-only fields,
    rename the S2 sensitivity block to the live key, and emit C7 rows without the gold-side
    deciding_kind. The selftest grades this round-trip (-> 1.000/AllPass) to prove alignment."""
    from .suites import dcf as _dcf
    m = copy.deepcopy(_dcf.oracle(case))
    # the live model emits S2.sensitivity_block (not the gold's *_gold key)
    s2 = m.get("S2") or {}
    if isinstance(s2, dict) and s2.get("sensitivity_block_gold") and not s2.get("sensitivity_block"):
        s2["sensitivity_block"] = s2["sensitivity_block_gold"]
    for cp, drops in _SCHEMA_DROP.items():
        sect = m.get(cp)
        if isinstance(sect, dict):
            for k in drops:
                sect.pop(k, None)
    for row in (m.get("C7", {}) or {}).get("verdicts", []) or []:
        row.pop("deciding_kind", None)
    return json.loads(json.dumps(m, default=str))
