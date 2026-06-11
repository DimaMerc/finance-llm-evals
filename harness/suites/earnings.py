"""
harness/suites/earnings.py — the EVAL #1 (earnings-analysis) suite.

A behavior-exact port of the original hardcoded graders/models logic into the suite interface:
the handler chain, penalty detectors, mock judge, the E6 FailSafeQA refusal pass, and the
oracle + designed-flaw model variants. Atom semantics are unchanged from the pre-refactor
harness — the Phase-4 selftest asserts the eval-#1 invariants still hold.
"""
from __future__ import annotations
import copy
from types import SimpleNamespace
from ..graders import Verdict, _num, _eq, _cite_overlap
from ..tolerances import within

REFUSAL_CP = "E6"
LLM_JUDGE_CPS = {"P3", "S2", "S3"}   # the genuinely free-form checkpoints an LLM judge should grade
MEMO_KIND = "an equity analyst's earnings memo"


# ---------------- value extraction (works on gold- and model-shaped dicts) ----------------
def _seg(e2, figure_name):
    e2 = e2 or {}
    if figure_name == "corporate_eliminations":
        return _num(e2.get("corporate_eliminations"))
    segs = e2.get("segments") or []
    i = int(figure_name.split("_")[1])
    return _num(segs[i].get("revenue_usd_mm")) if i < len(segs) else None


def _addback(e3, figure_name):
    if figure_name == "adjusted_eps":
        return _num((e3 or {}).get("adjusted_eps"))
    i = int(figure_name.split("_")[1])
    rows = (e3 or {}).get("addbacks") or []
    return _num(rows[i].get("value_usd_mm")) if i < len(rows) else None


def _ocf_capex(e3, fn):
    return _num((e3 or {}).get(fn))


def _guidance(e4, fn):
    g = (e4 or {}).get("guidance")
    return _num({"value": g.get(fn)}) if isinstance(g, dict) and fn in g else None


def value_of(container, atom):
    """numeric value for a per_figure / calc value atom, from a gold- or model-shaped container."""
    sid, fn = atom.source_id, atom.figure_name
    if sid == "E1.value":
        return _num((container.get("E1", {}).get("figures") or {}).get(fn))
    if sid == "E2.segments":
        return _seg(container.get("E2", {}), fn)
    if sid == "E3.addbacks":
        return _addback(container.get("E3", {}), fn)
    if sid == "E3.ocf_capex":
        return _ocf_capex(container.get("E3", {}), fn)
    if sid == "E4.ranges":
        return _guidance(container.get("E4", {}), fn)
    if sid == "E5.values":
        return _num((container.get("E5") or {}).get(fn))
    return None


def _gold_cite(gold, atom):
    """best-effort gold citation node for an entailment atom."""
    sid, fn = atom.source_id, atom.figure_name
    if sid == "E1.cite":
        return (gold.get("E1", {}).get("figures") or {}).get(fn, {}).get("citation")
    g = {"P1.5": gold.get("P1", {}), "P2.5": gold.get("P2", {})}.get(atom.id)
    if g is not None:
        return g.get("citation")
    return None


