# Build plan — finance-llm-evals

Goal: a **runnable, portfolio-grade finance LLM evaluation** for the
**Asset Management → Earnings Analysis** workflow. Done well, it proves
workflow definition + eval creation + capability assessment + data curation
+ feedback in one repo.

## Phase 1 — Workflow decomposition  → `workflow/earnings-analysis.md`
- [ ] Define the task precisely (inputs, the analyst's real steps, the deliverable).
- [ ] Break into **checkpoints**: planning → extraction → calculation → synthesis.
- [ ] For each checkpoint: required inputs, intermediate artifact, success criteria.
- [ ] Name the **failure modes** each checkpoint guards against.

## Phase 2 — Rubric  → `rubric/rubric.md`
- [ ] **Gating conditions** (auto-fail): wrong fiscal period, wrong source/filing,
      unit/scale error, fabricated figure with no citation.
- [ ] Weighted categories: extraction accuracy · numerical correctness ·
      evidence entailment · financial reasoning · calibrated risk/uncertainty ·
      structure.
- [ ] Tiered scoring per category with explicit "what counts as a zero."
- [ ] Decide scoring: deterministic numeric checks (tolerance) + LLM-as-judge
      for free-form. Document the judge prompt.

## Phase 3 — Gold test cases  → `cases/`
- [ ] Pick 3–5 real companies; pull a 10-Q + earnings release each (SEC EDGAR).
- [ ] Author gold answers per checkpoint **with evidence citations** (page/string).
- [ ] Include hard cases: restatements, segment changes, one-offs, unit traps,
      consensus beats/misses, and an "unanswerable / data-missing" case to test
      calibrated refusal.
- [ ] Store as structured files (JSON/YAML) the harness can load.

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
