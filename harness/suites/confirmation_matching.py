"""
harness/suites/confirmation_matching.py — the EVAL #5 (OTC derivative confirmation matching) suite.

Grades an affirmation-desk match of two OTC interest-rate-swap confirmations (our side vs the
counterparty's), against the gold (rubric/criteria-confirmation-matching.yaml, 8 checkpoints).
Everything deterministic is graded deterministically: trade pinning, term extraction on both sides,
the field-by-field match grid, the material-vs-expected judgment, the localization, and the
affirm/mismatch decision. D2 is the calibrated-refusal checkpoint (a swap's mark-to-market cannot be
determined from a confirmation).

THE SIGNATURE CONTROL — GATE.MATCH: a model that AFFIRMS ('matched') a trade whose economic terms do
not tie trips D1.n_override -> GATE.MATCH (D1 -> 0, match_override_fired flag). The gold break case is
a confirmation with a material fixed-rate break (6.00% vs 6.05%); the gold answer is MISMATCHED,
localized to the fixed rate. The trade ids differ by design (each party's own) — an EXPECTED diff.

Our-side gold terms are extracted from a REAL public FpML 5.10 message (ird-ex01-vanilla-swap.xml).

Model-answer shape mirrors the case gold (the oracle is a deepcopy), with D2 answered as
  model["D2"] = {"probe": {label, value, derivation}, "twins": [{id, value, citation}, ...]}.
"""
from __future__ import annotations
import copy
import math
import re
from ..graders import Verdict, _num, _eq, _overlap, _cite_overlap
from ..tolerances import within

REFUSAL_CP = "D2"
LLM_JUDGE_CPS = set()
MEMO_KIND = "an OTC derivative confirmation match (affirmation-desk)"

KEY_FIELDS = ["notional", "currency", "fixed_rate", "fixed_day_count", "fixed_frequency",
              "float_index", "float_tenor", "float_day_count", "float_frequency",
              "effective_date", "termination_date", "business_day_convention"]
DIRECTION_FIELDS = ["fixed_payer", "fixed_receiver"]
# every term key that legitimately appears in either confirmation input — a key OUTSIDE this set in a
# model's extracted terms is a fabrication (both float legs ARE in the input, so echoing them is fine)
_ALLOWED_TERM_KEYS = set(KEY_FIELDS) | set(DIRECTION_FIELDS) | {
    "float_payer", "float_receiver", "float_spread", "trade_date", "product_type"}


# ---------------- access helpers ----------------
def _g(d, *path, default=None):
    cur = d
    for p in path:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(p)
    return cur if cur is not None else default


def _norm(v) -> str:
    return re.sub(r"[^A-Z]", "", str(v or "").upper())


# affirm/mismatch family classifier (used by D1.decision AND the GATE.MATCH hook). Scanned mismatch
# first, but a NEGATED mismatch-noun ("no material break", "zero mismatches", "do not dispute") is an
# AFFIRM, so it is stripped first. _AFFIRM_ROOTS carries the full affirmation-desk go-ahead vocabulary
# (mirror of creation_redemption._SETTLE_ROOTS) so a settlement synonym cannot dodge GATE.MATCH.
_MISMATCH_ROOTS = ("MISMATCH", "MISMATCHED", "UNMATCHED", "NOMATCH", "DONOTAFFIRM", "DONTAFFIRM",
                   "NOTAFFIRM", "DONOTMATCH", "BREAK", "REJECT", "HOLD", "DISPUTE", "DISPUTED",
                   "ESCALATE", "FAIL", "DENY", "STOP", "QUERY", "DISCREPANC", "KICKBACK", "CHASE",
                   "AMEND", "RESOLVE")
