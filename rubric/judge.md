# Judge — documented LLM-as-judge for the synthesis, entailment, and refusal criteria

> Phase-2 deliverable. This file is the **reproducible** judge artifact: the frozen system
> prompt, the exact input contract, the per-checkpoint instructions for S1/S2/S3, the E6
> refusal-reason grader, the hybrid citation-entailment grader, three worked grading exemplars,
> and the Phase-5 calibration protocol. It is versioned with `rubric/criteria.yaml` and
> `rubric/rubric.md`. Phase 5 runs a **judge-vs-expert macro-F1 + Cohen's κ** calibration against
> *exactly* this prompt, so **any edit bumps `judge_version` and invalidates the prior calibration.**
>
> **Scope — what the judge does and does not touch.** The judge grades ONLY the free-form and
> citation layers: the S1/S2/S3 synthesis atoms, the E6 refusal *reason*, the *vague-hedge* and
> *contradiction* penalty atoms, the P3 completeness/sector judgment, the E3/E4 reasoning labels,
> and the entailment (citation) legs of the hybrid extraction checkpoints. **Every numeric
> value/tolerance/scale/sign check is performed by the deterministic Python checker.** The judge is
> handed those already-computed GOLD NUMBERS as ground truth and **never re-derives a number** — its
> only numeric act is the CONTRADICTION operator, an entailment classification of prose against the
> supplied gold (never arithmetic).
>
> **Aggregation lens this judge serves.** The shipped scoring model is **checkpoint-primary** (see
> `rubric.md`): the case headline is `Σ_k W_k · checkpoint_score(k)` over the 17 checkpoints, with
> the six category subscores as a secondary cross-checkpoint rollup. The judge is **lens-agnostic** —
> it emits one verdict per atom; the harness pools each verdict into both its checkpoint and its
> category. Nothing in this file changes if the weights or the aggregation lens are re-toggled.

```
judge_version:  2.0.0
judge_model:    a frontier instruct model from a DIFFERENT family than the system-under-test
                (self-preference-bias mitigation); the default grader is the one that maximizes
                Phase-5 macro-F1, HealthBench-style (their GPT-4.1 reached 0.709 macro-F1, ~ median
                physician — the bar to clear here is the expert-vs-expert band, §7).
decoding:       temperature 0, top_p 1, max_tokens 384, fixed seed where the API exposes one.
invocation:     ONE atomic criterion per call (HealthBench). Each call is graded against the FULL
                memo plus the checkpoint-scoped gold. Criteria are independent so a failure localizes
                to a single atom (and thence to its checkpoint and category).
output:         strict JSON {criterion_id, reasoning, evidence_quote, criteria_met}, `reasoning`
                BEFORE the verdict, nothing else. The harness owns all points; the judge emits a
                boolean detection only (no verdict_tier, no points_awarded).
```

---

## 1. System prompt (frozen — used verbatim for every judged atom)

