"""
harness/judge_llm.py — a real LLM-as-judge backend (local, via LM Studio) for the free-form atoms.

Implements the judge.md contract for the genuinely subjective checkpoints (P3 scope, S2 material
changes / quality, S3 calibrated bottom line): one atomic criterion per call; the judge is given the
criterion + the memo's relevant section + the GOLD reference; it does NOT re-derive numbers; it returns
a strict JSON verdict {criteria_met, reasoning}. This replaces the offline `--judge mock` (which gives
any non-empty answer a free 1.0) for those atoms, so the synthesis score is real.

Scope (v1): the positive `judge`-graded atoms of P3 / S2 / S3. S1's directional atoms keep their
deterministic C5-contingency logic; entailment + penalty atoms stay on their existing path.
"""
from __future__ import annotations
import json
from . import live

LLM_JUDGE_CHECKPOINTS = {"P3", "S2", "S3"}

_SYS = ("You are a meticulous finance-domain grader applying ONE rubric criterion to an equity "
        "analyst's earnings memo. You are given the criterion, the relevant part of the memo, and a "
        "GOLD reference written by an expert. Decide whether the memo SATISFIES the criterion. Treat "
        "the GOLD as ground truth; do NOT re-derive or recompute any number. Be strict: award only if "
        "the memo actually contains the required substance (not merely a non-empty answer). Reply with "
        "ONLY a JSON object: {\"criteria_met\": true|false, \"reasoning\": \"<=2 sentences\"}.")


def _section(container, cp):
    return container.get(cp, {}) if isinstance(container, dict) else {}


def make_judge(endpoint=live.DEFAULT_ENDPOINT, model_id=None, max_tokens=300):
    """Return judge_fn(atom, model, gold) -> met in {0.0, 1.0} using the local model."""
    def judge_fn(atom, model, gold):
        cp = atom.checkpoint
        memo = json.dumps(_section(model, cp), default=str)[:4000]
        ref = json.dumps(_section(gold, cp), default=str)[:4000]
        user = (f"CRITERION ({atom.id}): {_criterion_text(atom)}\n\n"
                f"MEMO SECTION ({cp}):\n{memo}\n\n"
                f"GOLD REFERENCE ({cp}):\n{ref}\n\n"
                "Does the memo satisfy the criterion? JSON only.")
        try:
            content, _ = live.chat([{"role": "system", "content": _SYS}, {"role": "user", "content": user}],
                                   endpoint=endpoint, model_id=model_id, max_tokens=max_tokens, temperature=0.0)
            verdict = live.parse_answer(content)
            return 1.0 if bool(verdict.get("criteria_met")) else 0.0
        except Exception:
            return 0.0   # a judge that can't decide does not award credit
    return judge_fn


# criterion text is carried on the rubric atom; the harness passes the Atom which only has ids/points,
# so we look the text up from criteria.yaml once and cache it.
_CRIT_TEXT = {}


def _criterion_text(atom):
    if not _CRIT_TEXT:
        from .rubric import load_rubric
        for a in load_rubric()["criteria"]:
            _CRIT_TEXT[a["id"]] = a.get("criterion", "")
    return _CRIT_TEXT.get(atom.source_id, atom.source_id)
