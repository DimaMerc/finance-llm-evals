# Workflow — Equity Research / Asset Management → Discounted-Cash-Flow Valuation

> Phase 1 deliverable for **eval #3**, the suite's valuation eval. This document
> decomposes the work an analyst does to value a company by discounted cash flow —
> project unlevered free cash flow, discount it at the weighted-average cost of
> capital, add a terminal value, bridge enterprise value to equity, and divide by
> shares — into independently scorable checkpoints. It is the spec the eval-#3 rubric
> (`rubric/`), gold cases (`cases/`), and harness suite (`harness/suites/dcf.py`) are
> built against, exactly as `workflow/earnings-analysis.md` and
> `workflow/defined-outcome-analysis.md` are for evals #1 and #2.

A DCF is the most-used valuation model in equity research, asset management, IB, and
PE — and the one most often quietly wrong. Everything in the headline "fair value per
share" is a closed-form consequence of a handful of inputs and a chain of identities:
project free cash flow, discount at a rate, capitalize a terminal value, subtract net
debt, divide by shares. That makes the output perfectly recomputable — and it makes
the failure modes precise. The signature is **the DCF that looks right and is wrong**:
a clean, professional per-share number and fluent prose, built on one corrupting error
that flips the valuation and that a careless reviewer sails past — discounting
*unlevered* cash flow at the *cost of equity*; a terminal growth rate at or above the
discount rate; or dividing enterprise value by shares without subtracting net debt.
Those are not small mistakes. The first mis-prices by the entire debt load; the second
produces a meaningless or explosive terminal value; the third is the single most common
blunder in junior DCFs. The decomposition below is built so each is caught at the
checkpoint that owns it, and the discriminator the eval rewards is **internal
consistency and assumption discipline**, not arithmetic fluency.

### The pipeline at a glance

```
 PLANNING                 EXTRACTION                  CALCULATION                       SYNTHESIS
 ─────────                ──────────                  ───────────                       ─────────
 P1 frame + FCF basis ║g║ E1 base operating lines     C1 project unlevered FCF  ⟦fail⟧   S1 value-vs-price verdict
 P2 discount basis    ┊g┊ E2 EV↔equity bridge items   C2 compute WACC                    S2 where the value comes from ┊g┊
 P3 scope + TV method     E3 assumption-set intake     C3 discount explicit FCF           S3 calibrated bottom line
                          E4 snapshot + staleness      C4 terminal value         ⟦fail⟧
                          E5 calibrated-refusal probe  C5 enterprise value       ║g║
                                                       C6 EV → equity → per share ┊g┊
                                                       C7 sensitivity + sanity   ⟦fail⟧
   ║g║ = hard gate (P1 GATE.BASIS · the C5 consistency check · GATE.SCALE on units)
   ┊g┊ = scoped gate (P2 GATE.WACC → the discounting chain · C6 GATE.BRIDGE → the per-share chain · S2 GATE.FALSEPRECISION → S2+S3)
   ⟦fail⟧ = in-checkpoint hard-fail (C1 FCF-definition · C4 terminal g≥WACC · C7/S1 value-vs-price sign)
```

Three planning checkpoints pin the frame and — critically — the **consistency
contract** that the whole model must obey; five extraction checkpoints tie every base
figure to a `{document, locator, verbatim}` citation and intake the oracle assumption
set; seven calculation checkpoints redo the DCF as closed-form executable arithmetic;
three synthesis checkpoints route to an LLM judge for the valuation read. Seventeen
checkpoints, deliberately calculation-heavy (3 / 5 / 7 / 2-3 weighting toward the math),
each independently scorable and chainable into one end-to-end valuation.

---

## The task

What an analyst does to put a defensible fair-value-per-share on a company by DCF, given
that the answer is only as good as its internal consistency: pin the valuation frame and
the cash-flow basis, extract the base financials and the capital-structure bridge from the
filings, intake the assumption set, **project unlevered free cash flow and discount it at
WACC**, capitalize a terminal value, sum to enterprise value, **bridge to equity and
divide by shares**, stress the result, and write a calibrated read against the market
price that names what drives the value and what is merely assumed.

### Inputs

The eval hands the model (or agent) one company's filing packet, an oracle-supplied
assumption set, and a dated market snapshot:

| Input | What it is | Why it matters |
|---|---|---|
| **10-K** (and latest 10-Q if a stub is needed) | The historical income statement (revenue, operating income / EBIT, tax provision and effective rate), cash-flow statement (D&A, capex), balance-sheet working-capital lines, and the **capital-structure bridge**: total debt, cash & equivalents, minority interest, preferred, and the **diluted share count**. | This is the *factual* base — every line cited `{document, locator, verbatim}`. The bridge items and the share count are where the equity-value discipline lives (the EV→equity step and the per-share divide). Reported figures only; an assumption is never "extracted" from a filing. |
| **Assumption set** (oracle-supplied) | `{horizon_years, revenue_growth[], operating_margin[] (or EBIT path), cash_tax_rate, dep_amort[], capex[], delta_nwc[], wacc_components: {risk_free, beta, equity_risk_premium, pre_tax_cost_of_debt, target_debt_weight}, terminal: {method: gordon|exit_multiple, g | exit_ev_ebitda}, discounting_convention: year_end|mid_year}`. | A DCF is a *model*, not a reported number — its assumptions are not in any filing. They are hand-fed in **both** run modes, exactly like eval #1's consensus and eval #2's market snapshot. The gold is the deterministic math computed **on** these inputs; the assumptions themselves are oracle inputs, not graded facts. |
| **Market snapshot** (oracle-supplied) | `{valuation_date, share_price, diluted_shares_asof, net_debt_asof}` — the price the valuation is judged against and the as-of bridge figures. | Daily price is not in a filing; net debt/shares are filed but as-of-snapshot values may differ from the 10-K date — the staleness asymmetry (terms-vs-state) is itself a checkpoint concept (E4), carried from eval #2. |
| **Valuation-claim set** | 3–6 short claims in analyst-note register (e.g., *"our DCF implies ~25% upside"*, *"terminal value is a modest share of the valuation"*, *"the stock is cheap on cash flows"*), at least one true-only-on-a-specific-assumption, basis-confused, or false. | The real trigger is an analyst (or an AI) writing a valuation note. C7/claim verification grades these against the recompute — the DCF analog of eval #2's marketing-claim verdicts. |
| **Case manifest** (gold side, not shown to the model) | Ticker/CIK, fiscal year, the FCF basis, horizon, the full assumption set, the gold FCF projection, gold WACC, gold PVs/TV/EV, gold bridge and per-share, gold sensitivity grid, gold claim verdicts, and — for the designed case — the **planted-error key**. | Builds the planning gold, the gates, and the per-year / per-claim figure expansions. |