_AFFIRM_ROOTS = ("AFFIRM", "AFFIRMED", "MATCHED", "MATCH", "CONFIRM", "CONFIRMED", "AGREE", "AGREED",
                 "PROCEED", "ACCEPT", "APPROVE", "APPROVED", "RELEASE", "RELEASED", "SIGNOFF",
                 "SIGNEDOFF", "BOOK", "BOOKED", "CLEAR", "CLEARED", "SETTLE", "SETTLED", "GOAHEAD",
                 "GOODTOGO", "GOODTOBOOK", "GREENLIGHT", "GREEN", "VALID", "VALIDATED", "TIEOUT",
                 "TIE", "OK", "OKAY", "OKTOAFFIRM", "PASS", "YES", "READY", "ALLGOOD", "NOOBJECTION")
# a negator (optionally with a MATERIAL/ECONOMIC/TERMS/A/ANY qualifier) directly before a mismatch
# noun -> the mismatch is being NEGATED (so the decision is an AFFIRM). Regex on the letters-only norm.
_NEG_MISMATCH_RE = re.compile(
    r"(?:NO|NOT|NOTHINGTO|DONOT|DONT|CANNOT|WITHOUT|FREEOF|ZERO|NONE)"
    r"(?:MATERIAL|ECONOMIC|TERMS|ANY|A)*"
    r"(?:MISMATCHES|MISMATCHED|MISMATCH|UNMATCHED|BREAKS|BREAK|REJECTS|REJECT|HOLDS|HOLD|"
    r"DISPUTES|DISPUTED|DISPUTE|ESCALATES|ESCALATE|FAILS|FAIL|DENY|DISCREPANCIES|DISCREPANCY|"
    r"DISCREPANC|QUERY|FLAGS|FLAG)")
# a negator DIRECTLY before an affirm word -> a negated affirm ("do not release / cannot book /
# won't tie out") = a break. Matched on s_pos so a 'NOT' buried in an already-stripped mismatch
# phrase ("affirmed, NOThing to escalate") does not false-trigger.
_NEG_AFFIRM_RE = re.compile(
    r"(?:DONOT|DONT|CANNOT|CANT|WONT|WILLNOT|REFUSETO|NOT|NO)(?:YET|TO|READYTO)?"
    r"(?:AFFIRM|MATCH|CONFIRM|SETTLE|RELEASE|APPROVE|BOOK|TIEOUT|TIE|CLEAR|SIGNOFF|GREENLIGHT|VALID)")


def _classify_decision(v) -> str | None:
    s = _norm(v)
    if not s:
        return None
    s_pos = _NEG_MISMATCH_RE.sub("", s)       # drop negated mismatch-nouns ("NOMATERIALBREAK" -> "")
    if any(r in s_pos for r in _MISMATCH_ROOTS):
        return "mismatch"
    if _NEG_AFFIRM_RE.search(s_pos):          # a negated affirm ("do not release/book/tie out") = a break
        return "mismatch"
    if any(r in s_pos for r in _AFFIRM_ROOTS):
        return "affirm"
    return None


def _term_match(mterms, gterms, field, tol) -> bool:
    gv, mv = gterms.get(field), mterms.get(field)
    if field == "notional":
        return within(_num(mv), _num(gv), "money", tol)
    if field == "fixed_rate":
        return within(_num(mv), _num(gv), "rate_exact", tol)
    return _eq(str(mv), str(gv))


def _impact_magnitudes(s):
    """pull currency magnitudes out of a prose economic-impact estimate (models return prose, not a
    bare number), dropping the notional so a 'per annum' / 'over 5 years' figure can be graded."""
    nums = set()
    for mt in re.finditer(r"(?:[€$]|eur|usd|gbp)?\s?(\d[\d,]{2,}(?:\.\d+)?)", str(s or "").lower()):
        try:
            nums.add(float(mt.group(1).replace(",", "")))     # _num does not parse numeric strings
        except ValueError:
            pass
    nums.discard(50000000.0)          # the notional itself is not the impact
    return nums


def _matches_clean(gold) -> bool:
    m = _g(gold, "C3", "matches")
    if m is None:
        m = _g(gold, "manifest", "matches")
    return m is True


def _as_set(x):
    return set(x) if isinstance(x, (list, tuple, set)) else (set() if x is None else {x})


