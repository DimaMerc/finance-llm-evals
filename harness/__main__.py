"""
harness/__main__.py — CLI.

  python -m harness list
  python -m harness run  --case cases/snow-fy2026q2.case.yaml [--model scale_slip] [--all]
  python -m harness run  --case koct-op2026-anchor --model free_lunch
  python -m harness demo                       # the canonical oracle-vs-scale-slip contrast on SNOW
  python -m harness suite [--model oracle]     # score every case in cases/ (both suites)
  python -m harness selftest                   # per-suite regression invariants

`--judge mock` (default, offline/no-API) grades the entailment/judge/refusal atoms heuristically;
`--judge llm` is the (spend-incurring) live swap. The deterministic core + all gating are exact in
both modes. Cases route to their suite (eval #1 earnings / eval #2 defined-outcome / eval #3 dcf) by
the case file's `suite:` field; `--model` accepts that suite's variants.
"""
from __future__ import annotations
import argparse
import glob
import os
from . import run_case, REPO, suites
from .rubric import load_case, suite_of
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
    by_suite = {}
    for p in _cases():
        by_suite.setdefault(suite_of(load_case(p)), []).append(p)
    for s, paths in sorted(by_suite.items()):
        variants = suites.for_case(load_case(paths[0])).VARIANTS
        print(f"Suite {s}:")
        for p in paths:
            print("  -", os.path.basename(p).replace(".case.yaml", ""))
        print("  variants:", ", ".join(variants))


def cmd_run(a):
    path = _resolve(a.case)
    case = load_case(path)
    variants = suites.for_case(case).VARIANTS if a.all else [a.model]
    for v in variants:
        mo, label = None, v
        if v == "live":
            if suite_of(case) == "defined-outcome-etf":
                from . import live_defined_outcome as ldo
                print(f"[live] building the filings packet{' + distractors (--e2e)' if a.e2e else ''} and calling LM Studio at {a.endpoint} ...")
                ans = ldo.answer(case, endpoint=a.endpoint, model_id=a.model_id, max_tokens=a.max_tokens, e2e=a.e2e)
            elif suite_of(case) == "dcf-valuation":
                from . import live_dcf
                print(f"[live] building the 10-K statements packet and calling the model at {a.endpoint} ...")
                ans = live_dcf.answer(case, endpoint=a.endpoint, model_id=a.model_id, max_tokens=a.max_tokens)
            else:
                from . import live
                print(f"[live] fetching the press release{' + 10-Q excerpt' if a.tenq else ''} and calling LM Studio at {a.endpoint} ...")
                ans = live.answer(case, endpoint=a.endpoint, model_id=a.model_id, max_tokens=a.max_tokens, with_tenq=a.tenq)
            mo, label = ans, "live:" + str(ans.get("_model_id", "?"))
            print(f"[live] model={ans.get('_model_id')}  (parsed {len([k for k in ans if not k.startswith('_')])} sections; raw {len(ans.get('_raw',''))} chars)")
        if a.judge == "llm":
            print(f"[judge] grading the free-form judge atoms with the local model at {a.endpoint} ...")
        result, rubric = run_case(path, variant=v, mode=a.judge, model_output=mo,
                                  endpoint=a.endpoint, model_id=a.model_id)
        print(render(result, rubric, variant=label, mode=a.judge))


