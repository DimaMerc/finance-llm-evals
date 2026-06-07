# Harness — Phase 4

A runnable scorer that loads the [rubric](../rubric/criteria.yaml), grades a model's structured
earnings memo against a [gold case](../cases/), and emits the scored report the rubric specifies:
the **17-checkpoint vector**, the weighted **CaseScore**, the six-category **rollup**, and
**gated / ungated / GAP / AllPass** — with the three gate tiers applied.

```bash
python -m harness list                                   # cases + model variants
python -m harness suite  --model oracle                  # score every case
python -m harness run    --case snow --all               # all flawed variants on one case
python -m harness demo                                   # the canonical scale-slip finding
python -m harness selftest                               # regression guard (invariants must hold)
```

No API key is needed for any of the above — see *Offline vs. live* below.

## Framework decision

PLAN.md floated DeepEval vs. OpenAI Evals. Having built the rubric, a **purpose-built scorer** is the
right call, and deliberately so:

- The rubric's scoring model — checkpoint-primary aggregation with a category rollup, **three-tier
  gating** (hard / scoped / in-checkpoint) with per-atom blast radii, the **FailSafeQA `LLMC_β`**
  headline for E6, `per_figure` **expand + prune**, the value/entailment split, and omission
  penalties — does not map onto a generic metric abstraction (DeepEval's `GEval`, an Evals
  `Eval`). Forcing it through one would *hide* the logic that is the whole point of the artifact.
- A transparent scorer that loads `criteria.yaml` directly is what a screener can actually read and
  trust. The LLM-judge piece (the `judge`/`entailment`/`refusal` atoms) is cleanly isolated and could
  be wrapped as a DeepEval custom metric or an Evals grader later without touching the scoring core.

So: the deterministic scoring engine is ours and exact; the LLM graders are a pluggable interface.

## Architecture

| Module | Responsibility |
|---|---|
| [`rubric.py`](rubric.py) | load `criteria.yaml` + a case; **materialize** the per-case atom set (per_figure expand/split + N/A prune from the manifest) |
| [`tolerances.py`](tolerances.py) | the deterministic tolerance bands (eps, aggregate, margin-delta bps, fcf, ratio, the floor-RSS tax-rate-delta), scale-folded |
| [`graders.py`](graders.py) | grade each atom: model answer vs gold → `met`. Deterministic + gating exact; entailment/judge/refusal mockable |
| [`scoring.py`](scoring.py) | inner checkpoint score, gate firing + blast radius, E6 `LLMC_β`, CaseScore, category rollup, AllPass, GAP |
| [`models.py`](models.py) | offline model answers (oracle + named flawed variants); a `LiveModel` skeleton for a real run |
| [`report.py`](report.py) · [`__main__.py`](__main__.py) | render + CLI |

## Offline vs. live

- **Deterministic core + all gating** — exact, offline, no API. This is the majority of the atoms and
  every gating decision (period, scale, basis, sign, fabrication).
- **`judge` / `entailment` / `refusal` atoms** — `--judge mock` (default) grades them heuristically
  offline so the whole pipeline runs with no key and no spend; `--judge llm` is the live swap that
  uses [`../rubric/judge.md`](../rubric/judge.md). The frozen judge prompt and the Phase-5 macro-F1 /
  κ calibration contract live there.
- **The model under test** — the offline variants build the answer from the gold (perfect, or with a
  specific injected error). A real run wires `models.LiveModel` to an Anthropic/OpenAI SDK call that
  feeds the model the filing text + the output schema and parses its JSON. That path incurs spend and
  is intentionally not exercised in the committed demo.

## What the demo shows

`python -m harness demo` scores a model that does Snowflake's analysis **correctly** but misreads the
statement header ("in thousands" as "in millions"). Its **ungated** score stays ~0.99 (the arithmetic
is internally consistent), but **`GATE.P2`** collapses the **gated** score to ~0.45 — a **GAP ≈ 0.53**.
That gap is the diagnostic the eval exists to produce: *can do the math, cannot be trusted to read a
statement header.* See [`../outputs/`](../outputs/) for the captured run and the gate-tier taxonomy.

## Requirements

`pip install -r requirements.txt` (just `pyyaml`; `anthropic`/`openai` only for a live run).