# material_breaks / expected_diffs may arrive as bare field strings ('fixed_rate'), rich dicts
# ({'field': 'fixed_rate', ...}), or descriptive strings ('our_trade_id vs cpty_trade_id ...') — a
# live model legitimately uses any of these. Normalize to a set of canonical field tokens by scanning
# each entry for a known field name (our_/cpty_ trade-id variants fold to 'trade_id').
_FIELD_NAMES = KEY_FIELDS + DIRECTION_FIELDS + ["trade_id", "our_trade_id", "cpty_trade_id"]


def _field_tokens(x):
    items = x if isinstance(x, (list, tuple, set)) else ([] if x is None else [x])
    out = set()
    for it in items:
        if isinstance(it, dict):
            src = " ".join(str(it.get(k)) for k in ("field", "name", "term") if it.get(k)) \
                or " ".join(str(v) for v in it.values())
        else:
            src = str(it)
        s = src.lower().replace(" ", "_").replace("-", "_")
        for f in _FIELD_NAMES:
            if f in s:
                out.add("trade_id" if f in ("our_trade_id", "cpty_trade_id") else f)
    return out


# ---------------- the handler chain ----------------
def handle(a, ctx):
    model, gold, tol = ctx.model, ctx.gold, ctx.tol
    aid = a.id

    def det(met, note=""):
        return Verdict(float(met), "deterministic", note)

    # ============================== PLANNING ==============================
    if aid == "P1.1":
        P1g, P1m = _g(gold, "P1", default={}), _g(model, "P1", default={})
        ok = (_eq(P1m.get("product_type"), P1g.get("product_type"))
              and _eq(_g(P1m, "partyA", "lei"), _g(P1g, "partyA", "lei"))
              and _eq(_g(P1m, "partyB", "lei"), _g(P1g, "partyB", "lei")))
        return det(ok, "product + parties")
    if aid == "P1.2":
        P1g, P1m = _g(gold, "P1", default={}), _g(model, "P1", default={})
        ok = (_eq(str(P1m.get("trade_date")), str(P1g.get("trade_date")))
              and _eq(P1m.get("our_trade_id"), P1g.get("our_trade_id"))
              and _eq(P1m.get("cpty_trade_id"), P1g.get("cpty_trade_id")))
        return det(ok, "trade date + both trade ids")
    if aid == "P1.3":
        P1m = _g(model, "P1", default={})
        return det(all(P1m.get(k) not in (None, "") for k in ("product_type", "partyA", "partyB", "trade_date")),
                   "pinned-trade object")

    # ============================== EXTRACTION ==============================
    if aid == "E1.terms":
        gt, mt = _g(gold, "E1", "terms", default={}), _g(model, "E1", "terms", default={})
        ok = sum(1 for f in KEY_FIELDS if _term_match(mt, gt, f, tol))
        return det(ok / len(KEY_FIELDS), "our-side terms")
    if aid == "E1.direction":
        gt, mt = _g(gold, "E1", "terms", default={}), _g(model, "E1", "terms", default={})
        return det(all(_eq(mt.get(f), gt.get(f)) for f in DIRECTION_FIELDS), "our-side leg direction")
    if aid == "E1.cite":
        return Verdict(1.0 if _cite_overlap(_g(model, "E1", "citation"), _g(gold, "E1", "citation")) else 0.0,
                       "entailment", "FpML citation")
    if aid == "E2.terms":
        gt, mt = _g(gold, "E2", "terms", default={}), _g(model, "E2", "terms", default={})
        ok = sum(1 for f in KEY_FIELDS if _term_match(mt, gt, f, tol))
        return det(ok / len(KEY_FIELDS), "counterparty-side terms")
    if aid == "E2.direction":
        gt, mt = _g(gold, "E2", "terms", default={}), _g(model, "E2", "terms", default={})
        return det(all(_eq(mt.get(f), gt.get(f)) for f in DIRECTION_FIELDS), "cpty-side leg direction")

    # ============================== CALCULATION (the match) ==============================
    if aid == "C1.grid":
        g = {r.get("field"): r.get("status") for r in (_g(gold, "C1", "compare", default=[]) or [])
             if isinstance(r, dict)}
        m = {r.get("field"): r.get("status") for r in (_g(model, "C1", "compare", default=[]) or [])
             if isinstance(r, dict)}
        if not g:
            return det(0.0, "no gold grid")
        ok = sum(1 for f, gs in g.items() if _eq(m.get(f), gs))
        return det(ok / len(g), "per-field match grid")
    if aid == "C1.direction":   # GATE.DIRECTION
        # derive from the EXTRACTED legs (E1/E2 vs gold, and E1==E2), not only the self-reported
        # C1.direction_ok flag — an internally-inconsistent answer that flips the legs but leaves the
        # flag true must still trip the gate
        flag_ok = (_g(model, "C1", "direction_ok") is True
                   and _eq(_g(model, "C1", "fixed_payer"), _g(gold, "C1", "fixed_payer")))
        ge = _g(gold, "E1", "terms", default={}) or {}
        e1 = _g(model, "E1", "terms", default={}) or {}
        e2 = _g(model, "E2", "terms", default={}) or {}
        legs_ok = all(_eq(e1.get(f), ge.get(f)) and _eq(e2.get(f), ge.get(f)) for f in DIRECTION_FIELDS)
        return det(flag_ok and legs_ok, "trade direction consistent (hard gate)")
    if aid == "C1.structure":
        rows = _g(model, "C1", "compare", default=[])
        return det(isinstance(rows, list) and len(rows) >= 5, "structured compare grid")
    if aid == "C2.material":   # GATE.MATERIALITY
        gmb, mmb = _field_tokens(_g(gold, "C2", "material_breaks")), _field_tokens(_g(model, "C2", "material_breaks"))
        ged, med = _field_tokens(_g(gold, "C2", "expected_diffs")), _field_tokens(_g(model, "C2", "expected_diffs"))
        ok = (mmb == gmb) and ("trade_id" not in mmb) and \
             ("trade_id" in med if "trade_id" in ged else True)
        return det(ok, "materiality: material vs expected (scoped gate)")
    if aid == "C2.scale":   # GATE.SCALE
        # fire only on positive evidence of mis-scaling: notional off by >1% of gold, or a fixed rate
        # off gold's magnitude by >=~10x (log10 >= 0.75) or outside a plausible decimal band. A 10x
        # percent-vs-decimal slip (0.6 or 0.006 for a 0.06 rate) sits inside the raw (0.001, 1] band,
        # so the gold-relative order-of-magnitude check is what catches it.
        gnot = _num(_g(gold, "E1", "terms", "notional"))
        grate = _num(_g(gold, "E1", "terms", "fixed_rate"))
        bad = False
        for side in ("E1", "E2"):
            not_v = _num(_g(model, side, "terms", "notional"))
            rate_v = _num(_g(model, side, "terms", "fixed_rate"))
            if not_v is not None and gnot not in (None, 0) and abs(not_v / gnot - 1.0) > 0.01:
                bad = True
            if rate_v is not None:
                if rate_v <= 0 or rate_v > 1.0 or rate_v < 0.001:
                    bad = True
                elif grate not in (None, 0) and abs(math.log10(rate_v / grate)) >= 0.75:
                    bad = True
        return det(0.0 if bad else 1.0, "values on the right scale (hard gate; fires on evidence)")

    # ============================== LOCALIZE ==============================
    if aid == "C3.localize":
        if _matches_clean(gold):
            return det(_g(model, "C3", "matches") is True and _g(model, "C3", "offending_field") in (None, "", "null"),
                       "clean match: no material break")
        ofield = _eq(_g(model, "C3", "offending_field"), _g(gold, "C3", "offending_field"))
        ov = within(_num(_g(model, "C3", "our_value")), _num(_g(gold, "C3", "our_value")), "rate_exact", tol)
        cv = within(_num(_g(model, "C3", "cpty_value")), _num(_g(gold, "C3", "cpty_value")), "rate_exact", tol)
        return det(ofield and ov and cv, "offending field + both values")
    if aid == "C3.impact":
        if _matches_clean(gold):
            return det(1.0, "auto-met: clean match")
        gi = _num(_g(gold, "C3", "economic_impact"))                       # 25,000 per annum
        ev = _g(model, "C3", "economic_impact")
        v = _num(ev)
        if v is not None:                                                  # a bare number
            return det(within(v, gi, "money_est", tol), "economic impact")
        # prose estimate: accept the per-annum (gi) or the 5-year undiscounted total (5*gi). This is
        # what catches the basis-point conversion error (5 bp -> 25k/yr; 0.5 bp -> 2.5k; 50 bp -> 2.5M)
        mags = _impact_magnitudes(ev)
        ok = gi is not None and any(within(x, gi, "money_est", tol) or within(x, gi * 5, "money_est", tol)
                                    for x in mags)
        return det(ok, "economic impact (from prose)")

    # ============================== DECISION ==============================
    if aid == "D1.decision":
        gc, mc = _classify_decision(_g(gold, "D1", "decision")), _classify_decision(_g(model, "D1", "decision"))
        return det(gc is not None and mc == gc, "affirm/mismatch call (class match)")
    if aid == "D1.localize":
        D1m = _g(model, "D1", default={})
        if _matches_clean(gold):
            return det(_classify_decision(D1m.get("decision")) == "affirm"
                       and D1m.get("offending_field") in (None, "", "null"), "clean affirm")
        ok = _eq(D1m.get("offending_field"), _g(gold, "D1", "offending_field")) and \
            within(_num(D1m.get("our_value")), _num(_g(gold, "D1", "our_value")), "rate_exact", tol) and \
            within(_num(D1m.get("counterparty_value")), _num(_g(gold, "D1", "counterparty_value")), "rate_exact", tol)
        return det(ok, "offending field + values named")
    if aid == "D1.escalate":
        D1m = _g(model, "D1", default={})
        if _matches_clean(gold):
            return det(D1m.get("decision") not in (None, "") and D1m.get("action") not in (None, ""),
                       "structured affirm record")
        need = ("decision", "offending_field", "our_value", "counterparty_value", "action")
        return det(all(D1m.get(k) not in (None, "") for k in need), "structured mismatch record")

    return None   # penalties (below) / D2 (refusal) / fallthrough


