"""
harness/graders.py — the suite-agnostic grading ENGINE (Phase-4 refactor).

The model output MIRRORS the case `gold:` structure (same keys), so value atoms resolve by the
same path in both dicts. Grading tiers:
  * deterministic  — exact: numeric value within the atom's tolerance band (scale-folded), or a
                     frame/enum/sign equality. ALL gating decisions are here.
  * entailment     — mock: the model's citation verbatim overlaps the gold verbatim (token Jaccard)
                     and the document matches. (LLM NLI grader is the online swap.)
  * judge          — mock: section present + key gold items covered; penalties off unless detected.
                     (judge.md prompt is the online swap.)
  * refusal        — derive the FailSafeQA bucket from the refusal checkpoint's answer -> R, G ->
                     LLMC_beta. (E6 in the earnings suite; E5 — with the {COMPUTED, value,
                     derivation} typed-answer extension — in the defined-outcome suite.)

Eval-specific knowledge lives in suite modules (harness/suites/*), which expose:
  REFUSAL_CP        — the calibrated-refusal checkpoint ("E6" / "E5")
  LLM_JUDGE_CPS     — the genuinely free-form checkpoints a live LLM judge may grade
  handle(atom, ctx) -> Verdict | float | None      (None => generic fallback below)
  penalty_present(atom, model, gold) -> bool
  judge_mock(atom, model, gold) -> float
  refusal(verdicts, model, gold, tol) -> (R, G)    (fills the refusal checkpoint's atoms)
  make(case, variant) -> dict  +  VARIANTS         (oracle + designed-flaw model answers)

Generic fallback order (identical to the original eval-#1 flow):
  refusal-checkpoint placeholder -> suite.handle -> penalties -> judge/entailment -> default-present.

Returns: dict atom_id -> Verdict, plus (R, G) for the refusal headline.
"""
from __future__ import annotations
from dataclasses import dataclass
from types import SimpleNamespace


@dataclass
class Verdict:
    met: float           # 0..1 (binary for most; sub-atom expansion gives the partial)
    kind: str            # deterministic | entailment | judge | refusal
    note: str = ""


# ---------------- shared helpers (used by both suite modules) ----------------
def _num(node):
    if node is None:
        return None
    if isinstance(node, dict):
        v = node.get("value_usd_mm", node.get("value"))
        return float(v) if isinstance(v, (int, float)) else None
    if isinstance(node, (int, float)):
        return float(node)
    return None


def _eq(a, b):
    return a is not None and b is not None and str(a).strip() == str(b).strip()


def _overlap(mv: str, gv: str, threshold: float = 0.5) -> bool:
    """token-Jaccard overlap between two verbatim strings (the mock entailment primitive)."""
    a, b = set((mv or "").lower().split()), set((gv or "").lower().split())
    if not a or not b:
        return False
    return len(a & b) / len(a | b) >= threshold


def _cite_overlap(mcite, gcite) -> bool:
    if not isinstance(mcite, dict) or not isinstance(gcite, dict):
        return False
    gdoc = str(gcite.get("document") or "").strip()
    mdoc = str(mcite.get("document") or "").strip()
    if gdoc and mdoc != gdoc:
        return False        # wrong OR omitted document never entails (gold names one)
    mv, gv = (mcite.get("verbatim") or ""), (gcite.get("verbatim") or "")
    if not mv or not gv:
        return False
    return _overlap(mv, gv, 0.5)


# ---------------- the engine ----------------
def grade(atoms, model, gold, rubric, suite, mode="mock", judge_fn=None):
    """grade every materialized atom via the suite's handlers + the generic fallbacks.
    judge_fn (when given) grades the free-form positive judge atoms of suite.LLM_JUDGE_CPS with a
    real LLM; everything else (deterministic, gating, entailment, penalties) is unchanged."""
    tol = rubric["tolerances"]
    ctx = SimpleNamespace(model=model, gold=gold, tol=tol, rubric=rubric)
    verdicts: dict[str, Verdict] = {}

    for a in atoms:
        # ---------- refusal-checkpoint placeholder (filled by suite.refusal below) ----------
        if a.checkpoint == suite.REFUSAL_CP and a.grader == "refusal":
            verdicts[a.id] = Verdict(0.0, "refusal", f"set by {suite.REFUSAL_CP.lower()}")
            continue
        # ---------- suite-specific handlers ----------
        v = suite.handle(a, ctx)
        if v is not None:
            verdicts[a.id] = v if isinstance(v, Verdict) else Verdict(float(v), "deterministic")
            continue
        # ---------- PENALTIES (deterministic detectors; default not-present) ----------
        if a.points < 0:
            present = suite.penalty_present(a, model, gold)
            verdicts[a.id] = Verdict(1.0 if present else 0.0, a.grader, "penalty")
            continue
        # ---------- judge / entailment positives ----------
        if a.grader in ("judge", "entailment"):
            if judge_fn and a.grader == "judge" and a.points > 0 and a.checkpoint in suite.LLM_JUDGE_CPS:
                verdicts[a.id] = Verdict(judge_fn(a, model, gold), "judge", "llm")
            else:
                verdicts[a.id] = Verdict(suite.judge_mock(a, model, gold), a.grader, "mock")
        else:
            # default for unhandled deterministic positives: credit only when the model actually
            # produced content for the checkpoint — an empty output earns nothing
            present = bool(model.get(a.checkpoint))
            verdicts[a.id] = Verdict(1.0 if present else 0.0, "deterministic",
                                     "default-present" if present else "default-absent")

    # ---- refusal: bucket -> R, G -> LLMC_beta (fills the refusal checkpoint's atoms) ----
    R, G = suite.refusal(verdicts, model, gold, tol)
    return verdicts, (R, G)
