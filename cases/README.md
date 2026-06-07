# Gold cases — Phase 3

Three real SEC filings, each authored into a gold answer for **every checkpoint** of the
[earnings-analysis workflow](../workflow/earnings-analysis.md), scored by the
[rubric](../rubric/criteria.yaml). Every gold figure is transcribed from the actual filing and
carries a `{document, locator, verbatim}` citation — **no invented numbers**. Consensus is
oracle-supplied (not in the filings) and cited to a public source. The shared contract is
[`_TEMPLATE.case.yaml`](_TEMPLATE.case.yaml).

| Case | Issuer | Period | Scale | Deliberate traps exercised |
|---|---|---|---|---|
| [`blk-2025q3`](blk-2025q3.case.yaml) | **BlackRock, Inc.** (asset manager — the flagship vertical) | Q3 2025 (ended 2025-09-30) | millions | **sector-N/A** (no gross profit / inventory / COGS); GAAP $8.43 vs **as-adjusted $11.55** non-GAAP EPS divergence with a **basis-guard** against a false ~$2.88 "miss"; geographic-revenue tie-out (4,181+2,065+263 = 6,509); total-NI vs attributable (NCI \$204M); the newly-dilutive Subco-units share subtlety; **not-disclosed probe** (regional operating income) + **answerable twin** (ETF revenue) |
| [`msft-fy2026q2`](msft-fy2026q2.case.yaml) | **Microsoft Corp.** | **Fiscal Q2 2026** (ended 2025-12-31) | millions | **fiscal-vs-calendar** (June FYE → fiscal Q2 = calendar Q4 2025); **three-segment tie-out** (34,116+32,907+14,250 = 81,273); real COGS/gross margin (NOT sector-N/A); guidance largely qualitative → **E4 not_disclosed**; the Azure-deceleration / segment-beat-but-stock-down read |
| [`snow-fy2026q2`](snow-fy2026q2.case.yaml) | **Snowflake Inc.** | **Fiscal Q2 2026** (ended 2025-07-31) | **thousands** | **unit/scale trap** ("in thousands"); **GAAP loss / non-GAAP profit → non-GAAP diluted shares (372,383) > GAAP diluted (335,215)**; full GAAP→non-GAAP **EPS bridge** (SBC \$436M, disclosed income-tax-effect line); **basic-vs-diluted** non-GAAP EPS discipline ($0.38 basic vs $0.35 diluted) on the beat/miss |

Together the three exercise every gating tier and most of the failure taxonomy: a scale trap
(SNOW), a fiscal-vs-calendar period (MSFT, SNOW), a non-GAAP street consensus and the GAAP-vs-street
basis trap (all three), a loss-quarter diluted-share divergence (SNOW), a sector-N/A issuer (BLK),
segment sum-to-total tie-outs (BLK, MSFT), and a genuine not-disclosed + answerable-twin probe (BLK).

## Verification

Each case carries a `verification:` block. **BLK** and **MSFT** were authored and then
**independently re-verified by a separate agent** that re-fetched the primary sources and checked
every figure against its cited string (the MSFT pass caught and corrected a real consensus-narrative
error before shipping). **SNOW**'s automated verify pass did not complete (a spend limit), so every
SNOW figure was re-confirmed **by hand against EDGAR** and the C5 EPS beat was re-based from non-GAAP
basic to non-GAAP diluted for like-for-like consistency with the bridge.

## Provenance

All filings are public on SEC EDGAR. Each case file records the 10-Q and earnings-release (8-K
Exhibit 99.1) accession numbers and URLs under `sources:`. Consensus snapshots cite the public outlet
and date under `consensus:` and are explicitly flagged as oracle-supplied, not filing-derived.
