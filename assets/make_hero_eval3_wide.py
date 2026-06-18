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
# thin amber rule down the middle gutter
ax.plot([0.520, 0.520], [0.16, 0.84], color=FAINT, lw=1.4, zorder=1)

# ---------------- LEFT: the question ----------------
LX = 0.055
ax.text(LX, 0.855, "THREE FRONTIER MODELS  -  ONE REAL DCF",
        fontsize=13, color=AMBER, weight="bold", va="center")
ax.text(LX, 0.690, "Can an AI", fontsize=46, color=WHITE, weight="bold", va="center")
ax.text(LX, 0.575, "value a company?", fontsize=46, color=WHITE, weight="bold", va="center")
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

# ---------------- RIGHT: the trap (enterprise value / shares) ----------------
RX = 0.575
ax.text(RX, 0.840, "E N T E R P R I S E   V A L U E   /   7 1 6 M   S H A R E S",
        fontsize=11.5, color=MUTE, weight="bold", va="center")

# wrong path
ax.text(RX, 0.690, "$279", fontsize=52, color=RED, weight="bold", va="center")
ax.text(RX + 0.165, 0.715, "skip the net-debt bridge", fontsize=14.5, color=WHITE, va="center", weight="bold")
ax.text(RX + 0.165, 0.672, "~3% from price -- looks fair", fontsize=13, color=RED, va="center")

# the bridge step between them
ax.add_patch(FancyArrowPatch((RX + 0.055, 0.610), (RX + 0.055, 0.470),
             arrowstyle="-|>,head_width=5,head_length=10", color=MUTE, lw=2.0, zorder=4))
ax.text(RX + 0.10, 0.540, "- $40B net debt", fontsize=14, color=AMBER, weight="bold", va="center")
ax.text(RX + 0.10, 0.500, "(the bridge to equity)", fontsize=12, color=MUTE, va="center")

# right path
ax.text(RX, 0.380, "$228", fontsize=52, color=TEAL, weight="bold", va="center")
ax.text(RX + 0.165, 0.405, "cross it (equity / shares)", fontsize=14.5, color=WHITE, va="center", weight="bold")
ax.text(RX + 0.165, 0.362, "~20% overvalued -- the truth", fontsize=13, color=TEAL, va="center")

fig.savefig(os.path.join(HERE, "hero-eval3-wide.png"), dpi=100, facecolor=BG)
print("wrote", os.path.join(HERE, "hero-eval3-wide.png"))
