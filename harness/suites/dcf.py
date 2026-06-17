"""
harness/suites/dcf.py — the EVAL #3 (discounted-cash-flow valuation) suite.

Grades a model's DCF valuation memo against the MCD-style case gold (rubric/criteria-dcf.yaml,
18 checkpoints, calculation-heavy). Everything the workflow doc declares deterministic is graded
deterministically here: the base-line + bridge extraction, the unlevered-FCFF projection, the WACC
build, discounting, the terminal value, enterprise value, the EV->equity bridge, the sensitivity
grid, and the claim verdicts. The judge tier (S1-S3) uses presence/consistency mocks offline (the
live LLM judge is the online swap, judge.md section 9).

Suite-specific machinery:
  * E5 calibrated refusal — the company WACC, undisclosed-in-the-filing-but-computable-from-the-
    components — with the {COMPUTED, value, derivation} typed answer keyed to C2's WACC band
    (judge.md section 9.1, run-mode-dependent G-mapping).
  * The TWO-HOOK GATE.BASIS: the unlevered<->WACC<->EV<->bridge consistency commitment, checked at
    P1 (the declared chain) AND C5 (the assembled EV's internal consistency).
  * GATE.SCALE (units), GATE.WACC (book-weight / pre-tax-Kd), GATE.BRIDGE (net-debt omission /
    EV-divided-by-shares), the in-checkpoint C1FCF / C4TERM / C7SIGN fails, and GATE.FALSEPRECISION
    — the deterministic predicate on S2's structured value-attribution + sensitivity block (parallel
    to eval #2's GATE.FREELUNCH): absent/empty while a point target is asserted -> S2+S3 zero,
    false_precision_fired flag.

Model-answer shape: mirrors the case gold (the oracle is a deepcopy), with E5 answered as
  model["E5"] = {"probe": {label, value, derivation}, "twins": [{id, value, citation}, ...]}.
"""
from __future__ import annotations
import copy
import re
from ..graders import Verdict, _num, _eq, _cite_overlap
from ..tolerances import within

REFUSAL_CP = "E5"
LLM_JUDGE_CPS = {"S2", "S3"}   # S1 stays on the mock: its C6-contingency must always run
MEMO_KIND = "an equity-research DCF valuation memo"

_VERDICT_ENUM = {"ACCURATE", "ACCURATE_ON_BASE_CASE_ONLY", "WRONG_BASIS", "FALSE", "NOT_VERIFIABLE"}


# ---------------- small access helpers ----------------
def _g(d, *path, default=None):
    cur = d
    for p in path:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(p)
    return cur if cur is not None else default


def _figs(container, cp):
    return _g(container, cp, "figures", default={}) or {}


def _years(container, cp):
    return _g(container, cp, "per_year", default=[]) or []


def _grid(container):
    return _g(container, "C7", "grid", default=[]) or []


def _vrows(container):
    rows = _g(container, "C7", "verdicts", default=[]) or []
    return {r.get("id"): r for r in rows if isinstance(r, dict)}


def _sentences(text: str) -> int:
    parts = [p for p in re.split(r"(?<=[.!?])\s+(?=[A-Z])", (text or "").strip()) if p.strip()]
    return len(parts)


def _sens_block(model):
    s2 = model.get("S2", {}) or {}
    blk = s2.get("sensitivity_block") or s2.get("sensitivity_block_gold")
    return blk if isinstance(blk, dict) and blk else None


def _range_ok(node):
    """a genuine sensitivity RANGE: a dict (or list) of >=2 DISTINCT non-zero numeric values
    (a stub of equal/placeholder values is not a range)."""
    vals = []
    if isinstance(node, dict):
        vals = [v for v in node.values() if isinstance(v, (int, float))]
    elif isinstance(node, (list, tuple)):
        vals = [v for v in node if isinstance(v, (int, float))]
    vals = [v for v in vals if v != 0]
    return len(vals) >= 2 and (max(vals) - min(vals)) > 1e-9


def _idx(fn):
    """'year_3' / 'cell_7' / 'claim_2' -> 3 / 7 / 2."""
    try:
        return int(str(fn).split("_")[1])
    except (IndexError, ValueError):
        return -1


