"""
harness/models.py — produce a model's structured answer for a case.

Offline (spend-safe) models build the answer FROM the gold so the demo is deterministic and
reproducible, and named "flawed" variants inject specific, realistic analyst errors so the report
shows the gates / GAP / category rollup doing their job. The variant sets are SUITE-SPECIFIC and
live in harness/suites/ (earnings.py / defined_outcome.py); this module routes by the case's
`suite:` field and keeps the LiveModel adapter sketch.

  eval #1: oracle | scale_slip | fabricate_probe | flip_eps_beat | basis_mismatch
  eval #2: oracle | vintage_slip | refscale_slip | feebasis_mix | free_lunch | fabricate_probe | c6_flip

A LiveModel adapter (Anthropic / OpenAI) is sketched for a real run; the offline demo never calls it.
"""
from __future__ import annotations
from . import suites


def make(case: dict, variant: str = "oracle") -> dict:
    return suites.for_case(case).make(case, variant)


def variants_for(case: dict) -> list:
    return suites.for_case(case).VARIANTS


# back-compat: the eval-#1 variant list (CLI help text)
VARIANTS = ["oracle", "scale_slip", "fabricate_probe", "flip_eps_beat", "basis_mismatch"]


class LiveModel:
    """Skeleton for a real run (not used in the offline demo). Build a prompt from the case inputs
    (the filings' text + the required output schema) and call the provider; parse JSON to the
    same structure the suite's oracle() returns. Requires an API key and will incur spend."""

    def __init__(self, provider: str, model: str):
        self.provider, self.model = provider, model

    def answer(self, case: dict) -> dict:   # pragma: no cover (live path)
        raise NotImplementedError(
            "LiveModel is a documented skeleton. Wire the Anthropic/OpenAI SDK here: feed the filing "
            "text + the output schema, call the model, parse JSON. Guarded off in the offline demo to "
            "respect the spend limit."
        )
