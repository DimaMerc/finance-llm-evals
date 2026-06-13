# Eval #2 — live-run failure taxonomy (work in progress)

> Built from REAL graded traces as Phase 5 runs accumulate. Sample size is stated per finding;
> nothing here is extrapolated beyond what the traces show. Run artifacts (parsed answer, raw
> completion, scored report) sit beside this file as
> `<case>__<model>__<mode>.{answer.json,raw.txt,report.*.txt}`.

## Run log

All runs: qwen3.6-27b (a reasoning model; think phase 10–15k chars per case), oracle-packet mode
unless noted, mock judge. Grading = handler calibration v2 (see *Grader calibration*, below).

| # | Case | Mode | Gated | Ungated | Gates fired | Notes |
|---|---|---|---|---|---|---|
| 1 | anchor | oracle-packet | 0.517 | 0.527 | C2SIGN, FREELUNCH† | superseded by run 2 — 900s-deadline truncation cut S1–S3/C7 (salvaged); † truncation-driven |
| 2 | anchor | oracle-packet | **0.732** | 0.741 | C2SIGN | complete memo (926s, 17.1k chars) |
| 3 | postrally | oracle-packet | **0.708** | 0.754 | C2SIGN, C6DIR‡ | complete (932s); ‡ see *band-rule contract gap* |
| 4 | postdrawdown | oracle-packet | 0.473 | 0.507 | FREELUNCH†, C2SIGN, C6DIR | superseded by run 6 — 16k-token cap truncated mid-C7 (salvaged); † truncation-driven |
| 6 | postdrawdown | oracle-packet | **0.702** | 0.749 | C2SIGN, C6DIR | COMPLETE memo (24k budget; needed the inner-quote JSON repair — the model quoted the filing's (the "Buffer") with raw quotes); **FREELUNCH passes on content**: full cost block present |
| 5 | anchor | **e2e** (distractor packet) | **0.651** | 0.660 | C2SIGN | pinned the RIGHT vintage out of 3 same-day filings — no GATE.VINTAGE; modest extraction cost (0.863 → 0.825, post-recalibration) |

## Confirmed failure modes (qwen3.6-27b, N=4 complete-or-salvaged runs)

**The headline contrast (systematic).** Extraction is near-perfect everywhere (E1/E2 = 1.000 in
oracle-packet runs; every stated term, every FLEX leg, exact to the cent with citations) and the
**E5 remaining-cap probe scored a perfect `COMPUTED` derivation in all runs** — inputs named,
fixed-price-level convention stated, value in C6's band (6.06 / 0.81 / 18.26 vs gold 6.0598 /
0.8066 / 18.2550). The model can do *the* headline calculation. The failures live in the
surrounding discipline:

1. **Grid-convention conflation — 4/4 runs, fired `GATE.C2SIGN` every time.** The payoff-grid rows
   come back in the prospectus's idealized %-convention (−85, −5, 0, 17.18 …) instead of per-unit
   dollars — while the same answers carry exactly correct `signature_values`
   (281.11 / 239.54 / 36.29). The model knows the dollar arithmetic and still swaps conventions in
   the table the prospectus prints in %. This is the C2.n_convention failure mode the workflow doc
   predicted, surfaced at gate tier, on every single run.
2. **Consumed-buffer miss — the post-drawdown case's designed trap, caught and CONFIRMED on the
   complete run** (`GATE.C6DIR`, runs 4 and 6): with S_t at 226.00 — 6.6% below Ref₀, inside the
   band — the model labeled buffer status `intact`, after computing the enlarged remaining cap
   (18.26 ✓) correctly. Run 6 adds a clean semantics misread: it computed
   `downside_before_buffer` +0.91 (right value) and labeled it a **"0.91% gap"** — under the
   convention a positive value means NO gap (the buffer-top price level sits above entry).
   Stated-vs-remaining arithmetic survives; the reference-side STATE read does not.
   **The free-lunch predicate, tested honestly**: on the complete memo the model produced a full,
   correct cost-of-protection block (cap cited, dividends, prorated fee, path/exit) — the
   signature gate did NOT catch this model on content. Both of its fires in the log were
   truncation-driven, exactly what the † labeling discipline is for.