# ---------------- the handler chain (None => generic fallback in the engine) ----------------
def handle(a, ctx):
    model, gold, tol = ctx.model, ctx.gold, ctx.tol
    sid = a.source_id

    def det(met, note=""):
        return Verdict(float(met), "deterministic", note)

    Gv = lambda *p: _num(_g(gold, *p))     # noqa: E731
    Mv = lambda *p: _num(_g(model, *p))    # noqa: E731

    # ============================== per-row / per-figure expansions ==============================
    if sid == "E1.value":
        fn = a.figure_name
        g = _figs(gold, "E1").get(fn) or {}
        m = _figs(model, "E1").get(fn) or {}
        return det(within(_num(m), _num(g), a.tolerance, tol), f"E1 {fn}")
    if sid == "E2.value":
        fn = a.figure_name
        g = _figs(gold, "E2").get(fn) or {}
        m = _figs(model, "E2").get(fn) or {}
        return det(within(_num(m), _num(g), a.tolerance, tol), f"E2 {fn}")
    if sid == "C1.fcff":
        i = _idx(a.figure_name)
        gy, my = _years(gold, "C1"), _years(model, "C1")
        if i < 0 or i >= len(gy):
            return det(0.0, "gold year missing")
        mr = my[i] if i < len(my) else {}
        return det(within(_num({"value": mr.get("fcff")}), _num({"value": gy[i].get("fcff")}), a.tolerance, tol),
                   f"FCFF year {i+1}")
    if sid == "C3.pv":
        i = _idx(a.figure_name)
        gy, my = _years(gold, "C3"), _years(model, "C3")
        if i < 0 or i >= len(gy):
            return det(0.0, "gold PV year missing")
        mr = my[i] if i < len(my) else {}
        return det(within(_num({"value": mr.get("pv_fcff")}), _num({"value": gy[i].get("pv_fcff")}), a.tolerance, tol),
                   f"PV(FCFF) year {i+1}")
    if sid == "C7.grid":
        i = _idx(a.figure_name)
        gg, mg = _grid(gold), _grid(model)
        if i < 0 or i >= len(gg):
            return det(0.0, "gold grid cell missing")
        mr = mg[i] if i < len(mg) else {}
        return det(within(_num({"value": mr.get("per_share")}), _num({"value": gg[i].get("per_share")}),
                          a.tolerance, tol), f"grid cell {i}")
    if sid == "C7.verdicts":
        i = _idx(a.figure_name)
        gg = _g(gold, "C7", "verdicts", default=[]) or []
        if i < 0 or i >= len(gg):
            return det(0.0, "gold claim missing")
        gr = gg[i]
        mr = _vrows(model).get(gr.get("id")) or {}
        return det(_eq(mr.get("verdict"), gr.get("verdict")), f"claim {gr.get('id')}")

    # ============================== entailment cites ==============================
    if a.id == "P1.cite":
        return Verdict(1.0 if _cite_overlap(_g(model, "P1", "citation"), _g(gold, "P1", "citation")) else 0.0,
                       "entailment", "frame cite")
    if a.id == "P2.cite":
        return Verdict(1.0 if _cite_overlap(_g(model, "P2", "citation"), _g(gold, "P2", "citation")) else 0.0,
                       "entailment", "convention cite")
    if a.id == "E1.cite":
        gf, mf = _figs(gold, "E1"), _figs(model, "E1")
        ok = n = 0
        for fn, gnode in gf.items():
            gc = (gnode or {}).get("citation")
            if not gc:
                continue
            n += 1
            ok += 1 if _cite_overlap((mf.get(fn) or {}).get("citation"), gc) else 0
        return Verdict((ok / n) if n else 1.0, "entailment", "base-line cites")
    if a.id == "E2.cite":
        gf, mf = _figs(gold, "E2"), _figs(model, "E2")
        ok = n = 0
        for fn, gnode in gf.items():
            gc = (gnode or {}).get("citation")
            if not gc:
                continue
            n += 1
            ok += 1 if _cite_overlap((mf.get(fn) or {}).get("citation"), gc) else 0
        return Verdict((ok / n) if n else 1.0, "entailment", "bridge cites")
    if a.id == "E4.cite":
        return Verdict(1.0 if _cite_overlap(_g(model, "E4", "citation"), _g(gold, "E4", "citation")) else 0.0,
                       "entailment", "staleness cite")

    # ============================== planning ==============================
    P1g, P1m = gold.get("P1", {}) or {}, model.get("P1", {}) or {}
    P2g, P2m = gold.get("P2", {}) or {}, model.get("P2", {}) or {}
    P3g, P3m = gold.get("P3", {}) or {}, model.get("P3", {}) or {}
    if a.id == "P1.frame":
        ok = (_eq(P1m.get("ticker"), P1g.get("ticker")) and _eq(P1m.get("fiscal_year"), P1g.get("fiscal_year"))
              and _eq(P1m.get("currency"), P1g.get("currency")) and _eq(P1m.get("units"), P1g.get("units"))
              and _eq(P1m.get("valuation_date"), P1g.get("valuation_date")))
        return det(ok, "frame pinned")
    if a.id == "P1.basis":
        oc = str(P1m.get("output_chain") or "").lower()
        return det(_eq(P1m.get("fcf_basis"), "unlevered_FCFF") and "ev" in oc and "bridge" in oc and "equity" in oc,
                   "unlevered FCFF basis + chain")
    if a.id == "P1.consistency":   # GATE.BASIS (hook 1): the declared chain must be self-consistent
        # structured commitment (not free-text parsing where a stray token disarms the trigger):
        # unlevered FCFF MUST be paired with WACC, and the chain MUST bridge EV -> equity (not EV-as-equity)
        oc = str(P1m.get("output_chain") or "").lower()
        bad = (not _eq(P1m.get("fcf_basis"), "unlevered_FCFF")) \
            or (not _eq(P1m.get("discount_rate_for_fcff"), "WACC")) \
            or ("equity value directly" in oc) or ("ev / shares" in oc) or ("ev/shares" in oc) \
            or ("ev" not in oc) or ("bridge" not in oc and "equity" not in oc)
        return det(0.0 if bad else 1.0, "basis consistency (hard gate, P1 hook)")
    if a.id == "P1.horizon":
        return det(_eq(P1m.get("horizon_years"), P1g.get("horizon_years"))
                   and _eq(P1m.get("terminal_method"), P1g.get("terminal_method")), "horizon + method")
    if a.id == "P1.header":
        need = ("ticker", "fiscal_year", "valuation_date", "currency", "units", "fcf_basis",
                "output_chain", "horizon_years", "terminal_method")
        return det(all(P1m.get(k) not in (None, "") for k in need), "pinned header")
    if a.id == "P2.scale":         # GATE.SCALE — units lock + figure-magnitude sanity
        if not _eq(P2m.get("units"), P2g.get("units")):
            return det(0.0, "units mismatch")
        m0 = _num({"value": (_years(model, "C1")[0] if _years(model, "C1") else {}).get("fcff")})
        g0 = _num({"value": (_years(gold, "C1")[0] if _years(gold, "C1") else {}).get("fcff")})
        if m0 is not None and g0 not in (None, 0):
            if not (0.1 <= m0 / g0 <= 10.0):
                return det(0.0, "projection magnitude off by a scale factor")
        return det(1.0, "units + magnitude (hard gate)")
    if a.id == "P2.waccbasis":     # GATE.WACC — market weights + after-tax Kd + CAPM
        wb = P2m.get("wacc_basis") or {}
        ok = _eq(wb.get("weights"), "market") and _eq(wb.get("cost_of_debt"), "after_tax") \
            and "rf" in str(wb.get("capm") or "").lower()
        return det(ok, "WACC basis (scoped gate)")
    if a.id == "P2.convention":
        return det(_eq(P2m.get("discounting_convention"), P2g.get("discounting_convention")), "convention pinned")
    if a.id == "P2.nominal":
        return det(_eq(P2m.get("nominal_consistency"), P2g.get("nominal_consistency")), "nominal consistency declared")
    if a.id == "P2.lease":
        return det(_eq(P2m.get("lease_treatment"), "operating"), "lease treatment = operating")
    if a.id == "P3.terminal":
        g_frac = _num({"value": P3m.get("terminal_param_g")})
        gold_g = _num({"value": P3g.get("terminal_param_g")})
        wacc = Mv("C2", "wacc", "value")
        g_match = within(g_frac, gold_g, "exact_2dp_pp", tol)     # g matches gold (was a dead `is not None`)
        g_below = g_frac is not None and wacc is not None and (g_frac * 100.0) < wacc
        return det(_eq(P3m.get("terminal_method"), P3g.get("terminal_method")) and g_match and g_below,
                   "terminal method + g matches gold + g<WACC pre-committed")
    if a.id == "P3.normalize":
        rules = " ".join(str(x) for x in (P3m.get("consistency_rules") or [])).lower()
        return det(any(k in rules for k in ("normal", "steady-state", "steady state", "mid-cycle", "mid cycle")),
                   "terminal normalization flagged")
    if a.id == "P3.inputmap":
        im = P3m.get("input_map") or {}
        return det(bool(im.get("filed")) and bool(im.get("oracle")), "oracle/filed input map")
    if a.id == "P3.scope":
        return det(bool(P3m.get("terminal_method")) and bool(P3m.get("consistency_rules"))
                   and bool(P3m.get("input_map")), "scoping record")

    # ============================== extraction ==============================
    if a.id == "E1.ebit":
        ebit = _num(_figs(model, "E1").get("ebit"))
        g_ebit = Gv("E1", "figures", "ebit")
        ni, ebitda = 8563.0, (g_ebit + 2199.0 if g_ebit else None)   # not NI, not EBITDA (MCD anchors)
        ok = ebit is not None and within(ebit, g_ebit, "exact_round", tol) \
            and abs(ebit - ni) > 1.0 and (ebitda is None or abs(ebit - ebitda) > 1.0)
        return det(ok, "EBIT (not NI, not EBITDA)")
    if a.id == "E1.source":
        da = _num(_figs(model, "E1").get("dep_amort"))
        return det(da is not None and within(da, Gv("E1", "figures", "dep_amort"), "exact_round", tol)
                   and abs(da - 457.0) > 1.0, "D&A from cash flow (not the 457 partial)")
    if a.id == "E1.taxnote":
        return det(_num(_figs(model, "E1").get("effective_tax_rate")) is not None
                   and within(Mv("C1", "tax_rate_used"), Gv("C1", "tax_rate_used"), None, tol)
                   if Mv("C1", "tax_rate_used") is not None else False, "FCFF tax = cash_tax_rate")
    if a.id == "E2.netdebt":
        td, cash, nd = (_num(_figs(model, "E2").get(k)) for k in ("total_debt", "cash_and_equiv", "net_debt"))
        return det(None not in (td, cash, nd) and abs((td - cash) - nd) <= 0.5, "net debt = total debt - cash")
    if a.id == "E2.leases":
        le = str(_g(model, "E2", "lease_exclusion") or "").lower()
        return det("lease" in le and ("exclud" in le or "operating" in le or "not " in le),
                   "operating-lease liabilities excluded")
    if a.id == "E2.nonop":
        return det(within(_num(_figs(model, "E2").get("non_op_assets")),
                          Gv("E2", "figures", "non_op_assets"), "exact_round", tol), "non-op assets captured")
    if a.id == "E2.shares":
        return det(within(_num(_figs(model, "E2").get("diluted_shares")),
                          Gv("E2", "figures", "diluted_shares"), "exact_int", tol), "diluted shares")
    if a.id == "E2.bookequity":
        note = str(_g(model, "E2", "negative_book_equity_note") or "").lower()
        return det(any(k in note for k in ("buyback", "negative", "deficit", "data error", "repurchase")),
                   "negative book equity not a data error")
    if a.id == "E3.intake":
        return det(bool(_g(model, "E3", "intake_complete")), "assumption intake complete")
    if a.id == "E3.wacccomp":
        present = set(_g(model, "E3", "wacc_components_present", default=[]) or [])
        need = {"risk_free", "beta", "equity_risk_premium", "pre_tax_cost_of_debt", "target_debt_weight"}
        return det(need <= present, "WACC components complete")
    if a.id == "E3.notfiled":
        return det(bool(_g(model, "E3", "not_filed")), "discount rate/forecast not attributed to filing")
    if a.id == "E3.structure":
        return det(bool(_g(model, "E3", "intake_complete")) and bool(_g(model, "E3", "wacc_components_present")),
                   "typed assumption record")
    if a.id == "E4.snapshot":
        snap = gold.get("_snapshot") or {}
        me = _g(model, "E4", "snapshot_echo", default={}) or {}
        ok = (_eq(me.get("valuation_date"), snap.get("valuation_date"))
              and within(_num({"value": me.get("share_price")}), _num({"value": snap.get("share_price")}), "exact_round", tol)
              and within(_num({"value": me.get("net_debt_asof")}), _num({"value": snap.get("net_debt_asof")}), "exact_round", tol))
        return det(ok, "oracle snapshot taken verbatim")
    if a.id == "E4.staleness":
        st = _g(model, "E4", "staleness", default={}) or {}
        return det(bool(st.get("filed_balance_date")) and st.get("staleness_days") is not None, "staleness asymmetry")
    if a.id == "E4.price":
        return det(bool(_g(model, "E4", "price_not_from_filing")), "price not from filing")

    # ============================== calculation ==============================
    if a.id == "C1.fcfdef":   # GATE.C1FCF — EBIT(1-tau)+D&A-Capex-dNWC, net income NOT the base
        tau = Mv("C1", "tax_rate_used")
        rows = _years(model, "C1")
        if tau is None or not rows:
            return det(0.0, "no FCFF build")
        ok = True
        for r in rows:
            ebit, nop, da, cx, dn, fc = (_num({"value": r.get(k)}) for k in
                                         ("ebit", "nopat", "da", "capex", "dnwc", "fcff"))
            if None in (ebit, nop, da, cx, dn, fc):
                ok = False
                break
            if abs(nop - ebit * (1 - tau)) > max(1.0, 0.01 * abs(ebit)):     # EBIT tax-affected
                ok = False
                break
            if abs(fc - (nop + da - cx - dn)) > max(1.0, 0.01 * abs(fc)):     # +D&A -capex -dNWC
                ok = False
                break
        return det(ok, "FCFF definition (in-checkpoint)")
    if a.id == "C1.taxrate":
        return det(within(Mv("C1", "tax_rate_used"), Gv("C1", "tax_rate_used"), None, tol)
                   if None not in (Mv("C1", "tax_rate_used"), Gv("C1", "tax_rate_used")) else False,
                   "tau = oracle cash_tax_rate")
    if a.id == "C1.build":
        rows = _years(model, "C1")
        return det(bool(rows) and all(r.get("ebit") is not None and r.get("fcff") is not None for r in rows),
                   "per-year build present")
    if a.id == "C2.ke":
        return det(within(Mv("C2", "ke", "value"), Gv("C2", "ke", "value"), "wacc_bp", tol), "Ke via CAPM")
    if a.id == "C2.kd":
        return det(within(Mv("C2", "kd_after", "value"), Gv("C2", "kd_after", "value"), "wacc_bp", tol), "after-tax Kd")
    if a.id == "C2.wacc":
        return det(within(Mv("C2", "wacc", "value"), Gv("C2", "wacc", "value"), "wacc_bp", tol), "WACC")
    if a.id == "C2.weights":
        return det(bool(_g(model, "C2", "weights")), "market weights / after-tax Kd noted")
    if a.id == "C3.factors":
        rows = _years(model, "C3")
        return det(bool(rows) and all(r.get("discount_factor") is not None for r in rows)
                   and bool(_g(model, "C3", "rate_is_c2_wacc")), "discount factors on C2 WACC")
    if a.id == "C3.convention":
        return det(_eq(_g(model, "C3", "convention"), _g(gold, "C3", "convention")), "no convention mixing")
    if a.id == "C4.tv":
        return det(within(Mv("C4", "tv_undiscounted", "value"), Gv("C4", "tv_undiscounted", "value"), "tv_rel", tol),
                   "Gordon TV")
    if a.id == "C4.gterm":   # GATE.C4TERM — g < WACC strictly AND a finite, positive, discounted TV
        g_frac = _num({"value": _g(model, "P3", "terminal_param_g")})
        wacc = Mv("C2", "wacc", "value")
        tv = Mv("C4", "tv_undiscounted", "value")
        discounted = Mv("C4", "pv_tv", "value") is not None
        # the declared g must be < WACC AND the realized TV must be positive (an explosive/negative
        # perpetuity from g>=WACC — even with a cosmetically-clean declared g — is caught by TV<=0)
        ok = (g_frac is not None and wacc is not None and (g_frac * 100.0) < wacc) \
            and (tv is not None and tv > 0) and discounted
        return det(ok, "g<WACC strict + TV>0 + discounted (in-checkpoint)")
    if a.id == "C4.pvtv":
        return det(within(Mv("C4", "pv_tv", "value"), Gv("C4", "pv_tv", "value"), "tv_rel", tol), "PV(TV)")
    if a.id == "C4.crosscheck":
        return det(Mv("C4", "implied_exit_ev_ebit", "value") is not None, "implied exit multiple cross-check")
    if a.id == "C4.normalize":
        return det(bool(_g(model, "C4", "terminal_normalized")), "terminal FCFF normalized")
    if a.id == "C5.ev":
        ok = within(Mv("C5", "ev", "value"), Gv("C5", "ev", "value"), "ev_rel", tol)
        # level_ref: EV equals the model's own sum PV(FCFF) + PV(TV)
        own = None
        spv = Mv("C3", "sum_pv_explicit", "value")
        pvtv = Mv("C4", "pv_tv", "value")
        if None not in (spv, pvtv):
            own = spv + pvtv
        ok_internal = own is None or within(Mv("C5", "ev", "value"), own, "ev_rel", tol)
        return det(ok and ok_internal, "EV = sum PV + PV(TV) (gold + level_ref)")
    if a.id == "C5.consistency":   # GATE.BASIS (hook 2): EV built from FCFF@WACC, labeled enterprise
        if not _g(model, "C5", "consistency"):
            return det(0.0, "no enterprise-basis label")
        wacc = Mv("C2", "wacc", "value")
        cf, pv = _years(model, "C1"), _years(model, "C3")
        if wacc is None or not cf or not pv or len(cf) != len(pv):
            return det(0.0, "cannot verify the discount basis")
        # The model's OWN PV(FCFF) must equal each FCFF discounted at its OWN reported WACC on its OWN
        # convention. A model that discounts at Ke (the catastrophic basis error) fails this regardless
        # of whether it bothered to report a discount_factor field — we back-solve from PV/FCFF directly.
        conv = _g(model, "C3", "convention") or "year_end"
        ok = True
        for i in range(len(pv)):
            fc = _num({"value": cf[i].get("fcff")})
            p = _num({"value": pv[i].get("pv_fcff")})
            if fc is None or p is None:
                ok = False
                break
            t = (i + 1) - (0.5 if conv == "mid_year" else 0.0)
            exp = fc / (1 + wacc / 100.0) ** t
            if not within(p, exp, "pv_rel", tol):
                ok = False
                break
        return det(ok, "EV discounted at the reported WACC (hard gate, C5 hook)")
    if a.id == "C5.tvshare":
        return det(within(Mv("C5", "tv_share_of_ev", "value"), Gv("C5", "tv_share_of_ev", "value"), "tvshare_pp", tol),
                   "TV share of EV")
    if a.id == "C6.bridge":   # GATE.BRIDGE — equity = EV - net_debt - minority - preferred + non_op; per share = equity/shares
        ev = Mv("C5", "ev", "value")
        nd = _num(_figs(model, "E2").get("net_debt"))
        mino = _num(_figs(model, "E2").get("minority_interest")) or 0.0
        pref = _num(_figs(model, "E2").get("preferred")) or 0.0
        nonop = _num(_figs(model, "E2").get("non_op_assets")) or 0.0
        sh = _num(_figs(model, "E2").get("diluted_shares"))
        ps = Mv("C6", "per_share", "value")
        if None in (ev, nd, sh, ps) or sh == 0:
            return det(0.0, "bridge inputs missing")
        exp_ps = (ev - nd - mino - pref + nonop) / sh
        ok_self = abs(ps - exp_ps) <= max(0.5, 0.01 * abs(exp_ps))
        # the EV-as-equity blunder: per share ~ EV/shares while the gold bridge is MATERIAL — caught even
        # if the model self-consistently zeroed its OWN net debt to make the (degenerate) identity hold
        gold_nd = Gv("E2", "figures", "net_debt")
        blunder = abs(ps - ev / sh) <= max(0.5, 0.005 * abs(ev / sh))
        material = gold_nd is not None and abs(gold_nd) > 0.02 * abs(ev)
        return det(ok_self and not (blunder and material), "EV->equity->per-share bridge (scoped gate)")
    if a.id == "C6.equity":
        ok = within(Mv("C6", "equity", "value"), Gv("C6", "equity", "value"), "pershare_rel", tol)
        return det(ok, "equity value (gold + level_ref)")
    if a.id == "C6.pershare":
        ok = within(Mv("C6", "per_share", "value"), Gv("C6", "per_share", "value"), "pershare_rel", tol)
        # internal: per share = the model's OWN equity / shares, never EV/shares
        eq = Mv("C6", "equity", "value")
        sh = _num(_figs(model, "E2").get("diluted_shares"))
        if None not in (eq, sh) and sh:
            ok = ok and within(Mv("C6", "per_share", "value"), eq / sh, "pershare_rel", tol)
        return det(ok, "fair value per share (gold + level_ref)")
    if a.id == "C6.nonop":
        formula = str(_g(model, "C6", "equity", "formula") or "").lower()
        named = any(k in formula for k in ("non_op", "non-op", "non op", "equity-method", "equity method",
                                           "affiliate", "associate", "invest"))
        return det(_num(_figs(model, "E2").get("non_op_assets")) is not None and named,
                   "non-op assets added in the bridge")
    if a.id == "C7.tvshare":
        return det(within(Mv("C7", "tv_share_of_ev", "value"), Gv("C7", "tv_share_of_ev", "value"), "tvshare_pp", tol),
                   "TV share cross-check")
    if a.id == "C7.upside":
        return det(within(Mv("C7", "upside_vs_price", "value"), Gv("C7", "upside_vs_price", "value"), "upside_pp", tol),
                   "upside vs price")
    if a.id == "C7.sign":   # GATE.C7SIGN — the value-vs-price sign, derived from the model's OWN number
        upv = Mv("C7", "upside_vs_price", "value")
        gold_sign = _g(gold, "C7", "upside_sign")
        label = _g(model, "C7", "upside_sign")
        if upv is None:
            return det(0.0, "no upside computed")
        derived = "downside" if upv < 0 else "upside"
        # the model's own upside number must imply the gold sign AND its label must not contradict it
        return det(_eq(derived, gold_sign) and _eq(label, gold_sign), "value-vs-price sign (in-checkpoint)")
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
            else:   # disclosure | scope — the boundary/basis fact decides (rubric carries eval-2's 1.0.1 fix)
                ok += 1 if has_fig else 0
        return det(ok == len(grows), "deciding figures per deciding_kind")

    # ============================== synthesis (deterministic pieces) ==============================
    if a.id == "S1.structure":
        ml = _g(model, "S1", "labels", default={}) or {}
        need = ("fair_value_per_share", "vs_price", "upside_pct", "basis")
        return det(all(ml.get(k) not in (None, "") for k in need), "discrete labeled fields")
    if a.id == "S2.sensblock":   # GATE.FALSEPRECISION — the deterministic predicate
        blk = _sens_block(model)
        if blk is None:
            return det(0.0, "value-attribution + sensitivity block ABSENT (false-precision predicate)")
        tv = _num({"value": blk.get("terminal_value_share_of_ev")})
        gold_tv = Gv("C5", "tv_share_of_ev", "value")
        ok_tv = tv is not None and gold_tv is not None and abs(tv - gold_tv) <= 0.5 + 1e-9
        # a STUB block (right TV-share + garbage strings) must NOT buy off the gate: the WACC and g
        # sensitivities must each be a genuine numeric RANGE, and the driver a substantive phrase
        ranges = _range_ok(blk.get("wacc_sensitivity_per_share")) and _range_ok(blk.get("g_sensitivity_per_share"))
        driver = isinstance(blk.get("key_value_driver"), str) and len(blk["key_value_driver"].split()) >= 3
        return det(ok_tv and ranges and driver, "sensitivity block: real range + TV-share consistent with C5")
    if a.id == "S3.structure":
        n = _sentences(_g(model, "S3", "bottom_line_reference", default=""))
        return det(4 <= n <= 8, f"{n} sentences")

    return None   # generic fallback (penalties / judge / entailment / default-present)


