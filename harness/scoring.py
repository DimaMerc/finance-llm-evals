"""
harness/scoring.py — aggregate atom verdicts into the rubric's scored report.

INNER (per checkpoint k): awarded = sum(met*points) over ALL atoms (met negatives subtract);
raw_pos = sum positive points; checkpoint_score = clip(awarded/raw_pos, 0, 1). The refusal
checkpoint (E6 in eval #1, E5 in eval #2 — supplied by the suite via run_case, defaulted E6) is
the exception: its headline is the FailSafeQA F-beta LLMC_beta(R, G), not the pool (rubric §2.2/§7).
CASE = sum_k W_k * checkpoint_score(k). Category rollup pools the same atoms by tag.
Gates set m=0 on dependent atoms (gated pass only); zeroed atoms stay in the denominator.

GATE FIRING IS DATA-DRIVEN (Phase-4 refactor): each gate in the rubric's `gates:` block declares
`fired_by` — one or more atom ids. A hook that is a POSITIVE atom fires its gate when UNMET
(met < 1); a hook that is a PENALTY atom (points < 0 in the rubric) fires when PRESENT (met >= 1).
Positive-hook gates are evaluated first in rubric order, then penalty-hook gates — reproducing the
original hardcoded ordering. A gate may declare `headline_flag` (e.g. GATE.FREELUNCH ->
free_lunch_fired): fired flags are surfaced on the Result beside the CaseScore.
"""
from __future__ import annotations
from dataclasses import dataclass, field


def _llmc_beta(R, G, beta):
    denom = beta * beta * G + R
    return 0.0 if denom == 0 else (1 + beta * beta) * R * G / denom


def _gated(atom, fired_gates, gate_specs):
    """is `atom` zeroed by any fired gate? (checkpoint-level or atom-id[:selector] dependents)"""
    for gid in fired_gates:
        for dep in gate_specs[gid].get("dependents", []) or []:
            base, sel = (dep.split(":", 1) + [None])[:2] if ":" in dep else (dep, None)
            if base == atom.checkpoint:
                return True
            if base == atom.source_id and (sel is None or (sel == "aggregate" and atom.tolerance == "aggregate")):
                return True
    return False


def _fired_gates(rubric, verdicts):
    """which gates fired, from the gates' own fired_by hooks (positive-hook gates first)."""
    atom_pts = {a["id"]: a.get("points", 0) for a in rubric["criteria"]}
    fired = []
    deferred = []   # penalty-hook gates evaluate after positive-hook gates (original ordering)
    for g in rubric["gates"]:
        hooks = g["fired_by"] if isinstance(g["fired_by"], list) else [g["fired_by"]]
        target = deferred if all(atom_pts.get(h, 0) < 0 for h in hooks) else fired
        fires = False
        for h in hooks:
            v = verdicts.get(h)
            if v is None:
                continue
            if atom_pts.get(h, 0) < 0:
                fires = fires or v.met >= 0.999       # penalty present
            else:
                fires = fires or v.met < 0.999        # positive gate atom unmet
        if fires:
            target.append(g["id"])
    return fired + deferred


@dataclass
class Result:
    case_id: str
    checkpoints: dict          # k -> {raw_pos, score_ungated, score_gated, raw_unclipped}
    categories: dict           # t -> rollup score (raw)
    case_ungated: float
    case_gated: float
    gap: float
    allpass: int
    fired_gates: list
    e6: tuple = field(default_factory=lambda: (0.0, 0.0))   # (R, G) for the refusal checkpoint
    refusal_cp: str = "E6"
    flags: list = field(default_factory=list)                # fired headline flags (e.g. free_lunch_fired)


def score(atoms, verdicts, e6_RG, rubric, case_id="case", beta=None, refusal_cp="E6"):
    meta = rubric["meta"]
    cpw = meta["checkpoint_weights"]
    beta = meta.get("refusal_beta", 0.5) if beta is None else beta
    gate_specs = {g["id"]: g for g in rubric["gates"]}
    R, G = e6_RG

    # ---- which gates fired? (data-driven from the rubric's fired_by hooks) ----
    fired = _fired_gates(rubric, verdicts)
    flags = [g["headline_flag"] for g in rubric["gates"] if g.get("headline_flag") and g["id"] in fired]

    # ---- per-checkpoint pooling ----
    cps = {}
    for k in cpw:
        sub = [a for a in atoms if a.checkpoint == k]
        raw_pos = sum(a.points for a in sub if a.points > 0)
        if k == refusal_cp:
            rh = _llmc_beta(R, G, beta)
            # a fired gate that lists the refusal checkpoint in its dependents (e.g. GATE.VINTAGE -> E5,
            # GATE.P1 -> E6) zeroes the gated headline too — the F-beta substitution is not a gate shield
            zeroed = any(k in (gate_specs[gid].get("dependents") or []) for gid in fired)
            cps[k] = dict(raw_pos=raw_pos, score_ungated=rh,
                          score_gated=0.0 if zeroed else rh, raw_unclipped=rh)
            continue
        aw_u = aw_g = 0.0
        for a in sub:
            v = verdicts.get(a.id)
            m = v.met if v else 0.0
            aw_u += m * a.points
            aw_g += (0.0 if _gated(a, fired, gate_specs) else m) * a.points
        raw_u = aw_u / raw_pos if raw_pos else 0.0
        cps[k] = dict(raw_pos=raw_pos,
                      score_ungated=max(0.0, min(1.0, raw_u)),
                      score_gated=max(0.0, min(1.0, aw_g / raw_pos)) if raw_pos else 0.0,
                      raw_unclipped=raw_u)

    case_u = sum(cpw[k] * cps[k]["score_ungated"] for k in cpw)
    case_g = sum(cpw[k] * cps[k]["score_gated"] for k in cpw)

    # ---- category rollup (ungated, the diagnostic) ----
    cats = {}
    for t in meta["weights"]:
        num = den = 0.0
        for a in atoms:
            if a.category != t:
                continue
            if a.points > 0:
                den += a.points
            v = verdicts.get(a.id)
            num += (v.met if v else 0.0) * a.points
        cats[t] = (num / den) if den else 0.0

    # ---- AllPass: no gate fired, every positive in-scope atom met, no penalty present, R=G=1 ----
    allpass = 1
    if fired:
        allpass = 0
    else:
        for a in atoms:
            if a.checkpoint == refusal_cp:
                continue
            v = verdicts.get(a.id)
            if a.points > 0 and (v is None or v.met < 0.999):
                allpass = 0; break
            if a.points < 0 and v is not None and v.met >= 0.999:
                allpass = 0; break
        if allpass and not (R >= 0.999 and G >= 0.999):
            allpass = 0

    return Result(case_id=case_id, checkpoints=cps, categories=cats,
                  case_ungated=round(case_u, 4), case_gated=round(case_g, 4),
                  gap=round(case_u - case_g, 4), allpass=allpass, fired_gates=fired, e6=(R, G),
                  refusal_cp=refusal_cp, flags=flags)
