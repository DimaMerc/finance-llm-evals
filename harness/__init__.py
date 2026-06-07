"""finance-llm-evals harness — load the rubric + a gold case, grade a model's earnings memo, score it.

Public API:
    from harness import run_case
    result = run_case("cases/snow-fy2026q2.case.yaml", variant="scale_slip")
"""
from __future__ import annotations
import os
from .rubric import load_rubric, load_case, materialize
from .graders import grade
from .scoring import score
from . import models

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run_case(case_path: str, variant: str = "oracle", mode: str = "mock", model_output: dict | None = None):
    """Load a case, get a model answer (offline variant or a supplied dict), grade, and score."""
    rubric = load_rubric()
    case = load_case(case_path)
    atoms = materialize(rubric, case)
    answer = model_output if model_output is not None else models.make(case, variant)
    gold = dict(case["gold"]); gold["manifest"] = case.get("manifest", {})
    verdicts, e6_RG = grade(atoms, answer, gold, rubric, mode=mode)
    return score(atoms, verdicts, e6_RG, rubric, case_id=case["case_id"]), rubric
