# Gold cases — Phase 3

Real SEC filings, each authored into a gold answer for **every checkpoint** of its workflow,
scored by its rubric. Every gold figure is transcribed from the actual filing and carries a
`{document, locator, verbatim}` citation — **no invented numbers**. Oracle inputs (consensus,
market snapshots) are not in the filings and are either cited to a public source or explicitly
labeled as constructed.

## Eval #1 — Earnings analysis

Workflow: [earnings-analysis](../workflow/earnings-analysis.md) · rubric:
[criteria.yaml](../rubric/criteria.yaml) · contract: [`_TEMPLATE.case.yaml`](_TEMPLATE.case.yaml).

| Case | Issuer | Period | Scale | Deliberate traps exercised |
|---|---|---|---|---|
| [`blk-2025q3`](blk-2025q3.case.yaml) | **BlackRock, Inc.** (asset manager — the flagship vertical) | Q3 2025 (ended 2025-09-30) | millions | **sector-N/A** (no gross profit / inventory / COGS); GAAP $8.43 vs **as-adjusted $11.55** non-GAAP EPS divergence with a **basis-guard** against a false ~$2.88 "miss"; geographic-revenue tie-out (4,181+2,065+263 = 6,509); total-NI vs attributable (NCI \$204M); the newly-dilutive Subco-units share subtlety; **not-disclosed probe** (regional operating income) + **answerable twin** (ETF revenue) |
| [`msft-fy2026q2`](msft-fy2026q2.case.yaml) | **Microsoft Corp.** | **Fiscal Q2 2026** (ended 2025-12-31) | millions | **fiscal-vs-calendar** (June FYE → fiscal Q2 = calendar Q4 2025); **three-segment tie-out** (34,116+32,907+14,250 = 81,273); real COGS/gross margin (NOT sector-N/A); guidance largely qualitative → **E4 not_disclosed**; the Azure-deceleration / segment-beat-but-stock-down read |
| [`snow-fy2026q2`](snow-fy2026q2.case.yaml) | **Snowflake Inc.** | **Fiscal Q2 2026** (ended 2025-07-31) | **thousands** | **unit/scale trap** ("in thousands"); **GAAP loss / non-GAAP profit → non-GAAP diluted shares (372,383) > GAAP diluted (335,215)**; full GAAP→non-GAAP **EPS bridge** (SBC \$436M, disclosed income-tax-effect line); **basic-vs-diluted** non-GAAP EPS discipline ($0.38 basic vs $0.35 diluted) on the beat/miss |

Together the three exercise every gating tier and most of the failure taxonomy: a scale trap
(SNOW), a fiscal-vs-calendar period (MSFT, SNOW), a non-GAAP street consensus and the GAAP-vs-street
basis trap (all three), a loss-quarter diluted-share divergence (SNOW), a sector-N/A issuer (BLK),
segment sum-to-total tie-outs (BLK, MSFT), and a genuine not-disclosed + answerable-twin probe (BLK).

## Eval #2 — Defined-outcome (buffer) ETF analysis

Workflow: [defined-outcome-analysis](../workflow/defined-outcome-analysis.md) · rubric:
[criteria-defined-outcome.yaml](../rubric/criteria-defined-outcome.yaml) · contract:
[`_TEMPLATE-defined-outcome.case.yaml`](_TEMPLATE-defined-outcome.case.yaml).

The KOCT core: **one real fund** (Innovator U.S. Small Cap Power Buffer ETF — October, series
S000065317, outcome period 2025-10-01 → 2026-09-30), **two filings that share no figure** (the
497K states the percentages; the N-PORT holds the four FLEX strikes — they tie only through the
options math), and **three oracle snapshots** that put the same structure into three different
mid-period states. The packet deliberately includes live distractors: the September and November
sibling-vintage N-PORTs (same-day filings, adjacent accessions, strikes ~1.7–2.9% apart) and a
**mid-period 497K restating the period-start terms** in a current-dated filing.

| Case | Snapshot | State probed | Headline gold |
|---|---|---|---|
| [`koct-op2026-anchor`](koct-op2026-anchor.case.yaml) | **REAL** 2026-06-10 (issuer NAV $36.46, NAV₀ $33.00, IWM $285.02 — all cited) | mid-period after a rally: reference above the cap strike, buffer intact | remaining cap **+6.06% gross / +5.82% net** vs the stated 17.18% — quoting the stated cap to today's buyer is the defining failure; the 9.49% unbuffered gap comes first |
| [`koct-op2026-postrally`](koct-op2026-postrally.case.yaml) | **constructed** 2026-09-18 (labeled hypothetical) | near-cap, 12 days to expiry | remaining cap **+0.81% gross / +0.78% net → "~zero"**: little or no remaining upside, full remaining downside (gap 13.97%); includes the no-arbitrage note on why the NAV-anchored net floor is ~the one-year ER, not negative |
| [`koct-op2026-postdrawdown`](koct-op2026-postdrawdown.case.yaml) | **constructed** 2026-08-14 (labeled hypothetical) | reference 6.60% below Ref₀, inside the buffer band | buffer **43.98% consumed ≠ breached**; remaining cap **ENLARGED to +18.26% gross** vs the stated 17.18%; NAV down only 0.91% against IWM's −6.60% (the put spread absorbing the move *is* the buffer working); no unbuffered gap — the stated terms here *understate* the buyer's upside |

