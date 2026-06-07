#!/usr/bin/env python3
"""
rubric/worked_example.py -- reproduces the §4.3 worked mini-example numbers from criteria.yaml.

Scenario (F19): an asset manager. P1 pinned correctly; P2 scale slip ("in thousands" read as
"in millions"). The arithmetic is internally consistent (scale-invariant ratios/growth/margins
all compute), but every scaled-aggregate VALUE atom fails tolerance after scale-folding, and the
GAAP-vs-consensus beat/miss and the segment tie-out (scaled dollars) fail. Synthesis reads well.

Asset-manager pruning (F6): gross_profit is N/A -> pruned from E1.value + E1.cite; inventory and
cogs are N/A -> pruned from E5.values + E5.cite. The "correctly marked N/A" atoms (E1.sector_na,
E5.sector_na) are the only scored atoms for those figures.

Per-share figures (P2.3 / F2): EPS sub-figures are already in dollars, NOT scaled -> they stay
correct under the gate (E1 gaap_*_eps, E4 guidance_eps_*, C5 eps_beatmiss_abs).

PER-CASE MANIFEST ASSUMPTIONS (this scenario; the harness reads these from the case manifest):
  - 3 disclosed segments (N_SEGMENTS = 3)        -> E2.segments segment_revenue_rows split 5.0/3.
  - 2 disclosed add-backs (N_ADDBACKS = 2)       -> E3.addbacks addback_rows split 6.0/2 and
                                                    C3.addbacks_steps split 6.0/2.
  - asset-manager prune set {gross_profit, inventory, cogs} (F6) -> gross_profit pruned from
    E1.value + E1.cite; inventory_current/inventory_prior/cogs pruned from E5.values + E5.cite;
    the "correctly marked N/A" atoms (E1.sector_na, E5.sector_na) are the only scored atoms there.
  - P2.3 / P2.4 are ASSUMED-PASSED in this scale-slip scenario: per-share is read correctly (P2.3,
    EPS already in dollars, not multiplied by the aggregate scale) and cross-document scale is
    reconciled to a common base (P2.4). Only the scale-DECLARATION atom P2.1 is missed, which is what
    fires GATE.P2 -- so P2.3/P2.4 keep their positive credit (they model the "did the right per-share /
    cross-doc handling" legs that survive a header-scale misread).

E6 (F1): E6's HEADLINE is NOT awarded/raw_pos -- it is the FailSafeQA F-beta LLMC_beta(R, G), beta=0.5.
In this scenario E6 is a grounded refusal on the undisclosed probe AND the answerable twin is retrieved
and cited, so R=1, G=1 -> LLMC_beta = 1.000. This faithful E6 branch reproduces the same 1.000 the
generic pool gave, so the published CaseScore numbers (0.831 / 0.453 / 0.378) are unchanged.

Run:  python worked_example.py
"""
import os
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
d = yaml.safe_load(open(os.path.join(HERE, "criteria.yaml"), encoding="utf-8"))
cpw = d["meta"]["checkpoint_weights"]
atoms = d["criteria"]
gp2 = [g for g in d["gates"] if g["id"] == "GATE.P2"][0]["dependents"]

# --- per-case manifest assumptions (segment/add-back counts; pruned N/A figures) ---
N_SEGMENTS = 3
N_ADDBACKS = 2
PRUNE = {
    "E1.value": {"gross_profit"},
    "E1.cite":  {"gross_profit"},
    "E5.values": {"inventory_current", "inventory_prior", "cogs"},
}


def materialize(a):
    """expand a per_figure template into (subid, points, tolerance_key); else the atom itself."""
    out = []
    if a.get("per_figure"):
        for f in a["figures"]:
            nm, pts, tk = f["figure_name"], f["points"], f.get("tolerance_key")
            if f.get("expand") == "per_segment_row":
                for i in range(N_SEGMENTS):
                    out.append((f"{a['id']}.seg{i}", pts / N_SEGMENTS, tk))
            elif f.get("expand") == "per_addback_row":
                for i in range(N_ADDBACKS):
                    out.append((f"{a['id']}.row{i}", pts / N_ADDBACKS, tk))
            else:
                out.append((f"{a['id']}.{nm}", pts, tk))
    else:
        out.append((a["id"], a["points"], a.get("tolerance")))
    return out


def is_pruned(aid, subid):
    return aid in PRUNE and any(subid.endswith("." + p) for p in PRUNE[aid])


