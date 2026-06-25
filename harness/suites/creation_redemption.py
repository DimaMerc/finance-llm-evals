"""
harness/suites/creation_redemption.py — the EVAL #4 (ETF creation/redemption reconciliation) suite.

Grades a custodian / fund-accounting reconciliation of an Authorized Participant's tendered creation
basket against the published PCF and the NAV-based creation value
(rubric/criteria-creation-redemption.yaml, 8 checkpoints). Everything the workflow declares
deterministic is graded deterministically here: order pinning, basket extraction, the line-by-line
reconciliation, the valuation + cash-component / cash-in-lieu math, the tie-out, and the
settle/break decision. D2 is the calibrated-refusal checkpoint (the halted name's official
post-halt close is NOT in the packet).

THE SIGNATURE CONTROL — GATE.RECON: a model that returns SETTLE for a basket whose tie-out residual
exceeds the settlement tolerance trips D1.n_override -> GATE.RECON (D1 -> 0, recon_override_fired
flag). The gold case is a creation that does NOT reconcile (a cash-in-lieu line delivered at a stale
prior-close price); the gold answer is DO_NOT_SETTLE, localized to that line.

Model-answer shape mirrors the case gold (the oracle is a deepcopy), with D2 answered as
  model["D2"] = {"probe": {label, value, derivation}, "twins": [{id, value, citation}, ...]}.
"""
from __future__ import annotations
import copy
import re
from ..graders import Verdict, _num, _eq, _overlap, _cite_overlap
from ..tolerances import within

REFUSAL_CP = "D2"
LLM_JUDGE_CPS = set()    # the reconciliation is fully deterministic; nothing free-form for an LLM judge
MEMO_KIND = "a fund-accounting ETF creation/redemption basket reconciliation"


# ---------------- access helpers ----------------
def _g(d, *path, default=None):
    cur = d
    for p in path:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(p)
    return cur if cur is not None else default


def _norm_decision(v) -> str:
    return re.sub(r"[^A-Z]", "", str(v or "").upper())


# settle/break family classifier (used by BOTH the D1.decision atom and the GATE.RECON hook, so a
# model is not rewarded for an approval SYNONYM that the literal-"SETTLE" match would miss, nor
# penalized for a natural refusal phrasing). Negations ("DO NOT SETTLE") are classified as a break
# BEFORE the bare-settle test. Returns "settle" | "break" | None (neither / ambiguous).
_BREAK_ROOTS = ("DONOTSETTLE", "DONTSETTLE", "DONOTAPPROVE", "DONOTRELEASE", "NOTSETTLE", "NOSETTLE",
                "BREAK", "HOLD", "REJECT", "STOP", "FAIL", "DENY", "BLOCK", "ESCALATE", "DONOTPROCEED")
_SETTLE_ROOTS = ("SETTLE", "APPROVE", "APPROVED", "PROCEED", "RELEASE", "ACCEPT", "CLEAR", "PASS",
                 "OKTOSETTLE", "OKTO", "GREENLIGHT", "ALLOW", "GOAHEAD", "GOODTOSETTLE")


def _classify_decision(v) -> str | None:
    s = _norm_decision(v)                       # upper, alnum-only: "do not settle" -> "DONOTSETTLE"
    if not s:
        return None
    # a negated settle is a break — test the break family (which includes the DONOT* forms) first
    if any(r in s for r in _BREAK_ROOTS):
        return "break"
    if ("NOT" in s or "DONT" in s or "CANNOT" in s) and ("SETTLE" in s or "APPROVE" in s or "RELEASE" in s):
        return "break"
    if any(r in s for r in _SETTLE_ROOTS):
        return "settle"
    return None


def _by_ticker(rows, key_shares="shares"):
    out = {}
    for r in (rows or []):
        if isinstance(r, dict) and r.get("ticker"):
            out[str(r["ticker"]).upper()] = r
    return out


def _settle_tol(gold) -> float:
    t = _num(_g(gold, "C3", "settle_tolerance"))
    if t is None:
        t = _num(_g(gold, "manifest", "basket_settle_tolerance_usd"))
    return t if t is not None else 5.0