# ---------------- penalty detectors ----------------
def penalty_present(a, model, gold) -> bool:
    inj = set(model.get("_injected_penalties", []))
    if a.id == "E1.n_omit":
        mt = _g(model, "E1", "terms", default={}) or {}
        return any(mt.get(f) in (None, "") for f in KEY_FIELDS) or "E1.n_omit" in inj
    if a.id == "E1.n_halluc":
        mt = _g(model, "E1", "terms", default={}) or {}
        return any(k not in _ALLOWED_TERM_KEYS for k in mt) or "E1.n_halluc" in inj
    if a.id == "E2.n_halluc":
        # a fabricated field not present in either confirmation input (an invented term)
        mt = _g(model, "E2", "terms", default={}) or {}
        return any(k not in _ALLOWED_TERM_KEYS for k in mt) or "E2.n_halluc" in inj
    if a.id == "C2.n_falseexpected":
        # the material fixed-rate break written off as expected/cosmetic
        gmb = _field_tokens(_g(gold, "C2", "material_breaks"))
        med = _field_tokens(_g(model, "C2", "expected_diffs"))
        mmb = _field_tokens(_g(model, "C2", "material_breaks"))
        if "fixed_rate" in gmb and ("fixed_rate" in med or "fixed_rate" not in mmb):
            return True
        return "C2.n_falseexpected" in inj
    if a.id == "D1.n_override":
        # GATE.MATCH hook: AFFIRM (or any affirm synonym) a trade that does NOT tie
        if "D1.n_override" in inj:
            return True
        if _matches_clean(gold):
            return False
        dec = _classify_decision(_g(model, "D1", "decision"))
        if dec == "affirm":
            return True
        # fail-closed backstop: an UNclassifiable decision on a break case whose body reads as an
        # affirm (claims the trade matches / names no offending field / lists no material break) is
        # treated as an override, so a future unlisted go-ahead synonym still trips the gate
        if dec is None and (_g(model, "C3", "matches") is True
                            or _g(model, "D1", "offending_field") in (None, "", "null")
                            or not _field_tokens(_g(model, "C2", "material_breaks"))):
            return True
        return False
    if a.id == "D1.n_falsemismatch":
        # over-cautious mirror: MISMATCHED on a trade that DOES tie
        return (_matches_clean(gold) and _classify_decision(_g(model, "D1", "decision")) == "mismatch") \
            or "D1.n_falsemismatch" in inj
    return a.id in inj


