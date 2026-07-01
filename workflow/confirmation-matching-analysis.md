# Workflow — OTC derivative confirmation matching (eval #5)

> The affirmation-desk **"affirm only if it ties"** control — the derivatives sibling of eval #4's
> reconciliation. Two counterparties each book their side of an OTC swap and send confirmations; the
> ops desk matches the economic terms field-by-field and **affirms only if they tie**, otherwise it
> is a mismatch (do not affirm; escalate). Phase-1 deliverable of eval #5. Rubric:
> `rubric/criteria-confirmation-matching.yaml`.

## Why this eval exists — and why it's grounded

Public back-office / post-trade AI benchmarking is a **green field**: every named finance benchmark
(Finance Agent Benchmark, BigFinanceBench, FinanceBench, FinQA) is analyst-facing over SEC filings;
none cover custody, settlement, reconciliation, or **trade matching**. Eval #4 opened that category;
this one extends it into **derivatives**.

And unlike eval #4 (where the ETF PCF is NSCC-disseminated and not public, so the gold had to be
*constructed*), this eval's gold is **grounded in a real, publicly-downloadable message**: the FpML
5.10 standard's own sample confirmation **`ird-ex01-vanilla-swap.xml`** from
[fpml.org](https://www.fpml.org/spec/fpml-5-10-5-rec-1/html/confirmation/fpml-5-10-examples.html)
(ISDA's official standards site, freely accessible). Our-side gold terms are extracted verbatim from
that message; only the counterparty confirmation and the planted break are constructed on top of the
real trade.

## The trade (real FpML `ird-ex01`)

A single-currency **EUR fixed-float interest-rate swap**. **Party A** receives fixed **6.00%**
(30E/360, annual) and pays **EUR-LIBOR-BBA 6M** (ACT/360, semi-annual) on **EUR 50,000,000**
notional, **1994-12-14 → 1999-12-14**, MODFOLLOWING. Party A's trade id is `TW9235`; the
counterparty's is `SW2000`.

## The gold cases and the planted break

**Break case** (`irs-confirm-2026`): the counterparty's confirmation matches on **everything** —
notional, dates, index, frequencies, day-counts, direction — **except the fixed rate: 6.00% (ours)
vs 6.05% (theirs).** A ~5 bp break ≈ **EUR 25,000 per annum** on EUR 50MM — unambiguously material.
Gold answer: **MISMATCHED, do not affirm, localized to the fixed rate.** The two trade ids differing
(`TW9235` vs `SW2000`) is **expected** — each party assigns its own internal id — *not* a break.
That's the materiality judgment.

**Clean case** (`irs-confirm-2026-clean`): the same trade with the counterparty rate at 6.00% (ties).
Gold answer: **AFFIRMED.** It closes the perma-mismatcher gap — a model that cries "mismatch" on
everything (e.g. flagging the expected trade-id difference) is caught here.

## Checkpoints (8)

| CP | Grades | Gate |
|---|---|---|
| **P1** Pin the trade | product (single-ccy fixed-float IRS), the two parties (by LEI), trade date, both trade ids | — |
| **E1** Extract our side | economic terms + leg direction, cited to the FpML message | — |
| **E2** Extract counterparty side | the same fields from their confirmation | — |
| **C1** Field-by-field compare | the match grid (our vs their, per field); **direction** consistent | **GATE.DIRECTION** (hard) |
| **C2** Materiality | material economic break vs expected/representational diff; **scale** lock | **GATE.SCALE** (hard), **GATE.MATERIALITY** (scoped) |
| **C3** Localize | name the offending field + both values + the economic impact | — |
| **D1** Affirm / mismatch decision | **AFFIRM** only if all economic terms tie; else **MISMATCHED**, localized + escalate | **GATE.MATCH** (the signature) |
| **D2** Calibrated refusal | the swap's mark-to-market is **not determinable** from a confirmation (needs market data) | **GATE.FABRICATION** on a made-up MTM |

Checkpoint weights: P1 .10 / E1 .12 / E2 .10 / C1 .16 / C2 .14 / C3 .14 / D1 .16 / D2 .08. D2's
headline is the FailSafeQA F-β LLMC_β(R, G), β = 0.5.

## Gate ledger

| Gate | Tier | Fires when | Blast radius |
|---|---|---|---|
| **GATE.DIRECTION** | hard | fixed payer/receiver read backwards — the whole comparison is on the wrong footing | C2, C3, D1 |
| **GATE.SCALE** | hard | notional or rate mis-scaled (EUR 50MM as 50k; 0.06 as 6.0/600% or 6 bp) | C3, D1 |
| **GATE.MATERIALITY** | scoped | the material-vs-expected judgment is wrong (expected trade-id flagged as a break, or the rate break dismissed as cosmetic) | C3, D1 |
| **GATE.MATCH** | scoped (**signature**) | the model **AFFIRMS a trade whose economic terms do not tie** | D1 → 0, **match_override_fired** flag |
| **GATE.FABRICATION** | hard (figure) | a fabricated term, or a made-up mark-to-market | per-figure void; AllPass = 0 |

Plus the over-cautious mirror penalty **`D1.n_falsemismatch`** — flagging MISMATCHED on a trade that
ties (caught on the clean case).

## The taxonomy (oracle + designed flaws)

| Variant | Gated | Gate | What it shows |
|---|---:|---|---|
| `oracle` | 1.000 | none | matches every term, catches the rate break, MISMATCHED |
| `affirm_match` | **0.840** | **GATE.MATCH** + flag | *all terms compared right, AFFIRMED a broken trade* — the highest-scoring failure, the most dangerous |
| `scale_slip` | 0.637 | GATE.SCALE | notional read in thousands |
| `materiality_blind` | 0.611 | GATE.MATERIALITY | flags the expected trade-id diff as a break (right verdict, wrong reason); MATCH does **not** fire |
| `direction_flip` | 0.466 | GATE.DIRECTION | fixed payer/receiver inverted — the biggest cascade |
| `fabricate_probe` | 0.920 | GATE.FABRICATION | invents a mark-to-market → D2 G = 0 |

On the clean case, `false_mismatch` (crying mismatch on a trade that ties) is caught — D1 → 0.
Reproduce any row: `python -m harness run --case irs-confirm-2026 --model <variant>`.

The pattern *is* the finding, and it mirrors reconciliation exactly: the eval tells "looks right, is
wrong" (`affirm_match`, 0.840, the control switched off) apart from a foundational error
(`direction_flip`, 0.466, the trade read backwards) — and localizes each to the checkpoint that owns
it. Confirmation matching and basket reconciliation are the two halves of the same **"tie out or
stop"** discipline.

## Hardening (adversarial gaming review)

The suite was put through a six-attacker adversarial gaming review (each trying to *game* a gate or
force a *false positive*, every candidate reproduced against the live harness and verified). Four
blockers and several soft spots were found and fixed: the affirm/mismatch call is graded by a
**settlement-desk family classifier** — a *go-ahead synonym* ("approve", "release for settlement",
"book it", "tie out", "green") still trips GATE.MATCH, and a *negated affirm* ("do not release") is
still a break, while a *negated break* ("no material break; terms tie") is correctly an affirm;
GATE.SCALE catches a **10× percent-vs-decimal** rate mis-scale via a gold-relative order-of-magnitude
check; GATE.DIRECTION is derived from the **extracted legs** (not a self-reported flag); a fabricated
mark-to-market **asserted in prose** trips GATE.FABRICATION; and the D2 refusal reason is
paraphrase-robust (a two-prong terms-not-value **and** needs-market-data check). A fail-closed
backstop trips GATE.MATCH on any *future* unlisted go-ahead synonym whose answer body reads as an
affirm.
