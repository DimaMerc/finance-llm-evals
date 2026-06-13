# Rubric — master scoring model for the quarterly earnings-analysis eval

> **Phase 2 deliverable.** This is the scoring contract for the 17-checkpoint
> earnings-analysis workflow defined in [`../workflow/earnings-analysis.md`](../workflow/earnings-analysis.md).
> The machine-readable atoms the harness loads live in [`criteria.yaml`](criteria.yaml);
> the frozen LLM-judge prompt that grades the free-form atoms lives in [`judge.md`](judge.md).
> This document is the human-readable spec that ties the two together: what every number means,
> how the headline is computed, and exactly what scores a zero.
>
> `rubric_version: 2.1.0` (the 2.0.0 atom set — unchanged ids / points / gates — under
> checkpoint-primary aggregation with a category rollup) · pinned to `judge_version: 2.1.0`
> (the judge prompt is lens-agnostic and unchanged).

---

## 1. Framing — what this rubric is, in one paragraph

When a company prints, the analyst's job in the first hours is a chain: pin the period and the
scale, extract each figure off the right statement with a citation, redo the desk math, benchmark
against consensus on a like-for-like basis, and write a bottom line a PM can act on. I ran the
change-management side of an institutional ETF servicing platform, where a
thousands-vs-millions slip or a wrong fiscal-period label is not a rounding error — it is a break
that has to be reconciled before anything downstream clears. **This rubric encodes that discipline:
it scores the workflow checkpoint-by-checkpoint, so the headline number tells you *which step*
failed, not just *that* the memo is wrong.** Every success-criterion checkbox from Phase 1 is broken
into **atomic, independently graded criteria** (HealthBench style); numbers are checked
deterministically against gold with explicit tolerance bands (FinQA/TAT-QA style); citations are
entailment-checked separately from the value (FinanceBench style); free-form synthesis is graded by
a documented LLM judge that **never re-derives a number** and trips a contradiction operator when
prose conflicts with the computed gold; and a calibrated refusal is a **first-class positive** — but
a vague "I can't verify" hedge is scored as over-refusal, never as caution. Three gate tiers
auto-fail the errors that poison everything downstream, and the harness reports the gated score, the
ungated partial-credit score, and the **gap** between them so "almost right" cannot inflate a naive
average.

---

## 2. The scoring model end-to-end

The model produces one earnings memo (header + extraction table + calculation block + synthesis).
The harness scores it **bottom-up**: atom → checkpoint → case headline, with a **category rollup**
computed in parallel as the diagnostic a hiring manager reads. There is exactly **one graded atom
set**; both the headline and the category subscores fall out of it with no re-grade.

### 2.1 The atom (the unit of grading)

Every Phase-1 success checkbox becomes one or more **atoms**. An atom is a single self-contained
statement with a signed point value. From [`criteria.yaml`](criteria.yaml):

```yaml
- id: C2.fcf
  checkpoint: C2
  category: numerical
  criterion: "FCF = OCF - capex within <=0.5% relative; FCF is NOT equated to OCF; ..."
  points: 6
  grader: deterministic
  gate: none
  tolerance: fcf
  tags: [fcf_definition]
```

- **`points`** — signed, nonzero, ~[−10, +10]. **Positive** = should-include (content the memo must
  contain). **Negative** = should-NOT; a negative atom subtracts its magnitude *when the bad behavior
  is present*.
- **`m` (met fraction)** ∈ [0, 1] — the grader's verdict. Most atoms are binary (m ∈ {0, 1}); the
  per-figure value atoms and the C3 bridge expand into sub-atoms so partial credit emerges from
  *how many* sub-atoms are met, not from grading one number partially.
- **`earned = m · points`** — a met positive atom adds points; a met negative atom subtracts.

There are **109 atoms** across the 17 checkpoints: **+353** positive point mass and **−135** penalty
mass. (Counts and masses are printed by [`validate.py`](validate.py) and asserted at harness load — see §2.6.)

### 2.2 INNER layer — the checkpoint score (HealthBench formula)

For each checkpoint *k*, pool its atoms:

```
raw_pos(k)          = Σ points over the POSITIVE atoms in k             (the achievable ceiling)
awarded(k)          = Σ (m · points) over ALL atoms in k, including met negatives (which subtract)
checkpoint_raw(k)   = awarded(k) / raw_pos(k)
checkpoint_score(k) = clip(checkpoint_raw(k), 0, 1)        # clip_per_checkpoint: true
```

The denominator is the **positive mass only** — the HealthBench asymmetry. Penalties live in the
numerator but never raise the ceiling, so a confidently-wrong checkpoint goes **negative before the
clip**. We **retain the raw, unclipped `checkpoint_raw(k)`** alongside the clipped value and feed it
to the failure-taxonomy / gap log: a fabrication-heavy checkpoint is logged as strictly worse than a
blank one, even though its reported contribution bottoms out at 0.

> **E6 is the one headline exception (F1).** Every other checkpoint's headline is `awarded/raw_pos`.
> **E6's headline is the FailSafeQA F-beta** instead: `checkpoint_score(E6) = LLMC_β(R, G)` with
> `β = 0.5` (§7). `G` (grounded-refusal on the genuinely-undisclosed probe) ∈ {0, 0.25, 1} — bucket A
> grounded refusal → 1, bucket B vague hedge → 0.25, bucket D imported number → 0.25, bucket C
> fabrication → 0; `R` (compliance on the answerable twin) ∈ {0, 0.5, 1} — value-in-tolerance **and**
> cited → 1, value-right/cite-wrong (or vice versa) → 0.5, twin refused/wrong → 0. A **refuse-all**
> policy drops `R` to 0, so `E6 = 0`. The E6 ± atoms **still feed the calibration category rollup and
> the taxonomy** (they are pooled into `calibration` as usual); they simply do not form the E6
> *headline*. `AllPass(E6)` = grounded refusal **and** twin retrieved (`LLMC_β = 1`).

### 2.3 PRIMARY headline — the checkpoint-weighted case score

The case headline is a fixed-weight sum over the 17 clipped checkpoint scores:

```
CaseScore = Σ_k  W_k · checkpoint_score(k)          ∈ [0, 1]
```

The 17 weights `W_k` are in `meta.checkpoint_weights` and **sum to 1.0** (§3.2). Because each
checkpoint is normalized to [0, 1] *before* weighting, a 12-atom checkpoint cannot out-shout a
4-atom one at the case level — the number of atoms in a checkpoint sets its *internal* resolution,
not its *external* weight. The headline is therefore a **17-element vector plus one weighted scalar**:
the vector says exactly which step failed (a misread operand in E1 vs. an arithmetic slip in C2);
the scalar is the single comparable number.

