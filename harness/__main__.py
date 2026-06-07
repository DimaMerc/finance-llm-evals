"""
harness/__main__.py — CLI.

  python -m harness list
  python -m harness run  --case cases/snow-fy2026q2.case.yaml [--model scale_slip] [--all]
  python -m harness demo                       # the canonical oracle-vs-scale-slip contrast on SNOW
  python -m harness suite [--model oracle]      # score every case in cases/

`--judge mock` (default, offline/no-API) grades the entailment/judge/refusal atoms heuristically;
`--judge llm` is the (spend-incurring) live swap. The deterministic core + all gating are exact in
both modes.
"""
from __future__ import annotations
import argparse
import glob
import os
from . import run_case, REPO, models
from .report import render

CASES_DIR = os.path.join(REPO, "cases")


def _cases():
    return sorted(p for p in glob.glob(os.path.join(CASES_DIR, "*.case.yaml"))
                  if not os.path.basename(p).startswith("_"))


def _resolve(case_arg: str) -> str:
    if os.path.exists(case_arg):
        return case_arg
    for p in _cases():
        if case_arg in os.path.basename(p):
            return p
    raise SystemExit(f"case not found: {case_arg}\navailable: {[os.path.basename(p) for p in _cases()]}")


def cmd_list(_):
    print("Cases:")
    for p in _cases():
        print("  -", os.path.basename(p).replace(".case.yaml", ""))
    print("Model variants:", ", ".join(models.VARIANTS))


def cmd_run(a):
    path = _resolve(a.case)
    variants = models.VARIANTS if a.all else [a.model]
    for v in variants:
        result, rubric = run_case(path, variant=v, mode=a.judge)
        print(render(result, rubric, variant=v, mode=a.judge))


def cmd_suite(a):
    rows = []
    for p in _cases():
        result, rubric = run_case(p, variant=a.model, mode=a.judge)
        rows.append((os.path.basename(p).replace(".case.yaml", ""), result))
        print(render(result, rubric, variant=a.model, mode=a.judge))
    print("\nSUITE SUMMARY  (model=%s, judge=%s)" % (a.model, a.judge))
    print("  case                  gated   ungated   GAP    AllPass")
    for name, r in rows:
        print(f"  {name:<20}  {r.case_gated:.3f}   {r.case_ungated:.3f}    {r.gap:.3f}   {r.allpass}")
    if rows:
        n = len(rows)
        print(f"  {'SUITE MEAN':<20}  {sum(r.case_gated for _,r in rows)/n:.3f}   "
              f"{sum(r.case_ungated for _,r in rows)/n:.3f}    {sum(r.gap for _,r in rows)/n:.3f}   "
              f"{sum(r.allpass for _,r in rows)/n:.2f}")


def cmd_selftest(_):
    """Regression guard: oracle must AllPass at 1.0; the gate tiers must open the expected GAPs."""
    failures = []
    for p in _cases():
        name = os.path.basename(p).replace(".case.yaml", "")
        oracle, _ = run_case(p, variant="oracle")
        if not (oracle.allpass == 1 and abs(oracle.case_gated - 1.0) < 1e-6 and oracle.gap == 0.0):
            failures.append(f"{name}: oracle expected 1.0/AllPass, got gated={oracle.case_gated} allpass={oracle.allpass}")
        ss, _ = run_case(p, variant="scale_slip")
        if not ("GATE.P2" in ss.fired_gates and ss.gap > 0.4 and ss.allpass == 0):
            failures.append(f"{name}: scale_slip expected GATE.P2 + GAP>0.4, got gates={ss.fired_gates} gap={ss.gap}")
        fp, _ = run_case(p, variant="fabricate_probe")
        if not (fp.e6[1] == 0.0 and fp.checkpoints["E6"]["score_gated"] == 0.0 and fp.allpass == 0):
            failures.append(f"{name}: fabricate_probe expected E6->0 (G=0), got E6={fp.checkpoints['E6']['score_gated']}")
        bm, _ = run_case(p, variant="basis_mismatch")
        if "GATE.P3" not in bm.fired_gates:
            failures.append(f"{name}: basis_mismatch expected GATE.P3 (scoped), got {bm.fired_gates}")
    if failures:
        print("SELFTEST FAILED:")
        for f in failures:
            print("  -", f)
        raise SystemExit(1)
    print(f"SELFTEST PASSED: {len(_cases())} cases x oracle/scale_slip/fabricate_probe/basis_mismatch invariants hold.")


def cmd_demo(_):
    path = _resolve("snow")
    print("DEMO — Snowflake FQ2'26 (in thousands). A model that does the analysis correctly but")
    print("misreads the statement header scale: the one error that poisons everything downstream.\n")
    for v in ("oracle", "scale_slip"):
        result, rubric = run_case(path, variant=v, mode="mock")
        print(render(result, rubric, variant=v, mode="mock"))
    print("\nThe scale_slip model keeps a HIGH ungated score (its arithmetic is internally consistent)")
    print("but GATE.P2 collapses the gated score — the GAP is exactly the diagnostic the eval exists to")
    print("surface: 'can do the math, cannot be trusted to read a statement header.'")


def main():
    ap = argparse.ArgumentParser(prog="harness", description="finance-llm-evals scoring harness")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list").set_defaults(fn=cmd_list)
    r = sub.add_parser("run"); r.add_argument("--case", required=True); r.add_argument("--model", default="oracle")
    r.add_argument("--all", action="store_true"); r.add_argument("--judge", default="mock", choices=["mock", "llm"])
    r.set_defaults(fn=cmd_run)
    s = sub.add_parser("suite"); s.add_argument("--model", default="oracle"); s.add_argument("--judge", default="mock", choices=["mock", "llm"])
    s.set_defaults(fn=cmd_suite)
    d = sub.add_parser("demo"); d.set_defaults(fn=cmd_demo)
    sub.add_parser("selftest").set_defaults(fn=cmd_selftest)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
