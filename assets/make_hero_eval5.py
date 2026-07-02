#!/usr/bin/env python3
"""
assets/make_hero_eval5.py -- hero image for the eval-#5 (OTC confirmation matching) LinkedIn post.
Output: assets/hero-eval5.png (1200x1200 square, LinkedIn feed).

The image IS the post: two confirmations of the same swap, everything ties EXCEPT the fixed rate
(6.00% vs 6.05%) -> MISMATCHED, do not affirm. Same white/navy ETF-family palette as the eval-#4
tie-out hero (this is ETF/derivatives-ops territory). Run: python assets/make_hero_eval5.py
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

HERE = os.path.dirname(os.path.abspath(__file__))
BG    = "#FFFFFF"
PANEL = "#F2F5F8"
REDBG = "#FBECEA"
NAVY  = "#16243B"
GREEN = "#2E7D5B"
RED   = "#C0392B"
MUTE  = "#6B7785"
LINE  = "#C9D3DE"
MONO  = "DejaVu Sans Mono"

fig = plt.figure(figsize=(12, 12), dpi=100)
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
ax.add_patch(Rectangle((0, 0), 1, 1, color=BG, zorder=0))

# ---------------- header ----------------
ax.text(0.5, 0.945, "D O   T H E   T W O   S I D E S   A G R E E ?",
        fontsize=27, color=NAVY, weight="bold", ha="center", va="center")
ax.text(0.5, 0.898, "Your ETF is full of swaps you never see - and each is affirmed only if the two sides tie.",
        fontsize=14.5, color=MUTE, ha="center", va="center")
ax.plot([0.08, 0.92], [0.868, 0.868], color=LINE, lw=1.4, zorder=1)

# ---------------- the match grid ----------------
# columns: term | our side | counterparty | status
CX_TERM, CX_OUR, CX_CPTY, CX_STAT = 0.11, 0.44, 0.66, 0.885
TOP = 0.828
ax.text(CX_TERM, TOP, "TERM", fontsize=12.5, color=MUTE, weight="bold", va="center")
ax.text(CX_OUR,  TOP, "OUR SIDE", fontsize=12.5, color=NAVY, weight="bold", va="center", ha="center")
ax.text(CX_CPTY, TOP, "COUNTERPARTY", fontsize=12.5, color=NAVY, weight="bold", va="center", ha="center")
ax.text(CX_STAT, TOP, "", fontsize=12.5, va="center", ha="center")

rows = [
    ("Notional",       "EUR 50,000,000", "EUR 50,000,000", True),
    ("Maturity",       "5-year term",    "5-year term",    True),
    ("Floating leg",   "6M float",       "6M float",       True),
    ("Direction",      "receive fixed",  "receive fixed",  True),
    ("Day-count",      "30E/360",        "30E/360",        True),
    ("Fixed rate",     "6.00%",          "6.05%",          False),   # THE BREAK
]
y = TOP - 0.052
rh = 0.058
for term, ours, cpty, ok in rows:
    if not ok:
        ax.add_patch(Rectangle((0.075, y - rh/2 + 0.004), 0.85, rh - 0.004, facecolor=REDBG, zorder=1))
    lc = NAVY
    vc = NAVY if ok else RED
    vw = "normal" if ok else "bold"
    ax.text(CX_TERM, y, term, fontsize=15, color=lc, va="center", weight=("normal" if ok else "bold"))
    ax.text(CX_OUR,  y, ours, fontsize=15, color=vc, va="center", ha="center", weight=vw, family=MONO)
    ax.text(CX_CPTY, y, cpty, fontsize=15, color=vc, va="center", ha="center", weight=vw, family=MONO)
    ax.text(CX_STAT, y, ("match" if ok else "MISMATCH"), fontsize=12.5,
            color=(GREEN if ok else RED), va="center", ha="center", weight="bold")
    y -= rh

# ---------------- verdict band ----------------
ax.add_patch(Rectangle((0.075, 0.245), 0.85, 0.145, facecolor=NAVY, zorder=2))
ax.text(0.5, 0.352, "The fixed rate is off by 5 bp - about EUR 25,000 a year on this trade.",
        fontsize=15.5, color="#D7E0EC", ha="center", va="center")
ax.text(0.5, 0.298, "MISMATCHED  ->  DO NOT AFFIRM", fontsize=27, color="#FF6B5E", weight="bold",
        ha="center", va="center")

# ---------------- the materiality footer (the honest, expert note) ----------------
ax.text(0.5, 0.175, "The two firms also used different trade IDs (TW9235 / SW2000).",
        fontsize=14, color=NAVY, ha="center", va="center")
ax.text(0.5, 0.140, "That's expected - not a break. The skill is telling the two apart.",
        fontsize=14, color=GREEN, weight="bold", ha="center", va="center")

ax.plot([0.08, 0.92], [0.075, 0.075], color=LINE, lw=1.4)
ax.text(0.5, 0.045, "finance-llm-evals   -   MIT   -   grounded in a real published FpML swap confirmation",
        fontsize=12.5, color=MUTE, ha="center", va="center")

fig.savefig(os.path.join(HERE, "hero-eval5.png"), dpi=100, facecolor=BG)
print("wrote", os.path.join(HERE, "hero-eval5.png"))
