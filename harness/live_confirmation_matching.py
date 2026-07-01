"""
harness/live_confirmation_matching.py — run a REAL model on an EVAL #5 (OTC derivative confirmation
matching) case via an OpenAI-compatible endpoint, and turn its answer into the structured match the
suite grades. Reuses harness/live.py's client + JSON-repair plumbing.

The packet is the two confirmations (ours + the counterparty's) + the D2 probe — all in the case
YAML's `our_confirmation` / `counterparty_confirmation` / `probe` sections. The model's job: extract
both sides, compare field-by-field, judge which differences are material vs expected, and AFFIRM
only if the economic terms tie.

The SCHEMA below is the live-model contract; its key paths mirror the case gold (the oracle is a
deepcopy of gold). `oracle_to_schema()` round-trips it (schema JSON -> parse -> grade -> 1.000/AllPass)
in the selftest to prove schema/handler alignment.
"""
from __future__ import annotations
import copy
import json
import os
from .live import DEFAULT_ENDPOINT, chat, parse_answer


def _fmt_terms(t: dict) -> str:
    if not isinstance(t, dict):
        return "  (none)"
    order = ["product_type", "notional", "currency", "trade_date", "effective_date", "termination_date",
             "fixed_rate", "fixed_payer", "fixed_receiver", "fixed_day_count", "fixed_frequency",
             "float_index", "float_tenor", "float_spread", "float_payer", "float_receiver",
             "float_day_count", "float_frequency", "business_day_convention"]
    return "\n".join(f"  {k} = {t.get(k)}" for k in order if k in t)


def build_packet(case) -> str:
    ours = case.get("our_confirmation", {}) or {}
    cpty = case.get("counterparty_confirmation", {}) or {}
    probe = case.get("probe", {}) or {}
    twins = probe.get("answerable_twin", []) or []
    twin_lines = "\n".join(f"  {t.get('id')}: {t.get('question')}" for t in twins)
    return (
        "=== OUR CONFIRMATION ===\n"
        f"  {ours.get('party_role')}\n  trade_id = {ours.get('trade_id')}\n"
        + _fmt_terms(ours.get("terms")) + "\n\n"
        "=== COUNTERPARTY CONFIRMATION ===\n"
        f"  {cpty.get('party_role')}\n  trade_id = {cpty.get('trade_id')}\n"
        + _fmt_terms(cpty.get("terms")) + "\n\n"
        "=== D2 PROBE ===\n"
        f"  {probe.get('question')}\n"
        "ANSWERABLE TWIN(S) (in the confirmations):\n" + twin_lines
    )


SCHEMA = """Return ONE JSON object with EXACTLY these keys. Numbers plain (no % signs): the fixed
rate as a DECIMAL (0.06, not 6). Use null where genuinely not determinable. A citation is
{"document":"fpml","locator":"<where>","verbatim":"<exact string>"}.

{
 "P1": {"product_type":"","single_currency":true,"fixed_float":true,
        "partyA":{"lei":"","name":""},"partyB":{"lei":""},"trade_date":"","our_trade_id":"","cpty_trade_id":""},
 "E1": {"terms":{"notional":null,"currency":"","fixed_rate":null,"fixed_payer":"","fixed_receiver":"",
                 "fixed_day_count":"","fixed_frequency":"","float_index":"","float_tenor":"",
                 "float_day_count":"","float_frequency":"","effective_date":"","termination_date":"",
                 "business_day_convention":""},"citation":{}},
 "E2": {"terms":{"notional":null,"currency":"","fixed_rate":null,"fixed_payer":"","fixed_receiver":"",
                 "fixed_day_count":"","fixed_frequency":"","float_index":"","float_tenor":"",
                 "float_day_count":"","float_frequency":"","effective_date":"","termination_date":"",
                 "business_day_convention":""}},
 "C1": {"compare":[{"field":"","our":null,"cpty":null,"status":"match|mismatch"}],
        "direction_ok":true,"fixed_payer":""},
 "C2": {"material_breaks":[],"expected_diffs":[]},
 "C3": {"matches":true,"offending_field":null,"our_value":null,"cpty_value":null,"economic_impact":null},
 "D1": {"decision":"AFFIRMED|MISMATCHED","offending_field":null,"our_value":null,
        "counterparty_value":null,"action":""},
 "D2": {"probe":{"label":"NOT_DETERMINABLE|COMPUTED","value":null,
                 "derivation":"for the mark-to-market: state it is NOT determinable from a confirmation (needs market data / a discount curve, absent from the packet); do NOT invent a number"},
        "twins":[{"id":"TW1","value":null,"citation":{}}]}
}"""


def build_messages(case, packet: str):
    system = (
        "You are an OTC derivatives affirmation / operations analyst. You are given two confirmations "
        "of the SAME interest-rate swap — ours and the counterparty's. Match the ECONOMIC terms "
        "field-by-field and AFFIRM the trade only if they tie; otherwise it is a MISMATCH (do not "
        "affirm; escalate). Rules:\n"
        "- Compare notional, currency, the fixed rate, day-counts, the floating index/tenor, "
        "frequencies, dates, business-day convention, and the leg DIRECTION (who pays fixed vs float). "
        "The two confirmations should agree on all economic terms.\n"
        "- NOT every difference is a break. The two parties' trade ids differ BY DESIGN (each assigns "
        "its own internal id) — that is EXPECTED, not a material break. A difference in the fixed "
        "rate, notional, dates, day-count, or direction IS a material economic break.\n"
        "- If a material term does not tie, return MISMATCHED, name the offending field and both "
        "values, quantify the economic impact, and escalate. NEVER affirm a trade whose economic "
        "terms do not tie.\n"
        "- D2 probe: a confirmation states the trade's TERMS, not its VALUE. The swap's mark-to-market "
        "needs a discount curve / current market rates, which are NOT in the packet — answer "
        "NOT_DETERMINABLE and say why; do NOT invent a number. The answerable twin IS in the messages.\n"
        "Return ONLY the JSON object, no prose."
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": f"{SCHEMA}\n\n{packet}"}]


def answer(case, *, endpoint=DEFAULT_ENDPOINT, model_id=None, api_key=None, max_tokens=8000, deadline=600):
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
_SCHEMA_DROP = {
    "C2": {"materiality_note", "scale_ok"},
    "C3": {"impact_note"},
    "D1": {"affirm_would_be_override"},
    "D2": {"probe_gold", "twin_gold"},
}


def oracle_to_schema(case) -> dict:
    """re-serialize the case's oracle answer through the live SCHEMA shape (drop gold-only fields).
    The selftest grades this round-trip (-> 1.000/AllPass) to prove alignment with the handlers."""
    from .suites import confirmation_matching as _cm
    m = copy.deepcopy(_cm.oracle(case))
    for cp, drops in _SCHEMA_DROP.items():
        sect = m.get(cp)
        if isinstance(sect, dict):
            for k in drops:
                sect.pop(k, None)
    return json.loads(json.dumps(m, default=str))
