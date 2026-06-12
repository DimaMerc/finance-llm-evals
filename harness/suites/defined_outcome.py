"""
harness/suites/defined_outcome.py — the EVAL #2 (defined-outcome / buffer ETF) suite.

Grades a model's suitability memo for a buffer ETF against the KOCT-style case gold
(rubric/criteria-defined-outcome.yaml, 18 checkpoints, calculation-heavy). Everything the
workflow doc declares deterministic is graded deterministically here: leg extraction, the
payoff reconstruction, the recompute-vs-stated spine, fee netting, tie-outs, the remaining
outcome at NAV_t, and claim verdicts. The judge tier (S1-S3) uses presence/consistency mocks
offline (the live LLM judge is the online swap, judge.md §8).

Suite-specific machinery:
  * E5 calibrated refusal with the {COMPUTED, value, derivation} typed-answer extension —
    the G-mapping documented in judge.md §8: in-band COMPUTED with derivation -> G=1.0;
    NOT_DISCLOSED naming the missing inputs -> G=0.75; vague hedge / out-of-band -> G=0.25;
    a confident underived number -> G=0.0 (E5.n_fabricate fires, and with it GATE.FABRICATION).
  * GATE.FREELUNCH: the deterministic predicate on S2's structured cost-of-protection block
    (present, non-empty, cap consistent with C3) — firing zeros S2+S3 and raises the
    free_lunch_fired headline flag (scoring surfaces it on the Result).
  * C7 deciding_kind: recompute rows need a C3/C4/C6 figure; disclosure/scope rows are decided
    by cited filing language / the packet boundary (rubric 1.0.1).

Model-answer shape: mirrors the case gold (the oracle is a deepcopy), with E5 answered as
  model["E5"] = {"probe": {label, value, derivation}, "twins": [{id, value, citation}, ...]}.
"""
from __future__ import annotations
import copy
import re
from ..graders import Verdict, _num, _eq, _overlap, _cite_overlap
from ..tolerances import within

REFUSAL_CP = "E5"
LLM_JUDGE_CPS = {"S2", "S3"}   # S1 stays on the mock: its C6-contingency must always run (F11)
MEMO_KIND = "an advisor's defined-outcome (buffer) ETF suitability memo"


# ---------------- small access helpers ----------------
def _g(d, *path, default=None):
    cur = d
    for p in path:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(p)
    return cur if cur is not None else default


def _legs(container):
    return _g(container, "E2", "legs", default=[]) or []


def _match_leg(legs, gleg):
    """match a model leg to a gold leg: exact strike first, then (type, direction)."""
    gs = _num({"value": gleg.get("strike")})
    for L in legs:
        ms = _num({"value": L.get("strike")})
        if ms is not None and gs is not None and abs(ms - gs) <= 0.005:
            return L
    for L in legs:
        if _eq(L.get("put_or_call"), gleg.get("put_or_call")) and \
           _eq(L.get("written_or_purchased"), gleg.get("written_or_purchased")):
            return L
    return None


def _verbatim_present(model_node, gold_node) -> bool:
    """a captured-language atom: the model carries the verbatim and it overlaps the gold's."""
    mv = (model_node or {}).get("verbatim") if isinstance(model_node, dict) else model_node
    gv = (gold_node or {}).get("verbatim") if isinstance(gold_node, dict) else gold_node
    return bool(mv) and bool(gv) and _overlap(str(mv), str(gv), 0.5)


def _grid_map(container):
    rows = _g(container, "C2", "grid_points", default=[]) or []
    out = {}
    for r in rows:
        k = r.get("underlying_return_pct")
        if isinstance(k, (int, float)):
            out[float(k)] = r
    return out


def _vrows(container):
    rows = _g(container, "C7", "verdicts", default=[]) or []
    return {r.get("id"): r for r in rows if isinstance(r, dict)}


def _sentences(text: str) -> int:
    parts = [p for p in re.split(r"(?<=[.!?])\s+(?=[A-Z])", (text or "").strip()) if p.strip()]
    return len(parts)


def _label(v):
    """normalize a verdict label: a YAML bare FALSE/TRUE parses as bool — map back to the enum string."""
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    return v


def _meaty(x):
    """non-trivial content for a required block item: a dict with any substantive value, a string of
    >=3 tokens (or a gold.* anchor reference), or a real number — placeholder dashes/blanks fail."""
    if isinstance(x, dict):
        return any(_meaty(v) for v in x.values())
    if isinstance(x, str):
        return len(x.split()) >= 3 or x.startswith("gold.")
    if isinstance(x, bool):
        return False
    return isinstance(x, (int, float))


def _cost_block(model):
    s2 = model.get("S2", {}) or {}
    blk = s2.get("cost_block") or s2.get("cost_block_gold")
    return blk if isinstance(blk, dict) and blk else None


