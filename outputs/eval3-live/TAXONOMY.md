# Eval #3 (DCF) — live failure taxonomy

Three frontier models (Anthropic, via the OpenAI-compatible endpoint) run on the McDonald's FY2025
DCF case ([`cases/mcd-fy2025-dcf.case.yaml`](../../cases/mcd-fy2025-dcf.case.yaml)), graded by the
deterministic core + the offline mock judge. Artifacts (the parsed answer, the raw completion, the
scored report) are under each model's folder here.

## The matrix

| Model | Gated | Ungated | GAP | Gate fired | **Numerical (math spine)** | WACC probe (E5) |
|---|---|---|---|---|---|---|
| **claude-opus-4-8**            | **0.965** | 0.965 | 0.000 | none          | **0.978** | refused, G=0.75 |
| **claude-sonnet-4-6**          | **0.955** | 0.955 | 0.000 | none          | **0.978** | refused, G=0.75 |
| **claude-haiku-4-5-20251001**  | **0.692** | 0.711 | 0.019 | **GATE.C1FCF** | **0.646** | refused, G=0.75 |

The headline is the **numerical-category split**: the two strong models reproduce the closed-form DCF
to ~0.98 on the math spine; the weak model collapses to **0.646** — and the eval localizes *why* to a
single checkpoint.

## What each model got right and wrong

**Opus 4.8 / Sonnet 4.6 — textbook DCF, essentially correct (no gate).** Both pinned the frame and
the unlevered basis, extracted the base lines + the EV→equity bridge from the 10-K, projected FCFF,
built WACC from the components, discounted, capitalized the terminal value, **bridged to equity, and
divided by diluted shares** — landing the fair value at ~$228 (gold $227.82) and the ~20%-overvalued
read. No gate fires; the entire C1–C6 calculation spine is clean. The residuals are calibration and
form, not correctness:
- **Both computed the WACC correctly inside the valuation** (C2: Ke 7.80% + after-tax Kd 3.768% on
  market weights = **7.15%**, exact) and discounted with it — but on the separate E5 probe ("what is the
  WACC, *per its 10-K*?") both answered `NOT_DISCLOSED` ("no 10-K states a WACC"), *without volunteering
  the 7.15% they had just computed*. The disclosure answer is true; not offering the figure is the
  calibration quirk. The mock awards the grounded refusal 0.75; the run-mode-aware live judge
  (judge.md §9.1) scores it *below* 0.75 when the components are in context, since the more useful
  answer pairs the (correct) "not in the filing" with the derived value.
- **Opus reported a 1-D WACC sweep, not the full 2-D WACC×g grid** (3/9 cells — the base-g column,
  computed correctly: 261.5/227.8/200.8 vs gold 262/228/201).
- **Opus graded one assumption-contingent claim (CL2, "overvalued by ~a fifth") as flatly `ACCURATE`**,
  missing the `ACCURATE_ON_BASE_CASE_ONLY` nuance (a 50bp-lower WACC roughly halves the gap).
- Both anchored a few frame/units citations to a valid-but-non-canonical statement line.

**Haiku 4.5 — a real FCFF-arithmetic error that cascades (GATE.C1FCF).** Haiku computed the FCFF
*components* about right (NOPAT, D&A, capex ≈ gold) but **its reported FCFF does not equal its own
build** — `nopat + D&A − capex − ΔNWC = 8,795` while it reported **10,795 (a consistent +2,000/yr
offset)**. `GATE.C1FCF` flags exactly this internal inconsistency at C1, and the eval pins the root
cause there — the wrong FCFF then propagates into a wrong EV and a fair value of **$138 vs the correct
$228**, dragging C3/C4/C5/C6/C7 down (numerical 0.646). One localized arithmetic slip, surfaced and
localized, is the whole point of the in-checkpoint gate.

## A note on the WACC probe (it is NOT a capability gap)

The most consistent cross-model behavior is easy to misread, so state it precisely: **all three
*computed* the discount rate correctly inside the model** (C2 WACC ≈ 7.15% from the components) and
discounted with it — the valuation arithmetic was right. The E5 probe is a *separate* calibrated-refusal
question — "what is the WACC, **per its 10-K**?" — and all three answered "it is not disclosed," which
is true (no 10-K states a WACC). What they did *not* do is volunteer the 7.15% they had just computed
two steps earlier. So this is a **framing/context-dependence quirk** — they do the work but won't claim
the number when asked about the *document* rather than asked to *use* it — not an inability to compute
a discount rate. It is also the one place the calculation-heavy design hands real weight to the live
judge's run-mode mapping (a "not disclosed" that ignores the in-context components should score below a
grounded refusal). *(Note: the probe's "per its 10-K" phrasing makes `NOT_DISCLOSED` defensible; a
sharper probe would ask the model to estimate the WACC from the provided inputs — a Phase-6 refinement.)*