def cmd_suite(a):
    rows = []
    for p in _cases():
        case = load_case(p)
        variant = a.model
        if variant != "oracle" and variant not in suites.for_case(case).VARIANTS:
            variant = "oracle"   # suite-specific flaw names don't cross suites; oracle always exists
        result, rubric = run_case(p, variant=variant, mode=a.judge)
        rows.append((os.path.basename(p).replace(".case.yaml", ""), suite_of(case), result))
        print(render(result, rubric, variant=variant, mode=a.judge))
    print("\nSUITE SUMMARY  (model=%s, judge=%s)" % (a.model, a.judge))
    print("  case                       suite                 gated   ungated   GAP    AllPass  flags")
    for name, s, r in rows:
        print(f"  {name:<25}  {s:<20}  {r.case_gated:.3f}   {r.case_ungated:.3f}    {r.gap:.3f}   {r.allpass}"
              + (f"        {','.join(r.flags)}" if r.flags else ""))
    if rows:
        n = len(rows)
        print(f"  {'MEAN':<25}  {'':<20}  {sum(r.case_gated for _,_,r in rows)/n:.3f}   "
              f"{sum(r.case_ungated for _,_,r in rows)/n:.3f}    {sum(r.gap for _,_,r in rows)/n:.3f}   "
              f"{sum(r.allpass for _,_,r in rows)/n:.2f}")


def _selftest_earnings(p, name):
    """eval #1 invariants (unchanged from the pre-refactor selftest)."""
    failures = []
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
    return failures


_VERDICT_ENUM = {"ACCURATE", "ACCURATE_AT_PERIOD_START_ONLY", "WRONG_BASIS", "FALSE", "NOT_VERIFIABLE"}


def _selftest_defined_outcome(p, name):
    """eval #2 invariants: oracle perfection + every gate tier + the free-lunch headline flag."""
    failures = []
    # case lint: C7 gold verdicts must be enum STRINGS (a bare YAML FALSE parses as a boolean,
    # which the oracle would silently mirror — the review caught exactly this)
    case = load_case(p)
    bad = [r.get("id") for r in (case.get("gold", {}).get("C7", {}).get("verdicts") or [])
           if not (isinstance(r.get("verdict"), str) and r["verdict"] in _VERDICT_ENUM)]
    if bad:
        failures.append(f"{name}: C7 gold verdicts not enum strings (YAML boolean?): {bad}")
    oracle, _ = run_case(p, variant="oracle")
    if not (oracle.allpass == 1 and abs(oracle.case_gated - 1.0) < 1e-6 and oracle.gap == 0.0
            and not oracle.flags):
        failures.append(f"{name}: oracle expected 1.0/AllPass/no-flags, got gated={oracle.case_gated} "
                        f"allpass={oracle.allpass} gates={oracle.fired_gates} flags={oracle.flags}")
    vs, _ = run_case(p, variant="vintage_slip")
    if not ("GATE.VINTAGE" in vs.fired_gates and vs.gap > 0.5 and vs.allpass == 0):
        failures.append(f"{name}: vintage_slip expected GATE.VINTAGE + GAP>0.5, got gates={vs.fired_gates} gap={vs.gap}")
    rs, _ = run_case(p, variant="refscale_slip")
    if not ("GATE.REFSCALE" in rs.fired_gates and rs.gap > 0.3 and rs.allpass == 0):
        failures.append(f"{name}: refscale_slip expected GATE.REFSCALE + GAP>0.3, got gates={rs.fired_gates} gap={rs.gap}")
    fb, _ = run_case(p, variant="feebasis_mix")
    if "GATE.FEEBASIS" not in fb.fired_gates:
        failures.append(f"{name}: feebasis_mix expected GATE.FEEBASIS (scoped), got {fb.fired_gates}")
    fl, _ = run_case(p, variant="free_lunch")
    if not ("GATE.FREELUNCH" in fl.fired_gates and "free_lunch_fired" in fl.flags
            and fl.checkpoints["S2"]["score_gated"] == 0.0 and fl.checkpoints["S3"]["score_gated"] == 0.0
            and fl.allpass == 0):
        failures.append(f"{name}: free_lunch expected GATE.FREELUNCH + flag + S2/S3->0, got "
                        f"gates={fl.fired_gates} flags={fl.flags} S2={fl.checkpoints['S2']['score_gated']} "
                        f"S3={fl.checkpoints['S3']['score_gated']}")
    fp, _ = run_case(p, variant="fabricate_probe")
    if not (fp.e6[1] == 0.0 and fp.checkpoints["E5"]["score_gated"] == 0.0
            and "GATE.FABRICATION" in fp.fired_gates and fp.allpass == 0):
        failures.append(f"{name}: fabricate_probe expected E5->0 (G=0) + GATE.FABRICATION, got "
                        f"E5={fp.checkpoints['E5']['score_gated']} gates={fp.fired_gates}")
    cf, _ = run_case(p, variant="c6_flip")
    if not ("GATE.C6DIR" in cf.fired_gates and cf.checkpoints["C6"]["score_gated"] == 0.0):
        failures.append(f"{name}: c6_flip expected GATE.C6DIR + C6->0, got gates={cf.fired_gates} "
                        f"C6={cf.checkpoints['C6']['score_gated']}")
    # live-schema round-trip: a schema-perfect answer (oracle re-serialized through the live OUTPUT
    # SCHEMA's wire format, JSON-parsed back) must grade 1.000/AllPass — proves the live contract's
    # key paths stay aligned with the suite handlers (no network involved)
    import json as _json
    from . import live_defined_outcome as _ldo
    from .live import parse_answer as _parse
    rt, _ = run_case(p, model_output=_parse(_json.dumps(_ldo.oracle_to_schema(case))))
    if not (rt.allpass == 1 and abs(rt.case_gated - 1.0) < 1e-6):
        failures.append(f"{name}: live-schema round-trip expected 1.0/AllPass, got "
                        f"gated={rt.case_gated} allpass={rt.allpass} gates={rt.fired_gates}")
    return failures