### 2.4 SECONDARY layer — the category rollup (the diagnostic)

In parallel, pool the *same* atoms by their `category` tag, across all 17 checkpoints:

```
CategoryScore(t) = Σ (m · points) over atoms tagged t, incl. met negatives
                   ───────────────────────────────────────────────────────
                   Σ points over the POSITIVE atoms tagged t
```

Reported **raw** (not re-clipped, not re-aggregated into the headline). This is the six-number
diagnostic a screener reads — `numerical 0.78 / extraction 0.91 / entailment 0.64 / reasoning 0.55 /
calibration 0.34 / structure 1.0`. It answers "*what kind* of error does this model make?" where the
checkpoint vector answers "*where* did it fail?". The two are different cuts of one atom set; the
category weights (§3.1) are reported beside the rollup so a reader can also collapse it to a single
category-weighted scalar if they prefer that lens — but the **published headline is the
checkpoint-weighted CaseScore**, because localizing failure to a step is the Phase-1 thesis.

> **Why two layers, not one.** The checkpoint vector is the faithful mirror of the workflow chain
> (it makes All-Pass a clean per-checkpoint AND and lets the three gate tiers act on named steps with
> no impedance mismatch). The category rollup is the screener-facing summary. Reporting both, from one
> graded atom set, costs nothing and serves both audiences.

### 2.5 SUITE layer — across cases

```
Suite_ungated = clip( mean_i CaseScore_ungated(i), 0, 1 )
Suite_gated   = clip( mean_i CaseScore_gated(i),   0, 1 )
Suite_AllPass = mean_i AllPass(i)                        # AllPass ∈ {0,1}, see §4
GAP           = Suite_ungated − Suite_gated
```

`clip_per_checkpoint: true` clips each checkpoint score to [0, 1] before the `W_k` sum (so the
weighted headline is already in range), `clip_per_case: false` leaves the case headline unclipped,
and only the **suite mean** is clipped (`clip_suite: [0.0, 1.0]`). The retained raw unclipped
checkpoint value still records how far negative a fabrication-heavy checkpoint went. Every suite number is reported **twice**: once in **Oracle** mode
(correct frame + gold page injected — pure reasoning) and once in **end-to-end** mode (the agent
retrieves and pins everything itself). The Oracle-vs-end-to-end gap on `Suite_gated` quantifies how
much of a model's failure is *retrieval/framing* vs. *reasoning*.

### 2.6 Load-time invariants (the harness asserts these before scoring; [`validate.py`](validate.py) enforces them)

- category weights sum to 1.0; checkpoint weights sum to 1.0;
- every checkpoint P1..P3, E1..E6, C1..C5, S1..S3 is present; every category is populated;
- every gate's `fired_by` + `dependents[]` (and `voids_positive` / `cascade_dependents`) resolves to real checkpoint/atom ids;
- every deterministic atom's `tolerance` key resolves in the `tolerances:` block; every `per_figure` template's `figures[].points` sum equals its declared `points`;
- **no atom is double-categorized**, and **entailment category ⇔ entailment grader** (bidirectional);
- total atoms = **109**, positive mass = **+353**, penalty mass = **−135** (global drift-detector on YAML edits);
- **per-checkpoint mass assertion** — each checkpoint's (+mass, −mass) matches the §3.3 table, so
  per-checkpoint drift is caught, not just the global total.

> **Static vs. materialized mass (F6).** The masses above are the **static template ceiling**
> (all per-figure figures present). For a given case the harness first **prunes** any manifest-N/A
> figure from *both* numerator and denominator (§5.1), so the per-CASE positive mass is the
> post-prune mass; `raw_pos(k)` is computed on the materialized figure set, and `AllPass` quantifies
> over the in-scope (non-N/A) atoms only.

---

## 3. The six weighted categories + the 17 checkpoint weights

### 3.1 Category weights (govern the SECONDARY rollup; sum = 1.0)

These are the six PLAN.md categories. They weight the **diagnostic rollup**, not the headline.

All counts/masses below are the exact [`validate.py`](validate.py) output (static template; `per_figure`
expansion changes runtime totals).

| Category | Weight | Atoms | +mass / −mass | Justification |
|---|---:|---:|---:|---|
| **numerical** | **0.26** | 29 | +98 / −16 | Largest. The desk math (P2 per-share/cross-doc, C1–C5) is what most directly misleads a PM when wrong, and it is the most objectively gradeable (deterministic tolerance), so it carries weight without importing judge noise. (−16 absorbs the new `C3.n_bridge_skipped` omission penalty.) |
| **extraction** | **0.22** | 30 | +101 / −62 | Second. Every downstream number consumes an extracted figure; a hallucinated or mis-scaled operand poisons the math. Below numerical only because the P1/P2 hard gates already remove the worst frame errors before this pool is scored. The **−62** is the new heaviest commission+omission penalty pool — the E1–E5 fabrication hooks (`E*.n_halluc`, −8 each) and the must-have/omission penalties (F4/F5) live here. |
| **reasoning** | **0.20** | 17 | +71 / −6 | The senior signal that separates a domain expert from a calculator (P3 scope/sector, the S1/S2 read, C1/C3 judgment legs). Below the deterministic pair because it depends on the numbers being right first and is judge-graded. (Gains `S2.grounding`, re-tagged from entailment — F8.) |
| **entailment** | **0.14** | 9 | +36 / −4 | FinanceBench-grade citation discipline and the anti-hallucination backstop. Deliberately lighter than raw extraction so the same figure is not double-counted at full freight across its value leg and its citation leg. (9, not 10: `S2.grounding` moved to reasoning — F8 — so every entailment-category atom now uses the entailment grader.) |
| **calibration** | **0.12** | 17 | +32 / **−47** | First-class per the project thesis, not an afterthought. Smaller positive mass because it concentrates in fewer checkpoints (E4, E5, E6, S1–S3), but it carries the **heaviest negative *concentration*** — fabrication, over-refusal, vague-hedge, new-figure, and the new `S3.n_no_uncertainty` omission penalty (−3, raised from −2 so silence about uncertainty is at least as costly as the attempted-but-vague `S3.n_blanket_hedge` hedge, F10) — so a confidently-wrong memo can drive a case below zero before the suite clip. |
| **structure** | **0.06** | 7 | +15 / −0 | Smallest **on purpose**. A traceable record is what makes everything else gradeable, but format must never buy a model out of a wrong number. 0.06 is the anti-gaming ceiling: a perfectly-formatted, confidently-wrong memo cannot clear ~0.06 on structure alone. |
| **Total** | **1.00** | **109** | **+353 / −135** | |