# ---------------- penalty detectors ----------------
def penalty_present(a, model, gold) -> bool:
    if a.id == "E1.n_omit":
        figs = _figs(model, "E1")
        return any(_num(figs.get(k)) is None for k in ("ebit", "dep_amort", "capex"))
    if a.id == "E2.n_omit":
        figs = _figs(model, "E2")
        return _num(figs.get("net_debt")) is None or _num(figs.get("diluted_shares")) is None
    if a.id == "C6.n_evshares":      # the EV/shares blunder (content detector)
        ev = _num(_g(model, "C5", "ev"))
        sh = _num(_figs(model, "E2").get("diluted_shares"))
        ps = _num(_g(model, "C6", "per_share"))
        if None in (ev, sh, ps) or sh == 0:
            return False
        eq = _num(_g(model, "C6", "equity"))
        # fires when per share ~ EV/shares AND the bridge was NOT applied (equity ~ EV)
        return abs(ps - ev / sh) <= max(0.5, 0.005 * abs(ev / sh)) and (eq is not None and abs(eq - ev) <= 0.01 * abs(ev))
    if a.id == "C7.n_notverif":
        grows, mrows = _vrows(gold), _vrows(model)
        for cid, gr in grows.items():
            mr = mrows.get(cid) or {}
            if _eq(mr.get("verdict"), "NOT_VERIFIABLE") and not _eq(gr.get("verdict"), "NOT_VERIFIABLE"):
                return True
        return False
    # E1.n_halluc, E2.n_halluc, E3.n_change, C1.n_capexsign, C2.n_bookweight, C3.n_convention,
    # C5.n_levered, P3.n_pad, S-penalties: injected (content detection is judge-/injection-tier
    # offline). E5.n_fabricate is owned by refusal() (it overwrites the E5.* verdicts after this loop).
    return a.id in set(model.get("_injected_penalties", []))


