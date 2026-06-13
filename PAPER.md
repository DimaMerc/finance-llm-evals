# A Runnable, Rubric-Graded Evaluation Suite for Finance LLMs: Earnings Analysis and Defined-Outcome ETF Diligence

**Dmitry Krutous** · MBA, PMP · [linkedin.com/in/dmitrykrutous](https://www.linkedin.com/in/dmitrykrutous/) · welt.management.solutions@gmail.com
*Methodology note & findings, v2. The artifact is the runnable repository this paper accompanies:
[github.com/DimaMerc/finance-llm-evals](https://github.com/DimaMerc/finance-llm-evals). v1 covered the
earnings eval alone; v2 adds the defined-outcome ETF eval, a two-model run matrix, the live failure
taxonomy, and the judge-vs-expert calibration.*

---

## Abstract

Most finance-LLM demos show a polished answer; few show the *scoring system* that decides whether the
answer can be trusted. This work builds one — a runnable two-eval suite covering real asset-management
workflows, judged against expert-authored rubrics the way a finance professional would: every figure
traced to a source filing, auto-fail "gates" for the errors that quietly poison a memo, and credit for
*calibrated uncertainty* rather than confident guessing. **Eval #1** scores quarterly **earnings
analysis** (17 checkpoints, 109 criteria, three gold cases from real 10-Qs). **Eval #2** scores a
workflow almost nobody publishes evals for: **defined-outcome ("buffer") ETF diligence** — given a
prospectus, the fund's actual FLEX-option legs from its N-PORT filing, and a dated market snapshot,
recompute the marketed cap and buffer *from the strikes*, compute what a **mid-period buyer actually
gets**, verify marketing claims, and price the protection (a memo asserting downside protection with no
forgone-upside cost auto-fails: the **free-lunch gate**). Both evals run on one scoring engine;
everything deterministic is graded deterministically, and the LLM judge is confined to the synthesis
tier. Live runs of two local models produce the intended diagnostics: a reasoning 27B beats a
non-reasoning 72B on every defined-outcome case; both subjects — two model generations of one vendor
lineage — walk into the same payoff-table convention trap (suggestive that it is task-level;
cross-family replication is named future work); the designed mid-period traps catch their targets; and
swapping the mock judge for a real one moves eval-#2 scores by only 2–4.5 points versus 14.7 on eval #1
— the calculation-heavy design working as intended. A judge-vs-expert calibration on the free-form
verdicts finds no overturned verdict (28/28, κ = 1.0, with caveats stated).

## 1. Motivation

A firm that wants an LLM to do analyst work has one hard problem before deployment: *how do we know
when — and exactly where — to trust it?* A blended accuracy number cannot answer that. The errors that
matter in finance are rarely small ones: misreading an "in thousands" header, pinning the wrong fiscal
period — or, in the structured-product world, quoting a prospectus cap to a client who is buying
**mid-period** (the stated terms belong only to a day-one buyer), reading FLEX-option strikes quoted on
an ETF's share price as index levels (~10–20× off), calling a partially-consumed buffer "breached," or
selling downside protection as if it were free. Each silently corrupts everything downstream while the
prose still reads fluently.

The public ingredients exist — **HealthBench** (expert rubric criteria, LLM-judged), **FinanceBench**
(evidence-cited answers over SEC filings), **FinQA/TAT-QA** (numeric reasoning with tolerance), the
**Vals AI Finance Agent Benchmark** (checkpointed end-to-end tasks), **FailSafeQA** (calibrated refusal)
— but not composed into a runnable whole, and not for derivatives-overlay products at all. Eval #2 is
deliberately the eval a generalist cannot author: it requires knowing that a buffer ETF is four FLEX
legs in a trust wrapper, that the prospectus and the N-PORT share **no figure** and tie only through
the options math, and that the issuer's own daily "remaining outcome" numbers live on its website, not
in any filing.

## 2. Method

### 2.1 Eval #1 — earnings analysis (summary; unchanged from v1)

The task — digest a 10-Q/10-K and earnings release, extract and reconcile key figures, benchmark versus
consensus, flag material changes — decomposes into 17 checkpoints across planning → extraction →
calculation → synthesis, scored by 109 atomic criteria with three gate tiers (hard / scoped /
in-checkpoint), evidence-citation entailment, and a FailSafeQA-style calibrated-refusal probe (E6,
F-β with an *answerable twin* so refuse-everything cannot farm safety credit). Three gold cases from
real filings (BlackRock Q3'25, Microsoft FQ2'26, Snowflake FQ2'26) exercise every gate tier:
sector-N/A, fiscal-vs-calendar, the "in thousands" scale trap, a GAAP-loss/non-GAAP-profit share
divergence, and a genuine not-disclosed probe. Details in v1 / the repository.

### 2.2 Eval #2 — defined-outcome ETF diligence (new)

**The task.** What a diligent advisor must do before recommending a buffer ETF to a client buying
*today*, mid-period: pin the exact fund vintage (the issuer runs twelve monthly series with identical
names except the month), extract the stated terms from the prospectus and the four FLEX legs from the
N-PORT, **recompute the marketing from the strikes** (the cap is literally the strike of the call sold
to finance the put spread — the prospectus says so), compute the *remaining* outcome for a buyer at
today's NAV, verify a marketing-claim set, and write a calibrated suitability read that prices the
protection.

**Decomposition.** 18 checkpoints, deliberately calculation-heavy (3 planning / 5 extraction / 7
calculation / 3 synthesis; stage weights .125/.275/.420/.180): vintage pin · reference/strike-scale
lock · fee basis; stated terms · the four legs (per-leg, signed) · fee/credit language · snapshot
staleness ledger · a calibrated-refusal probe; leg roles + initial reference recovery · payoff
reconstruction · **recompute-vs-stated reconciliation** · fee netting · notional tie-outs · the
remaining outcome at NAV_t · claim verdicts; entry-timing verdict · cost of protection · calibrated
bottom line. **110 atomic criteria** (76 deterministic, 8 entailment, 19 judge, 7 refusal): no *positive* judge
atom exists before the synthesis stage (one judge-tier anti-gaming penalty sits at planning).

**Gates.** `GATE.VINTAGE` (hard — analyzing the November fund's legs against the October fund's terms
poisons everything; sibling filings land the same day with adjacent accession numbers, so the
distractor is built into the source data) · `GATE.REFSCALE` (hard — ETF-share-price strikes read as
index levels, a dropped 100-share multiplier, or flipped written-leg signs; with an explicit survivor
list for the prospectus-side figures that carry no strike scale) · `GATE.FEEBASIS` (scoped —
gross-vs-net mixing zeroes the fee chain only) · three in-checkpoint fails (a buffer/floor/barrier
inversion; a payoff sign/regime error; a remaining-upside direction or buffer-status flip) · and the
signature: **`GATE.FREELUNCH`** — the deliverable *requires* a structured cost-of-protection block
(capped upside with the cap value, forgone dividends, fee drag, path/exit risk); a memo that presents
downside protection while that block is absent, hollow, or contradicts the recomputed cap is zeroed at
S2+S3 and flagged `free_lunch_fired` in the headline. The gate is a deterministic predicate, not a
judge opinion.

**Calibrated refusal, extended.** The probe — *"what is the remaining cap for a buyer at today's
NAV?"* — targets a figure that is **computable but undisclosed**: issuers publish daily remaining
outcomes on their websites (the prospectus delegates them there verbatim), never in EDGAR filings. The
typed answer therefore adds `{COMPUTED, value, derivation}` beside `{NOT_DISCLOSED, reason}`: full
credit for a correct computation *with* its derivation, refusal credit only for naming exactly which
inputs are missing and citing the delegation language, zero for a confident underived number — and an
imported issuer-website figure scores as an import, not a computation (the issuer's own tool nets out
fees already incurred, so its number is *correctly different* from the filings-derived one; we verified
the reconciliation to ≤1bp).

**Gold cases.** One real fund — Innovator U.S. Small Cap Power Buffer ETF – October (KOCT), whose four
filed strikes reproduce its stated 17.18%/15% terms to within 0.002pp — under three oracle snapshots:
the **anchor** (a real, cited snapshot: NAV₀ \$33.00, NAV \$36.46, IWM \$285.02 → remaining cap
**+6.06% gross / +5.82% net** against the stated 17.18%, with a 9.49% unbuffered gap), a
**post-rally** state (constructed, labeled: 12 days to expiry, remaining net **+0.78% ≈ zero**; the
case documents why the NAV-anchored net floor is ≈ ER/(1+cap_net) ≈ 0.68pp, strictly positive by
no-arbitrage), and a **post-drawdown** state (constructed, labeled: the reference 6.6% inside the
band — buffer **43.98% consumed ≠ breached** — while the remaining cap is *enlarged* to +18.26%).
Every case packets the live distractors: the September and November sibling N-PORTs and a mid-period
497K restating the period-start terms in a current-dated filing. Constructed snapshots are explicitly
labeled hypothetical; the gold is the deterministic math computed *on* the snapshot, never the snapshot
itself. Each case passed a multi-agent adversarial verification before commit — a pass that caught a
real error in the author's own draft (a constructed NAV that violated no-arbitrage at 47 days to
expiry: in-band, the put spread pins the package near the flat-zone PV, so the fund can only dip ~1%)
and a gold-encoding bug (a bare YAML `FALSE` parsing as a boolean), both fixed pre-publication and
logged in the case files.

**Harness.** One suite-agnostic scoring engine, two suite modules. The eval-#1 port was proven
**byte-identical** against a captured pre-refactor baseline; gate firing is derived from each rubric's
own `fired_by` hooks, never hardcoded. The engine and the new suite were adversarially reviewed
pre-commit (engine semantics, per-atom coverage, gaming surfaces, perturbation probes); the review
found and killed several exploit classes — among them placeholder cost blocks buying off the
free-lunch gate, substring-fished refusal credit, and two pre-existing eval-#1 grader bugs the
byte-identical baseline had only proven parity for (the full list is in the Phase-4 commit message). The live path drives any OpenAI-compatible local endpoint, and a **schema
round-trip selftest** (a schema-perfect answer must grade 1.000/AllPass on every case) pins the live
output contract to the graders permanently.

## 3. Findings

*The instrument first, then live models. All artifacts (answers, raw streams, scored reports, the
taxonomy) are committed under `outputs/eval2-live/`.*

**3.1 The gates fire cleanly, with tier-differentiated blast radii.** Against a perfect answer eval #2
scores 1.000/AllPass on all three cases; against planted errors (the selftest asserts these as
thresholds; the values below are from the current build):

| Injected error | Gate tier | GAP |
|---|---|---:|
| pinned the sibling vintage | hard (`GATE.VINTAGE`) | **0.88** |
| strikes read as index levels | hard (`GATE.REFSCALE`) | 0.46 |
| net committed against a gross recompute | scoped (`GATE.FEEBASIS`) | 0.18 |
| protection asserted, no cost block | scoped (`GATE.FREELUNCH`) + headline flag | 0.07 |
| remaining-upside sign flipped | in-checkpoint (`GATE.C6DIR`) | 0.07 |

The free-lunch GAP is deliberately small — the signature finding is a *flag*, not a big number: a memo
can be 93% "right" and still be the memo that mis-sells the product.

**3.2 Two real models, three cases each (local, no API spend).** A reasoning model (Qwen3.6-27B) and a
non-reasoning one (Qwen2.5-72B-Instruct); gated scores, offline judge:

| Case | Qwen3.6-27B (reasoning) | Qwen2.5-72B (non-reasoning) |
|---|---:|---:|
| anchor (real snapshot) | **0.732** | 0.638 |
| post-rally (near-cap) | **0.708** | 0.584 |
| post-drawdown (consumed buffer) | **0.702** | 0.577 |
| anchor, end-to-end (distractor packet) | **0.651** | — |

One subject per architecture class, so the reasoning-vs-non-reasoning contrast is an *observation*, not
an architecture study. What the per-checkpoint traces support:

- **A shared trap (N=2 subjects).** Both models filled the payoff-grid rows with the prospectus's
  idealized %-convention (−85, 0, 17.18 …) where per-unit dollars belong — the 27B in all four of its
  runs *while simultaneously producing the exactly-correct per-unit signature values* (281.11 / 239.54
  / 36.29). The prospectus prints the table in %; models follow the document instead of the asked-for
  reconstruction. Two subjects in the same trap is suggestive that the eval measures the task — but
  both are Qwen-lineage models (different generations), so cross-family replication is required
  before calling it task-level.
- **The remaining-outcome arithmetic is where the think phase earned its keep.** The reasoning model
  answered the remaining-cap probe with a perfect `COMPUTED` derivation in *every* run (6.06 / 0.81 /
  18.26 against gold 6.0598 / 0.8066 / 18.2550). The 72B missed all three — including reporting the
  *same* wrong 4.78% on two cases with different NAVs (an anchored value, not a recompute) and, on the
  post-drawdown case, a full state inversion (−0.94%, "negative," "below band" against gold +18.26%,
  positive, partially consumed). `GATE.C6DIR` caught both bad runs, as designed.
- **The designed traps catch their targets.** The post-drawdown case exists to test the consumed-buffer
  read: the 27B computed the enlarged cap correctly and *still* labeled the buffer `intact` with the
  reference 6.6% inside the band — and separately computed the downside-gap value correctly (+0.91) while
  inverting its semantics ("0.91% gap" where the positive sign means *no* gap). Right numbers, wrong
  state — precisely the failure class C6's label atoms exist to isolate from the arithmetic.
- **The end-to-end probe.** Given three same-day sibling N-PORTs (strikes ~2–3% apart) and a
  mid-period 497K restating stale terms, the 27B **pinned the correct vintage** — the hard gate did not
  fire — and paid for retrieval with a modest extraction cost (0.863 → 0.825) and a 0.08 gated drop
  (0.732 → 0.651).
- **The free-lunch gate, tested honestly.** On its complete memos the 27B produced a full, correct
  cost-of-protection block — the signature gate caught neither subject *on content*. Its only fires in
  the log were stream-truncation artifacts (a memo cut before S2 trivially "asserts protection with no
  cost block"), which the run log labels separately. An eval that wants to be trusted must distinguish
  its infrastructure artifacts from its findings.
- **Extraction is strong in both subjects** (0.91 on every 72B run; 0.86–0.91 across the 27B's),
  and both share the same
  per-contract/per-unit confusion at the notional tie-outs (the 100-share multiplier dropped at exactly
  the step the rubric predicted) and a stated-value-echo tendency in the reconciliation block — visible
  only where the echo diverges from a true recompute (a sanity ratio returned as the raw strike; a max
  loss returned sign-dropped). A third candidate (a code-specialized model) produced structurally
  unparseable output on its single attempt (schema-noncompliant decimals, unescaped quotes, a
  degeneration loop) — recorded as-is: an unassisted run would score zero.

**3.3 The judge matters far less here — by design.** Swapping the offline mock judge for a real LLM
judge moves eval-#2 scores by **2.0–4.5 points** (e.g. anchor 0.732 → 0.712). The same swap on eval #1
moved its single-model score by **14.7 points** (0.679 → 0.532). Eval #2 was built calculation-heavy
precisely so the headline would not ride on judge permissiveness; its deterministic surface —
extraction, all seven calculation checkpoints, every gate — does not touch the judge at all.

**3.4 Judge-vs-expert calibration.** The live judge's 28 free-form verdicts (7 synthesis atoms × 4
complete runs) were independently hand-graded by the author (ETF/derivatives background) from a
worksheet showing each criterion, the model's actual section, and the gold reference. Result: **28/28
agreement (κ = 1.0)** on a sample with real signal (the judge had awarded only 57% of the verdicts).
Caveats stated plainly: n = 28, one model's answers, and the worksheet displayed the judge's verdict
(an anchoring risk); the claim is *no verdict was overturned on expert review*, not that the judge is
infallible. The strongest caveat: the judge here is the *same model* whose memos it graded (qwen3.6-27b
judging qwen3.6-27b) — self-judging is a stronger bias channel than mere family overlap; an
independent cross-family judge is the correct next setup.

**3.5 Running real models improves the eval — again.** The first live batch surfaced three
grader-contract gaps the synthetic tests could not: a structure-class enum graded so literally that
`power_buffer` (the variant name) failed where `buffer` was meant; the fund's real cash-sleeve row
counted as a "fabricated fifth leg"; and a gold-side labeling band (when "≈ zero" applies to remaining
upside) that the model could never have known because the output contract never stated it. All three
were fixed and all runs re-graded, with the calibration log published in the taxonomy. This mirrors
v1's §3.3 finding on eval #1 — it appears to be a law of eval-building: *the first real model finds the
grader bugs your self-tests were written around.*

## 4. Limitations & future work

(i) **Two models, one fund family.** The matrix is 2 subjects × 3 cases + one end-to-end probe; the
deferred case set (an Ultra/Deep Buffer testing a different reference-recovery rule, a 100%-buffer
fund, a floor-vs-buffer discrimination probe, an SPX-scale contrast, a designed reconciliation break)
is specified in the repository plan. (ii) **Judge calibration** is small-sample and author-graded with
the anchoring caveat above; the cross-family judge and a larger blind sample are next. (iii) **Offline
judge-tier permissiveness**: in mock mode several synthesis atoms are presence-graded (documented and
quantified in the repo); the live judge is the swap, and the deterministic core is unaffected. (iv)
The constructed snapshots are clearly labeled hypotheticals; the anchor case's snapshot is real and
cited. None of these affect the method; they bound the results, which grow as the matrix fills.

## 5. Reproduce

One dependency (`pyyaml`), no API key for everything deterministic:

```bash
python -m harness suite                      # score all six gold cases, both evals
python -m harness selftest                   # gate tiers + the live-schema round-trip invariants
python -m harness run --case koct-op2026-anchor --model free_lunch   # watch the signature gate fire
python rubric/validate.py rubric/criteria-defined-outcome.yaml       # the rubric's 18 invariants
```

A real model is one flag away (any OpenAI-compatible endpoint):
`python outputs/run_live_eval2.py koct-op2026-anchor [--e2e] [--model-id …]` — artifacts, the failure
taxonomy, and the calibration worksheet are committed under `outputs/eval2-live/`.

## References

OpenAI HealthBench · FinanceBench (Patronus AI) · FinQA / ConvFinQA / TAT-QA · Vals AI Finance Agent
Benchmark · FailSafeQA. Filings: SEC EDGAR (BlackRock, Microsoft, Snowflake; Innovator ETFs Trust —
KOCT 497K and NPORT-P, with sibling-series N-PORTs as packaged distractors).