### 3.2 Checkpoint weights (the PRIMARY headline; sum = 1.0)

In `meta.checkpoint_weights`. Stage subtotals: **Planning 0.13 · Extraction 0.36 · Calculation
0.325 · Synthesis 0.185.** Extraction carries the most mass because it is the widest stage and every
later number traces to it; planning is light in *weight* but heaviest in *consequence* (its gates
zero everything downstream — see §4).

| Stage | Checkpoint | `W_k` | | Stage | Checkpoint | `W_k` |
|---|---|---:|---|---|---|---:|
| Planning | P1 — pin period *(hard gate)* | 0.040 | | Calculation | C1 — growth + Δshares | 0.060 |
| Planning | P2 — lock scale *(hard gate)* | 0.040 | | Calculation | C2 — margins(bps) + FCF | 0.065 |
| Planning | P3 — scope + basis *(scoped gate)* | 0.050 | | Calculation | C3 — EPS bridge | 0.075 |
| Extraction | E1 — income statement | 0.075 | | Calculation | C4 — QoE ratios | 0.060 |
| Extraction | E2 — segments + shares | 0.065 | | Calculation | C5 — beat/miss + tie-out | 0.065 |
| Extraction | E3 — non-GAAP + OCF/capex | 0.070 | | Synthesis | S1 — direction calls | 0.060 |
| Extraction | E4 — guidance | 0.045 | | Synthesis | S2 — material changes + QoE | 0.070 |
| Extraction | E5 — working capital | 0.045 | | Synthesis | S3 — calibrated bottom line | 0.055 |
| Extraction | E6 — refusal probe | 0.060 | | | **Sum** | **1.000** |

### 3.3 Checkpoint → category map (all 17)

Each checkpoint's atoms are tagged into categories; cross-checkpoint pooling is what makes the
rollup. The dominant category per checkpoint is **bold**.

All per-checkpoint masses below are the exact [`validate.py`](validate.py) per-checkpoint table
(static template). Each row's total is the load-time per-checkpoint mass assertion (§2.6).

| Checkpoint | +/− mass | Categories present (atom point mass by category) |
|---|---:|---|
| **P1** | +23 / 0 | **extraction** (+18) · entailment (+3) · structure (+2) |
| **P2** | +21 / 0 | **extraction** (+11) · numerical (+8) · entailment (+2) |
| **P3** | +21 / −3 | **reasoning** (+15, −3) · extraction (+4) · structure (+2) |
| **E1** | +25 / −18 | **extraction** (+17, −14) · entailment (+8, −4) |
| **E2** | +29 / −17 | **extraction** (+20, −17) · entailment (+6) · structure (+3) |
| **E3** | +27 / −15 | **extraction** (+18, −15) · entailment (+6) · reasoning (+3) |
| **E4** | +18 / −8 | **extraction** (+6, −8) · reasoning (+4) · calibration (+4) · entailment (+4) |
| **E5** | +14 / −8 | **extraction** (+7, −8) · entailment (+4) · calibration (+3) |
| **E6** | +19 / −18 | **calibration** (+16, −18) · entailment (+3) |
| **C1** | +22 / −2 | **numerical** (+16, −2) · reasoning (+4) · structure (+2) |
| **C2** | +21 / −4 | **numerical** (+21, −4) |
| **C3** | +20 / −10 | **numerical** (+17, −10) · reasoning (+3) |
| **C4** | +15 / 0 | **numerical** (+15) |
| **C5** | +23 / 0 | **numerical** (+21) · structure (+2) |
| **S1** | +17 / −9 | **reasoning** (+15, −3) · structure (+2) · calibration (−6) |
| **S2** | +22 / −9 | **reasoning** (+22) · calibration (−9) |
| **S3** | +16 / −14 | **calibration** (+9, −14) · reasoning (+5) · structure (+2) |

> **The hybrid split, made concrete.** Every extracted figure yields **two** atoms in **two
> different category pools**: a `*.value`/`*.values` atom (category `extraction`, deterministic) and
> a `*.cite` atom (category `entailment`, entailment grader). Right-number/wrong-citation lands as
> *extraction met, entailment not-met* — cleanly distinguished from a hallucination, where both miss,
> and from clean extraction, where both pass. The same figure is never scored twice in the same pool.

---

## 4. The gating model

Some errors make everything downstream unusable regardless of the arithmetic. HealthBench has no
gate; finance needs one. Gates are **deterministic predicates on gold**, encoded in `gates[]` with an
explicit `dependents[]` blast radius. A fired gate sets **`m = 0` on every dependent atom *before*
inner pooling**. Crucially, **zeroed atoms stay in their checkpoint denominators** — so gating
*lowers* the affected checkpoint scores rather than removing the work, and the cost of an upstream
slip is visible, not hidden.

### 4.1 The three tiers

| Tier | Gate | Fires when | Blast radius (`dependents[]`) |
|---|---|---|---|
| **Hard** | `GATE.P1` | wrong fiscal period / period-end / filing type (Q4-as-standalone-10-Q) / year-ago column read as current / wrong source document | **E1, E2, E3, E4, E5, E6, C1, C2, C3, C4, C5, S1, S2, S3** (the whole chain) |
| **Hard** | `GATE.P2` | declared scale off by 1000× / wrong currency / per-share × aggregate scale / cross-document scale unreconciled | an **explicit atom/figure-id list**: the **aggregate-scaled** value+citation legs in **E1–E5** (`E1.value:aggregate`, `E1.cite:aggregate`, `E1.gaap_distinct`, `E2.segments`, `E2.wavg_diluted`, `E2.nongaap_diluted`, `E2.prioryr_shares`, `E2.cite`, `E3.addbacks:aggregate`, `E3.taxeffect_line`, `E3.ocf_capex`, `E3.cite`, `E4.ranges:aggregate`, `E5.values`, `E5.cite`) **plus all of C1–C5**. **Excludes** the per-share/EPS sub-figures (already in dollars, P2.3): `E1.value.gaap_basic_eps` / `gaap_diluted_eps` (+ their cites) and `E4.ranges.guidance_eps_*`. The S1–S3 clause is **dropped** (not a deterministic predicate; `S1.n_contradiction` already catches scaled-number contradictions). |
| **Hard** | `GATE.FABRICATION` | an extraction atom returns a value with **no citation** that is **not in the filing** (hooks on **E1–E5** value legs: `E*.n_halluc`), OR a confident fabricated value on a genuinely-undisclosed E6 probe (`E6.n_fabricate`) | **voids the POSITIVE** value+cite legs of the fabricated figure (`voids_positive: [self.value_leg, self.cite_leg]`, m=0) **and** the penalty applies its negative in the numerator — so the figure is hard-zeroed **once** and penalized **once**. **Cascades** the whole chain (GATE.P1/P2) **only** when the fabricated *field* is the period/scale/source frame (`cascade_if`). |
| **Scoped** | `GATE.P3` | `consensus_basis` committed ≠ basis of the snapshot, OR designated mean/median statistic dropped/swapped | **C5, S1 only** (the beat/miss chain that inherits the basis); C1–C4 GAAP-internal math stands |
| **In-checkpoint** | `GATE.C1SIGN` | a growth rate or the Δ-share-count **sign is flipped** | **C1 atoms only**; does **not** gate downstream |
| **In-checkpoint** | `GATE.C5SIGN` | a beat called a miss (or vice versa) — a **sign flip** at the directional call (`C5.direction` only) | **C5 atoms only**; does **not** gate downstream |

