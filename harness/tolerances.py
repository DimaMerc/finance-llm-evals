"""
harness/tolerances.py — deterministic tolerance-band checks (rubric/criteria.yaml `tolerances:`).

Scale is folded into the number BEFORE comparison: the harness normalizes both the model value and
the gold value to a common base (USD millions for aggregates, dollars for per-share) so a
thousands-vs-millions misread deterministically fails the band. The locked scale (P2) is what the
model used to interpret the raw figure; we model a scale slip by the model reporting a value off by
the scale ratio (e.g., reads "in thousands" as "in millions" -> value 1000x too large).
"""
from __future__ import annotations


def _rel_or_exact(model, gold, band, or_exact=False):
    if model is None or gold is None:
        return False
    if or_exact and abs(model - gold) < 1e-9:
        return True
    denom = abs(gold) if abs(gold) > 1e-12 else 1.0
    return abs(model - gold) / denom <= band


def within(model, gold, tol_key: str, tol_specs: dict, *, level_value=None) -> bool:
    """True iff model is within the tol_key band of gold. None gold => figure not graded (caller skips)."""
    if tol_key is None:
        # non-numeric deterministic atom; caller handles equality elsewhere
        return model == gold
    spec = tol_specs.get(tol_key)
    if spec is None:
        return False
    if model is None or gold is None:
        return False
    t = spec["type"]
    if t == "abs":                       # eps, beat_miss_eps
        return abs(model - gold) <= spec["band"] + 1e-12
    if t == "pp":                        # growth_rate, margin_level (values expressed in percentage points)
        return abs(model - gold) <= spec["band"] + 1e-12
    if t == "bps":                       # margin_delta_bps (values in bps)
        return abs(model - gold) <= spec["band"] + 1e-9
    if t in ("rel",):                    # aggregate, fcf, ratio, beat_miss_rev
        return _rel_or_exact(model, gold, spec["band"], spec.get("or_exact", False))
    if t == "pp_floor_rss":              # tax_rate_delta_pp (F12): floor-RSS, rate-dependent
        rate = abs(level_value) if level_value is not None else 0.21
        band = max(spec["floor_pp"], spec["rel_per_level"] * rate * spec["rss_factor"] * 100.0)
        # level_value is a fraction (e.g. 0.21); rel band in pp -> *100 to compare pp deltas
        return abs(model - gold) <= band + 1e-9
    return False


def scale_factor(scale: str) -> float:
    """USD-millions normalization factor for a reporting scale."""
    return {"thousands": 1e-3, "millions": 1.0, "as_reported": 1.0}.get(scale, 1.0)
