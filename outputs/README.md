# Outputs — graded runs & findings (Phase 5)

> **Scope note.** Two cuts of Phase 5 live here: (1) an **offline** demo that proves the harness
> grades a model and the failure taxonomy fires as designed (`python -m harness demo`, no API/spend),
> and (2) a **first real local run** of an open model (Qwen2.5-32B via LM Studio on an RTX 5090 — no
> API spend) that produced an honest score *and* surfaced two grader bugs the synthetic tests missed.
> The full Phase-5 plan — 20–50 graded outputs across frontier + open models with a judge-vs-expert
> calibration — is still ahead.

## The demo finding

A model analyzes Snowflake's fiscal-Q2-2026 print (reported **"in thousands"**) and does the work
**correctly** — every growth rate, margin, the GAAP→non-GAAP bridge, the beat/miss — but misreads the
statement-header scale, treating "in thousands" as "in millions." One header misread.

| | ungated | gated (headline) | GAP | AllPass | gate |
|---|---:|---:|---:|---:|---|
| oracle (perfect) | 1.000 | 1.000 | 0.000 | 1 | — |
| **scale_slip** | **0.951** | **0.452** | **0.499** | 0 | `GATE.P2` (hard) |

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
| scale misread | **hard** (`GATE.P2`) | all dependent extraction + calc | 0.452 | 0.499 | unusable downstream |
| GAAP-vs-street basis | **scoped** (`GATE.P3`) | the beat/miss chain (C5, S1) | 0.861 | 0.125 | a false beat/miss |
| beat called a miss | **in-checkpoint** (`GATE.C5SIGN`) | C5 only, no cascade | 0.935 | 0.054 | one wrong call |
| fabricated the not-disclosed figure | E6 `LLMC_β` → 0 | calibration (no cascade) | 0.940 | 0.000 | sycophancy |

Note the **fabrication** case: inventing a number for the genuinely-not-disclosed E6 probe drives the
FailSafeQA refusal score `G→0`, so E6's headline (`LLMC_β`) goes to **0** — confident guessing is
penalized harder than the honest "not disclosed" the oracle gives. AllPass is 0 for every flawed run.

## First live run — Qwen2.5-32B-Instruct (local, RTX 5090, no API spend)

The first *real* model run, via LM Studio's OpenAI-compatible local server, fed the Snowflake
**press release** and graded against the gold. Captured in
[`live-snow-qwen2.5-32b.json`](live-snow-qwen2.5-32b.json) (the model's answer, re-gradeable) and
[`live-snow-qwen2.5-32b.report.txt`](live-snow-qwen2.5-32b.report.txt).

**Headline: 0.679 overall — but the honest, trustworthy signal is ~0.60** on the deterministic
*numeric* checkpoints (the synthesis checkpoints score a generous 1.0 only because the offline
`--judge mock` rewards any non-empty answer; a real LLM judge would grade them properly). Per
checkpoint the model is **strong on extraction** (segments + share counts E2 = 0.91, working capital
E5 = 0.91, revenue/net-income/EPS), the **EPS bridge** (C3 = 0.70) and **beat/miss** (C5 = 0.83), and
**weak on the derived ratios** (margins/FCF C2 = 0.14, effective-tax/DSO C4 = 0.13) — several of which
need 10-Q lines the press-release-only context didn't contain. It correctly **refused** the
not-disclosed E6 probe (good calibration) but couldn't retrieve the answerable twin (a 10-Q figure).

**What the live run *changed about the eval itself* — the real value.** Grading a real model
immediately surfaced **two grader bugs that the synthetic oracle/perturbation tests could not** (those
were built around the grader's own assumptions):

1. **Period match was too strict** — it demanded an exact label string, so the model writing *"Second
   Quarter Fiscal 2026"* (semantically identical to the gold's *"Fiscal Q2 2026 (…July 31, 2025)"*)
   falsely tripped `GATE.P1`. Fixed: the period is now keyed on the unambiguous **period-end date**.
2. **Scale match compared a label, not magnitude** — the model reported figures in USD millions (as
   asked) and correctly normalized "in thousands" → millions, but labeling its scale "millions"
   falsely tripped `GATE.P2` and zeroed every *correct* figure. Fixed: the scale gate now detects a
   real **~1000× magnitude error from the figures**, not a label string.

Before the fix the model looked like a 0.09; after, an honest 0.68. *That* is why you run real models
against an eval — they find the calibration errors a synthetic test never will.

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
