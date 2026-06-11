"""harness/suites — eval-specific grading suites.

A suite module supplies what the generic engine (harness/graders.py) and the CLI need:
REFUSAL_CP, LLM_JUDGE_CPS, handle(), penalty_present(), judge_mock(), refusal(), make(), VARIANTS.

Cases route by their `suite:` field; cases without one are eval #1 (earnings-analysis).
"""
from __future__ import annotations
from ..rubric import suite_of


def for_case(case: dict):
    if suite_of(case) == "defined-outcome-etf":
        from . import defined_outcome
        return defined_outcome
    from . import earnings
    return earnings
