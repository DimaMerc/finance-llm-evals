"""
harness/graders.py — grade each materialized atom: model answer vs case gold -> met fraction.

The model output MIRRORS the case `gold:` structure (same keys), so value atoms resolve by the same
path in both dicts. Grading tiers:
  * deterministic  — exact: numeric value within the atom's tolerance band (scale-folded), or a
                     frame/enum/sign equality. ALL gating decisions are here.
  * entailment     — mock: the model's citation verbatim overlaps the gold verbatim (token Jaccard)
                     and the document matches. (LLM NLI grader is the online swap.)
  * judge          — mock: section present + key gold items covered; penalties off unless detected.
                     (judge.md prompt is the online swap.)
  * refusal (E6)   — derive the FailSafeQA bucket from the model's E6 answer -> R, G -> LLMC_beta.

Returns: dict atom_id -> Verdict, plus e6_RG = (R, G), plus the set of fired in-checkpoint/gate atoms.
"""
from __future__ import annotations
from dataclasses import dataclass
from .tolerances import within


@dataclass
class Verdict:
    met: float           # 0..1 (binary for most; sub-atom expansion gives the partial)
    kind: str            # deterministic | entailment | judge | refusal
    note: str = ""


# ---------------- value extraction (works on gold- and model-shaped dicts) ----------------
def _num(node):
    if node is None:
        return None
    if isinstance(node, dict):
        v = node.get("value_usd_mm", node.get("value"))
        return float(v) if isinstance(v, (int, float)) else None
    if isinstance(node, (int, float)):
        return float(node)
    return None


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


def _cite_overlap(mcite, gcite) -> bool:
    if not isinstance(mcite, dict) or not isinstance(gcite, dict):
        return False
    if (mcite.get("document") or "").strip() and gcite.get("document"):
        if mcite["document"] != gcite["document"]:
            return False
    mv, gv = (mcite.get("verbatim") or ""), (gcite.get("verbatim") or "")
    if not mv or not gv:
        return False
    a, b = set(mv.lower().split()), set(gv.lower().split())
    if not a or not b:
        return False
    return len(a & b) / len(a | b) >= 0.5


def _gold_cite(gold, atom):
    """best-effort gold citation node for an entailment atom."""
    sid, fn = atom.source_id, atom.figure_name
    if sid == "E1.cite":
        return (gold.get("E1", {}).get("figures") or {}).get(fn, {}).get("citation")
    g = {"P1.5": gold.get("P1", {}), "P2.5": gold.get("P2", {})}.get(atom.id)
    if g is not None:
        return g.get("citation")
    return None


# ---------------- frame / boolean handlers (deterministic) ----------------
def _eq(a, b):
    return a is not None and b is not None and str(a).strip() == str(b).strip()


