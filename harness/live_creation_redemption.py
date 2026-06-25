"""
harness/live_creation_redemption.py — run a REAL model on an EVAL #4 (ETF creation/redemption basket
reconciliation) case via an OpenAI-compatible endpoint (a frontier API: set OPENAI_API_KEY +
--endpoint/--model-id; or a local LM Studio server), and turn its answer into the structured
reconciliation harness/suites/creation_redemption.py grades. Reuses harness/live.py's client +
JSON-repair plumbing.

Unlike eval #3 there is NO filing to fetch: the packet is the order ticket + the published PCF
(required basket) + the AP's tendered (delivered) basket + the D2 probe — all already in the case
YAML's `order` / `pcf` / `delivery` / `probe` sections. The model's job is the WORK: reconcile the
delivery line-by-line, value the in-kind basket and the cash-in-lieu (at the STRUCK fair-value
price, not the AP's delivered price), compute the tie-out residual, and SETTLE only if it ties
within the settlement tolerance — otherwise DO_NOT_SETTLE, localized.

The SCHEMA below is the live-model contract: its key paths mirror the case gold exactly, because the
suite's graders resolve model values by the same paths (the oracle is a deepcopy of gold).
`oracle_to_schema()` re-serializes a case's oracle answer through this shape; the harness selftest
round-trips it (schema JSON -> parse -> grade -> 1.000/AllPass) to prove schema/handler alignment.
"""
from __future__ import annotations
import copy
import json
import os
from .live import DEFAULT_ENDPOINT, chat, parse_answer


# ---------------- the packet (order + PCF + delivery + probe; all in the case) ----------------
def _fmt_inkind(rows, price_key="struck_price"):
    out = []
    for r in (rows or []):
        out.append(f"  {r.get('ticker'):<6} shares={r.get('shares')}  {price_key}={r.get(price_key)}"
                   + (f"  value={r.get('value')}" if r.get("value") is not None else ""))
    return "\n".join(out)


def build_packet(case) -> str:
    order = case.get("order", {}) or {}
    pcf = case.get("pcf", {}) or {}
    deliv = case.get("delivery", {}) or {}
    man = case.get("manifest", {}) or {}
    probe = case.get("probe", {}) or {}
    tol = man.get("basket_settle_tolerance_usd")
    cil = (pcf.get("cash_in_lieu") or [{}])
    cil_d = (deliv.get("cash_in_lieu_delivered") or [{}])
    cil_lines = "\n".join(
        f"  {c.get('ticker'):<6} shares={c.get('shares')}  struck_price={c.get('struck_price')}  "
        f"(reason: {c.get('reason')})  cil_amount={c.get('cil_amount')}" for c in cil)
    cil_d_lines = "\n".join(
        f"  {c.get('ticker'):<6} shares={c.get('shares')}  price_used={c.get('price_used')}  "
        f"value={c.get('value')}  (basis: {c.get('basis')})" for c in cil_d)
    twins = probe.get("answerable_twin", []) or []
    twin_lines = "\n".join(f"  {t.get('id')}: {t.get('question')}" for t in twins)
    return (
        "=== ORDER TICKET ===\n"
        f"  fund={order.get('fund')}  ticker={order.get('ticker')}  order_id={order.get('order_id')}\n"
        f"  direction={order.get('direction')}  trade_date={order.get('trade_date')}\n"
        f"  nav_per_share={order.get('nav_per_share')}  nav_strike_date={order.get('nav_strike_date')}\n"
        f"  cu_size={order.get('cu_size')} (shares per Creation Unit)  num_cus={order.get('num_cus')}  "
        f"total_shares={order.get('total_shares')}\n"
        f"  settlement_tolerance_usd={tol}\n\n"
        "=== PUBLISHED PCF (the REQUIRED basket for the whole order) ===\n"
        "IN-KIND (deliver these securities):\n" + _fmt_inkind(pcf.get("in_kind")) + "\n"
        "CASH-IN-LIEU (halted/restricted names delivered as cash; CIL = shares x struck fair-value price):\n"
        + cil_lines + "\n"
        f"CASH COMPONENT TOTAL (balancing amount, incl. cash-in-lieu) = {pcf.get('cash_component_total')}\n"
        f"  (of which base balancing plug = {pcf.get('base_cash_plug')})\n\n"
        "=== AP DELIVERED BASKET (what the Authorized Participant actually tendered) ===\n"
        "IN-KIND delivered:\n" + _fmt_inkind(deliv.get("in_kind"), price_key="price") + "\n"
        "CASH-IN-LIEU delivered:\n" + cil_d_lines + "\n"
        f"CASH DELIVERED TOTAL = {deliv.get('cash_delivered_total')}\n"
        f"  (of which base balancing plug = {deliv.get('base_cash_plug_delivered')})\n\n"
        "=== D2 PROBE ===\n"
        f"  {probe.get('question')}\n"
        "ANSWERABLE TWIN(S) (these ARE computable from the packet):\n" + twin_lines
    )