Notes that keep this consistent with Phase 1 and the YAML:
- **`GATE.P2` is atom-granular (F2), not checkpoint-granular.** It zeros only the **aggregate-scaled**
  value+citation legs (above), which is why a correctly-read **per-share/EPS** figure survives the gate
  (Phase-1 P2.3: per-share figures are already in dollars, *not* scaled). The blast list is byte-for-byte
  the YAML `GATE.P2.dependents`.
- **`GATE.FABRICATION` separates detection from blast radius (F4).** Detection is the negative penalty
  atom (`E*.n_halluc` −8 / `E6.n_fabricate` −10), applied in the numerator — untouched. The blast radius
  **voids the positive credit** of the fabricated figure's value+cite sub-atoms only (m=0). A fabricated
  figure is therefore hard-zeroed **once** (its positive voided) and penalized **once** (its negative
  applied) — never double-counted beyond the single intended hard-zero. It **cascades** the whole chain
  (via `cascade_dependents` → GATE.P1/P2) **only** when the fabricated field *is* the period/scale frame.
- **`GATE.C5SIGN` fires on `C5.direction` only (F16).** A GAAP-vs-street **basis** mismatch *at* the
  checkpoint is handled by `C5.basis_guard` as a **normal penalty atom** (and the basis decision is
  already the P3 scoped gate) — it does not fire the in-checkpoint sign gate.
- **C3 has NO wrong-sign in-checkpoint fail.** A GAAP→non-GAAP bridge has no single directional
  conclusion to invert, so there is no `GATE.C3SIGN`. C3 is purely step-checked (§5.1).
- The S1 verbal directional error is **not** a gate; it is caught by the `S1.n_contradiction`
  penalty atom (judge contradiction operator, now checked against **GOLD_NUMBERS** not the memo's own
  C5 — F9), so a flipped narrative call is penalized inside S1 without a separate gate.

### 4.2 All-Pass, ungated, gap

- **`CaseScore_ungated`** — gates **not** applied; every checkpoint contributes its raw partial.
- **`CaseScore_gated`** — gates applied (dependents zeroed), then pooled and weighted.
- **`AllPass ∈ {0,1}`** — 1 iff **every** gating condition holds **AND** every positive atom is met
  (value + entailment both, all correctness ops, no contradiction op fired, no negative atom met).
  This is the Vals-AI All-Pass: a clean per-checkpoint AND.
- **`GAP = ungated − gated`** — reported first-class. It quantifies how much "almost right" inflates
  a naive average: a model that nails the arithmetic but misreads "in thousands" as dollars shows a
  *large* gap (high ungated, near-zero gated), which is exactly the diagnostic the eval exists to surface.

### 4.3 Worked mini-example

A model analyzes an **asset manager**. It pins the period correctly (P1 ✓) but reads the income
statement **"in thousands" as "in millions"** — a 1000× scale slip. Downstream it does the
*arithmetic* flawlessly: every growth rate, margin-delta, and ratio is internally consistent and would
be right *if the scale were right*. It also nails the synthesis read. Because the issuer is an asset
manager, **gross profit, inventory, and COGS are N/A** and pruned from the materialized figure set
(F6); the per-share/EPS figures are read correctly (they are already in dollars — not scaled).

The exact numbers below are produced by [`worked_example.py`](worked_example.py) against the **final**
gate semantics (F2 value-atom scope + F6 prune), not asserted by hand:

**Ungated** (gates off): P1 = 1.000, P2 = 0.619 (the scale atom `P2.1` missed; per-share P2.3 + the
rest fine), E1 = 0.720 / E2 = 0.310 / E3 = 0.407 / E5 = 0.636 (the **aggregate** value legs fail the
tolerance band after scale-folding while the **EPS** legs and the citations survive), E4 = 0.833 and
E6 = 1.000, C1–C4 = 1.000 (scale-invariant ratios/growth/margins are internally consistent), C5 = 0.652
(the scaled-$ revenue beat/miss and segment tie-out fail; the absolute-EPS beat/miss survives), and
S1–S3 = 1.000 → **`CaseScore_ungated` = 0.831**.

**Gated:** `GATE.P2` fires → set `m = 0` on the **aggregate-scaled value+cite legs of E1–E5 and all of
C1–C5** (they stay in their denominators). E1 → 0.323, E2 → 0.103, E3 → 0.185, E5 → 0.273, and
C1–C5 → 0.000; P1, P2, P3, E4, E6, and S1–S3 survive (E4's revenue legs already failed ungated, so the
gate adds nothing there; the EPS legs survive). → **`CaseScore_gated` = 0.453**.

**Result:** **`GAP = 0.378`**. `AllPass = 0` (a gate fired). The taxonomy log records `unit_scale` at
P2, with the *raw unclipped* C-stage checkpoint values driven to 0 and the retained raw E-stage values
marking those steps strictly worse than blanks. The headline correctly says: *this model can do the
math but cannot be trusted to read a statement header* — the single most important thing to know about
it. (The gap is large but **not** maximal precisely because the synthesis, the per-share figures, and
the scale-invariant ratios legitimately survive; an honest gate does not pretend a competent reasoner
is incompetent everywhere.)

---

## 5. Tiered scoring + "what counts as a ZERO"

### 5.1 The tiers (how `m` is set)

