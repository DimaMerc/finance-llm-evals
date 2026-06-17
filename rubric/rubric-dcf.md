# Rubric — eval #3 scoring model (discounted-cash-flow valuation)

> **Phase-2 deliverable of eval #3.** The machine-readable atoms live in
> [`criteria-dcf.yaml`](criteria-dcf.yaml) (same schema as eval #1's
> [`criteria.yaml`](criteria.yaml) and eval #2's
> [`criteria-defined-outcome.yaml`](criteria-defined-outcome.yaml) — no schema change); the judge
> is [`judge.md`](judge.md) §9's documented extension of the same frozen prompt
> (`judge_version: 2.2.0` — §9 is additive over 2.1.0); the workflow spec with every checkpoint's success criteria is
> [`../workflow/dcf-analysis.md`](../workflow/dcf-analysis.md).
> This document is deliberately **compact**: it states what differs from evals #1–2 and where the
> numbers come from, instead of mirroring tables that can drift.
>
> Validate: `python rubric/validate.py rubric/criteria-dcf.yaml` — 18 assertions; the printed mass
> tables are the **source of truth** (eval #1's hand-mirrored tables produced exactly the drift bugs
> its review caught, so this doc does not duplicate them).
>
> `rubric_version: 1.0.0` · 107 atoms · +360 positive / −110 penalty mass ·
> graders: deterministic 75 / entailment 6 / judge 19 / refusal 7.

## What is identical to evals #1–2

The scoring model is the suite's: **checkpoint-primary aggregation**
(`CaseScore = Σ_k W_k · checkpoint_score(k)`, HealthBench inner pool `awarded/raw_pos`, clip per
checkpoint, raw retained), the **six-category diagnostic rollup with the same weights**
(numerical .26 / extraction .22 / reasoning .20 / entailment .14 / calibration .12 / structure .06 —
kept identical for cross-eval comparability), gates as deterministic predicates that zero dependents
*before* pooling, gated/ungated/GAP/AllPass reported in Oracle and end-to-end modes, the
value-vs-entailment hybrid split, omission-vs-commission penalty discipline, and the refusal
checkpoint's **F-β headline** (`LLMC_β`, β = 0.5) as the one non-pool checkpoint score (E5 here).

## What is different, and why

**1. Eighteen checkpoints, calculation-heavy weights.** Stage subtotals
planning **.130** / extraction **.250** / calculation **.440** / synthesis **.180**
(eval #1: .130/.360/.325/.185; eval #2: .125/.275/.420/.180). A DCF *is* arithmetic on a handful of
inputs — seven deterministic calculation checkpoints, zero judge calls before synthesis. The heaviest
single checkpoint is **C6** (the EV→equity→per-share bridge, **.085**) — the highest-frequency
real-world error and the signature scoped gate — then **E2** (the bridge items, .075), and **C3**
(discounting) / **C7** (sensitivity + claims) / **S2** (the false-precision gate) tied at **.070** each.

| P1 | P2 | P3 | E1 | E2 | E3 | E4 | E5 | C1 | C2 | C3 | C4 | C5 | C6 | C7 | S1 | S2 | S3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| .050 | .050 | .030 | .050 | .075 | .040 | .035 | .050 | .065 | .055 | .070 | .050 | .045 | .085 | .070 | .060 | .070 | .050 |

**2. The gate ledger** (all deterministic predicates; blast radii in the YAML `gates:` block):

| Gate | Tier | Fires on | Zeros |
|---|---|---|---|
| `GATE.BASIS` | hard | unlevered↔WACC↔EV↔bridge **inconsistency** (P1.consistency **or** C5.consistency) | everything downstream (C1–C7, S1–S3); E-stage extraction survives |
| `GATE.SCALE` | hard | units / thousands-vs-millions error (P2.scale) | the **scaled-dollar chain** (inclusion list: C1, C3, C4, C5.ev, C6.equity, C6.pershare, C7.grid); WACC, ratios, labels survive |
| `GATE.WACC` | scoped | book-weight / pre-tax-Kd / CAPM double-count (P2.waccbasis) | the WACC-derived value chain `[C3, C4, C5.ev]`; C5.consistency / C5.tvshare and C1/C2/E2 survive |
| `GATE.BRIDGE` | scoped | net-debt omission/sign-flip, minority/preferred miss, or EV÷shares (C6.bridge) | the per-share/equity chain `[C6, S1]`; C1–C5 and S2/S3 survive |
| `GATE.FALSEPRECISION` | scoped | the **value-attribution + sensitivity block** absent/empty/contradicting C5 while a point target is asserted (S2.sensblock) | **S2 + S3**, `AllPass = 0`, `false_precision_fired` headline flag |
| `GATE.C1FCF` / `GATE.C4TERM` / `GATE.C7SIGN` | in-checkpoint | FCF-definition error / `g ≥ WACC` / value-vs-price sign flip | that checkpoint only |
| `GATE.FABRICATION` | per-figure | fabricated base figure, "filed" number not in the 10-K, or a discount rate asserted as disclosed | voids that figure's value+cite legs; cascades only on a frame fabrication |

`GATE.FALSEPRECISION` is the suite's **second synthesis-stage-firing gate** (parallel to eval #2's
`GATE.FREELUNCH`) — kept honest by being a deterministic predicate on a required structured field, not
a judge opinion. It is the eval's signature: a single decimal-precise fair value sold as truth, when
70%+ of the value is terminal and a 50 bp WACC move shifts it 15%+, is false precision *by
construction*. `GATE.BASIS` is the spine — it fires from **two** hooks (the planning commitment at P1
and the assembled-EV consistency check at C5), so a basis error declared late is caught the same as one
declared early; the C5 firing atom is in its own blast radius by design (a wrong basis at C5 should
zero C5 too).