# ---------------- the handler chain (None => generic fallback in the engine) ----------------
def handle(a, ctx):
    model, gold, tol = ctx.model, ctx.gold, ctx.tol
    snap = gold.get("_snapshot") or {}
    sid = a.source_id

    def det(met, note=""):
        return Verdict(float(met), "deterministic", note)

    # ============================== per-row expansions ==============================
    if sid == "E1.terms":
        fn = a.figure_name
        gnode = _g(gold, "E1", "figures", fn)
        mnode = _g(model, "E1", "figures", fn)
        if a.tolerance:                                  # cap/buffer gross+net at printed rounding
            return det(within(_num(mnode), _num(gnode), a.tolerance, tol))
        gv = (gnode or {}).get("value")                  # period_start / period_end (dates)
        mv = (mnode or {}).get("value")
        return det(_eq(mv, gv))
    if sid == "E2.legs":
        i = int(a.figure_name.split("_")[1])
        glegs = _legs(gold)
        if i >= len(glegs):
            return det(0.0, "gold leg missing")
        gleg = glegs[i]
        mleg = _match_leg(_legs(model), gleg)
        if mleg is None:
            return det(0.0, "leg not found")
        ok = (_eq(mleg.get("put_or_call"), gleg.get("put_or_call"))
              and _eq(mleg.get("written_or_purchased"), gleg.get("written_or_purchased"))
              and within(_num({"value": mleg.get("strike")}), _num({"value": gleg.get("strike")}), "exact_cents", tol)
              and _eq(mleg.get("expiry"), gleg.get("expiry"))
              and within(_num({"value": mleg.get("contracts_signed")}), _num({"value": gleg.get("contracts_signed")}), "exact_int", tol)
              and within(_num({"value": mleg.get("multiplier")}), _num({"value": gleg.get("multiplier")}), "exact_int", tol))
        return det(ok, f"leg {gleg.get('leg_id')}")
    if sid == "E2.cite":
        i = int(a.figure_name.split("_")[1])
        glegs = _legs(gold)
        if i >= len(glegs):
            return Verdict(0.0, "entailment", "gold leg missing")
        gleg = glegs[i]
        mleg = _match_leg(_legs(model), gleg)
        mtitle = (mleg or {}).get("title_verbatim") or _g(mleg or {}, "citation", "verbatim", default="")
        return Verdict(1.0 if _overlap(str(mtitle), str(gleg.get("title_verbatim") or ""), 0.5) else 0.0,
                       "entailment", "leg title cite")
    if sid == "C2.regimes":
        i = int(a.figure_name.split("_")[1])
        grows = _g(gold, "C2", "grid_points", default=[]) or []
        if i >= len(grows):
            return det(0.0, "gold grid row missing")
        gr = grows[i]
        mrow = _grid_map(model).get(float(gr.get("underlying_return_pct")))
        mv = _num({"value": (mrow or {}).get("V_usd")})
        return det(within(mv, _num({"value": gr.get("V_usd")}), "payoff_usd", tol),
                   f"V(S_T) @ {gr.get('underlying_return_pct')}%")
    if sid == "C7.verdicts":
        i = int(a.figure_name.split("_")[1])
        grows = _g(gold, "C7", "verdicts", default=[]) or []
        if i >= len(grows):
            return det(0.0, "gold claim row missing")
        gr = grows[i]
        mr = _vrows(model).get(gr.get("id"))
        return det(_eq(_label((mr or {}).get("verdict")), _label(gr.get("verdict"))), f"claim {gr.get('id')}")

    # ============================== planning ==============================
    P1g, P1m = gold.get("P1", {}) or {}, model.get("P1", {}) or {}
    P2g, P2m = gold.get("P2", {}) or {}, model.get("P2", {}) or {}
    P3g, P3m = gold.get("P3", {}) or {}, model.get("P3", {}) or {}
    if a.id == "P1.1":
        return det(_eq(P1m.get("trust"), P1g.get("trust")) and _eq(P1m.get("series_id"), P1g.get("series_id"))
                   and _eq(P1m.get("series_name"), P1g.get("series_name")))
    if a.id == "P1.2":      # GATE.VINTAGE — the joint pin {seriesId, seriesName, expDt/period, vintage}
        ok = (_eq(P1m.get("series_id"), P1g.get("series_id"))
              and _eq(P1m.get("vintage_month"), P1g.get("vintage_month"))
              and _eq(P1m.get("outcome_period_start"), P1g.get("outcome_period_start"))
              and _eq(P1m.get("outcome_period_end"), P1g.get("outcome_period_end")))
        return det(ok, "vintage pin (hard gate)")
    if a.id == "P1.3":
        gl, ml = P1g.get("date_ledger") or {}, P1m.get("date_ledger") or {}
        ok = all(_eq(ml.get(k), gl.get(k)) for k in
                 ("outcome_start", "outcome_end_eq_expiry", "nport_repPdDate", "nport_repPdEnd"))
        return det(ok, "date quadruple")
    if a.id == "P1.4":
        return det(_eq(P1m.get("variant_type"), P1g.get("variant_type")))
    if a.id == "P1.5":
        return Verdict(1.0 if _cite_overlap(P1m.get("citation"), P1g.get("citation")) else 0.0,
                       "entailment", "period sentence cite")
    if a.id == "P1.6":
        need = ("trust", "series_id", "ticker", "vintage_month",
                "outcome_period_start", "outcome_period_end", "variant_type")
        return det(all(P1m.get(k) not in (None, "") for k in need), "pinned header")
    if a.id == "P2.1":      # GATE.REFSCALE — the gate's condition names THREE families:
        # index-level strikes, multiplier dropped, written-leg sign flipped (rubric + workflow C7).
        ok_asset = _eq(_g(P2m, "reference_asset", "ticker"), _g(P2g, "reference_asset", "ticker"))
        ok_flag = P2m.get("reference_is_etf_share_price", False) is True
        mstr = [_num({"value": L.get("strike")}) for L in _legs(model)]
        gstr = [_num({"value": L.get("strike")}) for L in _legs(gold)]
        mtop = max((s for s in mstr if s), default=None)
        gtop = max((s for s in gstr if s), default=None)
        ok_scale = True if (mtop is None or gtop in (None, 0)) else (0.5 <= mtop / gtop <= 2.0)
        gm = _num({"value": P2g.get("contract_multiplier")})
        mm = _num({"value": P2m.get("contract_multiplier")})
        ok_mult = True if (gm is None or mm is None) else abs(mm - gm) < 0.5
        if gm is not None:
            for L in _legs(model):
                lv = _num({"value": L.get("multiplier")})
                if lv is not None and abs(lv - gm) >= 0.5:
                    ok_mult = False
        ok_sign = True
        for L in _legs(model):        # internal: a leg's own label vs its own signed balance
            c = _num({"value": L.get("contracts_signed")})
            d = L.get("written_or_purchased")
            if c is None or d is None:
                continue
            if (_eq(d, "Written") and c > 0) or (_eq(d, "Purchased") and c < 0):
                ok_sign = False
        for gleg in _legs(gold):      # vs the filing: matched legs' sign vs the filed direction
            mleg = _match_leg(_legs(model), gleg)
            c = _num({"value": (mleg or {}).get("contracts_signed")})
            if c is None:
                continue
            if _eq(gleg.get("written_or_purchased"), "Written") != (c < 0):
                ok_sign = False
        return det(ok_asset and ok_flag and ok_scale and ok_mult and ok_sign,
                   "scale + multiplier + sign conventions (hard gate)")
    if a.id == "P2.2":
        return det(within(_num({"value": P2m.get("contract_multiplier")}),
                          _num({"value": P2g.get("contract_multiplier")}), "exact_int", tol))
    if a.id == "P2.3":
        if not _eq(P2m.get("sign_convention"), "written_legs_negative"):
            return det(0.0, "sign convention not locked")
        ok = True
        for L in _legs(model):        # internally consistent: own label vs own signed balance
            c = _num({"value": L.get("contracts_signed")})
            d = L.get("written_or_purchased")
            if c is None or d is None:
                continue
            if (_eq(d, "Written") and c > 0) or (_eq(d, "Purchased") and c < 0):
                ok = False
        return det(ok, "written legs negative (internally consistent)")
    if a.id == "P2.4":
        gsyn = next((L for L in _legs(gold) if _eq(L.get("leg_id"), "synth")), None)
        if gsyn is None:
            return det(1.0, "no synth leg in gold")
        mleg = _match_leg(_legs(model), gsyn)
        return det(mleg is not None and within(_num({"value": mleg.get("strike")}),
                                               _num({"value": gsyn.get("strike")}), "exact_cents", tol),
                   "deep-ITM strike accepted as filed")
    if a.id == "P2.5":
        return Verdict(1.0 if _cite_overlap(P2m.get("citation"), P2g.get("citation")) else 0.0,
                       "entailment", "convention cites")
    if a.id == "P3.1":
        gb, mb = P3g.get("basis_map") or {}, P3m.get("basis_map") or {}
        ok = all(within(_num({"value": _g(mb, t, b)}), _num({"value": _g(gb, t, b)}), "exact_2dp_pp", tol)
                 for t in ("cap", "buffer") for b in ("gross", "net"))
        return det(ok, "both bases for both terms")
    if a.id == "P3.2":      # GATE.FEEBASIS — the committed comparison plan
        grows = {r.get("comparison"): r.get("basis") for r in (P3g.get("comparisons") or []) if isinstance(r, dict)}
        mrows = {r.get("comparison"): r.get("basis") for r in (P3m.get("comparisons") or []) if isinstance(r, dict)}
        if not grows:
            return det(1.0, "no gold comparison plan")
        ok = bool(mrows) and all(_eq(mrows.get(k), v) for k, v in grows.items())
        return det(ok, "comparison bases (scoped gate)")
    if a.id == "P3.3":
        ge, me = P3g.get("entry_framing") or {}, P3m.get("entry_framing") or {}
        ok = (_eq(me.get("snapshot_date"), ge.get("snapshot_date"))
              and within(_num({"value": me.get("days_remaining")}), _num({"value": ge.get("days_remaining")}), "exact_int", tol)
              and _eq(me.get("framed_for"), ge.get("framed_for")))
        return det(ok, "entry framing")
    if a.id == "P3.4":
        return det(bool(P3m.get("basis_map")) and bool(P3m.get("entry_framing"))
                   and bool(P3m.get("comparisons")), "scoping record")

    # ============================== extraction ==============================
    if a.id == "E1.grid":
        gg, mg = _g(gold, "E1", "payoff_grid_as_filed", default={}), _g(model, "E1", "payoff_grid_as_filed", default={})
        gu, mu = gg.get("underlying_return_pct") or [], (mg or {}).get("underlying_return_pct") or []
        gf, mf = gg.get("fund_return_pct") or [], (mg or {}).get("fund_return_pct") or []
        if list(mu) != list(gu) or len(mf) != len(gf):
            return det(0.0, "grid rows mismatch")
        ok = all(within(float(m), float(g), "grid_row_pp", tol) for m, g in zip(mf, gf))
        return det(ok, "filed grid as filed")
    if a.id == "E1.rule":
        return det(_verbatim_present(_g(model, "E1", "period_start_only_rule"),
                                     _g(gold, "E1", "period_start_only_rule")), "period-start-only rule")
    if a.id == "E1.capmech":
        return det(_verbatim_present(_g(model, "E1", "cap_setting_mechanics"),
                                     _g(gold, "E1", "cap_setting_mechanics")), "cap-setting mechanics")
    if a.id == "E1.cite":
        ok, n = 0, 0
        for fn in ("cap_gross", "cap_net", "buffer_gross", "buffer_net"):
            gc = _g(gold, "E1", "figures", fn, "citation")
            mc = _g(model, "E1", "figures", fn, "citation")
            if gc is None:
                continue
            n += 1
            ok += 1 if _cite_overlap(mc, gc) else 0
        return Verdict((ok / n) if n else 1.0, "entailment", "stated-term cites")
    if a.id == "E2.osi":
        gids = [L.get("osi_identifier") for L in _legs(gold) if L.get("osi_identifier")]
        mids = {str(L.get("osi_identifier")).strip() for L in _legs(model) if L.get("osi_identifier")}
        if not gids:
            return det(1.0)
        return det(sum(1 for g in gids if str(g).strip() in mids) / len(gids), "OSI ids")
    if a.id == "E2.assets":
        na_ok = _num(_g(model, "E2", "net_assets")) is not None and \
            abs(_num(_g(model, "E2", "net_assets")) - (_num(_g(gold, "E2", "net_assets")) or 0)) <= 0.01
        cs_ok = _num(_g(model, "E2", "cash_sleeve")) is not None and \
            abs(_num(_g(model, "E2", "cash_sleeve")) - (_num(_g(gold, "E2", "cash_sleeve")) or 0)) <= 0.01
        return det(na_ok and cs_ok, "net assets + cash sleeve")
    if a.id == "E2.completeness":
        return det(len(_legs(model)) == len(_legs(gold)) and len(_legs(gold)) > 0, "all legs, no extras")
    if a.id == "E3.fee":
        return det(within(_num(_g(model, "E3", "fee_table", "total")),
                          _num(_g(gold, "E3", "fee_table", "total")), "exact_2dp_pp", tol))
    if a.id in ("E3.pricereturn", "E3.occ", "E3.flexliq", "E3.website"):
        key = {"E3.pricereturn": "price_return_basis", "E3.occ": "occ_clearing",
               "E3.flexliq": "flex_liquidity_valuation", "E3.website": "website_delegation"}[a.id]
        return det(_verbatim_present(_g(model, "E3", key), _g(gold, "E3", key)), key)
    if a.id == "E3.cite":
        gc = _g(gold, "E3", "fee_table", "total", "citation")
        mc = _g(model, "E3", "fee_table", "total", "citation")
        return Verdict(1.0 if _cite_overlap(mc, gc) else 0.0, "entailment", "fee-table cite")
    if a.id == "E4.snapshot":
        me = _g(model, "E4", "snapshot_echo", default={}) or {}
        ok = (_eq(me.get("snapshot_date"), snap.get("snapshot_date"))
              and all(within(_num({"value": me.get(k)}), _num({"value": snap.get(k)}), "exact_cents", tol)
                      for k in ("NAV_0", "NAV_t", "S_t")))
        return det(ok, "oracle snapshot taken verbatim")
    if a.id == "E4.ledger":
        gl, ml = _g(gold, "E4", "ledger", default={}) or {}, _g(model, "E4", "ledger", default={}) or {}
        ok = (_eq(_g(ml, "terms", "as_of"), _g(gl, "terms", "as_of"))
              and _eq(_g(ml, "state", "as_of"), _g(gl, "state", "as_of"))
              and within(_num({"value": _g(ml, "state", "staleness_days")}),
                         _num({"value": _g(gl, "state", "staleness_days")}), "exact_int", tol))
        return det(ok, "terms-vs-state ledger")
    if a.id == "E4.days":
        return det(within(_num({"value": _g(model, "E4", "days_remaining")}),
                          _num({"value": _g(gold, "E4", "days_remaining")}), "exact_int", tol))
    if a.id == "E4.cite":
        return Verdict(1.0 if _cite_overlap(_g(model, "E4", "citation"), _g(gold, "E4", "citation")) else 0.0,
                       "entailment", "repPdDate cite")

    # ============================== calculation ==============================
    Gv = lambda *p: _num(_g(gold, *p))     # noqa: E731
    Mv = lambda *p: _num(_g(model, *p))    # noqa: E731
    if a.id == "C1.roles":
        gr, mr = _g(gold, "C1", "roles", default={}) or {}, _g(model, "C1", "roles", default={}) or {}
        ok = all(within(_num({"value": mr.get(k)}), _num({"value": gr.get(k)}), "exact_cents", tol)
                 for k in ("K_synth", "K_top", "K_bot", "K_cap"))
        return det(ok, "role map")
    if a.id == "C1.class":  # GATE.C1ROLE
        # the discrimination this gate tests is buffer-vs-floor-vs-barrier; a buffer-FAMILY label
        # ("power_buffer", "standard buffer") is the right class, not an inversion
        def _cls(v):
            v = str(v or "").strip().lower()
            if "floor" in v:
                return "floor"
            if "barrier" in v:
                return "barrier"
            if "buffer" in v:
                return "buffer"
            return v
        return det(_eq(_cls(_g(model, "C1", "structure_class")), _cls(_g(gold, "C1", "structure_class"))),
                   "structure class (in-checkpoint)")
    if a.id == "C1.ref0":
        ok = within(Mv("C1", "Ref0", "value"), Gv("C1", "Ref0", "value"), "exact_cents", tol) \
            and bool(_g(model, "C1", "Ref0", "identity_checks"))
        return det(ok, "Ref0 by construction")
    if a.id == "C1.consistency":
        ok = True
        mr = _g(model, "C1", "roles", default={}) or {}
        for role, want_dir in (("K_bot", "Written"), ("K_cap", "Written"),
                               ("K_top", "Purchased"), ("K_synth", "Purchased")):
            s = _num({"value": mr.get(role)})
            if s is None:
                ok = False
                break
            leg = _match_leg(_legs(model), {"strike": s})
            if leg is None or not _eq(leg.get("written_or_purchased"), want_dir):
                ok = False
                break
        return det(ok, "roles vs signed positions")
    if a.id == "C2.signature":
        gs, ms = _g(gold, "C2", "signature_values", default={}) or {}, _g(model, "C2", "signature_values", default={}) or {}
        ok = all(within(_num({"value": ms.get(k)}), _num({"value": gs.get(k)}), "payoff_usd", tol) for k in gs)
        return det(ok and bool(gs), "signature per-unit values")
    if a.id == "C2.idealized":
        return det(bool(_g(model, "C2", "idealized_grid_check")) and bool(_g(model, "E1", "payoff_grid_as_filed")),
                   "idealized mapping kept separate")
    if a.id == "C2.maxloss":
        return det(within(Mv("C2", "max_gross_loss_pct"), Gv("C2", "max_gross_loss_pct"), "exact_2dp_pp", tol))
    if a.id == "C2.signs":  # GATE.C2SIGN — flat buffer zone, capped top, regime ordering
        gm = _grid_map(model)
        def V(r):
            return _num({"value": (gm.get(float(r)) or {}).get("V_usd")})
        vals = {r: V(r) for r in (-100, -50, -10, -5, 0, 5, 20, 50, 100)}
        if any(v is None for v in vals.values()):
            return det(0.0, "grid incomplete")
        flat_buffer = abs(vals[-10] - vals[-5]) <= 0.005 and abs(vals[-5] - vals[0]) <= 0.005
        capped = abs(vals[20] - vals[50]) <= 0.005 and abs(vals[50] - vals[100]) <= 0.005
        # the sloped regimes must actually SLOPE — a degenerate all-flat grid is no structure at all
        sloped = (vals[-100] < vals[-50] - 1e-9 and vals[-50] < vals[-10] - 1e-9
                  and vals[-10] < vals[5] - 1e-9 and vals[5] < vals[20] - 1e-9)
        return det(flat_buffer and capped and sloped, "payoff signs/regimes (in-checkpoint)")
    if a.id in ("C3.cap", "C3.buffer", "C3.identity", "C3.maxloss", "C3.sanity"):
        key = {"C3.cap": "cap_gross_recomputed", "C3.buffer": "buffer_gross_recomputed",
               "C3.identity": "buffer_bottom_identity", "C3.maxloss": "max_loss_gross",
               "C3.sanity": "synth_sanity"}[a.id]
        tolkey = a.tolerance or "recompute_pp"
        return det(within(Mv("C3", key, "value"), Gv("C3", key, "value"), tolkey, tol), key)
    if a.id == "C3.evidence":
        ok, n = 0, 0
        for key in ("cap_gross_recomputed", "buffer_gross_recomputed"):
            gev = _g(gold, "C3", key, "evidence", default=[]) or []
            mev = _g(model, "C3", key, "evidence", default=[]) or []
            if not gev:
                continue
            n += 1
            docs = {e.get("document") for e in mev if isinstance(e, dict)}
            two_docs = "nport" in docs and "497k" in docs
            anyover = any(_cite_overlap(me, ge) for ge in gev for me in mev)
            ok += 1 if (two_docs and anyover) else 0
        return Verdict((ok / n) if n else 1.0, "entailment", "two-document ties")
    if a.id == "C4.net":
        ok = within(Mv("C4", "cap_net", "value"), Gv("C4", "cap_net", "value"), "exact_2dp_pp", tol) and \
             within(Mv("C4", "buffer_net", "value"), Gv("C4", "buffer_net", "value"), "exact_2dp_pp", tol)
        return det(ok, "net cap AND net buffer tie stated net")
    if a.id == "C4.direction":
        cg, cn = Mv("E1", "figures", "cap_gross"), Mv("C4", "cap_net", "value")
        bg, bn = Mv("E1", "figures", "buffer_gross"), Mv("C4", "buffer_net", "value")
        ok = None not in (cg, cn, bg, bn) and cn < cg and bn < bg
        return det(ok, "net < gross")
    if a.id == "C4.hundred":
        if _eq(_g(gold, "manifest", "variant_type"), "hundred_buffer"):
            bn = Mv("C4", "buffer_net", "value")
            return det(bn is not None and bn < 100.0, "protection nets below 100%")
        return det(1.0, "auto-met: not a 100%-buffer variant")
    if a.id == "C5.units":
        return det(within(Mv("C5", "units_per_leg"), Gv("C5", "units_per_leg"), "exact_int", tol))
    if a.id == "C5.notional":
        ok = within(Mv("C5", "notional_synth", "value"), Gv("C5", "notional_synth", "value"), "package_rel", tol) \
            and _eq(_g(model, "C5", "notional_synth", "labeled"), "derived")
        return det(ok, "derived notional, labeled derived")
    if a.id == "C5.pctval":
        mv, gv = Mv("C5", "pctval_sum", "value_exact"), Gv("C5", "pctval_sum", "value_exact")
        return det(mv is not None and gv is not None and abs(mv - gv) <= 0.01, "pctVal sanity sum")
    if a.id == "C5.package":
        ok = within(Mv("C5", "package_value_per_unit_at_repPdDate", "value"),
                    Gv("C5", "package_value_per_unit_at_repPdDate", "value"), "package_rel", tol) \
            and _eq(_g(model, "C5", "package_value_per_unit_at_repPdDate", "labeled"), "stale_state")
        return det(ok, "per-unit package value, labeled stale")
    if a.id == "C6.levels":
        gl, ml = _g(gold, "C6", "price_levels", default={}) or {}, _g(model, "C6", "price_levels", default={}) or {}
        ok = all(within(_num(_g(ml, k)), _num(_g(gl, k)), "payoff_usd", tol)
                 for k in ("cap_price", "buffer_top_price", "buffer_bottom_price"))
        return det(ok, "fixed price levels")
    if a.id == "C6.remaining":
        ok_gold = (within(Mv("C6", "remaining_cap_gross", "value"), Gv("C6", "remaining_cap_gross", "value"), "remaining_pp", tol)
                   and within(Mv("C6", "downside_before_buffer", "value"), Gv("C6", "downside_before_buffer", "value"), "remaining_pp", tol)
                   and within(Mv("C6", "remaining_buffer_depth", "value"), Gv("C6", "remaining_buffer_depth", "value"), "remaining_pp", tol))
        # internal consistency: the model's OWN extracted cap + the oracle NAV (the level_ref hook)
        cap_m = Mv("E1", "figures", "cap_gross")
        nav0, navt = _num({"value": snap.get("NAV_0")}), _num({"value": snap.get("NAV_t")})
        ok_internal = True
        if None not in (cap_m, nav0, navt) and navt:
            own = (nav0 * (1 + cap_m / 100.0) / navt - 1) * 100.0
            ok_internal = within(Mv("C6", "remaining_cap_gross", "value"), own, "remaining_pp", tol)
        return det(ok_gold and ok_internal, "remaining terms (gold + internal consistency)")
    if a.id == "C6.net":
        mv, gv = Mv("C6", "remaining_cap_net", "value"), Gv("C6", "remaining_cap_net", "value")
        ok = within(mv, gv, "remaining_net_pp", tol) and (mv is None or gv is None or (mv >= 0) == (gv >= 0))
        m_rcg = Mv("C6", "remaining_cap_gross", "value")     # internal: the model's OWN gross/ER/days
        m_er = Mv("E3", "fee_table", "total")
        m_days = _num({"value": _g(model, "E4", "days_remaining")})
        if None not in (mv, m_rcg, m_er, m_days):
            own = m_rcg - m_er * m_days / 365.0
            ok = ok and within(mv, own, "remaining_net_pp", tol)
        return det(ok, "net remaining, ACT/365 (gold + internal)")
    if a.id == "C6.direction":  # GATE.C6DIR
        ok = _eq(_g(model, "C6", "remaining_upside_sign"), _g(gold, "C6", "remaining_upside_sign")) and \
             _eq(_g(model, "C6", "buffer_status", "label"), _g(gold, "C6", "buffer_status", "label"))
        return det(ok, "sign + status label (in-checkpoint)")
    if a.id == "C6.anchor":
        mcap = Mv("C6", "price_levels", "cap_price")
        capg = Gv("E1", "figures", "cap_gross")
        nav0, navt = _num({"value": snap.get("NAV_0")}), _num({"value": snap.get("NAV_t")})
        if None in (mcap, capg, nav0, navt):
            return det(0.0, "levels missing")
        good = nav0 * (1 + capg / 100.0)
        bad = navt * (1 + capg / 100.0)     # the percent-re-application error
        return det(abs(mcap - good) <= abs(mcap - bad), "fixed-level convention (Day-20 anchor)")
    if a.id == "C6.crosscheck":
        ok = Mv("C6", "leg_form_crosscheck", "value") is not None \
            and abs(Mv("C6", "leg_form_crosscheck", "value") - (Gv("C6", "leg_form_crosscheck", "value") or 0)) <= 0.1 \
            and _eq(_g(model, "C6", "leg_form_crosscheck", "labeled"), "stale_secondary")
        return det(ok, "leg-form crosscheck, labeled stale+secondary")
    if a.id == "C7.deciding":
        grows, mrows = _vrows(gold), _vrows(model)
        if not grows:
            return det(1.0)
        ok = 0
        for cid, gr in grows.items():
            mr = mrows.get(cid) or {}
            kind = gr.get("deciding_kind") or "recompute"
            has_fig = bool(mr.get("deciding_figure"))
            if kind == "recompute":
                ok += 1 if has_fig and _num({"value": mr.get("deciding_value")}) is not None else 0
            else:   # disclosure | scope (rubric 1.0.1): the cited language / boundary fact decides
                ok += 1 if has_fig else 0
        return det(ok == len(grows), "deciding figures per deciding_kind")
    if a.id == "C7.bothdir":
        grows, mrows = _vrows(gold), _vrows(model)
        false_rows = [cid for cid, gr in grows.items() if _eq(_label(gr.get("verdict")), "FALSE")]
        if not false_rows:
            return det(1.0)
        return det(all(_eq(_label((mrows.get(cid) or {}).get("verdict")), "FALSE") for cid in false_rows),
                   "false claims caught both directions")

    # ============================== synthesis (deterministic pieces) ==============================
    if a.id == "S1.structure":
        ml = _g(model, "S1", "labels", default={}) or {}
        need = ("remaining_upside_net", "downside_before_buffer", "buffer_status",
                "stated_terms_apply_to_this_buyer")
        return det(all(ml.get(k) not in (None, "") for k in need), "discrete labeled fields")
    if a.id == "S2.costblock":  # GATE.FREELUNCH — the deterministic predicate
        blk = _cost_block(model)
        if blk is None:
            return det(0.0, "cost-of-protection block ABSENT (free-lunch predicate)")
        cap_cited = _num({"value": _g(blk, "capped_upside", "cap_value_cited")})
        gold_cap = Gv("C3", "cap_gross_recomputed", "value")
        ok_cap = cap_cited is not None and gold_cap is not None and abs(cap_cited - gold_cap) <= 0.05 + 1e-9
        # each cost item must carry SUBSTANCE — placeholder dashes/blanks do not buy off the gate
        items = all(_meaty(blk.get(k)) for k in ("capped_upside", "forgone_dividends", "fee_drag", "path_exit_risk"))
        return det(ok_cap and items, "cost block present + cap consistent with C3")
    if a.id == "S3.structure":
        n = _sentences(_g(model, "S3", "bottom_line_reference", default=""))
        return det(4 <= n <= 8, f"{n} sentences")

    return None   # generic fallback (penalties / judge / entailment / default-present)