3. **Stated-value echo in place of recompute** (C3, all runs): "recomputed" terms are the filing's
   printed figures verbatim; `synth_sanity` echoes the raw strike (2.42) instead of the ratio;
   max loss arrives sign-dropped (+85). The 0.05pp band cannot separate echo from recompute when
   the terms tie (by design — the deferred reconciliation-BREAK case is the discriminator); the
   sanity row and the sign are where the echo shows.
4. **Per-contract / per-unit confusion** (C5, all runs): units 5,278 (multiplier dropped),
   "notional" = the unit count or a 100×-off value, package value null — while `pctval_sum` is
   exact to 10 dp. Extraction-grade precision feeding arithmetic-grade confusion.
5. **Sign discipline on buyer-relative terms** (C6 values, runs 2–5): `downside_before_buffer`
   magnitude right / sign dropped; remaining buffer depth echoes the stated 15% instead of the
   23.07% depth; fee proration day-count slips. The flagship `remaining_cap_gross` is right every
   time.
6. **The e2e result worth quoting**: given three same-day N-PORTs (Sep/Oct/Nov vintages, strikes
   ~1.7–2.9% apart) and a mid-period 497K restating period-start terms, the model **pinned the
   correct series** (S000065317, October, 2026-09-30) — the hard-gate trap did not fire. The
   distractor cost shows up instead as a modest extraction dip (0.863 → 0.825) and a ~0.08 gated
   drop vs the oracle packet.

## The LLM-judge pass (mock vs live judge, the four complete answers)

| Run | mock | LLM judge | delta |
|---|---|---|---|
| anchor (oracle-packet) | 0.732 | **0.712** | −0.020 |
| postrally | 0.708 | **0.682** | −0.026 |
| postdrawdown | 0.702 | **0.657** | −0.045 |
| anchor (e2e) | 0.651 | **0.615** | −0.036 |

The live judge (qwen3.6-27b judging the 7 S2/S3 free-form atoms per case, judge.md contract)
moves the headline by only 2–4.5 points — versus eval #1's −0.147 for the same swap on the same
model family. That is the calculation-heavy design doing its job: eval #2's deterministic surface
(planning, extraction, all seven calculation checkpoints, the gates) is immune to judge
permissiveness by construction, so the mock-vs-live gap collapses to the synthesis tier.

## Grader calibration (changes made after batch 1, all runs re-graded)

- **C1 structure-class labels normalize to the buffer/floor/barrier families**: run 3 answered
  `power_buffer` (the variant name) where the enum wanted `buffer` — buffer-family ≠ an inversion,
  and the gate's intent is catching floor/barrier flips. (Fire cleared on re-grade: 0.629 → 0.708.)
- **Extra-leg fabrication now requires a non-filed strike**: runs 3/5 listed the cash-sleeve MMDA
  row as a fifth "leg" (strike null). Over-including a real filed row is an E2.completeness error,
  not an invented instrument; `GATE.FABRICATION` no longer fires for it. (0.627 → 0.651 on e2e.)
- **Band-rule contract gap (run 3's remaining `C6DIR` fire)**: the model's numbers are exactly
  right (0.81 / 0.78 vs gold 0.8066 / 0.7806) but it labeled the sign `positive` where the gold
  label is `~zero` — the ±1.0pp band rule lived only gold-side. The live SCHEMA now states the
  band rule (and that the cash sleeve is not a leg, and that structure_class is the class, not the
  variant name). Run 3 keeps its grade; the fire is annotated as contract-gap-driven.

## Infrastructure notes

- Qwen3.6 thinks in `delta.reasoning_content` for 10–15k chars per case; the client captures it,
  budgets 16k+ tokens / 2400s, and salvages truncated JSON (`_salvaged`, flagged in run output).
  The post-drawdown case provokes the longest think — it needed >16k total tokens (rerun at 24k).
- A truncated memo fires `GATE.FREELUNCH` by the predicate's letter (protection asserted upstream,
  cost block never reached). Truncation-driven fires are labeled † in the run log, never counted
  as content findings.