**3. Tolerances derive from figure provenance** (the YAML `tolerances:` block): base lines & bridge
items **exact at the filing's printed rounding** (scale-folded); the diluted share count **integer-
exact**; unlevered FCF per year, each PV, the terminal value, and EV all **≤ 0.5 % relative** (pure
arithmetic on the oracle assumptions); WACC **≤ 5 bps** vs the gold build; equity value and **fair
value per share ≤ 1.0 % relative** (the band compounds EV + net debt + share count in quadrature, so
it is wider than the EV band yet an order of magnitude below the conceptual errors it must catch — the
~$39B MCD net-debt bridge moves equity 15%+). EV, equity, and per-share carry an **internal-
consistency leg** (`level_ref`) against the model's own components, separate from the gold match.

**4. The E5 refusal probe is computable-from-components-but-undisclosed-in-the-filing**, so the typed
answer adds `{COMPUTED, value, derivation}` and the G-mapping in [`judge.md`](judge.md) §9.1 is
**run-mode-dependent** (a finer line than eval #2, whose probed NAV is absent from *any* source): a
derived in-band WACC earns full credit (G = 1.0); a refusal that names the missing market inputs earns
G = 0.75 **only when the WACC components are not injected** — when E3 *is* in context, the model can
compute, so a bare `NOT_DISCLOSED` maps below 0.75; a vague hedge 0.25; a confident "the filing's WACC
is X %" **0.0** (fabrication). The value atom is keyed to **C2's** WACC band so the probe and the
calculation can never diverge. `R` (the answerable twin: total debt and the diluted share count)
still collapses a refuse-all policy to `LLMC_β = 0`.

## What counts as a zero (the short version)

A checkpoint zeroes when its gate fires (table above). An atom zeroes when: a value misses its band
after the scale fold; a citation fails entailment against the named 10-K span; a required+disclosed
figure is omitted with no attempt (omission penalties: E1/E2 must-haves); a verdict label misses the
gold enum (C7); prose contradicts the gold C6/C7 numbers (S1/S3 contradiction operators); or the
answer fabricates — a "filed" base line not in the 10-K, a bridge item, or a confident underived
discount rate (G = 0, the hardest single penalty at −10).

## Forward

**Phase 3 (`cases/`)**: the MCD FY2025 gold case (every base line + bridge item cited to the 10-K, the
assumption set as the labeled oracle layer, the closed-form DCF as gold) plus the signature
**"subtly-wrong DCF"** — headline variant is the missing net-debt bridge (scoped, looks-right-is-wrong,
C1–C5 stay green); the basis mix and `g ≥ WACC` are the catastrophic-but-obvious contrast.
**Phase 4 (`harness/suites/dcf.py`)**: the suite module (projection / WACC / discounting / TV / EV /
bridge / sensitivity / claims handlers + the `GATE.FALSEPRECISION` predicate); the only shared-code
change is **two literal keys** appended to `_EXPANSIONS` in `harness/rubric.py` (`per_year_row`,
`per_grid_cell`) — `per_claim_row` is reused as-is — additive and byte-invariant for evals #1–2,
guarded by `selftest`. **Phase 5**: frontier + local models through both run modes, the taxonomy from
real traces, and the judge-vs-expert calibration that `judge_version: 2.2.0` awaits.