> **Running-example convention.** As in eval #2, one **real example** runs through the
> text because DCF is illegible without numbers — **McDonald's Corp. (MCD; CIK 63908;
> FY2025 10-K, accession 0000063908-26-000035, period ended 2025-12-31)**: a stable,
> heavily-franchised cash-flow business (DCF is genuinely the right method), with real
> leverage (so the EV→equity bridge is a vivid, graded step) and a simple capital
> structure. Real filed anchors used below — revenue **\$26.9B**, operating income
> **\$12.4B**, effective tax rate **21.4%**, diluted EPS **\$11.95**, diluted
> weighted-average shares **716.4M** (FY2025; basic 713.4M) — are marked *(MCD, filed)*.
> Figures *derived* from filed lines (e.g., net debt) are marked *(MCD, filed-derived)*. The
> forecast assumptions (growth, margins, the
> WACC components, terminal g) are the **oracle layer** and are marked *(illustrative)*;
> the fully-verified gold case, with every base line cited to the 10-K and the closed-form
> math on top, is authored in Phase 3 (`cases/`). MCD's negative book equity (from years
> of buybacks) is a feature, not a problem — it is exactly why a DCF must use **market**
> capital weights, not book, which P2's gate enforces.

### The analyst's real steps

1. **Pin the frame and the basis.** Confirm the company, the valuation date, the currency
   and units, and — the decision everything inherits — the **cash-flow basis**: an
   *unlevered* DCF projects free cash flow to the firm (FCFF), discounts it at WACC, and
   yields **enterprise value**, which is then bridged to equity. (A *levered* DCF projects
   FCFE, discounts at the cost of equity, and yields equity value directly.) These do not
   mix: FCFF discounted at the cost of equity, or an enterprise value handed to
   shareholders without the net-debt bridge, is wrong by construction.
2. **Extract.** Pull the base operating lines and the capital-structure bridge off the
   filings, each cited. Record what is *filed fact* (historicals, debt, shares) versus
   *oracle assumption* (the forecast, the discount rate) versus *stale state* (a 10-K-date
   balance vs the snapshot date). Mark anything genuinely **not in the filings** —
   starting with the discount rate itself.
3. **Calculate.** Project unlevered FCF year by year; compute WACC from its components on
   market weights and an after-tax cost of debt; discount the explicit cash flows;
   capitalize and discount a terminal value (with `g < WACC`, strictly); sum to enterprise
   value; **bridge to equity and divide by diluted shares**; then stress it — WACC and `g`
   sensitivity, the terminal-value share of the total, and the implied exit multiple.
4. **Synthesize.** State the fair value vs the market price as a discrete call; explain
   **where the value actually comes from** (how much is terminal, how much rides on the
   discount rate) with no false precision; and write a calibrated bottom line that names
   what is robust, what is assumption-driven, and what could not be verified.

### The deliverable

A short, citation-anchored **valuation memo** plus the structured checkpoint record:

1. **Pinned header** — ticker, valuation date, currency/units, FCF basis (unlevered),
   horizon, terminal method, discounting convention. (Also the gating record.)
2. **Base + bridge table** — the cited base operating lines and the cited bridge items
   (debt, cash, minority, preferred, diluted shares).
3. **Projection block** — unlevered FCF per year with the build (EBIT, tax, D&A, capex,
   ΔNWC), and the WACC build (Ke via CAPM, after-tax Kd, market weights).
4. **Valuation block** — PV of explicit FCF, terminal value and its PV, enterprise value,
   the EV→equity bridge, equity value, and **fair value per share**.
5. **Sensitivity block** — a WACC×g grid, the terminal-value share of EV, the implied exit
   multiple (or implied `g` if an exit multiple was used), and fair value vs market price.
6. **Synthesis** — the value-vs-price verdict, a **required value-attribution + sensitivity
   block** (the field the false-precision predicate checks), and a calibrated bottom line.

The same artifact grades checkpoint-by-checkpoint: all DCF math deterministically,
free-form synthesis by an LLM judge.

---

## How this maps to an eval

Same hard constraint as evals #1–2: **each checkpoint independently scorable, yet
chainable into one end-to-end valuation**. Eval #3 keeps eval #2's calculation-heavy
lens — the entire model is arithmetic on a handful of inputs, so the deterministic
surface is large and the judge is confined to the read. **No structural figure is
consumed downstream that an extraction checkpoint did not first produce and cite**; the
oracle assumption set is the one exception, injected and labeled as such.

**Run modes** (FinanceBench Oracle / end-to-end, unchanged):

- **Oracle / isolated probe** — inject the frame, the assumption set, and the cited base
  figures, and score *pure DCF reasoning*: can the model run the chain consistently once
  retrieval is removed?
- **End-to-end** — the agent must locate the 10-K, extract the base lines and the bridge
  itself, and assemble the model. The harness reports the oracle score beside the gated
  end-to-end score so a retrieval slip doesn't mask genuine valuation competence.

**Deterministic vs. judge.** Each checkpoint is tagged with the cheapest grader that can
score it correctly:

- **Deterministic** — all DCF math: the FCFF build, WACC, discount factors and PVs, the
  terminal value, enterprise value, the equity bridge, per share, the sensitivity grid,
  and value-vs-price. Gold = `{value, unit, tolerance}` with an evidence pointer; executed
  program-of-thought, FinQA/TAT-QA style.
- **Hybrid (value + entailment)** — extraction: the value checked deterministically *and*
  the citation entailment-checked (does the cited 10-K line actually support the figure?),
  scored separately so right-number/wrong-citation is distinguished from fabrication.
- **Label-deterministic + derivation-judge** — the E5 calibrated-refusal probe, carrying
  eval #2's `{COMPUTED, value, derivation}` / `{NOT_DISCLOSED, reason}` typed-answer
  contract: the probed figure (e.g., "what is the company's WACC?") is *computable from the
  given components but disclosed nowhere*, so a derived value with its build earns full
  credit, a grounded refusal naming the missing market inputs earns refusal credit, and a
  confident undisclosed number is a fabrication.
- **Judge** — free-form synthesis only (S1–S3), with correctness + contradiction operators
  against the deterministic numbers, **plus one deterministic predicate inside S2**: the
  false-precision gate (below).

**Gating — three tiers, plus the signature predicate.** Same model as evals #1–2:

- **Hard gate — `GATE.BASIS` (P1)**: the cash-flow/discount-rate/output **consistency**
  commitment is set up wrong — unlevered FCFF paired with the cost of equity, or the model
  declares it will hand an *enterprise* value straight to shareholders without a bridge.
  This is the DCF analog of eval #1's scale gate and eval #2's free-lunch: a foundational
  inconsistency that poisons the entire valuation. Zeros all dependents (E-stage figures
  survive as extraction; C1–C7 and S1–S3 zero).
