# A Runnable, Rubric-Graded Evaluation for Finance LLMs: Quarterly Earnings Analysis

**Dmitry Krutous** · MBA, PMP · [linkedin.com/in/dmitrykrutous](https://www.linkedin.com/in/dmitrykrutous/) · welt.management.solutions@gmail.com
*Methodology note & preliminary findings. The artifact is the runnable repository this paper accompanies:
[github.com/DimaMerc/finance-llm-evals](https://github.com/DimaMerc/finance-llm-evals).*

---

## Abstract

Most finance-LLM demos show a polished answer; few show the *scoring system* that decides whether the
answer can be trusted. This work builds one — a runnable evaluation of a real asset-management analyst
workflow, **quarterly earnings analysis**, judged against an expert-authored rubric the way a finance
professional would: every figure traced to a source filing, auto-fail "gates" for the errors that
quietly poison a memo, and credit for *calibrated uncertainty* rather than confident guessing. The
contribution is the evaluation design and a working harness, not a leaderboard: the workflow decomposed
into 17 independently-scorable checkpoints, a gating-plus-weighted rubric of 109 machine-readable
criteria, three gold cases transcribed verbatim from real SEC filings with `{document, locator,
verbatim}` citations and an independent adversarial verification log (no invented numbers), and a Python
harness that grades a model end-to-end and **localizes where it fails**. Synthetic perturbations show the
eval discriminates by design — a perfect answer scores 1.000, a scale misread collapses to 0.45 — and a
first single-model run (Qwen2.5-32B-Instruct) shows the capability split a firm must see before trusting
a model with a memo: a strong *extractor* whose *synthesis* and *derived calculations* fall short — on
one model, with a judge not yet expert-calibrated.

## 1. Motivation

A firm that wants an LLM to do equity analysis has one hard problem before deployment: *how do we know
when — and exactly where — to trust it?* A single blended accuracy number cannot answer that. The error
that matters most in finance is rarely a small one: misreading an "in thousands" statement header,
pinning the wrong fiscal period, comparing GAAP EPS to a non-GAAP street consensus, or fabricating a
figure the filing never disclosed. Each silently corrupts everything downstream while the prose still
reads fluently.

The public state of the art frames the pieces but not this whole. **HealthBench** grades expert rubric
criteria with an LLM judge; **FinanceBench** ties every answer to an evidence string and page;
**FinQA/TAT-QA** execute numeric reasoning with tolerance; the **Vals AI Finance Agent Benchmark**
checkpoint-scores an end-to-end analyst task (best reported agent ~47% as of this writing); **FailSafeQA**
rewards calibrated refusal. This work composes those ideas into a single *runnable* evaluation of the
first-hours earnings-analysis workflow, designed so failure is localized to the step that owns it.

## 2. Method

**2.1 Workflow → 17 checkpoints.** The task — digest a company's 10-Q/10-K and earnings release, extract
and reconcile the key figures, benchmark versus consensus, flag material changes — is decomposed into
four stages and 17 checkpoints, each independently scorable yet chainable into one end-to-end run:
*Planning* (P1 pin period · P2 lock scale/currency · P3 scope + consensus basis), *Extraction* (E1
income statement · E2 segments + share counts · E3 non-GAAP reconciliation + cash flow · E4 guidance ·
E5 working capital · E6 a calibrated-refusal probe), *Calculation* (C1 growth + Δshares · C2 margins/FCF
· C3 the GAAP→non-GAAP EPS bridge · C4 quality-of-earnings ratios · C5 beat/miss + segment tie-out), and
*Synthesis* (S1 directional calls · S2 material changes + earnings quality · S3 a calibrated bottom
line).

**2.2 Rubric.** Each checkpoint's success criteria become **109 atomic, machine-readable criteria** (the
static template; per-figure extraction atoms expand further at run time; +353 positive / −135 penalty
mass) routed to the cheapest grader that can score them correctly: 65
deterministic (value + tolerance, scale-folded), 9 citation-entailment, 29 LLM-judge, 6 calibrated-
refusal. Scoring is **checkpoint-primary** (a 17-element vector plus one weighted scalar) with a
six-category diagnostic rollup (extraction · numerical · entailment · reasoning · calibration ·
structure). Three **gate tiers** auto-fail corrupting errors with differentiated blast radii — *hard*
(wrong period/scale → zero all dependents), *scoped* (GAAP-vs-street basis → zero the beat/miss chain
only), and *in-checkpoint* (a flipped sign → zero one checkpoint). Calibrated refusal is first-class: E6
is scored by an asymmetric F-β composite (LLMC_β, β=0.5) in the spirit of FailSafeQA — confidently
fabricating a not-disclosed figure scores 0 while an honest "not disclosed" earns credit, and an
*answerable twin* (a figure that *is* disclosed, just buried) keeps a refuse-everything policy from
farming safety credit. A `validate.py` linter asserts 18 structural invariants
(weights sum to 1, masses balance, every gate/atom resolves) so the rubric is provably self-consistent.

**2.3 Gold cases.** Three quarters from real SEC filings, every figure transcribed and cited
`{document, locator, verbatim}` — **no invented numbers**: **BlackRock Q3 2025** (asset manager;
sector-N/A with no gross margin; GAAP \$8.43 vs as-adjusted \$11.55 with a basis-guard against a false
miss; a genuine not-disclosed probe), **Microsoft FQ2 2026** (fiscal-vs-calendar period; three-segment
tie-out to \$81,273M), and **Snowflake FQ2 2026** ("in thousands" scale trap; GAAP-loss/non-GAAP-profit
diluted-share divergence; full EPS bridge). Together they exercise every gate tier and most of the
failure taxonomy.

**2.4 Harness.** A purpose-built Python scorer (chosen over wrapping DeepEval/OpenAI Evals, whose generic
metric abstractions would hide the gating/aggregation logic that is the point) loads the rubric, grades
a model's structured memo, and emits the full report — the checkpoint vector, the weighted CaseScore,
the category rollup, and **gated / ungated / GAP / AllPass**. The deterministic core and all gating run
offline with no API key; the judge is a pluggable interface (offline mock or a real local/cloud LLM).

## 3. Preliminary findings

*Sections 1–2 describe the finished instrument; the findings below are an early, single-model read of it.*

**3.1 The gates fire cleanly on planted errors, and the GAP is the diagnostic.** These are synthetic
injected-error variants the eval was built to catch — a self-test of the gating, not live model behavior.
Run against a *perfect* answer the eval scores 1.000 / AllPass; against each planted error the three gate
tiers open cleanly differentiated gaps between the naive (ungated) and honest (gated) score:

| Injected error | Gate tier | ungated → gated | GAP |
|---|---|---|---:|
| misread "in thousands" as "in millions" | hard (`GATE.P2`) | 0.951 → 0.452 | **0.499** |
| GAAP EPS vs non-GAAP consensus | scoped (`GATE.P3` → C5,S1) | 0.986 → 0.861 | 0.125 |
| beat called a miss | in-checkpoint (`GATE.C5SIGN`) | 0.989 → 0.935 | 0.054 |
| fabricated the not-disclosed figure | E6 F-β → 0 | 0.940 → 0.940 | 0.000 |

The first row is the headline: a model that does the math flawlessly but misreads the scale looks ~95%
right on a blended average yet collapses to 0.45 once the gate zeroes every figure that inherits the
error — *"can do the math, cannot be trusted to read a statement header."*

**3.2 A real model: strong extractor, weak synthesis and derived calculations.** Qwen2.5-32B-Instruct (run
locally, no API spend) scored **0.679** with the offline mock judge but **0.532** once a real LLM judge
graded the free-form synthesis (a same-family, not-yet-calibrated judge — see §4). The drop is
directionally right and matches a manual read of the memo: the model listed surface metrics ("revenue
+32%") instead of the thesis-moving changes and never flagged that Snowflake is GAAP-unprofitable, so
S2/S3 fell from a free 1.0 to 0.0. It extracted well (segments + shares E2 = 0.91, working capital
E5 = 0.91) and handled the harder *structured* calculations decently (the GAAP→non-GAAP EPS bridge
C3 = 0.70, beat/miss C5 = 0.83), but collapsed on the plain *derived* ratios (margins C2 = 0.14,
quality-of-earnings ratios C4 = 0.13 — it emitted *formulas* instead of numbers, or nothing). Feeding it
a 10-Q excerpt (the working-capital footnotes; the income statement and cash flow are already in the
release) did **not** move those checkpoints (0.679 → 0.671): the weakness is **computation, not data
access**.

**3.3 Running a real model improves the eval.** The first live run immediately surfaced two grader bugs
that the synthetic tests could not — they had been written around the grader's own assumptions. The
period check demanded an exact label string (failing a model that wrote "Second Quarter Fiscal 2026" for
"Fiscal Q2 2026"), and the scale check compared a label rather than figure magnitude (failing a model
whose numbers were correct). Both were fixed; the model went from a false 0.09 to an honest 0.68. *This
is why one runs real models against an eval: they find the calibration errors a synthetic test never
will.*

## 4. Limitations & future work

These findings are **preliminary** and honestly scoped. (i) **One model.** A multi-model comparison was
blocked by local-inference infrastructure limits, not the eval; the harness is wired (`--model live
--endpoint …`) for it. (ii) **Judge calibration** is specified as a contract (macro-F1 / Cohen's κ versus
an expert on a hand-graded sample) but not yet run; the present judge is also same-family (a Qwen model
judging a Qwen model), where a cross-family judge is the correct setup. (iii) **Three cases**; broadening
the suite and adding an options/ETF/defined-outcome "moat" case is the planned next step. None of these
affect the method; they bound the *results* section, which grows as more models are run.

## 5. Reproduce

The evaluation is runnable with one dependency (`pyyaml`) and no API key:

```bash
python -m harness demo        # grade a known-good and a known-broken answer, side by side
python -m harness suite       # score all three gold cases
python -m harness selftest    # assert the gate-tier invariants
python rubric/validate.py     # assert the 18 rubric invariants
```

A real model is one flag away: `python -m harness run --case snow --model live --judge llm
--endpoint http://<host>:1234/v1`. The full design, gold cases, and harness are in the accompanying
repository.

## References

OpenAI HealthBench · FinanceBench (Patronus AI) · FinQA / ConvFinQA / TAT-QA · Vals AI Finance Agent
Benchmark · FailSafeQA. Filings: SEC EDGAR (BlackRock, Microsoft, Snowflake).
