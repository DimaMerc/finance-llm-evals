"""outputs/calibration_score.py — compute judge-vs-expert agreement from the filled worksheet.

  python outputs/calibration_score.py

Reads outputs/eval2-live/calibration.csv (expert_met filled with 1/0), reports exact agreement,
Cohen's kappa, the confusion matrix, and per-atom agreement — the numbers PAPER v2 cites.
"""
from __future__ import annotations
import csv
import os

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "outputs", "eval2-live")


def main():
    rows = list(csv.DictReader(open(os.path.join(OUT, "calibration.csv"), encoding="utf-8")))
    graded = [r for r in rows if str(r.get("expert_met", "")).strip() in ("0", "1", "0.0", "1.0")]
    if not graded:
        raise SystemExit("no expert_met values filled in calibration.csv yet")
    n = len(graded)
    j = [int(float(r["judge_met"])) for r in graded]
    e = [int(float(r["expert_met"])) for r in graded]
    agree = sum(1 for a, b in zip(j, e) if a == b)
    p_o = agree / n
    # Cohen's kappa
    pj1, pe1 = sum(j) / n, sum(e) / n
    p_e = pj1 * pe1 + (1 - pj1) * (1 - pe1)
    kappa = (p_o - p_e) / (1 - p_e) if p_e < 1 else 1.0
    tp = sum(1 for a, b in zip(j, e) if a == 1 and b == 1)
    tn = sum(1 for a, b in zip(j, e) if a == 0 and b == 0)
    fp = sum(1 for a, b in zip(j, e) if a == 1 and b == 0)   # judge awarded, expert says no
    fn = sum(1 for a, b in zip(j, e) if a == 0 and b == 1)   # judge withheld, expert says yes

    print(f"judge-vs-expert calibration  (n = {n} verdicts, {len(rows) - n} ungraded)")
    print(f"  exact agreement : {p_o:.3f}  ({agree}/{n})")
    print(f"  Cohen's kappa   : {kappa:.3f}")
    print(f"  confusion       : TP {tp}  TN {tn}  FP {fp} (judge lenient)  FN {fn} (judge strict)")
    by_atom = {}
    for r, a, b in zip(graded, j, e):
        by_atom.setdefault(r["atom"], []).append(a == b)
    print("  per-atom agreement:")
    for atom, oks in sorted(by_atom.items()):
        print(f"    {atom:<16} {sum(oks)}/{len(oks)}")
    dis = [(r['run'], r['atom']) for r, a, b in zip(graded, j, e) if a != b]
    if dis:
        print("  disagreements:")
        for run, atom in dis:
            print(f"    {run}  {atom}")


if __name__ == "__main__":
    main()
