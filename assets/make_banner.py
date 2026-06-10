#!/usr/bin/env python3
"""
assets/make_banner.py -- LinkedIn profile banner (1584x396) in the hero.png style.

Layout constraint: LinkedIn overlays the circular profile photo on the banner's BOTTOM-LEFT
(roughly the left ~25% width, lower two-thirds), so all content sits right of x~0.28 and the
left zone stays decorative only.

Numbers are the real Snowflake scale-slip result (0.951 ungated -> 0.452 gated).
Run: python assets/make_banner.py
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch

HERE = os.path.dirname(os.path.abspath(__file__))

INK = "#16243B"
GRAY = "#5B6B7F"
LIGHT = "#9AA7B6"
GREEN = "#2E9E6B"
CRIMSON = "#CC4B5C"
RULE = "#E5EAF0"
FAINT = "#F3F6F9"

fig = plt.figure(figsize=(15.84, 3.96), dpi=100)
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
ax.add_patch(Rectangle((0, 0), 1, 1, color="white", zorder=0))

# decorative left zone (safe under the avatar): soft navy panel + accent edge
ax.add_patch(Rectangle((0, 0), 0.26, 1, color=FAINT, zorder=1))
ax.add_patch(Rectangle((0.26, 0), 0.004, 1, color=INK, zorder=2))

# ---- text block (starts right of the avatar zone) ----
TX = 0.30
ax.text(TX, 0.80, "A  R U N N A B L E ,   R U B R I C - G R A D E D   E V A L   F O R   F I N A N C E   L L M s",
        fontsize=10.5, color=GRAY, weight="bold", va="center")
ax.text(TX, 0.50, "Looks right", fontsize=44, color=INK, weight="bold", va="center")
ax.text(TX + 0.29, 0.50, "≠ is right", fontsize=44, color=CRIMSON, weight="bold", va="center")
ax.text(TX, 0.17, "17 checkpoints  ·  gating rubric  ·  gold cases from real SEC filings",
        fontsize=14, color=GRAY, va="center")

# ---- compact bars, far right ----
yb, ytop = 0.16, 0.66
def bar_top(v): return yb + v * (ytop - yb)
b1x, b2x, bw = 0.845, 0.94, 0.05
v1, v2 = 0.951, 0.452
ax.add_patch(Rectangle((b2x - bw/2, yb), bw, bar_top(v1) - yb, facecolor=CRIMSON, alpha=0.10, zorder=1))
ax.add_patch(Rectangle((b1x - bw/2, yb), bw, bar_top(v1) - yb, facecolor=GREEN, alpha=0.90, zorder=2))
ax.add_patch(Rectangle((b2x - bw/2, yb), bw, bar_top(v2) - yb, facecolor=CRIMSON, alpha=0.92, zorder=3))
ax.add_patch(FancyArrowPatch((b1x, bar_top(v1) + 0.01), (b2x, bar_top(v2) + 0.04),
             connectionstyle="arc3,rad=-0.35", arrowstyle="-|>,head_width=3.5,head_length=7",
             color=GRAY, lw=1.5, zorder=4))
ax.text(b1x, bar_top(v1) + 0.13, "95%", fontsize=22, color=GREEN, weight="bold", ha="center", va="center")
ax.text(b2x, bar_top(v2) + 0.13, "45%", fontsize=22, color=CRIMSON, weight="bold", ha="center", va="center")
ax.text(b1x, yb - 0.085, "naive", fontsize=11.5, color=GRAY, ha="center", va="center")
ax.text(b2x, yb - 0.085, "honest", fontsize=11.5, color=GRAY, ha="center", va="center")
ax.plot([b1x - bw/2 - 0.012, b2x + bw/2 + 0.012], [yb, yb], color=RULE, lw=1.3, zorder=1)

fig.savefig(os.path.join(HERE, "banner.png"), dpi=100, facecolor="white")
print("wrote", os.path.join(HERE, "banner.png"))
