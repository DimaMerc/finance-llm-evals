#!/usr/bin/env python3
"""
assets/make_hero_eval3.py -- hero image for the eval-#3 (DCF) LinkedIn post/article.
Output: assets/hero-eval3.png (1200x1200 square, LinkedIn feed).

The signature "looks right vs is right" trap an LLM must avoid on a DCF: divide enterprise value by
shares and skip the net-debt bridge -> ~$279 (looks ~fair vs McDonald's ~$286 price); do it correctly
-> ~$228 (~20% overvalued). Footer ties it to the three-frontier-model test. Brand-consistent with the
eval-#2 hero set. Run: python assets/make_hero_eval3.py
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
# --- header ---
ax.text(LX, 0.935, "C A N   A N   A I   V A L U E   A   C O M P A N Y ?",
        fontsize=15.5, color=GRAY, weight="bold", va="center")
ax.text(LX, 0.860, "Looks right", fontsize=46, color=INK, weight="bold", va="center")
ax.text(LX + 0.420, 0.860, "is not", fontsize=46, color=GRAY, weight="bold", va="center", style="italic")
ax.text(LX, 0.788, "is right.", fontsize=46, color=CRIMSON, weight="bold", va="center")
ax.text(LX, 0.722, "A discounted-cash-flow valuation of McDonald's. The same model, one omitted step.",
        fontsize=15.5, color=GRAY, va="center")

# --- the two numbers ---
yb, yt, ybar = 0.255, 0.560, 0.255
def bar_h(v, vmax=300.0): return (v / vmax) * (yt - yb)
b1x, b2x, bw = 0.33, 0.66, 0.165
v1, v2 = 279.0, 228.0   # EV/shares blunder vs the correct equity-bridge value

# faint full-height ghost on the wrong bar to show what's "lost" to the bridge
ax.add_patch(Rectangle((b1x - bw/2, yb), bw, bar_h(v1), facecolor=CRIMSON, alpha=0.90, zorder=2))
ax.add_patch(Rectangle((b2x - bw/2, yb), bw, bar_h(v1), facecolor=GREEN, alpha=0.10, zorder=1))
ax.add_patch(Rectangle((b2x - bw/2, yb), bw, bar_h(v2), facecolor=GREEN, alpha=0.92, zorder=3))

# the dropped net-debt slab annotation on the green bar
ax.add_patch(FancyArrowPatch((b1x, bar_h(v1) + yb + 0.006), (b2x, bar_h(v2) + yb + 0.012),
             connectionstyle="arc3,rad=-0.28", arrowstyle="-|>,head_width=5,head_length=10",
             color=GRAY, lw=1.8, zorder=4))
ax.text((b1x + b2x)/2, 0.640, "subtract", fontsize=13.5, color=GRAY, style="italic", ha="center")
ax.text((b1x + b2x)/2, 0.610, "$40B net debt", fontsize=13.5, color=GRAY, style="italic", ha="center")

ax.text(b1x, bar_h(v1) + yb + 0.050, "$279", fontsize=44, color=CRIMSON, weight="bold", ha="center", va="center")
ax.text(b2x, bar_h(v2) + yb + 0.050, "$228", fontsize=44, color=GREEN, weight="bold", ha="center", va="center")
ax.text(b1x, yb - 0.034, "EV / shares", fontsize=16, color=INK, weight="bold", ha="center")
ax.text(b1x, yb - 0.066, "(net-debt bridge skipped)", fontsize=12.5, color=GRAY, ha="center")
ax.text(b1x, yb - 0.094, "~3% from price -- looks fair", fontsize=12.5, color=CRIMSON, ha="center")
ax.text(b2x, yb - 0.034, "equity / shares", fontsize=16, color=INK, weight="bold", ha="center")
ax.text(b2x, yb - 0.066, "(bridge done right)", fontsize=12.5, color=GRAY, ha="center")
ax.text(b2x, yb - 0.094, "~20% overvalued -- the truth", fontsize=12.5, color=GREEN, ha="center")
ax.plot([b1x - bw/2 - 0.03, b2x + bw/2 + 0.03], [yb, yb], color=RULE, lw=1.6, zorder=1)

# --- footer: the three-model result ---
ax.plot([LX, 0.925], [0.120, 0.120], color=RULE, lw=1.4)
ax.text(LX, 0.088, "I ran three frontier models through it.",
        fontsize=15, color=INK, weight="bold", va="center")
ax.text(LX, 0.055, "Two did textbook DCF correctly. One quietly broke the cash-flow math --",
        fontsize=13, color=GRAY, va="center")
ax.text(LX, 0.030, "the eval caught it and pinned the step. All three refused to compute the discount rate.",
        fontsize=13, color=GRAY, va="center")
ax.text(0.925, 0.030, "finance-llm-evals  -  MIT", fontsize=12, color=LIGHT, va="center", ha="right")

fig.savefig(os.path.join(HERE, "hero-eval3.png"), dpi=100, facecolor="white")
print("wrote", os.path.join(HERE, "hero-eval3.png"))