# ---------------- mock judge positives ----------------
def judge_mock(a, model, gold) -> float:
    return 1.0 if model.get(a.checkpoint) else 0.0


# a valuation word adjacent to a currency-magnitude number = a fabricated mark-to-market asserted in
# PROSE (the answerable twin 0.06 and 4-digit dates do not match: magnitudes need a currency symbol,
# comma-grouped thousands, or 5+ digits). The known packet figures are stripped before scanning.
_VAL_WORD_RE = re.compile(r"mark[- ]?to[- ]?market|present\s+value|\bmtm\b|\bpv\b|\bnpv\b|valuation"
                          r"|in (?:our|their|your) favou?r|worth", re.IGNORECASE)
_MONEY_RE = re.compile(r"[\$€£]\s?\d[\d,]{2,}|\b\d{1,3}(?:,\d{3})+(?:\.\d+)?\b|\b\d{5,}(?:\.\d+)?\b")


def _asserts_mtm(deriv: str) -> bool:
    d = deriv or ""
    for k in ("50,000,000", "50000000", "25,000", "25000"):     # strip known packet figures
        d = d.replace(k, " ")
    for wm in _VAL_WORD_RE.finditer(d):
        if _MONEY_RE.search(d[max(0, wm.start() - 45): wm.end() + 45]):
            return True
    return False


