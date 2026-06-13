#!/usr/bin/env python3
"""
assets/make_hero_eval2.py -- the eval #2 headline graphic.
Output: assets/hero-eval2.png (1200x627, LinkedIn-article cover / README banner ratio).

Shares eval #1's brand (navy ink, green/crimson semantics, the left accent bar) but a DIFFERENT
composition -- a scorecard, not the two-bar GAP chart -- so the sequel reads as new at thumbnail
scale. The message matches the reworked article: can you trust an AI analyst, and exactly where?
The four rows are the real finding (taxonomy / PAPER §3.2): strong on extraction + the single
headline calc, weak on the multi-step options math and the risk-state read.
Run: python assets/make_hero_eval2.py
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyBboxPatch

HERE = os.path.dirname(os.path.abspath(__file__))

INK = "#16243B"       # deep navy (primary text)
GRAY = "#5B6B7F"      # muted slate (secondary)
LIGHT = "#9AA7B6"     # light gray (footer)
GREEN = "#2E9E6B"     # holds up
CRIMSON = "#CC4B5C"   # breaks
RULE = "#E5EAF0"
CARD = "#F5F8FB"      # scorecard fill

fig = plt.figure(figsize=(12, 6.27), dpi=100)
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
ax.add_patch(Rectangle((0, 0), 1, 1, color="white", zorder=0))
ax.add_patch(Rectangle((0, 0), 0.016, 1, color=INK, zorder=2))            # left accent bar

# ---- left column: the words ----
LX = 0.065
ax.text(LX, 0.885, "A  R U N N A B L E ,   R U B R I C - G R A D E D   E V A L   F O R   F I N A N C E   L L M s",
        fontsize=11.0, color=GRAY, weight="bold", va="center")
ax.text(LX, 0.730, "Can you trust", fontsize=43, color=INK, weight="bold", va="center")
ax.text(LX, 0.610, "an AI analyst?", fontsize=43, color=INK, weight="bold", va="center")
ax.text(LX, 0.470, "I built the test that says — checkpoint", fontsize=16, color=GRAY, va="center")
ax.text(LX, 0.420, "by checkpoint — exactly where.", fontsize=16, color=GRAY, va="center")
ax.text(LX, 0.150, "Buffer-ETF diligence: recompute the marketing", fontsize=13, color=GRAY, va="center")
ax.text(LX, 0.100, "from the fund’s real option math, or fail.", fontsize=13, color=GRAY, va="center")
ax.text(LX, 0.040, "18 checkpoints  ·  the free-lunch gate  ·  gold cases from real SEC filings",
        fontsize=11, color=LIGHT, va="center")

# ---- right column: the scorecard ----
CX0, CX1 = 0.520, 0.950
ax.add_patch(FancyBboxPatch((CX0, 0.205), CX1 - CX0, 0.625, boxstyle="round,pad=0.012,rounding_size=0.02",
             facecolor=CARD, edgecolor=RULE, lw=1.3, zorder=1))
TX = CX0 + 0.028
ax.text(TX, 0.770, "W H E R E   I T   H E L D   U P   —   A N D   B R O K E",
        fontsize=10.5, color=GRAY, weight="bold", va="center")
ax.plot([TX, CX1 - 0.028], [0.730, 0.730], color=RULE, lw=1.2, zorder=2)

rows = [
    (GREEN, "✓", "Pulls & cites every figure"),
    (GREEN, "✓", "Computes the one headline cap"),
    (CRIMSON, "✗", "The multi-step options math"),
    (CRIMSON, "✗", "Reading the real risk state"),
]
ys = [0.650, 0.530, 0.410, 0.290]
for (col, mark, label), y in zip(rows, ys):
    ax.text(TX + 0.004, y, mark, fontsize=21, color=col, weight="bold", va="center", ha="left")
    ax.text(TX + 0.055, y, label, fontsize=15.5, color=INK, va="center", ha="left")

ax.text((CX0 + CX1) / 2, 0.150, "two open models  ·  the gap is the finding",
        fontsize=11, color=LIGHT, va="center", ha="center", style="italic")

fig.savefig(os.path.join(HERE, "hero-eval2.png"), dpi=100, facecolor="white")
print("wrote", os.path.join(HERE, "hero-eval2.png"))
