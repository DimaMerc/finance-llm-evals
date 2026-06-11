# Rubric — eval #2 scoring model (defined-outcome / buffer ETF analysis)

> **Phase-2 deliverable of eval #2.** The machine-readable atoms live in
> [`criteria-defined-outcome.yaml`](criteria-defined-outcome.yaml) (same schema as eval #1's
> [`criteria.yaml`](criteria.yaml) — no schema change); the judge is
> [`judge.md`](judge.md) §8's documented extension of the same frozen prompt
> (`judge_version: 2.1.0`); the workflow spec with every checkpoint's success criteria is
> [`../workflow/defined-outcome-analysis.md`](../workflow/defined-outcome-analysis.md).
> This document is deliberately **compact**: it states what differs from eval #1 and where the
> numbers come from, instead of mirroring tables that can drift.
>
> Validate: `python rubric/validate.py rubric/criteria-defined-outcome.yaml` — 18 assertions; the
> printed mass tables are the **source of truth** (eval #1's hand-mirrored tables produced exactly
> the drift bugs its review caught, so eval #2 does not duplicate them).
>
> `rubric_version: 1.0.0` · 110 atoms · +349 positive / −121 penalty mass ·
> graders: deterministic 76 / entailment 8 / judge 19 / refusal 7.

## What is identical to eval #1

The scoring model is the suite's: **checkpoint-primary aggregation**
(`CaseScore = Σ_k W_k · checkpoint_score(k)`, HealthBench inner pool `awarded/raw_pos`, clip per
checkpoint, raw retained), the **six-category diagnostic rollup with the same weights**
(numerical .26 / extraction .22 / reasoning .20 / entailment .14 / calibration .12 / structure .06 —
kept identical for cross-eval comparability), gates as deterministic predicates that zero dependents
*before* pooling, gated/ungated/GAP/AllPass reported in Oracle and end-to-end modes, the
value-vs-entailment hybrid split, omission-vs-commission penalty discipline, and the refusal
checkpoint's **F-β headline** (`LLMC_β`, β = 0.5) as the one non-pool checkpoint score.

## What is different, and why

**1. Eighteen checkpoints, calculation-heavy weights.** Stage subtotals
planning **.125** / extraction **.275** / calculation **.420** / synthesis **.180**
(eval #1: .130/.360/.325/.185). The workflow's center of gravity is closed-form options math —
seven deterministic calculation checkpoints, zero judge calls before synthesis. The heaviest single
checkpoints are **C6** (the remaining outcome for today's buyer, .080), **C3** (the
recompute-vs-stated spine, .075), and **E2** (the FLEX legs, .075).

| P1 | P2 | P3 | E1 | E2 | E3 | E4 | E5 | C1 | C2 | C3 | C4 | C5 | C6 | C7 | S1 | S2 | S3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| .045 | .045 | .035 | .055 | .075 | .045 | .045 | .055 | .055 | .065 | .075 | .045 | .040 | .080 | .060 | .065 | .070 | .045 |

**2. The gate ledger** (all deterministic predicates; blast radii in the YAML `gates:` block):

| Gate | Tier | Fires on | Zeros |
|---|---|---|---|
| `GATE.VINTAGE` | hard | wrong series/vintage/outcome-period **year** (P1.2) | everything downstream |
| `GATE.REFSCALE` | hard | strike-scale / reference-asset / convention error (P2.1) | the **leg-derived chain only** (exclusion list: E1, E3, E5's twin, and the oracle snapshot survive) |
| `GATE.FEEBASIS` | scoped | gross-vs-net basis committed wrong (P3.2) | C4, C7, S1, **C6's net leg** |
| `GATE.FREELUNCH` | scoped | the structured **cost-of-protection block** absent/empty/contradicting C3 while protection is asserted (S2.costblock) | **S2 + S3**, `AllPass = 0`, `free_lunch_fired` headline flag |
| `GATE.C1ROLE` / `GATE.C2SIGN` / `GATE.C6DIR` | in-checkpoint | structure-class inversion / payoff sign-regime flip / remaining-upside sign or status flip | that checkpoint only |
| `GATE.FABRICATION` | per-figure | fabricated strike/leg/CUSIP/notional/underived remaining value | voids that figure's value+cite legs; cascades only on a frame fabrication |

`GATE.FREELUNCH` is the suite's **one synthesis-stage-firing gate** — a declared deviation from
eval #1, kept honest by being a deterministic predicate on a required structured field, not a judge
opinion. It is the eval's signature: an analysis that reports downside protection with no
forgone-upside cost is wrong *by construction* (the fund's own prospectus: *"The Cap is the strike
price of that sold call FLEX Option"*).

**3. Tolerances derive from figure provenance** (the YAML `tolerances:` block): strikes/identities
**exact to the filed cent**; stated figures **exact at printed rounding**; strike-ratio recomputes
**≤ 0.05 pp**; per-unit payoff dollars **± $0.01**; the filed payoff-grid %-rows **≤ 0.5 pp**
(idealized convention — "correcting" it to leg-exact values is a penalized atom, not a banded miss);
NAV-based remaining terms **≤ 0.1 pp gross / ≤ 0.15 pp net** (ACT/365 pinned) with an
internal-consistency leg against the model's own extracted terms. The remaining-terms band is sized
an order of magnitude above honest rounding noise (~3 bp RSS from cent-quoted NAVs) and an order of
magnitude below the smallest conceptual error (quoting a stated cap after a modest rally ≈ 100+ bp).

**4. The E5 refusal probe is computable-but-undisclosed**, so the typed answer adds
`{COMPUTED, value, derivation}` and the G-mapping in [`judge.md`](judge.md) §8.1: a derived in-band
value earns full credit (G = 1.0), a refusal that names the missing inputs and the method earns
G = 0.75, a vague hedge 0.25, and a confident underived number or website import **0.0** — with the
value atom keyed to **C6's** tolerance band so the probe and the calculation can never diverge.
`R` (the answerable twin: the fee-table ER and a leg's contract count) still collapses a refuse-all
policy to `LLMC_β = 0`.

## What counts as a zero (the short version)

A checkpoint zeroes when its gate fires (table above). An atom zeroes when: a value misses its band
after the scale/multiplier folds; a citation fails entailment against the named filing span; a
required+disclosed figure is omitted with no attempt (omission penalties: E1/E3 must-haves); a
verdict label misses the gold enum (C7); prose contradicts the gold C6/C7 numbers (S1/S3
contradiction operators); or the answer fabricates — a strike, a CUSIP (FLEX legs file `cusip='N/A'`),
a notional (none is filed), or an underived remaining-terms value (G = 0, the hardest single penalty
at −10).

## Forward

**Phase 3 (`cases/`)**: the case roster in the workflow doc's forward links — KOCT as the anchor
(its same-day sibling-vintage N-PORTs are built-in distractors), post-rally, post-drawdown,
Ultra/Deep, 100%-buffer, floor-discrimination, SPX contrast, and a designed reconciliation break.
**Phase 4 (`harness/`)**: precondition is the **data-driven grader dispatch** refactor
(`graders.py` hardcodes eval-#1 atom ids; `scoring.py` hardcodes the gate→atom map), then the
`COMPUTED`-aware refusal grader and the `free_lunch_fired` flag. **Phase 5**: both evals through
both run modes, the taxonomy from real traces, and the judge-vs-expert calibration that
`judge_version: 2.1.0` awaits.
