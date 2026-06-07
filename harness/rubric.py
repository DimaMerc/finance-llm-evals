"""
harness/rubric.py — load criteria.yaml + a case, and MATERIALIZE the per-case atom set.

The rubric's per_figure templates are expanded into concrete sub-atoms using the case manifest
(segment / add-back counts via SPLIT semantics; N/A figures PRUNED from num+denom). This mirrors
rubric/worked_example.py exactly, generalized so the harness can grade any case.

A materialized atom carries everything the grader and the scorer need:
  id, checkpoint, category, points, grader, gate, tolerance, tags, figure_name, source_id
"""
from __future__ import annotations
import os
import yaml
from dataclasses import dataclass, field

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
RUBRIC_PATH = os.path.join(REPO, "rubric", "criteria.yaml")


@dataclass
class Atom:
    id: str                      # materialized id (e.g. E1.value.total_revenue)
    source_id: str               # the template/atom id in criteria.yaml (e.g. E1.value)
    checkpoint: str
    category: str
    points: float
    grader: str                  # deterministic | entailment | judge | refusal
    gate: str                    # none | hard | scoped | in_checkpoint
    tolerance: str | None = None
    tags: list = field(default_factory=list)
    figure_name: str | None = None   # for per_figure sub-atoms


def load_rubric(path: str = RUBRIC_PATH) -> dict:
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def load_case(path: str) -> dict:
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _manifest_params(case: dict):
    """N_segments, N_addbacks, and the prune set (figure_names marked N/A for this case)."""
    man = case.get("manifest", {}) or {}
    counts = man.get("expand_counts", {}) or {}
    n_seg = int(counts.get("segment_rows", 0) or 0)
    n_add = int(counts.get("addback_rows", 0) or 0)
    na = set(man.get("na_figures", []) or [])
    return n_seg, n_add, na


def materialize(rubric: dict, case: dict) -> list[Atom]:
    """Expand the rubric's atoms into the concrete per-case atom set (split + prune)."""
    n_seg, n_add, na = _manifest_params(case)
    out: list[Atom] = []
    for a in rubric["criteria"]:
        base = dict(
            source_id=a["id"], checkpoint=a["checkpoint"], category=a["category"],
            grader=a["grader"], gate=a.get("gate", "none"), tags=a.get("tags", []),
        )
        if a.get("per_figure"):
            for f in a["figures"]:
                nm, pts, tk = f["figure_name"], f["points"], f.get("tolerance_key")
                exp = f.get("expand")
                if exp == "per_segment_row":
                    n = n_seg
                    for i in range(n):
                        out.append(Atom(id=f"{a['id']}.seg{i}", points=pts / n if n else 0.0,
                                        tolerance=tk, figure_name=f"segment_{i}", **base))
                elif exp in ("per_addback_row", "per_bridge_row"):
                    n = n_add
                    for i in range(n):
                        out.append(Atom(id=f"{a['id']}.row{i}", points=pts / n if n else 0.0,
                                        tolerance=tk, figure_name=f"addback_{i}", **base))
                else:
                    if a.get("prune") == "per_manifest" and nm in na:
                        continue  # PRUNE: figure removed from num+denom (F6)
                    out.append(Atom(id=f"{a['id']}.{nm}", points=pts, tolerance=tk,
                                    figure_name=nm, **base))
        else:
            # C3 bridge step pool also splits per add-back row (F3)
            if a["id"] == "C3.addbacks_steps":
                n = n_add
                for i in range(n):
                    out.append(Atom(id=f"{a['id']}.row{i}", points=a["points"] / n if n else 0.0,
                                    tolerance=a.get("tolerance"), figure_name=f"addback_{i}", **base))
            else:
                out.append(Atom(id=a["id"], points=a["points"], tolerance=a.get("tolerance"), **base))
    return out


def gate_index(rubric: dict) -> dict:
    """id -> gate spec, for the scorer."""
    return {g["id"]: g for g in rubric["gates"]}


if __name__ == "__main__":
    import sys
    rub = load_rubric()
    case_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(REPO, "cases", "blk-2025q3.case.yaml")
    case = load_case(case_path)
    atoms = materialize(rub, case)
    pos = sum(a.points for a in atoms if a.points > 0)
    neg = sum(a.points for a in atoms if a.points < 0)
    by_g = {}
    for a in atoms:
        by_g[a.grader] = by_g.get(a.grader, 0) + 1
    print(f"case {case['case_id']}: {len(atoms)} materialized atoms | +{pos:.1f} / {neg:.1f}")
    print("by grader:", by_g)
    n_seg, n_add, napos = _manifest_params(case)
    print(f"manifest: segments={n_seg} addbacks={n_add} na_figures={sorted(napos)}")