- **Deterministic value atoms** — `m = 1` iff the model's value is within the figure-type tolerance
  band **after scale-folding** (the locked scale is applied to the number *before* comparison, so a
  thousands/millions slip deterministically zeros it); else `m = 0`. **No partial credit on a single
  value atom** — partial credit comes from *how many* per-figure sub-atoms pass. The harness expands a
  compound value atom (e.g. `E1.value`, `E2.segments`, `E3.addbacks`, `E5.values`) into one sub-atom
  per gold figure, each carrying its own `tolerance` key (EPS rows → `eps`, aggregates → `aggregate`).

  | Figure type | `tolerance` key | Band |
  |---|---|---|
  | EPS (reported or computed) | `eps` | ± \$0.01 |
  | Growth rates & margin **levels** | `growth_rate` / `margin_level` | ≤ 0.1 pp |
  | Margin **deltas** (YoY/QoQ) | `margin_delta_bps` | ≤ 15 bps **and** internally consistent with the model's own two levels |
  | Effective-tax-rate **level** | `ratio` | ≤ 0.5% relative |
  | Effective-tax-rate **YoY delta** (F12) | `tax_rate_delta_pp` | **floor-RSS**: ≤ max(0.15 pp, 0.5% × eff_rate × √2) — the 0.15 pp is a **floor** that widens with the rate **and** internally consistent with the model's own two rate levels |
  | As-reported aggregates | `aggregate` | exact to reported precision, or ≤ 0.5% relative |
  | Free cash flow (derived) | `fcf` | ≤ 0.5% relative on the computed difference |
  | Beat/miss magnitude (F13) | `beat_miss_eps` / `beat_miss_rev` | **EPS ± \$0.01 absolute only**; revenue ≤ 0.5% relative, **both** absolute and percent |
  | QoE ratios (DSO/DIO, OCF/NI) | `ratio` | ≤ 0.5% relative |

  > The **15-bps** margin-delta band is the root-sum-square of two ±0.1pp (10-bps) level tolerances:
  > two in-tolerance levels can legitimately produce a delta off by ~14 bps, so a tighter band would
  > fail a model whose levels each pass. The delta must *also* equal the model's own (current − prior)
  > margins — an internal-consistency check that blocks a lucky-but-incoherent delta.
  >
  > **The effective-tax-rate YoY delta gets RSS treatment too, but as a FLOOR (F12).** `C4.efftax` is
  > split into a **level** check (`ratio`, 0.5% relative on each of the two rate levels) and a **delta**
  > check (`tax_rate_delta_pp`). **The parallel to the margin delta is NOT exact:** the margin *level*
  > band is *absolute* (±0.1 pp), so its RSS is the fixed 0.15-bps-scale value; but the effective-tax
  > *level* band is **relative** (0.5% of the rate), so its percentage-point equivalent **scales with the
  > rate** and the true RSS of two relative level bands is `0.5% × eff_rate × √2` pp. A *fixed* 0.15 pp
  > band is only ≈ RSS near a ~21% rate and is slightly **tighter** than the true RSS at higher rates.
  > So `tax_rate_delta_pp` is encoded as a **floor-RSS band** = `max(0.15 pp, 0.5% × eff_rate × √2)`: the
  > 0.15 pp is a **floor** that approximates RSS for typical ~20–25% effective rates and **widens with
  > the rate**, never failing a model whose two levels each legitimately pass. As with the margin delta,
  > the delta must **also** equal the model's own (current − prior) effective rates — the
  > internal-consistency leg.
  >
  > **EPS beat/miss is absolute-only (F13).** Phase-1 specifies *EPS ± \$0.01; revenue ≤ 0.5% relative*
  > — it never asked for an EPS-percent beat/miss, which is unstable near a breakeven/loss-quarter base
  > and collides with `C5.near_zero`. So `C5.beatmiss` grades EPS on the absolute band only (the
  > removed `eps_beatmiss_pct` points fold into `eps_beatmiss_abs`); revenue keeps both absolute and
  > percent.

- **Split (per-row) and prune (N/A) expansion — the rounding convention (F3 / F6 / F20).** A
  `per_figure` template with an `expand: per_*_row` row (`E2.segments` 5 pts, `E3.addbacks` 6 pts,
  `C3.addbacks_steps` 6 pts) **splits its pool evenly** over the *N* disclosed rows the manifest
  supplies: `points_per_row = pool / N` — *no fixed per-row constant* (the old `C3` fixed 2-pts-per-row
  broke the denominator for any case with N ≠ 3, which the loss-quarter / discrete-tax cases require).
  A `prune: per_manifest` template (`E1.value`/`E1.cite`, `E4.ranges`, `E5.values`/`E5.cite`) **removes**
  any manifest-N/A figure from *both* numerator and denominator before pooling; the matching
  "correctly-marked-N/A" atom (`E1.sector_na`, `E5.sector_na`, `C4.sector_na`) is then the only scored
  atom for that figure. **Convention:** split sub-atom points are kept **exact (rational)** in
  computation — `5/3`, `6/2`, etc. are never rounded mid-pool — so the per-checkpoint denominator
  invariant `raw_pos(k)` holds exactly for any *N*; **only the final reported checkpoint / case / suite
  scores round to 3 decimals.**

- **Entailment atoms (F14)** — a separate 3-way NLI grader fed the model's **candidate evidence span**
  (the cited text) so it verifies support **directly**, using the **gold pointer only to locate** the
  figure (anchoring-resistant): `entailed → m=1`; `neutral → m=0`; `contradicted → m=0`. The **−4
  plausible-but-wrong-citation penalty currently applies to the E1 income-statement figures
  (`E1.n_wrongcite`)** — the only such atom in the set — so a `contradicted` E1 cite is m=0 **and**
  `E1.n_wrongcite` (−4). On the **other extraction cite legs (E2–E5, `E6.twin_cite`) a wrong citation
  loses the entailment positive (m=0) WITHOUT the additional −4**; extending an explicit `n_wrongcite`
  atom to E2–E6 is a noted **Phase-4 option** (it would change the frozen mass, so it is deferred, not
  silently applied). **If only the gold pointer is available** (the model supplied no candidate span),
  `neutral` and `contradicted` collapse into a single **"not-entailed"** (`m = 0`) and (for E1) the **−4
  `E1.n_wrongcite`** is reserved for a **deterministic document/page mismatch** the harness detects (not
  a soft judge boundary). Scored independently of the value (§3.3).

- **Judge atoms** — binary `met`/`not-met` per the correctness or contradiction operator. The judge
  **never re-derives a number**; it checks prose against the supplied deterministic gold (see §6, judge.md).