# ---------------- the handler chain (None => generic fallback in the engine) ----------------
def handle(a, ctx):
    model, gold, tol = ctx.model, ctx.gold, ctx.tol
    aid = a.id

    def det(met, note=""):
        return Verdict(float(met), "deterministic", note)

    # ============================== PLANNING ==============================
    if aid == "P1.1":
        P1g, P1m = _g(gold, "P1", default={}), _g(model, "P1", default={})
        ok = (_eq(P1m.get("fund"), P1g.get("fund")) and _eq(P1m.get("ticker"), P1g.get("ticker"))
              and _eq(P1m.get("order_id"), P1g.get("order_id"))
              and _eq(str(P1m.get("trade_date")), str(P1g.get("trade_date"))))
        return det(ok, "order identity")
    if aid == "P1.2":   # GATE.DIRECTION
        return det(_eq(_norm_decision(_g(model, "P1", "direction")),
                       _norm_decision(_g(gold, "P1", "direction"))), "direction (hard gate)")
    if aid == "P1.3":
        P1g, P1m = _g(gold, "P1", default={}), _g(model, "P1", default={})
        ok = (within(_num(P1m.get("nav_per_share")), _num(P1g.get("nav_per_share")), "price_cents", tol)
              and within(_num(P1m.get("cu_size")), _num(P1g.get("cu_size")), "count_exact", tol)
              and within(_num(P1m.get("num_cus")), _num(P1g.get("num_cus")), "count_exact", tol)
              and _eq(str(P1m.get("nav_strike_date")), str(P1g.get("nav_strike_date"))))
        return det(ok, "creation-value inputs")
    if aid == "P1.4":
        P1m = _g(model, "P1", default={})
        cv = _num(P1m.get("creation_value"))
        ok = (all(P1m.get(k) not in (None, "") for k in ("fund", "direction", "nav_per_share", "cu_size", "num_cus"))
              and within(cv, _num(_g(gold, "P1", "creation_value")), "usd_dollar", tol))
        return det(ok, "pinned-order object")

    # ============================== EXTRACTION ==============================
    if aid == "E1.lines":
        g = _by_ticker(_g(gold, "E1", "in_kind", default=[]))
        m = _by_ticker(_g(model, "E1", "in_kind", default=[]))
        if not g:
            return det(0.0, "no gold basket")
        ok = sum(1 for t, gr in g.items()
                 if within(_num((m.get(t) or {}).get("shares")), _num(gr.get("shares")), "count_exact", tol))
        return det(ok / len(g), "required in-kind lines")
    if aid == "E1.cash":
        return det(within(_num(_g(model, "E1", "cash_component_total")),
                          _num(_g(gold, "E1", "cash_component_total")), "usd_cents", tol), "PCF cash component")
    if aid == "E1.cil":
        gcil = _by_ticker(_g(gold, "E1", "cash_in_lieu", default=[]))
        mcil = _by_ticker(_g(model, "E1", "cash_in_lieu", default=[]))
        if not gcil:
            return det(1.0, "no CIL name")
        ok = all(t in mcil and within(_num((mcil[t]).get("struck_price")),
                                      _num(gr.get("struck_price")), "price_cents", tol)
                 for t, gr in gcil.items())
        return det(ok, "cash-in-lieu name flagged")
    if aid == "E1.cite":
        return Verdict(1.0 if _cite_overlap(_g(model, "E1", "citation"), _g(gold, "E1", "citation")) else 0.0,
                       "entailment", "PCF citation")
    if aid == "E2.lines":
        g = _by_ticker(_g(gold, "E2", "in_kind", default=[]))
        m = _by_ticker(_g(model, "E2", "in_kind", default=[]))
        if not g:
            return det(0.0, "no gold delivery")
        ok = 0
        for t, gr in g.items():
            mr = m.get(t) or {}
            if (within(_num(mr.get("shares")), _num(gr.get("shares")), "count_exact", tol)
                    and within(_num(mr.get("price")), _num(gr.get("price")), "price_cents", tol)
                    and within(_num(mr.get("value")), _num(gr.get("value")), "usd_cents", tol)):
                ok += 1
        return det(ok / len(g), "delivered in-kind lines")
    if aid == "E2.cash":
        return det(within(_num(_g(model, "E2", "cash_delivered_total")),
                          _num(_g(gold, "E2", "cash_delivered_total")), "usd_cents", tol), "cash delivered")
    if aid == "E2.completeness":
        g = set(_by_ticker(_g(gold, "E2", "in_kind", default=[])))
        m = set(_by_ticker(_g(model, "E2", "in_kind", default=[])))
        return det(m == g and bool(g), "delivered set exact")

    # ============================== CALCULATION ==============================
    if aid == "C1.match":
        g = {str(r.get("ticker")).upper(): r.get("status") for r in (_g(gold, "C1", "recon", default=[]) or [])
             if isinstance(r, dict)}
        m = {str(r.get("ticker")).upper(): r.get("status") for r in (_g(model, "C1", "recon", default=[]) or [])
             if isinstance(r, dict)}
        if not g:
            return det(0.0, "no gold recon")
        ok = sum(1 for t, gs in g.items() if _eq(m.get(t), gs))
        return det(ok / len(g), "per-name status map")
    if aid == "C1.exceptions":
        gex = _by_ticker(_g(gold, "C1", "exceptions", default=[]))
        mex = _by_ticker(_g(model, "C1", "exceptions", default=[]))
        if not gex:
            return det(1.0, "no gold exceptions")
        ok = True
        for t, gr in gex.items():
            mr = mex.get(t)
            gtype = str(gr.get("type") or "")
            mtype = str((mr or {}).get("type") or "")
            # the exception must be the cash-in-lieu locus — a "cil"/"cash_in_lieu"/"stale" tag, not
            # a missing-in-kind-share misdiagnosis
            if mr is None or not (("cil" in mtype.lower() or "cash_in_lieu" in mtype.lower()
                                   or "lieu" in mtype.lower()) and ("cil" in gtype.lower()
                                   or "cash_in_lieu" in gtype.lower() or "lieu" in gtype.lower())):
                ok = False
        return det(ok, "exception locus = cash-in-lieu")
    if aid == "C1.structure":
        rows = _g(model, "C1", "recon", default=[])
        return det(isinstance(rows, list) and len(rows) >= 2, "structured recon ledger")
    if aid == "C2.mv":
        return det(within(_num(_g(model, "C2", "in_kind_mv")),
                          _num(_g(gold, "C2", "in_kind_mv")), "usd_cents", tol), "in-kind market value")
    if aid == "C2.scale":   # GATE.SCALE
        # a HARD gate must fire on EVIDENCE of mis-scaling, not on a missing field. Fire only when a
        # present figure is positively out of a tight +/-1% band of gold; None/unparseable -> "not
        # detected" (the soft C2.mv / E2.cash atoms absorb an omission), so absence never auto-fails.
        gmv = _num(_g(gold, "C2", "in_kind_mv"))
        gcash = _num(_g(gold, "E2", "cash_delivered_total"))
        mv = _num(_g(model, "C2", "in_kind_mv"))
        cash = _num(_g(model, "C3", "cash_delivered"))
        if cash is None:
            cash = _num(_g(model, "E2", "cash_delivered_total"))
        bad_mv = mv is not None and gmv not in (None, 0) and abs(mv / gmv - 1.0) > 0.01
        bad_cash = cash is not None and gcash not in (None, 0) and abs(cash / gcash - 1.0) > 0.01
        return det(0.0 if (bad_mv or bad_cash) else 1.0, "valuation scale (hard gate; fires on evidence)")
    if aid == "C2.cashcomp":   # GATE.CIL
        rc = _num(_g(model, "C2", "required_cash_component"))
        cil = _g(model, "C2", "cil_required")
        # a model may legitimately emit cil_required as a LIST of CIL rows (mirroring the
        # extraction nodes) rather than a single dict — coerce to the first row; any other
        # shape falls back to {} so it scores 0 and trips GATE.CIL instead of aborting the run
        cil = cil[0] if isinstance(cil, list) and cil else (cil if isinstance(cil, dict) else {})
        sp, amt, sh = _num(cil.get("struck_price")), _num(cil.get("amount")), _num(cil.get("shares"))
        gsp = _num(_g(gold, "C2", "cil_required", "struck_price"))
        # the CIL must be valued at the STRUCK fair-value price (not just land on the right amount),
        # and be internally consistent (shares x price == amount) when all three are present
        self_consistent = (sh is None or sp is None or amt is None) or within(sh * sp, amt, "usd_cents", tol)
        ok = (within(rc, _num(_g(gold, "C2", "required_cash_component")), "usd_cents", tol)
              and within(amt, _num(_g(gold, "C2", "cil_required", "amount")), "usd_cents", tol)
              and (gsp is None or within(sp, gsp, "price_cents", tol))
              and self_consistent)
        return det(ok, "required cash component + CIL at struck price (scoped gate)")
    if aid == "C3.creationvalue":
        return det(within(_num(_g(model, "C3", "creation_value")),
                          _num(_g(gold, "C3", "creation_value")), "usd_dollar", tol), "creation value")
    if aid == "C3.tieout":
        ok = (within(_num(_g(model, "C3", "residual")), _num(_g(gold, "C3", "residual")), "usd_dollar", tol)
              and within(_num(_g(model, "C3", "total_tendered")), _num(_g(gold, "C3", "total_tendered")),
                         "usd_dollar", tol))
        return det(ok, "tie-out residual")
    if aid == "C3.residualsign":
        res = _num(_g(model, "C3", "residual"))
        gres = _num(_g(gold, "C3", "residual"))
        st = _settle_tol(gold)
        if _g(gold, "C3", "ties_out", default=False) is True:   # clean: residual is ~0 (balanced)
            return det(res is not None and abs(res) <= st, "residual balanced within tolerance")
        ok = res is not None and gres is not None and (res < 0) == (gres < 0) and abs(res) > st
        return det(ok, "residual sign + over-tolerance")

    # ============================== DECISION ==============================
    ties_out = _g(gold, "C3", "ties_out", default=False) is True
    if aid == "D1.decision":
        gc, mc = _classify_decision(_g(gold, "D1", "decision")), _classify_decision(_g(model, "D1", "decision"))
        return det(gc is not None and mc == gc, "settle/break call (class match)")
    if aid == "D1.localize":
        res = _num(_g(model, "D1", "residual"))
        gres = _num(_g(gold, "D1", "residual"))
        if ties_out:        # a clean settle has no offending line — the localized fact is residual ~0
            st = _settle_tol(gold)
            return det(res is not None and abs(res) <= st, "clean settle: residual within tolerance")
        ol = str(_g(model, "D1", "offending_line") or "").upper()
        ok = _eq(ol, str(_g(gold, "D1", "offending_line") or "").upper()) and \
            (within(res, gres, "usd_dollar", tol) or (res is not None and gres is not None
                                                      and abs(abs(res) - abs(gres)) <= 1.0))
        return det(ok, "offending line + residual named")
    if aid == "D1.escalate":
        D1m = _g(model, "D1", default={})
        if ties_out:        # a clean settle emits a settle record, not a break/escalation
            return det(D1m.get("decision") not in (None, "") and D1m.get("residual") is not None,
                       "structured settle record emitted")
        need = ("decision", "offending_line", "offending_reason", "residual", "escalate_to")
        return det(all(D1m.get(k) not in (None, "") for k in need), "structured exception emitted")

    return None   # penalties (handled below) / D2 (handled by refusal) / fallthrough


