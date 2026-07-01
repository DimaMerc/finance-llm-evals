# Eval #5 live runs — OTC derivative confirmation matching

Three frontier models (Claude **Opus 4.8** / **Sonnet 4.6** / **Haiku 4.5**, via the Anthropic
OpenAI-compatible endpoint) on both gold cases — the **break** case (`irs-confirm-2026`, a
counterparty confirmation with a 6.05% fixed rate where ours says 6.00%) and the **clean-match** case
(`irs-confirm-2026-clean`, the rates tie). Each model is given the two confirmations and must match
the economic terms field-by-field and affirm only if they tie. Reproduce:
`python outputs/run_live_eval5.py --model-id <id> --case <case>`.

## The matrix

| Model | Break case (gated) | Gate | Clean case (gated) | Affirmed a break? |
|---|---:|---|---:|---|
| **Opus 4.8** | **0.980** | none | 0.980 | no (correct MISMATCHED) |
| **Sonnet 4.6** | 0.933 | none | 0.980 | no (correct MISMATCHED) |
| **Haiku 4.5** | 0.933 | none | 0.980 | no (correct MISMATCHED) |

## What the runs show

**All three match correctly.** On the break case, every model compares the two confirmations
field-by-field, flags the fixed-rate difference as the material break (correctly treating the
differing trade ids `TW9235`/`SW2000` as *expected*, not a break), returns **MISMATCHED — do not
affirm**, and answers the D2 mark-to-market probe with NOT_DETERMINABLE. On the clean case all three
correctly **AFFIRM**. None affirmed a broken trade.

**The discriminator is the basis-point conversion — a classic finance-ops trap, and two of three
frontier models get it wrong, in opposite directions.** The break is 6.05% vs 6.00% = **5 bp ≈ EUR
25,000 per annum** on EUR 50MM:

- **Opus 4.8** — "~EUR 25,000 per year ... ~EUR 125,000 undiscounted over 5 years." **Correct.**
- **Sonnet 4.6** — "a **0.5 bp** discrepancy ... ~EUR 2,500 per annum." **10× too small** (called
  0.05% "0.5 bp").
- **Haiku 4.5** — "a **50 basis point** difference ... ~EUR 2,500,000." **10× too big** (called
  0.05% "50 bp").

The eval localizes this to **C3.impact**: Opus scores it 1.0 (0.980 overall), Sonnet and Haiku 0.667
(0.933 overall). So the models agree on *what* is wrong (the rate) and *what to do* (don't affirm),
but disagree on *how big* — and only the strongest sizes it correctly. The remaining gap to a perfect
1.0 is a minor PCF-**citation** entailment miss at E1.

## The honest negative result

**`GATE.MATCH` never fired.** Across all six runs, no model affirmed a trade whose economic terms did
not tie — the signature failure this eval exists to catch did not appear in these frontier models.
As on eval #4, the capability difference surfaced not as the marquee failure but as the *quality of
the underlying quantification* (here, the basis-point conversion), which the eval still catches and
localizes.

## Two grader-calibration fixes the live runs surfaced

The first real models surfaced two grader bugs the synthetic tests were written around (the same law
that held on evals #1–#4) — both fixed, oracle still 1.000/AllPass, designed variants still gate:

1. **`material_breaks` / `expected_diffs` shape.** Sonnet returned these as rich *dicts*
   (`[{"field": "fixed_rate", ...}]`) and Opus as *descriptive strings*
   (`"our_trade_id vs cpty_trade_id (...)"`) rather than bare field tokens — reasonable, richer
   answers the strict set-membership check crashed on / false-flagged. Fixed with a tolerant
   `_field_tokens` normalizer (dict `field` key, or a known field name inside a descriptive string).
2. **`economic_impact` as prose.** All three returned a paragraph, not a bare number, so the numeric
   check failed all three identically instead of *catching Opus getting it right*. Fixed with
   `_impact_magnitudes` (extract the currency magnitude from the prose, accept the per-annum or the
   5-year total) — which is exactly what surfaces the basis-point error above.

## Caveats

- **n = 1 per case, single model family** (all Claude) — a cross-family run (GPT / Gemini) is the
  honest next step, as on evals #3–#4.
- **Grounded, not fully sourced.** Our-side terms are extracted verbatim from a real, public FpML
  5.10 message (`ird-ex01-vanilla-swap.xml`); the counterparty confirmation and the planted break are
  constructed on top of that real trade.

Artifacts (parsed answer, raw completion, scored report) per model+case under
`outputs/eval5-live/<model>/<case>/`.
