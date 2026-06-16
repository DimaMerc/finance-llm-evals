#!/usr/bin/env python3
"""
assets/make_post_midperiod.py -- feed image for the "what a mid-period buyer gets" post.
Output: assets/post-midperiod.png (1200x1200 square, LinkedIn feed).
Brand-consistent with the hero set; real KOCT anchor numbers (stated cap 17.18% -> remaining
cap 6.06% eight months in; ~9.49% unbuffered gap). Run: python assets/make_post_midperiod.py
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch

HERE = os.path.dirname(os.path.abspath(__file__))
INK, GRAY, LIGHT = "#16243B", "#5B6B7F", "#9AA7B6"
GREEN, CRIMSON, RULE = "#2E9E6B", "#CC4B5C", "#E5EAF0"

fig = plt.figure(figsize=(12, 12), dpi=100)
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
ax.add_patch(Rectangle((0, 0), 1, 1, color="white", zorder=0))
ax.add_patch(Rectangle((0, 0), 0.016, 1, color=INK, zorder=2))

LX = 0.075
ax.text(LX, 0.935, "B U F F E R   E T F :   S T A T E D   vs   M I D - P E R I O D   C A P",
        fontsize=15, color=GRAY, weight="bold", va="center")
ax.text(LX, 0.855, "The cap on the brochure", fontsize=40, color=INK, weight="bold", va="center")
ax.text(LX, 0.785, "isn't the cap you get.", fontsize=40, color=CRIMSON, weight="bold", va="center")

# two bars
ybase, ytop, VMAX = 0.27, 0.66, 18.0
def bar_top(v): return ybase + (v / VMAX) * (ytop - ybase)
b1x, b2x, bw = 0.33, 0.66, 0.15
v1, v2 = 17.18, 6.06
ax.add_patch(Rectangle((b2x - bw/2, ybase), bw, bar_top(v1) - ybase, facecolor=CRIMSON, alpha=0.10, zorder=1))
ax.add_patch(Rectangle((b1x - bw/2, ybase), bw, bar_top(v1) - ybase, facecolor=GREEN, alpha=0.90, zorder=2))
ax.add_patch(Rectangle((b2x - bw/2, ybase), bw, bar_top(v2) - ybase, facecolor=CRIMSON, alpha=0.92, zorder=3))
ax.add_patch(FancyArrowPatch((b1x, bar_top(v1) + 0.004), (b2x, bar_top(v2) + 0.012),
             connectionstyle="arc3,rad=-0.30", arrowstyle="-|>,head_width=5,head_length=10",
             color=GRAY, lw=1.8, zorder=4))
ax.text((b1x + b2x)/2, 0.405, "8 months in,", fontsize=14, color=GRAY, style="italic", ha="center", va="center")
ax.text((b1x + b2x)/2, 0.365, "after a rally", fontsize=14, color=GRAY, style="italic", ha="center", va="center")
ax.text(b1x, bar_top(v1) + 0.045, "17%", fontsize=42, color=GREEN, weight="bold", ha="center", va="center")
ax.text(b2x, bar_top(v2) + 0.045, "~6%", fontsize=42, color=CRIMSON, weight="bold", ha="center", va="center")
ax.text(b1x, ybase - 0.035, "stated cap (day 1)", fontsize=16, color=GRAY, ha="center", va="center")
ax.text(b2x, ybase - 0.035, "remaining cap (today)", fontsize=16, color=GRAY, ha="center", va="center")
ax.plot([b1x - bw/2 - 0.03, b2x + bw/2 + 0.03], [ybase, ybase], color=RULE, lw=1.6, zorder=1)

ax.text(LX, 0.150, "...and a ~9.5% gap before the \"15% buffer\" even starts.",
        fontsize=18, color=INK, va="center")
ax.text(LX, 0.065, "Real fund, real filing - recomputed from its actual option strikes.",
        fontsize=13.5, color=LIGHT, va="center")

fig.savefig(os.path.join(HERE, "post-midperiod.png"), dpi=100, facecolor="white")
print("wrote", os.path.join(HERE, "post-midperiod.png"))