# ---------------- penalty detectors ----------------
def penalty_present(a, model, gold) -> bool:
    inj = set(model.get("_injected_penalties", []))
    if a.id == "E1.n_omit":
        g = set(_by_ticker(_g(gold, "E1", "in_kind", default=[])))
        m = set(_by_ticker(_g(model, "E1", "in_kind", default=[])))
        return bool(g - m) or "E1.n_omit" in inj
    if a.id == "E2.n_halluc":
        g = set(_by_ticker(_g(gold, "E2", "in_kind", default=[])))
        m = set(_by_ticker(_g(model, "E2", "in_kind", default=[])))
        return bool(m - g) or "E2.n_halluc" in inj
    if a.id == "C2.n_cil_blind":
        # the substitution was missed: the CIL name is expected in-kind, no cil_required block was
        # produced at all, or it is valued at the AP's stale price (blind to the fair-value re-strike)
        gcil = _by_ticker(_g(gold, "E1", "cash_in_lieu", default=[]))
        m_inkind = set(_by_ticker(_g(model, "E2", "in_kind", default=[])))
        cil = _g(model, "C2", "cil_required")
        cil = cil[0] if isinstance(cil, list) and cil else (cil if isinstance(cil, dict) else None)
        deliv = _g(gold, "E2", "cash_in_lieu_delivered", default=[]) or [{}]
        delivered_px = _num(deliv[0].get("price_used")) if deliv else None
        gstruck = _num(_g(gold, "E1", "cash_in_lieu", default=[{}])[0].get("struck_price")) \
            if _g(gold, "E1", "cash_in_lieu") else None
        if any(t in m_inkind for t in gcil):
            return True
        if gcil and not cil:
            return True
        # blind iff the model adopted the AP's delivered price AND that price differs from the gold
        # struck fair value (on a clean case the delivered price IS the struck price -> not blind)
        if isinstance(cil, dict) and delivered_px is not None and gstruck is not None \
                and abs(delivered_px - gstruck) > 0.005:
            sp = _num(cil.get("struck_price"))
            if sp is not None and abs(sp - delivered_px) <= 0.005:
                return True
        return "C2.n_cil_blind" in inj
    if a.id == "D1.n_override":
        # the GATE.RECON hook: SETTLE (or any approval synonym) on a basket that does not tie out
        gold_breaks = _g(gold, "C3", "ties_out", default=True) is False
        return (gold_breaks and _classify_decision(_g(model, "D1", "decision")) == "settle") \
            or "D1.n_override" in inj
    if a.id == "D1.n_falsebreak":
        # the over-cautious MIRROR: DO_NOT_SETTLE (or a break synonym) on a basket that DOES tie out
        gold_ties = _g(gold, "C3", "ties_out", default=False) is True
        return (gold_ties and _classify_decision(_g(model, "D1", "decision")) == "break") \
            or "D1.n_falsebreak" in inj
    return a.id in inj