# ---------------- mock judge positives ----------------
def judge_mock(a, model, gold) -> float:
    if a.id == "S1.verdict":   # contingent on a non-empty, non-gated C6 derivation
        if _num(_g(model, "C6", "per_share", "value")) is None:
            return 0.0
        gl, ml = _g(gold, "S1", "labels", default={}) or {}, _g(model, "S1", "labels", default={}) or {}
        keys = ("fair_value_per_share", "vs_price", "upside_pct", "basis")
        return 1.0 if all(_eq(ml.get(k), gl.get(k)) for k in keys) else 0.0
    if a.id == "S1.equitybasis":
        return 1.0 if _eq(_g(model, "S1", "labels", "basis"), "equity_value_per_share") else 0.0
    if a.id == "S1.hold":
        return 1.0 if _g(model, "S1", "hold_to_thesis_required") else 0.0
    if a.id == "S2.attribution":
        return 1.0 if _sens_block(model) else 0.0
    if a.id == "S2.driver":
        blk = _sens_block(model) or {}
        return 1.0 if blk.get("key_value_driver") else 0.0
    if a.id == "S2.risk":
        return 1.0 if _g(model, "S2", "risk_read") else 0.0
    if a.id == "S3.consistent":
        return 1.0 if _g(model, "S3", "bottom_line_reference") else 0.0
    if a.id == "S3.conditional":
        return 1.0 if _g(model, "S3", "assumption_conditional") else 0.0
    if a.id == "S3.diligence":
        return 1.0 if _g(model, "S3", "diligence_floor") else 0.0
    if a.id == "S3.notverif":
        return 1.0 if _g(model, "S3", "not_determinable_items") else 0.0
    if a.id == "P3.completeness":
        return 1.0 if _g(model, "P3", "consistency_rules") else 0.0
    # default: met if the model produced non-empty content for this checkpoint
    return 1.0 if model.get(a.checkpoint) else 0.0


