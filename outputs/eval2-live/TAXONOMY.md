# Eval #2 — live-run failure taxonomy (work in progress)

> Built from REAL graded traces as Phase 5 runs accumulate. Sample size is stated per finding;
> nothing here is extrapolated beyond what the traces show. Run artifacts (parsed answer, raw
> completion, scored report) sit beside this file as
> `<case>__<model>__<mode>.{answer.json,raw.txt,report.*.txt}`.

## Run log

| # | Case | Model | Mode | Gated | Ungated | Gates fired | Notes |
|---|---|---|---|---|---|---|---|
| 1 | koct-op2026-anchor | qwen3.6-27b (reasoning) | oracle-packet, mock judge | **0.517** | 0.527 | GATE.C2SIGN, GATE.FREELUNCH† | stream truncated by the 900s deadline mid-C7; answer salvaged (S1–S3 absent); † the free-lunch fire is **truncation-driven** (the memo never reached S2), not a content finding |

## Findings from run 1 (N=1, truncated — content findings only from sections the model completed)

**The headline contrast.** E1/E2 extraction = 1.000 (every stated term and every FLEX leg exact,
citations included) and **E5 = 1.000**: the model answered the remaining-cap probe with a perfect
`COMPUTED` response — named NAV₀/NAV_t/stated-cap inputs, stated the fixed-price-level convention,
computed 6.06% (gold 6.0598). The same model then leaked errors across the *surrounding*
calculation block. Strong-extractor / weak-derivation is the same profile eval #1 measured for
Qwen2.5-32B; eval #2 localizes it to specific options-math steps:

1. **Grid-convention conflation** (C2, fired `GATE.C2SIGN`): the payoff grid rows were filled with
   the prospectus's idealized %-convention (−85, −5, 0, 17.18 …) instead of per-unit dollars —
   while the model's own `signature_values` are exactly right (281.11 / 239.54 / 36.29). It knows
   the dollar arithmetic; it conflated the two conventions the workflow doc deliberately separates
   (the C2.n_convention failure mode, caught at the gate tier).
2. **Stated-value echo in place of recompute** (C3): the "recomputed" cap/buffer/identity are the
   filing's printed figures verbatim (17.18 / 15 / 205.67); `synth_sanity` came back as the raw
   strike (2.42) instead of the ratio (1.0002); max loss came back **+85 — the sign dropped**.
   The 0.05pp recompute band cannot distinguish an echo from a real recompute when the terms tie
   (by design — the designed reconciliation-BREAK case, deferred, is the discriminator); the
   sanity row and the sign are where the echo became visible.
3. **Ref₀ recovered by inversion, then rounded** (C1): used `K_cap/(1+cap)` (defensible inversion,
   wrong rule — Power Buffer pins `Ref₀ = K_top`) and reported 242.0, failing exact-cents against
   241.96. The roles map itself was perfect.
4. **Per-contract vs per-unit confusion** (C5): units 5,278 (the 100-share multiplier dropped at
   exactly the step the rubric predicts), "notional" 527,800 (which IS the unit count, mislabeled),
   package value null — while `pctval_sum` is exact to 10 decimal places. Extraction-grade
   precision feeding arithmetic-grade confusion.
5. **Sign discipline on buyer-relative terms** (C6): `downside_before_buffer` reported +9.49 —
   right magnitude, dropped sign (the convention's negative marks the unbuffered gap);
   `remaining_buffer_depth` echoed the stated 15% instead of computing 23.07%; the fee proration
   used a wrong day count (0.46pp vs 0.2424pp). Yet `remaining_cap_gross` 6.06 ✓, buffer status
   `intact` ✓, sign label `positive` ✓ — so the C6 in-checkpoint gate did NOT fire; the failures
   were banded-value misses, exactly the granularity the per-atom design wants.

**Infrastructure findings** (not model capability, but real harness lessons):
- Qwen3.6 is a reasoning model: its think phase streams as `delta.reasoning_content` and runs
  thousands of tokens on this task (~15k chars observed). The client now budgets for it
  (16k tokens / `--deadline 2400`), captures the reasoning stream for diagnostics, and salvages
  deadline-truncated JSON (close-the-brackets parser, `_salvaged: true`).
- A truncated memo fires `GATE.FREELUNCH` "honestly" (protection asserted upstream, no cost block
  present) — true by the predicate's letter, but run reports must label truncation-driven fires
  separately from content fires. This run's flag is truncation-driven.
- The M5 Max rig drops ~30 min after last user interaction (macOS sleep; network streaming does
  not prevent it). Use `caffeinate -dims` for queue sessions.

## Open items

- Re-run the anchor un-truncated (deadline 2400s) to replace run 1's S1–S3/C7 blanks with content.
- postrally / postdrawdown / anchor `--e2e` (the vintage-distractor probe).
- A non-reasoning subject (qwen3-coder-next) for the thinking-vs-non-thinking contrast.
- `--judge llm` pass on completed runs (mock judge inflates S-tier presence atoms).