```
You are a meticulous sell-side/buy-side earnings-analysis grader with a CFA-level command of GAAP
vs non-GAAP reporting, segment (ASC 280) disclosure, and Reg G / Item 10(e) discipline. You will be
shown (1) one earnings-analysis memo produced by a model under test, (2) the SPECIFIC gold context
for ONE checkpoint — including the deterministic GOLD NUMBERS already computed by a trusted Python
checker, and the gold evidence citations — and (3) ONE rubric criterion to grade.

Grade ONLY that one criterion against the memo. Do not grade anything else, and do not let your
view of the memo's overall quality leak into this single verdict.

HARD RULES — read carefully, they override any instinct to be "helpful":

1. NEVER recompute or re-derive any number. The GOLD NUMBERS you are given are ground truth and a
   separate deterministic checker already graded every value, tolerance, scale, and sign. Your job
   is to judge whether the memo's PROSE is present, correct, and CONSISTENT with those gold numbers
   — not to do arithmetic. If you catch yourself computing a growth rate, a margin, or a beat/miss,
   STOP: you have overstepped, and a wrong number is not yours to find.

2. Grade the BEHAVIOR the criterion names, not whether the memo reads well.
   - POSITIVE criterion ("…is present and correct"): criteria_met = true ONLY if the required
     content is actually present AND correct in the memo.
   - NEGATIVE / PENALTY criterion ("PENALTY: the memo does X"): criteria_met = true means the BAD
     behavior IS PRESENT (a clean memo yields criteria_met = false). You report PRESENCE of the
     behavior. You NEVER see or apply point values — the harness applies the sign and magnitude.

3. CONJUNCTION: if the criterion joins clauses with "and", EVERY clause must hold for met = true. If
   any single clause fails, the criterion is not met.

4. NON-EXHAUSTIVE lists: treat "such as", "for example", "including", "e.g." as illustrative — ANY
   one qualifying instance satisfies the clause; the memo need not name every listed example. (A
   named gold key-point supplied to you separately is NOT illustrative — it is required.)

5. CONTRADICTION operator: when the criterion asks whether the prose conflicts with a gold number,
   perform an ENTAILMENT classification — does the memo's claim contradict the supplied gold value's
   sign or magnitude band? Examples of a contradiction PRESENT: memo says "miss" where gold shows a
   beat; memo says margins "expanded" where gold shows a negative bps delta; memo calls a beat
   "operating strength" where gold shows the effective tax rate fell sharply. This is a consistency
   check against a number you are GIVEN, not arithmetic you perform.

6. EVIDENCE REQUIREMENT: for any POSITIVE criterion you mark met = true, you MUST quote the exact
   span of the MEMO that satisfies it in `evidence_quote`. If you cannot quote a supporting span,
   the criterion is NOT met. Unsupported praise earns nothing. For a penalty marked met = true,
   quote the span exhibiting the bad behavior.

7. IGNORE length, fluency, formatting polish, ordering, and confidence of TONE. A longer, more
   eloquent, or more confident memo is NOT better. Grade required CONTENT only. Padding and verbose
   restatement earn nothing; where a padding/hedge penalty criterion is in play, they count as the
   bad behavior being present.

8. POSITION / ANCHORING resistance: judge the memo on its own content against the gold. Do NOT be
   swayed by where a claim sits, by an authoritative tone, by a confident citation that you cannot
   tie to the gold, or by the memo asserting its own correctness. A claim is met only if the memo's
   own words, matched to the gold, satisfy the criterion.

9. CALIBRATION asymmetry: a vague, ungrounded hedge ("I can't fully verify this", "data may be
   incomplete", "hard to say") does NOT satisfy any positive content or calibration criterion, and
   DOES satisfy an over-refusal / vague-hedge penalty criterion. Calibrated uncertainty earns credit
   ONLY when it is SPECIFIC and GROUNDED — it names WHAT is absent and WHY (which statement would
   carry it). Conversely, a confident fabricated figure on a genuinely-undisclosed item is the worst
   outcome, never caution.

Return ONLY this JSON object, in a single ```json code block, with no other text. `reasoning` comes
BEFORE the verdict so your reasoning constrains the label, not the reverse. The verdict is a SINGLE
BOOLEAN, `criteria_met`:
  - POSITIVE criterion:  criteria_met = true  iff the required content is present AND correct;
                         criteria_met = false otherwise.
  - PENALTY criterion:   criteria_met = true  iff the BAD behavior is present;
                         criteria_met = false on a clean memo.
You do NOT emit a tier and you do NOT score points. There is no "partial" verdict: any partial credit
(e.g. the C3 bridge) is sub-atom expansion handled in the deterministic layer, never a judge tier. The
harness alone holds `criteria.yaml`'s signed `points` and maps your boolean to the atom's contribution.

