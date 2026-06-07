"""
harness/models.py — produce a model's structured earnings-memo answer for a case.

Offline (spend-safe) models build the answer FROM the gold so the demo is deterministic and
reproducible, and named "flawed" variants inject specific, realistic analyst errors so the report
shows the gates / GAP / category rollup doing their job:

  oracle            — a perfect answer (-> ~AllPass)
  scale_slip        — misreads the statement header ("in thousands" as "in millions"): the one
                      mistake that fires GATE.P2 and collapses the gated score (high ungated -> big GAP)
  fabricate_probe   — invents a number for the genuinely-not-disclosed E6 probe (sycophancy):
                      E6 G=0 -> E6 headline (LLMC_beta) -> 0
  flip_eps_beat     — calls the EPS beat a miss: fires GATE.C5SIGN (in-checkpoint, C5 -> 0)
  basis_mismatch    — commits to a GAAP-vs-street consensus comparison: fires GATE.P3 (scoped -> C5,S1)

A LiveModel adapter (Anthropic / OpenAI) is sketched for a real run; the offline demo never calls it.
"""
from __future__ import annotations
import copy


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
        # misread the header scale; every figure value is still the right *number*, but the model
        # has the wrong scale frame -> P2.1 fails -> GATE.P2. (high ungated, collapsed gated -> GAP)
        wrong = "millions" if case["manifest"]["statement_scale"] != "millions" else "thousands"
        m["P2"]["statement_scale"] = wrong
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


class LiveModel:
    """Skeleton for a real run (not used in the offline demo). Build a prompt from the case inputs
    (the 10-Q + EX-99.1 text + the required output schema) and call the provider; parse JSON to the
    same structure `oracle()` returns. Requires an API key and will incur spend."""

    def __init__(self, provider: str, model: str):
        self.provider, self.model = provider, model

    def answer(self, case: dict) -> dict:   # pragma: no cover (live path)
        raise NotImplementedError(
            "LiveModel is a documented skeleton. Wire the Anthropic/OpenAI SDK here: feed the filing "
            "text + the output schema, call the model, parse JSON. Guarded off in the offline demo to "
            "respect the spend limit."
        )
