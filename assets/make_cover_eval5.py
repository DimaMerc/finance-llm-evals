#!/usr/bin/env python3
"""
assets/make_cover_eval5.py -- WIDE cover image for the eval-#5 LinkedIn ARTICLE header.
Output: assets/cover-eval5.png (1200x630, ~1.91:1 -- LinkedIn crops article covers to a wide
banner, so the square hero-eval5.png loses its title/footer as a cover. This one is laid out
horizontally: title + subtitle across the top, the match grid on the left, the verdict on the
right, nothing important near the edges. Same white/navy brand as hero-eval5. Run:
python assets/make_cover_eval5.py
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle

HERE = os.path.dirname(os.path.abspath(__file__))
BG    = "#FFFFFF"
REDBG = "#FBECEA"
NAVY  = "#16243B"
GREEN = "#2E7D5B"
RED   = "#C0392B"
MUTE  = "#6B7785"
LINE  = "#C9D3DE"
LGREEN= "#7FD1A8"
ACC   = "#FF6B5E"
MONO  = "DejaVu Sans Mono"

fig = plt.figure(figsize=(12, 6.3), dpi=100)
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
ax.add_patch(Rectangle((0, 0), 1, 1, color=BG, zorder=0))

# ---------------- header ----------------
ax.text(0.038, 0.90, "Do the two sides of a swap agree?",
        fontsize=30, color=NAVY, weight="bold", ha="left", va="center")
ax.text(0.040, 0.815, "Your ETF is full of swaps you never see. This is the desk check that catches the ones that don't tie.",
        fontsize=13.5, color=MUTE, ha="left", va="center")
ax.plot([0.038, 0.962], [0.755, 0.755], color=LINE, lw=1.4, zorder=1)

# ---------------- left: the match grid ----------------
CX_TERM, CX_OUR, CX_CPTY = 0.055, 0.335, 0.485
TOP = 0.685
ax.text(CX_TERM, TOP, "TERM",  fontsize=10.5, color=MUTE, weight="bold", va="center")
ax.text(CX_OUR,  TOP, "OURS",  fontsize=10.5, color=NAVY, weight="bold", va="center", ha="center")
ax.text(CX_CPTY, TOP, "THEIRS",fontsize=10.5, color=NAVY, weight="bold", va="center", ha="center")

rows = [
    ("Notional",     "EUR 50M",       "EUR 50M",       True),
    ("Maturity",     "5-year",        "5-year",        True),
    ("Floating leg", "EURIBOR 6M",    "EURIBOR 6M",    True),
    ("Direction",    "receive fixed", "receive fixed", True),
    ("Day-count",    "30E/360",       "30E/360",       True),
    ("Fixed rate",   "6.00%",         "6.05%",         False),   # THE BREAK
]
y = TOP - 0.075
rh = 0.083
for term, ours, cpty, ok in rows:
    if not ok:
        ax.add_patch(Rectangle((0.035, y - rh/2 + 0.006), 0.535, rh - 0.006, facecolor=REDBG, zorder=1))
    vc = NAVY if ok else RED
    vw = "normal" if ok else "bold"
    ax.text(CX_TERM, y, term, fontsize=13, color=NAVY, va="center", weight=("normal" if ok else "bold"))
    ax.text(CX_OUR,  y, ours, fontsize=13, color=vc, va="center", ha="center", weight=vw, family=MONO)
    ax.text(CX_CPTY, y, cpty, fontsize=13, color=vc, va="center", ha="center", weight=vw, family=MONO)
    y -= rh

# ---------------- right: the verdict panel ----------------
ax.add_patch(FancyBboxPatch((0.615, 0.115), 0.345, 0.545,
             boxstyle="round,pad=0.010,rounding_size=0.03",
             facecolor=NAVY, edgecolor="none", zorder=2))
PX = 0.7875   # panel center
ax.text(PX, 0.585, "The fixed rate is off by 5 bp", fontsize=13.5, color="#C6D2E2", ha="center", va="center", zorder=3)
ax.text(PX, 0.525, "about EUR 25,000 a year", fontsize=15, color="#EAF0F7", ha="center", va="center", weight="bold", zorder=3)
ax.text(PX, 0.405, "MISMATCHED", fontsize=31, color=ACC, ha="center", va="center", weight="bold", zorder=3)
ax.text(PX, 0.330, "DO NOT AFFIRM", fontsize=21, color="#FFFFFF", ha="center", va="center", weight="bold", zorder=3)
ax.text(PX, 0.215, "The two firms' trade IDs differ.", fontsize=11, color="#C6D2E2", ha="center", va="center", zorder=3)
ax.text(PX, 0.170, "That's expected - not a break.", fontsize=11, color=LGREEN, ha="center", va="center", weight="bold", zorder=3)

# ---------------- footer ----------------
ax.plot([0.038, 0.962], [0.065, 0.065], color=LINE, lw=1.2)
ax.text(0.038, 0.035, "finance-llm-evals", fontsize=11, color=NAVY, ha="left", va="center", weight="bold")
ax.text(0.962, 0.035, "grounded in a real published FpML swap confirmation", fontsize=11, color=MUTE, ha="right", va="center")

fig.savefig(os.path.join(HERE, "cover-eval5.png"), dpi=100, facecolor=BG)
print("wrote", os.path.join(HERE, "cover-eval5.png"))
