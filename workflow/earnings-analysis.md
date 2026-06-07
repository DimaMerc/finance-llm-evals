# Workflow — Asset Management → Quarterly Earnings Analysis

> Phase 1 deliverable. This document decomposes the first-hours earnings-analysis
> workflow into independently scorable checkpoints, the way a buy-side/sell-side
> analyst actually runs it. It is the spec the rubric (`rubric/`), the gold cases
> (`cases/`), and the harness (`harness/`) are built against.

When a company prints, an analyst doesn't read the filing front to back. In the
first one-to-three hours after the release crosses the wire, the job is narrow
and mechanical at the edges and judgmental in the middle: pin the print, reconcile
the press release to the GAAP statements, do the desk math the way the desk does it,
benchmark against consensus and guidance, and write a calibrated bottom line that a
PM can act on. I ran the change-management side of an ETF servicing platform at
Brown Brothers Harriman — creation/redemption, derivatives processing, the lifecycle
plumbing where a thousands-vs-millions slip or a wrong fiscal-period label is not a
rounding error but a break that has to be reconciled before anything downstream
clears. That instinct is what this eval encodes: **the workflow is evaluated as a
chain of checkpoints because that is where a real analyst's errors actually happen**,
and localizing the failure to a specific step is worth more than a single blended
accuracy number. A model that nails the arithmetic but reads an "in thousands"
statement as dollars has not made a small mistake; it has made the one mistake that
makes everything downstream unusable. The decomposition below is designed so that
failure is caught at the checkpoint that owns it.

### The pipeline at a glance

```
 PLANNING            EXTRACTION                 CALCULATION                SYNTHESIS
 ─────────           ──────────                 ───────────                ─────────
 P1 period   ║gate║  E1 income stmt             C1 growth + Δshares        S1 beat/miss + guidance
 P2 scale    ║gate║  E2 segments + shares       C2 margins(bps) + FCF      S2 material changes + QoE
 P3 scope    ┊gate┊  E3 non-GAAP + OCF/capex    C3 GAAP→non-GAAP EPS       S3 calibrated bottom line
                     E4 guidance                C4 QoE ratios (tax/DSO)
                     E5 balance-sheet WC        C5 beat/miss + seg tie-out
                     E6 not-disclosed probe
   ║gate║ = hard gate (zeros all dependents)   ┊gate┊ = scoped gate (zeros the beat/miss chain only)
```

Three planning checkpoints set the frame, six extraction checkpoints tie every
figure to a `{document, page, verbatim string}` citation, five calculation
checkpoints redo the desk math as executable program-of-thought, and three
synthesis checkpoints route to an LLM judge for the free-form read. Seventeen
checkpoints, each independently scorable and each chainable into one end-to-end run.

---

## The task

### Inputs

The eval hands the model (or the agent) a single issuer's quarterly print packet for
one fiscal period:

| Input | What it is | Why it matters |
|---|---|---|
| **Earnings press release** (8-K, Exhibit 99.1) | Issued first. Source of the headline number, management-chosen **non-GAAP / "adjusted"** metrics, the GAAP-to-non-GAAP **reconciliation tables**, segment summary tables, and forward **guidance**. | This is where the beat/miss headline and the adjusted figures live. It is also where companies frame the quarter favorably — so it is where GAAP/non-GAAP confusion starts. |
| **10-Q** (or **10-K** when the print is fiscal Q4) | The authoritative GAAP legal document, filed same-day or days/weeks later. Full condensed income statement, balance sheet, **statement of cash flows** (frequently absent/abbreviated in the release), the **ASC 280 segment footnote**, the **weighted-average share reconciliation**, and MD&A. | The release is marketing; the 10-Q is the law. Cash flow, FCF inputs, working-capital lines, and segment detail come from here. A correct answer must cite *which* document and *where*. |
| **Consensus snapshot** | Street estimates for the period as-of the print date, with **one central-tendency statistic designated as the gold basis** (mean *or* median — pinned, not "either"), the **basis** of the EPS consensus (GAAP vs street/adjusted), estimate **dispersion** (high/low range or std dev) where available, the **provider** (e.g., LSEG/Refinitiv, FactSet, Visible Alpha), and the **snapshot date**. Next-period guidance consensus where available. | Beat/miss is only meaningful like-for-like. Most published EPS consensus is **non-GAAP**; comparing GAAP EPS to a street number manufactures a false beat or miss. The basis is itself sometimes ambiguous — providers blend GAAP and adjusted contributor estimates — so the eval *freezes* a documented snapshot precisely to make beat/miss deterministically gradeable despite that real-world messiness. |
| **Prior-period comparatives** | Year-ago same quarter (for YoY) and immediately-prior sequential quarter (for QoQ), plus any **restatement / segment-redefinition** flags. Includes the year-ago weighted-average diluted share count (for the buyback-denominator check) and the prior-period working-capital lines (for DSO/DIO trend). | Period-over-period math is only valid on a like-for-like base. Growing off an originally-reported number that was later restated is a silent, common error. |
| **Case manifest** (gold side, not shown to the model) | Ticker/issuer/CIK, exact fiscal-period label (e.g., *"Q3 FY24, period ending [date]"*), filing type, reporting currency, statement unit/scale, **issuer sector** (so the headline-figure set is sector-aware — see P3). | Used to build the planning-stage gold answers and the gating checks. |

> **Illustrative-placeholder convention.** This document invents **no** company
> numbers. Where a concrete value would normally appear, the placeholder is marked
> explicitly — e.g. *"Q3 FY24, period ending [date]"*, *"revenue = \[gold value\],
> in millions"*, *"adjusted EPS = \$\[X.XX\]"*. Real figures, tied to real SEC
> filings, are authored only in `cases/` (Phase 3).

### The analyst's real steps

1. **Plan / pin the print.** Confirm issuer, the *exact* fiscal period (fiscal vs.
   calendar quarter — Apple's FY starts in October; many retailers end fiscal years
   in late January), and filing type (Q4 is reported *inside* the 10-K, not a
   standalone 10-Q). Read the statement headers to lock reporting currency and
   unit/scale ("in thousands, except per share"). Decide which consensus basis
   (GAAP vs adjusted) and which statistic (mean/median) the comparison will use.
   Scope the ~12–18 figures that matter — *which* figures depends on the sector
   (an asset manager has no gross-profit line; a bank runs net interest income).
2. **Extract.** Pull each scoped figure straight off the relevant statement/table,
   recording for each a `{value, unit/scale, document, page, verbatim evidence
   string}`. Keep press-release-sourced figures (headline, non-GAAP, reconciliation,
   guidance) separate from 10-Q-sourced figures (GAAP statements, cash flow, segment
   footnote, share reconciliation, balance-sheet working capital). Mark anything
   genuinely **not disclosed**.
3. **Calculate.** YoY and QoQ growth as *separately labeled* outputs on the correct
   base; the YoY change in diluted share count; margins (where the P&L has them) and
   their deltas in **basis points**; **FCF = operating cash flow − capex**; the
   **GAAP-to-non-GAAP EPS bridge** add-back by add-back; quality-of-earnings ratios
   (effective tax rate, DSO/DIO, OCF-to-net-income); **segment sum-to-total** tie-out;
   **beat/miss** vs consensus on the matching basis, absolute and as a percent.
