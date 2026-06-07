# Build plan — finance-llm-evals

Goal: a **runnable, portfolio-grade finance LLM evaluation** for the
**Asset Management → Earnings Analysis** workflow. Done well, it proves
workflow definition + eval creation + capability assessment + data curation
+ feedback in one repo.

## Phase 1 — Workflow decomposition  → `workflow/earnings-analysis.md`  ✅ done
- [x] Define the task precisely (inputs, the analyst's real steps, the deliverable).
- [x] Break into **checkpoints**: planning → extraction → calculation → synthesis.
- [x] For each checkpoint: required inputs, intermediate artifact, success criteria.
- [x] Name the **failure modes** each checkpoint guards against.

> Delivered: 17 checkpoints (P1–P3 planning · E1–E6 extraction · C1–C5 calculation ·
> S1–S3 synthesis), each independently scorable and chainable end-to-end. Grading routed
> per checkpoint (deterministic / hybrid value+entailment / label-det+reason-judge / judge).
> Three-tier gating (hard gate · scoped gate · in-checkpoint fail). Failure-taxonomy table
> maps every named failure mode to its catching checkpoint. Sets the contract Phases 2–4 build on.

## Phase 2 — Rubric  → `rubric/rubric.md`  ✅ done
- [x] **Gating conditions** (auto-fail): wrong fiscal period, wrong source/filing,
      unit/scale error, fabricated figure with no citation. *(Three tiers: hard gate ·
      scoped gate (P3→C5,S1) · in-checkpoint fail (wrong-sign).)*
- [x] Weighted categories: extraction accuracy · numerical correctness ·
      evidence entailment · financial reasoning · calibrated risk/uncertainty ·
      structure. *(Secondary diagnostic rollup; headline is checkpoint-weighted.)*
- [x] Tiered scoring per category with explicit "what counts as a zero."
- [x] Decide scoring: deterministic numeric checks (tolerance) + LLM-as-judge
      for free-form. Document the judge prompt.

> Delivered: `rubric/rubric.md` (master scoring model), `rubric/criteria.yaml`
> (109 machine-readable atoms the harness loads), `rubric/judge.md` (frozen LLM-judge
> prompt + entailment/refusal graders + few-shots + Phase-5 calibration contract), and
> `rubric/validate.py` + `rubric/worked_example.py` (a linter — 18 invariant assertions —
> and a reproducible worked example: ungated 0.831 / gated 0.453 / GAP 0.378). Checkpoint-
> primary aggregation with a six-category rollup; E6 scored by FailSafeQA LLMC_β (refuse-all → 0);
> omission penalties close the "answer easy, stay silent on hard" exploit. Adversarially
> reviewed (3 reviewers → revise), revised against 20 findings, re-verified (3 → ship).

## Phase 3 — Gold test cases  → `cases/`  ✅ done (3 cases; expandable to 5)
- [x] Pick 3–5 real companies; pull a 10-Q + earnings release each (SEC EDGAR).
      *(BlackRock Q3'25 · Microsoft FQ2'26 · Snowflake FQ2'26 — fetched from EDGAR.)*
- [x] Author gold answers per checkpoint **with evidence citations** (page/string).
- [x] Include hard cases: unit/scale trap (SNOW "in thousands"), fiscal-vs-calendar
      (MSFT/SNOW), GAAP-vs-street basis trap (all 3), loss-quarter non-GAAP diluted-share
      divergence (SNOW), sector-N/A asset manager (BLK), segment tie-outs (BLK/MSFT), and a
      genuine **not-disclosed + answerable-twin** probe (BLK).
- [x] Store as structured files (YAML) the harness can load. *(`_TEMPLATE.case.yaml` is the contract.)*

> Delivered: `cases/<id>.case.yaml` × 3 (every gold figure transcribed from the real filing
> with a `{document, locator, verbatim}` citation — no invented numbers), `cases/_TEMPLATE.case.yaml`
> (the schema), `cases/README.md`. BLK + MSFT independently re-verified by a separate agent (the MSFT
> pass caught a real consensus error); SNOW re-confirmed by hand against EDGAR (its automated verify
> pass hit a spend limit) and its EPS beat re-based to non-GAAP diluted for like-for-like consistency.

## Phase 4 — Runnable harness  → `harness/`
- [ ] Choose framework: **OpenAI Evals** or **DeepEval** (lean toward DeepEval
      for rubric + LLM-judge ergonomics; decide in-session).
- [ ] Wire model adapters (GPT-5 / Claude) + the deterministic + judge graders.
- [ ] `python -m ...` runs the full suite and emits a scored report.

## Phase 5 — Graded outputs + write-up  → `outputs/` + `README.md`
- [ ] Run 20–50 model outputs; grade; write rationales.
- [ ] Build the **failure taxonomy** table from real traces.
- [ ] A short calibration write-up (judge-vs-human agreement on a sample).
- [ ] Polished README so a screener can run it and read the findings.

## Phase 6 — Publish + apply
- [ ] Push to GitHub (public).
- [ ] (Later) Moat version: an options / ETF / defined-outcome eval.
