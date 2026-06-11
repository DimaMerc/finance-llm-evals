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

## Phase 4 — Runnable harness  → `harness/`  ✅ done
- [x] Choose framework: decided **purpose-built scorer** (not DeepEval/OpenAI Evals — the rubric's
      gating/aggregation/`LLMC_β`/per_figure model doesn't map onto a generic metric abstraction;
      the LLM-judge piece stays pluggable). Rationale in `harness/README.md`.
- [x] Wire model adapters + the deterministic + judge graders. *(Deterministic core + all gating
      exact & offline; entailment/judge/refusal `--judge mock` offline or `--judge llm` live;
      `models.LiveModel` skeleton for a real GPT-5/Claude run.)*
- [x] `python -m harness suite` runs the suite and emits the scored report (checkpoint vector +
      CaseScore + category rollup + gated/ungated/GAP/AllPass). Plus `demo` and a `selftest` guard.

> Delivered: `harness/` (rubric.py · tolerances.py · graders.py · scoring.py · models.py · report.py ·
> __main__.py + README + requirements). Oracle → 1.000/AllPass on all 3 cases; the three gate tiers
> open differentiated GAPs (hard 0.53 · scoped 0.13 · in-checkpoint 0.05); `selftest` asserts it.

## Phase 5 — Graded outputs + write-up  → `outputs/` + `README.md`  ◐ single demo done; full run deferred (spend)
- [x] **Single demo** (offline, no spend): the SNOW scale-slip finding (GATE.P2, GAP 0.53) + the
      gate-tier taxonomy, captured in `outputs/`. — `python -m harness demo`
- [ ] Run 20–50 *live* model outputs; grade; write rationales. *(deferred — needs the spend cap raised)*
- [ ] Build the **failure taxonomy** table from real traces.
- [ ] A short calibration write-up (judge-vs-human agreement on a sample).
- [x] README so a screener can run it and read the findings (`outputs/README.md`, `harness/README.md`).

## Phase 6 — Publish & extend
- [x] MIT-licensed, public-ready: `LICENSE`, line-ending normalization, README + `PAPER.md`.
- [x] Push to GitHub (public): `github.com/DimaMerc/finance-llm-evals`.
- [ ] **Next:** broaden the suite (more issuers/quarters) and run the judge-vs-expert calibration.
- [x] **Moat version** chosen and started → Eval #2 below.

---

# Eval #2 — Defined-outcome (buffer) ETF analysis  *(the moat eval; same repo, same machinery)*

The workflow almost nobody else can author: given a buffer ETF's prospectus + its
N-PORT FLEX-option legs + a dated market snapshot, **recompute the marketing from the
options math** — stated cap/buffer from the strikes, the remaining outcome for a
mid-period buyer, claim-by-claim verification — with the **free-lunch gate** (downside
protection asserted with no forgone-upside cost = auto-fail) as the signature.

## Phase 1 — Workflow decomposition  → `workflow/defined-outcome-analysis.md`  ✅ done
- [x] Feasibility verified live on EDGAR first: KOCT (Innovator U.S. Small Cap Power
      Buffer ETF – October, CIK 1415726, NPORT-P 0000894189-26-009590) — 4 FLEX legs on
      IWM whose strikes reproduce the stated terms exactly (241.96 × 0.85 = 205.67;
      283.53/241.96 − 1 = 17.18%); 497K stated terms verified (17.18/16.39 gross/net cap,
      15/14.21 buffer, 0.79% fee).
- [x] 18 checkpoints (3/5/7/3, deliberately calculation-heavy): P1–P3 planning (vintage
      pin · reference/strike-scale · fee basis), E1–E5 extraction (incl. the remaining-cap
      calibrated-refusal probe with the `{COMPUTED, value, derivation}` typed-answer
      extension), C1–C7 calculation (leg roles/Ref₀ · payoff regimes · recompute-vs-stated
      reconciliation · fee netting · notional tie-outs · remaining outcome at NAV_t ·
      claim verdicts), S1–S3 synthesis (entry-timing verdict · cost of protection ·
      calibrated suitability).
- [x] Gates: GATE.VINTAGE + GATE.REFSCALE (hard), GATE.FEEBASIS (scoped),
      **GATE.FREELUNCH** (scoped, deterministic predicate on the required
      cost-of-protection block → zeros S2+S3; the suite's one synthesis-stage gate),
      GATE.FABRICATION (reused), three in-checkpoint fails (C1/C2/C6).
- [x] Every formula and every live figure independently verified (strikes, OSI ids,
      contracts, 497K terms, payoff regimes, grid conventions, the Day-20 anchor).

## Phase 2 — Rubric atoms  → `rubric/`  ✅ done *(criteria.yaml schema reused; no schema change)*
- [x] `rubric/criteria-defined-outcome.yaml`: **110 atoms** (+349/−121) across the 18 checkpoints
      (per_leg_row / per_grid_row / per_claim_row expansions); the full gate ledger as deterministic
      predicates (incl. GATE.FREELUNCH on the structured cost-of-protection block, with the
      `free_lunch_fired` headline flag); the derivatives tolerance keys (strike-exact, 0.05pp
      recompute, 0.5pp grid %-row, 0.1/0.15pp remaining-terms with internal-consistency);
      calculation-heavy weights (.125/.275/.420/.180). Graders: det 76 / entailment 8 / judge 19 /
      refusal 7.
- [x] `rubric/validate.py` generalized to validate any suite criteria file (checkpoint set derived
      from the file); both evals pass 18/18.
- [x] The `COMPUTED` G-score mapping + free-lunch judge notes documented as `rubric/judge.md` §8
      (`judge_version` 2.0.0 → 2.1.0; no eval-#1 instruction changed).
- [x] `rubric/rubric-defined-outcome.md`: compact scoring doc (deliberately does NOT mirror the mass
      tables — the validator prints them as the source of truth, closing eval #1's drift-bug class).

## Phase 3 — Gold cases  → `cases/`
- [ ] KOCT anchor case (+ same-day sibling-vintage N-PORTs as live distractors);
      post-rally (≈0/negative net remaining upside); post-drawdown (buffer partially
      consumed); Ultra/Deep Buffer (Ref₀ = K_top/0.95 rule); 100%-buffer fund; a
      floor-vs-buffer discrimination probe; an SPX contrast case (~20× strike scale);
      a designed reconciliation-break case.

## Phase 4 — Harness extension  → `harness/`
- [ ] **Precondition:** refactor graders.py to data-driven dispatch (currently hardcodes
      earnings atom ids) + scoring.py's gate→atom map; then the `COMPUTED`-aware refusal
      grader and the `free_lunch_fired` headline flag.

## Phase 5 — Graded runs + write-up
- [ ] Run models through both evals; populate the taxonomy from real traces; extend
      `PAPER.md` (or a v2) with the suite framing.
