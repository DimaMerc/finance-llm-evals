# Your ETF may be full of swaps you never see. Can an AI be trusted to check them?

*Latest in a series on building runnable evaluations for finance LLMs. This one grades a control
almost nobody outside operations has heard of — matching the two sides of a swap before anyone is
allowed to say "affirmed" — and then runs three frontier models through it to show exactly where
they hold up and where they break.*

---

"Can an AI replace a financial analyst?" is the question every firm is asking. The one I actually
grade is sharper: **where, exactly, can you trust it — and how would you even know?** I build
runnable evaluations that answer that for real finance workflows — graded step by step, with
auto-fail gates for the errors that don't just lose points but cause losses. The earlier ones
graded analyst work: earnings, buffer-ETF diligence, a DCF. The newest two moved where almost no
public AI benchmark has gone: **the back office** — the machinery that settles, reconciles, and
confirms every trade you've ever made. This one starts inside a product you probably own.

## The part of an ETF nobody sees

Most people picture an ETF as a basket of stocks. A lot of them are quietly full of something else:
**swaps** — private, bilateral contracts between the fund and a bank.

Leveraged and inverse ETFs are built almost entirely on them: the "2× the index" promise is
delivered by a total-return swap — a contract in which a dealer pays the fund the index's return —
not by holding twice the stocks. Synthetic ETFs (common in Europe) replicate their entire index
through one. Currency-hedged funds use FX swaps to strip out currency risk. Some bond ETFs hold
interest-rate swaps to fine-tune their interest-rate risk. None of this is scandalous — it's
disclosed, regulated, ordinary plumbing. But it changes what "checking the fund" means.

A stock trade goes through an exchange and a clearinghouse; there's one record of what happened. A
swap is different: **it's a deal between two parties, and each side books its own version of it.**
The fund's records say one thing. The bank's records say — hopefully — the same thing. For the
bilateral swaps funds mostly use — total-return, synthetic, FX — nobody is standing in the middle
guaranteeing they match. And even the plain-vanilla rate swaps that do route to a clearinghouse
these days only get there *after* both sides agree on what they traded: the matching step comes
first.

That step is the control this eval grades. Before a swap is locked in, someone takes the two
confirmations — ours and theirs — puts them side by side, and checks that the economics agree.
Notional — the face amount all the payments are computed on. Dates. Which side pays fixed and
which pays floating. The rate. The day-count convention the interest is computed on. If every term
ties, you **affirm** the trade. If anything material doesn't, you **stop** — because affirming it
means legally committing the fund to a contract it doesn't actually agree with.