Shared across all three: the strike-level recompute that reproduces the stated terms
(283.53/241.96 − 1 = 17.18%; 241.96 × 0.85 = 205.67), the filed payoff grid reconstructed to the
cent at all 12 points, the deep-ITM 2.42 synthetic-long call (pctVal 101.24% — real, not an error),
the E5 calibrated-refusal probe (today's remaining cap is in **no filing** — computable from the
oracle NAV or refusable with the filing's own website-delegation sentence; the issuer tool's 5.39%
print nets out incurred fees, so importing it scores as an import), and a 6-claim verdict table per
case covering all five labels across the trio (distribution: AAPSO×5, FALSE×7, WRONG_BASIS×3,
NOT_VERIFIABLE×2, ACCURATE×1) — including an ACCURATE remaining-terms claim (post-drawdown) and
FALSE claims in *both* directions (false comfort and false alarm).

**Snapshot policy.** Daily NAV and outcome values are Rule 6c-11 issuer-website items, present in
no EDGAR filing — so snapshots are oracle inputs in both run modes. The anchor's snapshot is real
and cited (issuer page + market data). The two variants are **constructed hypotheticals, clearly
labeled** with construction notes; the gold is the deterministic math computed *on* the snapshot,
never the snapshot itself.

## Eval #3 — Discounted-cash-flow valuation

Workflow: [dcf-analysis](../workflow/dcf-analysis.md) · rubric:
[criteria-dcf.yaml](../rubric/criteria-dcf.yaml) · contract:
[`_TEMPLATE-dcf.case.yaml`](_TEMPLATE-dcf.case.yaml) · gold recompute:
[`_dcf_gold_mcd.py`](_dcf_gold_mcd.py).

**One real company, one labeled oracle model.** A DCF's base lines are filed facts; its
assumptions are not. So the case splits cleanly: the income/balance/cash-flow lines are the
**real FY2025 10-K** (cited to the cent at printed rounding), and the forecast + WACC components +
terminal are the **oracle layer** (labeled, fed in both run modes). The gold is the closed-form
math computed *on* those inputs — reproduced by `_dcf_gold_mcd.py`, no hand arithmetic.

| Case | Issuer | Base period | Headline gold |
|---|---|---|---|
| [`mcd-fy2025-dcf`](mcd-fy2025-dcf.case.yaml) | **McDonald's Corp.** (stable, heavily-franchised cash-flow business — DCF is genuinely the right method) | FY2025 (accession 0000063908-26-000035) | fair value **$227.82/share** on a conservative base case (4% growth, **WACC 7.15%**, g 2.5%) → **~20% overvalued** vs the real $286.12 price — but **TV is 80.6% of EV** and a ±50bp WACC swing moves per-share **+14.8%/−11.9%**, so the call hinges on the discount rate (false-precision territory) |

The case exercises the full gate ledger: the unlevered-FCFF↔WACC↔EV↔bridge **consistency spine**
(`GATE.BASIS`), the **net-debt bridge** (`GATE.BRIDGE` — the EV/share blunder lands at **$278.60**,
only −2.6% from the market price, so the *wrong* method looks fair while the right one says
overvalued), the false-precision predicate (`GATE.FALSEPRECISION`, 80.6% terminal value), the
units lock (`GATE.SCALE`), and the WACC-basis gate (`GATE.WACC`). The **E5 probe** is the company
WACC — undisclosed in any 10-K but computable from the supplied components (the typed
`{COMPUTED, value, derivation}` answer, keyed to C2's band), with total debt + diluted shares as
the answerable twin. The **6-claim** verdict table spans all five labels (ACCURATE×2,
ACCURATE_ON_BASE_CASE_ONLY×1, FALSE×1, WRONG_BASIS×1 — the bridge blunder — NOT_VERIFIABLE×1 — the
undisclosed WACC). The `manifest.planted_error_variants` block pins the three Phase-4 "subtly-wrong
DCF" perturbations (the bridge omission as the headline looks-right-is-wrong case; basis-mix and
`g ≥ WACC` as the catastrophic-but-obvious contrast).

**Assumption policy.** A DCF is a model: the discount rate and forecast live in no filing, so they
are oracle inputs in both run modes (like eval #1's consensus, eval #2's snapshot). The base lines
are real and cited; the market price is a real 2026-06-15 quote (oracle input — daily price is in no
filing); the gold is the math computed *on* these, never the assumptions themselves.

## Verification

Each case carries a `verification:` block. **BLK** and **MSFT** were authored and then
**independently re-verified by a separate agent** that re-fetched the primary sources and checked
every figure against its cited string (the MSFT pass caught and corrected a real consensus-narrative
error before shipping). **SNOW**'s automated verify pass did not complete (a spend limit), so every
SNOW figure was re-confirmed **by hand against EDGAR** and the C5 EPS beat was re-based from non-GAAP
basic to non-GAAP diluted for like-for-like consistency with the bridge.

The **KOCT cases** were verified by a four-agent adversarial pass (independent N-PORT re-extraction
including both sibling XMLs, 497K re-extraction against the raw filing text, closed-form recompute
of every calculated gold, and a rubric-atom coverage map) — zero blockers; the minor locator and
rounding findings were fixed in place and are logged in each case's `verification.notes`. The two
variant cases share the anchor's filings gold byte-for-byte; their variant-specific math is
verified separately.

## Provenance

All filings are public on SEC EDGAR. Each case file records its accession numbers and URLs under
`sources:`. Eval #1 consensus snapshots cite the public outlet and date under `consensus:`;
eval #2 market snapshots document their provenance (real + cited, or constructed + labeled) under
`snapshot:`. Both are explicitly oracle-supplied, never filing-derived.