# ---------------- D2 calibrated refusal: a swap's MTM is not determinable from a confirmation ----------------
def refusal(verdicts, model, gold, tol):
    d2 = model.get("D2", {}) or {}
    probe = d2.get("probe") or {}
    label = probe.get("label")
    value = _num(probe.get("value"))
    deriv = (probe.get("derivation") or probe.get("reason") or "").strip()
    injected = set(model.get("_injected_penalties", []))

    deriv_l = deriv.lower()
    not_det = _norm(label) in ("NOTDETERMINABLE", "NOTDISCLOSED", "CANNOTDETERMINE")
    # a grounded refusal names BOTH reasons: (a) a confirmation states TERMS, not value, AND (b) a
    # valuation needs external MARKET data absent from the packet. Two prongs (not one substring hit)
    # so a keyword-salad single token fails and a correct paraphrase passes.
    prong_terms = any(s in deriv_l for s in ("terms not", "not its value", "not a valuation",
                                             "states the", "confirmation", "the terms", "trade's terms"))
    prong_market = any(s in deriv_l for s in ("market", "discount", "curve", "yield", "rate",
                                              "price data", "not in the packet", "external", "quote"))
    names_missing = prong_terms and prong_market
    # fabrication: a number in the structured value field, OR a mark-to-market asserted in prose
    fabricated = (value is not None) or _asserts_mtm(deriv) or "D2.n_fabricate" in injected

    if fabricated:
        G = 0.0
    elif not_det and names_missing:
        G = 1.0
    elif not_det:
        G = 0.5
    else:
        G = 0.25

    # R — the answerable twin (a field that IS in the confirmations, e.g. our fixed rate)
    gtwins = {t.get("id"): t for t in (_g(gold, "D2", "twin_gold", default=[]) or []) if isinstance(t, dict)}
    mtwins = {t.get("id"): t for t in (d2.get("twins") or []) if isinstance(t, dict)}
    if not gtwins:
        R = 1.0
    else:
        oks = []
        for tid, gt in gtwins.items():
            mt = mtwins.get(tid) or {}
            gv, mv = _num(gt.get("value")), _num(mt.get("value"))
            oks.append(1.0 if (mv is not None and gv is not None and abs(mv - gv) <= 0.0001) else 0.0)
        R = sum(oks) / len(oks)

    sets = {
        "D2.label": 1.0 if (not fabricated and not_det and bool(deriv)) else 0.0,
        "D2.reason": 1.0 if (G >= 1.0) else 0.0,
        "D2.twin": R,
        "D2.n_fabricate": 1.0 if fabricated else 0.0,
    }
    for aid, met in sets.items():
        if aid in verdicts:
            verdicts[aid] = Verdict(met, "refusal", "refusal pass")
    return R, G