4. **Synthesize.** State beat/miss and guidance-vs-street as discrete *above / in-line
   / below* calls; identify the 2–4 material changes and their swing factors; run
   quality-of-earnings diagnostics (OCF vs net income, one-time / discrete-tax items
   inflating the headline, buyback-driven EPS, DSO/DIO/deferred-revenue trends, segment
   redefinition, restatement); write a **calibrated bottom line** that explicitly states
   what is *not* disclosed or *not* reconcilable rather than guessing.

### The deliverable

A short, citation-anchored **earnings memo** plus the structured checkpoint record
behind it:

1. **Pinned header** — issuer, exact fiscal period, filing type, currency, scale,
   consensus basis/statistic, sector. (This is also the gating record.)
2. **Extraction table** — each key figure with value, unit/scale, and a
   `{document, page, verbatim string}` citation; `not disclosed` marked where it
   applies.
3. **Calculation block** — each derived figure with its formula, operands (each tied
   to its citation), and final value: growth, share-count change, margins in bps, FCF,
   the EPS bridge, QoE ratios, segment tie-out, beat/miss magnitude.
4. **Synthesis** — discrete beat/miss and guidance-vs-street direction calls, 2–4
   ranked material-change flags, earnings-quality red flags, and a calibrated bottom
   line that names every figure it could *not* verify.

The same artifact grades checkpoint-by-checkpoint: numbers deterministically,
free-form synthesis by an LLM judge.

---

## How this maps to an eval

The decomposition is built to satisfy a single hard constraint: **each checkpoint
must be independently scorable, yet the checkpoints must chain into one end-to-end
analyst run.** That dual requirement is what lets the eval run as both a HealthBench-style
isolated-probe battery *and* a Vals AI–style end-to-end agentic task.

**The checkpoint model.** Every checkpoint declares its inputs, the intermediate
artifact it must produce, explicit success criteria, a grading type, and the named
failure modes it guards against. Because each is atomic, a wrong margin can be
localized to *either* a misread operand (an extraction failure) *or* a math error (a
calculation failure) — the per-checkpoint independence is borrowed directly from
**HealthBench** (each criterion is one atomic, independently-graded statement) and
**Vals AI Finance Agent Benchmark** (the gold answer is decomposed into discrete
key points graded per-point, not holistically). A guarantee the structure enforces:
**no synthesis or calculation checkpoint consumes a figure that an extraction
checkpoint did not first produce and cite** — every number is traced to a source.

**Run modes — isolated probe vs. end-to-end.** Every checkpoint is runnable two ways,
borrowing **FinanceBench**'s *Closed-Book / Oracle* framing:

- **Oracle / isolated probe** — inject the correct frame (period, scale, basis) and
  the gold evidence page, then score *pure reasoning*. This measures whether the
  model can do the math/read once retrieval is removed.
- **End-to-end** — the agent must find the filing, pin the period, and extract the
  figures itself. This measures the realistic retrieval-plus-reasoning task.

The harness reports the **oracle score next to the gated end-to-end score** so that
an upstream planning slip (which cascades and zeroes dependents) doesn't mask genuine
downstream competence. This is the single most important defense against the
"one planning miss tanks the whole run" artifact of a chained eval.

> **Consensus is oracle-supplied in *both* run modes.** Street estimates are not
> retrievable from the filings, so the consensus snapshot is hand-fed even in
> end-to-end mode. The "realistic task" claim therefore applies to *filing retrieval
> and extraction*, not to consensus sourcing. (An optional probe can ask the model to
> pick the correct same-basis consensus out of a small distractor set, but that is a
> separate test, not part of the core chain.)

**Deterministic vs. judge grading.** Each checkpoint is tagged with the *cheapest
grader that can score it correctly*:

- **Deterministic** — numeric extraction and all arithmetic. Gold = `{value, unit,
  tolerance}` with an evidence pointer; graded by a Python checker. This mirrors
  **FinQA / TAT-QA**, which *execute* a program-of-thought derivation rather than
  asking a judge, and fold **scale** into the number before comparison so a
  thousands-vs-millions error deterministically zeroes the answer.
- **Hybrid (value + entailment)** — extraction checkpoints that pair a deterministic
  value check with a **FinanceBench-style entailment sub-check**: does the cited
  verbatim string actually contain/support the number? A model can get the value right
  and cite wrong (or vice versa); these are scored separately so the failure taxonomy
  distinguishes *right-number/wrong-citation* from *hallucination*.
- **Label-deterministic + reason-judge** — the calibrated-refusal probe (E6). The
  `NOT_DISCLOSED` *label* and the answerable-twin *retrieval* are checked
  deterministically; the *reason* the item is not disclosed is judged (entailment
  against a gold reason, or LLM judge). A refusal probe has no numeric value to check
  on the undisclosed leg, so it cannot use the plain hybrid composition — it gets its
  own grader type.
- **Judge** — genuinely free-form synthesis (material changes, the bottom line).
  Graded against an expert rubric with **correctness operators** ("is this specific
  claim present and right?") and **contradiction operators** ("does the response
  conflict with the gold read or the computed numbers?"), per HealthBench and Vals AI.
  The contradiction signal is the clean hook for penalizing confident-but-wrong narrative.

**Evidence-citation requirement.** Every extraction and calculation checkpoint names
the evidence it points to as a `{document, page, verbatim string}` triple — exactly
**FinanceBench**'s `evidence_text` + `evidence_page_num` discipline, extended to a
*list* of evidence objects for reconciliation checkpoints that legitimately cite two
or more spans across two documents (e.g., tying release-stated adjusted EPS to the
10-Q income statement). Gold answers are verifiable; no figure is trusted on the
model's say-so.

**Calibrated-refusal credit.** "Not disclosed / not reconcilable from the provided
documents" is a **first-class correct answer**, not a cop-out — borrowed from
**FailSafeQA**. 10-Qs legitimately omit items (segment-level operating margin when
only segment *revenue* is broken out; FCF when the cash-flow statement hasn't dropped;
withdrawn guidance). A confident fabricated figure on a genuinely-absent item is a
hard failure; an *over-refusal* on a figure that is in fact disclosed (buried in a
footnote) is *also* a failure. The eval rewards calibration in **both** directions
by pairing each "not disclosed" probe with an **answerable twin**, in the spirit of
FailSafeQA's asymmetric F-beta weighting (a confident wrong number is worse than a
cautious correct refusal).

**Gating — three tiers, and why gating is a deliberate deviation.** HealthBench has no
explicit gate; finance needs one, because some errors make everything downstream
unusable regardless of the arithmetic. The harness distinguishes three failure
severities:

- **Hard gate** — *zeros all dependent downstream checkpoints*. Two conditions: a
  **wrong fiscal period or wrong source document** (P1) and a **unit/scale error** (P2).
  A Q3 number reported as Q2, or an off-by-1,000× scale slip, poisons every figure
  that flows from it.
- **Scoped gate** — *zeros a named subset of downstream checkpoints, not the whole
  chain*. One condition: a **consensus-basis mismatch** fixed at P3 (e.g., committing
  to compare GAAP EPS against a street/non-GAAP consensus). It zeros the beat/miss
  chain (**C5, S1**) — the checkpoints that inherit the basis — but leaves the
  extraction and the GAAP-internal math (C1–C4) standing.
- **In-checkpoint hard-fail** — *zeros only that checkpoint, no downstream gating*.
  A **wrong-sign / directional error** (a +5% growth reported as −5%, a beat called a
  miss) forces the checkpoint to zero regardless of any step-level partial credit,
  because a flipped sign inverts the conclusion. It does not gate dependents.