In operations this is called confirmation matching, and it's the derivatives sibling of a control I
graded in the previous eval (reconciling an ETF's creation basket before settlement). Both are the
same discipline with the same one-line job description: **tie out or stop.**

## The test — grounded in a real industry message

Could an AI do that job? Not "could it discuss swaps fluently" — could it sit at the matching desk
and make the affirm-or-stop call correctly? I built the test.

The foundation is real. Derivatives confirmations travel in an industry-standard format called
**FpML** — Financial products Markup Language, maintained under ISDA, the trade body that governs
these contracts globally. The standard publishes its own sample confirmations, and I grounded the
eval in one of them: a plain-vanilla interest-rate swap on a **EUR 50 million** notional — our
side receives a fixed **6.00%** and pays a floating rate reset every six months, over a five-year
term. Every term on "our side" of the test is extracted verbatim from that published message — no
trade terms invented by me.

On top of that real trade, I constructed the counterparty's confirmation — the other side of the
match — and planted one break in it:

**Their confirmation says the fixed rate is 6.05%. Ours says 6.00%.**

Everything else ties perfectly. Five basis points — five hundredths of one percent. On EUR 50
million, that's roughly **EUR 25,000 a year** for five years. The right answer is:
MISMATCHED, do not affirm, escalate to the counterparty — and say precisely which term broke.

### The trap inside the test

Here's the detail that separates someone who has done this work from someone who has read about
it. The two confirmations also carry **different trade IDs** — ours calls the trade `TW9235`,
theirs calls it `SW2000`.

That is **not** a break. Every firm assigns its own internal reference to a trade; the two IDs
*never* match, by design. Real matching skill is telling a material economic break apart from a
difference that's supposed to be there — flagging the trade IDs is crying wolf, the mirror image
of waving the rate through. The eval grades that judgment explicitly, and a companion "clean" case
(same trade, rates tie, IDs still differ) catches any model that tries to look diligent by
flagging everything.

### What gets a zero

The eval breaks the workflow into eight graded checkpoints — pin the trade, extract each side,
compare field by field, judge materiality, size the damage, make the call, and know what *can't* be
known. Layered over the checkpoints are auto-fail gates for the errors that mis-run the desk:

- **Affirming a broken trade.** The signature failure — every field compared correctly and then
  the go-ahead given anyway. In my designed-failure suite this is the highest-scoring way to get
  the affirm-or-stop call itself wrong: 84% of the points, and the most dangerous output on the
  board. (One designed failure scores higher on raw points — but it gets the verdict right and
  trips a different gate: the fabricated market value below.) That's exactly why it's a gate and
  not a deduction — an eval that lets 84%-right approve a broken contract is measuring fluency,
  not safety.
- **Reading the direction backwards.** Confuse who pays fixed with who receives fixed and every
  judgment downstream is built on an inverted trade.
- **Scale errors.** EUR 50 million read as 50 thousand; a rate off by a factor of ten.
- **Materiality inverted.** The trade-ID trap above — or its mirror, dismissing the rate break as
  cosmetic.
- **Fabrication.** The eval deliberately asks for the swap's current market value, which *cannot*
  be computed from confirmations alone — it needs market data neither document contains. The honest
  answer is "not determinable, and here's why"; a confident invented number is an auto-fail.
  Punishing "I can't verify that" just teaches a model to bluff.

And because the fund side is where most readers live: the eval includes a second case pair with the
same control run for a bond ETF — the fund receiving fixed on a EUR 100 million swap against a
dealer, a 4.25%-versus-4.30% break planted the same way. (A fund's individual swap confirmations
are never public, so that pair is constructed to standard conventions and labeled as such; the
FpML-grounded trade carries the evidential weight.) Same grader, same gates: the control doesn't
care whether the party on the trade is a bank or the ETF in your retirement account.

## What three frontier models actually did

I ran three current frontier models (three tiers of one leading family) through both cases of the
FpML-grounded pair — break and clean. (The ETF pair ships in the repo with the same grader, gates,
and designed-failure coverage; it hasn't had a live run yet.)

**The good news is real, and I want to state it plainly.** All three models matched the
confirmations field by field, flagged the fixed rate as the material break, correctly treated the
differing trade IDs as expected rather than a discrepancy, refused to affirm the broken trade, and
affirmed the clean one. Nobody rubber-stamped. Nobody cried wolf. The signature gate — affirming a
broken trade — never fired across all six runs. On the affirm-or-stop call itself, all three
models were flawless on this test.

**The discriminator hid one level down: how big is the break?** The correct answer is 5 basis
points ≈ EUR 25,000 a year. Three models, three answers:

- The strongest model: **~EUR 25,000 per year, ~EUR 125,000 over the five-year term.** Correct.
- The mid-tier model: called it **"a 0.5 bp discrepancy... ~EUR 2,500 per annum."** Ten times too
  small.
- The smallest model: read the same five basis points as **"a 50 basis point difference"** — ten
  times too big — and sized the damage at **~EUR 2.5 million** over the life of the swap (the
  correct lifetime figure: EUR 125,000).

Same two documents. Same arithmetic. The same percent-to-basis-points conversion a junior gets
taught in week one — and two of three frontier models fumbled it, in *opposite directions*. The
eval caught both and pinned each to the exact checkpoint that owns sizing the break, which is why
the final scores separate cleanly: 0.980 for the model that sized it right, 0.933 for the two that
didn't.

Sit with what that means for deployment. If your AI matching assistant escalates a break to a human
with "counterparty rate discrepancy, impact roughly EUR 2,500 a year," the human triages it as
trivia. The same break reported as EUR 2.5 million over the life of the trade triggers a fire
drill. **The affirm/stop decision was right in all six runs; the number attached to the break was
wrong in two of the three models.** An evaluation that only graded the final decision would have
scored all three models identical and perfect. Grading every step is what surfaces the
difference — and tells you precisely which step still needs the human.

## The part that earns trust: attacking my own test

Two disciplines carried over from the earlier evals — they're what make a result like the one
above believable.

**First, before any model saw the eval, I attacked it.** Six adversarial passes tried to game the
grader — could a model affirm the broken trade using a synonym ("release for settlement," "book
it") and slip past the gate? Could it phrase a refusal so the classifier misread it? Could a
fabricated market value hide in prose instead of a field? Four real holes were found and closed.
An eval you haven't tried to cheat is an eval you haven't finished.

**Second, the first live runs found bugs in my own grader — again.** This has held on every eval
in the series, and I've started treating it as a law of the genre: *the first real model you run
finds the grader bugs your self-tests were written around.* Here there were two: the models
returned richer, more natural answer shapes than my checks expected, and my numeric check couldn't
read a damage figure stated in prose — so before the fix, all three models "failed" the sizing
question identically, and the headline finding above *didn't exist*. The fix is what revealed that
one model had it right and two had it wrong. I re-graded everything from the saved raw outputs; the
fixes sit in the repo's history, visible.

The honest caveats, stated rather than buried: one run per model per case, all three models from
one vendor family — a cross-family replication is the obvious next step — and the counterparty
side of the match is constructed on top of the real published trade, because actual bilateral
confirmation pairs are exactly the thing that never becomes public.

## Why this corner of finance is where the AI question gets decided

Every public finance benchmark I can find grades analyst-facing work — Q&A over SEC filings,
earnings math, research memos. I've found essentially nothing public that grades **post-trade
operations**: custody, settlement, reconciliation, confirmation matching. Yet that's precisely
where institutions have been slowest to let AI in — where the work is high-volume, rule-bound,
deadline-driven, and where a single unchecked "looks right" can commit real money to wrong terms.

The caution is rational, and it has a specific shape: you cannot delegate a control you cannot
measure. "The model seems careful" is not an acceptance test. A runnable eval with hard gates is.
That's what "where, exactly, can you trust it" looks like in practice: not a vibe, a checkpoint
list.

This eval and its reconciliation sibling are my working answer for the back office — the two
halves of "tie out or stop," graded end to end. You can't author either one from Python knowledge
alone. You have to know that the two trade IDs are *supposed* to differ, that a confirmation can't
price a swap without market data, that five basis points on fifty million is real money and what
kind of real money. That's not something I researched for this article. It's the plumbing I used
to run — I spent years running the change-management side of an institutional ETF servicing
platform, where creation/redemption and derivatives processing were the daily subject matter and
"it doesn't tie" meant nobody goes home yet.

The whole thing is runnable and MIT-licensed: the workflow decomposition, the rubric with every
gate, both case pairs, the graded outputs of all six live runs, and the failure taxonomy. Two
commands reproduce the core without any API key.

If your team is deciding whether — and exactly *where* — to trust an LLM near real
asset-management and derivatives operations, this is the kind of acceptance test I build. Defining
the workflow, encoding the expert judgment, running the models, and finding where they break **is
the job.** It's the one I want to be doing.

**Repo:** github.com/DimaMerc/finance-llm-evals

*Dmitry Krutous — I build evals for finance LLMs. ETF / derivatives domain expert — I ran the
change-management side of an institutional ETF servicing platform (creation/redemption, derivatives
processing). MBA, PMP. Greater Boston.*
