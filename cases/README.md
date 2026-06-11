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
| [`koct-op2026-postdrawdown`](koct-op2026-postdrawdown.case.yaml) | **constructed** 2026-08-14 (labeled hypothetical) | reference 6.60% below Ref₀, inside the buffer band | buffer **43.98% consumed ≠ breached**; remaining cap **ENLARGED to +21.41% gross**; no unbuffered gap — the stated terms here *understate* the buyer's upside |

Shared across all three: the strike-level recompute that reproduces the stated terms
(283.53/241.96 − 1 = 17.18%; 241.96 × 0.85 = 205.67), the filed payoff grid reconstructed to the
cent at all 12 points, the deep-ITM 2.42 synthetic-long call (pctVal 101.24% — real, not an error),
the E5 calibrated-refusal probe (today's remaining cap is in **no filing** — computable from the
oracle NAV or refusable with the filing's own website-delegation sentence; the issuer tool's 5.39%
print nets out incurred fees, so importing it scores as an import), and a 6-claim verdict table per
case covering all five labels across the trio — including an ACCURATE remaining-terms claim
(post-drawdown) and FALSE claims in *both* directions (false comfort and false alarm).

**Snapshot policy.** Daily NAV and outcome values are Rule 6c-11 issuer-website items, present in
no EDGAR filing — so snapshots are oracle inputs in both run modes. The anchor's snapshot is real
and cited (issuer page + market data). The two variants are **constructed hypotheticals, clearly
labeled** with construction notes; the gold is the deterministic math computed *on* the snapshot,
never the snapshot itself.

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
