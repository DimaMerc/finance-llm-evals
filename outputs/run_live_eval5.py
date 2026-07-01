#!/usr/bin/env python3
"""
outputs/run_live_eval5.py — drive a REAL model through an eval-#5 (OTC confirmation matching) case
and save artifacts.

  python outputs/run_live_eval5.py --model-id claude-opus-4-8 \
      --endpoint https://api.anthropic.com/v1 [--case irs-confirm-2026] [--max-tokens 8000]

Saves under outputs/eval5-live/<model>/<case>/: answer.json, raw.txt, report.txt. The API key is
read from the environment (OPENAI_API_KEY / OPENROUTER_API_KEY) — never passed on the command line.
"""
from __future__ import annotations
import argparse
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from harness import run_case                                # noqa: E402
from harness.rubric import load_case                        # noqa: E402
from harness import live_confirmation_matching as lcm        # noqa: E402
from harness.report import render                            # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model-id", required=True)
    ap.add_argument("--endpoint", default="https://api.anthropic.com/v1")
    ap.add_argument("--case", default="irs-confirm-2026")
    ap.add_argument("--max-tokens", type=int, default=8000)
    ap.add_argument("--judge", default="mock", choices=["mock", "llm"])
    a = ap.parse_args()

    case_path = os.path.join(REPO, "cases", a.case + ".case.yaml")
    case = load_case(case_path)
    outdir = os.path.join(REPO, "outputs", "eval5-live", a.model_id.replace("/", "_"), a.case)
    os.makedirs(outdir, exist_ok=True)

    print(f"[live] {a.model_id} @ {a.endpoint} — building the two-confirmation packet ({a.case}) ...")
    try:
        ans = lcm.answer(case, endpoint=a.endpoint, model_id=a.model_id, max_tokens=a.max_tokens)
    except Exception as e:
        raw = getattr(e, "raw", "")
        if raw:
            with open(os.path.join(outdir, "raw_FAILED.txt"), "w", encoding="utf-8") as fh:
                fh.write(raw)
        print(f"[live] FAILED: {e}")
        sys.exit(1)

    with open(os.path.join(outdir, "raw.txt"), "w", encoding="utf-8") as fh:
        fh.write(ans.get("_raw", ""))
    clean = {k: v for k, v in ans.items() if not k.startswith("_")}
    with open(os.path.join(outdir, "answer.json"), "w", encoding="utf-8") as fh:
        json.dump(clean, fh, indent=2, default=str)

    result, rubric = run_case(case_path, model_output=ans, mode=a.judge)
    report = render(result, rubric, variant=f"live:{a.model_id}", mode=a.judge)
    with open(os.path.join(outdir, "report.txt"), "w", encoding="utf-8") as fh:
        fh.write(report)
    print(report)
    print(f"\n[live] {a.model_id} ({a.case}): gated={result.case_gated:.3f} ungated={result.case_ungated:.3f} "
          f"GAP={result.gap:.3f} AllPass={result.allpass} "
          f"gates={result.fired_gates} flags={result.flags} "
          f"D2(R,G)={result.e6}  (prompt ~{ans.get('_prompt_tokens_approx')} tok)")
    print(f"[live] artifacts -> {outdir}")


if __name__ == "__main__":
    main()