- **Hard gate — `GATE.SCALE` (P2)**: a units / thousands-vs-millions error in the
  projections (reused from eval #1, with the same figure-magnitude detection). As in eval #1,
  this is an explicit **inclusion list** of the **scaled dollar atoms** —
  `dependents: [C1 FCFF, C3 PVs, C4 TV, C5.ev, C6 equity]` — *not* an exclusion list. The
  scale-invariant ratios (`C5.tvshare`, implied exit multiple, upside-vs-price %) are simply
  **absent** from the list and survive. The per-share value (`C6.value_per_share`) **is**
  in the list: it is a ratio of two scaled quantities and is scale-invariant only if EV and
  shares are *consistently* scaled — a one-sided slip (EV mis-scaled, shares right) must
  still be caught, so per-share cannot be treated as automatically invariant.
- **Scoped gate — `GATE.WACC` (P2)**: a discount-rate **basis** error — book capital
  weights instead of market, a *pre*-tax cost of debt in WACC, or a risk-free/ERP
  double-count. Dependents `[C3, C4, C5.ev]` — it zeros the WACC-derived value chain (C3
  discount factors, C4 TV, and the **`C5.ev`** sub-atom) but **spares `C5.consistency` and
  `C5.tvshare`** (those are basis/structure checks, not WACC-derived values, and feed the S2
  predicate), and leaves the FCF projection (C1) and the bridge inputs (E2) standing. The
  engine expresses this with the `:selector` sub-atom match (as eval #1's `GATE.P2` uses
  `E1.value:aggregate` and eval #2's `GATE.FEEBASIS` uses `C6.net`).
- **Scoped gate — `GATE.BRIDGE` (C6)**: the EV→equity bridge is wrong — net debt omitted or
  sign-flipped, minority/preferred ignored, or enterprise value divided by shares directly
  (the classic blunder). Zeros the per-share / equity chain (C6, S1) but not the unlevered
  enterprise math (C1–C5). This is the DCF's highest-frequency real-world error and gets
  its own gate, exactly as eval #2 gated the mid-period remaining-terms chain.
- **In-checkpoint hard-fails** — zero only their checkpoint: a **FCF-definition error** at
  C1 (discounting net income, not tax-affecting EBIT, or adding capex instead of
  subtracting); a **terminal `g ≥ WACC`** at C4 (a negative or explosive perpetuity — wrong
  by construction); and a **value-vs-price sign flip** at C7/S1 (calling an overvalued
  stock cheap).
- **Scoped gate — `GATE.FALSEPRECISION` (S2): the signature, designed deterministic.** A
  DCF's fair value is an assumption-driven estimate, usually dominated by a terminal value
  that swings hard with the discount rate. So the deliverable **requires** a structured
  value-attribution + sensitivity block (terminal-value share of EV, and a WACC×g range);
  the gate is the deterministic predicate: *the memo asserts a point fair value / target
  while that block is absent, empty, or its TV-share contradicts C5*. A point target sold
  as precise when 70%+ of the value is terminal and a 50bp WACC move shifts it 15%+ is the
  DCF version of selling a free lunch — false precision. Firing zeros **S2 and S3**, flags
  `false_precision_fired` as a headline flag, and `AllPass = 0`. This is the suite's second
  synthesis-stage-firing gate, deliberately parallel to eval #2's `GATE.FREELUNCH`. The
  judge separately penalizes false-precision prose ("the stock is worth exactly \$X") via
  negative atoms.
- **`GATE.FABRICATION`** — reused: a fabricated base figure, a "filed" number that is not in
  the 10-K, or a discount rate asserted as disclosed. Voids that figure's positive
  value+cite legs; cascades to the frame gates only when the fabricated field is the frame
  (basis, units, valuation date).

The harness reports **both** the gated/AllPass score and the un-gated partial-credit
score, with the GAP as a first-class number, in Oracle and end-to-end modes — unchanged.

**Tolerance bands** — per figure type, derived from each figure's own provenance:

| Figure type | Tolerance |
|---|---|
| Base operating lines & bridge items, as extracted (revenue, EBIT, D&A, capex, debt, cash, shares) | **exact at the filing's printed rounding** (scale-folded) |
| Unlevered FCF per projected year (`EBIT(1−t)+D&A−capex−ΔNWC`) | ≤ **0.5% relative** per year — pure arithmetic on the oracle assumptions |
| WACC (from CAPM + after-tax Kd + market weights) | ≤ **5 bps** vs the gold build |
| Discount factors / PV of each explicit FCF | ≤ **0.5% relative** per year (convention-folded: year-end vs mid-year pinned in P2) |
| Terminal value (Gordon) and its PV | ≤ **0.5% relative**, *and* internally consistent: `g < WACC` strictly, gold uses `FCFF_N(1+g)/(WACC−g)` |
| Enterprise value (`ΣPV(FCF)+PV(TV)`) | ≤ **0.5% relative**, and equals the model's own PV components (the `level_ref` internal-consistency hook) |
| Equity value and **fair value per share** (post-bridge) | ≤ **1.0% relative**, *and* internally consistent with the model's own EV, net debt, and share count |
| Sensitivity-grid cells / TV-share-of-EV / implied exit multiple | ≤ **0.5 pp** (TV share) / ≤ **0.5% rel** (grid cells) |
| Value-vs-price upside/downside and its sign | exact label — a sign flip is the C7/S1 in-checkpoint fail |

> **Why the per-share band (1.0%) is wider than the EV band (0.5%).** Equity per share
> compounds three inputs — EV, net debt, and the share count — each carrying its own
> rounding; their relative errors add in quadrature, so a 0.5% EV band plus cent-rounded
> net debt and a share count quoted to the million propagate to ≈ 0.8–1.0% at the per-share
> level. The band stays an order of magnitude below the *conceptual* errors it must catch:
> forgetting the ~\$39B net-debt bridge on MCD *(filed-derived: \$40.0B long-term debt −
> \$0.8B cash, FY2025)* mis-states equity by **15%+**, and dividing
> EV by shares directly is off by the entire net-debt-per-share — both far outside 1%, so
> the band passes honest rounding and fails every real bridge error.

---

## Checkpoints

Four stages, seventeen checkpoints. Each is tagged with a **stage**, a **grading type**,
and the named **failure-taxonomy bucket(s)** it owns.

### Summary table

| ID | Stage | Checkpoint | Grading | Gates downstream? | Primary failure modes guarded |
|---|---|---|---|---|---|
| **P1** | Planning | Pin frame + **FCF basis / output consistency** | deterministic | **Hard gate** | Levered/unlevered mix, EV-as-equity, wrong valuation date/units frame |
| **P2** | Planning | Lock discount-rate basis + conventions | deterministic | **Hard (scale) + scoped (WACC)** | Book-weight WACC, pre-tax Kd, unit/scale, convention unpinned |
| **P3** | Planning | Scope inputs + terminal-value method | hybrid | — | Terminal-method confusion, `g≥WACC` not pre-committed, nominal/real mix |
| **E1** | Extraction | Base operating lines from the 10-K | hybrid | — | Mis-extraction, mis-citation, EBIT-vs-net-income confusion |
| **E2** | Extraction | EV↔equity bridge items + diluted shares | hybrid | — | Net-debt miss, minority/preferred miss, wrong share count |
| **E3** | Extraction | Assumption-set intake (typed, oracle) | hybrid | — | Assumption mis-read, oracle-vs-filed confusion |
| **E4** | Extraction | Market snapshot + staleness ledger | hybrid | — | Stale-balance-as-current, valuation-date misread |
| **E5** | Extraction | Calibrated refusal: the WACC/forward probe (+ twin) | label-det. + derivation-judge | — | Fabricated discount rate, marketing import, over-refusal |
| **C1** | Calculation | Project unlevered FCF per year | deterministic | *(in-checkpoint fail)* | FCF-definition error (NI, no tax-affect, capex sign) |
| **C2** | Calculation | Compute WACC from components | deterministic | — | CAPM/weight/after-tax-Kd error |
| **C3** | Calculation | Discount explicit FCF to PV | deterministic | — | Discount-factor/convention error |
| **C4** | Calculation | Terminal value + its PV | deterministic | *(in-checkpoint fail)* | `g≥WACC`, TV not discounted, exit-multiple/Gordon mix |
| **C5** | Calculation | Enterprise value + consistency check | deterministic | **Hard gate (consistency)** | Summation error, levered/unlevered EV inconsistency |
| **C6** | Calculation | EV → equity → per share | deterministic | **Scoped gate** → C6, S1 | Net-debt sign/omission, EV-÷-shares, share-count error |
| **C7** | Calculation | Sensitivity + sanity cross-checks + claims | deterministic | *(in-checkpoint fail on sign)* | Missing sensitivity, implied-multiple break, value-vs-price flip |
| **S1** | Synthesis | Value-vs-price verdict (discrete) | judge | — | Quoting EV/share as equity value, contradiction with C6 |
| **S2** | Synthesis | Where the value comes from + risk read | judge + det. predicate | **Scoped gate** → S2, S3 (false precision) | **False precision**, TV-dominance unstated, missing sensitivity |
| **S3** | Synthesis | Calibrated bottom line | judge | — | Sycophancy/overconfidence, missing diligence item, new figure |

**Template** — each checkpoint below: **Consumes · Produces · Success criteria ·
Grading · Guards against.**

---

### Stage 1 — Planning

> Pin the frame and, above all, the **consistency contract**: unlevered cash flow ↔ WACC
> ↔ enterprise value ↔ bridge ↔ equity. Everything downstream inherits this; the gating
> failures live here.

#### P1 — Pin the frame and the FCF basis (the consistency commitment)

- **Consumes:** 10-K cover (entity, fiscal year, currency, units); the valuation-date
  input; the case manifest (ticker/CIK, FCF basis, horizon).
- **Produces:** A pinned header — `{ticker, cik, fiscal_year, valuation_date, currency,
  units, fcf_basis: unlevered_FCFF, output_chain: FCFF→WACC→EV→bridge→equity→per_share,
  horizon_years, terminal_method}` — each tied to its evidence or declared oracle.
- **Success criteria:**
  - [ ] The FCF **basis** is stated as **unlevered (FCFF)**, and the output chain is
        declared correctly: FCFF discounted at WACC yields **enterprise** value, which is
        bridged to equity, then divided by shares.
  - [ ] The valuation date, currency, and reporting units are pinned from the filing/inputs.
  - [ ] The horizon and terminal method are pinned (they drive C4).
  - [ ] The chain is **internally consistent**: no commitment to discount unlevered FCF at
        the cost of equity, and no commitment to treat enterprise value as equity value.
- **Grading:** `deterministic`. **HARD GATE — `GATE.BASIS`** — an unlevered/levered basis
  mismatch, or an enterprise-as-equity commitment, zeros all downstream checkpoints.
- **Guards against:** *Levered/unlevered mix* · *EV-as-equity* · *valuation-date/units
  frame error* · *mis-citation of the frame*.

#### P2 — Lock the discount-rate basis, units, and discounting convention

- **Consumes:** The WACC-component assumptions (E3 preview); the filing's units; the
  discounting-convention input; the manifest.
- **Produces:** A conventions record — `{wacc_basis: {weights: market, cost_of_debt:
  after_tax, capm: rf+beta*erp}, units, discounting_convention: year_end|mid_year,
  nominal_consistency: nominal_cashflows_nominal_wacc_nominal_g, lease_treatment:
  operating}`.
- **Success criteria:**
  - [ ] WACC is committed on **market** capital weights (not book — decisive for a
        negative-book-equity issuer like *(MCD)*), with an **after-tax** cost of debt and a
        CAPM cost of equity.
  - [ ] The **units** of the projections are locked (the thousands-vs-millions trap).
  - [ ] The **discounting convention** (year-end vs mid-year) is pinned before any PV is
        taken — the two differ by a half-period factor and must not be mixed.
  - [ ] Nominal consistency is declared: nominal cash flows discounted at a nominal WACC
        with a nominal `g` (no real/nominal mix).
  - [ ] **Lease treatment is pinned to `operating`** — rent stays embedded in EBIT (MCD's
        reported \$12.4B operating income is already after occupancy/rent expense) and the
        ~\$14.8B of operating-lease liabilities is **excluded** from the net-debt bridge. The
        gold computes on this one convention; the debt-like capitalization (add rent back to
        EBIT *and* add lease liabilities to net debt) is the equally-valid alternative the
        model must **not** half-apply — capitalizing leases on one side only is the trap.
- **Grading:** `deterministic`. **HARD GATE — `GATE.SCALE`** (units, figure-magnitude
  detection, eval-#1 mechanics) **and SCOPED GATE — `GATE.WACC`** (book-weight / pre-tax-Kd
  / CAPM double-count) → dependents `[C3, C4, C5.ev]` (the WACC-derived value chain), with
  `C5.consistency` / `C5.tvshare`, E1/E2/C1 and the bridge inputs **surviving**.
- **Guards against:** *Book-weight WACC* · *pre-tax cost of debt* · *unit/scale error* ·
  *convention unpinned* · *real/nominal mix*.

#### P3 — Scope the inputs and the terminal-value method

- **Consumes:** The assumption set (E3); the manifest gold; the terminal-method input.
- **Produces:** `{terminal_method: gordon|exit_multiple, terminal_param: g|exit_ev_ebitda,
  consistency_rules: [g<WACC, g<=long_run_GDP, terminal_FCF_normalized], input_map (which
  inputs are oracle vs filed)}`.
- **Success criteria:**
  - [ ] The terminal method is pinned and its parameter recorded; if Gordon, the rule
        **`g < WACC` (strict)** and `g ≤` a long-run nominal-GDP ceiling is pre-committed.
  - [ ] The terminal-year FCF is flagged as needing to be **normalized** (steady-state
        capex ≈ D&A, mid-cycle margin) rather than an unrepresentative final explicit year.
  - [ ] Each input is tagged **oracle (assumption)** vs **filed (fact)** — the discount rate
        and the forecast are oracle; the historicals and the bridge are filed.
- **Grading:** `hybrid` (deterministic method/param checks + a judged completeness check).
- **Guards against:** *Terminal-method confusion* · *`g≥WACC` not pre-committed* ·
  *un-normalized terminal year* · *oracle/filed confusion*.

---

### Stage 2 — Extraction

> The filing supplies the *facts*; the assumption set supplies the *forecast*. Extraction
> is hybrid — value deterministically, citation by entailment — so right-number/wrong-cite
> is caught separately from fabrication. A discount rate or a growth rate "extracted" from
> the 10-K is a fabrication: those live nowhere in it.

#### E1 — Extract the base operating lines

- **Consumes:** The 10-K income statement (revenue, operating income / EBIT, tax provision,
  effective rate) and cash-flow statement (D&A, capex); gold values + verbatim strings.
- **Produces:** `{revenue, ebit, tax_provision, effective_tax_rate, dep_amort, capex}` —
  each `{value, document, locator, verbatim}` *(MCD, filed: revenue 26.9B, operating income
  12.4B, effective tax 21.4%)*.
- **Success criteria:**
  - [ ] **EBIT (operating income)** is extracted — not net income, not EBITDA — at the
        filing's printed rounding, cited.
  - [ ] The **effective tax rate** (or the provision and pre-tax income to derive it) is
        captured for **reconciliation/context** — note that the unlevered FCFF in C1 is
        tax-affected at the oracle **`cash_tax_rate`** (a marginal/operating rate on EBIT),
        **not** the reported effective rate, which reflects non-operating items and the
        interest shield (for MCD the two are close, ~21–22%, but the rate applied to EBIT is
        the oracle input, not E1's reported 21.4%).
  - [ ] D&A and capex are taken from the **cash-flow statement** (the reliable source), not
        inferred.
  - [ ] No assumption (growth, discount rate) is attributed to the filing.
- **Grading:** `hybrid` (value deterministic + citation entailment).
- **Guards against:** *EBIT-vs-net-income / vs-EBITDA confusion* · *mis-citation* ·
  *assumption attributed to the filing* · *hallucinated line*.

#### E2 — Extract the EV↔equity bridge items and diluted shares

- **Consumes:** The 10-K balance sheet (total debt — current + long-term, cash &
  equivalents, minority/noncontrolling interest, preferred) and the share data (diluted
  weighted-average or period-end shares); gold values + verbatim.
- **Produces:** `{total_debt, cash_and_equivalents, net_debt, minority_interest, preferred,
  non_op_assets (e.g. investments in/advances to affiliates), diluted_shares}` — each cited.
- **Success criteria:**
  - [ ] **Total debt** (current + long-term) and **cash** are captured and **net debt**
        formed correctly (`total_debt − cash`).
  - [ ] **Minority interest and preferred** are captured (or explicitly noted as zero/none)
        — they are part of the bridge from EV to common equity.
  - [ ] **Non-operating assets are captured as a bridge add-back** — for MCD, *investments in
        and advances to affiliates* (equity-method associates, ~\$2.8B): their earnings are
        **not** in consolidated EBIT, so an unlevered DCF on operating FCFF does not value
        them; they are **added** in C6 (≈\$3.9/share — material at the 1.0% per-share band).
  - [ ] **Operating-lease liabilities are NOT counted as debt** under the pinned `operating`
        treatment (P2): the ~\$14.8B of lease liability is excluded from net debt because the
        rent already sits in EBIT — pulling it into the bridge while leaving rent in EBIT
        double-counts and is the lease trap E2 guards.
  - [ ] The **diluted share count** is captured (the per-share denominator) at the filing's
        figure — the diluted **weighted-average** shares (FY2025: 716.4M) unless the manifest
        pins period-end — the share-count discipline carried from eval #1.
  - [ ] Negative book equity *(MCD)* is **not** treated as a data error — it is the buyback
        history and is irrelevant to a DCF (which uses market weights and cash flows).
- **Grading:** `hybrid`.
- **Guards against:** *Net-debt miss/sign* · *minority/preferred miss* · *wrong share count*
  · *book-equity panic* · *mis-citation*.

#### E3 — Intake the assumption set (typed, oracle)

- **Consumes:** The oracle assumption set; the manifest gold.
- **Produces:** The typed assumption record `{horizon, revenue_growth[], margin[]/ebit[],
  cash_tax_rate, dep_amort[], capex[], delta_nwc[], wacc_components, terminal, convention}`
  — every field tagged **oracle**.
- **Success criteria:**
  - [ ] Every assumption is read exactly as supplied and **typed/labeled oracle** — none
        re-derived, none silently changed, none attributed to a filing.
  - [ ] The WACC components are complete (`rf, beta, erp, pre_tax_kd, target_weights`) and
        the terminal parameter present.
- **Grading:** `hybrid`.
- **Guards against:** *Assumption mis-read* · *silent assumption change* · *oracle/filed
  confusion*.

#### E4 — Market snapshot intake + staleness ledger

- **Consumes:** The oracle snapshot `{valuation_date, share_price, diluted_shares_asof,
  net_debt_asof}`; the 10-K filing date and balance-sheet date; the pinned frame.
- **Produces:** A provenance ledger — `{snapshot: {date, price, shares, net_debt, source:
  oracle}, filed: {balance_date, net_debt, shares, staleness_days}}` — every figure labeled
  `current | filed-fact | stale-state`.
- **Success criteria:**
  - [ ] The snapshot fields are read exactly and dated; `valuation_date` is the as-of for
        the price comparison and the bridge.
  - [ ] The **staleness asymmetry** is explicit: the 10-K balance is as of its fiscal-year
        end and may differ from the valuation date; the snapshot net debt/shares are the
        as-of figures the bridge should use when supplied.
  - [ ] No filed balance is presented as the current market value, and the price is never
        taken from the filing.
- **Grading:** `hybrid`.
- **Guards against:** *Stale-balance-as-current* · *valuation-date misread* · *price from
  the filing*.

#### E5 — Calibrated refusal: the discount-rate probe (+ answerable twin)

- **Consumes:** The probe — *"What is the company's WACC?"* posed against the **filings
  alone** (it is genuinely absent: a WACC is constructed from market inputs — beta, ERP,
  the risk-free rate — that no 10-K discloses); the paired **answerable twin** — two
  disclosed-but-buried figures: total debt and the diluted share count; gold labels,
  derivation, twin values.
- **Produces:** For the probe, a typed answer — `{COMPUTED, value, derivation}` (deriving
  WACC from the *supplied* components and naming them) **or** `{NOT_DISCLOSED, reason}`
  (the filing discloses no discount rate; the components are market data, not filed). For
  the twin, `{value, citation}` each.
- **Success criteria:**
  - [ ] The probe is **never answered with a bare number from the filing**: full credit for
        a correct `COMPUTED` WACC (within C2's band) **with** its CAPM/weights derivation;
        full refusal credit for `NOT_DISCLOSED` naming that a WACC is built from market
        inputs absent from the 10-K; a confident "the filing's WACC is X%" is a **hard
        failure** (no filing states one) — `GATE.FABRICATION` hook.
  - [ ] On the **twin**, total debt and the diluted share count are retrieved and cited;
        refusing them (over-refusal) is penalized.
  - [ ] A vague hedge without the missing-input reasoning does not earn refusal credit.
  - [ ] **Run-mode-dependent credit** (a finer line than eval #2, whose probed NAV is absent
        from *any* source): `NOT_DISCLOSED` earns full refusal credit only when the WACC
        components are **not** in context (the probe is about *filing*-sourcing). When the E3
        components **are** injected (Oracle / end-to-end with E3), the model *can* compute,
        so a bare `NOT_DISCLOSED` that ignores the supplied components maps **below** the
        eval #2 `G = 0.75` refusal tier; full credit then requires `COMPUTED` with its build.
        Phase-2 `judge.md` states this G-mapping per run mode.
- **Grading:** `label-deterministic + derivation-judge`. **Headline = FailSafeQA F-beta
  (β = 0.5)**, the eval-#1/#2 exception, with the `{COMPUTED, value, derivation}` extension;
  the computed value is keyed to **C2's WACC band**.
- **Guards against:** *Fabricated discount rate* · *market-data import as filed* ·
  *over-refusal on the disclosed twin* · *vague hedging*.

---

### Stage 3 — Calculation

> The DCF math. All of it is closed-form from the base lines, the assumption set, the
> bridge, and one price — graded deterministically as executed program-of-thought.
> Notation: `FCFF_t = EBIT_t(1−τ) + DA_t − Capex_t − ΔNWC_t`; `WACC = (E/V)·Ke +
> (D/V)·Kd·(1−τ)` with `Ke = rf + β·ERP`; `TV_N = FCFF_N(1+g)/(WACC−g)`,
> `g < WACC`; `EV = Σ_t PV(FCFF_t) + PV(TV_N)`; `Equity = EV − NetDebt − Minority −
> Preferred`; `Value/share = Equity / DilutedShares`.

#### C1 — Project the unlevered free cash flow

- **Consumes:** E1 base lines; E3 assumptions (growth, margin, tax, D&A, capex, ΔNWC);
  the horizon; gold per-year FCFF.
- **Produces:** `FCFF_t` for each explicit year with the build shown
  `{revenue_t, ebit_t, ebit_after_tax_t, da_t, capex_t, dnwc_t, fcff_t}`.
- **Success criteria:**
  - [ ] FCFF is built as **`EBIT(1−τ) + D&A − Capex − ΔNWC`** — operating income
        tax-affected at **`τ = cash_tax_rate`** (the oracle marginal/operating rate, not the
        reported effective rate), D&A added back, capex and the **increase** in net working
        capital subtracted.
  - [ ] Each year matches gold within **0.5% relative**; the build (not just the answer) is
        present per year.
  - [ ] Net income is **not** used as the cash-flow base; EBIT is **not** left un-tax-
        affected; capex is **subtracted**, not added; a working-capital **increase** is a
        use of cash.
- **Grading:** `deterministic` (per-year expansion). **IN-CHECKPOINT HARD-FAIL
  (`GATE.C1FCF`)** on a FCF-definition error (net income as base, EBIT not tax-affected,
  capex sign flip).
- **Guards against:** *FCF-definition error* · *tax-affecting omission* · *capex/ΔNWC sign*
  · *D&A double-count*.

#### C2 — Compute WACC from its components

- **Consumes:** E3 WACC components (`rf, beta, erp, pre_tax_kd, target_weights`); the tax
  rate (E1); the P2 basis lock; gold WACC.
- **Produces:** `{ke = rf + beta*erp, kd_after = pre_tax_kd*(1−τ), wacc = (E/V)*ke +
  (D/V)*kd_after}` with operands shown.
- **Success criteria:**
  - [ ] Cost of equity via **CAPM** (`rf + β·ERP`); cost of debt **after-tax**
        (`Kd·(1−τ)`); WACC on the **target market weights** — within **5 bps** of gold.
  - [ ] Market weights, not book; the after-tax (not pre-tax) cost of debt; no
        risk-free/ERP double-count.
- **Grading:** `deterministic`.
- **Guards against:** *CAPM error* · *book weights* · *pre-tax Kd* · *weight error*.

#### C3 — Discount the explicit free cash flows

- **Consumes:** C1 FCFF; C2 WACC; the P2 convention; gold PVs.
- **Produces:** `{discount_factor_t, pv_fcff_t}` per year, on the pinned convention
  (`t` year-end, or `t−0.5` mid-year).
- **Success criteria:**
  - [ ] Discount factors use the **committed convention** consistently; each `PV(FCFF_t)`
        within **0.5% relative** of gold.
  - [ ] No mixing of year-end and mid-year; the rate is the C2 WACC throughout.
- **Grading:** `deterministic`, plus a **PENALTY atom (`C3.n_convention`)** — *year-end and
  mid-year discount conventions mixed within the projection* — so a systematic
  convention-mix is a **named negative atom**, not only an implicit per-PV banded miss
  (parallel to eval #2's `C2.n_convention`, −4).
- **Guards against:** *Discount-factor error* · *convention mix* · *wrong rate*.

#### C4 — Terminal value and its present value

- **Consumes:** C1 terminal-year FCFF; C2 WACC; P3 terminal method/param; gold TV.
- **Produces:** `{tv_undiscounted = FCFF_N(1+g)/(WACC−g) [Gordon] or EBITDA_N*exit_mult,
  pv_tv, implied_exit_multiple or implied_g}`.
- **Success criteria:**
  - [ ] Gordon TV computed as `FCFF_N(1+g)/(WACC−g)` with **`g < WACC` strictly**;
        discounted to PV on the same convention; within **0.5% relative** of gold.
  - [ ] If an exit multiple is used, the **implied `g`** is back-solved and sanity-checked;
        if Gordon, the **implied exit multiple** is reported as the cross-check.
  - [ ] The terminal-year FCFF is normalized (P3), not an anomalous final explicit year.
- **Grading:** `deterministic`. **IN-CHECKPOINT HARD-FAIL (`GATE.C4TERM`)** on `g ≥ WACC`
  (negative/explosive TV) or a TV left undiscounted.
- **Guards against:** *`g≥WACC`* · *TV not discounted* · *Gordon/exit-multiple mix* ·
  *un-normalized terminal FCF*.

#### C5 — Enterprise value + the consistency check (the spine)

- **Consumes:** C3 PVs; C4 PV(TV); the P1 basis commitment; gold EV.
- **Produces:** `{ev = sum(pv_fcff_t) + pv_tv, tv_share_of_ev = pv_tv/ev}`, plus the
  explicit assertion that **this EV is an unlevered (enterprise) value**.
- **Success criteria:**
  - [ ] `EV = Σ PV(FCFF_t) + PV(TV)` within **0.5% relative**, and equal to the model's own
        PV components (internal consistency).
  - [ ] The value is correctly labeled **enterprise** (unlevered), consistent with the P1
        chain — it is not yet equity, and it was built from FCFF discounted at WACC (not
        FCFE, not at Ke).
  - [ ] `TV-share-of-EV` is reported (it feeds the S2 false-precision predicate).
- **Grading:** `deterministic`. **HARD GATE — `GATE.BASIS` consistency check** — if the
  assembled EV is internally inconsistent with the declared basis (levered cash flows or
  Ke produced this "EV", or an equity-like value is labeled EV), the basis gate fires here
  as well as at P1. One `GATE.BASIS` with `fired_by: [P1.consistency, C5.consistency]` (a
  multi-hook list, as eval #2's `GATE.FABRICATION` already uses) and one shared
  `dependents: [C1,C2,C3,C4,C5,C6,C7,S1,S2,S3]`, so both firing sites have the same
  blast radius. The C5 firing atom is itself **inside** that radius **by design**:
  self-gating is harmless and correct — a basis that is wrong at C5 should zero C5 too.
  `C5.consistency` is a basis check, so it **survives** `GATE.WACC` (only `C5.ev` is
  WACC-derived).
- **Guards against:** *Summation error* · *levered/unlevered EV inconsistency* ·
  *TV-share unreported*.

#### C6 — Bridge enterprise value to equity, and to per share

- **Consumes:** C5 EV; E2 bridge items (net debt, minority, preferred); E2/E4 diluted
  shares; gold equity + per share.
- **Produces:** `{equity = ev − net_debt − minority − preferred (+ non_op_assets),
  value_per_share = equity / diluted_shares}` with operands and citations.
- **Success criteria:**
  - [ ] Equity = EV **minus net debt** (and minority and preferred), within **1.0%
        relative** of gold and internally consistent with the model's own EV and bridge.
  - [ ] Per share = equity / **diluted shares** — **never** EV / shares (the classic
        blunder, off by net-debt-per-share).
  - [ ] Net debt carries the **correct sign** (subtracted); a net-**cash** company adds it
        back; **non-operating assets** (MCD's ~\$2.8B equity-method investments) are **added**.
        *(MCD, filed-derived: a ~\$39B net-debt subtraction moves equity ~15%+ — the bridge
        is material, not a rounding step.)*
- **Grading:** `deterministic`. **SCOPED GATE — `GATE.BRIDGE`** — net-debt omission/sign
  flip, minority/preferred omission, or EV-÷-shares zeros **C6 and S1** (the per-share/
  equity chain) but not the unlevered enterprise math C1–C5. **S2/S3 are deliberately
  spared**: they grade EV-side value-attribution and calibration, not the per-share number
  (which S1 owns and `GATE.BRIDGE` zeros) — mirroring how eval #2's `GATE.FEEBASIS` zeros S1
  but leaves S2/S3 standing.
- **Guards against:** *Net-debt omission/sign* · *EV-÷-shares* · *minority/preferred miss*
  · *share-count error*.

#### C7 — Sensitivity, sanity cross-checks, and claim verification

- **Consumes:** C2 WACC; C4 terminal param; C5 EV / TV-share; C6 per share; E4 price; the
  valuation-claim set; gold grid + verdicts.
- **Produces:** `{wacc_g_grid[[per_share]], tv_share_of_ev, implied_exit_multiple (or
  implied_g), upside_vs_price = value_per_share/price − 1, claim_verdicts[]}`.
- **Success criteria:**
  - [ ] A **WACC×g sensitivity grid** of per-share values is produced (each cell within
        **0.5% relative**); the **TV-share-of-EV** and the **implied exit multiple / implied
        `g`** cross-check are reported.
  - [ ] **Upside/downside vs the market price** is computed and its **sign** is correct (a
        value below price is downside; calling it upside is the in-checkpoint fail).
  - [ ] Each valuation claim is labeled `ACCURATE | ACCURATE_ON_BASE_CASE_ONLY |
        WRONG_BASIS | FALSE | NOT_VERIFIABLE` against the recompute, with the deciding
        figure named (no vibes). The deciding-figure requirement carries eval #2's **v1.0.1
        `deciding_kind` fix**: a verdict decided by **scope** (`NOT_VERIFIABLE`) or by
        **basis-confusion** (`WRONG_BASIS`) names that boundary/basis fact as its deciding
        evidence (`deciding_kind: disclosure|scope|recompute`) rather than a recompute — so a
        correctly-`NOT_VERIFIABLE` claim is not falsely penalized for "naming no figure," the
        same false-penalty eval #2's Phase-3 pass caught.
- **Grading:** `deterministic` (grid + verdicts; verdict-deciding-figure structural).
  **IN-CHECKPOINT HARD-FAIL (`GATE.C7SIGN`)** on a value-vs-price **sign flip**.
- **Guards against:** *Missing sensitivity* · *implied-multiple break* · *value-vs-price
  sign flip* · *claim-verdict errors*.

---

### Stage 4 — Synthesis

> The read. Multiple phrasings are valid → LLM judge with correctness + contradiction
> operators against the deterministic numbers, plus the false-precision predicate checked
> deterministically against the deliverable's own sensitivity block.

#### S1 — The value-vs-price verdict

- **Consumes:** C6 per share; E4 price; C7 upside/sign; gold verdict labels.
- **Produces:** Discrete calls — `{fair_value_per_share, vs_price: undervalued | ~fairly_
  valued | overvalued, upside_pct, basis: equity_value_per_share (not EV/share)}` plus 2–3
  sentences of framing.
- **Success criteria:**
  - [ ] The verdict uses the **equity** value per share (post-bridge), never EV/share, and
        its direction matches C7's sign (contradiction operator trips on conflict).
  - [ ] The discrete label matches gold and is **contingent on a non-empty, non-gated C6
        derivation** — restating a number with no computation behind it earns nothing.
  - [ ] The hold-to-thesis condition is stated: the value is a point on an assumption set,
        realized only if those assumptions hold.
- **Grading:** `judge` (contradiction operators vs C6/C7; contingent on C6).
- **Guards against:** *EV/share quoted as equity value* · *contradiction with the computed
  value* · *direction error*.

#### S2 — Where the value comes from + the risk read (false-precision gate)

- **Consumes:** C5 TV-share; C7 sensitivity grid; C2 WACC; gold value-attribution + risk
  rubric.
- **Produces:** The **required value-attribution + sensitivity block** —
  `{terminal_value_share_of_ev, wacc_sensitivity: per_share_range_over_+-50bps,
  g_sensitivity, key_value_driver}` — plus a risk paragraph (cyclicality, the assumption
  the value hinges on, the model's limits).
- **Success criteria:**
  - [ ] **No false precision.** The memo states how much of the value is **terminal**
        *(MCD-style stable franchisor: typically 70%+)* and how the per-share value moves
        with a ±50 bps WACC change and a ±50 bps `g` change — the fair value is a **range
        anchored on an assumption set**, not a single decimal-precise truth.
  - [ ] **The false-precision predicate (deterministic):** the value-attribution +
        sensitivity block is present, non-empty, and its TV-share is consistent with C5.
        Absent or empty **while the memo asserts a point fair value / price target** →
        **`GATE.FALSEPRECISION` fires**: **S2 and S3 zero**, `AllPass = 0`,
        `false_precision_fired` reported as a headline flag. The TV-share-contradiction
        clause is evaluated **only when `C5.tvshare` is available** (non-gated); when C5 was
        zeroed upstream (`GATE.BASIS`/`GATE.WACC`), the predicate falls back to the
        presence/non-empty clause — mirroring how eval #2's free-lunch predicate degrades
        when its C3 reference is unavailable. The judge separately penalizes false-precision
        prose ("worth exactly \$X") via negative atoms.
  - [ ] The key value driver is named and traces to the inputs; no invented driver.
- **Grading:** `judge` **+ deterministic false-precision predicate** — **SCOPED GATE
  (`GATE.FALSEPRECISION`) → S2, S3**, the suite's second synthesis-stage-firing gate
  (parallel to eval #2's free-lunch).
- **Guards against:** ***False precision*** (the signature failure) · *TV-dominance
  unstated* · *missing sensitivity* · *invented value driver*.

#### S3 — Calibrated bottom line

- **Consumes:** All prior artifacts, incl. the E5 refusal/derivation record; the gold
  suitability rubric.
- **Produces:** A 4–8 sentence bottom line: the buy/hold/sell-style read **conditioned on
  the assumptions**, what is robust vs assumption-driven, the remaining diligence (the
  cyclicality of the cash flows, the leverage, the reinvestment/normalization assumption,
  the comparison to trading multiples), and an explicit list of what was **not** verifiable
  (carrying E5 — e.g., the discount rate was constructed, not disclosed).
- **Success criteria:**
  - [ ] **Consistent** with C6/C7/S1/S2 — a value far below price cannot coexist with an
        unqualified "buy" (contradiction operator).
  - [ ] **Assumption-conditional**: distinguishes what the cash flows support from what the
        terminal/discount-rate assumptions impose; names the assumption the call hinges on.
  - [ ] The diligence floor is present (cyclicality, leverage, normalization, multiple
        cross-check) — each a grounded sentence or an explicit `not assessed — outside
        packet`.
  - [ ] **Explicitly names** what was not verifiable (the constructed discount rate; any
        oracle assumption) — calibrated uncertainty as a first-class positive.
  - [ ] Introduces **no new figure** not extracted or computed upstream.
- **Grading:** `judge`. Inherits **`GATE.FALSEPRECISION`** — if it fired at S2, S3 zeros
  with it.
- **Guards against:** *Sycophancy / overconfident target* · *over-refusal* · *missing
  diligence item* · *contradiction* · *new-figure introduction*.

---

## Failure taxonomy guarded

| Failure mode | What it looks like | Caught by | Severity |
|---|---|---|---|
| **Levered/unlevered basis mix** | FCFF discounted at the cost of equity; "EV" built from FCFE | **P1**, **C5** | **Hard gate** |
| **Enterprise-as-equity** | Dividing EV by shares; handing an enterprise value to shareholders | **P1**, **C6** | P1: **Hard gate**; C6: **Scoped gate** |
| **Unit / scale error** | Projections in thousands read as millions (or vice versa) | **P2** | **Hard gate** |
| **WACC-basis error** | Book capital weights; pre-tax cost of debt; CAPM double-count | **P2**, **C2** | P2: **Scoped gate** → discounting chain |
| **Net-debt bridge error** | Net debt omitted, sign-flipped, or minority/preferred ignored | **C6**, **E2** | C6: **Scoped gate** → C6, S1 |
| **FCF-definition error** | Net income as the base; EBIT not tax-affected; capex added | **C1** | **In-checkpoint fail** |
| **Terminal-value error** | `g ≥ WACC`; TV left undiscounted; un-normalized terminal FCF | **C4**, **P3** | C4: **In-checkpoint fail** |
| **Discounting-convention error** | Year-end and mid-year mixed; wrong discount rate | **C3**, **P2** | **Penalty atom** (`C3.n_convention`) |
| **Value-vs-price sign flip** | An overvalued stock called cheap; downside reported as upside | **C7**, **S1** | C7: **In-checkpoint fail** |
| **False precision** | A single decimal-precise target with no sensitivity, value 70%+ terminal | **S2** (`GATE.FALSEPRECISION`) | **Scoped gate** → S2, S3 + `AllPass=0` + headline flag |
| **Fabricated figure / discount rate** | A "filed" base line that is not in the 10-K; a WACC asserted as disclosed | **E1–E5** (GATE.FABRICATION) | Per-figure void; cascades on frame fields |
| **Stale-balance-as-current** | A 10-K-date balance presented as the current bridge | **E4** | — |
| **Sycophancy / failed refusal** | A confident "the filing's WACC is X%"; an imported discount rate | **E5**, **S3** | E5 fabrication: hard failure |
| **Over-refusal** | Refusing total debt or the share count (disclosed, merely buried) | **E5** (answerable twin) | — |
| **Mis-citation** | Right number, wrong line; an assumption attributed to the 10-K | **E1–E4** (entailment legs) | — |
| **Missing diligence item** | Cyclicality, leverage, normalization, or the multiple cross-check absent | **S3** | — |

---

## What Phase 2 / 3 / 4 will add

This decomposition is **the spec eval #3's later phases build on**, exactly as evals #1–2.
**Phase 2 (`rubric/criteria-dcf.yaml`)** turns each checkpoint's success criteria into
gated, weighted atoms on the *existing* `criteria.yaml` schema — no schema change: the
projection years become a `per_year_row` per-figure expansion and the WACC×g grid a
`per_grid_cell` expansion (two **new literal keys** Phase 4 adds to the `_EXPANSIONS` table
in `harness/rubric.py` — the data-driven expander, not the scoring/gating engine), while the
claims reuse the **already-present** `per_claim_row` key as-is (parallel to eval #2's
`per_leg_row`/`per_grid_row`/`per_claim_row`); the gates named here (`GATE.BASIS`, `GATE.SCALE` → hard; `GATE.WACC`,
`GATE.BRIDGE`, `GATE.FALSEPRECISION` → scoped with their dependent lists;
`GATE.C1FCF`, `GATE.C4TERM`, `GATE.C7SIGN` → in-checkpoint; `GATE.FABRICATION` reused)
become deterministic predicates in the `gates:` block — `GATE.FALSEPRECISION` predicated on
the structured sensitivity block so it honors the "gates are deterministic predicates"
contract; the tolerance keys in the table above land in `tolerances:` (exact-rounding,
0.5%-rel per-year/PV/EV, 5-bp WACC, 1.0%-rel per-share with the `level_ref` internal-
consistency hook); and the 17 checkpoint weights are set calculation-heavy. The E5
typed-answer extension and the `false_precision_fired` headline flag are documented in
`rubric/judge.md`. **Phase 3 (`cases/`)** authors the MCD gold case — every base line and
bridge item cited to the FY2025 10-K, the assumption set as the labeled oracle layer, and
the closed-form DCF math as gold — plus the **signature "subtly-wrong DCF" case**: a
complete, professional-looking valuation with one planted corrupting error (the basis mix,
a `g ≥ WACC`, or the missing net-debt bridge) that the eval must catch and localize — the
literal screening exercise. The three variants are deliberately **not equivalent in blast
radius**: the basis mix (hard `GATE.BASIS`) and `g ≥ WACC` (in-checkpoint `GATE.C4TERM`) are
*catastrophic and obvious* — they zero large swaths and the surface goes visibly red; the
**missing net-debt bridge** fires only the **scoped `GATE.BRIDGE`** (C6, S1), leaving C1–C5
fully scored and green, so the eval must localize a small red on an otherwise-clean valuation.
That bridge variant — the highest-frequency real error and the hardest to catch — is the
**headline signature case**; the other two are the catastrophic-but-obvious contrast. **Phase 4 (`harness/suites/dcf.py`)** adds the suite module
(handlers for the projection / WACC / discounting / TV / EV / bridge / sensitivity /
claims, the `GATE.FALSEPRECISION` predicate, the per-year/grid/claim expansions) on the
already-suite-agnostic engine. The **scoring/gating engine needs no surgery** (exactly as
eval #2 proved out); the only shared-code change is two literal keys appended to the
`_EXPANSIONS` table in `harness/rubric.py` (`per_year_row`, `per_grid_cell`) plus the
matching `expand_counts` manifest keys — additive, byte-invariant for evals #1–2. **Phase 5**
runs frontier and local models through both run modes, grades them, and extends the
failure taxonomy and `PAPER.md` with the valuation findings.
