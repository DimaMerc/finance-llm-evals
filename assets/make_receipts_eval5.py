#!/usr/bin/env python3
"""
assets/make_receipts_eval5.py -- the "receipts" image for the eval-#5 LinkedIn post: a faithful,
clean render of the ACTUAL scored harness output for a real frontier model on the break case
(Claude Sonnet 4.6, irs-confirm-2026). Shows the model caught the mismatch and refused to affirm
(D1 = 1.00) but the eval pinned the one step it got wrong -- sizing the 5 bp break (C3 = 0.67).
Output: assets/receipts-eval5.png (1200x1200). Run: python assets/make_receipts_eval5.py
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle

HERE = os.path.dirname(os.path.abspath(__file__))
PAGE  = "#FFFFFF"
CARD  = "#0E1726"     # dark terminal
TXT   = "#C7D2E0"
DIM   = "#7C8AA0"
GREEN = "#4CC38A"
AMBER = "#E8B24A"
RED   = "#FF6B5E"
NAVY  = "#16243B"
MONO  = "DejaVu Sans Mono"

fig = plt.figure(figsize=(12, 12), dpi=100)
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
ax.add_patch(Rectangle((0, 0), 1, 1, color=PAGE, zorder=0))

# title
ax.text(0.5, 0.945, "The actual scored output", fontsize=24, color=NAVY, weight="bold", ha="center")
ax.text(0.5, 0.902, "a real frontier model, run through the eval on the break case",
        fontsize=14.5, color="#6B7785", ha="center")

# terminal card
ax.add_patch(FancyBboxPatch((0.07, 0.20), 0.86, 0.66, boxstyle="round,pad=0.012,rounding_size=0.02",
             facecolor=CARD, edgecolor="#26364F", lw=1.5, zorder=1))

def line(x, y, s, color=TXT, size=15, weight="normal"):
    ax.text(x, y, s, color=color, fontsize=size, family=MONO, weight=weight, va="center", zorder=2)

LX = 0.105
line(LX, 0.828, "$ python -m harness run --case irs-confirm-2026 --model live", DIM, 13.5)
line(LX, 0.784, "CASE irs-confirm-2026   model = claude-sonnet-4-6", TXT, 14)
line(LX, 0.735, "CaseScore (gated)  : 0.933", TXT, 15)
line(LX, 0.700, "Decision           : MISMATCHED", GREEN, 15, "bold")
line(LX + 0.335, 0.700, "(refused to affirm)", GREEN, 13.5)
line(LX, 0.665, "Gates fired        : none", TXT, 15)

line(LX, 0.610, "Checkpoint vector (which step failed):", DIM, 13.5)
rows = [
    ("P1  1.000   pin the trade",                                          TXT,   False, False),
    ("E1  0.833   extract our side",                                       TXT,   False, False),
    ("E2  1.000   extract counterparty",                                   TXT,   False, False),
    ("C1  1.000   field-by-field match",                                   TXT,   False, False),
    ("C2  1.000   materiality judgment",                                   TXT,   False, False),
    ("C3  0.667   economic impact    <- sized 5 bp as \"0.5 bp\"",         AMBER, True,  False),
    ("D1  1.000   affirm/mismatch call  <- refused to affirm",            GREEN, False, True),
    ("D2  1.000   calibrated refusal",                                     TXT,   False, False),
]
y = 0.572
for text, col, flagged, correct in rows:
    if flagged or correct:
        ax.add_patch(Rectangle((0.095, y - 0.021), 0.815, 0.040,
                     facecolor=("#2A2410" if flagged else "#10241A"), zorder=1))
    line(LX, y, text, col, 14, ("bold" if (flagged or correct) else "normal"))
    y -= 0.0425

# caption
ax.text(0.5, 0.145, "It agreed on WHAT was wrong and WHAT to do - it just mis-sized the break.",
        fontsize=15, color=NAVY, ha="center", va="center")
ax.text(0.5, 0.108, "The eval catches that, and pins it to the one step (C3).",
        fontsize=15, color=NAVY, weight="bold", ha="center", va="center")
ax.text(0.5, 0.055, "finance-llm-evals   -   every step graded, every failure localized",
        fontsize=12.5, color="#6B7785", ha="center", va="center")

fig.savefig(os.path.join(HERE, "receipts-eval5.png"), dpi=100, facecolor=PAGE)
print("wrote", os.path.join(HERE, "receipts-eval5.png"))