_DCF_VERDICT_ENUM = {"ACCURATE", "ACCURATE_ON_BASE_CASE_ONLY", "WRONG_BASIS", "FALSE", "NOT_VERIFIABLE"}


def _selftest_dcf(p, name):
    """eval #3 invariants: oracle perfection + every gate tier + the false-precision headline flag."""
    failures = []
    case = load_case(p)
    bad = [r.get("id") for r in (case.get("gold", {}).get("C7", {}).get("verdicts") or [])
           if not (isinstance(r.get("verdict"), str) and r["verdict"] in _DCF_VERDICT_ENUM)]
    if bad:
        failures.append(f"{name}: C7 gold verdicts not enum strings (YAML boolean?): {bad}")
    oracle, _ = run_case(p, variant="oracle")
    if not (oracle.allpass == 1 and abs(oracle.case_gated - 1.0) < 1e-6 and oracle.gap == 0.0
            and not oracle.flags):
        failures.append(f"{name}: oracle expected 1.0/AllPass/no-flags, got gated={oracle.case_gated} "
                        f"allpass={oracle.allpass} gates={oracle.fired_gates} flags={oracle.flags}")
    bm, _ = run_case(p, variant="basis_mix")
    if not ("GATE.BASIS" in bm.fired_gates and bm.gap > 0.5 and bm.allpass == 0):
        failures.append(f"{name}: basis_mix expected GATE.BASIS + GAP>0.5, got gates={bm.fired_gates} gap={bm.gap}")
    bl, _ = run_case(p, variant="basis_late")   # the EXECUTED Ke-discount, caught at the C5 hook
    if not ("GATE.BASIS" in bl.fired_gates and bl.allpass == 0):
        failures.append(f"{name}: basis_late expected GATE.BASIS (C5 hook), got gates={bl.fired_gates}")
    ss, _ = run_case(p, variant="scale_slip")
    if not ("GATE.SCALE" in ss.fired_gates and ss.gap > 0.2 and ss.allpass == 0):
        failures.append(f"{name}: scale_slip expected GATE.SCALE + GAP>0.2, got gates={ss.fired_gates} gap={ss.gap}")
    ws, _ = run_case(p, variant="wacc_slip")
    if "GATE.WACC" not in ws.fired_gates:
        failures.append(f"{name}: wacc_slip expected GATE.WACC (scoped), got {ws.fired_gates}")
    bo, _ = run_case(p, variant="bridge_omit")
    if not ("GATE.BRIDGE" in bo.fired_gates and bo.checkpoints["C6"]["score_gated"] == 0.0
            and bo.checkpoints["S1"]["score_gated"] == 0.0):
        failures.append(f"{name}: bridge_omit expected GATE.BRIDGE + C6/S1->0, got gates={bo.fired_gates} "
                        f"C6={bo.checkpoints['C6']['score_gated']} S1={bo.checkpoints['S1']['score_gated']}")
    fp, _ = run_case(p, variant="false_precision")
    if not ("GATE.FALSEPRECISION" in fp.fired_gates and "false_precision_fired" in fp.flags
            and fp.checkpoints["S2"]["score_gated"] == 0.0 and fp.checkpoints["S3"]["score_gated"] == 0.0
            and fp.allpass == 0):
        failures.append(f"{name}: false_precision expected GATE.FALSEPRECISION + flag + S2/S3->0, got "
                        f"gates={fp.fired_gates} flags={fp.flags} S2={fp.checkpoints['S2']['score_gated']} "
                        f"S3={fp.checkpoints['S3']['score_gated']}")
    ge, _ = run_case(p, variant="g_explode")
    if not ("GATE.C4TERM" in ge.fired_gates and ge.checkpoints["C4"]["score_gated"] == 0.0):
        failures.append(f"{name}: g_explode expected GATE.C4TERM + C4->0, got gates={ge.fired_gates} "
                        f"C4={ge.checkpoints['C4']['score_gated']}")
    cs, _ = run_case(p, variant="c7_sign")
    if not ("GATE.C7SIGN" in cs.fired_gates and cs.checkpoints["C7"]["score_gated"] == 0.0):
        failures.append(f"{name}: c7_sign expected GATE.C7SIGN + C7->0, got gates={cs.fired_gates} "
                        f"C7={cs.checkpoints['C7']['score_gated']}")
    cf, _ = run_case(p, variant="c1_fcf")
    if not ("GATE.C1FCF" in cf.fired_gates and cf.checkpoints["C1"]["score_gated"] == 0.0):
        failures.append(f"{name}: c1_fcf expected GATE.C1FCF + C1->0, got gates={cf.fired_gates} "
                        f"C1={cf.checkpoints['C1']['score_gated']}")
    fab, _ = run_case(p, variant="fabricate_probe")
    if not (fab.e6[1] == 0.0 and fab.checkpoints["E5"]["score_gated"] == 0.0
            and "GATE.FABRICATION" in fab.fired_gates and fab.allpass == 0):
        failures.append(f"{name}: fabricate_probe expected E5->0 (G=0) + GATE.FABRICATION, got "
                        f"E5={fab.checkpoints['E5']['score_gated']} gates={fab.fired_gates}")
    # live-schema round-trip: a schema-perfect answer (the oracle re-serialized through the live
    # DCF OUTPUT SCHEMA, JSON-parsed back) must grade 1.000/AllPass — proves the live contract's key
    # paths stay aligned with the suite handlers (no network involved)
    import json as _json
    from . import live_dcf as _ldcf
    from .live import parse_answer as _parse
    rt, _ = run_case(p, model_output=_parse(_json.dumps(_ldcf.oracle_to_schema(case))))
    if not (rt.allpass == 1 and abs(rt.case_gated - 1.0) < 1e-6):
        failures.append(f"{name}: live-schema round-trip expected 1.0/AllPass, got "
                        f"gated={rt.case_gated} allpass={rt.allpass} gates={rt.fired_gates}")
    return failures


