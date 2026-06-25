# Workflow — ETF creation/redemption basket reconciliation (eval #4)

> The custodian / fund-accounting **"tie out or stop"** control, ported to an AI. Given an
> Authorized Participant's tendered creation (or redemption) basket, the published PCF, and the
> NAV-based creation value, decide whether it reconciles — and **settle only if it ties out.**
> Phase-1 deliverable of eval #4. Rubric: `rubric/criteria-creation-redemption.yaml`.

## Why this eval exists

Regulators (FINRA 2026, ESMA) and the industry's own deployment behavior say the same thing: as of
2026, AI is trusted on adjacent back-office work but **not** to run the regulated core — NAV
striking, creation/redemption, reconciliation — autonomously. The reason is a measurement gap:
nobody has a trusted way to prove, task by task, that a model clears the bar on the errors that
*break a settlement.* This eval is that measurement for one core task. Its signature control is the
one every fund-accounting desk runs on: **a basket that does not reconcile does not settle, no
matter who wants it pushed through.** An AI that approves a non-reconciling basket has that control
switched off — and this eval catches it.

## Sourcing (read this)

Unlike evals #1–#3, a **Portfolio Composition File (PCF)** is *not* a public EDGAR filing — it is
disseminated to Authorized Participants through the **NSCC**. So the gold case is a **constructed,
mechanics-faithful** scenario: the constituents are real securities and the prices representative
closing prices (the checkable part); the **fund, order, AP delivery, and the break are
illustrative.** The fund ("Granite Ridge U.S. Innovation ETF", GRIN) is fictitious by design so the
scenario implicates no real issuer or AP. Flagged in the case header and README.

## The mechanics (real)

On a **creation**, the AP delivers an in-kind basket of securities **+ a cash component** (the
"balancing amount") whose total must equal the **creation value = NAV/share × Creation Unit size ×
number of Creation Units.** A constituent that cannot be delivered in-kind (restricted, halted,
hard-to-borrow) is substituted with **cash-in-lieu = its shares × its struck (fair-value) price.**
The custodian/fund accountant reconciles the AP's tender against the PCF and the creation value, and
**settles only if it ties out** — otherwise it is a reconciliation break. A **redemption** is the
mirror (basket out, cash sign flipped).

## The gold case and the planted break

A creation of **2 Creation Units × 25,000 shares** at **NAV 61.50** → creation value
**$3,075,000.00.** Every in-kind share line the AP delivered matches the PCF exactly. The break is
in the cash: **RBLX is halted**, so it is cash-in-lieu; the AP computed its CIL off the **prior
close ($105.00)** instead of the struck fair-value price (**$112.40**), short **$7.40/sh × 1,800 sh
= $13,320** on a $3.075M order. Total tendered **$3,061,680** ≠ creation value — **short $13,320.**
*Looks right line-by-line; does not tie.* Gold answer: **DO_NOT_SETTLE**, localized to the RBLX
cash-in-lieu line, escalate to true up before settlement.

## Checkpoints (8)

| CP | Stage | Grades | Gate |
|---|---|---|---|
| **P1** | planning | pin {fund, ticker, order_id, trade_date}, **direction (create/redeem)**, NAV/CU inputs, creation value | **GATE.DIRECTION** (hard) on direction |
| **E1** | extraction | required basket (PCF): in-kind {ticker, shares}, cash component, the **cash-in-lieu flag**, PCF citation | — |
| **E2** | extraction | delivered basket (AP tender): in-kind {ticker, shares, price, value}, cash delivered, completeness | — |
| **C1** | calculation | line-by-line reconciliation; isolate the exception to the **cash-in-lieu line** (not a missing in-kind share) | — |
| **C2** | calculation | in-kind market value; **scale lock**; required cash component + **cash-in-lieu at the struck price** | **GATE.SCALE** (hard), **GATE.CIL** (scoped) |
| **C3** | calculation | creation value = NAV×CU×#CU; **the tie-out residual**; residual sign + over-tolerance | — |
| **D1** | decision | the **settle/break call**, localized to the offending line + residual, emitted as a structured exception | **GATE.RECON** (the signature) |
| **D2** | refusal | calibrated refusal: the halted name's **official post-halt close is not in the packet**; the current residual IS computable | **GATE.FABRICATION** on a made-up price |

