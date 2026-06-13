# Can an AI do an analyst's job? The useful question is *where you can trust it* — so I built the test

*Second in a series on building runnable evaluations for finance LLMs. This one grades the workflow
almost nobody can grade — buffer-ETF diligence — and then runs real models through it to show
exactly where they hold up and where they break.*

---

"Can an AI replace a financial analyst?" is the question every firm is asking — and the wrong one to
lead with. A model can produce a flawless-looking memo and be confidently, invisibly wrong on the
one number that decides the call. So the useful question is sharper: **where, exactly, can you trust
it — and how would you even know?**

Everyone asks the first question. Almost no one measures the second. That's the work I do: runnable
evaluations that put an AI through a real analyst workflow and grade every figure against the source
filing — with auto-fail "gates" for the errors that quietly poison a memo, and credit for *saying
"I can't verify that"* instead of guessing.

My first one graded quarterly earnings analysis — a workflow most people understand, so anyone could
check my work. It made a simple point: *"looks right" is not "is right."* A model can write a fluent
memo and still have misread "in thousands" as "in millions," poisoning every number downstream. The
fair next question from anyone hiring in this space is sharper: *can you build the eval that needs
**you** — the one a smart generalist with a Python notebook can't fake?*

This is that one. One model got the headline math right every time; the other missed it every
time — and yet **both fell into the exact same trap.** That contrast is what a good eval is built to
surface.

## The product almost no one stress-tests

Roughly $80 billion now sits in **defined-outcome ETFs** — the "buffer" funds you've seen advertised
with a **cap** ("up to ~17% upside") and a **buffer** ("first 15% of losses absorbed"). They're sold
as a defined outcome. The marketing is clean and reassuring.

Here's the catch that matters, and that an advisor reading the fact sheet to a client can miss:
**those numbers only hold for someone who bought on day one of the fund's outcome period.** Buy in
the middle — which is when almost everyone actually buys — and you get something different.
Sometimes very different. After a rally, the "17% cap" might be **6% of upside left** with most of
the downside still live. After a drawdown, a buffer that's "15%" on the brochure can be **partly
used up already** — not breached, but not what the label says either.

And there's a deeper truth the brochure never volunteers: **protection is never free.** A buffer
ETF pays for your downside cushion by capping your upside — literally, the fund sells away your
gains above a certain level to fund the protection. Any analysis that describes the protection and
*not* its cost is describing a free lunch that does not exist. In my prior life running the
change-management side of an ETF servicing platform — creation/redemption, derivatives processing —
"this position doesn't reconcile to its stated terms" wasn't a rounding note. It was a break.

So: can an AI do this diligence correctly — pin the right fund, recompute the real terms for a
mid-period buyer, and refuse to sell the free lunch? I built a test that grades exactly that, and
**auto-fails any memo that claims protection with no cost.** I call it the free-lunch gate.

## How the test works (without the jargon)

A buffer ETF is, under the wrapper, **four stock-option contracts**. Every number in the
marketing — the cap, the buffer, the max loss — is a direct mathematical consequence of four
strike prices. That's the key that makes a rigorous eval possible.

So the test refuses to take the brochure's word for anything. It makes the model **recompute the
marketing from the actual option holdings** the fund files with the SEC — a separate document from
the prospectus. The elegant part: the prospectus and the holdings report **share no number at
all.** The prospectus says "17.18% cap"; the holdings report lists option strikes. They tie
together *only* through the options math. A model that can't do that math can't fake its way
through.

On top of that, the eval has **auto-fail gates** for the handful of errors that don't just lose
points — they mis-sell the product:

- **Wrong fund.** The issuer runs twelve near-identical monthly versions of the same fund; the
  filings land the same day with adjacent ID numbers. Analyze October's holdings against November's
  terms and everything downstream is poisoned. (The distractor is built right into the real source
  data — the sibling funds are in the packet.)
- **Wrong scale.** The option strikes are quoted on the underlying ETF's share price (~$242), not
  the index it tracks (~2,400). Read them as index levels and you're off by 10×.
- **The free lunch.** Assert downside protection without the structured cost behind it → the
  suitability sections of the memo are zeroed and the whole thing is flagged in the headline.

And one more thing I care about a lot: **calibrated uncertainty.** The eval asks for a number that
genuinely is *not* in the SEC filings — today's remaining cap, which issuers publish only on their
websites. The honest answers are "here's how to compute it from these inputs" or "not disclosed,
and here's exactly why." A confident guess is a failure. Punishing "I can't verify that" would just
teach a model to bluff; rewarding it is the whole point.

## What real models actually did

I then ran two real, open-weight models through it — locally, at zero API cost — across three
market snapshots of a real fund (an Innovator U.S. Small Cap Power Buffer ETF whose four filed
strikes reproduce its advertised 17.18% / 15% terms to within a rounding error): a **real, cited
anchor** (a recent post-rally state), plus two **clearly-labeled hypotheticals** — a near-cap state
and a consumed-buffer state.

