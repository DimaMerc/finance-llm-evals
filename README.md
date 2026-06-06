# finance-llm-evals

A runnable evaluation of how well large language models perform a real
**asset-management analyst workflow — quarterly earnings analysis** — judged
the way a finance professional actually judges it: against a rubric, with every
figure traced to a source filing, and credit for *calibrated uncertainty*
rather than confident guessing.

Most finance LLM demos show a polished answer. This shows the **scoring system**
behind the answer: the workflow broken into checkpoints, a gating-plus-weighted
rubric, gold cases cited to SEC filings, and graded model runs that surface
exactly where today's models fail.

> Status: **in progress.** See [`PLAN.md`](PLAN.md) for the roadmap and
> [`CLAUDE.md`](CLAUDE.md) for full project context.

## What's here

| Path | Contents |
|---|---|
| `workflow/` | The earnings-analysis workflow decomposed into measurable checkpoints |
| `rubric/` | Gating conditions + weighted, tiered grading rubric |
| `cases/` | Gold test cases (10-Q / earnings release) with cited answers |
| `harness/` | Runnable eval harness (deterministic checks + LLM-as-judge) |
| `outputs/` | Graded model outputs, rationales, and the failure taxonomy |

## Why it's built this way

The design follows the public state of the art — OpenAI's HealthBench (expert
rubric criteria graded by an LLM judge), FinanceBench (every answer tied to an
evidence string + page), and the Vals AI Finance Agent Benchmark (checkpoint
scoring of an end-to-end analyst task) — and targets the failure modes that
matter in finance: wrong reporting period, unit/scale errors, mis-citation,
fabricated figures, false precision, missing material items, and sycophancy.

## License

TBD.