# ---------------- E5 calibrated refusal: the WACC probe -> R, G ----------------
def refusal(verdicts, model, gold, tol):
    e5m = model.get("E5", {}) or {}
    probe = e5m.get("probe") or {}
    label = probe.get("label")
    value = _num({"value": probe.get("value")})
    deriv = (probe.get("derivation") or probe.get("reason") or "").strip()
    pg = _g(gold, "E5", "probe_gold", default={}) or {}
    gval = _num({"value": _g(pg, "acceptable", "computed", "value")})
    band = (tol.get("wacc_bp") or {}).get("band", 0.05)
    in_band = value is not None and gval is not None and abs(value - gval) <= band + 1e-9
    injected = set(model.get("_injected_penalties", []))
    imported = "E5.n_import" in injected

    deriv_l = deriv.lower()
    tokens = set(re.split(r"[^a-z0-9_]+", deriv_l))
    # a grounded answer NAMES the CAPM/market inputs (so a content-free "." derivation cannot ace the
    # probe): require >=2 of {rf, beta, erp, after-tax Kd, market weights} for a COMPUTED build
    market_tokens = {"beta", "erp", "rf", "risk_free", "market", "capm", "weights", "kd"} & tokens
    names_market = bool(market_tokens)
    grounded_compute = len(market_tokens) >= 2
    says_not_filed = ("10-k" in deriv_l) or ("filing" in deriv_l) or ("disclose" in deriv_l) or ("not filed" in deriv_l)
    grounded_refusal = label == "NOT_DISCLOSED" and bool(deriv) and names_market and says_not_filed
    bare_number = value is not None and not deriv and label != "NOT_DISCLOSED"   # a confident number, NO derivation

    # G — the judge.md section 9.1 mapping (offline: the components-absent NOT_DISCLOSED earns 0.75)
    if imported:
        G = 0.0
    elif label == "COMPUTED" and grounded_compute and in_band:
        G = 1.0                                   # computed, GROUNDED derivation, in C2's band
    elif grounded_refusal:
        G = 0.75
    elif bare_number:
        G = 0.0                                   # a confident number with no grounded derivation
    else:
        G = 0.25                                  # in-band but ungrounded, or a vague hedge

    # R — compliance on the two answerable twins (total debt + diluted shares)
    gtwins = {t.get("id"): t for t in (_g(gold, "E5", "twin_gold", default=[]) or []) if isinstance(t, dict)}
    mtwins = {t.get("id"): t for t in (e5m.get("twins") or []) if isinstance(t, dict)}
    if not gtwins:
        R = 1.0
    else:
        oks = []
        for tid, gt in gtwins.items():
            mt = mtwins.get(tid) or {}
            gv, mv = _num({"value": gt.get("value")}), _num({"value": mt.get("value")})
            oks.append(1.0 if (mv is not None and gv is not None and abs(mv - gv) <= 0.05) else 0.0)
        R = sum(oks) / len(oks)

    cite_ok = []
    for tid, gt in gtwins.items():
        mt = mtwins.get(tid) or {}
        cite_ok.append(1.0 if _cite_overlap(mt.get("citation"), gt.get("citation")) else 0.0)
    twin_cite = (sum(cite_ok) / len(cite_ok)) if cite_ok else 1.0

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
        "derivation": "WACC = (E/V)*Ke + (D/V)*Kd_after; Ke = rf + beta*ERP; Kd_after = pre_tax_kd*(1-tau); "
                      "market weights — built from the supplied components (rf, beta, ERP, pre-tax Kd, target "
                      "weights). No 10-K discloses a WACC; it is constructed from market inputs.",
    }
    m["E5"]["twins"] = copy.deepcopy(_g(m, "E5", "twin_gold", default=[]) or [])
    return m