- The M5 Max rig sleeps ~30 min after last user interaction unless caffeinated; runs ~15–17 min
  per case at ~10k prompt tokens.

## The second subject: qwen2.5-72b-instruct (non-reasoning, 3 complete runs)

| Case | qwen3.6-27b (reasoning) | qwen2.5-72b (non-reasoning) | 72B gates |
|---|---|---|---|
| anchor | 0.732 | **0.638** | none |
| postrally | 0.708 | **0.584** | C6DIR |
| postdrawdown | 0.702 | **0.577** | C6DIR |

The reasoning 27B beats the non-reasoning 72B on every case despite a 2.7× size disadvantage —
N=1 per architecture class, so this is an observation, not an architecture study. What the
per-checkpoint traces support:

- **The grid conflation is shared (now N=2 subjects).** The 72B filled the same idealized-% rows
  (−85 / 0 / 17.18) where per-unit dollars belong — same as qwen3.6 in all four of its runs. Two
  subjects in the same trap is suggestive the prospectus's %-table convention genuinely captures
  models — though both are Qwen-lineage (different generations), so cross-family replication is
  needed before calling it task-level. C2's dollars requirement caught both either way. (The 72B's grids were complete, so GATE.C2SIGN's structural check passed and the misses
  landed in the per-row payoff_usd bands instead — same substance, different scoring surface.)
- **The remaining-outcome arithmetic is where the think phase earns its keep.** qwen3.6 computed
  the E5 remaining-cap probe perfectly in every run; the 72B missed it in all three — including
  reporting **4.78% on two different cases with different NAV_t inputs** (an anchored/reused wrong
  value rather than a recompute), and on post-drawdown a full state inversion (−0.94%, `negative`,
  `below_band` vs gold +18.26%, `positive`, `partially_consumed` — GATE.C6DIR fired, as designed).
- **Extraction is strong in both subjects**: 0.912 on all three 72B runs; 0.86–0.91 across the
  27B's runs. Both subjects also share the C5 per-contract/per-unit confusion and
  stated-echo tendencies (the 72B's `synth_sanity` came back as a literal `true`).
- Run mechanics: the 72B produced complete, parse-clean memos in ~12 min/case with zero thinking
  chars — no salvage, no truncation. The failure mode is wrong numbers, not broken output.

## The qwen3-coder-next attempt (single run, recorded as-is)

The non-reasoning contrast subject produced an **ungradeable answer** on its one attempt
(JIT-loaded with a small context): no think phase and instant emission, but (a) **percentage
values as decimal fractions** (0.06058 where the schema demands 6.06 — an instruction-compliance
failure that would fail every band), (b) **unescaped quotes inside compact-line citations**
(raw XML attribute fragments pasted into verbatims), and (c) a **degeneration loop** in the
synthesis prose ("…remaining_cap_gross = 0.06058; but the oracle NAV_t…" repeating until the
context cut at ~32.5k chars). Three repair classes (base, inner-quote escape, truncation salvage)
could not recover a parseable memo — which is itself the graded outcome an unassisted run would
score: zero. A fair re-attempt needs the model loaded with a ≥32k context; until then this stands
as N=1: the reasoning model produced four complete, parseable, ~0.7-gated memos; the coder model
produced none.

## Open items
- `--judge llm` pass on completed answers (mock judge inflates S-tier presence atoms).
- PAPER v2 once the run matrix is filled.
