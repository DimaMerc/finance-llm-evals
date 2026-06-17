#!/usr/bin/env python3
"""
assets/make_hero_eval3.py -- hero image for the eval-#3 (DCF) LinkedIn post/article.
Output: assets/hero-eval3.png (1200x1200 square, LinkedIn feed).

DELIBERATELY DIFFERENT from the eval-#2 image set (which were white-background two-bar comparisons in
navy/green/crimson). This is a DARK-themed WATERFALL "bridge" chart -- the canonical finance visual,
and literally the thing the eval is about: walking enterprise value DOWN across the net-debt bridge to
equity value, then dividing by shares. Skip the bridge and you overstate the price by ~$51/share
($279 vs the correct $228). Run: python assets/make_hero_eval3.py
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch

HERE = os.path.dirname(os.path.abspath(__file__))
# dark palette (new, not the eval-#2 brand set)
BG      = "#0F1D33"   # deep navy background
PANEL   = "#16263F"
AMBER   = "#E8B24A"   # enterprise value / the "before"
TEAL    = "#34B5A0"   # equity value / the correct answer
RED     = "#E0635E"   # the net-debt slab / the blunder
WHITE   = "#EEF3F8"
MUTE    = "#8FA2BB"
FAINT   = "#27395A"

fig = plt.figure(figsize=(12, 12), dpi=100)
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
ax.add_patch(Rectangle((0, 0), 1, 1, color=BG, zorder=0))

LX = 0.085
# ---------------- header ----------------
ax.text(LX, 0.945, "T H R E E   F R O N T I E R   M O D E L S   -   O N E   R E A L   D C F",
        fontsize=13.5, color=AMBER, weight="bold", va="center")
ax.text(LX, 0.882, "Can an AI value a company?", fontsize=42, color=WHITE, weight="bold", va="center")
ax.text(LX, 0.822, "On a McDonald's DCF, it comes down to one subtraction most people skip.",
        fontsize=15.5, color=MUTE, va="center")

# ---------------- the waterfall (values in $B) ----------------
VMAX = 215.0
y0, y1 = 0.300, 0.660                       # plotting band for the bars
def H(v): return (v / VMAX) * (y1 - y0)     # bar height for a $B value
def Y(v): return y0 + H(v)                  # y-coord of a $B level

EV, ND, AFF = 200.0, 39.0, 3.0
EQ = EV - ND + AFF                          # ~164

cols = {"ev": 0.215, "nd": 0.430, "eq": 0.645}
bw = 0.135

# faint baseline + a couple of gridlines
ax.plot([LX, 0.915], [y0, y0], color=FAINT, lw=1.4, zorder=1)
for gv in (50, 100, 150, 200):
    ax.plot([LX, 0.915], [Y(gv), Y(gv)], color=FAINT, lw=0.8, ls=(0, (2, 4)), zorder=1)
    ax.text(0.918, Y(gv), f"${gv}B", fontsize=11, color=MUTE, va="center", ha="left")

# 1) Enterprise value (full bar)
ax.add_patch(Rectangle((cols["ev"] - bw/2, y0), bw, H(EV), facecolor=AMBER, zorder=3))
ax.text(cols["ev"], Y(EV) + 0.028, "$200B", fontsize=27, color=AMBER, weight="bold", ha="center")
ax.text(cols["ev"], y0 - 0.030, "enterprise", fontsize=15, color=WHITE, ha="center", weight="bold")
ax.text(cols["ev"], y0 - 0.058, "value", fontsize=15, color=WHITE, ha="center", weight="bold")

# 2) the net-debt slab (a floating decrement from EV down toward equity) -- the BRIDGE
ax.add_patch(Rectangle((cols["nd"] - bw/2, Y(EV - ND)), bw, H(ND), facecolor=RED, alpha=0.92, zorder=3))
ax.plot([cols["ev"] + bw/2, cols["nd"] - bw/2], [Y(EV), Y(EV)], color=MUTE, lw=1.2, ls=(0, (3, 3)), zorder=2)
ax.plot([cols["nd"] + bw/2, cols["eq"] - bw/2], [Y(EV - ND), Y(EV - ND)], color=MUTE, lw=1.2, ls=(0, (3, 3)), zorder=2)
ax.text(cols["nd"], Y(EV) + 0.028, "- $39B", fontsize=22, color=RED, weight="bold", ha="center")
ax.text(cols["nd"], y0 - 0.030, "net debt", fontsize=15, color=RED, ha="center", weight="bold")
ax.text(cols["nd"], y0 - 0.058, "(+$3B affiliates)", fontsize=11.5, color=MUTE, ha="center")

# 3) Equity value (full bar)
ax.add_patch(Rectangle((cols["eq"] - bw/2, y0), bw, H(EQ), facecolor=TEAL, zorder=3))
ax.text(cols["eq"], Y(EQ) + 0.028, "$163B", fontsize=27, color=TEAL, weight="bold", ha="center")
ax.text(cols["eq"], y0 - 0.030, "equity", fontsize=15, color=WHITE, ha="center", weight="bold")
ax.text(cols["eq"], y0 - 0.058, "value", fontsize=15, color=WHITE, ha="center", weight="bold")

# ---------------- the per-share punchline ----------------
ax.add_patch(Rectangle((LX, 0.085), 0.83, 0.140, facecolor=PANEL, zorder=2))
ax.text(LX + 0.025, 0.190, "divide by 716M shares:", fontsize=15, color=MUTE, va="center", style="italic")
# wrong path
ax.text(LX + 0.025, 0.140, "$279", fontsize=33, color=RED, weight="bold", va="center")
ax.text(LX + 0.150, 0.150, "skip the bridge (EV / shares)", fontsize=13.5, color=WHITE, va="center")
ax.text(LX + 0.150, 0.118, "~3% from the real price -- looks fair", fontsize=12.5, color=RED, va="center")
# right path
ax.text(LX + 0.470, 0.140, "$228", fontsize=33, color=TEAL, weight="bold", va="center")
ax.text(LX + 0.595, 0.150, "cross it (equity / shares)", fontsize=13.5, color=WHITE, va="center")
ax.text(LX + 0.595, 0.118, "~20% overvalued -- the truth", fontsize=12.5, color=TEAL, va="center")
ax.add_patch(FancyArrowPatch((LX + 0.405, 0.140), (LX + 0.455, 0.140), arrowstyle="-|>,head_width=4,head_length=8",
             color=MUTE, lw=1.6, zorder=4))

# ---------------- footer ----------------
ax.text(LX, 0.045, "Two of the three crossed the bridge. The eval caught the one that didn't -",
        fontsize=13, color=MUTE, va="center")
ax.text(LX, 0.020, "and pinned exactly where it slipped.",
        fontsize=13, color=MUTE, va="center")
ax.text(0.915, 0.020, "finance-llm-evals  -  MIT", fontsize=11.5, color=FAINT, va="center", ha="right")

fig.savefig(os.path.join(HERE, "hero-eval3.png"), dpi=100, facecolor=BG)
print("wrote", os.path.join(HERE, "hero-eval3.png"))
