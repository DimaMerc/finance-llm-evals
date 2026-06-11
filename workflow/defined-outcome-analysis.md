# Workflow — Asset Management → Defined-Outcome (Buffer) ETF Analysis

> Phase 1 deliverable for **eval #2**, the suite's moat eval. This document decomposes
> the diligence a competent advisor/analyst must run before putting a client into a
> defined-outcome ("buffer") ETF — especially **mid-period** — into independently
> scorable checkpoints. It is the spec the eval-#2 rubric (`rubric/`), gold cases
> (`cases/`), and harness extension (`harness/`) are built against, exactly as
> `workflow/earnings-analysis.md` is for eval #1.

A buffer ETF is four FLEX option legs in a trust wrapper. Everything the marketing
says — the cap, the buffer, the "defined outcome" — is a closed-form consequence of
four strike prices, one initial reference level, and one fee. I ran the
change-management side of an ETF servicing platform at Brown Brothers Harriman —
creation/redemption, derivatives processing, the lifecycle plumbing where an options
position that doesn't reconcile to its stated terms is a break, not a rounding error.
Later, building an options-overlay analyzer, the signature bug I caught was the
**free lunch**: an analysis that reported downside protection with no forgone-upside
cost. That analysis is wrong *by construction* — the cap exists because the buffer
must be paid for; the fund's own prospectus says the cap is literally the strike of
the call sold to finance the put spread. This eval encodes that discipline:
**every stated marketing number is recomputable from the option legs, so the eval's
spine is the recompute-vs-stated reconciliation — deterministic everywhere the math
lives, with the judge reserved for the suitability read.** A model that quotes the
prospectus cap to a mid-period buyer, mixes a gross cap with a net buffer, or reports
protection without its cost has not made a small mistake; it has made the mistake
that mis-sells the product. The decomposition below is designed so each of those is
caught at the checkpoint that owns it.

### The pipeline at a glance

```
 PLANNING              EXTRACTION                   CALCULATION                      SYNTHESIS
 ─────────             ──────────                   ───────────                      ─────────
 P1 vintage   ║gate║   E1 stated terms (497K)       C1 leg roles + ref level ⟦fail⟧  S1 entry-timing verdict
 P2 ref/scale ║gate║   E2 FLEX legs (N-PORT)        C2 payoff at expiry      ⟦fail⟧  S2 cost of protection ┊gate┊
 P3 fee basis ┊gate┊   E3 fees + basis + OCC        C3 recompute vs stated           S3 calibrated suitability
                       E4 snapshot + staleness      C4 net-of-fee terms
                       E5 remaining-cap probe       C5 notional tie-outs
                                                    C6 remaining outcome     ⟦fail⟧
                                                    C7 claim verification
   ║gate║ = hard gate (zeros all dependents)   ┊gate┊ = scoped gate (P3: the fee-basis chain; S2: the free-lunch predicate → S2 + S3)
   ⟦fail⟧ = in-checkpoint hard-fail (zeros that checkpoint only)
```

Three planning checkpoints pin the vintage and the conventions, five extraction
checkpoints tie every figure to a `{document, locator, verbatim string}` citation
across two filings that never repeat each other, seven calculation checkpoints redo
the options math as closed-form executable arithmetic — no judge anywhere in the
stage — and three synthesis checkpoints route to an LLM judge for the read. Eighteen
checkpoints, each independently scorable and each chainable into one end-to-end run.
The stage split is deliberately calculation-heavy (3 / 5 / 7 / 3 versus eval #1's
3 / 6 / 5 / 3): this workflow's center of gravity is the deterministic options math.

---

## The task

What a diligent advisor or analyst must do before recommending a buffer ETF to a
client — given that the client would buy **today**, which is almost never the
outcome-period start date: pin the exact fund vintage and outcome period, extract
the stated terms and the actual option legs, **recompute the terms from the strikes**,
compute the *remaining* outcome for a buyer entering at today's NAV, verify the
marketing claims, and write a calibrated suitability read.

### Inputs

The eval hands the model (or the agent) one fund's document packet plus a dated
market snapshot:

| Input | What it is | Why it matters |
|---|---|---|
| **Summary / statutory prospectus** (497K and/or 485BPOS on EDGAR, plus the post-reset 497 "sticker") | The stated terms: **cap (gross *and* net)**, **buffer (gross *and* net)**, outcome-period start/end dates, the unitary expense ratio in the **fee table**, the hypothetical **payoff grid**, the cap-setting mechanics, and the risk language (OCC settlement guarantee, price-return basis, FLEX liquidity). | This is where every stated percentage lives — and where the **strikes appear nowhere**. The stated terms apply *only to a period-start buyer*; a mid-period 485BPOS restates the same period-start terms, which makes "I found 17.18% in a current filing" a live trap. The fact sheet is marketing; the prospectus and the N-PORT legs are the law. |
| **N-PORT holdings report** (NPORT-P, filed per series) | The four FLEX option legs: verbatim titles, **strikes**, expiry, **signed** contract counts, the 100-share multiplier, month-end marks (`valUSD`/`pctVal`), net assets, the cash sleeve, and the series identity (`seriesName`/`seriesId`). | The **only public source for the strikes** — and the stated cap/buffer percentages appear nowhere in it. The two documents tie *only* through the options math. Terms (strikes, expiry) are static all period; state (marks, net assets) is a stale month-end snapshot — the asymmetry is itself a checkpoint concept (E4). Sibling monthly vintages file the same day with adjacent accession numbers: the wrong-vintage distractor is built into the source data. |
| **Market snapshot** (oracle-supplied) | `{snapshot_date, NAV_t (fund NAV/share today), NAV_0 (fund NAV/share on day 1 of the outcome period), S_t (current reference-asset level)}`. | The remaining-outcome math needs today's and day-1 NAV, and **neither is in any EDGAR filing** (daily NAV and "current outcome period values" are Rule 6c-11 / issuer-website items — the prospectus delegates them to the website verbatim). Hand-fed in *both* run modes, mirroring eval #1's consensus snapshot. |
| **Marketing claim set** | 3–6 short verbatim claims in fact-sheet / issuer-website register (e.g., *"15% downside buffer"*, *"upside to a cap of [X]%"*, *"defined outcomes regardless of market direction"*), at least one of which is true-only-at-period-start, basis-confused, or false. | The real-world trigger for this workflow is an advisor reading marketing. C7 grades claim verification deterministically against gold verdicts. |
| **Case manifest** (gold side, not shown to the model) | Trust/CIK, `seriesId`, ticker, vintage month, outcome-period start/end, **variant type** (Buffer / Power Buffer / Ultra-Deep Buffer / 100%-buffer / floor / barrier — drives the leg-role recovery rule), the four strikes with roles, the initial reference level, stated terms gross/net, ER, gold payoff-grid values, gold remaining-outcome values at the snapshot, gold claim verdicts. | Builds the planning-stage gold answers, the gates, and the per-leg figure expansion. |

