# Leaderboard — every live model run in this suite

One page, every real model this suite has graded so far — with the caveats stated **before** the
numbers: sample sizes are small (1–3 runs per case), evals **#3–#5** were run against a single
model family (three Claude tiers), evals **#1–#2** against local open-weight models (two Qwen
generations), and eval #5's swap-inside-an-ETF case pair has not been live-run yet. Cross-family
runs (GPT, Gemini) are the roadmap; the harness takes any OpenAI-compatible endpoint
(`--model live --endpoint <url> --model-id <model>`), so adding a family is a run, not a rebuild.

**How to read the scores.** Every eval reports a **gated** score: point-weighted, tiered rubric
criteria, collapsed by auto-fail **gates** when a model commits one of the errors that quietly
poison real work — a unit/scale slip, a wrong fiscal period, a fabricated number, settling a
basket that doesn't reconcile, affirming a confirmation that doesn't tie. A model can score ~0.95
on a naive average and ~0.45 gated; **the gap is the finding.** Mechanics:
[README → How the scoring works](README.md#how-the-scoring-works-30-more-seconds).

## Frontier runs — evals #3–#5 (Claude Opus 4.8 / Sonnet 4.6 / Haiku 4.5)

| Eval · case | Opus 4.8 | Sonnet 4.6 | Haiku 4.5 |
|---|---:|---:|---:|
| **#3 DCF** — McDonald's FY2025 | **0.965** | 0.955 | 0.692 · `GATE.C1FCF` |
| **#4 Creation/redemption** — break case | **0.983** | 0.943 | 0.496 · `GATE.SCALE` |
| **#4** — clean-settle counterweight | 0.983 | 0.983 | 0.983 |
| **#5 Confirmation matching** — break case | **0.980** | 0.933 | 0.933 |
| **#5** — clean-match counterweight | 0.980 | 0.980 | 0.980 |

### What separated the models

- **#5 — the basis-point conversion.** All three models matched the confirmations correctly and
  returned MISMATCHED on the 6.05%-vs-6.00% break. Only Opus sized it right (~5 bp ≈ EUR 25k/yr on
  EUR 50MM). Sonnet called it "0.5 bp" (EUR 2,500 — 10× low); Haiku called it "50 bp"
  (EUR 2,500,000 — 10× high). Same trap, opposite directions, localized to one checkpoint
  (`C3.impact`). [Full traces](outputs/eval5-live/)
- **#4 — a $200,000 arithmetic slip.** Opus and Sonnet reconciled to the dollar (residual exactly
  −$13,320, DO_NOT_SETTLE localized to the right line). Haiku overstated the in-kind value by
  exactly $200k, flipping the residual sign — it concluded the basket was *over*-delivered when it
  was short. Right refusal, wrong diagnosis; `GATE.SCALE` pinned it. [Full traces](outputs/eval4-live/)
- **#3 — an FCF that doesn't equal its own build.** Opus and Sonnet produced textbook DCFs
  (fair value ~$228 vs gold $227.82). Haiku's reported free cash flow carried a +$2B/yr offset from
  its own components; `GATE.C1FCF` flagged it at the checkpoint and the error cascaded to a wrong
  $138 valuation. All three showed the same framing quirk: they *derive* the ~7.15% discount rate
  correctly, then answer "not disclosed" when asked for the WACC per the 10-K — without
  volunteering the figure they just computed. [Full traces](outputs/eval3-live/)

### The honest negatives

The marquee decision gates **never fired on a frontier model**: no model settled the broken basket
(`GATE.RECON`) or affirmed the broken trade (`GATE.MATCH`), and none cried break/mismatch on the
clean counterweight cases. On these runs the frontier capability gap lives in the *quantification*
(the bp conversion, the $200k slip), not the *decision*. Stated plainly because a benchmark that
only reports its hits isn't one.

## Open-weight local runs — evals #1–#2

**Eval #1 (earnings, Snowflake FQ2-2026) — Qwen2.5-32B-Instruct**, local, press-release packet:
**0.532** with a real LLM judge (0.679 with the permissive mock judge). The split is the finding: a
competent *extractor* (segments/shares 0.91, EPS bridge 0.70, beat/miss 0.83) but a weak *analyst*
— its "material changes" synthesis listed surface metrics and missed the +1,118 bps GAAP-margin
swing; it correctly refused the not-disclosed probe. Feeding the 10-Q barely moved the score — the
ratio failures were computation failures, not data starvation. [Details](outputs/README.md)

**Eval #2 (buffer-ETF diligence, real Innovator fund, three market snapshots):**

| Case | qwen3.6-27b (reasoning) | qwen2.5-72b (non-reasoning) |
|---|---:|---:|
| anchor | **0.732** | 0.638 |
| post-rally | **0.708** | 0.584 · `GATE.C6DIR` |
| post-drawdown | **0.702** | 0.577 · `GATE.C6DIR` |

The 27B reasoning model beat the 72B non-reasoning model on every case despite a 2.7× size
disadvantage. Both nailed extraction (0.86–0.91) and the headline remaining-cap calculation, and
both fell into the same payoff-grid conflation — two subjects, one lineage, so a cross-family
replication is the honest next step before calling it task-level. [Taxonomy](outputs/eval2-live/TAXONOMY.md)

## Scope notes

- Evals #1–#2 have not been run against frontier models; evals #3–#5 have not been run against
  open-weight models. The grid will fill in as runs accumulate.
- Eval #5's second case pair (the same confirmation-matching control on a swap held *inside an
  ETF*) ships with gold cases and taxonomy but no live run yet.
- Every number above is reproducible from the artifacts in [`outputs/`](outputs/) — parsed
  answers, raw completions, scored reports — or re-runnable via
  `python -m harness run --case <case> --model live ...`.

## What's next

Cross-family frontier runs (GPT, Gemini) to lift the single-family caveat; frontier runs on
evals #1–#2; the ETF-swap pair live; and eval #6 (in design: corporate-actions processing — the
back-office domain with a documented $58B/yr industry cost and, as of mid-2026, no independently
published accuracy metrics).