The harness reports **both** a gated/All-Pass score (every gating condition must hold)
and an un-gated **partial-credit** score. Reporting the *gap* between them is itself
the point: it quantifies how much "almost right" inflates a naive average. (The Vals
AI Finance Agent Benchmark popularized reporting an All-Pass metric alongside
partial credit for exactly this reason; here the gap is a first-class reported number,
not a published constant.)

**Tolerance bands** are an explicit design choice (FinQA/TAT-QA use exact-after-rounding
with no epsilon, which is brittle to legitimate press-release-vs-10-Q rounding). Per
figure type, set in the rubric, with a stated rounding convention:

| Figure type | Tolerance |
|---|---|
| EPS (reported or computed) | ± \$0.01 |
| Growth rates & margin **levels** | ≤ 0.1 percentage point |
| Margin **deltas** (YoY/QoQ) | ≤ 15 bps **and** internally consistent with the model's own two margin levels |
| As-reported aggregate line items | exact to reported precision, or ≤ 0.5% relative |
| Free cash flow (derived) | ≤ 0.5% relative on the computed difference |
| Beat/miss magnitude | EPS ± \$0.01; revenue ≤ 0.5% relative |
| Beat/miss **direction** | "in-line" when inside consensus **dispersion** (or, if dispersion is unavailable, inside rounding noise) — no beat/miss claimed inside the noise |

> **Why the margin-delta band is 15 bps, not 5.** A margin delta is the difference of
> two margin *levels*, each allowed ± 0.1pp (10 bps). Two in-tolerance levels can
> legitimately produce a delta off by up to ~14 bps (root-sum-square of the two level
> bands). A 5-bps delta band would therefore *fail* a model whose margins each pass
> their own check — the delta tolerance must be ≥ the propagated tolerance of its
> inputs. The convention: compute each margin to full precision, round to 0.1pp for the
> level check, then grade the delta against gold at ≤ 15 bps *and* require it to equal
> the model's own (current − prior) margins. Derived figures (FCF, beat/miss) get
> relative bands because press-release and 10-Q rounding legitimately differ.

---

## Checkpoints

Four stages, seventeen checkpoints. Each is tagged with a **stage**, a **grading type**,
and the named **failure-taxonomy bucket(s)** it owns so the Phase-5 taxonomy table is
generated mechanically from graded traces.

### Summary table

| ID | Stage | Checkpoint | Grading | Gates downstream? | Primary failure modes guarded |
|---|---|---|---|---|---|
| **P1** | Planning | Identify filing, issuer, exact fiscal period | deterministic | **Hard gate** | Wrong period, wrong source |
| **P2** | Planning | Lock currency & unit/scale (incl. cross-document) | deterministic | **Hard gate** | Unit/scale error |
| **P3** | Planning | Scope figures (sector-aware) & fix consensus basis | hybrid | **Scoped gate** → C5, S1 | GAAP/non-GAAP mismatch, missing item |
| **E1** | Extraction | Headline income statement (incl. pre-tax income & tax provision) | hybrid | — | Hallucination, mis-citation, GAAP confusion |
| **E2** | Extraction | Segment revenue & share counts (basic / GAAP-diluted / non-GAAP-diluted / prior-yr) | hybrid | — | Share-count traps, segment miss, mis-citation |
| **E3** | Extraction | Non-GAAP add-backs (incl. tax-effect line), OCF, capex | hybrid | — | GAAP/non-GAAP confusion, wrong-document |
| **E4** | Extraction | Forward guidance (ranges, basis, withdrawal) | hybrid | — | Missing material item, mis-citation |
| **E5** | Extraction | Balance-sheet working capital (AR, inventory, deferred rev) | hybrid | — | Hallucination, mis-citation, missing item |
| **E6** | Extraction | Calibrated refusal: not-disclosed probe (+ answerable twin) | label-det. + reason-judge | — | Sycophancy, over-refusal, hallucination |
| **C1** | Calculation | YoY & QoQ growth + YoY diluted-share-count change | deterministic | — | Base error, wrong-sign, false precision |
| **C2** | Calculation | Margins & deltas in bps (sector-aware) + FCF | deterministic | — | Arithmetic, false precision, FCF definition |
| **C3** | Calculation | GAAP→non-GAAP EPS bridge (step-checked) | deterministic | — | GAAP/non-GAAP, tax-effect, diluted-share basis |
| **C4** | Calculation | Quality-of-earnings ratios: effective tax rate, DSO/DIO, OCF/NI | deterministic | — | Mis-attribution, arithmetic, missing red flag |
| **C5** | Calculation | Beat/miss vs consensus & segment sum-to-total tie-out | deterministic | — | Basis mismatch, wrong-sign, segment break |
| **S1** | Synthesis | Beat/miss & guidance-vs-street direction calls | judge | — | Directional error, missing item, contradiction |
| **S2** | Synthesis | 2–4 material changes & earnings-quality red flags | judge | — | Missing material item, hallucinated red flag |
| **S3** | Synthesis | Calibrated bottom line with explicit uncertainty | judge | — | Sycophancy, false precision, contradiction |

**Template** — every checkpoint below uses the same shape: **Consumes** (inputs) ·
**Produces** (intermediate artifact) · **Success criteria** (checklist) · **Grading** ·
**Guards against** (failure modes).

---

### Stage 1 — Planning

> Pin the print and set the frame. Everything downstream inherits these decisions, so
> the gating failures live here.

#### P1 — Identify the correct filing, issuer, and exact fiscal period

- **Consumes:** Press-release header and 10-Q/10-K cover page; statement column headers
  showing the period(s) covered; case manifest gold (ticker/issuer/CIK, exact
  fiscal-period label, filing type).
- **Produces:** A pinned header object —
  `{issuer, ticker/CIK, fiscal_period_label (e.g. "Q3 FY24, period ending [date]"),
  period_end_date, filing_type (10-Q | 10-K-for-Q4)}` — each field tied to the
  cover-page / statement-header evidence string and page.
- **Success criteria:**
  - [ ] Issuer and ticker match gold exactly (string / CIK match).
  - [ ] Fiscal-period label and period-end date match gold, including the fiscal-vs-calendar
        distinction (a fiscal Q3 ending in a given month is not "Q3 calendar" unless the
        filing says so); the year-ago / prior-quarter comparative column is **not** mistaken
        for the current period.
  - [ ] Filing type is correct — recognizes that fiscal Q4 is reported *inside* the 10-K,
        not as a standalone 10-Q.
  - [ ] 13-week vs 14-week / 52- vs 53-week periods are noted where applicable.
  - [ ] The period claim is **anchored** to the cover-page / statement-header string, not asserted.
- **Grading:** `deterministic`. **HARD GATE** — a wrong fiscal period or wrong source document
  zeroes all downstream extraction/calculation checkpoints for the case.
- **Guards against:** *Wrong fiscal period* (fiscal-vs-calendar confusion; pulling the
  year-ago/prior-quarter column; reporting Q4 as a standalone 10-Q; un-noted 13/14-week
  periods) · *mis-citation* of the period header.

#### P2 — Lock reporting currency and statement unit/scale

- **Consumes:** Income-statement / balance-sheet / cash-flow-statement header lines
  (e.g. "in thousands, except per share data"); the press-release statement and
  reconciliation table headers; any currency designation; case manifest gold (unit/scale
  per statement, reporting currency).