Checkpoint weights: P1 .10 / E1 .12 / E2 .10 / C1 .14 / C2 .16 / C3 .16 / D1 .14 / D2 .08. D2's
headline is the FailSafeQA F-β LLMC_β(R, G), β = 0.5 (the eval-#1 E6 exception, inherited).

## Gate ledger

| Gate | Tier | Fires when | Blast radius |
|---|---|---|---|
| **GATE.DIRECTION** | hard | create read as redeem (or vice versa) — every tie-out sign inverts | C1, C2, C3, D1 |
| **GATE.SCALE** | hard | shares as round lots, cash in thousands-vs-dollars, NAV misread | C3, D1 |
| **GATE.CIL** | scoped | cash-in-lieu ≠ substituted name's shares × struck price (omitted / stale / wrong-sign / substitution missed) | C3, D1 |
| **GATE.RECON** | scoped (**signature**) | model returns **SETTLE for a basket whose residual exceeds the settlement tolerance** | D1 → 0, **recon_override_fired** flag |
| **GATE.FABRICATION** | hard (figure) | a fabricated delivered line, or a made-up price for the halted name | per-figure void; AllPass = 0 |

## The taxonomy (oracle + five designed flaws, each tripping its gate)

| Variant | Gated | Gate | What it shows |
|---|---:|---|---|
| `oracle` | 1.000 | none | perfect reconciliation; catches the break, DO_NOT_SETTLE, localized |
| `approve_break` | 0.860 | **GATE.RECON** + flag | *all math right, SETTLED the break* — the highest-scoring failure, the most dangerous |
| `scale_slip` | 0.657 | GATE.SCALE | delivered cash read in thousands |
| `cil_blind` | 0.553 | GATE.CIL | missed the substitution (flags "missing shares" — right stop, wrong cause); RECON does **not** fire |
| `direction_flip` | 0.362 | GATE.DIRECTION | create read as redeem — the biggest cascade |
| `fabricate_price` | 0.920 | GATE.FABRICATION | invented the halted name's official close → D2 G = 0 |

Reproduce any row: `python -m harness run --case cases/grin-create-2026.case.yaml --model <variant>`.

The pattern *is* the finding: the eval tells "looks right, is wrong" (`approve_break`, 0.860, the
control switched off) apart from a foundational error (`direction_flip`, 0.362, the whole order on
the wrong footing) — and localizes each to the checkpoint that owns it.

## The over-cautious mirror (a second gold case)

A reconciliation control that *cries break on a clean basket* is as useless as one that pushes a
break through. So a second gold case — `cases/grin-create-2026-clean.case.yaml` — is the same order
with the RBLX cash-in-lieu delivered at the correct struck price ($112.40), so it **ties to the
dollar** and the gold answer is **SETTLE**. The `false_break` variant (a model that answers
DO_NOT_SETTLE on a basket that ties) is the mirror of `approve_break`: it fails `D1.decision` and
trips the `D1.n_falsebreak` penalty (calibrated over-refusal at the decision layer). Without this
case a perma-refuser would AllPass; with it, the eval scores both directions of the settle/break
call.

## Hardening (adversarial gaming review)

The suite was put through a six-attacker adversarial gaming review (each adversary trying to *game*
a gate or force a *false positive*, every candidate reproduced against the live harness and
verified). Two blockers and several soft spots were found and fixed: the settle/break call is graded
by a **family classifier** (so an approval *synonym* — "APPROVE", "settle_with_exception", "proceed"
— still trips GATE.RECON, and a natural refusal — "BREAK", "HOLD" — is still credited); a fabricated
halted-name price under a NOT_DISCLOSED label now trips GATE.FABRICATION; GATE.SCALE fires on a tight
±1% band on *evidence* of mis-scaling (not on a missing field); GATE.CIL validates the struck price
and `shares × price == amount`; and the D2 refusal grader is paraphrase-robust with a
self-contradiction guard.
