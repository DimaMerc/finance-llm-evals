"""finance-llm-evals harness — load the rubric + a gold case, grade a model's memo, score it.

Two suites share one engine: eval #1 (earnings-analysis) and eval #2 (defined-outcome-etf).
Cases route by their `suite:` field; each suite brings its rubric file, handlers, oracle and
designed-flaw variants (harness/suites/*).

Public API:
    from harness import run_case
    result, rubric = run_case("cases/snow-fy2026q2.case.yaml", variant="scale_slip")
    result, rubric = run_case("cases/koct-op2026-anchor.case.yaml", variant="free_lunch")
"""
from __future__ import annotations
import os
from .rubric import load_rubric, load_case, materialize, rubric_path_for
from .graders import grade
from .scoring import score
from . import suites

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run_case(case_path: str, variant: str = "oracle", mode: str = "mock", model_output: dict | None = None,
             endpoint: str | None = None, model_id: str | None = None):
    """Load a case, get a model answer (offline variant or a supplied dict), grade, and score.
    mode='llm' grades the free-form judge atoms with a real local LLM judge (LM Studio)."""
    case = load_case(case_path)
    rubric = load_rubric(rubric_path_for(case))
    suite = suites.for_case(case)
    atoms = materialize(rubric, case)
    answer = model_output if model_output is not None else suite.make(case, variant)
    gold = dict(case["gold"])
    gold["manifest"] = case.get("manifest", {})
    gold["_snapshot"] = case.get("snapshot")   # oracle inputs the graders may need (eval #2)
    gold["_claims"] = case.get("claims")
    judge_fn = None
    if mode == "llm":
        from .judge_llm import make_judge
        from .live import DEFAULT_ENDPOINT
        judge_fn = make_judge(endpoint=endpoint or DEFAULT_ENDPOINT, model_id=model_id, rubric=rubric,
                              memo_kind=getattr(suite, "MEMO_KIND", "an analyst's memo"))
    verdicts, refusal_RG = grade(atoms, answer, gold, rubric, suite, mode=mode, judge_fn=judge_fn)
    return score(atoms, verdicts, refusal_RG, rubric, case_id=case["case_id"],
                 refusal_cp=suite.REFUSAL_CP), rubric
