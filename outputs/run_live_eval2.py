"""outputs/run_live_eval2.py — drive the eval-#2 live runs and capture everything the
Phase-5 taxonomy needs: the parsed model answer, the raw completion, and the scored report.

  python outputs/run_live_eval2.py <case-substr> [--e2e] [--judge mock|llm] [--model-id ID]
                                   [--endpoint URL] [--max-tokens N]

Artifacts land in outputs/eval2-live/<case>__<model>__<mode>.{answer.json,raw.txt,report.txt}
"""
from __future__ import annotations
import argparse
import glob
import json
import os
import re
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from harness import run_case                                    # noqa: E402
from harness.rubric import load_case                            # noqa: E402
from harness import live_defined_outcome as ldo                 # noqa: E402
from harness.report import render                               # noqa: E402

OUT = os.path.join(REPO, "outputs", "eval2-live")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("case")
    ap.add_argument("--e2e", action="store_true")
    ap.add_argument("--judge", default="mock", choices=["mock", "llm"])
    ap.add_argument("--model-id", default=None)
    ap.add_argument("--endpoint", default="http://192.168.1.10:1234/v1")
    ap.add_argument("--max-tokens", type=int, default=16000)   # reasoning models think for thousands of tokens first
    ap.add_argument("--deadline", type=int, default=2400)       # qwen3.6-27b on the M5 Max needs ~20 min/case (think + 4k-token JSON)
    a = ap.parse_args()

    path = next(p for p in sorted(glob.glob(os.path.join(REPO, "cases", "*.case.yaml")))
                if a.case in os.path.basename(p))
    case = load_case(path)
    name = case["case_id"]
    mode = "e2e" if a.e2e else "oracle-packet"
    print(f"[{name}] building packet ({mode}) and calling {a.endpoint} ...", flush=True)

    t0 = time.time()
    try:
        ans = ldo.answer(case, endpoint=a.endpoint, model_id=a.model_id,
                         max_tokens=a.max_tokens, e2e=a.e2e, deadline=a.deadline)
    except Exception as e:
        raw = getattr(e, "raw", "")
        if raw:
            os.makedirs(OUT, exist_ok=True)
            fp = os.path.join(OUT, f"{name}__parsefail__{int(time.time())}.raw.txt")
            with open(fp, "w", encoding="utf-8") as fh:
                fh.write(raw)
            print(f"[{name}] parse failed; raw completion saved to {fp}")
        raise
    dt = time.time() - t0
    model = ans.get("_model_id", "unknown")
    slug = re.sub(r"[^A-Za-z0-9.-]+", "-", model)
    print(f"[{name}] {model} answered in {dt:.0f}s "
          f"(prompt ~{ans.get('_prompt_tokens_approx', 0):,} tok, raw {len(ans.get('_raw', '')):,} chars)", flush=True)

    os.makedirs(OUT, exist_ok=True)
    base = os.path.join(OUT, f"{name}__{slug}__{mode}")
    with open(base + ".raw.txt", "w", encoding="utf-8") as fh:
        fh.write(ans.get("_raw", ""))
    clean = {k: v for k, v in ans.items() if not k.startswith("_")}
    with open(base + ".answer.json", "w", encoding="utf-8") as fh:
        json.dump(clean, fh, indent=1, default=str)

    result, rubric = run_case(path, model_output=ans, mode=a.judge, endpoint=a.endpoint, model_id=a.model_id)
    report = render(result, rubric, variant=f"live:{model}", mode=a.judge)
    with open(base + f".report.{a.judge}.txt", "w", encoding="utf-8") as fh:
        fh.write(report + f"\n\n(answered in {dt:.0f}s; mode={mode})\n")
    print(report)
    print(f"\nartifacts: {base}.{{answer.json,raw.txt,report.{a.judge}.txt}}")


if __name__ == "__main__":
    main()
