# content/ — plain-language write-ups

These are the **LinkedIn write-ups and research** that accompany the eval suite — the human-facing
half of the repo. Each one turns a runnable eval into a short, plain-language story: a concrete
finance failure mode, what it would take for an AI to catch it, and what actually happened when one
was tested. They are drafts (publish manually; on LinkedIn the repo link goes in the first comment,
not the post body).

## Each eval has a write-up

| Eval (run it from the repo root) | Write-up(s) in this folder |
|---|---|
| **#1 — Earnings analysis** | [`linkedin-followup-1-judgment.txt`](linkedin-followup-1-judgment.txt) — judgment vs. arithmetic |
| **#2 — Buffer ETF diligence** | [`linkedin-post-eval2.md`](linkedin-post-eval2.md) · [`linkedin-article-eval2.md`](linkedin-article-eval2.md) (long-form) · [`linkedin-followup-2-freelunch.txt`](linkedin-followup-2-freelunch.txt) — the free-lunch gate · [`linkedin-followup-3-midperiod.txt`](linkedin-followup-3-midperiod.txt) — recompute vs. quote |
| **#3 — DCF valuation** | [`linkedin-post-eval3.txt`](linkedin-post-eval3.txt) · [`linkedin-article-eval3.txt`](linkedin-article-eval3.txt) (long-form) |
| **#4 — Creation/redemption reconciliation** | [`linkedin-post-eval4-custodian.txt`](linkedin-post-eval4-custodian.txt) — the back-office tie-out (hero: [`assets/hero-eval4.png`](../assets/hero-eval4.png)) |

## The "can AI replace the analyst?" series

The follow-up posts run as one thread — each pairs a vivid, domain-specific failure with a general
AI-trust lesson:

1. [`linkedin-followup-1-judgment.txt`](linkedin-followup-1-judgment.txt) — the failure that isn't being wrong
2. [`linkedin-followup-2-freelunch.txt`](linkedin-followup-2-freelunch.txt) — protection is never free (eval #2)
3. [`linkedin-followup-3-midperiod.txt`](linkedin-followup-3-midperiod.txt) — does it recompute, or just quote? (eval #2)
4. [`linkedin-followup-4-sycophancy.txt`](linkedin-followup-4-sycophancy.txt) — does it know what it knows? (eval #3 WACC probe + eval #4's reconciliation control)

…and the custodian post ([`linkedin-post-eval4-custodian.txt`](linkedin-post-eval4-custodian.txt)) is
the capstone: the same trust question on the back-office core, backed by a real three-model run.

## Research

[`research-brief-ai-analyst-2026.md`](research-brief-ai-analyst-2026.md) — a fact-checked briefing on
what firms are actually struggling with when deploying AI for analyst work (2025–2026), with
per-source credibility caveats and a do-not-cite list. The source material the series draws on.

> The `*-plaintext.txt` files are pure-ASCII versions of the Markdown posts (straight quotes, no
> em-dashes) for pasting straight into the LinkedIn composer.
