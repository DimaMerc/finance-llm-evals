# Harness — Phase 4

A runnable scorer for **both evals in the suite**: it loads each case's rubric
([criteria.yaml](../rubric/criteria.yaml) for the earnings eval,
[criteria-defined-outcome.yaml](../rubric/criteria-defined-outcome.yaml) for the defined-outcome
ETF eval), grades a model's structured memo against a [gold case](../cases/), and emits the scored
report the rubric specifies: the **checkpoint vector**, the weighted **CaseScore**, the
six-category **rollup**, and **gated / ungated / GAP / AllPass** — with the gate tiers applied and
**headline flags** (eval #2's `free_lunch_fired`) surfaced beside the score.

```bash
python -m harness list                                   # cases + variants, per suite
python -m harness suite  --model oracle                  # score every case (both suites)
python -m harness run    --case snow --all               # all flawed variants on one case
python -m harness run    --case koct-op2026-anchor --model free_lunch   # the signature gate
python -m harness demo                                   # the canonical scale-slip finding
python -m harness selftest                               # per-suite regression invariants
```

No API key is needed for any of the above — see *Offline vs. live* below.

## Framework decision

PLAN.md floated DeepEval vs. OpenAI Evals. Having built the rubric, a **purpose-built scorer** is the
right call, and deliberately so:

- The rubric's scoring model — checkpoint-primary aggregation with a category rollup, **three-tier
  gating** (hard / scoped / in-checkpoint) with per-atom blast radii, the **FailSafeQA `LLMC_β`**
  refusal headline, `per_figure` **expand + prune**, the value/entailment split, and omission
  penalties — does not map onto a generic metric abstraction (DeepEval's `GEval`, an Evals
  `Eval`). Forcing it through one would *hide* the logic that is the whole point of the artifact.
- A transparent scorer that loads the criteria files directly is what a screener can actually read
  and trust. The LLM-judge piece (the `judge`/`entailment`/`refusal` atoms) is cleanly isolated and
  could be wrapped as a DeepEval custom metric or an Evals grader later without touching the core.

So: the deterministic scoring engine is ours and exact; the LLM graders are a pluggable interface.

## Architecture (Phase-4 refactor: one engine, two suites)

| Module | Responsibility |
|---|---|
| [`rubric.py`](rubric.py) | route a case to its suite's criteria file; **materialize** the per-case atom set (per_figure expand/split — segments/add-backs, legs/grid-rows/claims — + N/A prune from the manifest) |
| [`tolerances.py`](tolerances.py) | the deterministic tolerance bands, scale-folded |
| [`graders.py`](graders.py) | the suite-agnostic grading **engine**: refusal placeholder → suite handlers → penalties → judge/entailment → default, exactly the original flow |
| [`suites/earnings.py`](suites/earnings.py) | **eval #1**: the original handler chain, penalty detectors, E6 FailSafeQA pass, oracle + flawed variants — behavior-identical to the pre-refactor harness (the selftest asserts it) |
| [`suites/defined_outcome.py`](suites/defined_outcome.py) | **eval #2**: leg/payoff/recompute/remaining-outcome/claim-verdict handlers, the **E5 `{COMPUTED, value, derivation}` typed refusal** (judge.md §8 G-mapping), the **GATE.FREELUNCH deterministic predicate** on the cost-of-protection block, `deciding_kind`-aware C7 grading, oracle + flawed variants |
| [`scoring.py`](scoring.py) | inner checkpoint score; **data-driven gate firing** (each gate's `fired_by` hooks: positive atoms fire when unmet, penalty atoms when present); blast radius; the refusal `LLMC_β` headline (E6/E5, passed by the suite — never hardcoded); CaseScore, rollup, AllPass, GAP, **headline flags** |
| [`models.py`](models.py) | routes `make(case, variant)` to the case's suite; `LiveModel` skeleton |
| [`report.py`](report.py) · [`__main__.py`](__main__.py) | render + CLI (suite-aware list/run/suite/selftest) |

Cases route by their `suite:` field (`defined-outcome-etf`; absent = eval #1). The gate map,
expansion counts, tolerance keys, and the refusal checkpoint all come from the rubric files and the
suite modules — `graders.py` and `scoring.py` contain **no eval-specific atom ids**.

## Offline vs. live

- **Deterministic core + all gating** — exact, offline, no API. This is the majority of the atoms
  and every gating decision (period/vintage, scale, basis, sign, the free-lunch predicate,
  fabrication).
- **`judge` / `entailment` / `refusal` atoms** — `--judge mock` (default) grades them heuristically
  offline so the whole pipeline runs with no key and no spend; `--judge llm` is the live swap that
  uses [`../rubric/judge.md`](../rubric/judge.md) (eval #2's §8 documents the `COMPUTED` G-mapping).
- **The model under test** — the offline variants build the answer from the gold (perfect, or with
  a specific injected error). A real run wires `models.LiveModel` (earnings `--model live` already
  drives a local LM Studio endpoint; the defined-outcome live path is Phase 5).

## What the selftest asserts

Eval #1 (3 cases): oracle 1.000/AllPass; `scale_slip` fires GATE.P2 with GAP > 0.4;
`fabricate_probe` zeroes E6; `basis_mismatch` fires GATE.P3.

Eval #2 (3 KOCT cases): oracle 1.000/AllPass with no flags; `vintage_slip` fires **GATE.VINTAGE**
(hard, GAP ≈ 0.82); `refscale_slip` fires **GATE.REFSCALE** (hard, GAP ≈ 0.46); `feebasis_mix`
fires **GATE.FEEBASIS** (scoped, GAP ≈ 0.18); `free_lunch` fires **GATE.FREELUNCH** — S2+S3 zero,
`free_lunch_fired` raised, AllPass 0 (GAP ≈ 0.07: the signature finding is a *flag*, not a big
number); `fabricate_probe` zeroes the E5 headline (G=0) and fires GATE.FABRICATION; `c6_flip`
fires GATE.C6DIR (in-checkpoint, C6 → 0).

## What the demo shows

`python -m harness demo` scores a model that does Snowflake's analysis **correctly** but misreads
the statement header ("in thousands" as "in millions"). Its **ungated** score stays ~0.99 (the
arithmetic is internally consistent), but **`GATE.P2`** collapses the **gated** score to ~0.45 — a
**GAP ≈ 0.53**. That gap is the diagnostic the eval exists to produce: *can do the math, cannot be
trusted to read a statement header.* See [`../outputs/`](../outputs/) for the captured run and the
gate-tier taxonomy.

## Requirements

`pip install -r requirements.txt` (just `pyyaml`; `anthropic`/`openai` only for a live run).