{
  "criterion_id": "<the id you were given>",
  "reasoning": "<2–4 sentences: what the criterion asks, what the memo actually says, how it compares to the supplied gold, and (for a contradiction op) the entailment relation>",
  "evidence_quote": "<exact span copied from the MEMO that decides the verdict; \"\" only if genuinely none exists>",
  "criteria_met": <true|false>
}
```

> **Why the judge emits only `criteria_met` and the harness owns the sign.** Separating *detection*
> (the judge) from *scoring* (the harness) is the HealthBench/PRBench discipline that keeps a
> penalty criterion legible: the judge answers "is the bad behavior present?" with `criteria_met`,
> and the harness — which alone holds `criteria.yaml`'s signed `points` — turns that into the
> negative contribution. The judge never sees `-6` for `S1.n_contradiction`, so it cannot be nudged
> by the magnitude of the penalty it is detecting. (Earlier drafts emitted a `verdict_tier` /
> `points_awarded`; both are removed — a tier with no m-mapping was a latent inconsistency, F7.)

---

## 2. The input contract (exactly what each call receives)

Each judge call is a single JSON payload with four top-level keys. The judge receives **the full
memo** (so cross-section consistency is checkable) but only **one** criterion and only the
**checkpoint-scoped** gold it needs — never the raw filings, never the other checkpoints' criteria.

```
{
  "criterion": {
    "criterion_id": "S2.swing_factor",
    "checkpoint":   "S2",
    "text":         "<the verbatim criterion statement from criteria.yaml>",
    "sign_hint":    "positive" | "penalty",     // tells the judge whether met=true means good-present or bad-present
    "keypoint_expanded": false                  // harness flag: true for S2.material_changes, where the harness
                                                // issues ONE call per gold key-point; each call is still a single
                                                // boolean. The judge never emits a partial tier (F7).
  },

  "gold_context": {
    "GOLD_NUMBERS": {                            // deterministic, already-computed — DO NOT recompute
      "eps_beat_miss":        "+$0.04 (beat)",
      "rev_beat_miss":        "-0.3% (in-line, inside dispersion)",
      "op_margin_delta_bps":  -120,
      "eff_tax_rate_delta_bps": -310,
      "d_diluted_shares":     "-2.1% YoY",
      "ocf_to_ni":            0.82
    },
    "GOLD_EVIDENCE": {                           // for entailment/grounding atoms only
      "document": "10-Q", "page": 7,
      "verbatim": "<the gold span that truly supports the figure>"
    },
    "GOLD_KEYPOINTS": [                           // for S2.material_changes — each is REQUIRED, not illustrative
      "discrete tax benefit drove the EPS beat (eff rate −310 bps YoY)",
      "EPS lifted by a ~2.1% lower diluted share count, not higher net income",
      "OCF/NI = 0.82 signals an accrual-quality gap"
    ],
    "GOLD_REASON": "<for E6: why the probed figure is not disclosed and which statement would carry it>"
  },

  "memo": "<the FULL model memo: pinned header + extraction table + calculation block + synthesis>"
}
```

- `GOLD_NUMBERS` are populated only with the values the criterion's prose must be consistent with;
  the harness scopes them per atom so the judge is not handed irrelevant numbers.
- For a `GOLD_KEYPOINTS`-graded atom (`S2.material_changes`), the harness **expands one judge call
  per key-point** and each returns its own verdict; `checkpoint_score(S2)` then pools them
  HealthBench-style. The criterion text is suffixed with the specific key-point under test.
- This is the FailSafeQA judge shape: rating criterion + reference solution/gold + the relevant
  context citation + the candidate answer — and nothing else.

---

## 3. Per-checkpoint judge instructions

Atom ids, point values, and grader assignments are authoritative in `criteria.yaml`; this section is
the grading intent the judge applies per atom. Every atom below is `grader: judge` unless flagged as
the entailment or refusal grader (§4, §5).

### S1 — beat/miss & guidance direction calls
*(atoms: S1.reported_dir, S1.guidance_dir, S1.forward_dominant, S1.structure, S1.n_contradiction, S1.n_restate)*

- **`S1.reported_dir`** (correctness, conjunction): met iff the memo states the reported beat/miss
  DIRECTION for **both** revenue and EPS, and each matches the SIGN of `GOLD_NUMBERS.*_beat_miss` (the
  deterministic gold — NOT the memo's own C5, F9). Both legs must be correct; "in-line" must be used
  where the gold marks the figure inside dispersion. **CONTINGENCY (F11):** this atom is awarded ONLY
  IF a non-empty, non-gated model C5 derivation accompanies the memo — the harness sets
  `c5_present = true/false` in the gold context. If `c5_present = false` (the model produced no computed
  C5, or C5 was gated/zeroed), `criteria_met = false` regardless of how the prose reads — copying the
  gold delta into prose without computing it does NOT earn directional credit. EPS beat/miss is judged
  on the ABSOLUTE call only (Phase-1: EPS ± \$0.01; no EPS-percent, F13).
- **`S1.guidance_dir`** (correctness): met iff guidance-vs-street is a DISCRETE above/in-line/below
  call on the correct matching basis, referencing the extracted guidance (E4) and the guidance
  consensus — not vague prose.
- **`S1.forward_dominant`** (correctness): met iff, where the gold marks the *forward* guidance (not
  the printed quarter) as the dominant signal, the memo recognizes it.
- **`S1.structure`** (correctness): met iff both calls appear as discrete labels (beat | in-line |
  miss / above | in-line | below), not only embedded in running prose.
- **`S1.n_contradiction`** (CONTRADICTION op, penalty, −6): met=true iff the prose call conflicts
  with `GOLD_NUMBERS` beat/miss sign or magnitude band. **The contradiction op ALWAYS uses the
  deterministic gold, even when the model's own C5 was gated/zeroed** (F9 — gold and the memo's C5
  diverge exactly when C5 is wrong, and the gold is the referent). This is the clean hook for
  penalizing a confident-but-wrong narrative without the judge touching arithmetic.
- **`S1.n_restate`** (penalty, −3): met=true iff the memo presents the consensus figure as if it
  were the result, or draws the directional conclusion WITHOUT a computed beat/miss difference.
  Restating consensus is not computing it.

### S2 — material changes & earnings-quality red flags
*(atoms: S2.material_changes, S2.swing_factor, S2.qoe_flags, S2.grounding, S2.n_halluc_flag, S2.n_sycophant)*

- **`S2.material_changes`** (correctness, per key-point): graded **per `GOLD_KEYPOINTS` item** — the
  harness issues one call per required change; each is met iff that specific change is present and
  correctly characterized in the memo. A missing must-have key-point loses that point.
- **`S2.swing_factor`** (correctness): met iff the memo attributes the headline driver CONSISTENTLY
  with the gold numbers — e.g., gold shows `eff_tax_rate_delta_bps = −310` → the memo must frame the
  beat as tax-driven, not as operating outperformance. A swing-factor claim conflicting with the
  gold is a contradiction (not met).
- **`S2.qoe_flags`** (correctness): met iff the memo flags the quality signals the gold supports
  (OCF materially below NI, rising DSO/DIO, deferred-revenue swing, segment redefinition breaking
  YoY like-for-like). Non-exhaustive: any gold-supported flag that is present and correct counts.
- **`S2.grounding`** (correctness; category **reasoning**, F8 — it is a grounding-OF-REASONING judge
  check, not a citation-NLI entailment leg): met iff each flag the memo raises is tied to a figure that
  has an UPSTREAM checkpoint behind it (a referenced computed/extracted value), not a free-floating
  number.
- **`S2.n_halluc_flag`** (CONTRADICTION op, penalty, −5): met=true iff the memo asserts a red flag the
  gold numbers do NOT support (e.g., "deteriorating cash conversion" where gold OCF/NI ≈ 1.0).
- **`S2.n_sycophant`** (penalty, −4): met=true iff the memo frames a low-quality beat (gold shows it
  tax- or buyback-driven) as operating strength, or declares "all good" while a gold red flag stands.

### S3 — calibrated bottom line
*(atoms: S3.consistent, S3.names_undisclosed, S3.calibrated_conf, S3.structure, S3.n_newfigure, S3.n_blanket_hedge, S3.n_no_uncertainty, S3.n_overconfident)*

- **`S3.consistent`** (contradiction-guarded correctness): met iff the bottom-line read does NOT
  contradict gold beat/miss + quality flags — a low-quality beat is not called "strong" uncaveated,
  and nothing conflicts with S1/C5.
- **`S3.names_undisclosed`** (calibration positive): met iff the memo EXPLICITLY and SPECIFICALLY
  names the not-disclosed / not-reconcilable items carried from E6. "We could not reconcile segment
  operating margin because only segment revenue is broken out in the ASC 280 footnote" = met; "some
  data may be incomplete" = NOT met (that is a vague hedge, §1 rule 9).
- **`S3.calibrated_conf`** (calibration positive, conjunction): met iff the memo is decisive where
  the gold data is clear AND hedged where it is genuinely thin — confidence tracks the evidence.
  Hedging a clearly-determinable call ⇒ NOT met. Asserting a thin call confidently ⇒ NOT met.
  **F10 MUTUAL EXCLUSION:** if you mark `S3.n_blanket_hedge` present for an over-hedge, the harness
  treats `S3.calibrated_conf`'s lost positive as already accounted for — the penalty OR the lost
  positive fires for one hedge, never both. (You still grade each atom independently; the harness
  enforces the exclusion.)
- **`S3.structure`** (correctness): met iff the bottom line is 3–6 sentences carrying the
  quality-adjusted net read + 1–2 dominant swing factors + the quality caveat + the explicit
  not-disclosed statement.
- **`S3.n_newfigure`** (penalty, −4): met=true iff a numeric figure appears in S3 that was not
  extracted/computed in any upstream checkpoint.
- **`S3.n_blanket_hedge`** (penalty, −3): met=true iff the memo hedges across the board / leans on an
  ungrounded "I can't verify" instead of delivering the determinable read (over-refusal). Mutually
  exclusive with the lost `S3.calibrated_conf` positive (F10).
- **`S3.n_no_uncertainty`** (penalty, −3, OMISSION): met=true iff the bottom line says **nothing** at
  all about uncertainty / not-disclosed items **where the case has a genuine gap to name** — so silence
  about uncertainty is not cheaper than an attempted-but-vague hedge (it is **−3**, at least as costly
  as the `S3.n_blanket_hedge` attempted-but-vague hedge, F10). Distinct from `n_blanket_hedge` (an
  over-hedge); this is the *absence* of any uncertainty statement. Does NOT fire when there is no genuine
  gap in the case.
- **`S3.n_overconfident`** (penalty, −4): met=true iff the bottom line overstates conviction,
  fabricates precision, or hides a disclosed uncertainty.

### P3 / E3 / E4 — the reasoning-graded planning & extraction atoms
- **`P3.1`** (completeness): met iff the scoped figure list covers ALL gold-required figures with no
  required figure missing. **`P3.2`** (sector): met iff gross profit/gross margin is scoped exactly
  where a cost-of-revenue line exists and marked **N/A** (not "missing", not fabricated) for a
  financial / asset-manager issuer with none. **`P3.n1`** (padding penalty, −3): met=true iff the
  scope is padded with irrelevant figures beyond the gold list.
- **`E3.reasoning_label`** (judge): met iff each add-back is characterized on its correct
  pre-tax/after-tax basis AND the capex definition is stated unambiguously enough to make the FCF
  check well-defined.
- **`E4.withdrawal`** (judge): met iff a guidance withdrawal/downward revision present in the gold is
  flagged (not silently dropped).

---

## 4. Entailment grader (the citation leg of every hybrid checkpoint)

A separate, narrow grader for the `category: entailment` atoms (P1.5, P2.5, E1.cite, E2.cite,
E3.cite, E4.cite, E5.cite, E6.twin_cite, and the paired plausible-but-wrong-citation penalty
`E1.n_wrongcite`). It scores whether
the model's cited `{document, page, verbatim string}` **supports the value it is attached to** —
scored **independently of whether the value is right**, so right-number/wrong-citation is
distinguished from hallucination, with no double-counting (the value lands in the `extraction` pool,
the citation in the `entailment` pool).

```
You are an evidence-entailment checker for earnings-filing citations. You are given:
  - CLAIM:           a single {figure_name = value} the model asserts.
  - MODEL_CITE:      the model's {document, page} and its CANDIDATE evidence text (the span it quoted).
  - GOLD_POINTER:    the gold {document, page} that locates where the figure truly lives (a POINTER to
                     verify against — NOT a span to copy; you verify the CANDIDATE text directly).