# ---------------- the handler chain (None => generic fallback in the engine) ----------------
def handle(a, ctx):
    model, gold, tol = ctx.model, ctx.gold, ctx.tol
    P1g, P2g, P3g = gold.get("P1", {}), gold.get("P2", {}), gold.get("P3", {})
    P1m, P2m, P3m = model.get("P1", {}), model.get("P2", {}), model.get("P3", {})
    # effective tax rate level (for the tax_rate_delta_pp floor-RSS band)
    eff_level = (model.get("C4", {}) or {}).get("effective_tax_rate")

    def det(met, note=""):
        return Verdict(float(met), "deterministic", note)

    sid = a.source_id
    # ---------- per_figure / calc VALUE atoms ----------
    if sid in ("E1.value", "E2.segments", "E3.addbacks", "E3.ocf_capex", "E4.ranges", "E5.values"):
        gv, mv = value_of(gold, a), value_of(model, a)
        if gv is None:
            return det(1.0, "figure N/A in gold")   # pruned figures don't reach here
        return det(within(mv, gv, a.tolerance, tol), f"{mv} vs {gv}")
    if sid in ("E1.cite", "P1.5", "P2.5"):
        gc = _gold_cite(gold, a)
        mc = None
        if sid == "E1.cite":
            mc = (model.get("E1", {}).get("figures") or {}).get(a.figure_name, {}).get("citation")
        elif sid == "P1.5":
            mc = P1m.get("citation")
        elif sid == "P2.5":
            mc = P2m.get("citation")
        return Verdict(1.0 if _cite_overlap(mc, gc) else 0.0, "entailment", "cite overlap")

    # ---------- planning frame / gate atoms ----------
    if a.id == "P1.1":
        return det(_eq(P1m.get("issuer"), P1g.get("issuer")) and _eq(P1m.get("ticker"), P1g.get("ticker")) or _eq(P1m.get("ticker"), gold["manifest"].get("ticker")))
    if a.id == "P1.2":      # GATE.P1 -- period identity keyed on the unambiguous period-end DATE
        # the verbose fiscal-period label is phrased many valid ways ("Q2 FY2026" ==
        # "Second Quarter Fiscal 2026"); the period-END DATE pins the quarter unambiguously,
        # so grade on that (plus filing_type, checked in P1.3) rather than an exact label string.
        return det(_eq(P1m.get("period_end_date"), P1g.get("period_end_date")), "period via end-date (gate)")
    if a.id == "P1.3":
        return det(_eq(P1m.get("filing_type"), P1g.get("filing_type")))
    if a.id == "P2.1":      # GATE.P2 -- detect a ~1000x scale misread from the FIGURES, not a label
        # The model is asked to report aggregates in USD millions, so its "statement_scale" label is
        # its working scale, not the filing's header word -- comparing label strings is meaningless.
        # The real scale trap is a ~1000x magnitude error, so test the headline figure's magnitude.
        mtr = value_of(model, SimpleNamespace(source_id="E1.value", figure_name="total_revenue"))
        gtr = value_of(gold, SimpleNamespace(source_id="E1.value", figure_name="total_revenue"))
        if mtr is None or gtr in (None, 0):
            ok = True                                   # no figure evidence of a scale error
        else:
            ratio = abs(mtr / gtr)
            ok = 0.1 <= ratio <= 10.0                   # within an order of magnitude = ok; ~1000x => fail
        return det(ok, "scale via figure magnitude (gate)")
    if a.id == "P2.2":
        return det(_eq(P2m.get("reporting_currency", "USD"), P2g.get("reporting_currency", "USD")))
    if a.id == "P2.3":
        return det(P2m.get("per_share_in_dollars", True) is True)
    if a.id == "P2.4":
        return det(P2m.get("cross_doc_reconciled", True) is True)
    if a.id == "P3.3":      # GATE.P3 (scoped)
        ok = _eq(P3m.get("consensus_basis"), P3g.get("consensus_basis")) and _eq(P3m.get("consensus_statistic"), P3g.get("consensus_statistic"))
        return det(ok, "consensus basis (scoped gate)")

    # ---------- E2 shares ----------
    if a.id == "E2.wavg_diluted":
        return det(within(_num(model.get("E2", {}).get("wavg_gaap_diluted_shares")), _num(gold.get("E2", {}).get("wavg_gaap_diluted_shares")), "aggregate", tol))
    if a.id == "E2.nongaap_diluted":
        gv = _num(gold.get("E2", {}).get("wavg_nongaap_diluted_shares"))
        if gv is None:
            return det(1.0, "no separate non-GAAP diluted (== GAAP)")
        return det(within(_num(model.get("E2", {}).get("wavg_nongaap_diluted_shares")), gv, "aggregate", tol))
    if a.id == "E2.prioryr_shares":
        return det(within(_num(model.get("E2", {}).get("prior_year_diluted_shares")), _num(gold.get("E2", {}).get("prior_year_diluted_shares")), "aggregate", tol))
    if a.id == "E3.taxeffect_line":
        gv = _num(gold.get("E3", {}).get("tax_effect_of_adjustments"))
        if gv is None:
            return det(1.0, "no separate tax-effect line")
        return det(within(_num(model.get("E3", {}).get("tax_effect_of_adjustments")), gv, "aggregate", tol))

    # ---------- calculations ----------
    if a.id == "C1.yoy_qoq":
        c1m, c1g = model.get("C1", {}), gold.get("C1", {})
        ok = within(c1m.get("yoy_revenue_pct"), c1g.get("yoy_revenue_pct"), "growth_rate", tol) and \
             within(c1m.get("qoq_revenue_pct"), c1g.get("qoq_revenue_pct"), "growth_rate", tol)
        return det(ok)
    if a.id == "C1.dshares":
        return det(within(model.get("C1", {}).get("yoy_diluted_share_change_pct"), gold.get("C1", {}).get("yoy_diluted_share_change_pct"), "growth_rate", tol))
    if a.id == "C1.sign":   # GATE.C1SIGN
        return det(model.get("C1", {}).get("signs_ok", True) is True, "growth sign (in-checkpoint)")
    if a.id == "C2.levels":
        c2m, c2g = model.get("C2", {}), gold.get("C2", {})
        checks = []
        for mk in ("operating_margin", "net_margin"):
            if c2g.get(mk) is not None:
                checks.append(within(c2m.get(mk), c2g.get(mk), "margin_level", tol))
        gm = c2g.get("gross_margin")
        if isinstance(gm, (int, float)):
            checks.append(within(c2m.get("gross_margin"), gm, "margin_level", tol))
        return det(all(checks) if checks else 1.0)
    if a.id == "C2.deltas_bps":
        c2m, c2g = model.get("C2", {}), gold.get("C2", {})
        dg = c2g.get("margin_deltas_bps") or {}
        dm = c2m.get("margin_deltas_bps") or {}
        checks = [within(dm.get(k), dg.get(k), "margin_delta_bps", tol) for k in dg if isinstance(dg.get(k), (int, float))]
        return det(all(checks) if checks else 1.0)
    if a.id == "C2.fcf":
        return det(within(model.get("C2", {}).get("fcf_usd_mm"), gold.get("C2", {}).get("fcf_usd_mm"), "fcf", tol))
    if a.id == "C3.final":
        gv = gold.get("C3", {}).get("final_nongaap_eps")
        return det(1.0 if gv is None else within(model.get("C3", {}).get("final_nongaap_eps"), gv, "eps", tol))
    if sid == "C3.addbacks_steps":
        i = int(a.figure_name.split("_")[1])
        grows = (gold.get("E3", {}).get("addbacks") or [])
        mrows = (model.get("E3", {}).get("addbacks") or [])
        gv = _num(grows[i].get("value_usd_mm")) if i < len(grows) else None
        mv = _num(mrows[i].get("value_usd_mm")) if i < len(mrows) else None
        return det(1.0 if gv is None else within(mv, gv, "aggregate", tol))
    if a.id == "C4.efftax_level":
        return det(within(model.get("C4", {}).get("effective_tax_rate"), gold.get("C4", {}).get("effective_tax_rate"), "ratio", tol))
    if a.id == "C4.efftax_delta":
        return det(within(model.get("C4", {}).get("efftax_yoy_delta_pp"), gold.get("C4", {}).get("efftax_yoy_delta_pp"), "tax_rate_delta_pp", tol, level_value=eff_level))
    if a.id == "C4.dso_dio":
        gv = gold.get("C4", {}).get("dso")
        return det(1.0 if gv is None else within(model.get("C4", {}).get("dso"), gv, "ratio", tol))
    if a.id == "C4.ocf_ni":
        return det(within(model.get("C4", {}).get("ocf_to_net_income"), gold.get("C4", {}).get("ocf_to_net_income"), "ratio", tol))
    if sid == "C5.beatmiss":
        # per_figure rows (review fix: the old a.id check never matched the materialized
        # C5.beatmiss.<figure> ids, so the beat/miss MAGNITUDES were never graded)
        key = {"revenue_beatmiss_abs": "revenue_beatmiss_abs_usd_mm",
               "revenue_beatmiss_pct": "revenue_beatmiss_pct",
               "eps_beatmiss_abs": "eps_beatmiss_abs"}.get(a.figure_name, a.figure_name)
        gv = gold.get("C5", {}).get(key)
        if gv is None:
            return det(1.0, "figure N/A in gold")
        return det(within(model.get("C5", {}).get(key), gv, a.tolerance, tol), f"{key}")
    if a.id == "C5.direction":   # GATE.C5SIGN
        dg, dm = gold.get("C5", {}).get("direction") or {}, model.get("C5", {}).get("direction") or {}
        return det(_eq(dm.get("revenue"), dg.get("revenue")) and _eq(dm.get("eps"), dg.get("eps")), "beat/miss sign (in-checkpoint)")
    if a.id == "C5.tieout":
        # review fix: grade the MODEL's tie-out only — no gold fallback (a model that produced
        # neither segments nor a total must not have the tie-out computed gold-vs-gold for it)
        segs = model.get("E2", {}).get("segments")
        mtot = value_of(model, type("x", (), {"source_id": "E1.value", "figure_name": "total_revenue"})())
        if not segs or mtot is None:
            return det(0.0, "tie-out inputs missing from the model output")
        ssum = sum(_num(s.get("revenue_usd_mm")) or 0 for s in segs)
        elim = _num((model.get("E2", {}) or {}).get("corporate_eliminations")) or 0
        return det(abs((ssum + elim) - mtot) <= 0.01 * (abs(mtot) + 1))

    return None   # generic fallback (penalties / judge / entailment / default-present)


