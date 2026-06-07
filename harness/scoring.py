"""
harness/scoring.py — aggregate atom verdicts into the rubric's scored report.

INNER (per checkpoint k): awarded = sum(met*points) over ALL atoms (met negatives subtract);
raw_pos = sum positive points; checkpoint_score = clip(awarded/raw_pos, 0, 1). E6 is the exception:
its headline is the FailSafeQA F-beta LLMC_beta(R, G), not the pool (rubric §2.2/§7).
CASE = sum_k W_k * checkpoint_score(k). Category rollup pools the same atoms by tag.
Gates set m=0 on dependent atoms (gated pass only); zeroed atoms stay in the denominator.
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
    e6: tuple = field(default_factory=lambda: (0.0, 0.0))


def score(atoms, verdicts, e6_RG, rubric, case_id="case", beta=None):
    meta = rubric["meta"]
    cpw = meta["checkpoint_weights"]
    beta = meta.get("refusal_beta", 0.5) if beta is None else beta
    gate_specs = {g["id"]: g for g in rubric["gates"]}
    R, G = e6_RG

    # ---- which gates fired? (positive gate atoms: fire when NOT met; FABRICATION: when a hook is present) ----
    fired = []
    pos_gate_atom = {"GATE.P1": "P1.2", "GATE.P2": "P2.1", "GATE.P3": "P3.3",
                     "GATE.C1SIGN": "C1.sign", "GATE.C5SIGN": "C5.direction"}
    for gid, aid in pos_gate_atom.items():
        v = verdicts.get(aid)
        if v is not None and v.met < 0.999:
            fired.append(gid)
    for hook in gate_specs["GATE.FABRICATION"].get("fired_by", []):
        if verdicts.get(hook) and verdicts[hook].met >= 0.999:
            fired.append("GATE.FABRICATION")
            break

    # ---- per-checkpoint pooling ----
    cps = {}
    for k in cpw:
        sub = [a for a in atoms if a.checkpoint == k]
        raw_pos = sum(a.points for a in sub if a.points > 0)
        if k == "E6":
            e6h = _llmc_beta(R, G, beta)
            cps[k] = dict(raw_pos=raw_pos, score_ungated=e6h, score_gated=e6h, raw_unclipped=e6h)
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

    # ---- AllPass: no gate fired, every positive in-scope atom met, no penalty present, E6 R=G=1 ----
    allpass = 1
    if fired:
        allpass = 0
    else:
        for a in atoms:
            if a.checkpoint == "E6":
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
                  gap=round(case_u - case_g, 4), allpass=allpass, fired_gates=fired, e6=(R, G))
