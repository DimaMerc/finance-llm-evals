"""outputs/calibration_capture.py — capture the LLM judge's per-atom verdicts + reasoning on the
four completed eval-#2 answers and emit the judge-vs-expert calibration worksheet.

  python outputs/calibration_capture.py [--endpoint URL] [--model-id ID]

Needs the LM Studio rig (~28 judge calls, ~20 min). Emits:
  outputs/eval2-live/CALIBRATION-WORKSHEET.md   — the human-readable grading sheet
  outputs/eval2-live/calibration.csv            — fill expert_met (1/0) + optional expert_note
Then run outputs/calibration_score.py on the filled CSV.
"""
from __future__ import annotations
import argparse
import csv
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from harness.rubric import load_rubric, load_case, materialize, rubric_path_for   # noqa: E402
from harness.graders import grade                                                # noqa: E402
from harness import suites                                                       # noqa: E402
from harness.judge_llm import make_judge                                         # noqa: E402

OUT = os.path.join(REPO, "outputs", "eval2-live")
RUNS = [
    ("koct-op2026-anchor", "koct-op2026-anchor__qwen-qwen3.6-27b__oracle-packet"),
    ("koct-op2026-postrally", "koct-op2026-postrally__qwen-qwen3.6-27b__oracle-packet"),
    ("koct-op2026-postdrawdown", "koct-op2026-postdrawdown__qwen-qwen3.6-27b__oracle-packet"),
    ("koct-op2026-anchor", "koct-op2026-anchor__qwen-qwen3.6-27b__e2e"),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--endpoint", default="http://192.168.1.10:1234/v1")
    ap.add_argument("--model-id", default="qwen/qwen3.6-27b")
    a = ap.parse_args()

    rows = []
    for case_id, base in RUNS:
        path = os.path.join(REPO, "cases", f"{case_id}.case.yaml")
        case = load_case(path)
        rubric = load_rubric(rubric_path_for(case))
        suite = suites.for_case(case)
        atoms = materialize(rubric, case)
        ans = json.load(open(os.path.join(OUT, base + ".answer.json"), encoding="utf-8"))
        gold = dict(case["gold"])
        gold["manifest"] = case.get("manifest", {})
        gold["_snapshot"] = case.get("snapshot")
        gold["_claims"] = case.get("claims")
        crit = {x["id"]: x.get("criterion", "") for x in rubric["criteria"]}
        record = {}
        judge_fn = make_judge(endpoint=a.endpoint, model_id=a.model_id, rubric=rubric,
                              memo_kind=getattr(suite, "MEMO_KIND", "an analyst's memo"), record=record)
        print(f"[{base}] judging the {sum(1 for x in atoms if x.grader == 'judge' and x.points > 0 and x.checkpoint in suite.LLM_JUDGE_CPS)} free-form atoms ...", flush=True)
        grade(atoms, ans, gold, rubric, suite, mode="llm", judge_fn=judge_fn)
        for aid, rec in sorted(record.items()):
            cp = aid.split(".")[0]
            rows.append({
                "run": base, "atom": aid, "criterion": crit.get(aid, aid),
                "model_section": json.dumps(ans.get(cp, {}), default=str)[:1200],
                "gold_reference": json.dumps(case["gold"].get(cp, {}), default=str)[:1200],
                "judge_met": rec["met"], "judge_reasoning": rec["reasoning"],
                "expert_met": "", "expert_note": "",
            })
        print(f"[{base}] captured {len(record)} verdicts", flush=True)

    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "calibration.csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    with open(os.path.join(OUT, "CALIBRATION-WORKSHEET.md"), "w", encoding="utf-8") as fh:
        fh.write("# Judge-vs-expert calibration worksheet (eval #2, S2/S3 judge atoms)\n\n")
        fh.write("For each row: did the LLM judge call it correctly? Fill `expert_met` (1 = the\n"
                 "criterion IS satisfied by the model section, 0 = it is not) in calibration.csv —\n"
                 "judge the MEMO against the CRITERION using the GOLD as reference, independently\n"
                 "of the judge's verdict. Then run outputs/calibration_score.py.\n\n")
        cur = None
        for i, r in enumerate(rows, 1):
            if r["run"] != cur:
                cur = r["run"]
                fh.write(f"\n---\n\n## {cur}\n\n")
            fh.write(f"### {i}. `{r['atom']}`  (judge said: **{'MET' if r['judge_met'] else 'NOT MET'}**)\n\n")
            fh.write(f"**Criterion:** {r['criterion']}\n\n")
            fh.write(f"**Judge's reasoning:** {r['judge_reasoning']}\n\n")
            fh.write(f"**Model section:**\n```json\n{r['model_section']}\n```\n\n")
            fh.write(f"**Gold reference:**\n```json\n{r['gold_reference']}\n```\n\n")
    print(f"\nworksheet: {os.path.join(OUT, 'CALIBRATION-WORKSHEET.md')}")
    print(f"fill in:   {os.path.join(OUT, 'calibration.csv')}  (expert_met column)")


if __name__ == "__main__":
    main()
