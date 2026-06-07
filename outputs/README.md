# Outputs — graded runs & findings (Phase 5)

> **Scope note.** This is the **single demo** cut of Phase 5: a runnable, reproducible, **offline**
> demonstration that the harness grades a model and that the failure taxonomy fires as designed.
> The full Phase-5 plan — running 20–50 *live* GPT-5 / Claude outputs and a judge-vs-expert
> calibration — is deferred until the spend cap is raised (running frontier models over the suite is
> the token-heavy step). Everything here runs with **no API key and no spend**:
> `python -m harness demo`.

## The demo finding

A model analyzes Snowflake's fiscal-Q2-2026 print (reported **"in thousands"**) and does the work
**correctly** — every growth rate, margin, the GAAP→non-GAAP bridge, the beat/miss — but misreads the
statement-header scale, treating "in thousands" as "in millions." One header misread.

| | ungated | gated (headline) | GAP | AllPass | gate |
|---|---:|---:|---:|---:|---|
| oracle (perfect) | 1.000 | 1.000 | 0.000 | 1 | — |
| **scale_slip** | **0.985** | **0.452** | **0.533** | 0 | `GATE.P2` (hard) |

The model looks ~99% right on a naive average (**ungated**), but the gated headline collapses to
**0.45** because `GATE.P2` zeroes every figure and calculation that inherits the scale. **The GAP
(0.53) is the finding**: *this model can do the math but cannot be trusted to read a statement
header* — exactly the error a blended accuracy score hides and a PM most needs flagged. Full capture:
[`demo-snow-scale-slip.txt`](demo-snow-scale-slip.txt).

## The three gate tiers, and the GAP each opens

The same suite run against four injected errors shows the gate tiers producing **differentiated blast
radii** — the whole point of localizing failure to a step. ([`suite-by-variant.txt`](suite-by-variant.txt))

| Injected error | Gate tier | Blast radius | Gated | GAP | Reads as |
|---|---|---|---:|---:|---|
| scale misread | **hard** (`GATE.P2`) | all dependent extraction + calc | 0.452 | 0.533 | unusable downstream |
| GAAP-vs-street basis | **scoped** (`GATE.P3`) | the beat/miss chain (C5, S1) | 0.861 | 0.125 | a false beat/miss |
| beat called a miss | **in-checkpoint** (`GATE.C5SIGN`) | C5 only, no cascade | 0.935 | 0.054 | one wrong call |
| fabricated the not-disclosed figure | E6 `LLMC_β` → 0 | calibration (no cascade) | 0.940 | 0.000 | sycophancy |

Note the **fabrication** case: inventing a number for the genuinely-not-disclosed E6 probe drives the
FailSafeQA refusal score `G→0`, so E6's headline (`LLMC_β`) goes to **0** — confident guessing is
penalized harder than the honest "not disclosed" the oracle gives. AllPass is 0 for every flawed run.

## How to reproduce

```bash
python -m harness demo            # the scale-slip finding, side by side with the oracle
python -m harness suite --model scale_slip      # the hard-gate collapse across all three cases
python -m harness selftest        # asserts these invariants still hold
```

## What the full Phase 5 will add (when budget allows)

Run real frontier models (`--judge llm`, `models.LiveModel`) over the three cases, grade 20–50
outputs, build the failure-taxonomy table mechanically from the fired-atom `tags[]`, and report the
judge-vs-expert macro-F1 / Cohen's κ calibration from [`../rubric/judge.md`](../rubric/judge.md). The
harness, the gold, and the rubric are all in place for it — only the spend gates it.