def grade(atoms, model, gold, rubric, mode="mock"):
    """grade every materialized atom. mode 'mock' = offline; 'llm' would call judge/entailment graders."""
    tol = rubric["tolerances"]
    P1g, P2g, P3g = gold.get("P1", {}), gold.get("P2", {}), gold.get("P3", {})
    P1m, P2m, P3m = model.get("P1", {}), model.get("P2", {}), model.get("P3", {})
    verdicts: dict[str, Verdict] = {}

    # effective tax rate level (for the tax_rate_delta_pp floor-RSS band)
    eff_level = (model.get("C4", {}) or {}).get("effective_tax_rate")

    def det(met, note=""):
        return Verdict(float(met), "deterministic", note)

    for a in atoms:
        sid = a.source_id
        # ---------- per_figure / calc VALUE atoms ----------
        if sid in ("E1.value", "E2.segments", "E3.addbacks", "E3.ocf_capex", "E4.ranges", "E5.values"):
            gv, mv = value_of(gold, a), value_of(model, a)
            if gv is None:
                verdicts[a.id] = det(1.0, "figure N/A in gold")   # pruned figures don't reach here
                continue
            verdicts[a.id] = det(within(mv, gv, a.tolerance, tol), f"{mv} vs {gv}")
            continue
        if sid in ("E1.cite", "P1.5", "P2.5"):
            gc = _gold_cite(gold, a)
            mc = None
            if sid == "E1.cite":
                mc = (model.get("E1", {}).get("figures") or {}).get(a.figure_name, {}).get("citation")
            elif sid == "P1.5":
                mc = P1m.get("citation")
            elif sid == "P2.5":
                mc = P2m.get("citation")
            verdicts[a.id] = Verdict(1.0 if _cite_overlap(mc, gc) else 0.0, "entailment", "cite overlap")
            continue

        # ---------- planning frame / gate atoms ----------
        if a.id == "P1.1":
            verdicts[a.id] = det(_eq(P1m.get("issuer"), P1g.get("issuer")) and _eq(P1m.get("ticker"), P1g.get("ticker")) or _eq(P1m.get("ticker"), gold["manifest"].get("ticker")))
            continue
        if a.id == "P1.2":      # GATE.P1
            ok = _eq(P1m.get("fiscal_period_label"), P1g.get("fiscal_period_label")) and _eq(P1m.get("period_end_date"), P1g.get("period_end_date"))
            verdicts[a.id] = det(ok, "period match (gate)")
            continue
        if a.id == "P1.3":
            verdicts[a.id] = det(_eq(P1m.get("filing_type"), P1g.get("filing_type")))
            continue
        if a.id == "P2.1":      # GATE.P2
            verdicts[a.id] = det(_eq(P2m.get("statement_scale"), P2g.get("statement_scale")), "scale match (gate)")
            continue
        if a.id == "P2.2":
            verdicts[a.id] = det(_eq(P2m.get("reporting_currency", "USD"), P2g.get("reporting_currency", "USD")))
            continue
        if a.id == "P2.3":
            verdicts[a.id] = det(P2m.get("per_share_in_dollars", True) is True)
            continue
        if a.id == "P2.4":
            verdicts[a.id] = det(P2m.get("cross_doc_reconciled", True) is True)
            continue
        if a.id == "P3.3":      # GATE.P3 (scoped)
            ok = _eq(P3m.get("consensus_basis"), P3g.get("consensus_basis")) and _eq(P3m.get("consensus_statistic"), P3g.get("consensus_statistic"))
            verdicts[a.id] = det(ok, "consensus basis (scoped gate)")
            continue

        # ---------- E2 shares ----------
        if a.id == "E2.wavg_diluted":
            verdicts[a.id] = det(within(_num(model.get("E2", {}).get("wavg_gaap_diluted_shares")), _num(gold.get("E2", {}).get("wavg_gaap_diluted_shares")), "aggregate", tol))
            continue
        if a.id == "E2.nongaap_diluted":
            gv = _num(gold.get("E2", {}).get("wavg_nongaap_diluted_shares"))
            if gv is None:
                verdicts[a.id] = det(1.0, "no separate non-GAAP diluted (== GAAP)")
            else:
                verdicts[a.id] = det(within(_num(model.get("E2", {}).get("wavg_nongaap_diluted_shares")), gv, "aggregate", tol))
            continue
        if a.id == "E2.prioryr_shares":
            verdicts[a.id] = det(within(_num(model.get("E2", {}).get("prior_year_diluted_shares")), _num(gold.get("E2", {}).get("prior_year_diluted_shares")), "aggregate", tol))
            continue
        if a.id == "E3.taxeffect_line":
            gv = _num(gold.get("E3", {}).get("tax_effect_of_adjustments"))
            if gv is None:
                verdicts[a.id] = det(1.0, "no separate tax-effect line")
            else:
                verdicts[a.id] = det(within(_num(model.get("E3", {}).get("tax_effect_of_adjustments")), gv, "aggregate", tol))
            continue

        # ---------- calculations ----------
        if a.id == "C1.yoy_qoq":
            c1m, c1g = model.get("C1", {}), gold.get("C1", {})
            ok = within(c1m.get("yoy_revenue_pct"), c1g.get("yoy_revenue_pct"), "growth_rate", tol) and \
                 within(c1m.get("qoq_revenue_pct"), c1g.get("qoq_revenue_pct"), "growth_rate", tol)
            verdicts[a.id] = det(ok)
            continue
        if a.id == "C1.dshares":
            verdicts[a.id] = det(within(model.get("C1", {}).get("yoy_diluted_share_change_pct"), gold.get("C1", {}).get("yoy_diluted_share_change_pct"), "growth_rate", tol))
            continue
        if a.id == "C1.sign":   # GATE.C1SIGN
            verdicts[a.id] = det(model.get("C1", {}).get("signs_ok", True) is True, "growth sign (in-checkpoint)")
            continue
        if a.id == "C2.levels":
            c2m, c2g = model.get("C2", {}), gold.get("C2", {})
            checks = []
            for mk in ("operating_margin", "net_margin"):
                if c2g.get(mk) is not None:
                    checks.append(within(c2m.get(mk), c2g.get(mk), "margin_level", tol))
            gm = c2g.get("gross_margin")
            if isinstance(gm, (int, float)):
                checks.append(within(c2m.get("gross_margin"), gm, "margin_level", tol))
            verdicts[a.id] = det(all(checks) if checks else 1.0)
            continue
        if a.id == "C2.deltas_bps":
            c2m, c2g = model.get("C2", {}), gold.get("C2", {})
            dg = c2g.get("margin_deltas_bps") or {}
            dm = c2m.get("margin_deltas_bps") or {}
            checks = [within(dm.get(k), dg.get(k), "margin_delta_bps", tol) for k in dg if isinstance(dg.get(k), (int, float))]
            verdicts[a.id] = det(all(checks) if checks else 1.0)
            continue
        if a.id == "C2.fcf":
            verdicts[a.id] = det(within(model.get("C2", {}).get("fcf_usd_mm"), gold.get("C2", {}).get("fcf_usd_mm"), "fcf", tol))
            continue
        if a.id == "C3.final":
            gv = gold.get("C3", {}).get("final_nongaap_eps")
            verdicts[a.id] = det(1.0 if gv is None else within(model.get("C3", {}).get("final_nongaap_eps"), gv, "eps", tol))
            continue
        if sid == "C3.addbacks_steps":
            i = int(a.figure_name.split("_")[1])
            grows = (gold.get("E3", {}).get("addbacks") or [])
            mrows = (model.get("E3", {}).get("addbacks") or [])
            gv = _num(grows[i].get("value_usd_mm")) if i < len(grows) else None
            mv = _num(mrows[i].get("value_usd_mm")) if i < len(mrows) else None
            verdicts[a.id] = det(1.0 if gv is None else within(mv, gv, "aggregate", tol))
            continue
        if a.id == "C4.efftax_level":
            verdicts[a.id] = det(within(model.get("C4", {}).get("effective_tax_rate"), gold.get("C4", {}).get("effective_tax_rate"), "ratio", tol))
            continue
        if a.id == "C4.efftax_delta":
            verdicts[a.id] = det(within(model.get("C4", {}).get("efftax_yoy_delta_pp"), gold.get("C4", {}).get("efftax_yoy_delta_pp"), "tax_rate_delta_pp", tol, level_value=eff_level))
            continue
        if a.id == "C4.dso_dio":
            gv = gold.get("C4", {}).get("dso")
            verdicts[a.id] = det(1.0 if gv is None else within(model.get("C4", {}).get("dso"), gv, "ratio", tol))
            continue
        if a.id == "C4.ocf_ni":
            verdicts[a.id] = det(within(model.get("C4", {}).get("ocf_to_net_income"), gold.get("C4", {}).get("ocf_to_net_income"), "ratio", tol))
            continue
        if a.id == "C5.beatmiss":
            c5m, c5g = model.get("C5", {}), gold.get("C5", {})
            ok = within(c5m.get("revenue_beatmiss_abs_usd_mm"), c5g.get("revenue_beatmiss_abs_usd_mm"), "beat_miss_rev", tol) and \
                 within(c5m.get("eps_beatmiss_abs"), c5g.get("eps_beatmiss_abs"), "beat_miss_eps", tol)
            verdicts[a.id] = det(ok)
            continue
        if a.id == "C5.direction":   # GATE.C5SIGN
            dg, dm = gold.get("C5", {}).get("direction") or {}, model.get("C5", {}).get("direction") or {}
            verdicts[a.id] = det(_eq(dm.get("revenue"), dg.get("revenue")) and _eq(dm.get("eps"), dg.get("eps")), "beat/miss sign (in-checkpoint)")
            continue
        if a.id == "C5.tieout":
            segs = model.get("E2", {}).get("segments") or gold.get("E2", {}).get("segments") or []
            tot = value_of(model, type("x", (), {"source_id": "E1.value", "figure_name": "total_revenue"})()) \
                  or _num((gold.get("E1", {}).get("figures") or {}).get("total_revenue"))
            ssum = sum(_num(s.get("revenue_usd_mm")) or 0 for s in segs)
            elim = _num((model.get("E2", {}) or {}).get("corporate_eliminations")) or 0
            verdicts[a.id] = det(abs((ssum + elim) - (tot or 0)) <= 0.01 * (abs(tot) + 1))
            continue

        # ---------- E6 refusal handled below (placeholder met for label/reason/twin set later) ----------
        if a.checkpoint == "E6" and a.grader == "refusal":
            verdicts[a.id] = Verdict(0.0, "refusal", "set by e6")  # filled in by e6 pass
            continue

        # ---------- PENALTIES (deterministic detectors; default not-present) ----------
        if a.points < 0:
            present = _penalty_present(a, model, gold)
            verdicts[a.id] = Verdict(1.0 if present else 0.0, a.grader, "penalty")
            continue

        # ---------- everything else (deterministic 'present', judge/entailment positives) ----------
        if a.grader in ("judge", "entailment"):
            verdicts[a.id] = Verdict(_judge_mock(a, model, gold), a.grader, "mock")
        else:
            verdicts[a.id] = det(1.0, "default-present")

    # ---- E6 refusal: bucket -> R, G -> LLMC_beta (filled into label/reason/twin atoms) ----
    R, G = _grade_e6(verdicts, model, gold)
    return verdicts, (R, G)


# ---------------- penalty detectors ----------------
def _penalty_present(a, model, gold) -> bool:
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
def _judge_mock(a, model, gold) -> float:
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
def _grade_e6(verdicts, model, gold):
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
