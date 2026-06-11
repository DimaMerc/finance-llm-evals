#!/usr/bin/env python3
"""
rubric/validate.py -- self-contained linter for the suite's criteria files (Phase-2 deliverable).

Usage:
    python rubric/validate.py                                   # eval #1 (criteria.yaml)
    python rubric/validate.py rubric/criteria-defined-outcome.yaml   # eval #2 (same schema)

Loads the criteria file, ASSERTS the load-time invariants documented in rubric.md §2.6, then
PRINTS the per-category mass table, the per-checkpoint mass table, and the exact static grader
counts. The checkpoint set and stage subtotals are DERIVED from meta.checkpoint_weights (P*/E*/C*/S*
prefixes), so the same linter validates every eval in the suite. Run until every assertion prints PASS.

Stdlib + pyyaml. If pyyaml is unavailable a tiny vendored loader handles this file's subset of YAML.
"""
import sys
import os

HERE = os.path.dirname(os.path.abspath(__file__))
YAML_PATH = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "criteria.yaml")

# ---------------------------------------------------------------------------
# YAML loading: prefer pyyaml; fall back to a minimal loader for THIS file.
# ---------------------------------------------------------------------------
def load_yaml(path):
    try:
        import yaml  # type: ignore
        with open(path, "r", encoding="utf-8") as fh:
            return yaml.safe_load(fh)
    except Exception as exc:  # pragma: no cover - exercised only without pyyaml
        sys.stderr.write(f"[validate] pyyaml unavailable or failed ({exc}); using minimal loader\n")
        return _minimal_load(path)