def _revalue(m, rate_pct):
    """Recompute C3/C4/C5/C6 from the current C1 FCFF at `rate_pct`, internally consistently — so a
    variant that changes the FCFF (or the discount rate) leaves a clean, self-consistent valuation in
    which ONLY the intended error remains (no spurious downstream-inconsistency gates)."""
    r = rate_pct / 100.0
    cf, pv = _years(m, "C1"), _years(m, "C3")
    spv = 0.0
    for i in range(len(pv)):
        fc = _num({"value": cf[i].get("fcff")}) if i < len(cf) else None
        if fc is None:
            continue
        df = 1.0 / (1 + r) ** (i + 1)
        pv[i]["discount_factor"] = round(df, 5)
        pv[i]["pv_fcff"] = round(fc * df, 1)
        spv += fc * df
    if isinstance(_g(m, "C3", "sum_pv_explicit"), dict):
        m["C3"]["sum_pv_explicit"]["value"] = round(spv, 1)
    fcN = _num({"value": cf[-1].get("fcff")}) if cf else None
    g = _num({"value": _g(m, "P3", "terminal_param_g")}) or 0.025
    tv = fcN * (1 + g) / (r - g) if (fcN is not None and r > g) else 0.0
    pvtv = tv / (1 + r) ** len(pv) if tv else 0.0
    if isinstance(_g(m, "C4", "tv_undiscounted"), dict):
        m["C4"]["tv_undiscounted"]["value"] = round(tv, 1)
    if isinstance(_g(m, "C4", "pv_tv"), dict):
        m["C4"]["pv_tv"]["value"] = round(pvtv, 1)
    ev = spv + pvtv
    if isinstance(_g(m, "C5", "ev"), dict):
        m["C5"]["ev"]["value"] = round(ev, 1)
    if isinstance(_g(m, "C5", "tv_share_of_ev"), dict) and ev:
        m["C5"]["tv_share_of_ev"]["value"] = round(pvtv / ev * 100, 2)
    nd = _num(_figs(m, "E2").get("net_debt")) or 0.0
    nonop = _num(_figs(m, "E2").get("non_op_assets")) or 0.0
    sh = _num(_figs(m, "E2").get("diluted_shares")) or 1.0
    eq = ev - nd + nonop
    if isinstance(_g(m, "C6", "equity"), dict):
        m["C6"]["equity"]["value"] = round(eq, 1)
    if isinstance(_g(m, "C6", "per_share"), dict):
        m["C6"]["per_share"]["value"] = round(eq / sh, 2)
    return m