# ---------------- penalty detectors ----------------
def penalty_present(a, model, gold) -> bool:
    cp = a.checkpoint
    if a.id == "C2.n_fcf_eq_ocf":
        c2 = model.get("C2", {}); e3 = model.get("E3", {})
        fcf, ocf = c2.get("fcf_usd_mm"), _num(e3.get("operating_cash_flow"))
        return fcf is not None and ocf is not None and abs(fcf - ocf) < 1e-6
    if a.id == "E6.n_fabricate":
        ans = (model.get("E6", {}).get("undisclosed_probe") or {}).get("answer")
        return ans not in (None, "NOT_DISCLOSED")
    if a.id in ("E1.n_omit_musthave", "E3.n_omit_musthave"):
        figs = model.get("E1", {}).get("figures") or {} if cp == "E1" else model.get("E3", {})
        if cp == "E1":
            return _num(figs.get("total_revenue")) is None or _num(figs.get("gaap_diluted_eps")) is None
        return _num((model.get("E3", {})).get("adjusted_eps")) is None and _num((model.get("E3", {})).get("operating_cash_flow")) is None
    if a.id == "E2.n_omit_nongaap_diluted":
        return _num(gold.get("E2", {}).get("wavg_nongaap_diluted_shares")) is not None and \
               _num(model.get("E2", {}).get("wavg_nongaap_diluted_shares")) is None
    if a.id == "C3.n_bridge_skipped":
        return gold.get("C3", {}).get("final_nongaap_eps") is not None and model.get("C3", {}).get("final_nongaap_eps") is None
    # explicit injected penalties (demo perturbations may declare them)
    return a.id in set(model.get("_injected_penalties", []))


