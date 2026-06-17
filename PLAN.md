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

## Phase 3 — Gold cases  → `cases/`  ✅ core done (KOCT trio; new-fund cases deferred)
- [x] **KOCT core** (scoped by budget decision 2026-06-10): the anchor case with a REAL
      cited snapshot (issuer NAV 36.46 / NAV₀ 33.00 / IWM 285.02, 2026-06-10 → remaining
      cap +6.06 gross / +5.82 net vs stated 17.18), plus **post-rally** (constructed,
      near-cap, +0.78 net → "~zero"; the NAV-anchored no-arb floor ≈ ER/(1+cap_net)
      documented) and **post-drawdown** (constructed, buffer 43.98% consumed ≠ breached,
      remaining cap ENLARGED to +18.26 gross) — both labeled hypothetical with
      construction notes. Same-day sibling-vintage N-PORTs (Sep/Nov) + a mid-period
      497K restating period-start terms packaged as live distractors in every case.
- [x] Eval-#2 case contract: `cases/_TEMPLATE-defined-outcome.case.yaml`; cases are
      self-contained YAML; `cases/README.md` carries the suite section.
- [x] Verified: a 4-agent adversarial pass on the anchor (N-PORT + 497K re-extraction,
      closed-form recompute, rubric-coverage map; 349 checks, zero blockers) and a
      3-agent judgment-layer pass on the variants — which caught a REAL no-arb
      construction error (post-drawdown NAV re-golded 31.85 → 32.70) and a rubric gap
      promoted to **rubric 1.0.1** (C7.deciding now admits disclosure-/scope-decided
      verdicts). Each case logs its pass in `verification:`.
- [ ] *(deferred to a later budget cycle)* Ultra/Deep Buffer (Ref₀ = K_top/0.95 rule);
      100%-buffer fund; floor-vs-buffer discrimination probe; SPX contrast case
      (~20× strike scale); designed reconciliation-break case.

## Phase 4 — Harness extension  → `harness/`  ✅ done
- [x] **The dispatch refactor:** `graders.py` is now a suite-agnostic engine (refusal
      placeholder → suite handlers → penalties → judge/entailment → default, the original
      flow); the eval-#1 logic moved verbatim into `harness/suites/earnings.py`;
      `scoring.py`'s gate map is **derived from each rubric's `fired_by` hooks** (positive
      atoms fire when unmet, penalty atoms when present) and the refusal checkpoint
      (E6/E5) is suite-supplied, never hardcoded. **Eval #1 verified byte-identical** to
      the pre-refactor baseline (3 cases × 5 variants + demo, diffed).
- [x] **Eval-#2 suite** (`harness/suites/defined_outcome.py`): leg/payoff/recompute/
      remaining-outcome/claim-verdict handlers; per_leg/grid/claim row expansion; the
      **`COMPUTED`-aware E5 refusal grader** (judge.md §8 G-mapping, value keyed to C6's
      band); the **GATE.FREELUNCH deterministic predicate** with the `free_lunch_fired`
      headline flag on the Result; `deciding_kind`-aware C7 grading (rubric 1.0.1);
      oracle + 6 flawed variants (vintage_slip / refscale_slip / feebasis_mix /
      free_lunch / fabricate_probe / c6_flip).
- [x] `python -m harness selftest` now guards BOTH suites: eval-#2 oracle 1.000/AllPass
      on all 3 KOCT cases; the gate tiers open differentiated GAPs (VINTAGE 0.82 ·
      REFSCALE 0.46 · FEEBASIS 0.18 · FREELUNCH 0.07+flag · C6DIR 0.07). This also fixes
      `suite`/`selftest`, which crashed on the KOCT cases after Phase 3 landed them.

## Phase 5 — Graded runs + write-up
- [x] **Eval-#2 live path** (`harness/live_defined_outcome.py`): the two-filing packet builder
      (anchored 497K excerpts + slimmed N-PORT XML; EDGAR + `.edgar_tmp/` cache fallback;
      ~10k-token oracle-packet mode, `--e2e` distractor mode ~20k), the live OUTPUT SCHEMA
      mirroring the gold key paths, prompt + tolerant parse reusing `live.py`'s client.
      The selftest now round-trips a schema-perfect answer to **1.000/AllPass** on every
      defined-outcome case — the live contract is pinned to the graders by regression test.
- [x] **Live runs, both judges**: qwen3.6-27b (reasoning) through all 3 KOCT cases + the
      e2e distractor probe — 0.732/0.708/0.702/0.651 mock, 0.712/0.682/0.657/0.615 llm-judge;
      qwen2.5-72b-instruct (non-reasoning) through the 3 cases — 0.638/0.584/0.577. All
      artifacts + reports committed under `outputs/eval2-live/`.
- [x] **Failure taxonomy from real traces** (`outputs/eval2-live/TAXONOMY.md`): the shared
      %-for-$ grid trap (N=2 subjects); the consumed-buffer miss caught by its designed case;
      the remaining-outcome arithmetic separating the reasoning from the non-reasoning subject;
      the e2e vintage pin succeeding; FREELUNCH passing on content (truncation fires labeled);
      grader-calibration log (running real models found 3 contract gaps, all fixed + re-graded).
- [x] **Judge-vs-expert calibration**: the 28 S2/S3 verdicts hand-graded by the author —
      28/28, κ = 1.0 (caveats: n=28, self-judging model, anchoring risk; stated in the paper).
- [x] **PAPER.md v2**: the suite framing + eval-#2 design + the two-model findings +
      calibration, fact-checked against the artifacts by a 2-agent verification pass
      (4 blockers fixed pre-commit, incl. a same-lineage honesty fix on the N=2 claim).

---

