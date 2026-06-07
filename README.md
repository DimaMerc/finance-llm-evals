# finance-llm-evals

A runnable evaluation of how well large language models perform a real
**asset-management analyst workflow — quarterly earnings analysis** — judged
the way a finance professional actually judges it: against a rubric, with every
figure traced to a source filing, and credit for *calibrated uncertainty*
rather than confident guessing.

Most finance LLM demos show a polished answer. This shows the **scoring system**
behind the answer: the workflow broken into checkpoints, a gating-plus-weighted
rubric, gold cases cited to SEC filings, and a grader that surfaces exactly
*where* — and how badly — a model fails.

## Quickstart (no API key, no setup)

```bash
python -m harness demo        # grade a known-good and a known-broken answer, side by side
python -m harness selftest    # sanity check — prints PASSED
```

The only dependency is `pyyaml`. The demo and the entire deterministic scoring
core run offline. (`pip install -r harness/requirements.txt` if `pyyaml` is missing.)

## What's here

| Path | Contents | Status |
|---|---|---|
| [`workflow/`](workflow/) | The earnings-analysis workflow decomposed into **17 measurable checkpoints** | ✅ |
| [`rubric/`](rubric/) | Gating + weighted, tiered rubric — `rubric.md` + **109 machine-readable atoms** (`criteria.yaml`) + frozen judge prompt (`judge.md`) + a `validate.py` linter | ✅ |
| [`cases/`](cases/) | **3 gold cases** (BlackRock, Microsoft, Snowflake) — every figure cited to a real 10-Q / 8-K | ✅ |
| [`harness/`](harness/) | The runnable scorer: deterministic checks + gating + LLM-judge interface | ✅ |
| [`outputs/`](outputs/) | The graded demo run + the failure-taxonomy findings | ◐ demo |

## Scope & status — what this proves (and what's next)

**What works today.** The measurement instrument is built and validated. The grader
loads the rubric, materializes the per-case checks, and produces the full report —
a 17-checkpoint vector, a weighted score, a category breakdown, and three tiers of
auto-fail "gates." Run against a *known-perfect* answer it scores **1.000 / AllPass**;
run against a *known-broken* one (a model that does the math but misreads "in
thousands" as "in millions") it catches the error, **pins it to the exact step**, and
separates the naive **0.985** grade from the honest **0.452** grade. That **0.53 gap**
is the finding — "can do the math, cannot be trusted to read a statement header."

**What's deliberately not done yet.** The demo grades *canned* answers, so it says
nothing about any real model's competence. Running a live GPT-5 / Claude / open-source
model over the real filings is the next step — it's a config change, not a rebuild
(`harness/models.LiveModel`), deferred only on cost. Think of it as a thermometer
calibrated against ice water and boiling water: the instrument is proven accurate;
taking a patient's temperature (a live model run) is the cheap next step.

**Why a firm cares.** Before any firm lets an AI do equity analysis, it needs to know
*whether — and exactly where — to trust it.* This is that answer: it catches the
errors that quietly poison a memo (scale, period, fabrication, GAAP-vs-non-GAAP,
wrong-consensus beat/miss), localizes each to the checkpoint that owns it, and tells
"looks right" apart from "is right." A firm uses it as an **acceptance test** (which
model is deployable, and where it needs a guardrail) and a **regression test** (did a
model/prompt change help or hurt, and where).

## Why it's built this way

The design follows the public state of the art — OpenAI's **HealthBench** (expert
rubric criteria graded by an LLM judge), **FinanceBench** (every answer tied to an
evidence string + page), **FinQA / TAT-QA** (executed numeric tolerance), the **Vals AI
Finance Agent Benchmark** (checkpoint scoring of an end-to-end analyst task; best agent
historically ~47%), and **FailSafeQA** (rewarding calibrated refusal) — and targets the
failure modes that matter in finance: wrong reporting period, unit/scale errors,
mis-citation, fabricated figures, false precision, missing material items,
GAAP-vs-non-GAAP confusion, and sycophancy.

See [`PLAN.md`](PLAN.md) for the phase roadmap and [`CLAUDE.md`](CLAUDE.md) for full
project context.

## License

TBD.