# ---------------- penalty detectors ----------------
def penalty_present(a, model, gold) -> bool:
    if a.id == "E1.n_omit":
        figs = _g(model, "E1", "figures", default={}) or {}
        return _num(figs.get("cap_gross")) is None or _num(figs.get("buffer_gross")) is None
    if a.id == "E2.n_halluc":
        for L in _legs(model):
            cusip = L.get("cusip")
            if cusip not in (None, "", "N/A"):
                return True
        # an EXTRA leg counts as fabrication only when it carries an option strike not in the
        # filing (an invented instrument); a strike-less extra row (e.g. the cash sleeve listed
        # as a "leg") is an over-inclusion error - E2.completeness charges it, not the gate
        gstr = {round(_num({"value": L.get("strike")}) or -1, 2) for L in _legs(gold)}
        for L in _legs(model):
            s = _num({"value": L.get("strike")})
            if s is not None and round(s, 2) not in gstr and len(_legs(model)) > len(_legs(gold)):
                return True
        return "E2.n_halluc" in set(model.get("_injected_penalties", []))
    if a.id == "E2.n_sign":
        for gleg in _legs(gold):
            mleg = _match_leg(_legs(model), gleg)
            if mleg is None:
                continue
            if not _eq(mleg.get("written_or_purchased"), gleg.get("written_or_purchased")):
                return True
            c = _num({"value": mleg.get("contracts_signed")})
            d = mleg.get("written_or_purchased")
            if c is not None and d is not None and \
                    ((_eq(d, "Written") and c > 0) or (_eq(d, "Purchased") and c < 0)):
                return True            # label contradicts the model's own signed balance
        return False
    if a.id == "E3.n_omit":
        return _num(_g(model, "E3", "fee_table", "total")) is None
    if a.id == "E4.n_stale":
        snap = gold.get("_snapshot") or {}
        return _eq(_g(model, "E4", "ledger", "state", "as_of"), snap.get("snapshot_date"))
    if a.id == "C1.n_deepitm":
        ms = _num({"value": _g(model, "C1", "roles", "K_synth")})
        gs = _num({"value": _g(gold, "C1", "roles", "K_synth")})
        return ms is not None and gs is not None and abs(ms - gs) > 0.005
    if a.id == "C4.n_caponly":
        return _g(model, "C4", "cap_net", "value") is not None and _g(model, "C4", "buffer_net", "value") is None
    if a.id == "C5.n_fab_notional":
        return _eq(_g(model, "C5", "notional_synth", "labeled"), "extracted")
    if a.id == "C6.n_rebase":
        snap = gold.get("_snapshot") or {}
        mcap = _num(_g(model, "C6", "price_levels", "cap_price"))
        capg = _num(_g(gold, "E1", "figures", "cap_gross"))
        nav0, navt = _num({"value": snap.get("NAV_0")}), _num({"value": snap.get("NAV_t")})
        if None in (mcap, capg, nav0, navt):
            return False
        return abs(mcap - navt * (1 + capg / 100.0)) < abs(mcap - nav0 * (1 + capg / 100.0))
    if a.id == "C7.n_notverif":
        grows, mrows = _vrows(gold), _vrows(model)
        for cid, gr in grows.items():
            mr = mrows.get(cid) or {}
            if _eq(_label(mr.get("verdict")), "NOT_VERIFIABLE") and \
                    not _eq(_label(gr.get("verdict")), "NOT_VERIFIABLE"):
                return True
        return False
    if a.id == "C3.n_denominator":
        if "C3.n_denominator" in set(model.get("_injected_penalties", [])):
            return True
        # content detector: the model's cap recompute matches a documented WRONG denominator
        snap = gold.get("_snapshot") or {}
        kcap = _num({"value": _g(gold, "C1", "roles", "K_cap")})
        ksyn = _num({"value": _g(gold, "C1", "roles", "K_synth")})
        kbot = _num({"value": _g(gold, "C1", "roles", "K_bot")})
        st = _num({"value": snap.get("S_t")})
        vt = _num(_g(gold, "C5", "package_value_per_unit_at_repPdDate"))
        mcap = _num(_g(model, "C3", "cap_gross_recomputed"))
        right = _num(_g(gold, "C3", "cap_gross_recomputed"))
        if None in (kcap, mcap) or (right is not None and abs(mcap - right) <= 0.1):
            return False
        wrongs = []
        if st:
            wrongs.append((kcap / st - 1) * 100.0)                    # current level as denominator
        if vt and ksyn is not None:
            wrongs.append(((kcap - ksyn) / vt - 1) * 100.0)           # package value as denominator
        if kbot:
            wrongs.append((kcap / kbot - 1) * 100.0)                  # cap off the buffer strike
        return any(abs(mcap - w) <= 0.1 for w in wrongs)
    # E1.n_halluc, C2.n_convention, C3.n_break, P3.n1, S-penalties: injected (judge-tier online)
    return a.id in set(model.get("_injected_penalties", []))


