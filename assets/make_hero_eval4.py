#!/usr/bin/env python3
"""
assets/make_hero_eval4.py -- hero image for the eval-#4 (ETF creation/redemption reconciliation)
LinkedIn post. Output: assets/hero-eval4.png (1200x1200 square, LinkedIn feed).

The image IS the post: a basket reconciliation that comes up SHORT $13,320 -> DO NOT SETTLE. Clean,
operational, ledger-style. ETF-family palette (white background, navy / forest-green / crimson) --
the eval-1/2 brand, since this is ETF-adjacent (not the dark DCF look). Run: python assets/make_hero_eval4.py
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch

HERE = os.path.dirname(os.path.abspath(__file__))
BG    = "#FFFFFF"
PANEL = "#F2F5F8"
NAVY  = "#16243B"
GREEN = "#2E7D5B"
RED   = "#C0392B"
MUTE  = "#6B7785"
LINE  = "#C9D3DE"
MONO  = "DejaVu Sans Mono"

fig = plt.figure(figsize=(12, 12), dpi=100)
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
ax.add_patch(Rectangle((0, 0), 1, 1, color=BG, zorder=0))

# ---------------- header ----------------
ax.text(0.5, 0.940, "D O E S   T H E   B A S K E T   T I E   O U T ?",
        fontsize=30, color=NAVY, weight="bold", ha="center", va="center")
ax.text(0.5, 0.892, "An ETF creation: 50,000 new shares, paid for with a basket of stocks + cash.",
        fontsize=15.5, color=MUTE, ha="center", va="center")
ax.plot([0.08, 0.92], [0.862, 0.862], color=LINE, lw=1.4, zorder=1)

# ---------------- two panels: DELIVERED vs REQUIRED ----------------
def panel(x0, x1, y0, y1, title, title_color):
    ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, facecolor=PANEL, edgecolor=LINE, lw=1.2, zorder=1))
    ax.text((x0 + x1) / 2, y1 - 0.040, title, fontsize=15.5, color=title_color, weight="bold",
            ha="center", va="center")

PL0, PL1 = 0.075, 0.485      # left panel (delivered)
PR0, PR1 = 0.515, 0.925      # right panel (required)
PY0, PY1 = 0.560, 0.835
panel(PL0, PL1, PY0, PY1, "WHAT THE FIRM DELIVERED", NAVY)
panel(PR0, PR1, PY0, PY1, "WHAT THE SHARES ARE WORTH", NAVY)

def row(lx, rx, y, label, value, lc=NAVY, vc=NAVY, lw="normal", vw="bold", fs=15):
    ax.text(lx, y, label, fontsize=fs, color=lc, weight=lw, va="center")
    ax.text(rx, y, value, fontsize=fs, color=vc, weight=vw, va="center", ha="right",
            family=MONO)

# left panel rows
row(PL0 + 0.022, PL1 - 0.022, 0.745, "stocks (in-kind)", "$2,838,400")
row(PL0 + 0.022, PL1 - 0.022, 0.700, "cash component", "$  223,280")
ax.plot([PL0 + 0.022, PL1 - 0.022], [0.672, 0.672], color=LINE, lw=1.2)
row(PL0 + 0.022, PL1 - 0.022, 0.640, "total tendered", "$3,061,680", lc=NAVY, vc=NAVY, lw="bold")

# right panel rows
row(PR0 + 0.022, PR1 - 0.022, 0.745, "creation value", "$3,075,000", lc=NAVY, vc=NAVY, lw="bold")
ax.text(PR0 + 0.022, 0.700, "50,000 shares x $61.50 NAV", fontsize=13, color=MUTE, va="center")
ax.text(PR0 + 0.022, 0.612, "every share line matched.", fontsize=13, color=MUTE, va="center", style="italic")
ax.text(PR0 + 0.022, 0.582, "only the cash was short.", fontsize=13, color=MUTE, va="center", style="italic")

# the "vs" connector between panels
ax.text(0.500, 0.700, "vs", fontsize=16, color=MUTE, ha="center", va="center", style="italic")

# ---------------- the gap / verdict ----------------
ax.add_patch(Rectangle((0.075, 0.345), 0.850, 0.150, facecolor=NAVY, zorder=2))
ax.text(0.215, 0.450, "THE GAP", fontsize=14, color="#9FB0C4", weight="bold", ha="center", va="center")
ax.text(0.215, 0.398, "SHORT", fontsize=20, color="#E8C9C4", weight="bold", ha="center", va="center")
ax.text(0.215, 0.362, "(a halted stock's cash, priced stale)", fontsize=11.5, color="#9FB0C4",
        ha="center", va="center")
ax.text(0.500, 0.420, "$13,320", fontsize=56, color="#FF6B5E", weight="bold", ha="center", va="center",
        family=MONO)
ax.add_patch(FancyArrowPatch((0.660, 0.420), (0.715, 0.420),
             arrowstyle="-|>,head_width=5,head_length=10", color="#9FB0C4", lw=2.2, zorder=3))
ax.text(0.820, 0.435, "DO NOT", fontsize=22, color="#FF6B5E", weight="bold", ha="center", va="center")
ax.text(0.820, 0.392, "SETTLE", fontsize=22, color="#FF6B5E", weight="bold", ha="center", va="center")

# ---------------- the AI result (the honest footer) ----------------
ax.text(0.5, 0.250, "Three frontier AI models reconciled this basket.",
        fontsize=16.5, color=NAVY, weight="bold", ha="center", va="center")
ax.text(0.5, 0.205, "None rubber-stamped it. The two strongest caught the $13,320 to the dollar;",
        fontsize=14, color=MUTE, ha="center", va="center")
ax.text(0.5, 0.173, "the weak one refused too - but its own math was off by $200,000.",
        fontsize=14, color=MUTE, ha="center", va="center")
ax.text(0.5, 0.130, "The eval pinned exactly where each one broke.",
        fontsize=14, color=GREEN, weight="bold", ha="center", va="center")

# ---------------- footer ----------------
ax.plot([0.08, 0.92], [0.075, 0.075], color=LINE, lw=1.4)
ax.text(0.5, 0.045, "finance-llm-evals   -   MIT   -   a runnable ETF creation/redemption reconciliation eval",
        fontsize=12.5, color=MUTE, ha="center", va="center")

fig.savefig(os.path.join(HERE, "hero-eval4.png"), dpi=100, facecolor=BG)
print("wrote", os.path.join(HERE, "hero-eval4.png"))