The pattern was consistent and, I think, genuinely useful to anyone deciding whether to trust one of
these models:

- **Extraction was perfect on both.** Every stated term and every option leg, exact to the cent,
  cited.
- **On the headline number, they split.** Asked for the remaining cap a buyer gets *today*, the
  smaller reasoning model nailed it in every run with a clean derivation; the larger non-reasoning
  model missed it every time — once reusing the same wrong figure across two different snapshots,
  once inverting the risk state entirely. Size lost to step-by-step reasoning, decisively, on the
  exact step that matters most.
- **Both fell into the same trap.** Asked to reconstruct the fund's payoff table in dollars, both
  filled it in *percentages* — following the format the prospectus happens to print instead of the
  reconstruction actually requested. Two different models making the identical mistake is the
  signal you want from an eval: it's catching something hard about the **task**, not a quirk of one
  model. (Both models share a vendor lineage, so I'm calling this *suggestive*, not proven —
  replicating it on an unrelated family is on the list.)
- **The designed traps fired.** On the consumed-buffer case, a model computed the correct *enlarged*
  remaining cap (+18%) and then still labeled the partly-used buffer "intact." Right arithmetic,
  wrong read of the actual risk state — exactly the failure the case was built to isolate.

One more design result I'm proud of. The common worry with LLM evals is that the "AI judges AI"
part is squishy — so I built this one **calculation-heavy on purpose**, with the subjective judge
confined to the final write-up. The proof: swapping the offline grader for a real LLM judge moved
the scores by only **2 to 4.5 points** here, versus **14.7** on the earnings eval. The headline
barely depends on the squishy part — by construction.

## So — can an AI do this job yet?

Here's the honest read, and it's more useful than a hot take. The shape is the same across the three
models I've run on these two evals: today's models are powerful **extractors** and reliable
**single-step calculators** — they pull every figure, cite it, and (when they reason step by step)
nail the one headline computation — and they are unreliable **multi-step reasoners and
judgment-callers**: they conflate conventions, echo a stated number instead of re-deriving it, and
misread the risk state even after getting the arithmetic right.

That is not "replace the analyst." It's **augment the analyst, with guardrails** — let the model do
the pulling and the tabulating, and keep a human (or a hard gate) on the synthesis and the risk
read: specifically the payoff-table reconstruction and the buffer-state call, the two checkpoints
both models failed. The point of the eval is that it doesn't just say *that* — it tells you **exactly
which checkpoints** need the guardrail, on which kind of task. That's the difference between an
opinion and an acceptance test.

## The part that earns trust: it caught my own mistakes

The strongest evidence the rig is real is that running live models found bugs in my own grader —
three of them, the kind my synthetic tests structurally couldn't catch because I'd written the
tests around my own assumptions. A model wrote "power_buffer" where my code wanted "buffer" and got
dinged for an error it didn't make; the fund's real cash holding got miscounted as a fabricated
option; a labeling rule lived only in my answer key and not in the model's instructions. I fixed
all three and re-graded everything. This seems to be a law of the genre: *the first real model you
run finds the grader bugs your self-tests were written around.*

A verification pass also caught an overclaim in my own write-up: I'd called the two models
"unrelated families" when they're two generations of one vendor's lineage — which weakened a claim
I'd leaned on. I corrected it before publishing. And I hand-graded the AI judge's verdicts against
my own expert read — full agreement on the sample, with the caveats (small sample; the judge graded
its own model's work) stated plainly, not buried.

That's the standard I think this work should be held to. An eval that can't catch its author's
errors has no business grading anyone else's.

## Why this one matters more than the first

The earnings eval proved a method. This one proves the **moat**. You cannot author it without
knowing that a buffer ETF is four FLEX-option legs in a trust wrapper, that the prospectus and the
N-PORT tie only through the strikes, that the cap is *literally* the strike of the call the fund
sold to finance your buffer, and that a partly-consumed buffer is not a breached one. That's not
Python knowledge. It's the plumbing I used to run.

The whole thing is runnable, MIT-licensed, and every gold number is traced to a real SEC filing —
no invented data. Two commands and no API key reproduce the core; one more runs a live model.

If your team is figuring out whether — and exactly *where* — to trust an LLM with real
asset-management work, this repo is a working answer. Defining the workflow, building the eval,
running the models, and finding where they break **is the job.** It's the one I want to be doing.

**Repo:** github.com/DimaMerc/finance-llm-evals · **Methodology paper** in the repo (`PAPER.md`).

*Dmitry Krutous — I build evals for finance LLMs. ETF / derivatives domain expert (ex-BBH ETF
servicing platform — creation/redemption, derivatives processing). MBA, PMP. Greater Boston.*
