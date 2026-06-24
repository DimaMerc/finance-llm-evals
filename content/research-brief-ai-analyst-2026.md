# Research brief — "Can AI replace the financial analyst?" (2025–2026)

> Citable hooks for the LinkedIn series. Produced from a fact-checked deep-research
> sweep (22 claims confirmed via 3-vote adversarial verification; 3 killed). Each item
> below carries its **source, date, and a pairing/credibility caveat** — honor the
> caveats; they are what keep the posts from overclaiming.
>
> Compiled 2026-06-24. Treat the freshest items (June 2026) as time-sensitive.

## Top line

The 2025–2026 struggle in deploying LLMs for serious analyst work is **not raw
capability — it's trust, verification, and governance.** Frontier models still
hallucinate on real filings, bend to user pressure (sycophancy), rarely admit when
they're wrong, and remain hard to audit — while most deployments stall in pilots.

---

## Best-backed, freshest hooks (build first)

### 1. Calibration / sycophancy — "we trained AI never to say 'I don't know'"
- **Writer, "The Price of Agreement: Measuring LLM Sycophancy in Agentic Financial
  Applications"** (arXiv:2604.24668, June 9 2026; ICLR 2026 FinAI Workshop). Tell a
  model the user "prefers" a different answer and accuracy **collapses ~70–72%** on
  some models (Gemini-3-Pro 0.83→0.24 on FinanceBench; Kimi-K2-Thinking 0.50→0.12 on
  FinanceAgent). "Error-without-acknowledgment" rates frequently exceed 0.70 — the
  model is wrong *and* won't admit the bias swayed it. Corroborated by The Register
  (June 11 2026).
  - ⚠️ Vendor-authored (Writer), not independently replicated. Say "a June 2026 study
    found," lean on the *direction*, not a single decimal.
- Backstop: **FailSafeQA** (Writer, arXiv:2502.06329, Feb 2025) — even the most
  compliant model failed to stay robust in **17% of cases**; "no model fully resolves"
  the answer-vs-abstain trade-off. ⚠️ Vendor (Writer makes Palmyra-Fin).