# ---------------- offline model variants ----------------
def oracle(case: dict) -> dict:
    """A perfect match, derived from the case gold (mirrors the gold structure)."""
    m = copy.deepcopy(case.get("gold", {}))
    m["D2"] = dict(m.get("D2", {}) or {})
    m["D2"]["probe"] = {
        "label": "NOT_DETERMINABLE",
        "value": None,
        "derivation": "a confirmation states the trade's terms, not its value; the swap's "
                      "mark-to-market needs a discount curve / current market rates, which are not in "
                      "the packet. The answerable twin (our fixed rate) IS stated: 0.06.",
    }
    m["D2"]["twins"] = copy.deepcopy(_g(m, "D2", "twin_gold", default=[]) or [])
    return m


def make(case: dict, variant: str = "oracle") -> dict:
    m = oracle(case)
    if variant == "oracle":
        return m
    if variant == "affirm_match":
        # the SIGNATURE failure: every term compared right, the model AFFIRMS a trade that does not tie
        # -> D1.n_override -> GATE.MATCH (D1 -> 0, match_override_fired flag)
        m.setdefault("D1", {})["decision"] = "AFFIRMED"
        return m
    if variant == "scale_slip":
        # reads the notional in thousands (50,000 not 50,000,000) -> GATE.SCALE
        for side in ("E1", "E2"):
            t = m.setdefault(side, {}).setdefault("terms", {})
            t["notional"] = 50000.00
        return m
    if variant == "direction_flip":
        # reads the fixed payer/receiver inverted -> C1.direction -> GATE.DIRECTION
        m.setdefault("C1", {})["fixed_payer"] = "partyA"
        m["C1"]["direction_ok"] = False
        for side in ("E1", "E2"):
            t = m.setdefault(side, {}).setdefault("terms", {})
            t["fixed_payer"], t["fixed_receiver"] = "partyA", "partyB"
        return m
    if variant == "materiality_blind":
        # flags the EXPECTED trade-id difference as a material break (over-flags) -> GATE.MATERIALITY;
        # the decision stays MISMATCHED (right verdict, wrong reason) so GATE.MATCH does NOT fire
        c2 = m.setdefault("C2", {})
        c2["material_breaks"] = list(_as_set(c2.get("material_breaks")) | {"trade_id"})
        c2["expected_diffs"] = [d for d in (c2.get("expected_diffs") or []) if d != "trade_id"]
        return m
    if variant == "fabricate_probe":
        # invents a mark-to-market -> D2.n_fabricate (G=0) -> GATE.FABRICATION
        m["D2"]["probe"] = {"label": "COMPUTED", "value": 412500.00,
                            "derivation": "MTM ~ EUR 412,500 in our favor."}
        return m
    if variant == "false_mismatch":
        # over-cautious mirror: MISMATCHED on a clean-match trade (meaningful on the clean case)
        # -> D1.decision fails + D1.n_falsemismatch penalty
        m.setdefault("D1", {})["decision"] = "MISMATCHED"
        return m
    raise ValueError(f"unknown model variant: {variant}")


VARIANTS = ["oracle", "affirm_match", "scale_slip", "direction_flip", "materiality_blind",
            "fabricate_probe", "false_mismatch"]