# ---------------- the OUTPUT SCHEMA (the live-model contract; key paths mirror the case gold) ----------------
SCHEMA = """Return ONE JSON object with EXACTLY these keys. Numbers are plain (no $, no thousands
separators). Use the dollar amounts as given. Use null only where you genuinely cannot determine a
value. A citation is {"document":"pcf","locator":"<where>","verbatim":"<exact string>"}.

{
 "P1": {"fund":"","ticker":"","order_id":"","trade_date":"YYYY-MM-DD","direction":"create|redeem",
        "nav_per_share":null,"nav_strike_date":"YYYY-MM-DD","cu_size":null,"num_cus":null,
        "total_shares":null,"creation_value":null},
 "E1": {"in_kind":[{"ticker":"","shares":null,"struck_price":null}],
        "cash_in_lieu":[{"ticker":"","shares":null,"struck_price":null,"cil_amount":null,"reason":""}],
        "cash_component_total":null,"base_cash_plug":null,"citation":{}},
 "E2": {"in_kind":[{"ticker":"","shares":null,"price":null,"value":null}],
        "cash_in_lieu_delivered":[{"ticker":"","shares":null,"price_used":null,"value":null,"basis":""}],
        "cash_delivered_total":null,"base_cash_plug_delivered":null},
 "C1": {"recon":[{"ticker":"","required_shares":null,"delivered_shares":null,
                  "status":"match|short|excess|substituted|missing|extra|cil_short"}],
        "exceptions":[{"ticker":"","type":"","detail":""}]},
 "C2": {"in_kind_mv":null,"required_cash_component":null,
        "cil_required":{"ticker":"","shares":null,"struck_price":null,"amount":null},
        "cil_delivered_amount":null,"cil_shortfall":null},
 "C3": {"creation_value":null,"in_kind_mv":null,"cash_delivered":null,"total_tendered":null,
        "residual":null,"residual_status":"balanced|short|over"},
 "D1": {"decision":"SETTLE|DO_NOT_SETTLE","offending_line":null,"offending_reason":null,
        "residual":null,"escalate_to":null},
 "D2": {"probe":{"label":"NOT_DISCLOSED|COMPUTED","value":null,
                 "derivation":"for the halted name's OFFICIAL post-halt close: state it is NOT in the packet (only the fund's fair-value strike is) and name that missing input; do NOT invent a price"},
        "twins":[{"id":"TW1","value":null,"citation":{}}]}
}"""


def build_messages(case, packet: str):
    system = (
        "You are a fund-accounting / custodian operations analyst reconciling an ETF CREATION order. "
        "You are given the order ticket, the published Portfolio Composition File (PCF / required "
        "basket), and the Authorized Participant's tendered (delivered) basket. Reconcile the delivery "
        "against the PCF and the NAV-based creation value, and SETTLE only if the basket ties out "
        "within the settlement tolerance; otherwise DO_NOT_SETTLE and localize the break to the "
        "offending line. Rules:\n"
        "- creation_value = nav_per_share x cu_size x num_cus. On a creation the AP delivers in-kind "
        "securities + a cash component; total_tendered = in-kind market value + cash delivered, and it "
        "must equal creation_value.\n"
        "- A halted/restricted constituent is CASH-IN-LIEU: the REQUIRED cash for it = its shares x the "
        "PCF STRUCK (fair-value) price. Value the cash-in-lieu at the struck price, NOT at the AP's "
        "delivered price. If the AP delivered the cash-in-lieu at a different (e.g. stale prior-close) "
        "price, that is a shortfall.\n"
        "- residual = total_tendered - creation_value. If |residual| exceeds the settlement tolerance, "
        "the basket does NOT reconcile: return DO_NOT_SETTLE, name the offending line and the residual, "
        "and escalate to true up. Never approve (SETTLE) a basket that does not tie out.\n"
        "- D2 probe: the halted name's OFFICIAL post-halt closing price is NOT in the packet (only the "
        "fund's fair-value strike is). Answer NOT_DISCLOSED and name the missing input; do NOT invent "
        "it. The CURRENT tie-out residual IS computable — give it as the answerable twin.\n"
        "Return ONLY the JSON object, no prose."
    )
    user = f"{SCHEMA}\n\n{packet}"
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


# ---------------- live answer ----------------
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
_SCHEMA_DROP = {            # gold-only fields a schema-following live model never emits, per section
    "C1": {"all_in_kind_shares_tie"},
    "C2": {"cil_delivered_amount", "cil_shortfall"},   # diagnostic-only; not graded
    "C3": {"residual_status", "settle_tolerance", "ties_out", "cash_delivered"},  # cash_delivered re-added below
    "D1": {"settle_would_be_override"},
    "D2": {"probe_gold", "twin_gold"},
}


def oracle_to_schema(case) -> dict:
    """re-serialize the case's oracle answer through the live SCHEMA shape: drop the gold-only fields
    a schema-following model would not emit. The selftest grades this round-trip (-> 1.000/AllPass)
    to prove the live contract stays aligned with the suite handlers."""
    from .suites import creation_redemption as _cr
    m = copy.deepcopy(_cr.oracle(case))
    # the gold C3 stores cash_delivered; keep it (C2.scale reads model C3.cash_delivered)
    for cp, drops in _SCHEMA_DROP.items():
        sect = m.get(cp)
        if isinstance(sect, dict):
            for k in drops:
                if k == "cash_delivered":
                    continue
                sect.pop(k, None)
    return json.loads(json.dumps(m, default=str))