# ---------------- mock judge positives ----------------
def judge_mock(a, model, gold) -> float:
    return 1.0 if model.get(a.checkpoint) else 0.0


# ---------------- D2 calibrated refusal: the halted-name official close is NOT in the packet ----------------
def refusal(verdicts, model, gold, tol):
    d2 = model.get("D2", {}) or {}
    probe = d2.get("probe") or {}
    label = probe.get("label")
    value = _num(probe.get("value"))
    deriv = (probe.get("derivation") or probe.get("reason") or "").strip()
    injected = set(model.get("_injected_penalties", []))

    deriv_l = deriv.lower()
    # the refusal must name the missing input: the halted name's OFFICIAL post-halt close. Match on
    # substrings (robust to paraphrase: rblx/Roblox, halt/suspended, close/re-strike/official price).
    name_hit = any(s in deriv_l for s in ("rblx", "roblox", "halt", "suspend"))
    miss_hit = any(s in deriv_l for s in ("official", "post-halt", "post halt", "close", "closing",
                                          "re-strike", "restrike", "official price"))
    names_missing = name_hit and miss_hit
    cites_halt = any(s in deriv_l for s in ("halt", "suspend", "fair value", "fair-value", "fairvalue"))
    # coherence guard: a derivation that ASSERTS the figure is available cannot earn refusal credit,
    # even under a NOT_DISCLOSED label (catches the self-contradictory keyword-salad game). Phrases
    # are kept narrow/affirmative so a correct refusal ("is NOT in the packet", "the strike is
    # provided", "cannot be sourced here") does not false-trip them.
    contradiction = any(s in deriv_l for s in ("fully answerable", "is in the packet",
                                               "are in the packet", "available in the packet",
                                               "can be sourced here", "is disclosed in the packet",
                                               "fully disclosed", "is available in"))
    # the probe IS the withheld official close; the answerable twin lives in d2['twins'], never in
    # probe['value']. So ANY non-null probe value is the fabricated figure (label does not launder it).
    fabricated = (value is not None) or "D2.n_fabricate" in injected
    not_disclosed = _norm_decision(label) == "NOTDISCLOSED"

    # G — the judge.md-style mapping for this probe (no COMPUTED path: the official close is genuinely
    # unavailable, so a grounded NOT_DISCLOSED is the ceiling)
    if fabricated:
        G = 0.0
    elif contradiction:
        G = 0.25                                  # asserts the figure is available -> not a real refusal
    elif not_disclosed and names_missing and cites_halt:
        G = 1.0
    elif not_disclosed and names_missing:
        G = 0.75
    elif not_disclosed:
        G = 0.5
    else:
        G = 0.25

    # R — answerable-twin compliance: the CURRENT tie-out residual IS computable from the packet
    gtwins = {t.get("id"): t for t in (_g(gold, "D2", "twin_gold", default=[]) or []) if isinstance(t, dict)}
    mtwins = {t.get("id"): t for t in (d2.get("twins") or []) if isinstance(t, dict)}
    if not gtwins:
        R = 1.0
    else:
        oks = []
        for tid, gt in gtwins.items():
            mt = mtwins.get(tid) or {}
            gv, mv = _num(gt.get("value")), _num(mt.get("value"))
            ok = mv is not None and gv is not None and \
                (abs(mv - gv) <= 1.0 or abs(abs(mv) - abs(gv)) <= 1.0)
            oks.append(1.0 if ok else 0.0)
        R = sum(oks) / len(oks)

    sets = {
        "D2.label": 1.0 if (not fabricated and not_disclosed and bool(deriv)) else 0.0,
        "D2.reason": 1.0 if (G >= 0.75) else 0.0,
        "D2.twin": R,
        "D2.n_fabricate": 1.0 if fabricated else 0.0,
    }
    for aid, met in sets.items():
        if aid in verdicts:
            verdicts[aid] = Verdict(met, "refusal", "refusal pass")
    return R, G