# Eval #3 — Discounted-cash-flow valuation  *(the most-used model in research/AM/PE; same repo, same machinery)*

The valuation every analyst runs and the one most often quietly wrong: project unlevered
free cash flow, discount at WACC, capitalize a terminal value, **bridge enterprise value to
equity**, divide by shares. The output is a closed-form consequence of a handful of inputs,
so it is perfectly recomputable — and the failure modes are precise. The signature is **the
DCF that looks right and is wrong**: a clean per-share number built on one corrupting error
(unlevered FCF discounted at the cost of equity; `g ≥ WACC`; or EV divided by shares with no
net-debt bridge). The discriminator the eval rewards is **internal consistency + assumption
discipline**, not arithmetic fluency. The signature gate is **`GATE.FALSEPRECISION`** — a
deterministic predicate that auto-fails a decimal-precise target on a 70%-terminal model
with no sensitivity block (the DCF analog of eval #2's free-lunch).

## Phase 1 — Workflow decomposition  → `workflow/dcf-analysis.md`  ✅ done
- [x] Define the task (inputs: 10-K + oracle assumption set + dated market snapshot +
      valuation-claim set; the analyst's real steps; the citation-anchored valuation memo).
- [x] **18 checkpoints** (P1–P3 planning · E1–E5 extraction · C1–C7 calculation ·
      S1–S3 synthesis), calculation-heavy, each independently scorable and chainable e2e.
- [x] Grading routed per checkpoint (deterministic DCF math · hybrid value+entailment ·
      label-det + derivation-judge for the E5 WACC refusal probe · judge for S1–S3).
- [x] Gate ledger across three tiers: **hard** (`GATE.BASIS` unlevered↔WACC↔EV↔bridge
      consistency, firing at P1 **and** C5; `GATE.SCALE` units) · **scoped** (`GATE.WACC`
      → `[C3,C4,C5.ev]`; `GATE.BRIDGE` → `[C6,S1]`; `GATE.FALSEPRECISION` → `[S2,S3]`) ·
      **in-checkpoint** (`GATE.C1FCF`, `GATE.C4TERM`, `GATE.C7SIGN`) · `GATE.FABRICATION` reused.
- [x] Tolerance table (exact-rounding base lines · 0.5%-rel FCF/PV/EV · 5-bp WACC ·
      1.0%-rel per-share with `level_ref`) and a full failure-taxonomy table.
- [x] Running example: **McDonald's FY2025** (CIK 63908, accession 0000063908-26-000035).

> Adversarially reviewed pre-commit by a 2-agent pass (finance-correctness + eval-design).
> Formula spine confirmed correct (FCFF/WACC/Gordon-TV/bridge/conventions). Fixes applied:
> 4 anchor/convention corrections (net debt ~$36B→~$39B filed-derived; diluted shares
> 718M→716.4M FY2025; **lease treatment pinned to `operating`** — the load-bearing bridge
> choice for a franchiser; equity-method-investment add-back named); 2 doc-honesty blockers
> (Phase 4 adds **two** literal `_EXPANSIONS` keys — `per_year_row`/`per_grid_cell` — not
> "no engine surgery"; `GATE.WACC` targets the `C5.ev` sub-atom, sparing `C5.consistency`/
> `C5.tvshare`); plus run-mode-dependent E5 credit, a `C3.n_convention` penalty atom, the
> `deciding_kind` carry-forward at C7, and the signature-case blast-radius note.

## Phase 2 — Rubric  → `rubric/criteria-dcf.yaml` + `rubric/rubric-dcf.md`  ⏳ next
- [ ] Turn each checkpoint's success criteria into gated, weighted atoms on the existing
      `criteria.yaml` schema (no schema change); set calculation-heavy weights.
- [ ] Encode the gate ledger as deterministic predicates; `GATE.FALSEPRECISION` predicated
      on the structured sensitivity block; tolerances into `tolerances:`.
- [ ] Document the E5 typed-answer extension + `false_precision_fired` flag in `judge.md`.
- [ ] `validate.py` linter (invariant assertions) + a reproducible worked example.

## Phase 3 — Gold cases  → `cases/`  ⏳
- [ ] MCD FY2025 gold: every base line + bridge item cited to the 10-K, the assumption set
      as the labeled oracle layer, the closed-form DCF math as gold.
- [ ] The **signature "subtly-wrong DCF"** case — headline variant = the missing net-debt
      bridge (scoped, looks-right-is-wrong); basis-mix + `g≥WACC` as catastrophic contrast.

## Phase 4 — Harness suite  → `harness/suites/dcf.py`  ⏳
- [ ] Suite module (projection / WACC / discounting / TV / EV / bridge / sensitivity / claims
      handlers + the `GATE.FALSEPRECISION` predicate), exposing `REFUSAL_CP = "E5"` and
      `LLM_JUDGE_CPS = {S1,S2,S3}` so `run_case` threads `refusal_cp='E5'` into `score()`
      (required for the E5 F-β substitution + the AllPass E5-exclusion to fire — default is E6).
- [ ] Register the suite: `'dcf-valuation': 'criteria-dcf.yaml'` in `harness/rubric.py`
      `SUITE_RUBRICS`, and `for_case` in `harness/suites/__init__.py`.
- [ ] Add the two `_EXPANSIONS` keys (`per_year_row`, `per_grid_cell`) so C1.fcff / C3.pv /
      C7.grid split per-row (until then they grade single-lump); evals #1–2 byte-invariant
      (guarded by `selftest`).

## Phase 5 — Graded runs + write-up  → `outputs/` + `PAPER.md`  ⏳
- [ ] Run frontier + local models through both run modes; grade; extend the taxonomy and PAPER.