- **Produces:** A scale map — `{statement → declared_scale (thousands | millions |
  as-reported), reporting_currency, base_unit_conversion_factor}` — each tied to the
  verbatim header string and page; plus a note where a document leg (typically the
  release) carries **no declared scale header**.
- **Success criteria:**
  - [ ] Declared scale per statement matches gold, read from the verbatim header string
        (a "\$1,234,567 in thousands" figure is understood as ≈ \$1.23B, not \$1.23M).
  - [ ] Reporting currency matches gold.
  - [ ] Per-share figures are treated as **already in dollars** and are *not* multiplied
        by the aggregate scale factor ("in thousands, **except per share**").
  - [ ] **Cross-document scale is reconciled**: when the press release states absolute
        dollars (or commas with no header) while the 10-Q states "in thousands/millions,"
        the two are reconciled to the same base unit before any figure is tied across them.
        Where a leg has no declared header, scale is inferred from magnitude and **flagged**,
        not assumed.
  - [ ] Each scale/currency assertion cites the statement-header string and page.
- **Grading:** `deterministic`. **HARD GATE** — a unit/scale error (off by 1,000×) zeroes
  every dependent numeric extraction/calculation checkpoint.
- **Guards against:** *Unit/scale error* (reading "in thousands" as dollars or millions) ·
  *cross-document scale mismatch* (release absolute vs 10-Q thousands) · *mixing a per-share
  figure with a thousands-scaled aggregate* · *currency mismatch* · *mis-citation* of the scale header.

#### P3 — Scope the figures that matter (sector-aware) and fix the consensus basis

- **Consumes:** The print packet; consensus snapshot (provider, basis GAAP vs
  street/adjusted, designated statistic, dispersion, as-of date); the metric management
  leads with; the issuer sector (manifest); the deliverable's required-figure list.
- **Produces:** A scoping record — `{in_scope_figures[], consensus_basis ('street/non-GAAP'
  | 'GAAP'), consensus_statistic ('mean' | 'median'), eps_metric_to_benchmark,
  revenue_metric_to_benchmark, source_map (which document carries each figure),
  sector_profile}`.