def p2_hits(aid, tol):
    """does GATE.P2 zero this (sub)atom? checkpoint-level deps (C1..C5) or atom[:selector] deps."""
    if aid.split(".")[0] in gp2:
        return True
    for dep in gp2:
        base, sel = (dep.split(":", 1) + [None])[:2] if ":" in dep else (dep, None)
        if base == aid and (sel is None or (sel == "aggregate" and tol == "aggregate")):
            return True
    return False


SCALED_AGG_VALUE = {"E1.value", "E2.segments", "E2.wavg_diluted", "E2.nongaap_diluted",
                    "E2.prioryr_shares", "E3.addbacks", "E3.taxeffect_line", "E3.ocf_capex",
                    "E4.ranges", "E5.values", "P2.3", "P2.4"}


def model_m(sid, tol):
    """the model's met-fraction for the scale-slip scenario (ungated, pre-gate)."""
    if sid == "P2.1":
        return 0.0                               # the scale atom itself is missed
    if tol == "eps":
        return 1.0                               # per-share not scaled -> stays right
    if tol == "beat_miss_rev":
        return 0.0                               # revenue beat/miss in scaled $ fails
    if sid == "C5.tieout":
        return 0.0                               # segment tie-out in scaled $ fails
    if any(sid.startswith(x) for x in SCALED_AGG_VALUE) and tol == "aggregate":
        return 0.0                               # scaled aggregate value wrong after scale-fold
    return 1.0                                    # everything scale-invariant is internally consistent


# --- F1: E6's headline is the FailSafeQA F-beta, NOT awarded/raw_pos (rubric.md §2.2/§7) ---
BETA = d["meta"].get("refusal_beta", 0.5)


def LLMC_beta(R, G, beta=BETA):
    """FailSafeQA F-beta on the two E6 axes; refuse-all => R=0 => 0. (rubric.md §7)"""
    denom = beta * beta * G + R
    return 0.0 if denom == 0 else (1 + beta * beta) * R * G / denom


def e6_headline_RG():
    """The §4.3 scenario: grounded refusal on the undisclosed probe (bucket A -> G=1) AND the
    answerable twin retrieved-and-cited (R=1). Neither the scale slip nor GATE.P2 touch E6, so the
    headline is identical ungated and gated. LLMC_beta(1, 1) = 1.000 -> matches the generic pool's
    prior E6 score, keeping the published CaseScore numbers unchanged."""
    R, G = 1.0, 1.0
    return R, G, LLMC_beta(R, G)


rows = {}
for k in cpw:
    sub = []
    for a in atoms:
        if a["checkpoint"] != k:
            continue
        for (sid, pts, tol) in materialize(a):
            if is_pruned(a["id"], sid):
                continue
            sub.append((sid, pts, tol, a["id"]))
    raw_pos = sum(p for (_, p, _, _) in sub if p > 0)

    if k == "E6":
        # F1: E6 headline = LLMC_beta(R, G), not the awarded/raw_pos pool. raw_pos is still reported
        # (for the table column) from the materialized positive atoms, but does NOT set the score.
        R, G, e6 = e6_headline_RG()
        rows[k] = (raw_pos, e6, e6)               # gate does not touch E6 -> ungated == gated
        continue

    aw_u = aw_g = 0.0
    for (sid, pts, tol, aid) in sub:
        if pts < 0:
            continue                              # no penalty met (clean except the scale slip)
        m = model_m(sid, tol)
        aw_u += m * pts
        aw_g += (0.0 if p2_hits(aid, tol) else m) * pts
    cs_u = max(0.0, min(1.0, aw_u / raw_pos)) if raw_pos else 0.0
    cs_g = max(0.0, min(1.0, aw_g / raw_pos)) if raw_pos else 0.0
    rows[k] = (raw_pos, cs_u, cs_g)

case_u = sum(cpw[k] * rows[k][1] for k in cpw)
case_g = sum(cpw[k] * rows[k][2] for k in cpw)

print("checkpoint  raw_pos  cs_ungated  cs_gated   W")
for k in cpw:
    rp, cu, cg = rows[k]
    print(f"  {k:<8} {rp:7.3f}   {cu:8.3f}   {cg:7.3f}   {cpw[k]:.3f}")
print()
print(f"CaseScore_ungated = {case_u:.3f}")
print(f"CaseScore_gated   = {case_g:.3f}")
print(f"GAP               = {case_u - case_g:.3f}")