- **Refusal atoms (E6 + the N/A legs)** — label and twin-retrieval are deterministic; the refusal
  *reason* is bucketed A/B/C/D by the refusal grader (§7). (See §6 — "refusal" is the operational name
  for Phase-1's *label-deterministic + reason-judge* composite, F15.)

- **Step-checked C3 bridge** — the one checkpoint with genuine intra-figure partial credit. The
  harness expands: `C3.s0` start-from-GAAP-NI (+2); `C3.addbacks_steps` the 6-pt pool **split evenly
  over the *N* disclosed add-backs** (`6/N` per sub-atom, exact — F3), each handled on its
  pre/after-tax basis; `C3.tax_step` disclosed tax-effect line (+3); `C3.share_step` correct
  diluted-share basis (+3); `C3.final` reproduce reported non-GAAP EPS ±\$0.01 (+3); plus penalties
  `C3.n_blended` blended-rate shortcut (−3), `C3.n_badshares` wrong share basis (−3), and the new
  **omission** penalty `C3.n_bridge_skipped` (−4, F5) when the case requires a bridge and the model
  produces none. A bridge that nails every step but lands \$0.02 off loses **only** `C3.final` and the
  failure localizes to the exact step — never to a vague "wrong EPS".

### 5.2 What counts as a ZERO, per category

| Category | An atom (or checkpoint) scores **zero** when… |
|---|---|
| **numerical** | result outside the band after scale-folding; FCF equated to OCF or capex forgotten (`C2.n_fcf_eq_ocf`); margin on a mismatched basis (GAAP income ÷ adjusted revenue); a blended-rate tax shortcut instead of the disclosed line (`C3.n_blended`); **wrong sign** on C1 growth/Δshares (`GATE.C1SIGN` zeros all C1) or C5 beat/miss (`GATE.C5SIGN` zeros all C5); or the figure is gated by P1/P2 upstream. **C3 is the exception** — graded step-wise, so one wrong step zeros only that step. |
| **extraction** | value outside tolerance after scale-folding; a thousands/millions slip; an N/A item fabricated; a GAAP line silently replaced by the adjusted line; basic/diluted EPS confused; period-end cover-page shares used for weighted-average (`E2.n_periodend`, −5); a hallucinated figure not in the filing (the E1–E5 `E*.n_halluc`, −8, fire `GATE.FABRICATION`); a **required + disclosed must-have figure silently omitted** (the omission penalties `E1.n_omit_musthave` / `E2.n_omit_nongaap_diluted` / `E3.n_omit_musthave`, −4); or gated by P1/P2. |
| **entailment** | the cited span does not support the value (NLI neutral / "not-entailed"); the wrong document (release vs. 10-Q per the source map); an empty/absent citation on a figure that requires one; or a confident **plausible-but-wrong** cite the harness flags as a document/page mismatch (NLI contradicted → m=0; on the E1 income-statement legs this **also** fires `E1.n_wrongcite`, −4 — the only such atom; on E2–E6 cite legs a wrong cite loses the entailment positive without the extra −4, with an explicit E2–E6 `n_wrongcite` noted as a Phase-4 option). |
| **reasoning** | a required gold material change / directional call is missing; a swing factor mis-attributed (calling a discrete-tax or buyback-driven beat "operating strength"); a directional call that contradicts **GOLD_NUMBERS** beat/miss (F9); consensus restated **without** computing the beat/miss (`S1.n_restate`, −3); a hallucinated red flag (`S2.n_halluc_flag`, −5); or a claim resting on a number with no upstream checkpoint (`S2.grounding` not-met — now reasoning, F8). |
| **calibration** | a **fabricated value on the genuinely-undisclosed probe** (`E6.n_fabricate`, −10, G=0, hard); **over-refusing the answerable twin** (R drops); a **vague "I can't verify"** with no grounded reason (`E6.n_vaguehedge` / `S3.n_blanket_hedge`) — scored as **over-refusal, NOT caution** (and **mutually exclusive** with the matching lost positive, F10); importing a prior-period/memorized number (`E6.n_import`, −5); **writing nothing about uncertainty where a gap exists** (`S3.n_no_uncertainty`, −3, F10); a new figure introduced in S3 (`S3.n_newfigure`, −4); or an overconfident bottom line hiding uncertainty (`S3.n_overconfident`, −4). Calibration credit **requires** a specific grounded reason naming *why* absent and *which* statement would carry it. |
| **structure** | a required deliverable block absent — no pinned header (`P1.6`), no scoping record (`P3.5`), calculations shown with no operands/formula (`C1.structure`), S1 calls buried in prose instead of discrete labels (`S1.structure`), S3 not 3–6 sentences (`S3.structure`); or **padding** — irrelevant figures scoped beyond the gold list (`P3.n1`, −3, anti-verbosity guard). Capped at 0.06 weight so format can never buy out a wrong number. |

**The omission ladder (F5).** Before these edits, a positive-mass-only denominator with commission-only
penalties meant "answer the easy figures, stay silent on the hard ones, never hedge" strictly dominated
— the eval trained *silent under-reporting*. Four deterministic **omission** penalties close that hole:
`E1.n_omit_musthave` (total revenue or GAAP diluted EPS), `E2.n_omit_nongaap_diluted` (a disclosed
distinct non-GAAP diluted count), `E3.n_omit_musthave` (adjusted EPS or OCF), and `C3.n_bridge_skipped`
(no GAAP→non-GAAP bridge where one is required) — each **−4**. They fire **only** when the figure is
**required + disclosed in gold and the model provides no value and no attempt** — *never* on a
genuinely-undisclosed item (those route through E6 and are *rewarded*), so calibrated refusal is
untouched. The resulting per-must-have-figure incentive order is therefore:

> **correct (+pos) ▸ wrong mis-read (lose +pos) ▸ omission (lose +pos −4) ▸ fabrication (lose +pos −8).**

**What counts as an "attempt" (anti-gaming).** An "attempt" at a required+disclosed figure requires a
**PARSEABLE candidate numeric value** (for `C3.n_bridge_skipped`, a parseable candidate derivation). An
empty string, a placeholder, or a **contentless non-answer** (e.g. "N/A — see 10-Q", "—", "TBD") on a
figure that **IS disclosed** counts as an **OMISSION** — it incurs the omission penalty (−4) and cannot
dodge it by masquerading as a refusal. This closes the fake-attempt vector. The mirror case is rewarded:
a correct "**not disclosed**" on a **genuinely-ABSENT** figure is *not* an omission — it routes through
the **E6 path** (the calibrated-refusal probe, §7) and earns calibration credit. The two are
distinguished by gold: omission penalties fire only where the figure is required **and disclosed**; the
E6 reward fires only where it is genuinely absent. (The same `S3.n_no_uncertainty` attempt rule applies
in the bottom line: a contentless uncertainty placeholder where a genuine gap exists is the omission, −3.)

There is deliberately **no S2 omission penalty** — the per-key-point positives in `S2.material_changes`
already cost silence, and a second omission atom there would be double-jeopardy.

---

## 6. Deterministic vs. judge grading — the split, and where each criterion lives

The cardinal rule: **numeric truth lives entirely in the Python checker; the judge grades only
free-form prose and never recomputes.** Each criterion is tagged with the *cheapest grader that can
score it correctly*.

Exact static grader counts (from [`validate.py`](validate.py); **`per_figure` expansion changes the
RUNTIME totals** as each template materializes into one sub-atom per gold figure):

| `grader` | What it scores | Lives in | Static atom count |
|---|---|---|---|
| **deterministic** | every value, tolerance, scale-fold, sign, and arithmetic check; P1/P2/P3 frame predicates; the C3 bridge steps; all of C1–C5 numeric; the omission penalties | Python checker in [`../harness/`](../harness/) | **65** |
| **entailment** | does the model's cited candidate span actually support its value? (3-way NLI, fed the candidate span + gold pointer) | entailment grader, prompt in [`judge.md §4`](judge.md) | **9** |
| **judge** | free-form synthesis (S1/S2/S3), the P3/E3/E4 reasoning legs, `S2.grounding`, the E6 reason + vague-hedge, and the contradiction operators | LLM judge, prompt in [`judge.md §1–3`](judge.md) | **29** |
| **refusal** | the E6 label/twin/reason buckets (E6.label, E6.twin, E6.n_fabricate, E6.n_import), E4.refuse_noguide, and the sector-N/A leg (E5.sector_na) | refusal grader, prompt in [`judge.md §5`](judge.md) | **6** |

> **"refusal" is not a fourth grader family (F15)** — it is the **operational name for Phase-1's
> "label-deterministic + reason-judge" composite**: the NOT_DISCLOSED label and the answerable-twin
> retrieval are graded **deterministically**, the refusal *reason* is graded by the **judge**, and the
> two axes are aggregated by `LLMC_β` (§7). It is broken out as its own `grader` value only so the
> harness routes E6/N-A atoms to the bucketing prompt; no separate model or contract is implied.

**The judge contract** (full prompt in [`judge.md`](judge.md), frozen at `judge_version: 2.1.0`):
one atomic criterion per call; temperature 0; `max_tokens 384`; strict JSON
`{criterion_id, reasoning, evidence_quote, criteria_met}` with **reasoning before the verdict** so the
rationale constrains the label. The judge is given the **computed gold numbers** and the **gold
citation spans** — never the raw filings — so it cannot and must not re-derive. For a **negative
atom**, `criteria_met = true` means the *bad behavior is present*; the **harness, not the judge,
applies the point sign**. Every met=true positive **must quote the supporting memo span** or it is not
met (kills unsupported praise). The judge is from a **different model family** than the system under
test (self-preference-bias mitigation). The **contradiction operator** is an NLI check, not
arithmetic: prose says "miss" where gold shows a beat → contradiction present.

**Phase-5 calibration contract:** the judge is *not* ground truth. On a hand-graded stratified sample,
report **macro-F1** (≥ the human inter-rater band; HealthBench's GPT-4.1 ≈ 0.709) **and Cohen's κ**
(≥ 0.8 strong, 0.6–0.8 substantial, **< 0.6 = rework, do not publish**), plus temp-0 run-to-run
stability. **Any edit to the prompt bumps `judge_version` and invalidates prior calibration.**

---

## 7. Calibrated-refusal scoring (both directions)

Calibration is graded as a **first-class positive in both directions** and is the category with the
heaviest negative mass (**−47**). The **E6 headline** is the FailSafeQA F-beta (F1 — the one checkpoint
whose headline is not `awarded/raw_pos`):

```
checkpoint_score(E6) = LLMC_β(R, G) = (1 + β²) · R · G / (β² · G + R)     with  β = 0.5
  R = compliance on the ANSWERABLE TWIN ∈ {0, 0.5, 1}   (over-refusal axis: did it retrieve the buried figure?)
      value-in-tolerance AND cited → 1 ;  value-right/cite-wrong (or vice versa) → 0.5 ;  twin refused/wrong → 0
  G = grounded-refusal on the genuinely-UNDISCLOSED probe ∈ {0, 0.25, 1}   (fabrication axis)
      bucket A grounded refusal → 1 ;  bucket B vague hedge → 0.25 ;  bucket D imported → 0.25 ;  bucket C fabrication → 0
```

β = 0.5 (not 0.2) is a documented choice: a confident wrong number in a PM-facing memo is the costlier
error, so fabrication is punished harder than a missed buried figure — **but over-refusal still hurts
meaningfully.** Every "not disclosed" probe is paired with an **answerable twin**, so refusing
*everything* drops **R to 0** → `E6 = 0`: a refuse-all policy cannot farm safety credit. `AllPass(E6)`
= grounded refusal **and** twin retrieved (`LLMC_β = 1`). The E6 ± atoms still feed the **calibration
category rollup** and the **failure taxonomy**; they simply do not form the E6 *headline*.

The E6 refusal grader buckets each answer (prompt in [`judge.md §5`](judge.md)):

| Bucket | Behavior | Scoring | G |
|---|---|---|---|
| **A — grounded refusal** | declines **and** gives a specific reason consistent with the gold (names *why* absent / *which* statement would carry it) | **credit** → `E6.reason` met, drives **G** | **1** |
| **B — vague hedge** | declines with a generic ungrounded hedge ("I can't verify", "data may be incomplete") | **over-refusal** → `E6.n_vaguehedge` met (**XOR** the lost `E6.reason` positive — F10, never both). **Explicitly not caution.** | **0.25** |
| **C — fabrication** | supplies a confident value for the undisclosed item | **hard zero** → `E6.n_fabricate` (−10), `GATE.FABRICATION` | **0** |
| **D — imported number** | supplies a prior-period/memorized number to fill the gap | **penalty** → `E6.n_import` (−5) | **0.25** |

The discipline carries into S3: `S3.names_undisclosed` (+5) rewards explicitly naming the
not-disclosed items; `S3.n_blanket_hedge` (−3) penalizes board-wide hedging that ignores what *was*
determinable (**XOR** the lost `S3.calibrated_conf` positive — F10); and `S3.n_no_uncertainty` (−3)
fires when the bottom line says **nothing** about uncertainty where a gap exists, so silence is **not**
cheaper than an attempted-but-vague hedge. **A vague "I can't verify" never scores as caution — it
scores as over-refusal.** Each overlapping hedge fires **at most one** penalty (the F10 mutual-exclusion
rule), and because each checkpoint score is **clipped at 0**, calibration's negative mass cannot drag a
checkpoint below zero — together these bound the asymmetry so silence can never dominate a grounded
attempt. That is the project's explicit anti-sycophancy rule, enforced as signed atoms and in the judge
prompt, so the eval does not accidentally reward confident guessing by penalizing honesty.

---

## 8. Gaming-resistance

| Gaming attempt | Why it fails |
|---|---|
| **Padding / verbosity** | `structure` capped at 0.06 weight; `P3.n1` (−3) penalizes irrelevant scoped figures; the judge is told to grade required content not length and to award met **only with a quoted supporting span**. A longer memo earns nothing. |
| **Blanket hedging / "I can't verify"** | scored as **over-refusal** (G=0.25 on E6, not credit), never as caution; the answerable twin collapses R under a refuse-all policy → `E6 = 0`; `S3.n_blanket_hedge` fires (XOR the lost positive). Credit requires a grounded, specific reason. |
| **Answer the easy figures, stay silent on the hard ones (F5)** | the **omission ladder** — `E1.n_omit_musthave` / `E2.n_omit_nongaap_diluted` / `E3.n_omit_musthave` / `C3.n_bridge_skipped` (−4 each) fire on a **required + disclosed** figure the model neither values nor attempts, so silence on a must-have costs *more* than an honest mis-read (lose +pos) and only fabrication (−8) is worse. These never touch a genuinely-undisclosed item (E6 rewards that), so calibrated refusal is untouched. |
| **Restating consensus without computing (F11)** | `S1.reported_dir` (+7) is **awarded only if a non-empty, non-gated model C5 derivation accompanies the memo** — copying the gold delta into prose with no computed C5 cannot earn it; `S1.n_restate` (−3) fires if the prose presents consensus as the result; `S1.n_contradiction` (−6) fires if the verbal call conflicts with **GOLD_NUMBERS** (F9 — gold, not the memo's own possibly-wrong C5). |
| **Plausible-but-wrong citation (F14)** | the entailment leg is scored **separately** from the value and the entailment grader verifies the model's **candidate cited span** directly (gold pointer used only to locate), so a confident wrong cite returns `contradicted`/`not-entailed` → citation atom m=0. The −4 plausible-but-wrong-citation penalty currently applies to the **E1 income-statement figures (`E1.n_wrongcite`)** — the only such atom — so the E1 cite loses its entailment points **and** takes the −4 (or, with no candidate span, a deterministic document/page mismatch); on the **E2–E5 / `E6.twin_cite`** legs a wrong cite loses the entailment positive (m=0) **without** the extra −4 (an explicit E2–E6 `n_wrongcite` is a noted Phase-4 option, deferred to keep the frozen mass). |
| **Two offsetting errors hiding in a final number** | C3 is **step-checked** and `C3.final` requires internal consistency with the model's own bridge inputs; `C2.deltas_bps` must equal the model's own two margin levels. |
| **Judge re-deriving and "correcting" a right answer** | the judge is **forbidden** to recompute and consumes the deterministic gold only — numeric truth lives entirely in the Python checker. |
| **Gaming the gate** (one cheap upstream pass to unlock everything) | gates are **deterministic on gold** and cannot be talked past; the Oracle-vs-end-to-end split and the reported `GAP` surface any gate-masking. |
| **Self-preference / verbosity bias in the judge** | cross-family judge, temp 0, atomic content-specific criteria, mandatory evidence quote, and the Phase-5 macro-F1/κ calibration gate. |

The **HealthBench denominator asymmetry** (negatives in the numerator, excluded from the denominator,
`clip_per_case: false`) gives all of these penalties real bite: a confidently-wrong checkpoint goes
negative before the per-checkpoint clip, and the **retained raw unclipped value** records *how* wrong
in the taxonomy — a fabrication-heavy answer is logged as strictly worse than a blank one.

---

## 9. Forward links

- **[`criteria.yaml`](criteria.yaml)** — the 109 atomic criteria, six gates with `dependents[]`,
  `meta.weights` (category) + `meta.checkpoint_weights` (the 17), the `tolerances:` block, and the
  per-atom `category` / `grader` / `gate` / `tolerance` / `tags`. The harness loads this file and
  asserts the §2.6 invariants at load.
- **[`judge.md`](judge.md)** — the frozen LLM-judge system prompt, per-checkpoint judge instructions,
  the entailment grader (§4), the refusal grader (§5), five grading few-shots, and the Phase-5
  macro-F1 + κ calibration contract. Pinned to `judge_version: 2.1.0`.
- **[`validate.py`](validate.py)** — the self-contained linter that asserts every §2.6 invariant and
  **prints** the per-category mass table, the per-checkpoint mass table, and the exact static grader
  counts that every derived number in this document and in `judge.md` mirrors. Run it until green after
  any YAML edit. **[`worked_example.py`](worked_example.py)** reproduces the §4.3 gated/ungated/GAP numbers.
- **Phase 3 → [`../cases/`](../cases/)** — 3–5 real SEC filings (10-Q/10-K + release) with a gold
  answer and `{document, page, verbatim string}` citation per checkpoint, deliberately including the
  hard cases the checkpoints were built for: a thousands-vs-millions trap (exercises `GATE.P2`), a
  fiscal-vs-calendar period (`GATE.P1`), a non-GAAP street consensus (`GATE.P3`), a loss-quarter
  issuer whose non-GAAP diluted share count differs from GAAP (E2/C3), a buyback-driven-EPS quarter
  (C1/S2), a discrete-tax-benefit beat (C4/S2), a segment redefinition/restatement (C1), an asset
  manager with no gross-profit line (sector N/A), and a genuine "not disclosed" probe with its
  answerable twin (E6).
- **Phase 4 → [`../harness/`](../harness/)** — the Python checker (value + tolerance + scale-fold +
  entailment), the LLM judge, the label+reason refusal grader, both Oracle and end-to-end run modes,
  and a `python -m …` entry point that emits the scored report: the 17-element checkpoint vector +
  weighted `CaseScore`, the six-number category rollup, and `Suite_ungated` / `Suite_gated` /
  `Suite_AllPass` / `GAP` in both modes.
- **Phase 5 → [`../outputs/`](../outputs/) + `../README.md`** — frontier models run through the suite,
  graded with rationales, the failure-taxonomy table built mechanically from the `tags[]` on every
  fired atom (and the retained raw unclipped checkpoint values), and the judge-vs-expert calibration
  write-up that proves the judge is trustworthy.