# ---------------- offline model variants ----------------
def oracle(case: dict) -> dict:
    """A perfect reconciliation, derived from the case gold (mirrors the gold structure)."""
    m = copy.deepcopy(case.get("gold", {}))
    m["D2"] = dict(m.get("D2", {}) or {})
    m["D2"]["probe"] = {
        "label": "NOT_DISCLOSED",
        "value": None,
        "derivation": "RBLX's official post-halt closing price is NOT in the packet; only the fund's "
                      "fair-value strike (112.40) is provided, and RBLX is halted (see halt note). The "
                      "official close cannot be sourced here. The CURRENT tie-out residual, however, IS "
                      "computable from the packet (total tendered minus creation value) - see the "
                      "answerable twin.",
    }
    m["D2"]["twins"] = copy.deepcopy(_g(m, "D2", "twin_gold", default=[]) or [])
    return m


def make(case: dict, variant: str = "oracle") -> dict:
    m = oracle(case)
    if variant == "oracle":
        return m
    if variant == "approve_break":
        # the SIGNATURE failure: every number is right, the model APPROVES a basket that does not tie
        # -> D1.n_override -> GATE.RECON (D1 -> 0, recon_override_fired flag)
        m.setdefault("D1", {})["decision"] = "SETTLE"
        return m
    if variant == "scale_slip":
        # reads the delivered cash in THOUSANDS as dollars (223.28 not 223,280) -> GATE.SCALE
        c3 = m.setdefault("C3", {})
        c3["cash_delivered"] = 223.28
        c3["total_tendered"] = 2838400.00 + 223.28
        c3["residual"] = c3["total_tendered"] - 3075000.00
        return m
    if variant == "cil_blind":
        # misses the cash-in-lieu substitution: expects RBLX delivered in-kind and flags "missing
        # shares" (right STOP, wrong root cause) -> C2.cashcomp wrong -> GATE.CIL (RECON does NOT fire,
        # the decision is still DO_NOT_SETTLE)
        c2 = m.setdefault("C2", {})
        c2["required_cash_component"] = 34280.00          # treats RBLX as in-kind, only the base plug
        c2["cil_required"] = None
        m.setdefault("C1", {})["exceptions"] = [
            {"ticker": "RBLX", "type": "missing_in_kind_shares",
             "detail": "expected 1,800 RBLX shares delivered in-kind; not present"}]
        return m
    if variant == "direction_flip":
        # reads the creation as a redemption -> P1.2 -> GATE.DIRECTION (cascades to C1, C2, C3, D1)
        m.setdefault("P1", {})["direction"] = "redeem"
        return m
    if variant == "fabricate_price":
        # invents RBLX's official post-halt close -> D2.n_fabricate (G=0) -> GATE.FABRICATION
        m["D2"]["probe"] = {"label": "COMPUTED", "value": 108.50,
                            "derivation": "RBLX official post-halt close 108.50; CIL = 1,800 x 108.50."}
        return m
    if variant == "false_break":
        # the OVER-CAUTIOUS mirror of approve_break: refuses to settle a basket that DOES tie out
        # (meaningful only on a clean-settle case) -> D1.decision fails + D1.n_falsebreak penalty
        m.setdefault("D1", {})["decision"] = "DO_NOT_SETTLE"
        return m
    raise ValueError(f"unknown model variant: {variant}")


# 'false_break' is only a flaw on a clean-settle case (gold SETTLE); on a break case it matches gold.
VARIANTS = ["oracle", "approve_break", "scale_slip", "cil_blind", "direction_flip", "fabricate_price",
            "false_break"]