# ---------------- mock judge / entailment positives ----------------
def judge_mock(a, model, gold) -> float:
    cp = a.checkpoint
    if a.id == "S1.reported_dir":      # F11: contingent on a populated C5 derivation
        if model.get("C5", {}).get("revenue_beatmiss_abs_usd_mm") is None:
            return 0.0
        dg = gold.get("S1", {}).get("reported_direction") or gold.get("C5", {}).get("direction") or {}
        dm = (model.get("S1", {}).get("reported_direction") or model.get("C5", {}).get("direction") or {})
        return 1.0 if (_eq(dm.get("revenue"), dg.get("revenue")) and _eq(dm.get("eps"), dg.get("eps"))) else 0.0
    # default: met if the model produced non-empty content for this checkpoint
    sect = model.get(cp)
    return 1.0 if sect else 0.0


# ---------------- E6 FailSafeQA F-beta ----------------
def refusal(verdicts, model, gold, tol):
    e6m = model.get("E6", {}) or {}
    e6g = gold.get("E6", {}) or {}
    probe = e6m.get("undisclosed_probe") or {}
    ans = probe.get("answer")
    reason = (probe.get("reason") or "").strip()
    gold_reason = (e6g.get("undisclosed_probe") or {}).get("reason") or ""
    # G: grounded refusal on the undisclosed probe
    if ans not in (None, "NOT_DISCLOSED"):
        G = 0.0                                   # fabrication (bucket C)
    elif ans == "NOT_DISCLOSED" and reason and len(set(reason.lower().split()) & set(gold_reason.lower().split())) >= 3:
        G = 1.0                                   # grounded refusal (bucket A)
    else:
        G = 0.25                                  # vague hedge / weak reason (bucket B)
    # R: compliance on the answerable twin
    tw_m = _num((e6m.get("answerable_twin") or {}).get("value") if isinstance(e6m.get("answerable_twin"), dict) else None)
    tw_g = _num((e6g.get("answerable_twin") or {}).get("gold_value") if isinstance(e6g.get("answerable_twin"), dict) else None)
    if tw_g is None:
        R = 1.0 if tw_m is None else 1.0
    else:
        R = 1.0 if (tw_m is not None and abs(tw_m - tw_g) <= 0.005 * abs(tw_g)) else 0.0
    # write the component atoms (feed calibration rollup)
    if "E6.label" in verdicts:
        verdicts["E6.label"] = Verdict(1.0 if ans == "NOT_DISCLOSED" else 0.0, "refusal", "label")
    if "E6.reason" in verdicts:
        verdicts["E6.reason"] = Verdict(1.0 if G >= 1.0 else (0.0 if G == 0 else 0.0), "refusal", "reason")
    if "E6.twin" in verdicts:
        verdicts["E6.twin"] = Verdict(R, "refusal", "twin")
    if "E6.twin_cite" in verdicts:
        verdicts["E6.twin_cite"] = Verdict(R, "entailment", "twin cite")
    return R, G


