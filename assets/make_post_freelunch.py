#!/usr/bin/env python3
"""
assets/make_post_freelunch.py -- feed image for the "protection is never free" post.
Output: assets/post-freelunch.png (1200x1200 square, LinkedIn feed).
A simple structure diagram: the buffer (a put spread you get) is paid for by the cap (a call the
fund sells) - and the cap IS that call's strike. Brand-consistent with the hero set.
Run: python assets/make_post_freelunch.py
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyBboxPatch, FancyArrowPatch

HERE = os.path.dirname(os.path.abspath(__file__))
INK, GRAY, LIGHT = "#16243B", "#5B6B7F", "#9AA7B6"
GREEN, CRIMSON, RULE = "#2E9E6B", "#CC4B5C", "#E5EAF0"
GREENF, CRIMSONF = "#EAF6F0", "#FBECEE"   # soft fills

fig = plt.figure(figsize=(12, 12), dpi=100)
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
ax.add_patch(Rectangle((0, 0), 1, 1, color="white", zorder=0))
ax.add_patch(Rectangle((0, 0), 0.016, 1, color=INK, zorder=2))

LX = 0.075
ax.text(LX, 0.935, "W H A T   T H E   B R O C H U R E   D O E S N ' T   S P E L L   O U T",
        fontsize=15, color=GRAY, weight="bold", va="center")
ax.text(LX, 0.850, "Protection is never free.", fontsize=44, color=INK, weight="bold", va="center")

# two linked boxes
BXW = 0.85
def box(y, h, fill, edge, big, sub, small):
    ax.add_patch(FancyBboxPatch((LX, y), BXW, h, boxstyle="round,pad=0.006,rounding_size=0.018",
                 facecolor=fill, edgecolor=edge, lw=1.8, zorder=1))
    ax.text(LX + 0.035, y + h - 0.058, big, fontsize=23, color=edge, weight="bold", va="center")
    ax.text(LX + 0.035, y + h - 0.110, sub, fontsize=17, color=INK, va="center")
    ax.text(LX + 0.035, y + h - 0.150, small, fontsize=14, color=GRAY, style="italic", va="center")

box(0.560, 0.180, GREENF, GREEN,
    "WHAT YOU GET   -   the buffer", "First 15% of losses absorbed.",
    "A purchased put spread. It costs real money.")
box(0.265, 0.180, CRIMSONF, CRIMSON,
    "WHAT YOU GIVE UP   -   the cap", "Upside capped at ~17%.",
    "A call the fund sells - to pay for the buffer above.")

# connector
ax.add_patch(FancyArrowPatch((0.50, 0.560), (0.50, 0.445),
             arrowstyle="-|>,head_width=6,head_length=12", color=GRAY, lw=2.0, zorder=3))
ax.text(0.535, 0.502, "paid for by", fontsize=16, color=GRAY, style="italic", va="center")

ax.text(LX, 0.165, "The cap is, almost literally, the strike of that sold call.",
        fontsize=19, color=INK, weight="bold", va="center")
ax.text(LX, 0.118, "Two sides of one transaction - not two separate features.",
        fontsize=16, color=GRAY, va="center")
ax.text(LX, 0.055, "Any analysis that names the protection but not its cost is selling a free lunch.",
        fontsize=13.5, color=LIGHT, va="center")

fig.savefig(os.path.join(HERE, "post-freelunch.png"), dpi=100, facecolor="white")
print("wrote", os.path.join(HERE, "post-freelunch.png"))