def cmd_selftest(_):
    """Regression guard, per suite: oracle must AllPass at 1.0; the gate tiers must open the
    expected GAPs; eval #2 adds the free-lunch headline flag, eval #3 the false-precision flag."""
    failures, n1 = [], {"earnings-analysis": 0, "defined-outcome-etf": 0, "dcf-valuation": 0}
    dispatch = {"defined-outcome-etf": _selftest_defined_outcome, "dcf-valuation": _selftest_dcf}
    for p in _cases():
        case = load_case(p)
        name = os.path.basename(p).replace(".case.yaml", "")
        s = suite_of(case)
        n1[s] = n1.get(s, 0) + 1
        failures += dispatch.get(s, _selftest_earnings)(p, name)
    if failures:
        print("SELFTEST FAILED:")
        for f in failures:
            print("  -", f)
        raise SystemExit(1)
    print(f"SELFTEST PASSED: {n1.get('earnings-analysis', 0)} earnings cases x "
          f"oracle/scale_slip/fabricate_probe/basis_mismatch + {n1.get('defined-outcome-etf', 0)} "
          f"defined-outcome cases x oracle/vintage_slip/refscale_slip/feebasis_mix/free_lunch/"
          f"fabricate_probe/c6_flip + {n1.get('dcf-valuation', 0)} dcf cases x oracle/basis_mix/"
          f"scale_slip/wacc_slip/bridge_omit/false_precision/g_explode/c7_sign/c1_fcf/fabricate_probe "
          f"invariants hold.")