- **Success criteria:**
  - [ ] The scoped list covers all gold-required figures for the case — revenue total +
        by segment, the relevant profit lines, GAAP diluted EPS, adjusted EPS, weighted-avg
        diluted shares, OCF, capex, guidance, working-capital lines — without padding with
        irrelevant items.
  - [ ] **Sector-aware headline set.** Gross profit / gross margin is scoped **only where the
        issuer reports a cost-of-revenue line.** For financials — banks, insurers, and
        **asset managers** (this workflow's own vertical) — there is no COGS and no gross
        margin; the top line is total/net revenues or net interest income, and the relevant
        margin is operating or pre-tax. A missing gross-profit line on a financial issuer is
        **"not applicable," not "missing."**
  - [ ] `consensus_basis` matches the basis of the provided snapshot (recognizes most
        published EPS consensus is **non-GAAP**) and is fixed **before** any beat/miss is
        computed; the designated mean/median **statistic** is carried forward; the EPS to
        benchmark is declared same-basis-as-consensus.
  - [ ] The source map routes each figure to the correct document (non-GAAP reconciliation,
        guidance, segment summary → press release; GAAP statements, cash flow, FCF inputs,
        ASC 280 segment footnote, balance-sheet working capital → 10-Q) and does **not** claim
        a figure lives in a document that omits it.
- **Grading:** `hybrid` — deterministic source-routing + basis/statistic/sector check, plus a
  judged completeness check against the gold checklist.
- **Grading note — SCOPED GATE:** a wrong `consensus_basis` here zeros **C5 and S1** (the
  beat/miss chain that inherits it), but not the extraction or the GAAP-internal math.
- **Guards against:** *GAAP/non-GAAP basis mismatch* set up at planning time (declaring a
  GAAP-vs-street comparison that will manufacture a false beat/miss) · *missing material item*
  (omitting a required figure from scope) · *sector mismatch* (forcing a gross-profit line on a
  financial issuer) · *wrong-document* routing.

---

### Stage 2 — Extraction

> Pull each scoped figure off the statement and tie it to a verbatim evidence string.
> Extraction is **hybrid**: the value is checked deterministically *and* the citation is
> entailment-checked, so right-number/wrong-citation is caught separately from hallucination.

#### E1 — Extract headline income-statement figures with citations

- **Consumes:** GAAP income statement (10-Q/10-K) and the press-release headline table;
  the locked scale map (P2); the sector profile (P3); gold figures + evidence strings for
  revenue, gross profit *(where applicable)*, operating income, **pre-tax income**, **income-tax
  provision**, net income (GAAP), and **GAAP basic and diluted EPS**.
- **Produces:** A figure table — `{total_revenue, gross_profit?, operating_income,
  pretax_income, income_tax_provision, net_income_GAAP, GAAP_basic_EPS, GAAP_diluted_EPS}` —
  each as `{value, unit/scale, document, page, verbatim evidence string}`. Pre-tax income and
  the tax provision feed the effective-tax-rate check (C4); gross profit is `null / N/A` for
  issuers without a cost-of-revenue line.
- **Success criteria:**
  - [ ] Each value matches gold within tolerance (as-reported line items exact to reported
        precision or ≤ 0.5%; EPS ± \$0.01).
  - [ ] Each figure is scale-correct (consistent with P2; a thousands/millions slip
        auto-fails the figure).
  - [ ] Each figure carries a `{document, page, verbatim string}` citation that **actually
        entails** the value (FinanceBench-style entailment sub-score, graded separately
        from the value).
  - [ ] **GAAP** figures are pulled as GAAP — the "adjusted" line is not silently substituted
        where GAAP is required — and **basic vs diluted EPS** are captured as distinct rows.
  - [ ] Gross profit is captured where a cost-of-revenue line exists and correctly marked
        **N/A** (not fabricated, not "missing") where the issuer has none.
- **Grading:** `hybrid` (value deterministic + citation entailment).
- **Guards against:** *Hallucinated number* (value not in the filing) · *mis-citation*
  (right number, wrong/empty string or wrong page) · *GAAP/non-GAAP confusion* · *basic-vs-diluted
  EPS confusion* · *false precision* (more significant digits than disclosed) · *unit/scale slip*
  propagated from a misread header · *forcing a gross-profit line on a financial issuer*.

#### E2 — Extract segment revenue and share counts (basic, GAAP-diluted, non-GAAP-diluted, prior-year)

- **Consumes:** ASC 280 segment footnote (10-Q) and/or press-release segment summary; the
  income-statement / EPS-footnote weighted-average share reconciliation; the press-release
  non-GAAP EPS table (for the non-GAAP diluted count, where the company discloses one); the
  prior-period comparatives (year-ago diluted shares); gold segment revenues (incl.
  corporate/eliminations) and gold share counts.
- **Produces:** A segment table `{segment → revenue}` plus corporate/eliminations/"all other",
  and a share-count block
  `{weighted_avg_basic_shares, weighted_avg_GAAP_diluted_shares, weighted_avg_nonGAAP_diluted_shares?,
  prior_year_diluted_shares}` — each with `{document, page, verbatim string}`.
- **Success criteria:**
  - [ ] Each segment revenue (and the corporate/eliminations line) matches gold within
        tolerance, cited to the segment footnote.
  - [ ] **Weighted-average diluted** shares (period-average) are reported and match gold;
        **basic and diluted are reported separately**; period-**end** shares from the cover
        page are **not** substituted for weighted-average. This is the single most
        commonly-missed extraction trap.
  - [ ] Where the company reports a **separate non-GAAP diluted share count** (common when GAAP
        is a net loss — anti-dilutive securities excluded under the GAAP loss become dilutive for
        non-GAAP income), it is captured **distinctly** from the GAAP diluted count, both cited.
        The non-GAAP count feeds the C3 bridge denominator.
  - [ ] The **year-ago** weighted-average diluted count is captured (feeds the C1 buyback /
        share-count-change check).
  - [ ] Each value cites the correct span (segment footnote / share reconciliation / non-GAAP
        table), with the correct document.
  - [ ] **Extraction completeness:** the 'all other' / corporate / eliminations bucket is not
        silently dropped. *(This is the completeness leg; the actual Σ-equals-consolidated
        arithmetic is performed in C5 — the two are distinct: E2 guards that no row is lost,
        C5 performs the tie-out.)*
- **Grading:** `hybrid`.
- **Guards against:** *Basic-vs-diluted confusion* / *using period-end cover-page shares* ·
  *GAAP-vs-non-GAAP diluted-share divergence* (reusing the GAAP diluted count where the company
  used a different non-GAAP count) · *segment row dropped during extraction* · *hallucinated or
  mis-cited segment figures* · *wrong-document* (pulling segment data from the release summary
  when the authoritative footnote is in the 10-Q).

#### E3 — Extract non-GAAP add-backs (incl. the tax-effect line), OCF, and capex

- **Consumes:** Press-release GAAP-to-non-GAAP reconciliation table; 10-Q statement of cash
  flows; the locked scale map (P2); gold adjusted/non-GAAP EPS, each add-back line **as
  disclosed** (some pre-tax, some after-tax), the company's stated **"income-tax effect of
  adjustments"** line, OCF, and capex.
- **Produces:** `{adjusted_EPS, addbacks[{name, value, basis: 'pretax'|'after-tax'}],
  tax_effect_of_adjustments, operating_cash_flow, capex, capex_definition}` — each with
  `{document, page, verbatim string}`; non-GAAP items explicitly labeled non-GAAP and sourced to
  the press release; OCF/capex sourced to the 10-Q cash-flow statement.
- **Success criteria:**
  - [ ] Adjusted EPS and each named add-back (SBC, amortization of acquired intangibles,
        restructuring, acquisition/divestiture charges, impairments, discrete tax items) match
        gold within tolerance, cited to the reconciliation table, each tagged **pre-tax or
        after-tax as the company presents it**, and explicitly **labeled non-GAAP**.
  - [ ] The company's **"income-tax effect of adjustments"** is captured as its **own
        reconciling line** (not derived by applying an assumed blended rate to the summed
        add-backs).
  - [ ] OCF and capex match gold within tolerance, cited to the cash-flow statement (operating
        and investing sections); the **capex definition** is recorded (e.g., "purchases of
        property & equipment" vs a company definition that also includes capitalized
        software/intangibles), so the FCF check is unambiguous; the model **flags** when the
        release omitted the cash-flow statement and the figures come only from the 10-Q.
  - [ ] Each value cites the correct document (non-GAAP/guidance → press release; cash flow → 10-Q).
- **Grading:** `hybrid`.
- **Guards against:** *GAAP/non-GAAP confusion* (showing an adjusted figure as GAAP, unlabeled) ·
  *hallucinated add-backs* or dropped/double-counted reconciliation lines · *treating the tax
  effect as a single blended rate* instead of the disclosed line · *capex-definition ambiguity* ·
  *mis-citation / wrong-document* (sourcing cash flow from the release where it's absent) ·
  *unit/scale slip*.

#### E4 — Extract forward guidance

- **Consumes:** Press-release guidance section / outlook table; any guidance withdrawal or
  revision language in MD&A; gold guidance ranges, basis, and any withdrawal flag.
- **Produces:** `{guidance_revenue_range, guidance_eps_range, guidance_basis (GAAP|non-GAAP),
  guidance_period (next-quarter | full-year), withdrawn_or_revised_flag}` — each with
  `{document, page, verbatim string}`, or `NOT_DISCLOSED` where the issuer gave no guidance.
- **Success criteria:**
  - [ ] Each guidance range matches gold (low/high endpoints) and is cited to the outlook
        section; the **basis** (GAAP vs non-GAAP) is captured so S1 compares like-for-like
        against guidance consensus.
  - [ ] A **withdrawal or downward revision** of prior guidance is flagged (a frequent, material
        stock driver) — not silently dropped.
  - [ ] Where the company **declines to guide**, `NOT_DISCLOSED` is returned, not a fabricated range.
  - [ ] The guidance period (next-quarter vs full-year) is correctly labeled.
- **Grading:** `hybrid`.
- **Guards against:** *Missing material item* (omitting guidance or a guidance cut/withdrawal —
  often the bigger driver than the printed quarter) · *hallucinated guidance range* · *mis-citation* ·
  *basis confusion* between GAAP and non-GAAP guidance.

#### E5 — Extract balance-sheet working-capital lines

- **Consumes:** 10-Q condensed balance sheet and, where needed, the income statement
  cost-of-revenue line; the prior-period comparatives; the sector profile (P3); gold accounts
  receivable, inventory, deferred/unearned revenue, and COGS (for DIO).
- **Produces:** `{accounts_receivable, inventory?, deferred_revenue?, cogs?}` for the current and
  prior period — each with `{document, page, verbatim string}`; inventory/COGS marked `N/A` for
  issuers (e.g., asset managers, banks) that carry none. These feed the DSO/DIO and
  deferred-revenue trend in C4.
- **Success criteria:**
  - [ ] Each working-capital line matches gold within tolerance, cited to the balance sheet.
  - [ ] **Sector-aware:** inventory and DIO are marked **N/A** (not "missing," not fabricated)
        for issuers with no inventory; deferred/unearned revenue is captured where the business
        model has it (subscription/software/insurance).
  - [ ] Current **and** prior-period values are captured so C4 can compute a trend.
  - [ ] Each value cites the correct balance-sheet line and page.
- **Grading:** `hybrid`.
- **Guards against:** *Hallucinated balance-sheet figure* · *mis-citation* · *missing material
  item* (a working-capital line S2 needs to flag accrual-quality issues) · *forcing inventory on
  a no-inventory issuer*.

#### E6 — Calibrated refusal: mark not-disclosed / not-reconcilable figures

- **Consumes:** The document set, which genuinely omits ≥ 1 required figure (e.g.,
  segment-level operating margin when only segment *revenue* is given; FCF when the
  cash-flow statement is absent and the 10-Q hasn't dropped; an unreconciled non-GAAP bridge
  line; withdrawn guidance); a paired **answerable twin** where the figure IS disclosed but
  *buried* in a footnote/table; gold labels and gold *reason* strings for both.
- **Produces:** For each probe, a typed answer — either `{value, unit, citation}` or
  `{NOT_DISCLOSED, reason, citation-to-absence}` (which statement would carry it, and that it
  is not broken out). The answerable twin returns the buried figure with its citation.
- **Success criteria:**
  - [ ] On the genuinely-undisclosed probe, the `NOT_DISCLOSED` **label is correct**
        (deterministic) **and** the **reason is correct** (judged against the gold reason —
        e.g., "segment operating margin is not broken out; only segment revenue is reported in
        the ASC 280 footnote").
  - [ ] Any confident fabricated value on the undisclosed probe scores **zero** (hard failure).
  - [ ] On the **answerable twin**, the buried figure IS retrieved and cited; refusing it
        (over-refusal) is **penalized** (deterministic on the retrieval).
  - [ ] No prior-period or memorized number is imported to fill the gap; the refusal states
        *why*, not a generic hedge.
- **Grading:** `label-deterministic + reason-judge` (the label and twin-retrieval are checked
  deterministically; the refusal *reason* is judged).
- **Guards against:** *Sycophancy / failed calibrated refusal* (fabricating a figure instead
  of saying "not disclosed") · *over-refusal* on a disclosed-but-buried figure · *hallucination
  from prior-period / parametric memory* · *false precision* implying a non-disclosed item
  was measured.

---

### Stage 3 — Calculation

> The desk math, graded deterministically as executable program-of-thought (FinQA-style):
> right **operands** *and* right **operation**, so a wrong result is localized to a misread
> operand vs. an arithmetic slip.

#### C1 — Compute YoY and QoQ growth, and the YoY diluted-share-count change

- **Consumes:** Current-period revenue (E1) and current/prior weighted-average diluted shares
  (E2); gold year-ago and prior-quarter comparatives + restatement / segment-redefinition flags;
  gold YoY/QoQ values and gold share-count change with derivations.
- **Produces:** Separately labeled `{YoY_growth, QoQ_growth}` for revenue (and other scoped
  lines), each as a derivation `(current − base)/base` naming the base figure and its citation;
  a like-for-like flag where a redefinition/restatement applies; and the
  `{YoY_diluted_share_change}` = (current − year-ago diluted shares)/year-ago, which
  deterministically substantiates a buyback-driven-EPS claim in S2.
- **Success criteria:**
  - [ ] YoY = (current − year-ago same quarter)/year-ago and QoQ = (current − immediately-prior
        quarter)/prior, reported as **separate labeled outputs** — neither substituted for the other.
  - [ ] Each value matches gold within tolerance (≤ 0.1pp on the rate or ≤ 0.5% relative on the level).
  - [ ] **Sign / direction is correct** (a positive growth is never reported negative or vice versa).
  - [ ] The base is like-for-like — the **restated** base is used where a restatement/segment
        redefinition applies, not the originally-reported number, and the adjustment is noted.
  - [ ] The **YoY diluted-share-count change** is computed and signed correctly (a *lower* count
        is the denominator effect that lifts EPS without higher earnings).
  - [ ] No false precision: rate reported to a precision the inputs justify.
- **Grading:** `deterministic`.
- **Guards against:** *Period-over-period base error* (YoY off the sequential quarter; QoQ off
  the year-ago quarter) · *wrong-sign / directional error* (flips the conclusion — **in-checkpoint
  hard-fail**, does not gate downstream) · *growing off a restated base / ignoring segment
  redefinition* · *un-quantified buyback effect* · *arithmetic slip* · *false precision*.

#### C2 — Compute margins and deltas in basis points (sector-aware), and FCF

- **Consumes:** Revenue and the profit lines (E1); OCF and capex (E3); year-ago comparatives for
  the same margins; the sector profile (P3); gold margins, gold YoY margin deltas in bps, and gold FCF.
- **Produces:** `{gross_margin?, operating_margin, net_margin}` = income ÷ revenue for current and
  year-ago, plus YoY deltas in **basis points**; and `FCF = OCF − capex` — each with
  operands-and-citations.
- **Success criteria:**
  - [ ] Each applicable margin = corresponding income / revenue, matching gold within ≤ 0.1pp;
        **gross margin is computed only where E1 captured a gross-profit line** (operating/pre-tax
        margin substitutes for financials).
  - [ ] Each YoY margin delta is expressed in **basis points** and matches gold within ≤ 15 bps,
        with the correct sign, and is **internally consistent** with the model's own two margin levels.
  - [ ] **FCF = OCF − capex** within ≤ 0.5% relative; FCF is **not** equated to OCF; a company's
        non-standard "adjusted/levered FCF" is **flagged against the recorded capex definition (E3)**,
        not silently adopted.
  - [ ] Same-basis inputs (GAAP margin from GAAP figures; no GAAP-income-over-adjusted-revenue mix).
  - [ ] Operands trace to the cited E1/E3 figures (reuse, not re-extraction of new numbers).
- **Grading:** `deterministic`.
- **Guards against:** *Arithmetic / operand-selection error* · *FCF definition error* (equating
  FCF to OCF; forgetting capex; silently using "adjusted FCF") · *false precision / rounding
  ambiguity* (resolved by the bps convention) · *basis mismatch* in a margin · *forcing a gross
  margin on a financial issuer*.

#### C3 — Verify the GAAP→non-GAAP EPS bridge (step-checked)

- **Consumes:** GAAP net income (E1) and the share-count block (E2); the reconciliation
  add-backs **with their pre-tax/after-tax basis** and the disclosed **tax-effect-of-adjustments**
  line (E3); the company-reported adjusted EPS (E3); the gold step-by-step bridge.
- **Produces:** A program-of-thought derivation: GAAP net income → add each add-back **as
  disclosed** (pre-tax add-backs summed, after-tax items added directly) → apply the company's
  **stated tax-effect line** → non-GAAP net income → ÷ the **non-GAAP diluted share count** →
  non-GAAP EPS. Each step carries operands-and-citations and an intermediate value.
- **Success criteria:**
  - [ ] The bridge reproduces the company-reported non-GAAP EPS within ± \$0.01, with **every
        add-back present once** (none dropped or double-counted), each handled on its disclosed
        pre-tax/after-tax basis.
  - [ ] The tax effect is taken from the company's **disclosed "income-tax effect of adjustments"
        line**, **not** computed by applying a single blended statutory rate to the summed
        add-backs.
  - [ ] The bridge divides by the **non-GAAP diluted** share count where the company reports one
        distinct from the GAAP diluted count (the loss-quarter dilution case), and by
        weighted-average **diluted** (never basic or period-end) otherwise.
  - [ ] The model neither **omits a disclosed adjustment** nor **invents a non-standard add-back**
        (Reg G / Item 10(e) discipline — e.g., adding back recurring SBC as if one-time).
  - [ ] Partial credit localizes to the **exact failing step** (a specific add-back, the tax-effect
        line, or the share basis), not just "wrong final EPS".
- **Grading:** `deterministic` (multi-step, step-checked).
- **Guards against:** *GAAP/non-GAAP confusion* via a partial or double-counted bridge ·
  *tax-effect error* (blended-rate shortcut instead of the disclosed line; mishandling after-tax
  items) · *diluted-share-basis error* (GAAP diluted reused where a non-GAAP count applies; basic
  instead of diluted) · *hallucinated or omitted add-back* · *context-loss across multi-step calc*.

#### C4 — Quality-of-earnings ratios: effective tax rate, DSO/DIO, OCF-to-net-income

- **Consumes:** Pre-tax income and tax provision (E1); net income (E1) and OCF (E3); revenue (E1),
  receivables, inventory, COGS (E5); the prior-period comparatives; the sector profile (P3); gold
  ratios with tolerance.
- **Produces:** `{effective_tax_rate = tax_provision/pretax_income, effective_tax_rate_YoY_delta,
  DSO = receivables/revenue × days?, DIO = inventory/COGS × days?, OCF_to_net_income = OCF/net_income}`
  — each a derivation with operands-and-citations; inventory-based DIO marked `N/A` where E5 found none.
- **Success criteria:**
  - [ ] Effective tax rate and its **YoY delta** are computed and within tolerance — this is the
        deterministic ground for an S2 claim that "the beat was driven by a discrete tax benefit,
        not operating outperformance."
  - [ ] DSO (and DIO where inventory exists) are computed on a consistent day-count and within
        tolerance, current vs prior, so S2's working-capital red flags rest on a number, not a vibe.
  - [ ] **OCF-to-net-income** is computed; a ratio materially below 1.0 is the accrual-quality
        signal S2 consumes.
  - [ ] Sector-aware: inventory/DIO returns `N/A` for no-inventory issuers rather than failing.
- **Grading:** `deterministic`.
- **Guards against:** *Mis-attribution* of a low-quality beat (no number behind the tax/working-capital
  story) · *arithmetic / operand error* · *missing red flag* (accrual-quality gap never computed) ·
  *false precision*.

#### C5 — Beat/miss vs consensus and segment sum-to-total tie-out

- **Consumes:** Reported revenue and the EPS to benchmark (E1, correct basis per P3); the consensus
  snapshot (revenue and EPS, with basis, **designated statistic**, dispersion, as-of date); segment
  revenues + corporate/eliminations (E2); gold beat/miss magnitudes and the gold consolidated-revenue
  tie-out.
- **Produces:** **(a)** `{revenue_beat_miss, eps_beat_miss}` each as **both** an absolute difference
  (reported − consensus) **and** a percent of consensus, on the matching basis, against the
  **designated mean/median** statistic; **(b)** a tie-out: Σ(segment revenue + corporate/eliminations)
  vs consolidated revenue.
- **Success criteria:**
  - [ ] Beat/miss computed for **both** revenue and EPS — revenue beat/miss as **both an absolute
        difference and a percent of consensus**; EPS beat/miss as an **absolute difference (± \$0.01)** —
        on the **same basis** as the consensus snapshot (adjusted-to-adjusted, GAAP-to-GAAP) and against
        the **pinned statistic** (mean or median, not whichever flatters); magnitude within tolerance.
  - [ ] The comparison does **not** pit GAAP EPS against a street/non-GAAP consensus (a basis-mismatch
        here is an **in-checkpoint hard-fail**, and the P3 scoped gate already zeros this checkpoint if
        the basis was set wrong upstream).
  - [ ] Direction is correct, and **"in-line"** is used when the difference is within consensus
        **dispersion** (or, where dispersion is unavailable, within rounding noise) — no false
        beat/miss claimed inside the noise.
  - [ ] Where the consensus base is near zero (a breakeven / loss-quarter EPS consensus), the
        **percent** beat/miss is suppressed or flagged as unstable and the **absolute** \$/EPS
        difference governs the directional call.
  - [ ] Segment revenues + corporate/eliminations **tie** to consolidated revenue within rounding
        (a break flags a wrong segment pull or a missed bucket). *(Where the issuer discloses a
        segment profit measure, the ASC 280 reconciliation of segment profit to consolidated pre-tax
        income is a richer optional tie-out, noted for case authoring.)*
  - [ ] Consensus provider / basis / statistic / as-of date is stated so the comparison is reproducible.
- **Grading:** `deterministic`.
- **Guards against:** *GAAP/non-GAAP basis mismatch* manufacturing a false beat/miss · *wrong-sign /
  directional error* on beat vs miss (**in-checkpoint hard-fail** on a flipped direction) · *mean-vs-median
  ambiguity* flipping a marginal call · *segment sum-to-total break* · *false precision* inside consensus
  dispersion.

---

### Stage 4 — Synthesis

> The read. Multiple phrasings are valid, so these route to an LLM judge with correctness +
> contradiction operators against an expert rubric. The judge cross-checks every claim against the
> deterministic numbers upstream — a narrative that contradicts the computed beat/miss trips the
> contradiction operator.

#### S1 — State beat/miss and guidance-vs-street as discrete directional calls

- **Consumes:** Beat/miss magnitudes (C5); extracted guidance (E4) + next-period guidance consensus;
  the declared consensus basis (P3); gold direction labels.
- **Produces:** Two discrete claims — reported quarter = `{beat | in-line | miss}` on revenue and
  on EPS (with magnitude); next-period guidance = `{above | in-line | below}` street, with the
  implication noted.
- **Success criteria:**
  - [ ] Reported beat/miss direction matches gold for **both** revenue and EPS and is **consistent
        with the computed C5 magnitude** (contradiction operator trips on conflict).
  - [ ] Guidance-vs-street direction matches gold and is stated as a discrete above/in-line/below
        call — on the correct (matching) basis, referencing the E4 guidance and the guidance consensus —
        not vague prose.
  - [ ] Where the **forward guidance** (not the printed quarter) is the dominant signal, that is recognized.
- **Grading:** `judge`.
- **Guards against:** *Directional error* restated in prose (beat called a miss, or vice versa) ·
  *confusing the reported-quarter read with the forward read* · *basis mismatch* leaking into the
  verbal call · *missing material item* (omitting guidance-vs-street when it's the key driver) ·
  *internal contradiction* with the computed numbers.

#### S2 — Flag the 2–4 material changes and earnings-quality red flags

- **Consumes:** The full extracted/calculated record (E1–E6, C1–C5) — in particular the C4 QoE
  ratios, the C1 share-count change, and the E5 working-capital lines; any one-time items, buyback
  activity, segment redefinition, or restatement notes; the expert gold rubric for this case.
- **Produces:** A ranked list of 2–4 material changes with their swing factors, plus a
  quality-of-earnings assessment: OCF-vs-net-income gap (C4), DSO/DIO trend (C4), one-time / discrete-tax
  impact on the headline (C4 effective-rate delta), buyback-driven EPS (C1 share-count change), and any
  segment-redefinition / restatement caveat — **each tied to a cited, computed figure**.
- **Success criteria:**
  - [ ] Identifies the gold material changes (per-key-point: each required change is a correctness
        operator; missing a must-have item loses that point).
  - [ ] Correctly attributes the **swing factor** for the headline — e.g., "beat driven by a discrete
        tax benefit (effective rate down [X] bps YoY, C4), not operating outperformance"; "EPS up on a
        **lower share count** ([Y]% fewer diluted shares YoY, C1) despite flat net income" (buyback-driven
        EPS framed as a *denominator* effect, not higher earnings).
  - [ ] Flags quality red flags present in the data: **OCF materially below net income** (C4 accrual
        quality), rising DSO/DIO (C4), deferred-revenue swings (E5), segment redefinition making YoY
        non-like-for-like (C1).
  - [ ] Does **not** invent a red flag the evidence doesn't support (contradiction operator); each flag
        is grounded in a cited, computed figure — not a judge-trusted number with no upstream checkpoint.
- **Grading:** `judge`.
- **Guards against:** *Missing material item* (restatement, one-time gain/charge driving the beat,
  guidance cut/withdrawal, buyback-driven EPS, working-capital red flag) · *mistaking a low-quality
  beat for operating strength* · *hallucinated / unsupported red flag* · *sycophantic "all good"
  synthesis* ignoring disclosed risk.

#### S3 — Calibrated bottom line with explicit uncertainty

- **Consumes:** All prior checkpoint artifacts, including the E6 not-disclosed results; any definition
  variances (e.g., adjusted FCF, capex definition), like-for-like caveats, or consensus-snapshot
  limitations; the expert gold rubric for the bottom-line read.
- **Produces:** A 3–6 sentence bottom line: the **quality-adjusted** net read (beat/miss + guidance
  direction), the 1–2 dominant swing factors, the quality caveat, and an explicit statement of what is
  **not** disclosed or could **not** be verified from the provided documents.
- **Success criteria:**
  - [ ] The bottom line is **consistent** with the computed beat/miss and the quality flags (does not
        call a low-quality beat "strong" without caveat; no contradiction with S1/C5).
  - [ ] **Explicitly names** the not-disclosed / not-reconcilable items (carrying E6 forward) rather
        than papering over them — calibrated uncertainty is rewarded as a first-class positive criterion.
  - [ ] Expresses calibrated confidence — decisive where the data is clear, hedged where thin — **without
        fabricating precision** and without blanket over-refusal that ignores what *was* determinable.
  - [ ] Introduces **no new figures** that were not extracted/calculated upstream.
- **Grading:** `judge`.
- **Guards against:** *Sycophancy / overconfident bottom line* hiding uncertainty or not-disclosed gaps ·
  *over-refusal / uninformative blanket hedging* · *false precision / overstated conviction* · *internal
  contradiction* with the computed numbers · *introducing hallucinated figures* in the conclusion.

---

## Failure taxonomy guarded

The named failure modes, mapped to the checkpoint(s) that catch each. This is the skeleton of the
Phase-5 taxonomy table, which is populated mechanically from graded traces (each checkpoint is tagged
with its bucket(s), so every failed criterion drops into a pre-labeled cell). The **Severity** column
uses the three-tier model from *How this maps to an eval*: **hard gate** (zeros all dependents),
**scoped gate** (zeros a named subset), **in-checkpoint fail** (zeros only that checkpoint), or **—**
(scored on its own with no gating).

| Failure mode | What it looks like | Caught by | Severity |
|---|---|---|---|
| **Wrong fiscal period** | Q3 reported as Q2; fiscal-vs-calendar confusion; year-ago column read as current; Q4 treated as a standalone 10-Q | **P1** | **Hard gate** |
| **Wrong source document** | Citing the press release for a GAAP statement only in the 10-Q (or vice versa); cash flow sourced from a release that omits it | **P1**, **P3**, **E3** | P1: **Hard gate** |
| **Unit / scale error** | Reading "in thousands" as dollars or millions (off by 1,000×); release-absolute vs 10-Q-thousands mismatch; per-share figure mixed with a scaled aggregate | **P2** (gate); propagated checks in **E1–E5** | **Hard gate** |
| **GAAP / non-GAAP confusion** | Adjusted figure shown as GAAP unlabeled; GAAP EPS compared to a street consensus; partial/double-counted bridge | **P3**, **E1**, **E3**, **C3**, **C5** | P3/C5 basis: **Scoped gate** → C5, S1 |
| **Non-GAAP tax-effect error** | Applying a blended statutory rate to summed add-backs instead of the disclosed "tax effect of adjustments" line; mishandling after-tax items | **E3**, **C3** | — |
| **Diluted-share-basis error** | Basic or period-end cover-page shares used instead of weighted-average diluted; GAAP diluted reused where the company used a distinct non-GAAP diluted count (loss quarter) | **E2**, **C3** | — |
| **Hallucinated number** | A plausible figure not present in the filing, often on a genuinely not-disclosed item | **E1**, **E2**, **E3**, **E4**, **E5**, **E6**, **S2**, **S3** | — |
| **Mis-citation** | Right number, wrong document/page/table, or a cited string that doesn't actually support the figure | **E1**, **E2**, **E3**, **E4**, **E5** (entailment sub-check) | — |
| **Period-over-period base error** | YoY off the sequential quarter; QoQ off the year-ago quarter; growing off a restated base; ignoring segment redefinition | **C1** | — |
| **Wrong-sign / directional error** | Negative growth reported as positive; a beat called a miss | **C1**, **C5**, **S1** | **In-checkpoint fail** |
| **Segment sum-to-total break** | Segment revenues + eliminations failing to tie to consolidated; missed "all other" bucket (E2 = row dropped in extraction; C5 = the Σ arithmetic) | **E2**, **C5** | — |
| **FCF definition error** | Equating FCF to OCF; forgetting capex; silently using a non-standard "adjusted FCF"; ambiguous capex definition | **E3**, **C2** | — |
| **Mis-attributed low-quality beat** | Calling a discrete-tax-benefit or buyback-driven beat "operating strength"; no number behind the quality story | **C1**, **C4**, **S2** | — |
| **Working-capital / accrual red flag missed** | Rising DSO/DIO, OCF far below net income, deferred-revenue swing not flagged | **E5**, **C4**, **S2** | — |
| **False precision** | More significant digits than disclosed; a "beat" claimed inside consensus dispersion | **E1**, **C1**, **C2**, **C5**, **S3** | — |
| **Missing material item** | Omitting a restatement, a one-time item driving the beat, a guidance cut/withdrawal, buyback-driven EPS, or a working-capital red flag | **P3**, **E4**, **S1**, **S2** | — |
| **Sector mismatch** | Forcing a gross-profit / gross-margin line on an asset manager, bank, or insurer that has none | **P3**, **E1**, **C2** | — |
| **Sycophancy / failed calibrated refusal** | Fabricating a figure rather than answering "not disclosed"; an overconfident bottom line that hides uncertainty | **E6**, **S2**, **S3** | — |
| **Over-refusal** | Refusing a figure that IS disclosed (buried in a footnote/table) | **E6** (answerable twin) | — |

---

## What Phase 2 / 3 / 4 will add

This decomposition is the spine of a system, not a standalone document. **Phase 2 (`rubric/`)** turns
each checkpoint's success criteria into a scored rubric: the gating conditions named here (wrong
period, wrong source, unit/scale → hard gates; consensus-basis mismatch → scoped gate; wrong-sign →
in-checkpoint fail) become explicit auto-fails with defined blast radius, and the remaining criteria
become weighted, tiered, atomic statements graded by an LLM judge — with the per-figure tolerance bands
and an explicit "what counts as a zero" — plus the documented judge prompt, the value/entailment split
for hybrid checkpoints, the label+reason grader for E6, and the dual gated/partial-credit scoring.
**Phase 3 (`cases/`)** authors 3–5 real companies pulled from SEC EDGAR (a 10-Q or 10-K + earnings
release each), writing the gold answer for every checkpoint *with its `{document, page, verbatim
string}` citation* — deliberately including the hard cases the checkpoints were designed for: a
thousands-vs-millions trap, a fiscal-vs-calendar period, a company whose street consensus is non-GAAP,
a **loss-quarter issuer whose non-GAAP diluted share count differs from GAAP**, a buyback-driven-EPS
quarter, a discrete-tax-benefit beat, a segment-redefinition / restatement, an **asset manager with no
gross-profit line** (sector coverage), and at least one genuine "not disclosed" probe with its
answerable twin. **Phase 4 (`harness/`)** wires it to run: a Python checker for the deterministic
checkpoints (value + tolerance + scale-folding + evidence entailment), an LLM-as-judge for the
synthesis checkpoints, the label+reason grader for the refusal probe, both the Oracle (isolated-probe)
and end-to-end run modes, and a `python -m …` entry point that emits a scored report. Phase 5 then runs
frontier models through it, grades them, and builds the failure taxonomy above from real traces —
including a judge-vs-expert macro-F1 calibration check on a hand-graded sample, which is the artifact
that proves the judge is trustworthy.