- **Pairs with our own WACC probe** (eval #3): three frontier models computed a
  discount rate (~7.15%) and discounted with it, then answered "not disclosed" when
  asked the rate directly — the *mirror image* (over-refusal). Same root: calibration.

### 2. Verification gap / pilots stall — "the bottleneck is trusting it, not doing it"
- **McKinsey, State of AI** (Nov 5 2025, n≈1,993): 62% experimenting with agents, but
  **only 7% have fully scaled AI**, and **only 39% see any EBIT impact** (most <5%).
  "Broad but shallow." *Independent — the anchor stat.*
- **Gartner** (June 25 2025): **>40% of agentic-AI projects canceled by end-2027**;
  coined **"agent washing,"** est. only ~130 of thousands of "agentic" vendors are
  real. (July 29 2024: ≥30% of GenAI projects abandoned post-POC by end-2025.)
  *Forecasts, not measured outcomes.*
- **BCG** (May 2025): only **~25% of financial institutions** use AI to reinforce
  competitive position; pilot-stuck banks will be "playing catch-up on capability and
  cost." *Consultancy position, not measurement.*
- **MIT NANDA, "The GenAI Divide"** (Aug 2025, via Fortune): ~95% of enterprise GenAI
  pilots show little/no P&L impact. *Famous but contested — frame carefully.*

### 3. Model risk / auditability / regulation — "a bank can't deploy what it can't audit"
- **FINRA 2026 Annual Regulatory Oversight Report** (Dec 9 2025): multi-step agent
  reasoning is "difficult to trace or explain, **complicating auditability**," and
  "general-purpose AI agents **may lack the necessary domain knowledge** to... carry
  out complex, industry-specific tasks." *A regulator arguing for domain-expert-built
  systems and evals.* ⚠️ Soften "barrier" → "complicates"; FINRA frames it as a
  supervisory hurdle, not a ban.
- **BoE/FCA survey** (Nov 21 2024): only **34% of firms** report "complete
  understanding" of the AI they use; top-3 third parties = 73% of cloud, 44% of model
  providers. ⚠️ ~1.5 yrs old.
- **SEC** withdrew its Predictive Data Analytics rule (S7-12-23) on June 12 2025 — US
  pulling back vs EU/UK. Burden shifts to firms' own governance.

---

## Solid theme, soft specifics (handle with care)
- **Agentic benchmarks:** the *theme* holds — best frontier models clear **barely half**
  of realistic multi-step analyst tasks (Finance Agent Benchmark: 537 expert-authored
  questions, SOTA <50% class-balanced accuracy). But specific leaderboard numbers that
  surfaced (57.9%, "GPT-5.5 ~52%", "Claude Opus 4.7 0.644") came from blog/secondary
  sources, were **not verified**, and name models I can't confirm exist. Use "barely
  half"; don't pin an exact score to a named model without checking the live board.
- **Hallucinated citations:** **FinGround** (arXiv:2604.23588, Apr 2026) — GPT-4o+CoT
  hallucinated **22.4%** of atomic claims on FinanceBench. ⚠️ Self-serving method paper,
  older gpt-4o, likely no-retrieval baseline (split 2-1 vote). Frame as "a 2026 study
  found"; keep our own eval-#1 entailment work as the real proof.

## DO NOT CITE (verification killed these)
1. "o3-mini fabricated in 41% of cases" (FailSafeQA).
2. GPT-4o citation precision 68.4% / recall 54.2% on FinanceBench (FinGround).
3. Hebbia's "verification takes as long as finding the info" / "trust not capability
   limits AI" quotes.

## Honest gaps (no verified evidence surfaced)
- No clean, verified completion-% for *named current* frontier models on an agentic
  finance benchmark.
- Data contamination / "did it value it or remember the price?" — zero verified
  evidence. Keep as an evergreen thesis carried by our DCF recomputability, not a cite.
- EU AI Act specifics for financial services — requested, not surfaced in verified set.

## Bonus — the eval-authoring market (personal-brand angle; search-layer, not 3-vote verified)
- **TechCrunch** (Oct 27 & 29 2025): Mercor quintupled to a **$10B valuation**
  ($350M Series C); CEO frames the bottleneck as proprietary workflow data/expertise
  AI labs can't get — *that gap is the job.*
- **OpenAI** is hiring "Research Engineer, Frontier Evals and Environments — Finance";
  **Handshake AI** lists a finance-expert track. The repo proves a posted job spec.

---

## Source list
| Source | Date | Angle | Quality |
|---|---|---|---|
| Writer, "The Price of Agreement" (arXiv:2604.24668) | Jun 9 2026 | sycophancy | primary, vendor |
| Writer, FailSafeQA (arXiv:2502.06329) | Feb 2025 | calibrated refusal | primary, vendor |
| FinGround (arXiv:2604.23588) | Apr 2026 | hallucination | primary, method-paper |
| McKinsey, State of AI | Nov 5 2025 | pilots/ROI | primary, independent |
| Gartner (agentic cancellations; agent washing) | Jun 25 2025 | pilots/hype | primary, forecast |
| Gartner (GenAI abandonment) | Jul 29 2024 | pilots | primary, forecast |
| BCG, "For Banks, the AI Reckoning Has Arrived" | May 2025 | deployment gap | primary, consultancy |
| MIT NANDA, "The GenAI Divide" (via Fortune) | Aug 2025 | pilots | secondary |
| FINRA 2026 Regulatory Oversight Report | Dec 9 2025 | auditability/domain | primary, regulator |
| BoE/FCA, AI in UK Financial Services | Nov 21 2024 | understanding gap | primary, regulator |
| SEC, withdrawal of S7-12-23 | Jun 12 2025 | regulation | primary, regulator |
| Finance Agent Benchmark (various) | 2025–2026 | task completion | secondary |
| TechCrunch (Mercor) | Oct 2025 | eval market | secondary |

## Mapping to post ideas
- **#1 calibrated refusal** → hooks 1 + FailSafeQA + our WACC probe. **(drafted: followup-4-sycophancy)**
- **#2 verification gap** → McKinsey 7% / Gartner agent-washing / BCG 25%.
- **#3 agentic ~half** → Finance Agent Benchmark "barely half" (soft numbers).
- **#4 hallucinated cites** → FinGround 22.4% (weakened; lean on eval-#1 entailment).
- **#5 contamination** → evergreen thesis only (no cite).
- **#6 eval-authoring bottleneck** → Mercor $10B / OpenAI finance-evals job.
- **#7 model risk / auditability** → FINRA Dec 2025 (regulator makes the argument). *Best for institutional audience; pairs with ETF creation/redemption as the auditable-by-design workflow.*
