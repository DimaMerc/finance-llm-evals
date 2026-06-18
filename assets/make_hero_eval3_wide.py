#!/usr/bin/env python3
"""
assets/make_hero_eval3_wide.py -- WIDE (1.91:1) variant of the eval-#3 hero, for the slots where
LinkedIn crops to a banner: the ARTICLE cover image and link previews. A square image gets
center-cropped there, which decapitates the headline; this lays the same story out horizontally so
nothing important is in the crop zone. Output: assets/hero-eval3-wide.png (1200x628).
Same dark palette as the square hero. Run: python assets/make_hero_eval3_wide.py
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch

HERE = os.path.dirname(os.path.abspath(__file__))
BG    = "#0F1D33"
PANEL = "#16263F"
AMBER = "#E8B24A"
TEAL  = "#34B5A0"
RED   = "#E0635E"
WHITE = "#EEF3F8"
MUTE  = "#8FA2BB"
FAINT = "#27395A"

W, H = 1200, 628
fig = plt.figure(figsize=(W / 100, H / 100), dpi=100)
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
ax.add_patch(Rectangle((0, 0), 1, 1, color=BG, zorder=0))
# thin rule down the middle gutter
ax.plot([0.560, 0.560], [0.16, 0.84], color=FAINT, lw=1.4, zorder=1)

# ---------------- LEFT: the question ----------------
LX = 0.055
ax.text(LX, 0.855, "THREE FRONTIER MODELS  -  ONE REAL DCF",
        fontsize=13, color=AMBER, weight="bold", va="center")
ax.text(LX, 0.690, "Can an AI", fontsize=42, color=WHITE, weight="bold", va="center")
ax.text(LX, 0.580, "value a company?", fontsize=42, color=WHITE, weight="bold", va="center")
ax.text(LX, 0.430, "On a real McDonald's DCF, it comes down to",
        fontsize=15, color=MUTE, va="center")
ax.text(LX, 0.388, "one subtraction most people skip.",
        fontsize=15, color=MUTE, va="center")
ax.text(LX, 0.165, "Two of three models crossed the bridge.",
        fontsize=13.5, color=WHITE, weight="bold", va="center")
ax.text(LX, 0.120, "The eval caught the one that didn't - and pinned the step.",
        fontsize=13, color=MUTE, va="center")
ax.text(LX, 0.062, "finance-llm-evals  -  MIT  -  every number from a real SEC filing",
        fontsize=11.5, color=FAINT, va="center")

# ---------------- RIGHT: the trap (enterprise value / shares) -- stacked, no horizontal collisions ----------------
RX = 0.605
ax.text(RX, 0.850, "ENTERPRISE VALUE  /  716M SHARES",
        fontsize=12.5, color=MUTE, weight="bold", va="center")

# wrong path -- number on its own line, label stacked BELOW it
ax.text(RX, 0.715, "$279", fontsize=46, color=RED, weight="bold", va="center")
ax.text(RX, 0.628, "skip the net-debt bridge", fontsize=15, color=WHITE, weight="bold", va="center")
ax.text(RX, 0.588, "~3% from the price -- looks fair", fontsize=13, color=RED, va="center")

# the bridge step between the two numbers
ax.add_patch(FancyArrowPatch((RX + 0.025, 0.535), (RX + 0.025, 0.475),
             arrowstyle="-|>,head_width=5,head_length=10", color=MUTE, lw=2.0, zorder=4))
ax.text(RX + 0.075, 0.505, "minus $40B net debt", fontsize=13.5, color=AMBER, weight="bold", va="center")

# right path
ax.text(RX, 0.360, "$228", fontsize=46, color=TEAL, weight="bold", va="center")
ax.text(RX, 0.273, "cross it (equity / shares)", fontsize=15, color=WHITE, weight="bold", va="center")
ax.text(RX, 0.233, "~20% overvalued -- the truth", fontsize=13, color=TEAL, va="center")

fig.savefig(os.path.join(HERE, "hero-eval3-wide.png"), dpi=100, facecolor=BG)
print("wrote", os.path.join(HERE, "hero-eval3-wide.png"))