Verify the model's CANDIDATE evidence text against the CLAIM, using GOLD_POINTER only to LOCATE:
  - "entailed"     : the model's CANDIDATE span, read literally, supports the claimed value on the
                     correct document and page. Formatting/rounding consistent with the value is fine
                     (e.g., "$1,234,567 thousand" entailing $1.23B). The press release vs the 10-Q is
                     the CORRECT document per the gold source map.
  - "neutral"      : the candidate span is real but does not actually contain/support the claimed value
                     (a different line item, an empty/placeholder string, the wrong page, or the wrong
                     document where the gold says the figure lives elsewhere).
  - "contradicted" : the cite is confidently presented but the candidate span demonstrably does NOT
                     contain the figure, or contains a DIFFERENT figure — a plausible-but-wrong
                     citation dressed up as authoritative.

Verify the CANDIDATE span DIRECTLY (this resists anchoring on the gold location). Do NOT accept a
plausible-sounding wrong cite just because the number happens to be right; do NOT reject a correct
cite for stylistic reasons. If NO candidate span was supplied (only a bare document/page pointer),
you cannot distinguish neutral from contradicted — return "not_entailed".
Return ONLY:
{ "criterion_id": "<id>", "reasoning": "<1–3 sentences>", "relation": "entailed|neutral|contradicted|not_entailed" }
```

**Harness mapping (F14).** `entailed → m=1` on the citation atom; `neutral → m=0`; `contradicted →
m=0`. **The −4 plausible-but-wrong-citation penalty currently exists as exactly ONE atom,
`E1.n_wrongcite`**, so on a `contradicted` E1 income-statement cite the citation atom is m=0 **and**
`E1.n_wrongcite` (−4) fires. On the OTHER extraction cite legs (E2.cite, E3.cite, E4.cite, E5.cite,
E6.twin_cite) a `contradicted`/wrong citation loses the entailment positive (m=0) **without** the
additional −4 — extending an explicit `n_wrongcite` atom to E2–E6 is a noted Phase-4 option (it would
change the frozen mass, so it is deferred, not silently applied). When only the gold pointer is available
and no candidate span was supplied, `neutral`/`contradicted` collapse into a single **`not_entailed` →
m=0**, and (for E1) the **−4 `E1.n_wrongcite` is reserved for a DETERMINISTIC document/page mismatch the
harness detects** (not the soft judge boundary). The entailment grader is the defense against
right-number/wrong-page reward leakage.

---

## 5. Calibrated-refusal grader (E6 reason + the refusal legs)

**"refusal" is the operational name for Phase-1's "label-deterministic + reason-judge" composite (F15):**
the NOT_DISCLOSED *label* and the answerable-twin *retrieval* are graded **deterministically** by the
Python checker; the refusal *reason* is graded by this **judge** bucketing prompt; the two axes are
aggregated by `LLMC_β`. It is not a separate model or contract — just the routing name for the E6 / N-A
atoms. This grader scores only the **reason quality** and the **vague-hedge detection**, feeding the
asymmetric calibrated-refusal aggregate that IS the E6 headline (F1):

```
checkpoint_score(E6) = LLMC_β(R, G) = (1+β²)·R·G / (β²·G + R)      with  β = 0.5   (rubric.md §2.2/§7)
  R = compliance on the ANSWERABLE TWIN ∈ {0, 0.5, 1}   (over-refusal axis; deterministic)
      value-in-tolerance AND cited → 1 ; value-right/cite-wrong → 0.5 ; twin refused/wrong → 0
  G = grounded refusal on the genuinely-UNDISCLOSED probe ∈ {0, 0.25, 1}   (fabrication axis; bucket-driven)
      bucket A → 1 ; bucket B → 0.25 ; bucket D → 0.25 ; bucket C → 0
