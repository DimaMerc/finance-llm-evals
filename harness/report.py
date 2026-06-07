"""harness/report.py — render a scored Result as a readable text report."""
from __future__ import annotations


def render(result, rubric, *, variant="", mode="mock") -> str:
    cpw = rubric["meta"]["checkpoint_weights"]
    L = []
    L.append("=" * 72)
    L.append(f"  CASE {result.case_id}    model={variant or 'n/a'}    judge={mode}")
    L.append("=" * 72)
    L.append(f"  CaseScore (gated, headline) : {result.case_gated:.3f}")
    L.append(f"  CaseScore (ungated)         : {result.case_ungated:.3f}")
    L.append(f"  GAP (ungated - gated)       : {result.gap:.3f}")
    L.append(f"  AllPass                     : {result.allpass}")
    R, G = result.e6
    L.append(f"  E6 calibration (R,G->F_b)   : R={R:.2f} G={G:.2f} -> {result.checkpoints['E6']['score_gated']:.3f}")
    L.append(f"  Gates fired                 : {', '.join(result.fired_gates) or 'none'}")
    L.append("")
    L.append("  Checkpoint vector (which step failed):")
    L.append("    cp   W      ungated  gated   raw")
    for k in cpw:
        c = result.checkpoints[k]
        flag = "  <-- gated" if c["score_gated"] + 1e-9 < c["score_ungated"] else ""
        L.append(f"    {k:<4} {cpw[k]:.3f}  {c['score_ungated']:.3f}   {c['score_gated']:.3f}  {c['raw_unclipped']:+.2f}{flag}")
    L.append("")
    L.append("  Category rollup (diagnostic -- what KIND of error):")
    for t, v in result.categories.items():
        bar = "#" * max(0, min(20, int(round(v * 20))))
        L.append(f"    {t:<12} {v:+.3f}  {bar}")
    L.append("=" * 72)
    return "\n".join(L)