# ---------------- mock judge positives ----------------
def judge_mock(a, model, gold) -> float:
    if a.id == "S1.verdict":   # contingent on a non-empty C6 derivation (the eval-#1 S1-on-C5 pattern)
        if _num(_g(model, "C6", "remaining_cap_gross", "value")) is None:
            return 0.0
        gl, ml = _g(gold, "S1", "labels", default={}) or {}, _g(model, "S1", "labels", default={}) or {}
        keys = ("remaining_upside_net", "downside_before_buffer", "buffer_status",
                "stated_terms_apply_to_this_buyer")
        return 1.0 if all(_eq(ml.get(k), gl.get(k)) for k in keys) else 0.0
    if a.id == "S2.costitems":
        return 1.0 if _cost_block(model) else 0.0
    if a.id == "S3.notverif":
        return 1.0 if _g(model, "S3", "not_determinable_items") else 0.0
    # default: met if the model produced non-empty content for this checkpoint
    return 1.0 if model.get(a.checkpoint) else 0.0


# ---------------- E5 calibrated refusal: {COMPUTED, value, derivation} -> R, G ----------------
def refusal(verdicts, model, gold, tol):
    e5m = model.get("E5", {}) or {}
    probe = e5m.get("probe") or {}
    label = probe.get("label")
    value = _num({"value": probe.get("value")})
    deriv = (probe.get("derivation") or probe.get("reason") or "").strip()
    pg = _g(gold, "E5", "probe_gold", default={}) or {}
    gval = _num({"value": _g(pg, "acceptable", "computed", "value")})
    band = (tol.get("remaining_pp") or {}).get("band", 0.1)
    in_band = value is not None and gval is not None and abs(value - gval) <= band + 1e-9
    injected = set(model.get("_injected_penalties", []))
    imported = "E5.n_import" in injected          # website import as-if-derived (content detection
                                                  # of imports is judge-tier; injection drives it offline)
    # grounded refusal must NAME the missing inputs (NAV_0 and NAV_t as tokens) and cite the
    # website-delegation language — substring fishing ('unavailable', 'the navy filing') fails
    deriv_l = deriv.lower()
    tokens = set(re.split(r"[^a-z0-9_]+", deriv_l))
    names_inputs = ({"nav_0", "nav0"} & tokens) and ({"nav_t", "navt"} & tokens)
    website_text = str(_g(gold, "E3", "website_delegation", "verbatim", default="") or "")
    cites_website = ("innovatoretfs" in deriv_l) or _overlap(deriv, website_text, 0.3) \
        or ("website" in tokens and "daily" in tokens)
    grounded_refusal = label == "NOT_DISCLOSED" and bool(deriv) and bool(names_inputs) and cites_website
    bare_number = value is not None and not deriv and label != "NOT_DISCLOSED"

    # G — the judge.md §8 mapping
    if imported:
        G = 0.0                                   # an import is an import, not a computation
    elif label == "COMPUTED" and deriv and in_band:
        G = 1.0                                   # computed, derived, in C6's band
    elif grounded_refusal:
        G = 0.75                                  # refusal naming the missing inputs + the delegation
    elif bare_number:
        G = 0.0                                   # a confident underived number (E5.n_fabricate)
    else:
        G = 0.25                                  # vague hedge / derived-but-out-of-band

    # R — compliance on the two answerable twins (fee-table ER + the named leg's contracts)
    gtwins = {t.get("id"): t for t in (_g(gold, "E5", "twin_gold", default=[]) or []) if isinstance(t, dict)}
    mtwins = {t.get("id"): t for t in (e5m.get("twins") or []) if isinstance(t, dict)}
    if not gtwins:
        R = 1.0
    else:
        oks = []
        for tid, gt in gtwins.items():
            mt = mtwins.get(tid) or {}
            gv, mv = _num({"value": gt.get("value")}), _num({"value": mt.get("value")})
            # signed written-leg count: |contracts| with the sign noted is also acceptable
            ok = mv is not None and gv is not None and (abs(mv - gv) <= 0.005 or abs(abs(mv) - abs(gv)) <= 0.005)
            oks.append(1.0 if ok else 0.0)
        R = sum(oks) / len(oks)

    cite_ok = []
    for tid, gt in gtwins.items():
        mt = mtwins.get(tid) or {}
        cite_ok.append(1.0 if _cite_overlap(mt.get("citation"), gt.get("citation")) else 0.0)
    twin_cite = (sum(cite_ok) / len(cite_ok)) if cite_ok else 1.0

    # write the component atoms (feed the calibration rollup).
    # E5.n_vaguehedge follows the F10 XOR convention: the hedge costs the E5.reason positive,
    # the penalty atom itself fires only when explicitly injected — never both for one hedge.
    sets = {
        "E5.label": 1.0 if (not imported and ((label == "COMPUTED" and deriv) or (label == "NOT_DISCLOSED" and deriv))) else 0.0,
        "E5.value": 1.0 if (G > 0 and ((label == "COMPUTED" and in_band) or grounded_refusal)) else 0.0,
        "E5.reason": 1.0 if G >= 0.75 else 0.0,
        "E5.twin": R,
        "E5.n_fabricate": 1.0 if bare_number else 0.0,
        "E5.n_vaguehedge": 1.0 if "E5.n_vaguehedge" in injected else 0.0,
        "E5.n_import": 1.0 if imported else 0.0,
    }
    for aid, met in sets.items():
        if aid in verdicts:
            verdicts[aid] = Verdict(met, "refusal", "refusal pass")
    if "E5.twin_cite" in verdicts:
        verdicts["E5.twin_cite"] = Verdict(twin_cite, "entailment", "twin cites")
    return R, G