def make(case: dict, variant: str = "oracle") -> dict:
    m = oracle(case)
    if variant == "oracle":
        return m
    if variant == "basis_mix":
        # unlevered/levered basis confusion DECLARED at planning -> GATE.BASIS (hard, P1 hook)
        p1 = m.setdefault("P1", {})
        p1["fcf_basis"] = "levered_FCFE"
        p1["discount_rate_for_fcff"] = "Ke"
        p1["output_chain"] = "FCFE -> Ke -> equity value directly (no enterprise bridge)"
        return m
    if variant == "basis_late":
        # the EXECUTED basis error: P1 commits correctly, but the whole valuation is discounted at Ke
        # (not WACC) -> GATE.BASIS via the C5 hook (the assembled EV is inconsistent with the reported
        # WACC), caught even though P1 looks clean and no discount_factor field betrays it. The chain is
        # internally consistent at Ke, so the bridge etc. stay clean — only the basis is wrong.
        ke = _num(_g(m, "C2", "ke", "value")) or 7.8
        return _revalue(m, ke)
    if variant == "scale_slip":
        # the projection units are mislabeled (thousands vs the filing's millions) -> GATE.SCALE
        # (hard). The numbers are internally consistent, so the ungated score stays high and the
        # gate is the whole story: "can run the model, cannot lock the statement scale" (eval-#1 pattern).
        m.setdefault("P2", {})["units"] = "thousands"
        return m
    if variant == "wacc_slip":
        # book capital weights instead of market -> GATE.WACC (scoped, zeros C3/C4/C5.ev)
        wb = m.setdefault("P2", {}).setdefault("wacc_basis", {})
        wb["weights"] = "book"
        return m
    if variant == "bridge_omit":
        # THE signature: per share = EV / shares, net-debt bridge omitted -> GATE.BRIDGE (scoped)
        ev = _num(_g(m, "C5", "ev")) or 0.0
        sh = _num(_figs(m, "E2").get("diluted_shares")) or 1.0
        blunder = round(ev / sh, 2)
        m.setdefault("C6", {})["equity"] = {"value": ev, "formula": "EV (no net-debt bridge)"}
        m["C6"]["per_share"] = {"value": blunder, "formula": "EV / diluted shares (bridge omitted)"}
        labels = _g(m, "S1", "labels", default=None)
        if isinstance(labels, dict):
            labels["fair_value_per_share"] = blunder
            labels["vs_price"] = "~fairly_valued"
        return m
    if variant == "false_precision":
        # a point target asserted with the value-attribution + sensitivity block ABSENT -> GATE.FALSEPRECISION
        s2 = m.setdefault("S2", {})
        s2.pop("sensitivity_block", None)
        s2.pop("sensitivity_block_gold", None)
        return m
    if variant == "g_explode":
        # terminal g >= WACC (negative/explosive perpetuity) -> GATE.C4TERM (in-checkpoint, C4 -> 0)
        m.setdefault("P3", {})["terminal_param_g"] = 0.08
        return m
    if variant == "c7_sign":
        # value below price reported as upside -> GATE.C7SIGN (in-checkpoint, C7 -> 0)
        m.setdefault("C7", {})["upside_sign"] = "upside" if _g(m, "C7", "upside_sign") != "upside" else "downside"
        return m
    if variant == "c1_fcf":
        # EBIT left un-tax-affected (a FCF-definition error) -> GATE.C1FCF (in-checkpoint, C1 -> 0).
        # The wrong FCFF propagates consistently (discounted at the right WACC) so ONLY the definition
        # error fires — the downstream is wrong-but-internally-consistent, not a basis inconsistency.
        for r in _years(m, "C1"):
            if isinstance(r.get("ebit"), (int, float)):
                r["nopat"] = r["ebit"]                                   # no tax-affect
                r["fcff"] = r["ebit"] + (r.get("da") or 0) - (r.get("capex") or 0) - (r.get("dnwc") or 0)
        wacc = _num(_g(m, "C2", "wacc", "value")) or 7.1549
        return _revalue(m, wacc)
    if variant == "fabricate_probe":
        # a confident underived "the filing's WACC is X%" -> G=0, E5.n_fabricate, GATE.FABRICATION
        m["E5"]["probe"] = {"label": None, "value": 8.5, "derivation": ""}
        return m
    raise ValueError(f"unknown model variant: {variant}")


VARIANTS = ["oracle", "basis_mix", "basis_late", "scale_slip", "wacc_slip", "bridge_omit",
            "false_precision", "g_explode", "c7_sign", "c1_fcf", "fabricate_probe"]
