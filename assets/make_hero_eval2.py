#!/usr/bin/env python3
"""
assets/make_hero_eval2.py -- the eval #2 headline graphic, sibling to make_hero.py.
Output: assets/hero-eval2.png (1200x627, LinkedIn-article cover / README banner ratio).

Same visual grammar as eval #1's hero (the GAP is the diagnostic), applied to the PRODUCT
instead of the model: a buffer ETF's brochure cap (17.18%, stated for a day-1 buyer) vs. the
real REMAINING cap a mid-period buyer gets (6.06%, recomputed from the fund's actual filed
option strikes). Numbers are the real KOCT anchor case (cases/koct-op2026-anchor.case.yaml:
stated cap_gross 17.18%, C6 remaining_cap_gross 6.0598%).
Run: python assets/make_hero_eval2.py
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch

HERE = os.path.dirname(os.path.abspath(__file__))

INK = "#16243B"       # deep navy (primary text)
GRAY = "#5B6B7F"      # muted slate (secondary)
LIGHT = "#9AA7B6"     # light gray (footer)
GREEN = "#2E9E6B"     # "on the brochure / stated" (appealing but applies only at day 1)
CRIMSON = "#CC4B5C"   # "what today's buyer gets" (the honest figure)
RULE = "#E5EAF0"

fig = plt.figure(figsize=(12, 6.27), dpi=100)
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
ax.add_patch(Rectangle((0, 0), 1, 1, color="white", zorder=0))
ax.add_patch(Rectangle((0, 0), 0.016, 1, color=INK, zorder=2))            # left accent bar

# ---- left column: the words ----
LX = 0.065
ax.text(LX, 0.885, "A  R U N N A B L E ,   R U B R I C - G R A D E D   E V A L   F O R   B U F F E R - E T F   D I L I G E N C E",
        fontsize=11.0, color=GRAY, weight="bold", va="center")
ax.text(LX, 0.745, "The cap they quote", fontsize=38, color=INK, weight="bold", va="center")
ax.text(LX, 0.628, "isn’t the cap you get", fontsize=38, color=CRIMSON, weight="bold", va="center")
ax.text(LX, 0.505, "Can an LLM run a buffer-ETF advisor’s diligence?",
        fontsize=15.5, color=GRAY, va="center")
# caption
ax.text(LX, 0.235, "Brochure cap 17.18% — a mid-period buyer’s real remaining cap: 6.06%.",
        fontsize=14.0, color=INK, va="center")
ax.text(LX, 0.175, "Recomputed from the fund’s actual filed option strikes.",
        fontsize=14.0, color=GRAY, va="center")
ax.text(LX, 0.075, "18 checkpoints  ·  the free-lunch gate  ·  gold cases from real SEC filings",
        fontsize=12, color=LIGHT, va="center")

# ---- right column: the two bars (the GAP) ----
yb, ytop = 0.16, 0.60                       # baseline and axis-top (data y)
VMAX = 18.0                                 # % axis so the 17.18 bar nearly fills
def bar_top(v): return yb + (v / VMAX) * (ytop - yb)
b1x, b2x, bw = 0.685, 0.875, 0.095
v1, v2 = 17.18, 6.06

# faint "what the brochure implies" full bar behind the honest bar, to show the collapse
ax.add_patch(Rectangle((b2x - bw/2, yb), bw, bar_top(v1) - yb, facecolor=CRIMSON, alpha=0.10, zorder=1))
ax.add_patch(Rectangle((b1x - bw/2, yb), bw, bar_top(v1) - yb, facecolor=GREEN, alpha=0.90, zorder=2))
ax.add_patch(Rectangle((b2x - bw/2, yb), bw, bar_top(v2) - yb, facecolor=CRIMSON, alpha=0.92, zorder=3))

# drop arrow from the green top to the crimson top
ax.add_patch(FancyArrowPatch((b1x, bar_top(v1) + 0.005), (b2x, bar_top(v2) + 0.02),
             connectionstyle="arc3,rad=-0.32", arrowstyle="-|>,head_width=4,head_length=8",
             color=GRAY, lw=1.6, zorder=4))
ax.text((b1x + b2x)/2 + 0.005, bar_top(v1) + 0.075, "mid-period entry", fontsize=11.5,
        color=GRAY, style="italic", ha="center", va="center")

# big numbers + labels
ax.text(b1x, bar_top(v1) + 0.055, "17%", fontsize=33, color=GREEN, weight="bold", ha="center", va="center")
ax.text(b2x, bar_top(v2) + 0.055, "6%", fontsize=33, color=CRIMSON, weight="bold", ha="center", va="center")
ax.text(b1x, yb - 0.045, "stated cap", fontsize=13, color=GRAY, ha="center", va="center")
ax.text(b2x, yb - 0.045, "remaining cap", fontsize=13, color=GRAY, ha="center", va="center")
ax.plot([b1x - bw/2 - 0.02, b2x + bw/2 + 0.02], [yb, yb], color=RULE, lw=1.4, zorder=1)

fig.savefig(os.path.join(HERE, "hero-eval2.png"), dpi=100, facecolor="white")
print("wrote", os.path.join(HERE, "hero-eval2.png"))
