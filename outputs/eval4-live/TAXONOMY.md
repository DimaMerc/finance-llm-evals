# Eval #4 live runs — ETF creation/redemption basket reconciliation

Three frontier models (Claude **Opus 4.8** / **Sonnet 4.6** / **Haiku 4.5**, via the Anthropic
OpenAI-compatible endpoint) on both gold cases — the **break** case (`grin-create-2026`, a creation
short $13,320 on a stale cash-in-lieu) and the **clean-settle** case (`grin-create-2026-clean`, the
same order delivered correctly so it ties). Deterministic core + offline judge. Each model is given
the order ticket, the published PCF, and the AP's delivered basket, and must reconcile, compute the
tie-out, and decide. Reproduce: `python outputs/run_live_eval4.py --model-id <id> --case <case>`.

## The matrix

| Model | Break case (gated) | Gate fired | Clean case (gated) | False break? |
|---|---:|---|---:|---|
| **Opus 4.8** | **0.983** | none | 0.983 | no (correct SETTLE) |
| **Sonnet 4.6** | **0.943** | none | 0.983 | no (correct SETTLE) |
| **Haiku 4.5** | **0.496** | **GATE.SCALE** | 0.983 | no (correct SETTLE) |

## What the runs show

**The two strong models reconcile to the dollar.** On the break case, Opus and Sonnet both compute
the in-kind market value exactly ($2,838,400), value the RBLX cash-in-lieu at the **struck** price
($112.40, not the AP's stale $105.00), land the tie-out residual at exactly **−$13,320**, return
**DO_NOT_SETTLE** localized to the RBLX cash-in-lieu line, and answer the D2 probe correctly
(NOT_DISCLOSED for the halted name's official close; the −$13,320 residual as the answerable twin).
Textbook fund-accounting reconciliation. The 0.983 ceiling (not 1.000) is a single PCF-**citation**
entailment miss — the model cited a different verbatim than the gold's exact string — a
citation-format nicety, not a reconciliation error.

**The weak model catches that something is wrong, but its own arithmetic is off — and it mis-signs
the break.** Haiku overstates the in-kind market value by **exactly $200,000** ($3,038,400 vs the
correct $2,838,400 — an arithmetic slip summing the basket), which cascades: total tendered
$3,261,680, residual **+$186,680**. So Haiku concludes the basket is **over**-delivered by $186,680
— when it is actually **short** by $13,320. It still returns DO_NOT_SETTLE (the right *call*), but it
has the break **completely mischaracterized** (over vs. short), and its answerable-twin residual is
wrong (R=0.0). The eval localizes this precisely: **GATE.SCALE** fires (the valuation is >1% off),
and the wrong twin drops the calibrated-refusal R — the math error is pinned to C2, not smeared
across the whole case. On the **clean** case Haiku values correctly ($2,838,400, residual 0) and
settles, so the $200k error was a **one-off slip**, not a systematic weakness.

**Both directions of the decision are calibrated.** On the clean-settle case all three models
correctly **SETTLE** — none cried break on a basket that ties (no `D1.n_falsebreak`). So the eval
confirms the control works in both directions: catch the break that exists, don't invent one that
doesn't.

## The honest negative result

**No model approved a real break.** Across all six runs, `GATE.RECON` — the signature, *settle a
basket that does not reconcile* — never fired. All three frontier models refused to settle the
$13,320-short basket. So on this case the marquee failure mode did **not** appear in frontier
models; the capability difference surfaced instead as Haiku's $200k valuation error and the
resulting sign-flip, which the eval still caught and localized. That is the correct, non-overclaiming
read: the gate is the right *control*, and these models pass it — what separates them is the
arithmetic underneath.

## Caveats

- **n = 1 per case, single model family.** All three subjects are Claude; a cross-family run
  (GPT / Gemini) is the honest next step to separate "the task's difficulty" from "this family's
  behavior" — the same caveat carried on evals #2–#3.
- **Constructed case.** PCFs are NSCC-disseminated, not public filings, so the gold is a
  mechanics-faithful constructed scenario (real constituent securities and representative prices;
  fictional fund, illustrative order and break). The *mechanics* are real; the specific basket is not
  sourced.
- The break is **discoverable** from the packet (the PCF struck price $112.40 vs the AP's delivered
  $105.00 are both shown) — the test is whether the model does the reconciliation arithmetic and the
  decision correctly, not whether it can find hidden data.

Artifacts (parsed answer, raw completion, scored report) per model+case under
`outputs/eval4-live/<model>/<case>/`.
