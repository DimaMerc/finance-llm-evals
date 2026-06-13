# finance-llm-evals

![Looks right ≠ is right — a runnable, rubric-graded evaluation for finance LLMs: a model that misreads a statement header scores 95% on a naive average but 45% once the gate fires.](assets/hero.png)

A runnable **suite** of evaluations measuring how well large language models perform real
**asset-management analyst workflows** — judged the way a finance professional actually judges
work: against a rubric, with every figure traced to a source filing, auto-fail "gates" for the
errors that quietly poison a memo, and credit for *calibrated uncertainty* rather than confident
guessing.

Most finance-LLM demos show a polished answer. This shows the **scoring system** behind the
answer: the workflow broken into checkpoints, a gating-plus-weighted rubric, gold cases cited to
SEC filings, and a grader that surfaces exactly *where* — and how badly — a model fails.

**Two evals, one scoring engine:**

- **Eval #1 — Quarterly earnings analysis.** Digest a 10-Q/earnings release, reconcile the figures,
  benchmark versus consensus, flag what moved. 17 checkpoints, 109 criteria, three gold cases
  (BlackRock, Microsoft, Snowflake).
- **Eval #2 — Defined-outcome ("buffer") ETF diligence** *(the one a generalist can't author)*.
  Given a prospectus, the fund's actual FLEX-option legs from its N-PORT filing, and a dated market
  snapshot: recompute the marketed cap and buffer **from the option strikes**, compute what a
  **mid-period buyer actually gets**, verify the marketing claims, and price the protection — with
  the **free-lunch gate** (downside protection asserted with no forgone-upside cost = auto-fail) as
  the signature. 18 checkpoints, 110 criteria, three market-snapshot cases on a real buffer ETF.

## Quickstart (no API key, no setup)

```bash
python -m harness suite       # score every gold case in both evals
python -m harness demo        # grade a known-good and a known-broken answer, side by side
python -m harness selftest    # sanity check — prints PASSED
```

The only dependency is `pyyaml`; the demo and the entire deterministic scoring core run offline.
A real model is one flag/command away — see [`outputs/eval2-live/`](outputs/eval2-live/).

> 📄 **Prefer prose?** [`PAPER.md`](PAPER.md) is the methodology write-up (v2 covers the suite, the
> two-model run matrix, the failure taxonomy, and the judge-vs-expert calibration).

## What's here

| Path | Contents |
|---|---|
| [`workflow/`](workflow/) | Each workflow decomposed into measurable checkpoints (earnings: 17 · defined-outcome: 18) |
| [`rubric/`](rubric/) | Gating + weighted, tiered rubrics — machine-readable atoms (`criteria*.yaml`), the frozen judge prompt (`judge.md`), and a `validate.py` linter |
| [`cases/`](cases/) | Gold cases — every figure cited to a real SEC filing (10-Q / 8-K / 497K / N-PORT); **no invented numbers** |
| [`harness/`](harness/) | The runnable scorer: one suite-agnostic engine + a module per eval; deterministic checks + gating + a pluggable LLM-judge interface; a live path for real models |
| [`outputs/eval2-live/`](outputs/eval2-live/) | The real graded runs, the failure taxonomy, and the judge-vs-expert calibration |

## What the live runs found (eval #2)

Two open-weight models (a 27B reasoning model and a 72B non-reasoning one), run locally at zero API
cost, across a real Innovator buffer ETF under three market snapshots. The headline pattern: both
**nailed extraction and the single headline calculation** (the remaining cap for today's buyer),
and both **fell into the same payoff-reconstruction trap** — suggestive that the eval is catching
the *task's* difficulty, not one model's quirk (both subjects share a vendor lineage, so a
cross-family replication is the honest next step). The smaller reasoning model beat the larger
non-reasoning one on every case. And because the eval is **calculation-heavy by design**, swapping
the offline grader for a real LLM judge moved the scores by only **2–4.5 points** (versus ~15 on the
earnings eval) — the headline barely depends on the subjective part. Full traces, scored reports,
and the taxonomy are in [`outputs/eval2-live/`](outputs/eval2-live/); the calibration (judge vs. a
hand-graded expert sample, with caveats stated) is alongside.

Running real models also surfaced three calibration bugs in the grader itself — the kind a
synthetic self-test can't see because it's written around the grader's own assumptions. They were
fixed and everything re-graded; the log is in the taxonomy.

## What the demo shows

`python -m harness demo` grades a model that does Snowflake's analysis **correctly** but misreads
the statement header ("in thousands" as "in millions"). Its **ungated** score stays ~0.99 (the
arithmetic is internally consistent), but a hard gate collapses the **gated** score to ~0.45 — a
**0.53 gap** that is the finding itself: *can do the math, cannot be trusted to read a statement
header.*

## Why a firm cares

Before any firm lets an AI do analyst work, it needs to know *whether — and exactly where — to
trust it.* A blended accuracy number can't answer that. This suite catches the errors that quietly
poison a memo (scale, period, fabrication, GAAP-vs-non-GAAP for earnings; wrong fund vintage,
strike-scale, stated-vs-remaining terms, and the free lunch for buffer ETFs), localizes each to the
checkpoint that owns it, and tells "looks right" apart from "is right." A firm uses it as an
**acceptance test** (which model is deployable, and where it needs a guardrail) and a **regression
test** (did a model/prompt change help or hurt, and where).

## Why it's built this way

The design follows the public state of the art — OpenAI's **HealthBench** (expert rubric criteria
graded by an LLM judge), **FinanceBench** (every answer tied to an evidence string), **FinQA /
TAT-QA** (executed numeric tolerance), the **Vals AI Finance Agent Benchmark** (checkpoint scoring
of an end-to-end analyst task), and **FailSafeQA** (rewarding calibrated refusal) — and composes
them into a runnable whole, then extends it to a derivatives-overlay product that the public
benchmarks don't cover.

See [`PLAN.md`](PLAN.md) for the phase roadmap and [`CLAUDE.md`](CLAUDE.md) for full project context.

## License

MIT — see [`LICENSE`](LICENSE). Gold-case figures are public-record facts from SEC EDGAR,
attributed to their source filings.