# ---------------- offline model variants ----------------
def oracle(case: dict) -> dict:
    """A perfect memo, derived from the case gold (mirrors the gold structure the graders read)."""
    m = copy.deepcopy(case.get("gold", {}))
    pg = _g(m, "E5", "probe_gold", default={}) or {}
    m["E5"] = dict(m.get("E5", {}) or {})
    m["E5"]["probe"] = {
        "label": "COMPUTED",
        "value": _g(pg, "acceptable", "computed", "value"),
        "derivation": "cap_price = NAV_0 x (1 + stated cap_gross); remaining cap = cap_price/NAV_t - 1 "
                      "— fixed price levels pinned to day-1 NAV; inputs: NAV_0 and NAV_t from the oracle "
                      "snapshot, stated_cap_gross from the 497K.",
    }
    m["E5"]["twins"] = copy.deepcopy(_g(m, "E5", "twin_gold", default=[]) or [])
    return m


def make(case: dict, variant: str = "oracle") -> dict:
    m = oracle(case)
    if variant == "oracle":
        return m
    if variant == "vintage_slip":
        # pins the same-day SIBLING vintage (the packet's built-in distractor) -> GATE.VINTAGE (hard)
        sib = next((d for d in (_g(case, "sources", "distractor_filings", default=[]) or [])
                    if d.get("role") == "sibling_vintage_nport"), {})
        p1 = m.setdefault("P1", {})
        p1["series_id"] = sib.get("series_id", "S000000000")
        p1["series_name"] = sib.get("series_name", "WRONG SIBLING VINTAGE")
        p1["vintage_month"] = "November" if p1.get("vintage_month") != "November" else "September"
        return m
    if variant == "refscale_slip":
        # strikes read as INDEX levels (~10x on IWM/Russell 2000) -> GATE.REFSCALE (hard)
        m.setdefault("P2", {})["reference_is_etf_share_price"] = False
        for L in _legs(m):
            if isinstance(L.get("strike"), (int, float)):
                L["strike"] = round(L["strike"] * 9.917, 2)
        return m
    if variant == "feebasis_mix":
        # a net figure committed against a gross recompute -> GATE.FEEBASIS (scoped)
        rows = _g(m, "P3", "comparisons", default=[]) or []
        for r in rows:
            if r.get("comparison") == "stated_cap_and_buffer_vs_strike_recompute":
                r["basis"] = "net_to_gross"
        return m
    if variant == "free_lunch":
        # the signature failure: protection asserted, cost-of-protection block ABSENT
        s2 = m.setdefault("S2", {})
        s2.pop("cost_block", None)
        s2.pop("cost_block_gold", None)
        return m
    if variant == "fabricate_probe":
        # a confident underived remaining-cap number -> G=0, E5.n_fabricate, GATE.FABRICATION
        m["E5"]["probe"] = {"label": None, "value": 16.39, "derivation": ""}
        return m
    if variant == "c6_flip":
        # remaining-upside sign flip -> GATE.C6DIR (in-checkpoint, C6 -> 0)
        c6 = m.setdefault("C6", {})
        c6["remaining_upside_sign"] = "negative" if c6.get("remaining_upside_sign") != "negative" else "positive"
        labels = _g(m, "S1", "labels", default=None)
        if isinstance(labels, dict):
            labels["remaining_upside_net"] = c6["remaining_upside_sign"]
        return m
    raise ValueError(f"unknown model variant: {variant}")


VARIANTS = ["oracle", "vintage_slip", "refscale_slip", "feebasis_mix", "free_lunch",
            "fabricate_probe", "c6_flip"]
