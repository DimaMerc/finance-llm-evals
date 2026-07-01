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

# suite key (case `suite:` field) -> criteria file. Cases without a suite field are eval #1.
SUITE_RUBRICS = {
    "earnings-analysis": "criteria.yaml",
    "defined-outcome-etf": "criteria-defined-outcome.yaml",
    "dcf-valuation": "criteria-dcf.yaml",
    "creation-redemption": "criteria-creation-redemption.yaml",
    "confirmation-matching": "criteria-confirmation-matching.yaml",
}
DEFAULT_SUITE = "earnings-analysis"


def suite_of(case: dict) -> str:
    return case.get("suite") or DEFAULT_SUITE


def rubric_path_for(case: dict) -> str:
    return os.path.join(REPO, "rubric", SUITE_RUBRICS[suite_of(case)])


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


# expand key -> (manifest expand_counts key, materialized id suffix, figure_name prefix)
# eval-#1 suffixes are preserved exactly (.seg{i} / .row{i}) so atom ids stay byte-stable.
_EXPANSIONS = {
    "per_segment_row": ("segment_rows", "seg", "segment"),
    "per_addback_row": ("addback_rows", "row", "addback"),
    "per_bridge_row":  ("addback_rows", "row", "addback"),
    "per_leg_row":     ("leg_rows", "row", "leg"),
    "per_grid_row":    ("grid_rows", "row", "grid"),
    "per_claim_row":   ("claim_rows", "row", "claim"),
    # eval #3 (DCF) additions — additive, byte-invariant for evals #1-2:
    "per_year_row":    ("year_rows", "year", "year"),    # C1.fcff / C3.pv (one per projected year)
    "per_grid_cell":   ("grid_cells", "cell", "cell"),   # C7.grid (WACC x g sensitivity cells)
}


def _manifest_params(case: dict):
    """expand-row counts and the prune set (figure_names marked N/A for this case)."""
    man = case.get("manifest", {}) or {}
    counts = {k: int(v or 0) for k, v in (man.get("expand_counts", {}) or {}).items()}
    na = set(man.get("na_figures", []) or [])
    return counts, na


def materialize(rubric: dict, case: dict) -> list[Atom]:
    """Expand the rubric's atoms into the concrete per-case atom set (split + prune)."""
    counts, na = _manifest_params(case)
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
                if exp in _EXPANSIONS:
                    ckey, suffix, prefix = _EXPANSIONS[exp]
                    n = counts.get(ckey, 0)
                    for i in range(n):
                        out.append(Atom(id=f"{a['id']}.{suffix}{i}", points=pts / n if n else 0.0,
                                        tolerance=tk, figure_name=f"{prefix}_{i}", **base))
                else:
                    if a.get("prune") == "per_manifest" and nm in na:
                        continue  # PRUNE: figure removed from num+denom (F6)
                    out.append(Atom(id=f"{a['id']}.{nm}", points=pts, tolerance=tk,
                                    figure_name=nm, **base))
        else:
            # (C3.addbacks_steps is per_figure in criteria.yaml and expands above — no special case)
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
    counts, napos = _manifest_params(case)
    print(f"manifest: expand_counts={counts} na_figures={sorted(napos)}")