## Grader calibration — 5 contract gaps the live runs surfaced (all fixed + re-graded)

Running real models is the only way to find the assumptions a synthetic self-test is written around.
Each fix below makes the eval *fairer to a correct model* without weakening any gate (the selftest's
oracle still scores 1.000/AllPass and every flawed variant still trips its intended gate):

1. **Tax-rate units (pp vs fraction).** Opus reported `tax_rate_used = 21.5` (percentage points, per
   the schema's "percentages in pp" rule) while the handler expected the fraction 0.215 — its
   `EBIT*(1−21.5)` recompute spuriously fired GATE.C1FCF on a model whose FCFF was exact. Fix: normalize
   the tax rate (accept either). *(This is why Opus's first run showed a false GATE.C1FCF.)*
2. **Derived-rate tolerance.** The effective tax rate is *derived* (provision/pretax = 21.42%), not a
   2-dp filing print; the 0.001pp band rejected 21.42 vs the gold's rounded 21.4. Fix: a 0.1pp band for
   derived rates.
3. **Sensitivity-grid matching.** The WACC×g grid was matched by *position*; a model that produces a
   different/partial grid (Opus's 1-D sweep) scored 0/9. Fix: match by the cell's `(WACC, g)` point
   (g normalized for pp/fraction) so a correct partial grid earns per-cell credit.
4. **A calibrated range is not an error.** The eval *rewards* reporting fair value as a range over a
   ±50bp band (the false-precision discipline); S1's mock judge then demanded an exact number and
   penalized Opus's "201–262 (base ~228)". Fix: S1 accepts a number near gold *or* a range that brackets it.
5. **False-precision vs wrong-valuation.** GATE.FALSEPRECISION compared the sensitivity block's
   TV-share to the *gold* C5; Haiku's honest block (internally consistent with its own wrong valuation,
   TV-share 65.5%) fired the gate. Fix: compare to the *model's own* C5 (internal honesty) and normalize
   for pp/fraction — false precision means "no honest range," which the *wrong* valuation is not (the
   C5/C7 value atoms catch that separately).

**Operational note (not a grader bug):** the full DCF JSON runs ~5–7k output tokens; Sonnet truncated
mid-synthesis at an 8k cap, leaving an empty S2 block that *correctly* (but unhelpfully) fired
GATE.FALSEPRECISION. Re-running at 16k completed it cleanly (0.955, no gate). The live-path default
token floor was raised to 12k.

## Caveats (stated, per the suite's honesty discipline)

- **n = 3, one gold case, one vendor lineage.** All three subjects are Claude models; a cross-family
  panel (a GPT / Gemini / open-weight subject) is the honest next step — the same caveat eval #2 carries.
- **Mock judge.** S1–S3 and the E5 run-mode downgrade are graded offline by presence/consistency mocks;
  the live `--judge llm` pass (a different-family grader, judge.md §9) would refine the synthesis and
  the refusal scoring. The deterministic core + all gating are exact in both modes.
- **Decoding.** `temperature` is omitted for these models (they deprecate it), so there is mild
  run-to-run nondeterminism (e.g., Sonnet's E5 label varied between runs).
