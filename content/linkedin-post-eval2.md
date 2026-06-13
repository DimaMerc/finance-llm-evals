# LinkedIn post — eval #2 launch (drives to the article)

---

A "buffer ETF" brochure promises "15% downside protected, 17% upside cap."

If you bought mid-period — which is when almost everyone buys — both numbers can be wrong. And here's
the part the brochure never says: that protection isn't free. The fund pays for your downside cushion
by selling away your upside. Any analysis that describes the protection and not its cost is selling a
free lunch that doesn't exist.

A few weeks ago I published a runnable eval for whether an AI can read an earnings report. The fair
next question: can you build the eval that needs a *domain expert*, not just a coder?

So I built one for **defined-outcome (buffer) ETF diligence** — and it auto-fails any AI memo that
claims protection with no cost. The "free-lunch gate."

I ran two real open models through it. What I found:

→ Both nailed extraction and the one headline calculation.
→ Both fell into the *same* trap reconstructing the payoff — a signal (both are same-vendor lineage,
   so suggestive, not proven) that the eval is catching the task's difficulty, not a model quirk.
→ The designed traps fired: one model computed a buffer's enlarged cap correctly, then still called a
   partly-consumed buffer "intact."
→ And running real models found three bugs in my *own* grader. That's the law of the genre — the
   first real model finds the calibration errors your self-tests were written around.

Runnable, MIT-licensed, every number traced to a real SEC filing.

This is what the role actually is: define the workflow, build the eval, run the models, find where
they break. For finance LLMs.

Full write-up + repo in the comments. 👇

#AI #LLMevaluation #ETFs #AssetManagement #fintech

---

**First comment (post the links here, not in the body — LinkedIn suppresses reach on posts with
outbound links in the body):**

The eval, the methodology paper, and the full failure taxonomy: github.com/DimaMerc/finance-llm-evals
Long-form write-up: [paste the LinkedIn article URL here once it's published]