> **Running-example convention.** Eval #1's workflow doc invents no company numbers.
> This document deliberately adapts that rule: one **verified live example** runs
> through the text, because options math is only legible with real strikes —
> **Innovator U.S. Small Cap Power Buffer ETF – October** ("KOCT"; Innovator ETFs
> Trust, CIK 1415726, series S000065317; NPORT-P accession 0000894189-26-009590,
> period 2026-01-31; 497K accession 0001213900-25-094547, outcome period
> 2025-10-01 → 2026-09-30). Every figure from it is marked *(KOCT)* and was verified
> on EDGAR. All other values remain explicit placeholders (e.g., *"NAV_t =
> \$[XX.XX]"*). Additional gold cases are authored only in `cases/` (Phase 3).

**The KOCT structure, for reference throughout** *(KOCT — N-PORT, all four legs
5,278 contracts × 100 shares on IWM, the iShares Russell 2000 ETF, all expiring
2026-09-30, European-style, OCC-cleared)*:

| Leg | Verbatim N-PORT title | Strike | Role |
|---|---|---|---|
| Purchased call | `IWM 09/30/2026 2.42 C` | 2.42 | Deep-ITM **synthetic long** (pctVal 101.24% — normal, not an error) |
| Purchased put | `IWM 09/30/2026 241.96 P` | 241.96 | **Buffer top** = initial reference level Ref₀ |
| Written put | `IWM 09/30/2026 205.67 P` | 205.67 | **Buffer bottom** (241.96 × 0.85 = 205.67 → the 15% Power Buffer, exactly) |
| Written call | `IWM 09/30/2026 283.53 C` | 283.53 | **The cap** (283.53 / 241.96 − 1 = 17.18% gross) |

Stated terms *(KOCT — 497K)*: cap **17.18% gross / 16.39% net**, buffer
**15% gross / 14.21% net**, unitary fee **0.79%**. Every one of those numbers is
recomputable from the table above. That is the eval.

### The analyst's real steps

1. **Plan / pin the product.** Confirm the trust, the *exact series and vintage month*
   (the family runs 12 monthly series with identical names except the month), and the
   outcome period **including the year** (the "October" fund's period spans two
   calendar years). Lock the reference asset and its price scale — strikes are quoted
   on the **ETF share price** (IWM ≈ \$242), not the index level (Russell 2000 ≈
   2,400) — the 100-share contract multiplier, and the sign convention (written legs
   are negative). Fix the quote basis: every cap/buffer number has a **gross and a
   net-of-fee twin**; decide which basis each downstream comparison uses, and pin the
   entry framing (period-start buyer vs today's buyer at NAV_t).
2. **Extract.** Pull the stated terms, dates, and fee table off the prospectus and the
   four FLEX legs off the N-PORT, each with a `{document, locator, verbatim string}`
   citation. Record what is *state* (month-end marks, stale by construction) versus
   *terms* (strikes/expiry, static all period). Mark anything genuinely **not in the
   filings** — starting with today's remaining cap.
3. **Calculate.** Assign each leg its structural role and recover the initial
   reference level by construction; reconstruct the payoff at expiry from the four
   strikes; **recompute the stated cap, buffer, buffer-bottom identity, and max loss
   from the strikes and reconcile against the prospectus**; net the terms of the fee;
   tie out notionals and the per-unit package value; compute the **remaining**
   cap/buffer/downside-before-buffer for a buyer entering at NAV_t today.
4. **Synthesize.** State the entry-timing verdict (what today's buyer actually gets,
   versus what the prospectus states) as discrete calls; price the protection — capped
   upside, forgone dividends, fee drag, path/exit risk — with **no free lunch**; get
   the risk claims right in *both* directions (OCC-cleared FLEX options are not
   issuer-credit instruments, and "no counterparty risk at all" is also wrong); write
   a calibrated suitability bottom line that names what could not be verified.

### The deliverable

A short, citation-anchored **suitability memo** plus the structured checkpoint record
behind it:

1. **Pinned header** — trust/series/ticker, vintage month, outcome-period start and
   end dates, variant type, reference asset (with the ETF-share-price scale stated),
   quote basis (gross/net) per figure, entry framing (snapshot date and NAV_t).
   (This is also the gating record.)
2. **Leg table** — the four FLEX legs, each `{put/call, written/purchased, strike,
   expiry, signed contracts, multiplier}` with the verbatim N-PORT title as citation,
   plus assigned **role**; net assets and the cash sleeve.
3. **Terms-reconciliation block** — each stated term beside its strike-level
   recompute with the formula and both citations: cap (gross→net), buffer (gross→net),
   buffer-bottom identity, max loss, payoff grid values.
4. **Remaining-outcome block** — remaining cap (gross and net of remaining fee),
   downside-before-buffer, remaining buffer, buffer-status label, days remaining —
   each derived from the model's own extracted terms plus the oracle snapshot.
5. **Claim-verdict table** — each marketing claim labeled `ACCURATE |
   ACCURATE_AT_PERIOD_START_ONLY | WRONG_BASIS | FALSE | NOT_VERIFIABLE`, with the
   recomputed figure that decides it.
6. **Synthesis** — the entry-timing verdict, a **required cost-of-protection block**
   (capped upside + forgone dividends + fee drag + path/exit risk — the structured
   field the free-lunch predicate checks), the risk-claim read, and a calibrated
   bottom line naming every figure it could *not* verify.

The same artifact grades checkpoint-by-checkpoint: all options math deterministically,
free-form synthesis by an LLM judge.

---

## How this maps to an eval

The decomposition satisfies the same hard constraint as eval #1: **each checkpoint
must be independently scorable, yet the checkpoints must chain into one end-to-end
analyst run** — a HealthBench-style isolated-probe battery *and* a Vals AI–style
end-to-end agentic task in one artifact. Eval #2 adds a second, lens-defining
constraint: **maximize the deterministic surface.** Every domain trap here except the
suitability narrative reduces to dates, strikes, ratios, or fee arithmetic, so the
deterministic/judge ratio is pushed deliberately higher than eval #1's — seven
calculation checkpoints and zero judge calls before the synthesis stage.

**The checkpoint model.** Unchanged from eval #1: every checkpoint declares its
inputs, the intermediate artifact it must produce, explicit success criteria, a
grading type, and the named failure modes it guards against. The structural
guarantee also carries over: **no synthesis or calculation checkpoint consumes a
figure that an extraction checkpoint did not first produce and cite.** One
generalization: the citation triple is `{document, locator, verbatim string}` — for
the prospectus the locator is a page/section, for the N-PORT XML it is the element
path of the `invstOrSec` block, where the leg `title` strings (e.g.
`IWM 09/30/2026 241.96 P` *(KOCT)*) are perfect verbatim citations.

**Run modes — isolated probe vs. end-to-end** (FinanceBench Closed-Book / Oracle
framing, unchanged):

- **Oracle / isolated probe** — inject the correct frame (series, vintage, dates,
  reference asset, basis) and the gold evidence spans (the four leg blocks, the
  stated-terms sentences, the fee table), then score *pure reasoning*: can the model
  do the options math and the reconciliation once retrieval is removed?
- **End-to-end** — the agent must locate the filings, **pin the right vintage out of
  the sibling series** (the case packet deliberately includes the adjacent-accession
  sibling N-PORTs — for KOCT, the September and November funds, filed the same day
  with near-identical XML and strikes 2–4% apart), and extract the legs itself.

The harness reports the **oracle score next to the gated end-to-end score**, so a
wrong-vintage pin (which cascades) doesn't mask genuine downstream options-math
competence.

> **The market snapshot is oracle-supplied in *both* run modes.** Day-1 NAV, today's
> NAV, and today's reference level are not in any EDGAR filing — daily NAV and
> market price are Rule 6c-11 issuer-website items, and the prospectus *says*
> the daily potential-outcome values live on the website *(KOCT — 497K:
> "www.innovatoretfs.com/koct provides … information relating to the potential
> outcomes of an investment in the Fund on a daily basis")*. The "realistic task"
> claim therefore covers prospectus/N-PORT retrieval and extraction, not market-data
> sourcing. Note the asymmetry with eval #1's consensus snapshot: remaining-outcome
> values *do* exist publicly (issuer website) but are absent from the filings and
> **computable from the legs** — that asymmetry is the whole point of the E5 probe.

**Deterministic vs. judge grading.** Each checkpoint is tagged with the cheapest
grader that can score it correctly. Eval #2 keeps eval #1's four types and documents
two deliberate extensions:

- **Deterministic** — all options math: leg-role classification, payoff
  reconstruction, recompute-vs-stated reconciliation, fee netting, notional tie-outs,
  remaining-outcome arithmetic, claim verdicts. Gold = `{value, unit, tolerance}` with
  an evidence pointer; FinQA/TAT-QA-style executed program-of-thought, with the
  reference-asset scale and multiplier folded in before comparison.
- **Hybrid (value + entailment)** — extraction checkpoints: the value is checked
  deterministically *and* the citation is entailment-checked (does
  `IWM 09/30/2026 205.67 P` actually entail a written put struck at 205.67 expiring
  2026-09-30?), scored separately so *right-number/wrong-citation* is distinguished
  from *hallucination*. The N-PORT's user-defined OSI-style identifier
  (`4IWM 260930P00205670` *(KOCT)*) redundantly encodes expiry/type/strike, giving
  the entailment leg a deterministic cross-check.
- **Label-deterministic + derivation-judge** — the calibrated-refusal probe (E5),
  *extended*: because the probed figure (today's remaining cap) is
  computable-but-undisclosed, the typed-answer contract adds a third type —
  `{COMPUTED, value, derivation}` — beside eval #1's `{value, citation}` and
  `{NOT_DISCLOSED, reason}`. The label and any computed value are checked
  deterministically (the value against the C6 band); the derivation/reason is judged.
  This is a documented extension of the E6 contract, not a silent fork.
- **Judge** — free-form synthesis only (S1–S3), with correctness operators *and*
  contradiction operators against the deterministic numbers upstream — **plus one
  deterministic predicate inside S2**: the free-lunch gate (below).

**Evidence-citation requirement.** Every extraction and calculation checkpoint names
its evidence as `{document, locator, verbatim string}` triples, extended to a *list*
for the reconciliation checkpoints that legitimately cite both documents — C3 ties
the prospectus-stated cap sentence *(KOCT: "17.18% prior to taking into account any
fees")* to the N-PORT written-call title *(KOCT: `IWM 09/30/2026 283.53 C`)*: the
direct structural analog of eval #1's press-release-vs-10-Q reconciliation, except
here the two documents share **no figure at all** — they tie *only* through the math.

**Calibrated-refusal credit.** "Not in the provided filings" is a first-class
answer (FailSafeQA), and eval #2's probe is richer than eval #1's: *"What is the
remaining cap for a buyer at today's NAV?"* has **three gradeable outcomes** —
correct computation with derivation (best), refusal that names exactly which inputs
are missing from the filings and how the figure would be computed (acceptable), and
a confident number with no derivation (auto-fail; importing a remembered
issuer-website figure scores as an import, not a computation). The probe is paired
with an **answerable twin** that *is* disclosed but buried (the fee-table total and a
named leg's contract count), so over-refusal is penalized symmetrically. Headline
scoring keeps E6's FailSafeQA F-beta (β = 0.5) exception — the refusal checkpoint's
headline is the F-beta, not the awarded/raw-positive pool.

**Gating — three tiers, plus the signature predicate.** Same three-tier model as
eval #1, with eval #2's analogs (gate ids are YAML-ready for Phase 2):

- **Hard gate — `GATE.VINTAGE` (P1)**: wrong fund series, wrong vintage month, or
  wrong outcome-period **year** (the wrong-fiscal-period analog). Twelve sibling
  series differ only by a month label and 2–4% in strikes; analyzing the November
  fund's legs against the October fund's stated terms poisons everything. Zeros all
  dependents (E1–E5, C1–C7, S1–S3).
- **Hard gate — `GATE.REFSCALE` (P2)**: reference-asset / strike-scale / contract
  convention error (the unit-scale analog) — treating IWM-share-price strikes as
  Russell 2000 index levels (a ~10× slip; SPX-referenced competitor funds make it
  ~20×), dropping the 100-share multiplier, or flipping the written-leg sign
  convention. Dependents are declared as an **explicit exclusion list**, the same
  way eval #1's scale gate carves out the per-share sub-figures: the gate zeros the
  leg-derived chain — E2's value and cite legs, E4's state fields, C1–C7 — while
  **E1, E3, and E5's answerable twin survive** (prospectus-side percentages and
  fee-table figures carry no strike scale).
- **Scoped gate — `GATE.FEEBASIS` (P3)**: a gross-vs-net-of-fee basis mismatch (the
  GAAP/non-GAAP analog) — committing to compare a net cap against a gross recompute,
  or quoting "100% protection" as net. Zeros the fee-basis chain — **C4, C7, S1, and
  C6's net-of-fee legs** — but leaves the strike extraction and the gross options
  math standing.
- **In-checkpoint hard-fails** — zero only their own checkpoint: a leg-role /
  structure-class inversion at C1 (buffer read as floor or barrier), a payoff
  sign/regime error at C2, and a remaining-upside direction flip or buffer-status
  inversion at C6.
- **Scoped gate — `GATE.FREELUNCH` (S2): the signature gate, designed
  deterministic.** Eval #1's gates are deterministic predicates, and a judge-fired
  gate would break that contract. So the deliverable *requires* a structured
  **cost-of-protection block** (capped upside with the cap value, forgone dividends,
  fee drag, path/exit risk), and the gate is the deterministic predicate: *the memo
  presents downside protection while the cost block is absent, empty, or contradicts
  the C3 cap*. This mirrors how eval #1 made S1's directional read checkable by
  contingency on C5. The judge separately penalizes free-lunch *phrasing* in prose
  ("protection at no cost") via negative atoms. Firing zeros **S2 and S3** — a
  suitability bottom line built on costless-protection framing is poisoned, not just
  the section that framed it — flags the case `AllPass = 0`, and the harness reports
  `free_lunch_fired` as a named headline flag: it is the eval's signature finding.
  This is the suite's one **synthesis-stage-firing** gate — a deliberate, declared
  deviation from eval #1, whose gates all fire at planning.
- **`GATE.FABRICATION`** — reused unchanged from eval #1: a fabricated strike, leg,
  or CUSIP (FLEX legs have **no** CUSIP — `cusip = "N/A"` in the N-PORT; a model
  "extracting" one is hallucinating) voids that figure's positive value+cite legs and
  cascades to the frame gates only when the fabricated field *is* the frame (series
  identity, dates, reference asset, scale).

The harness reports **both** the gated/All-Pass score and the un-gated
partial-credit score, with the GAP between them as a first-class number, in Oracle
and end-to-end modes — unchanged from eval #1, and more important here, because a
wrong-vintage hard gate would otherwise dominate the headline.

**Tolerance bands** — per figure type, derived from the figures' own provenance
(strikes are filed to the cent; stated percentages are printed at 2 dp; NAV-based
terms inherit NAV rounding):

| Figure type | Tolerance |
|---|---|
| Strikes, expiry dates, contract counts, multiplier (as filed in the N-PORT) | **exact** — strike to the filed cent, counts integer-exact, dates exact |
| Stated terms as extracted (cap/buffer gross & net, ER, period dates) | **exact at the filing's printed rounding** |
| Recomputed gross cap / gross buffer / max gross loss (strike ratios) | ≤ **0.05 pp** vs the stated figure at its printed rounding *(KOCT: 283.53/241.96 − 1 = 17.1805% vs stated 17.18%)* |
| Buffer-bottom identity `K_bot = Ref₀ × (1 − buffer)` | exact to the cent *(KOCT: 241.96 × 0.85 = 205.666 → 205.67)* |
| Fee netting (net = gross − ER) | exact vs the **issuer's stated net** figure (the stated net is gold — issuer conventions can differ from naive subtraction) |
| Per-unit payoff values V(S_T) at gold grid points | exact to **\$0.01** (pure strike arithmetic) |
| Fund-return %-rows tied to the filed payoff grid (idealized convention) | ≤ **0.5 pp** per printed row — the filed grid prints the idealized reference-return convention; "correcting" it to the leg-exact values (or vice versa) is a penalized negative atom, not a banded miss |
| Per-leg notional / per-unit package value (from month-end marks) | ≤ **0.5% relative** |
| Remaining cap / downside-before-buffer / remaining buffer (NAV-based) | ≤ **0.1 pp**, *and* internally consistent with the model's own extracted terms + the oracle NAV |
| Remaining **net** terms (fee-prorated) | ≤ **0.15 pp** under the stated ACT/365 proration convention |
| Status labels (buffer intact / partially consumed / below band; remaining-upside sign) | exact label — a sign flip is the C6 in-checkpoint fail |

> **Why the remaining-cap band is 10 bps, not 1 (and not 100).** Remaining cap =
> NAV₀ (1 + cap_g) / NAV_t − 1. Each NAV leg is quoted to the cent on a ~\$25–45
> handle, contributing up to ±0.02% relative each; the two legs propagate by
> root-sum-square to ≈ 0.03%, and the stated cap's 2-dp rounding adds up to
> ±0.005 pp at the cap-price level. A 1-bp band would fail models whose inputs each
> pass their own checks. But the band must stay an order of magnitude below the
> smallest *conceptual* error in the chain — quoting the stated cap to a buyer after
> a modest 4% rally is off by **roughly 100 bps or more** — so 10 bps passes honest
> rounding and fails every real mistake. Net-of-fee remaining terms get 15 bps
> because the fee proration adds a day-count convention (ACT/365 pinned; a ±1-day
> disagreement on days-remaining moves the figure < 0.3 bp, so the convention, not
> the band, carries the precision). And the **NAV-anchored convention is pinned for
> a measured reason**: the defensible leg-intrinsic alternative,
> `(K_cap − K_synth)/v_t − 1`, differs from the NAV-anchored form by the day-1
> time-value and cash-sleeve residual — **≈ 15 bps at period start**, larger than
> every arithmetic-noise term above — so the two forms are different quantities, not
> two roundings of one. The leg form stays a labeled cross-check at C6, never the
> graded primary; and E5's `COMPUTED` value atom is keyed to this same C6 band in
> Phase 2, so the probe's tolerance and the calculation's tolerance can never diverge.

---

## Checkpoints

Four stages, eighteen checkpoints. Each is tagged with a **stage**, a **grading
type**, and the named **failure-taxonomy bucket(s)** it owns, so the Phase-5
taxonomy table is generated mechanically from graded traces.

### Summary table

| ID | Stage | Checkpoint | Grading | Gates downstream? | Primary failure modes guarded |
|---|---|---|---|---|---|
| **P1** | Planning | Pin trust, series, **vintage**, outcome period (incl. year) | deterministic | **Hard gate** | Vintage confusion, wrong outcome-period year, date-quadruple misread |
| **P2** | Planning | Lock reference asset, strike scale, contract conventions | deterministic | **Hard gate** | Strike-scale / reference-asset error, multiplier/sign error |
| **P3** | Planning | Fix the quote basis (gross vs net) and entry framing | hybrid | **Scoped gate** → C4, C7, S1, C6-net | Gross/net fee-basis mixing, period-start-vs-today framing |
| **E1** | Extraction | Stated outcome terms from the prospectus | hybrid | — | Stated-term mis-extraction, mis-citation, wrong-document |
| **E2** | Extraction | The four FLEX legs from the N-PORT (per-leg, signed) | hybrid | — | Dropped leg, sign flip, hallucinated CUSIP/strike |
| **E3** | Extraction | Fee table, return basis, OCC/credit language | hybrid | — | Fee miss, dividend-basis miss, credit-language miss |
| **E4** | Extraction | Market-snapshot intake + terms-vs-state staleness ledger | hybrid | — | Stale-mark-as-current, repPdDate/repPdEnd confusion |
| **E5** | Extraction | Calibrated refusal: the remaining-cap probe (+ twin) | label-det. + derivation-judge | — | Fabricated remaining terms, marketing import, over-refusal |
| **C1** | Calculation | Assign leg roles, classify structure, recover Ref₀ | deterministic | *(in-checkpoint fail)* | Buffer/floor/barrier inversion, deep-ITM call misread |
| **C2** | Calculation | Reconstruct the payoff at expiry (regimes + grid) | deterministic | *(in-checkpoint fail)* | Payoff arithmetic/regime error, dropped synthetic-long strike |
| **C3** | Calculation | **Recompute stated terms from strikes and reconcile** | deterministic | — | Recompute-vs-stated break, wrong denominator (Ref₀) |
| **C4** | Calculation | Net the terms of fees (cap and buffer both) | deterministic | — | Fee-netting error, "100% protection" netting |
| **C5** | Calculation | Notional, coverage, per-unit package value tie-outs | deterministic | — | Multiplier/notional error, pctVal>100% misread |
| **C6** | Calculation | Remaining outcome for a buyer at NAV_t today | deterministic | *(in-checkpoint fail)* | Stated-vs-remaining conflation, direction flip, consumed-buffer miss |
| **C7** | Calculation | Verify the marketing-claim set | deterministic | — | Claim-verdict errors in both directions |
| **S1** | Synthesis | Entry-timing verdict: stated vs remaining, as discrete calls | judge | — | Quoting stated terms to today's buyer, contradiction |
| **S2** | Synthesis | Cost of protection + risk-claim truthfulness | judge + det. predicate | **Scoped gate** → S2, S3 (free-lunch) | **Free-lunch claim**, false credit-risk claim, missing cost item |
| **S3** | Synthesis | Calibrated suitability bottom line | judge | — | Sycophancy, over-refusal, missing diligence item |

**Template** — every checkpoint below uses the same shape: **Consumes** ·
**Produces** · **Success criteria** · **Grading** · **Guards against**.

---

### Stage 1 — Planning

> Pin the vintage and the conventions. Twelve sibling series differ only by a month
> label and 2–4% in strikes, and every percentage in the product has a gross and a
> net twin — everything downstream inherits this pin, so the gating failures live here.

#### P1 — Pin the trust, series, vintage, and outcome period (including the year)

- **Consumes:** Prospectus cover/term sentences (fund name, outcome-period dates);
  N-PORT `genInfo` (`seriesName`, `seriesId`, `repPdDate`, `repPdEnd`) and the legs'
  `expDt`; the (deliberately included) sibling-vintage filings; case manifest gold
  (trust/CIK, seriesId, vintage month, outcome-period start/end, variant type).
- **Produces:** A pinned header —
  `{trust, cik, series_name, series_id, ticker, vintage_month, outcome_period_start,
  outcome_period_end, variant_type, date_ledger: {outcome_start, outcome_end_eq_expiry,
  nport_repPdDate, nport_repPdEnd}}` — each field tied to its cover-page /
  `genInfo` / term-sentence evidence string.
- **Success criteria:**
  - [ ] Trust, CIK, and **series** match gold (`seriesId` is the hard identifier —
        *(KOCT: S000065317, "Innovator U.S. Small Cap Power Buffer ETF - October")*);
        the sibling vintages in the packet are **not** the pinned series.
  - [ ] The **vintage month and the outcome-period year** match gold — the "October"
        fund's period spans two calendar years *(KOCT: 2025-10-01 → 2026-09-30)*, and
        the prior/next reset of the *same* series is a different outcome period.
  - [ ] The **date quadruple is disambiguated**: outcome-period start; outcome-period
        end = the legs' `expDt` (the **last business day**, not necessarily calendar
        month-end — the sibling November vintage expires 2026-10-30 because
        2026-10-31 is a Saturday); the N-PORT `repPdDate` (the month-end snapshot
        date, *(KOCT: 2026-01-31)*); and `repPdEnd` (the **trust fiscal-year end**,
        *(KOCT: 2026-10-31)* — not the data date, not the outcome-period end).
  - [ ] Outcome-period end, the option `expDt`, and the vintage month **mutually
        reconcile** (a mismatch means a wrong-vintage pull).
  - [ ] The pin is **anchored** to `seriesId`/`seriesName` and the term-sentence
        strings, not asserted from the fund's marketing name.
- **Grading:** `deterministic`. **HARD GATE — `GATE.VINTAGE`** — a wrong series,
  vintage month, or outcome-period year zeroes all downstream checkpoints for the case.
- **Guards against:** *Vintage confusion* (sibling monthly series; wrong
  outcome-period year) · *date-quadruple misread* (`repPdEnd` as the data date or
  period end) · *expiry off-by-one* (calendar vs last business day) · *mis-citation*
  of the series identity.

#### P2 — Lock the reference asset, strike scale, and contract conventions

- **Consumes:** N-PORT `derivativeInfo` blocks: `descRefInstrmnt/otherRefInst`
  (`issuerName`, ticker, CUSIP/ISIN of the underlying), `shareNo` (multiplier),
  signed `balance` (contracts) and signed `valUSD`/`pctVal`; the same filing's
  `varInfo` designated-index name (a built-in distractor); the prospectus's
  underlying-ETF definition; case manifest gold.
- **Produces:** A conventions record —
  `{reference_asset: {name, ticker, cusip/isin}, reference_is_etf_share_price: bool,
  strike_scale_sanity: {strike_magnitude, index_level_magnitude, ratio_note},
  contract_multiplier, sign_convention: written_legs_negative, units_per_leg =
  |contracts| × multiplier}` — each tied to its `otherRefInst` / `shareNo` /
  `balance` evidence.
- **Success criteria:**
  - [ ] The reference asset is identified as the **underlying ETF**, by
        ticker/CUSIP/ISIN *(KOCT: IWM, CUSIP 464287655, ISIN US4642876555)* — and
        the strikes are understood as **ETF share prices** (≈ \$242), *not* index
        levels (Russell 2000 ≈ 2,400), despite the same filing's `varInfo`
        designating "RUSSELL 2000 Index" as the Rule 18f-4 index — the in-document
        trap is recognized, not absorbed.
  - [ ] The **100-share multiplier** (`shareNo`) is captured; per-unit (per-share)
        figures are kept distinct from per-contract and notional figures.
  - [ ] The **sign convention** is locked: purchased legs positive, written legs
        negative (`balance` and `valUSD` carry signs in the filing); no leg's
        direction is inferred from its title alone when the signed fields disagree.
  - [ ] The deep-ITM call's strike *(KOCT: 2.42)* is **not** "sanity-corrected" — a
        strike at ~1% of spot is the synthetic-long construction, not a data error.
  - [ ] Each convention assertion cites the verbatim element
        (`otherRefInst`/`shareNo`/`balance`).
- **Grading:** `deterministic`. **HARD GATE — `GATE.REFSCALE`** — a strike-scale /
  reference-asset / multiplier / sign-convention error zeroes the leg-derived chain
  (E2 value + cite legs, E4 state fields, C1–C7), with an **explicit exclusion
  list**: E1, E3, and E5's answerable twin survive.
- **Guards against:** *Strike-scale / reference-asset error* (ETF share price read as
  index level; the ~20× SPX-fund variant) · *multiplier dropped* · *sign-convention
  flip* (written legs treated as purchased) · *"correcting" the deep-ITM strike* ·
  *mis-citation*.

#### P3 — Fix the quote basis (gross vs net of fees) and the entry framing

- **Consumes:** Prospectus stated-terms sentences (gross *and* net of the unitary
  fee — *(KOCT: cap "17.18% prior to taking into account any fees", net 16.39%;
  buffer 15%, net 14.21%)*); the fee table; the oracle snapshot date vs the
  outcome-period dates; case manifest gold.
- **Produces:** A basis-and-framing record — `{quote_basis_map: {cap: gross+net,
  buffer: gross+net, remaining_terms: gross-with-net-shown}, unitary_er,
  entry_framing: {snapshot_date, is_mid_period: bool, days_elapsed, days_remaining},
  comparison_plan (which basis each downstream comparison uses)}`.
- **Success criteria:**
  - [ ] **Both** bases are recognized for **both** terms — cap *and* buffer each have
        a gross and a net twin (fees reduce the effective buffer too, and even "100%
        protection" funds net below 100% by the ER) — and every downstream comparison
        declares its basis before any number is compared.
  - [ ] The **entry framing** is pinned: the snapshot date is located inside the
        outcome period; `days_remaining` runs to the outcome-period end (= `expDt`);
        the analysis is framed for a **buyer at NAV_t today**, with the period-start
        buyer as the explicitly-labeled reference case.
  - [ ] The stated-terms applicability rule is recorded: the prospectus terms apply
        **only to a period-start buyer** (the prospectus says so; a mid-period
        485BPOS restating "17.18%" does not change that).
  - [ ] The unitary ER is carried forward as the netting operand (C4) and the
        proration operand (C6).
- **Grading:** `hybrid` — deterministic basis/date checks plus a judged completeness
  check of the comparison plan.
- **Grading note — SCOPED GATE — `GATE.FEEBASIS`:** committing a gross-vs-net basis
  mismatch here zeros **C4, C7, S1, and C6's net-of-fee legs** — the fee-basis chain —
  but not the strike extraction or the gross options math.
- **Guards against:** *Gross/net fee-basis mixing* set up at planning time · *missing
  net-buffer twin* (netting only the cap) · *period-start framing applied to a
  mid-period buyer* · *days-remaining miscount*.

---

### Stage 2 — Extraction

> Two documents that never repeat each other: the prospectus states the percentages
> and dates; the N-PORT holds the strikes and counts. They tie only through the math.
> Extraction is hybrid — the value deterministically, the citation by entailment —
> so right-number/wrong-citation is caught separately from hallucination.

#### E1 — Extract the stated outcome terms from the prospectus

- **Consumes:** 497K/485BPOS (and any post-reset 497 sticker): the cap and buffer
  sentences (gross and net), the outcome-period sentence, the hypothetical payoff
  grid, the period-start-buyer-only language, the cap-setting mechanics paragraph;
  gold values + verbatim strings.
- **Produces:** A stated-terms table —
  `{cap_gross, cap_net, buffer_gross, buffer_net, outcome_period_start,
  outcome_period_end, payoff_grid_rows[{underlying_return, fund_return}],
  period_start_only_rule: verbatim, cap_setting_mechanics: verbatim}` — each as
  `{value, document, locator, verbatim string}`.
- **Success criteria:**
  - [ ] Cap and buffer are captured **gross and net**, each at the filing's printed
        rounding, each cited to its sentence *(KOCT: 17.18 / 16.39 and 15 / 14.21)* —
        the net figures are *extracted*, not derived (derivation is C4's job).
  - [ ] The outcome-period dates match gold and the **period-start-buyer-only**
        sentence is captured verbatim (it powers C6/C7/S1).
  - [ ] The **payoff grid** rows are captured as disclosed *(KOCT: underlying
        −100/−50/−20/−10/−5/0/+5/+10/+15/+20/+50/+100% → fund
        −85/−35/−5/0/0/0/5/10/15/17.18/17.18/17.18%)* — this is filing-anchored gold
        for C2 and the free-lunch contradiction evidence for S2 (the fund's own table
        prints the forgone upside next to the protection).
  - [ ] The cap-setting mechanics are captured *(KOCT: "The Cap is the strike price
        of that sold call FLEX Option")* — the verbatim basis for the S2 cost story.
  - [ ] **No strike is "extracted" from the prospectus** — strikes appear nowhere in
        it; a strike attributed to the prospectus is a fabrication (GATE.FABRICATION
        hook).
- **Grading:** `hybrid` (value deterministic + citation entailment).
- **Guards against:** *Stated-term mis-extraction* (wrong vintage's terms; gross
  where net was asked) · *mis-citation* · *wrong-document* (claiming strikes from the
  prospectus or percentages from the N-PORT) · *hallucinated term*.

#### E2 — Extract the four FLEX legs from the N-PORT

- **Consumes:** The pinned series' NPORT-P `invstOrSec` blocks; the conventions
  record (P2); gold per-leg fields + verbatim titles; net assets and the cash-sleeve
  line.
- **Produces:** A leg table, one row per leg —
  `{title_verbatim, osi_identifier, put_or_call, written_or_purchased, strike,
  expiry, contracts_signed, multiplier, valUSD_signed, pctVal_signed}` — plus
  `{net_assets, cash_sleeve_pctVal}`, each with its `{document, locator, verbatim
  string}` citation (the leg `title` is the citation).
- **Success criteria:**
  - [ ] **All four legs** are captured — none dropped, none double-counted *(KOCT:
        purchased call 2.42; purchased put 241.96; written put 205.67; written call
        283.53 — each 5,278 contracts × 100, expiring 2026-09-30)* — and no leg is
        imported from a sibling vintage's filing.
  - [ ] Strikes are **exact to the filed cent**; expiry dates exact; contract counts
        integer-exact and **signed** per the P2 convention (written legs negative).
  - [ ] The internal-consistency cross-check passes: each leg's OSI-style identifier
        *(KOCT: `4IWM 260930P00205670`)* re-encodes the same expiry/type/strike as
        the title and the structured fields.
  - [ ] **No CUSIP is reported for a FLEX leg** — the filing says `N/A`; an
        "extracted" CUSIP is a hallucination (GATE.FABRICATION hook).
  - [ ] The deep-ITM call's `pctVal` > 100% of net assets *(KOCT: 101.24%)* is
        captured as filed and **not** flagged as an error or silently rescaled.
  - [ ] Net assets *(KOCT: \$132,953,720.62)* and the cash sleeve *(KOCT: 0.29%)* are
        captured (C5 consumes them).
- **Grading:** `hybrid`. *(Phase 2: a `per_leg_row` per-figure expansion — four rows,
  value + cite legs each, exactly eval #1's per-segment-row mechanism.)*
- **Guards against:** *Dropped leg* · *sign flip* · *hallucinated strike/leg/CUSIP* ·
  *sibling-vintage leg imported* · *pctVal>100% "corrected"* · *mis-citation*.

#### E3 — Extract the fee table, return basis, and credit/structure language

- **Consumes:** The prospectus fee table; the dividend/price-return sentence; the
  OCC settlement-guarantee sentence; the FLEX liquidity / fair-value (Level 2)
  risk language; gold values + verbatim strings.
- **Produces:** `{fee_table: {management, twelve_b1, other, total}, return_basis:
  price_return_no_dividends (verbatim), occ_clearing: verbatim,
  flex_liquidity_valuation: verbatim}` — each with citations.
- **Success criteria:**
  - [ ] The **unitary ER** is extracted from the fee table *(KOCT: management 0.79%,
        12b-1 0.00%, other 0.00%, total 0.79%)* — this is also the E5 answerable-twin
        material, so the extraction must come with its fee-table citation.
  - [ ] The **price-return basis** is captured verbatim *(KOCT: the fund "will not
        receive or benefit from any dividend payments made by the Underlying ETF")* —
        the forgone-dividend cost item S2 requires.
  - [ ] The **OCC language** is captured verbatim *(KOCT: FLEX options "guaranteed
        for settlement by the Options Clearing Corporation")* — the evidence that
        polices the false issuer-credit claim in *both* directions at S2.
  - [ ] The FLEX **liquidity and Level-2 valuation** risk language is captured (the
        honest residual risks: OCC tail risk, clearing-member/omnibus-margin risk,
        model-priced FLEX marks, premium/discount).
- **Grading:** `hybrid`.
- **Guards against:** *Fee miss* · *dividend-basis miss* (setting up a total-return
  comparator error) · *credit-language miss* (setting up a false risk claim) ·
  *mis-citation*.

#### E4 — Intake the market snapshot and build the terms-vs-state staleness ledger

- **Consumes:** The oracle market snapshot `{snapshot_date, NAV_t, NAV_0, S_t}`; the
  N-PORT `repPdDate`/`repPdEnd` and the marks (`valUSD`/`pctVal`/net assets); the
  pinned date ledger (P1).
- **Produces:** A provenance ledger —
  `{snapshot: {date, NAV_t, NAV_0, S_t, source: oracle}, terms: {strikes, expiry,
  multiplier — static for the outcome period, as_of: filing}, state: {valUSD, pctVal,
  net_assets — month-end marks, as_of: repPdDate, staleness_days}}` — every figure
  in the case labeled `current | static-term | stale-state`.
- **Success criteria:**
  - [ ] The snapshot fields are read exactly and dated; `days_remaining =
        outcome_period_end − snapshot_date` is computed on the pinned convention.
  - [ ] **Terms vs state asymmetry is explicit**: strikes/expiry are valid all period
        regardless of filing age; `valUSD`/`pctVal`/net assets are **month-end marks
        as of `repPdDate`** *(KOCT: 2026-01-31, filed 25 days later)* and are never
        presented as current values.
  - [ ] No N-PORT mark is substituted for NAV_t, and `repPdEnd` (trust FYE) is not
        used as any as-of date.
  - [ ] The ledger notes that public N-PORT snapshots exist only for trust
        fiscal-quarter month-ends (25–60+ days stale at publication) — the reason a
        June analysis legitimately pairs a January holdings report with a June
        snapshot.
- **Grading:** `hybrid` (field values deterministic; the two N-PORT date citations
  entailment-checked).
- **Guards against:** *Stale-mark-as-current* · *repPdDate/repPdEnd confusion* ·
  *N-PORT mark substituted for NAV* · *days-remaining miscount*.

#### E5 — Calibrated refusal: the remaining-cap probe (+ answerable twin)

- **Consumes:** The probe — *"What is the remaining cap for a buyer at today's NAV,
  as of [snapshot_date]?"* — posed against the **filings alone** (the figure is
  genuinely absent: issuers publish daily remaining-outcome values on their websites,
  not in EDGAR filings, and the prospectus says so verbatim); the paired
  **answerable twin** — two disclosed-but-buried figures: the fee-table total ER and
  a named leg's contract count *(KOCT: 5,278)*; gold labels, gold derivation, gold
  twin values.
- **Produces:** For the probe, a typed answer — `{COMPUTED, value, derivation}`
  (derivation naming strikes + oracle NAV inputs) **or** `{NOT_DISCLOSED, reason,
  derivation_sketch}` (naming exactly which inputs are missing from the filings and
  how the figure would be computed). For the twin, `{value, citation}` each.
- **Success criteria:**
  - [ ] The probe is **never answered with a bare number**: full credit for a correct
        `COMPUTED` value (within the C6 band) **with** its derivation; full refusal
        credit for `NOT_DISCLOSED` that names the missing inputs (today's and day-1
        NAV) and cites the filing's own website-delegation language; a confident
        underived number is a **hard failure** (GATE.FABRICATION hook), and a number
        imported from remembered issuer marketing without derivation scores as an
        import, not a computation.
  - [ ] On the **twin**, both buried figures are retrieved and cited; refusing them
        (over-refusal) is penalized deterministically.
  - [ ] A vague hedge ("I can't verify that") without the missing-input derivation
        does not earn the refusal credit.
- **Grading:** `label-deterministic + derivation-judge` — labels and computed values
  deterministic, derivation/reason judged. **Headline = FailSafeQA F-beta (β = 0.5)**,
  the E6 exception carried over, with the documented `COMPUTED` extension to the
  typed-answer contract. *Phase-2 F-beta mapping for the new type:* a `COMPUTED`
  value inside the C6 band **with** its derivation earns full correct-answer credit
  in `LLMC_β` (the same R-credit as a retrieved disclosed answer); a confident
  underived number maps to `G = 0`; and the value atom is keyed to **C6's tolerance
  band**, so the probe and the calculation can never diverge.
- **Guards against:** *Sycophancy / failed calibrated refusal* (fabricating today's
  remaining cap) · *marketing import* (quoting the issuer's website number as if
  filed) · *over-refusal* on the disclosed twin · *vague hedging*.

---

### Stage 3 — Calculation

> The options math. All of it is closed-form from four strikes, one reference level,
> one fee, and one NAV — graded deterministically as executed program-of-thought.
> Notation, used throughout: `K_synth` (purchased deep-ITM call), `K_top` (purchased
> put = buffer top), `K_bot` (written put = buffer bottom), `K_cap` (written call),
> `Ref₀` (initial reference level), `ER` (unitary fee), with
> `K_synth < K_bot < K_top ≤ Ref₀ < K_cap`.

#### C1 — Assign leg roles, classify the structure, and recover the initial reference level

- **Consumes:** The leg table (E2); the variant type (P1 manifest gold); gold roles
  and gold Ref₀.
- **Produces:** A role map —
  `{K_synth: deep_ITM_synthetic_long, K_top: buffer_top_put, K_bot: buffer_bottom_put,
  K_cap: cap_call}` — plus `{structure_class: buffer | floor | barrier | accelerated |
  uncapped, Ref0_recovered, recovery_rule}`.
- **Success criteria:**
  - [ ] Each leg's **role** is assigned correctly from `{put/call, written/purchased,
        strike order}` — in particular the deep-ITM purchased call *(KOCT: K = 2.42 ≈
        1% of spot)* is identified as the **synthetic long**, not an error and not a
        zero-strike forward.
  - [ ] The **structure class** is `buffer`: a purchased put at/near the reference
        plus a **written** put below it (the investor bears everything beyond the
        buffer) — explicitly *not* a **floor** (which caps *total* loss and has no
        written lower put) and *not* a **barrier** (protection that vanishes once
        crossed). The classification is decided from the legs, not the fund's name.
  - [ ] **Ref₀ is recovered by the variant rule** — Power/standard Buffer:
        `Ref₀ = K_top` *(KOCT: 241.96)*; Ultra/Deep Buffer: `Ref₀ = K_top / 0.95` —
        and corroborated by two independent identities: `K_bot / Ref₀ = 1 − buffer`
        and `K_cap / Ref₀ = 1 + cap` (within their bands). Ref₀ appears as an
        explicit number in **no filing**; it exists only by construction.
  - [ ] The role map is consistent with the signed positions (a "buffer" read off
        two *purchased* puts fails).
- **Grading:** `deterministic`. **IN-CHECKPOINT HARD-FAIL (`GATE.C1ROLE`)** — a
  structure-class inversion (buffer ↔ floor ↔ barrier) or a leg-role inversion zeroes
  this checkpoint regardless of partial credit; it does not gate downstream (each
  downstream checkpoint is independently graded against gold).
- **Guards against:** *Buffer-vs-floor-vs-barrier inversion* (flips the entire risk
  read) · *deep-ITM call misread* · *role misassignment* · *Ref₀ conflated with the
  current reference level*.

#### C2 — Reconstruct the payoff at expiry

- **Consumes:** The role map + strikes (C1, E2); the disclosed payoff grid (E1);
  gold per-unit values at the gold grid points.
- **Produces:** The per-unit terminal value function, evaluated and regime-labeled —

  `V(S_T) = (S_T − K_synth)⁺ + (K_top − S_T)⁺ − (K_bot − S_T)⁺ − (S_T − K_cap)⁺`

  with the five regimes made explicit:

  | Region | V(S_T) | *(KOCT)* |
  |---|---|---|
  | `S_T ≥ K_cap` | `K_cap − K_synth` (capped) | 281.11 |
  | `K_top ≤ S_T < K_cap` | `S_T − K_synth` (1:1) | — |
  | `K_bot ≤ S_T < K_top` | `K_top − K_synth` (flat — the buffer zone) | 239.54 |
  | `K_synth ≤ S_T < K_bot` | `S_T − K_synth + (K_top − K_bot)` (1:1, cushioned) | — |
  | `S_T < K_synth` | `K_top − K_bot` (floor of the structure) | 36.29 |

  plus the idealized outcome mapping the prospectus grid prints, with
  `r = S_T/Ref₀ − 1`:
  `R_fund(r) = min(r, cap_g)` for `r ≥ 0`; `0` for `−buffer_g ≤ r < 0`;
  `max(r + buffer_g, maxloss_g)` for `r < −buffer_g`.
- **Success criteria:**
  - [ ] V(S_T) matches gold **exactly to \$0.01** at every gold grid point — pure
        strike arithmetic — with each point labeled with its regime.
  - [ ] The three signature per-unit values are produced: max value
        `K_cap − K_synth` *(KOCT: 281.11)*, buffer-zone value `K_top − K_synth`
        *(KOCT: 239.54 — **not** Ref₀; the 2.42 strike stays in the reconstruction)*,
        and structural floor `K_top − K_bot` *(KOCT: 36.29)*.
  - [ ] The **idealized mapping reproduces the prospectus's own grid** at its printed
        values *(KOCT: −10% → 0%; +50% → 17.18%; −100% → −85%)*, and the model keeps
        the two quantities **separate**: the idealized mapping is the outcome relative
        to day-1 NAV as the prospectus defines it; the leg-exact package values embed
        the `K_synth` offset (≈ `K_synth/Ref₀` ≈ 1 pp in the below-buffer region) and
        day-1 time value. **Grid-convention note:** the filed grid prints the
        idealized convention *(KOCT: −50% → −35%)* while leg-exact package arithmetic
        gives ≈ **−35.35%** from the `K_synth` offset — per-unit **dollars** grade
        exact to \$0.01, the **%-row tie** to the filed grid gets a ≤ 0.5 pp band per
        printed row, and a model that "corrects" the filed convention to the
        leg-exact values (or vice versa) trips a penalized negative atom, not a
        banded miss. Conflating them silently absorbs a conceptual error into a
        tolerance band.
  - [ ] Written legs **subtract** — a flipped sign (payoff rising above the cap, or
        the buffer zone not flat) is the in-checkpoint fail.
  - [ ] Max gross loss is stated correctly: `(K_top − K_bot)/Ref₀ − 1` *(KOCT:
        36.29/241.96 − 1 = **−85%**, matching the grid's −100% → −85% row)* — a 15%
        buffer does **not** mean losses stop at −15%.
- **Grading:** `deterministic` (multi-point, regime-checked). **IN-CHECKPOINT
  HARD-FAIL (`GATE.C2SIGN`)** on a payoff sign/regime inversion.
- **Guards against:** *Payoff arithmetic/regime error* · *dropped `K_synth` strike*
  (buffer-zone value reported as Ref₀) · *sign flip on written legs* · *"protected
  below the buffer" misread* (max loss ≠ −buffer) · *interim-NAV vs at-expiry
  conflation*.

#### C3 — Recompute the stated terms from the strikes and reconcile (the spine)

- **Consumes:** Strikes + roles + Ref₀ (C1, E2); the stated terms (E1); gold
  recomputed values.
- **Produces:** The reconciliation block — for each term, the recompute, the stated
  value, the difference, and a **two-document evidence list**:

  - `cap_gross_recomputed = K_cap / Ref₀ − 1` *(KOCT: 283.53/241.96 − 1 = 17.1805% →
    stated 17.18%)* — evidence: `[N-PORT "IWM 09/30/2026 283.53 C", 497K "17.18%
    prior to taking into account any fees"]`
  - `buffer_gross_recomputed = 1 − K_bot / Ref₀` *(KOCT: 1 − 205.67/241.96 =
    15.00% → stated 15%)* — evidence: `[N-PORT "IWM 09/30/2026 205.67 P", 497K
    buffer sentence]`
  - identity check `K_bot = Ref₀ × (1 − buffer_stated)` *(KOCT: 241.96 × 0.85 =
    205.666 → 205.67, exact to the cent)*
  - `maxloss_gross = (K_top − K_bot)/Ref₀ − 1` *(KOCT: −85%)* vs the grid's last row
  - the synthetic-long sanity `K_synth / Ref₀ ≈ 1%` *(KOCT: 2.42/241.96 = 1.0%)*
- **Success criteria:**
  - [ ] Recomputed gross cap and gross buffer match the stated figures within
        **0.05 pp at the stated rounding**; the buffer-bottom identity ties to the
        cent; max loss ties to the grid row.
  - [ ] The denominator is **Ref₀** throughout — not the current reference level, not
        the buffer-zone package value, not NAV — and Ref₀ is the C1-recovered value.
  - [ ] Each reconciliation row carries the **two-document evidence list** (the
        N-PORT leg title and the prospectus sentence): this is the eval's
        cross-document tie, the analog of eval #1's release-vs-10-Q reconciliation —
        and here the two documents share no figure at all.
  - [ ] A reconciliation **break** (recompute outside band) is *reported as a break*
        — the model does not silently average, force, or suppress it. (In gold cases
        the terms tie; a designed break case tests the reporting behavior.)
  - [ ] Stated figures come from E1's extraction (reuse, not re-extraction).
- **Grading:** `deterministic`.
- **Guards against:** *Recompute-vs-stated break unflagged* · *wrong denominator*
  (current level or NAV in place of Ref₀) · *strike/term cross-wiring* (cap computed
  off the buffer strike) · *single-document tie* (citing only one side of the
  reconciliation).

#### C4 — Net the terms of fees

- **Consumes:** Gross recomputed terms (C3); the unitary ER (E3); the stated net
  figures (E1); the basis map (P3); gold net values.
- **Produces:** `{cap_net = cap_gross − ER, buffer_net = buffer_gross − ER}` with
  operands-and-citations, reconciled against the **issuer's stated net figures**
  *(KOCT: 17.18 − 0.79 = 16.39 ✓; 15 − 0.79 = 14.21 ✓)*.
- **Success criteria:**
  - [ ] Net cap **and** net buffer are both computed — fees reduce the effective
        protection, not just the upside — and both tie to the issuer's stated net
        figures exactly (the **stated net is gold**; where an issuer's convention
        differs from simple subtraction, the issuer's figure governs and the
        difference is noted).
  - [ ] The gross→net direction is correct (net < gross, always) and no comparison
        downstream mixes a gross figure with a net one (the P3 scoped gate already
        zeros this checkpoint if the basis was committed wrong upstream).
  - [ ] The "100%-protection nets below 100%" logic is applied where the case is a
        100%-buffer fund: protection net of the ER is less than 100% — an investor
        can lose approximately the fee.
- **Grading:** `deterministic`.
- **Guards against:** *Fee-netting error* · *netting only the cap* · *phantom
  protection* ("can't lose money" on a 100%-buffer fund) · *gross/net mixing
  downstream*.

#### C5 — Tie out notionals, coverage, and the per-unit package value

- **Consumes:** The leg table with signed contracts and marks (E2); net assets and
  the cash sleeve (E2); the conventions record (P2); gold tie-out values.
- **Produces:** `{units = |contracts| × 100 (per leg), notional_synth = units ×
  Ref₀, coverage_ratio = notional_synth / net_assets, pctVal_sum_check,
  package_value_per_unit_at_repPdDate = Σ valUSD_signed / units}` — with
  operands-and-citations.
- **Success criteria:**
  - [ ] Units per leg = |contracts| × multiplier *(KOCT: 5,278 × 100 = 527,800)*;
        the synthetic-long notional ≈ units × Ref₀ *(KOCT: ≈ \$127.7M)* ≈ net assets
        at strike-set — the **N-PORT has no notional element for options; notional
        is derived**, and a model "extracting" one is fabricating.
  - [ ] The pctVal sanity sum holds *(KOCT: 101.24 + 4.15 − 1.57 − 4.05 + 0.29 ≈
        100.06%)* — and the deep-ITM call's > 100% weight is explained by the
        construction, not "corrected."
  - [ ] The per-unit package value at `repPdDate` is computed *(KOCT:
        \$132,651,974 / 527,800 = \$251.33)* and labeled **stale-state** (it is the
        month-end mark, used only as the C6 cross-check, never as NAV_t).
  - [ ] All operands trace to E2's cited figures (reuse, not re-extraction).
- **Grading:** `deterministic`.
- **Guards against:** *Multiplier/notional error* · *fabricated notional* ·
  *pctVal>100% misread* · *stale package value presented as current* · *per-share vs
  notional confusion*.

#### C6 — Compute the remaining outcome for a buyer entering at NAV_t today

- **Consumes:** The oracle snapshot `{snapshot_date, NAV_t, NAV_0, S_t}` (E4); the
  model's **own** stated/recomputed terms (E1/C3/C4) and ER (E3); strikes + Ref₀
  (C1); days_remaining (P3/E4); gold remaining-outcome values.
- **Produces:** The remaining-outcome block — fixed price levels first, then the
  buyer-relative terms:

  - price levels (fixed for the period): `cap_price = NAV_0 × (1 + cap_gross)`;
    `buffer_top_price = NAV_0`; `buffer_bottom_price = NAV_0 × (1 − buffer_gross)`
  - `remaining_cap_gross = cap_price / NAV_t − 1`
  - `downside_before_buffer = NAV_0 / NAV_t − 1` (≤ 0 when NAV_t > NAV_0 — the
    unbuffered gap a post-rally buyer bears first)
  - `remaining_buffer_depth = (NAV_t − buffer_bottom_price) / NAV_t`
  - `remaining_cap_net ≈ remaining_cap_gross − ER × days_remaining / 365` (ACT/365
    pinned)
  - reference-side buffer status: `intact` if `S_t ≥ Ref₀`; `partially consumed` if
    `K_bot < S_t < Ref₀` with consumed fraction `(Ref₀ − S_t)/(Ref₀ − K_bot)`;
    `below band` if `S_t < K_bot` (1:1 exposure from here at expiry; "breached" is
    an **at-expiry** verdict only)
  - leg-level cross-check: `remaining_cap_gross ≈ (K_cap − K_synth)/v_t − 1` with
    `v_t` the per-unit package value *(KOCT at the stale 2026-01-31 mark:
    281.11/251.33 − 1 ≈ **+11.85%**, vs the stated 17.18% — the running example's
    own demonstration that stated ≠ remaining)*. The leg form differs from the
    NAV-anchored form by the time-value + cash-sleeve residual (≈ 15 bps at period
    start) — a labeled cross-check, never the graded primary
- **Success criteria:**
  - [ ] Remaining gross cap, downside-before-buffer, and remaining buffer depth match
        gold within **0.1 pp**, and are **internally consistent with the model's own
        extracted cap/buffer and the oracle NAV** (graded separately from matching
        gold — the eval #1 `level_ref` mechanism).
  - [ ] The cap and buffer are treated as **fixed price levels pinned to day-1 NAV**
        — not as percentages re-applied to today's price. This is the issuer's own
        published convention, and the convention anchor is the issuer's own worked
        table *(Innovator's published Day-1/Day-20 example: NAV_0 \$25.00 with a
        stated 8.00% cap → cap price \$27.00, fixed for the period; a Day-20 buyer at
        \$25.17 has remaining cap 27.00/25.17 − 1 = **7.27%**, and
        downside-to-buffer-range 25.00/25.17 − 1 = **−0.68%**)* — the citable proof
        that remaining terms are price-level arithmetic, not re-based percentages.
  - [ ] `remaining_cap_net` is computed under the pinned ACT/365 proration (within
        0.15 pp) — and where it is **≈ 0 or negative** (a post-rally entry), the sign
        is correct: that single signed number is what S1's verdict hangs on.
  - [ ] Buffer status is assessed on the **reference level** (S_t vs Ref₀ and K_bot),
        not on the NAV path — a mid-period NAV dip into the buffer zone is time
        value, not a breached buffer.
  - [ ] The N-PORT-mark cross-check is labeled stale and never substituted for the
        NAV_t-based figures.
- **Grading:** `deterministic`. **IN-CHECKPOINT HARD-FAIL (`GATE.C6DIR`)** — a
  remaining-upside **sign flip** (positive reported where gold is negative, or vice
  versa) or a buffer-status label inversion zeroes the checkpoint.
- **Guards against:** *Stated-vs-remaining conflation* (the workflow's defining
  trap) · *percent-re-application error* (cap re-applied to today's price) ·
  *direction flip on remaining upside* · *consumed-buffer miss* · *NAV-path misread
  as breach* · *fee-proration slip*.

#### C7 — Verify the marketing-claim set

- **Consumes:** The marketing claim set (input); the reconciliation block (C3), net
  terms (C4), and remaining-outcome block (C6); the period-start-only rule (E1);
  gold verdicts per claim.
- **Produces:** A claim-verdict table — for each claim:
  `{claim_verbatim, verdict: ACCURATE | ACCURATE_AT_PERIOD_START_ONLY | WRONG_BASIS |
  FALSE | NOT_VERIFIABLE, deciding_figure (cited recompute), one_line_basis}`.
- **Success criteria:**
  - [ ] Each verdict matches gold exactly. The canonical patterns: *"15% downside
        buffer"* → `ACCURATE_AT_PERIOD_START_ONLY` (and gross-of-fee); *"upside to a
        cap of 17.18%"* quoted mid-period → `ACCURATE_AT_PERIOD_START_ONLY` (today's
        buyer faces the C6 remaining cap, not 17.18%); a net figure marketed against
        a gross recompute → `WRONG_BASIS`; *"defined outcome regardless of when you
        buy"* → `FALSE`.
  - [ ] Every verdict names its **deciding figure** from C3/C4/C6 — a verdict without
        a recomputed number behind it earns nothing (no vibes).
  - [ ] False claims are caught in **both directions** — overclaims (protection
        without scope) and false-comfort claims (a "no credit risk whatsoever" claim
        is also not `ACCURATE`; the honest residual is OCC/clearing-member tail risk).
  - [ ] `NOT_VERIFIABLE` is used where the claim needs data outside the packet —
        not stretched over claims the recomputes do decide.
- **Grading:** `deterministic` (verdict labels against gold; deciding-figure
  linkage checked as a structural field).
- **Guards against:** *Stated-vs-remaining conflation in marketing* · *gross/net
  mixing* · *false-claim acceptance* · *overcautious `NOT_VERIFIABLE` inflation* ·
  *unanchored verdicts*.

---

### Stage 4 — Synthesis

> The read. Multiple phrasings are valid, so these route to an LLM judge with
> correctness + contradiction operators against the deterministic numbers upstream —
> and the free-lunch predicate is checked deterministically against the deliverable's
> own cost block. The fact sheet is marketing; the prospectus and the N-PORT legs are
> the law.

#### S1 — The entry-timing verdict: what today's buyer actually gets

- **Consumes:** The remaining-outcome block (C6); the stated terms (E1) and the
  period-start-only rule; the claim verdicts (C7); gold verdict labels.
- **Produces:** Discrete calls for a buyer at NAV_t on the snapshot date —
  `{remaining_upside_net: positive | ~zero | negative, downside_before_buffer:
  none | [X]% gap, buffer_status: intact | partially_consumed | below_band,
  stated_terms_apply_to_this_buyer: no}` — each tied to its C6 figure, plus 2–3
  sentences of framing.
- **Success criteria:**
  - [ ] The verdict **never quotes the stated cap/buffer as what today's buyer
        gets** — the stated terms are cited only as the period-start reference case.
        Quoting "17.18%" to a mid-period buyer is the checkpoint's defining failure,
        and it is a *real, citable string* in a *current* filing, which is exactly
        why it is tested at the judge tier with a contradiction operator against C6.
  - [ ] The discrete labels match gold and are **consistent with the C6 magnitudes**
        (contradiction operator trips on conflict); the verdict is **contingent on a
        non-empty, non-gated C6 derivation** — restating gold labels in prose without
        the computation earns nothing (the eval #1 S1-on-C5 contingency).
  - [ ] Post-rally case: the unbuffered gap (`downside_before_buffer`) is named
        before any buffer talk; near-cap case: "little or no remaining upside, full
        remaining downside" is stated where C6 says so.
  - [ ] The hold-to-period-end condition is stated: the outcome formula applies at
        expiry; interim NAV participates < 1:1 in both directions.
- **Grading:** `judge` (with contradiction operators against C6/C7; contingent on C6).
- **Guards against:** *Stated terms quoted to today's buyer* · *internal
  contradiction with the computed remaining terms* · *unbuffered-gap omission* ·
  *near-cap upside overstatement*.

#### S2 — The cost of protection, and risk-claim truthfulness in both directions

- **Consumes:** The payoff reconstruction and grid (C2, E1 — the fund's own table
  prints +50% underlying → +17.18% fund next to −10% → 0%); the cap-setting
  mechanics verbatim (E1); the price-return and OCC language (E3); net terms (C4);
  gold cost-stack and risk-claim rubric.
- **Produces:** The **required cost-of-protection block** —
  `{capped_upside: {cap_value_cited, forgone_above_cap}, forgone_dividends:
  price_return_basis_cited, fee_drag: ER_cited, path_exit_risk: note}` — plus a
  risk-claim paragraph that gets the credit structure right.
- **Success criteria:**
  - [ ] **No free lunch.** The protection is priced: the buffer exists because the
        cap was sold to pay for it — the prospectus's own mechanics *(KOCT: "The Cap
        is the strike price of that sold call FLEX Option")* — and the cost stack
        names capped upside, forgone dividends (price-return exposure), the ER, and
        path/exit risk. An analysis reporting protection with no forgone-upside cost
        is wrong by construction and contradicts the fund's own payoff grid.
  - [ ] **The free-lunch predicate (deterministic):** the cost-of-protection block is
        present, non-empty, and its cap value is consistent with C3. Absent or empty
        while the memo presents downside protection → **`GATE.FREELUNCH` fires**:
        **S2 and S3 zero** (the suitability bottom line inherits the poisoned
        framing), `AllPass = 0`, `free_lunch_fired` reported as a headline flag.
        The judge additionally penalizes free-lunch prose ("protection at no cost",
        "keep the upside, lose the downside") via negative atoms.
  - [ ] **Risk claims are policed in both directions** (negative atoms): calling the
        fund an **issuer-credit** instrument like a structured note is a false claim
        — the FLEX options are OCC-cleared, per the E3 verbatim — and "**no
        counterparty risk at all**" is also false — the honest residuals are OCC
        tail risk, clearing-member/omnibus-margin risk, FLEX liquidity (model-priced
        Level-2 marks), and premium/discount.
  - [ ] The comparator discipline holds: any "versus just holding the underlying"
        framing accounts for the **dividend drag** (the fund's exposure is price
        return; the prospectus performance table shows both TR and PR index rows for
        exactly this reason) and the ER gap versus the underlying ETF's fee.
  - [ ] No invented risk and no invented benefit: every cost/risk claim traces to a
        cited disclosure or a computed figure.
- **Grading:** `judge` **+ deterministic free-lunch predicate** — **SCOPED GATE
  (`GATE.FREELUNCH`) → S2, S3**, the suite's one synthesis-stage-firing gate.
  Negative atoms for the false risk claims mirror eval #1's hallucinated-red-flag
  penalties.
- **Guards against:** ***Free-lunch claim*** (the eval's signature failure) · *false
  credit-risk claim* (issuer credit on an OCC-cleared product) · *false-comfort
  claim* (no counterparty risk at all) · *dividend/total-return comparator error* ·
  *missing cost item*.

#### S3 — Calibrated suitability bottom line

- **Consumes:** All prior checkpoint artifacts, including the E5 refusal/computation
  record and the E4 staleness ledger; the gold suitability rubric.
- **Produces:** A 4–8 sentence bottom line: for whom this fund at this entry point is
  and is not suitable, conditioned on the C6 remaining terms; the hold-to-period-end
  requirement; the remaining diligence items — tax/distribution profile (the funds
  distribute approximately nothing; creations/redemptions largely cash), AUM/
  liquidity, premium/discount, reset mechanics (gains above the old cap forfeited at
  reset; a new cap set by the same premium-neutral solve) — and an explicit list of
  what was **not** verifiable from the packet.
- **Success criteria:**
  - [ ] The bottom line is **consistent** with C6 and S1 — a near-zero or negative
        net remaining upside cannot coexist with an unqualified "attractive entry"
        (contradiction operator) — and with the S2 cost framing.
  - [ ] The suitability read is **entry-conditional**: it distinguishes the
        period-start buyer from today's buyer, and names the date the analysis is
        good for (terms static to period end; state as of the snapshot).
  - [ ] The diligence floor is present: hold-to-period-end behavior, tax/distribution
        character, AUM/liquidity/premium-discount, and reset consequences each get a
        grounded sentence or an explicit `not assessed — outside packet`.
  - [ ] **Explicitly names** what was not verifiable (carrying E5 forward — e.g.,
        the issuer's own daily remaining-cap figure was computed, not sourced) —
        calibrated uncertainty as a first-class positive criterion, with neither
        blanket hedging nor manufactured precision.
  - [ ] Introduces **no new figures** not extracted or computed upstream.
- **Grading:** `judge`. Inherits **`GATE.FREELUNCH`** — if the free-lunch predicate
  fired at S2, this checkpoint zeroes with it: a bottom line built on
  costless-protection framing is unusable however well it is written.
- **Guards against:** *Sycophancy / overconfident suitability call* · *over-refusal /
  uninformative hedging* · *missing diligence item* (tax, liquidity, reset) ·
  *internal contradiction* with the computed remaining terms · *new-figure
  introduction*.

---

## Failure taxonomy guarded

The named failure modes, mapped to the checkpoint(s) that catch each — the skeleton
of the Phase-5 taxonomy table, populated mechanically from graded traces via atom
tags. **Severity** uses the three-tier vocabulary from *How this maps to an eval*.

| Failure mode | What it looks like | Caught by | Severity |
|---|---|---|---|
| **Vintage / series confusion** | Analyzing the November fund's legs against the October fund's terms; wrong outcome-period **year**; sibling same-day N-PORT pulled | **P1** | **Hard gate** |
| **Outcome-period date error** | `repPdEnd` (trust FYE) read as the data date or period end; expiry assumed calendar month-end; days-remaining miscount | **P1**, **E4**, **P3** | P1 leg: **Hard gate** |
| **Strike-scale / reference-asset error** | IWM share-price strikes read as Russell 2000 index levels (~10×); SPX-fund strikes (~20×); the `varInfo` index name absorbed as the reference | **P2**, **E2** | **Hard gate** |
| **Multiplier / sign / notional error** | 100-share multiplier dropped; written legs treated as purchased; a notional "extracted" where none is filed | **P2**, **E2**, **C5** | P2 leg: **Hard gate** |
| **Leg-role misassignment** | The 2.42 deep-ITM call "corrected" or read as an error; cap computed off the buffer strike | **C1**, **C2**, **C3** | C1: **In-checkpoint fail** |
| **Buffer / floor / barrier inversion** | "Losses stop at −15%" (floor semantics on a buffer); max loss reported as the buffer; barrier knock-in missed | **C1**, **C2**, **S3** | C1: **In-checkpoint fail** |
| **Payoff arithmetic / regime error** | Buffer zone not flat; payoff rising above the cap; `K_synth` dropped from the reconstruction | **C2** | **In-checkpoint fail** |
| **Recompute-vs-stated break unflagged** | Strike-ratio recompute outside band silently averaged or suppressed | **C3** | — |
| **Gross-vs-net fee-basis mixing** | Net cap against a gross recompute; "100% protection" quoted net; buffer netting omitted | **P3**, **C4**, **C7** | P3: **Scoped gate** → C4, C7, S1, C6-net |
| **Stated-vs-remaining conflation** | The prospectus "17.18%" quoted to a mid-period buyer — a real string in a current filing, wrong by construction | **C6**, **C7**, **S1** | C6 direction: **In-checkpoint fail** |
| **Mid-period path misread** | NAV dip inside the buffer zone called a breached buffer; stale N-PORT marks presented as current; interim NAV projected 1:1 off the reference | **E4**, **C5**, **C6**, **S1** | — |
| **Hallucinated leg / strike / CUSIP** | A CUSIP for a FLEX leg (filed as N/A); a strike not in the N-PORT; a fabricated notional or remaining cap | **E2**, **E5**, **C5** (GATE.FABRICATION) | Per-figure void; cascades on frame fields |
| **Mis-citation** | Right strike, wrong leg title; percentages attributed to the N-PORT or strikes to the prospectus | **E1–E4** (entailment legs) | — |
| **Free-lunch claim** | Downside protection reported with no capped-upside / dividend / fee cost — contradicts the fund's own payoff grid and cap-setting mechanics | **S2** (`GATE.FREELUNCH`) | **Scoped gate** → S2, S3 + `AllPass = 0` + headline flag |
| **False risk claim (either direction)** | "Issuer credit risk" on an OCC-cleared FLEX product; or "no counterparty risk at all" | **S2** (negative atoms) | — |
| **Dividend / total-return comparator error** | Benchmarking the price-return structure against the total-return index; omitting dividend drag from a versus-underlying framing | **E3**, **S2** | — |
| **Sycophancy / failed calibrated refusal** | A confident remaining-cap number with no derivation; an issuer-website figure imported as if filed | **E5**, **S3** | E5 fabrication: hard failure |
| **Over-refusal** | Refusing the fee-table ER or a leg's contract count (disclosed, merely buried) | **E5** (answerable twin), **S3** | — |
| **Missing diligence item** | Tax/distribution character, AUM/liquidity, premium/discount, or reset consequences absent from the suitability read | **S3** | — |

---

## What Phase 2 / 3 / 4 will add

This decomposition is **the spec Phases 2–4 of eval #2 build on**, exactly as
eval #1's workflow doc was for its phases. **Phase 2 (`rubric/`)** turns each
checkpoint's success criteria into gated, weighted atoms on the *existing*
`criteria.yaml` schema — no schema changes required: the four FLEX legs become a
`per_leg_row` per-figure expansion with the verbatim N-PORT titles as entailment
cites; the gates named here (`GATE.VINTAGE`, `GATE.REFSCALE` → hard, the latter
with its explicit exclusion list — E1, E3, and E5's twin survive; `GATE.FEEBASIS` →
scoped with the C4/C7/S1/C6-net dependent list; `GATE.FREELUNCH` → scoped with the
S2/S3 dependent list; `GATE.C1ROLE`, `GATE.C2SIGN`, `GATE.C6DIR` → in-checkpoint;
`GATE.FABRICATION` reused) become deterministic predicates in the `gates:` block —
the free-lunch gate deliberately predicated on the structured cost-of-protection
block so it honors the "gates are deterministic predicates" contract; the tolerance
keys in the table above land in `tolerances:` (strike-exact, stated-rounding pp
bands, the 0.5-pp grid %-row band, the NAV-propagated 0.1 pp remaining-terms band
with its `level_ref`-style internal-consistency hook); and checkpoint weights for
the 18 checkpoints are set with the stage rebalance toward calculation. The E5
typed-answer extension (`{COMPUTED, value, derivation}`) is documented in
`rubric/judge.md` alongside the F-beta headline it inherits from E6 and the
`COMPUTED` G-score mapping (an in-band computed value with derivation earns full
correct-answer credit; a confident underived number maps to `G = 0`), with the
value atom keyed to C6's tolerance band.
**Phase 3 (`cases/`)** authors real EDGAR cases deliberately including every designed
trap: the KOCT running example as the anchor case with its **same-day sibling-vintage
N-PORTs as live distractors**; a **post-rally snapshot** where remaining upside net
of fees is ≈ 0 or negative; a **post-drawdown snapshot** with the buffer partially
consumed (and the remaining cap enlarged); an **Ultra/Deep Buffer** vintage (tests
the `Ref₀ = K_top / 0.95` recovery rule and the investor-takes-the-first-5% band); a
**100%-buffer fund** (protection nets below 100% by the ER); a **floor-vs-buffer
discrimination probe**; an **SPX-index-option contrast case** (OCC-as-issuer
reference encoding, ~20× strike scale); and a designed **reconciliation-break case**
for C3's reporting behavior. **Phase 4 (`harness/`)** wires it to run — and its
**precondition is the grader-dispatch refactor**: `harness/graders.py` currently
dispatches on hardcoded earnings atom ids (`P1.2` at line 160, `C1.sign` at 228,
`E6.n_fabricate` at 328, the E6 verdict overwrites at 382–389), and
`harness/scoring.py` hardcodes the gate→atom map (`pos_gate_atom`, lines 53–54);
eval #2's atom
families (leg extraction, payoff reconstruction, remaining-terms bands, structural
classification, claim verdicts) require **data-driven dispatch keyed off rubric atom
metadata** (grader type + tolerance key + gate hook), which the existing atom schema
already carries. Phase 4 also adds the `COMPUTED`-aware refusal grader and the
`free_lunch_fired` headline flag. Phase 5 then runs frontier models through both run
modes, grades them, populates the taxonomy table above from real traces, and
validates the judge with a judge-vs-expert macro-F1 on a hand-graded sample — the
artifact that proves the judge is trustworthy.