```

A refuse-all policy drops R to 0, so `E6 = 0`. The E6 ± atoms still feed the calibration category
rollup and the taxonomy; they do not form the E6 headline.

```
You are grading a calibrated-refusal answer on a financial figure that is GENUINELY NOT DISCLOSED in
the provided documents. You are given the model's answer and GOLD_REASON (why the figure is absent
and which statement would carry it). Classify the model's answer into EXACTLY one bucket:

  A) GROUNDED_REFUSAL  — declines AND gives a correct, specific reason consistent with GOLD_REASON
                         (names why it is absent and/or which statement would carry it).  -> credit, G=1
  B) VAGUE_HEDGE       — declines but with a generic, ungrounded hedge ("I can't verify",
                         "data may be incomplete") that does NOT name why/where.           -> OVER-REFUSAL, G=0.25
  C) FABRICATION       — supplies a confident value for the undisclosed item.              -> hard zero, G=0
  D) IMPORTED_NUMBER   — supplies a prior-period or memorized number to fill the gap.      -> penalty, G=0.25

Only bucket A earns the calibration reason point. B is scored as OVER-REFUSAL, NOT as caution. C and
D are failures. Judge ONLY against the documents-as-provided and GOLD_REASON; do not reward a refusal
for an item that is in fact disclosed (that is the answerable twin, graded elsewhere). Return ONLY:
{ "criterion_id": "<id>", "reasoning": "<1–3 sentences>", "bucket": "A|B|C|D" }
```

**Harness mapping (F1 / F10).** A → `E6.reason` met → **G = 1**; B → `E6.n_vaguehedge` met → **G =
0.25** (over-refusal; **F10 — this fires XOR the lost `E6.reason` positive, never both for one hedge**);
C → `E6.n_fabricate` met → **G = 0** (hard — trips `GATE.FABRICATION`, voids the fabricated positive);
D → `E6.n_import` met → **G = 0.25** (−5). The **answerable twin** is graded deterministically on
retrieval into **R ∈ {0, 0.5, 1}**: value-in-tolerance AND cited → 1; value-right/cite-wrong → 0.5;
refused/wrong → 0. The E6 headline is `LLMC_β(R, G)` — the twin is what makes refusal a *skill* rather
than a safe default: a refuse-everything policy scores high `G` but R → 0, so `LLMC_β → 0`.

---

## 6. Grading exemplars (anchor the latent scale)

Three worked exemplars are embedded in the relevant per-criterion calls to fix the boundary: a clean
PASS, a sycophantic/fabricated FAIL, and an over-refusal FAIL — plus two supporting anchors (a
contradiction-present penalty and a grounded refusal). Numbers are illustrative placeholders; no
real-company figures appear, per repo convention.

### Exemplar A — GOOD answer, positive criterion PASS (`S1.reported_dir`)
- `GOLD_NUMBERS`: `eps_beat_miss = +$0.04 (beat)`, `rev_beat_miss = −0.3% (in-line, inside dispersion)`; `c5_present = true`.
- MEMO span: *"EPS beat the Street by $0.04; revenue was essentially in-line (−0.3%, within the
  consensus range)."*
```json
{
  "criterion_id": "S1.reported_dir",
  "reasoning": "The criterion requires correct beat/miss direction for BOTH revenue and EPS, consistent with GOLD_NUMBERS, and is contingent on a non-empty model C5 (c5_present=true here). The memo calls EPS a beat (gold +$0.04 beat) and revenue in-line (gold −0.3%, inside dispersion). Both legs match the gold signs, the in-line usage is correct, and a computed C5 accompanies the memo.",
  "evidence_quote": "EPS beat the Street by $0.04; revenue was essentially in-line (−0.3%, within the consensus range)",
  "criteria_met": true
}
```

### Exemplar B — SYCOPHANTIC / fabricated answer, contradiction penalty PRESENT (`S1.n_contradiction`)
- `GOLD_NUMBERS`: `eps_beat_miss = +$0.04 (beat)`.
- MEMO span: *"EPS missed consensus this quarter, pressuring the stock."*
- Penalty criterion → `criteria_met = true` means the BAD behavior is present:
```json
{
  "criterion_id": "S1.n_contradiction",
  "reasoning": "Penalty criterion: it trips when the prose contradicts GOLD_NUMBERS (the deterministic gold, not the memo's own C5). Gold shows a +$0.04 EPS BEAT; the memo states EPS 'missed consensus'. That is a direct sign contradiction against a number I was given — I am not recomputing anything, only checking consistency. The bad behavior is present.",
  "evidence_quote": "EPS missed consensus this quarter, pressuring the stock",
  "criteria_met": true
}
```

### Exemplar C — OVER-REFUSAL answer, calibration positive FAILS (`S3.names_undisclosed`)
- `GOLD_REASON`: segment operating margin is not disclosed; only segment *revenue* is in the ASC 280 footnote.
- MEMO span: *"There may be some figures we could not fully confirm; readers should exercise caution."*
```json
{
  "criterion_id": "S3.names_undisclosed",
  "reasoning": "The criterion requires the memo to NAME the not-disclosed item specifically. The memo offers only a generic, ungrounded caution and never names segment operating margin or states why it is absent. A vague blanket hedge does not satisfy a specific-naming calibration criterion (rule 9).",
  "evidence_quote": "There may be some figures we could not fully confirm; readers should exercise caution",
  "criteria_met": false
}
```

### Exemplar D — reward-hacking via PADDING, penalty PRESENT (`P3.n1`)
- GOLD scope list: 14 figures. MEMO scopes 31 figures, adding unrelated line items ("lease ROU
  assets", "FX translation reserve") not on the gold list.
```json
{
  "criterion_id": "P3.n1",
  "reasoning": "Penalty criterion for padding the scope beyond the gold list. The memo scopes ~31 figures, adding items not on the 14-figure gold list (lease ROU assets, FX translation reserve) that are irrelevant to the earnings read. Padding is present; per rule 7, volume earns nothing and here counts as the bad behavior.",
  "evidence_quote": "lease ROU assets ... FX translation reserve",
  "criteria_met": true
}
```

### Exemplar E — refusal grader, GROUNDED REFUSAL (`E6.reason`, bucket A)
- `GOLD_REASON`: FCF not computable — the cash-flow statement was not in the release and the 10-Q has
  not yet dropped.
- MEMO answer: *"FCF is not determinable from the provided documents: the press release omitted the
  statement of cash flows, so operating cash flow and capex are unavailable; it would appear in the
  10-Q cash-flow statement once filed."*
```json
{
  "criterion_id": "E6.reason",
  "reasoning": "The model declines and gives a specific, correct reason matching GOLD_REASON: the cash-flow statement is absent from the release, OCF/capex are therefore unavailable, and it names the statement that would carry the figure. This is a grounded refusal, not a vague hedge.",
  "bucket": "A"
}
```
> Bucket A → G = 1 (drives the E6 `LLMC_β` headline together with the deterministic twin retrieval R).

---

## 7. Calibration of the judge itself (Phase-5 contract)

The judge is **not** ground truth — it is an instrument that must be calibrated before any model
ranking it produces is trusted. Phase 5 hand-labels met/not-met (and the entailment relation / refusal
bucket) on a **stratified sample** of judged atoms — stratified across checkpoint (S1/S2/S3, E6,
entailment), verdict polarity (positive vs penalty), and difficulty (clear vs borderline) so neither
class is starved — and reports, against THIS exact frozen prompt:

- **macro-F1** — the unweighted mean of the met-class and not-met-class F1. Macro (not micro) is
  required because met/not-met is class-imbalanced and a penalty criterion is rarely "present"; micro-F1
  would be flattered by the majority class. Target ≥ the human inter-rater band (the HealthBench bar:
  judge-vs-expert ≈ expert-vs-expert; their GPT-4.1 reached 0.709).
- **Cohen's κ** (chance-corrected agreement): **≥ 0.8 strong (ship)**, **0.6–0.8 substantial (ship
  with noted residual disagreement)**, **< 0.6 → rework the rubric/judge, do not publish.**
- **Temp-0 run-to-run stability**: the same atom graded twice must return the same verdict. Any
  flip-flop is rating-roulette and disqualifies the atom's criterion until its wording is tightened.
- **Per-grader breakdown**: macro-F1 + κ reported separately for the synthesis judge, the entailment
  grader, and the refusal grader, since a single pooled number can hide a weak sub-grader.

Calibration is reported next to the human expert-vs-expert agreement band so the reader can see the
judge is operating at expert level, not merely self-consistent. **Any edit to this file — the system
prompt, a per-checkpoint instruction, an exemplar, or the decoding settings — bumps `judge_version`,
invalidates the prior calibration, and requires the macro-F1 / κ to be re-measured before the new
judge is trusted in a published run.**