def cmd_demo(_):
    path = _resolve("snow")
    print("DEMO -- Snowflake FQ2'26 (in thousands). A model that does the analysis correctly but")
    print("misreads the statement header scale: the one error that poisons everything downstream.\n")
    for v in ("oracle", "scale_slip"):
        result, rubric = run_case(path, variant=v, mode="mock")
        print(render(result, rubric, variant=v, mode="mock"))
    print("\nThe scale_slip model keeps a HIGH ungated score (its arithmetic is internally consistent)")
    print("but GATE.P2 collapses the gated score -- the GAP is exactly the diagnostic the eval exists to")
    print("surface: 'can do the math, cannot be trusted to read a statement header.'")


def main():
    ap = argparse.ArgumentParser(prog="harness", description="finance-llm-evals scoring harness")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list").set_defaults(fn=cmd_list)
    r = sub.add_parser("run"); r.add_argument("--case", required=True); r.add_argument("--model", default="oracle",
        help="eval #1: oracle | scale_slip | fabricate_probe | flip_eps_beat | basis_mismatch | live ; "
             "eval #2: oracle | vintage_slip | refscale_slip | feebasis_mix | free_lunch | fabricate_probe | c6_flip ; "
             "eval #3: oracle | basis_mix | basis_late | scale_slip | wacc_slip | bridge_omit | false_precision | g_explode | c7_sign | c1_fcf | fabricate_probe")
    r.add_argument("--all", action="store_true"); r.add_argument("--judge", default="mock", choices=["mock", "llm"])
    r.add_argument("--endpoint", default="http://localhost:1234/v1", help="LM Studio OpenAI-compatible server (--model live)")
    r.add_argument("--model-id", default=None, help="LM Studio model id (default: the loaded one)")
    r.add_argument("--max-tokens", type=int, default=4000)
    r.add_argument("--tenq", action="store_true", help="also feed a 10-Q excerpt (earnings suite; needs ~40k context; fairer on ratio/working-capital checkpoints)")
    r.add_argument("--e2e", action="store_true", help="defined-outcome suite: include the sibling-vintage N-PORTs + the mid-period 497K as live distractors (end-to-end mode)")
    r.set_defaults(fn=cmd_run)
    s = sub.add_parser("suite"); s.add_argument("--model", default="oracle"); s.add_argument("--judge", default="mock", choices=["mock", "llm"])
    s.set_defaults(fn=cmd_suite)
    d = sub.add_parser("demo"); d.set_defaults(fn=cmd_demo)
    sub.add_parser("selftest").set_defaults(fn=cmd_selftest)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