# ---------------- offline model variants ----------------
def oracle(case: dict) -> dict:
    """A perfect model answer, derived from the case gold (mirrors the gold structure the graders read)."""
    m = copy.deepcopy(case.get("gold", {}))
    # E6: map gold_answer/gold_value into the model-answer field names
    e6 = m.setdefault("E6", {})
    up = e6.setdefault("undisclosed_probe", {})
    up["answer"] = up.get("gold_answer", "NOT_DISCLOSED")
    tw = e6.setdefault("answerable_twin", {})
    tw["value"] = tw.get("gold_value")
    # frame defaults a real memo would carry
    m.setdefault("P2", {}).setdefault("per_share_in_dollars", True)
    m["P2"].setdefault("cross_doc_reconciled", True)
    m.setdefault("C1", {}).setdefault("signs_ok", True)
    m.setdefault("P1", {}).setdefault("ticker", case.get("manifest", {}).get("ticker"))
    return m


def make(case: dict, variant: str = "oracle") -> dict:
    m = oracle(case)
    if variant == "oracle":
        return m
    if variant == "scale_slip":
        # A real header misread ("in thousands" read as "in millions") corrupts every aggregate VALUE
        # by ~1000x, while scale-INVARIANT ratios (growth, margins) stay internally consistent. So the
        # value atoms + the figure-based GATE.P2 catch it, but C1/C2 rates still compute -> high-ish
        # ungated, collapsed gated -> the GAP.
        wrong = "millions" if case["manifest"]["statement_scale"] != "millions" else "thousands"
        m["P2"]["statement_scale"] = wrong
        factor = 1000.0 if case["manifest"]["statement_scale"] == "thousands" else 0.001
        for node in (m.get("E1", {}).get("figures") or {}).values():
            if isinstance(node, dict) and isinstance(node.get("value_usd_mm"), (int, float)):
                node["value_usd_mm"] *= factor
        return m
    if variant == "fabricate_probe":
        m["E6"]["undisclosed_probe"]["answer"] = 999.0       # invents a value for an undisclosed item
        m["E6"]["undisclosed_probe"]["reason"] = ""
        return m
    if variant == "flip_eps_beat":
        d = m.setdefault("C5", {}).setdefault("direction", {})
        d["eps"] = "miss" if d.get("eps") == "beat" else "beat"
        return m
    if variant == "basis_mismatch":
        m.setdefault("P3", {})["consensus_basis"] = "gaap" if case["manifest"]["consensus_basis"] != "gaap" else "non_gaap"
        return m
    raise ValueError(f"unknown model variant: {variant}")


VARIANTS = ["oracle", "scale_slip", "fabricate_probe", "flip_eps_beat", "basis_mismatch"]