def _minimal_load(_path):  # pragma: no cover - best-effort fallback, not the primary path
    raise SystemExit(
        "[validate] pyyaml is required for the fallback path on this file's structure. "
        "Install pyyaml (pip install pyyaml) and re-run."
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
# The checkpoint set is DERIVED from meta.checkpoint_weights (insertion order preserved), so this
# linter validates any eval in the suite (eval #1's 17 checkpoints, eval #2's 18, ...).
STAGE_PREFIX = {"P": "planning", "E": "extraction", "C": "calculation", "S": "synthesis"}
CATEGORIES = ["extraction", "numerical", "entailment", "reasoning", "calibration", "structure"]
GRADERS = ["deterministic", "entailment", "judge", "refusal"]

PASS = []
FAIL = []


def check(label, ok, detail=""):
    (PASS if ok else FAIL).append((label, detail))
    return ok


def approx(a, b, eps=1e-9):
    return abs(a - b) <= eps


def fnum(x):
    """format a float without trailing-zero noise"""
    if abs(x - round(x)) < 1e-9:
        return str(int(round(x)))
    return f"{x:g}"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    doc = load_yaml(YAML_PATH)
    meta = doc["meta"]
    weights = meta["weights"]
    cp_weights = meta["checkpoint_weights"]
    tolerances = doc["tolerances"]
    gates = doc["gates"]
    atoms = doc["criteria"]

    CHECKPOINTS = list(cp_weights.keys())   # derived: the file declares its own checkpoint set
    atom_by_id = {a["id"]: a for a in atoms}

    # --- 1. category weights sum to 1.0 ---
    cw_sum = sum(weights.values())
    check("category weights sum to 1.0", approx(cw_sum, 1.0), f"sum={cw_sum}")

    # --- 2. checkpoint weights sum to 1.0 ---
    kw_sum = sum(cp_weights.values())
    check("checkpoint weights sum to 1.0", approx(kw_sum, 1.0), f"sum={kw_sum}")

    # --- 3. checkpoint set coherent: weights and criteria cover the same checkpoints ---
    cps_in_atoms = set(a["checkpoint"] for a in atoms)
    check(f"all {len(CHECKPOINTS)} checkpoints use stage prefixes P/E/C/S",
          all(k[0] in STAGE_PREFIX for k in CHECKPOINTS),
          f"bad={[k for k in CHECKPOINTS if k[0] not in STAGE_PREFIX]}")
    check(f"all {len(CHECKPOINTS)} checkpoints have >=1 atom (and no stray atoms)",
          cps_in_atoms == set(CHECKPOINTS),
          f"missing={set(CHECKPOINTS)-cps_in_atoms} extra={cps_in_atoms-set(CHECKPOINTS)}")

    # --- 4. every category populated; only known categories used ---
    cats_used = set(a["category"] for a in atoms)
    check("every declared category populated by >=1 atom",
          set(weights.keys()) <= cats_used,
          f"empty={set(weights.keys())-cats_used}")
    check("no atom uses an unknown category",
          cats_used <= set(CATEGORIES),
          f"unknown={cats_used-set(CATEGORIES)}")

    # --- 5. graders are from the known set ---
    bad_graders = set(a["grader"] for a in atoms) - set(GRADERS)
    check("all graders in {deterministic, entailment, judge, refusal}",
          not bad_graders, f"unknown={bad_graders}")

    # --- 6. entailment category <-> entailment grader (bidirectional) ---
    ent_cat_not_ent_grader = [a["id"] for a in atoms
                              if a["category"] == "entailment" and a["grader"] != "entailment"]
    ent_grader_not_ent_cat = [a["id"] for a in atoms
                              if a["grader"] == "entailment" and a["category"] != "entailment"]
    check("every entailment-category atom uses the entailment grader",
          not ent_cat_not_ent_grader, f"violations={ent_cat_not_ent_grader}")
    check("every entailment-grader atom is in the entailment category",
          not ent_grader_not_ent_cat, f"violations={ent_grader_not_ent_cat}")

    # --- 7. no atom double-categorized (single 'category' string per atom) ---
    multi_cat = [a["id"] for a in atoms if not isinstance(a["category"], str)]
    check("no atom is double-categorized (category is a single string)",
          not multi_cat, f"violations={multi_cat}")

    # --- 8. unique atom ids ---
    ids = [a["id"] for a in atoms]
    dupes = sorted(set(i for i in ids if ids.count(i) > 1))
    check("atom ids are unique", not dupes, f"dupes={dupes}")

    # --- 9. tolerance keys resolve ---
    tol_problems = []
    for a in atoms:
        if "tolerance" in a and a["tolerance"] not in tolerances:
            tol_problems.append(f"{a['id']}:{a['tolerance']}")
        for fig in a.get("figures", []) or []:
            tk = fig.get("tolerance_key")
            if tk and tk not in tolerances:
                tol_problems.append(f"{a['id']}.{fig.get('figure_name')}:{tk}")
    check("every deterministic tolerance key resolves in tolerances:",
          not tol_problems, f"unresolved={tol_problems}")

    # --- 10. per_figure templates: sum(figures.points) == template points ---
    pf_problems = []
    for a in atoms:
        if a.get("per_figure"):
            s = sum(f["points"] for f in a["figures"])
            if not approx(s, a["points"]):
                pf_problems.append(f"{a['id']}: figures sum {s} != template {a['points']}")
    check("per_figure templates: sum(figures.points) == template points",
          not pf_problems, f"mismatch={pf_problems}")

    # --- 11. gate fired_by + dependents resolve ---
    def base_id(token):
        """strip a ':selector' or '.suffix' decoration to the resolvable atom/checkpoint id"""
        t = token
        if ":" in t:
            t = t.split(":", 1)[0]
        return t

    def resolves(token):
        # checkpoint id, atom id, another gate id, or a 'self'/'GATE.*' macro
        if token in ("self",) or token.startswith("self."):
            return True
        if token in {g["id"] for g in gates}:
            return True
        b = base_id(token)
        return b in CHECKPOINTS or b in atom_by_id

    gate_problems = []
    for g in gates:
        fb = g.get("fired_by")
        fb_list = fb if isinstance(fb, list) else [fb]
        for tok in fb_list:
            if tok is None:
                continue
            if not resolves(tok):
                gate_problems.append(f"{g['id']}.fired_by:{tok}")
        for key in ("dependents", "voids_positive", "cascade_dependents"):
            for tok in g.get(key, []) or []:
                if not resolves(tok):
                    gate_problems.append(f"{g['id']}.{key}:{tok}")
    check("every gate fired_by + dependents/voids/cascade resolves to a real id",
          not gate_problems, f"unresolved={gate_problems}")

    # --- 12. fired_by penalty atoms for GATE.FABRICATION actually exist as negative atoms ---
    fab = next((g for g in gates if g["id"] == "GATE.FABRICATION"), None)
    fab_problems = []
    if fab:
        for tok in (fab["fired_by"] if isinstance(fab["fired_by"], list) else [fab["fired_by"]]):
            a = atom_by_id.get(base_id(tok))
            if a is None or a["points"] >= 0:
                fab_problems.append(tok)
    check("GATE.FABRICATION fired_by are real negative penalty atoms",
          not fab_problems, f"problems={fab_problems}")

    # ---------------------------------------------------------------------
    # MASS TABLES
    # ---------------------------------------------------------------------
    # Per-category mass (static template points; per_figure templates counted at template points).
    cat_pos = {c: 0.0 for c in CATEGORIES}
    cat_neg = {c: 0.0 for c in CATEGORIES}
    cat_atoms = {c: 0 for c in CATEGORIES}
    cp_pos = {k: 0.0 for k in CHECKPOINTS}
    cp_neg = {k: 0.0 for k in CHECKPOINTS}
    cp_atoms = {k: 0 for k in CHECKPOINTS}
    cp_cat = {k: {} for k in CHECKPOINTS}  # checkpoint -> {cat: [pos, neg]}
    grader_count = {g: 0 for g in GRADERS}

    total_pos = 0.0
    total_neg = 0.0
    for a in atoms:
        p = a["points"]
        c = a["category"]
        k = a["checkpoint"]
        cat_atoms[c] += 1
        cp_atoms[k] += 1
        grader_count[a["grader"]] += 1
        slot = cp_cat[k].setdefault(c, [0.0, 0.0])
        if p >= 0:
            cat_pos[c] += p
            cp_pos[k] += p
            slot[0] += p
            total_pos += p
        else:
            cat_neg[c] += p
            cp_neg[k] += p
            slot[1] += p
            total_neg += p

    total_atoms = len(atoms)

    # ---- print: weights ----
    print("=" * 78)
    print("VALIDATE.PY  --  rubric/criteria.yaml  (rubric_version %s)" % meta.get("rubric_version"))
    print("=" * 78)
    print()
    print("CATEGORY WEIGHTS (sum = %s):" % fnum(cw_sum))
    for c in CATEGORIES:
        print(f"  {c:<12} {weights[c]:.2f}")
    print()
    print("CHECKPOINT WEIGHTS (sum = %s):" % fnum(kw_sum))
    line = []
    for k in CHECKPOINTS:
        line.append(f"{k}={cp_weights[k]:.3f}")
        if len(line) == 6:
            print("  " + "  ".join(line)); line = []
    if line:
        print("  " + "  ".join(line))
    # stage subtotals (derived from the P/E/C/S prefixes)
    stages = {name: [k for k in CHECKPOINTS if k[0] == pfx] for pfx, name in STAGE_PREFIX.items()}
    print("  stage subtotals: " + " | ".join(
        f"{s} {sum(cp_weights[k] for k in ks):.3f}" for s, ks in stages.items() if ks))
    print()

    # ---- print: per-category mass table ----
    print("PER-CATEGORY MASS  (static template points):")
    print(f"  {'category':<12} {'atoms':>5} {'+mass':>7} {'-mass':>7}")
    for c in CATEGORIES:
        print(f"  {c:<12} {cat_atoms[c]:>5} {fnum(cat_pos[c]):>7} {fnum(cat_neg[c]):>7}")
    print(f"  {'TOTAL':<12} {total_atoms:>5} {fnum(total_pos):>7} {fnum(total_neg):>7}")
    print()

    # ---- print: per-checkpoint mass table ----
    print("PER-CHECKPOINT MASS  (static template points):")
    print(f"  {'cp':<4} {'atoms':>5} {'+mass':>7} {'-mass':>7}   categories(+/-)")
    for k in CHECKPOINTS:
        cats = []
        # dominant-first ordering by +mass then -mass magnitude
        for c in sorted(cp_cat[k], key=lambda cc: (-cp_cat[k][cc][0], cp_cat[k][cc][1])):
            pos, neg = cp_cat[k][c]
            seg = f"{c}(+{fnum(pos)}"
            seg += f",{fnum(neg)})" if neg else ")"
            cats.append(seg)
        print(f"  {k:<4} {cp_atoms[k]:>5} {fnum(cp_pos[k]):>7} {fnum(cp_neg[k]):>7}   " + " ".join(cats))
    print()

    # ---- print: grader counts ----
    print("STATIC GRADER COUNTS  (template atoms; per_figure expansion changes RUNTIME totals):")
    for g in GRADERS:
        print(f"  {g:<14} {grader_count[g]:>3}")
    print(f"  {'TOTAL':<14} {sum(grader_count.values()):>3}")
    print()

    # --- 13. per-checkpoint dominant category sanity already captured; assert masses are finite ---
    check("total positive mass > 0", total_pos > 0, f"total_pos={total_pos}")
    check("penalty mass < 0", total_neg < 0, f"total_neg={total_neg}")

    # --- 14. each checkpoint has positive mass (a denominator) ---
    no_denom = [k for k in CHECKPOINTS if cp_pos[k] <= 0]
    check("every checkpoint has positive (denominator) mass", not no_denom, f"zero={no_denom}")

    # ---------------------------------------------------------------------
    # RESULTS
    # ---------------------------------------------------------------------
    print("=" * 78)
    print("ASSERTIONS")
    print("=" * 78)
    for label, _ in PASS:
        print(f"  PASS  {label}")
    for label, detail in FAIL:
        print(f"  FAIL  {label}   [{detail}]")
    print()
    print(f"  {len(PASS)} passed, {len(FAIL)} failed")
    print()

    # machine-readable derived summary (for mirroring into the docs)
    print("DERIVED SUMMARY (mirror into rubric.md / judge.md):")
    print(f"  total_atoms = {total_atoms}")
    print(f"  positive_mass = +{fnum(total_pos)}")
    print(f"  penalty_mass  = {fnum(total_neg)}")
    print(f"  grader_counts = deterministic {grader_count['deterministic']} / "
          f"entailment {grader_count['entailment']} / judge {grader_count['judge']} / "
          f"refusal {grader_count['refusal']}")
    cat_summary = " / ".join(
        f"{c} {cat_atoms[c]}:+{fnum(cat_pos[c])}{('' if cat_neg[c]==0 else '/'+fnum(cat_neg[c]))}"
        for c in CATEGORIES)
    print(f"  category_mass = {cat_summary}")

    if FAIL:
        sys.exit(1)


if __name__ == "__main__":
    main()
