"""
harness/live.py — run a REAL model (via LM Studio's OpenAI-compatible local server) and turn its
answer into the structured memo the harness grades. All local, no API spend.

Flow: fetch the earnings press release text from EDGAR -> build a prompt (schema + filing text +
the oracle-supplied consensus + the two E6 probe questions) -> call the local model -> tolerantly
parse its JSON into the harness model-answer shape.

Default endpoint is LM Studio's server: http://localhost:1234/v1  (Developer tab -> Start Server).
Uses only the standard library (urllib/json) so there is no extra dependency.
"""
from __future__ import annotations
import json
import re
import time
import urllib.request
import urllib.error


def _fold_system(messages):
    """Some chat templates (e.g. Gemma) reject a `system` role -> fold it into the first user turn."""
    sys_text = "\n\n".join(m["content"] for m in messages if m.get("role") == "system")
    rest = [m for m in messages if m.get("role") != "system"]
    if sys_text and rest and rest[0].get("role") == "user":
        rest = [{"role": "user", "content": sys_text + "\n\n" + rest[0]["content"]}] + rest[1:]
    return rest

UA = "finance-llm-evals research welt.management.solutions@gmail.com"
DEFAULT_ENDPOINT = "http://localhost:1234/v1"


# ---------------- LM Studio (OpenAI-compatible) client ----------------
def _post(url, payload, timeout=600):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def list_models(endpoint=DEFAULT_ENDPOINT):
    with urllib.request.urlopen(endpoint.rstrip("/") + "/models", timeout=15) as r:
        return [m["id"] for m in json.loads(r.read().decode("utf-8")).get("data", [])]


def chat(messages, *, endpoint=DEFAULT_ENDPOINT, model_id=None, max_tokens=4000, temperature=0.0,
         stream=True, timeout=90, deadline=240, _folded=False):
    """Call the OpenAI-compatible chat endpoint. Streaming by default so a long generation trickles
    tokens. `timeout` is the per-read socket timeout; `deadline` is a HARD wall-clock cap on the whole
    call -- the loop breaks past it no matter what, so a stalled/looping server can never hang forever.
    On a 400 (some templates, e.g. Gemma, reject a `system` role) we fold system into user and retry."""
    if model_id is None:
        ms = list_models(endpoint)
        if not ms:
            raise RuntimeError("LM Studio reports no loaded model. Load one and Start Server.")
        model_id = ms[0]
    url = endpoint.rstrip("/") + "/chat/completions"
    payload = {"model": model_id, "messages": messages, "max_tokens": max_tokens,
               "temperature": temperature, "stream": stream}
    try:
        if not stream:
            return _post(url, payload, timeout)["choices"][0]["message"]["content"], model_id
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        parts, t0 = [], time.monotonic()
        with urllib.request.urlopen(req, timeout=timeout) as r:
            for raw in r:                               # SSE: one "data: {...}" line per token chunk
                if time.monotonic() - t0 > deadline:    # hard wall-clock cap -> never hang
                    break
                line = raw.decode("utf-8", "ignore").strip()
                if not line.startswith("data:"):
                    continue
                d = line[5:].strip()
                if d == "[DONE]":
                    break
                try:
                    obj = json.loads(d)
                except json.JSONDecodeError:
                    continue
                delta = (obj.get("choices") or [{}])[0].get("delta", {}).get("content")
                if delta:
                    parts.append(delta)
        return "".join(parts), model_id
    except urllib.error.HTTPError as e:
        if e.code == 400 and not _folded and any(m.get("role") == "system" for m in messages):
            return chat(_fold_system(messages), endpoint=endpoint, model_id=model_id, max_tokens=max_tokens,
                        temperature=temperature, stream=stream, timeout=timeout, deadline=deadline, _folded=True)
        raise


# ---------------- fetch the press release text ----------------
def _fetch_stripped(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=90) as r:
        html = r.read().decode("utf-8", "ignore")
    text = re.sub(r"<[^>]+>", " ", html)
    text = (text.replace("&#160;", " ").replace("&nbsp;", " ").replace("&amp;", "&")
                .replace("&#8217;", "'").replace("&#8212;", "-").replace("&#8220;", '"').replace("&#8221;", '"'))
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)
    return text.strip()


def fetch_release_text(case, max_chars=60000) -> str:
    url = ((case.get("sources", {}) or {}).get("release", {}) or {}).get("ex99_1_url")
    if not url:
        raise RuntimeError(f"{case['case_id']}: no sources.release.ex99_1_url to read")
    return _fetch_stripped(url)[:max_chars]


# The 10-Q is ~100k tokens -- too big for a 32k-context model alongside the press release. The income
# statement and cash flow are already in the press release, so the UNIQUE value of the 10-Q is the
# BALANCE SHEET (working capital), the share reconciliation, and the segment/geography footnote. Anchor
# the slice on the balance sheet (skipping the redundant income statement) so a ~33k-char window reaches
# the geography footnote and the combined prompt fits a 32k context.
_BS_ANCHORS = ["accounts receivable", "total current assets", "condensed consolidated balance sheets"]
_STMT_ANCHORS = ["condensed consolidated statements of operations", "condensed consolidated balance sheet",
                 "condensed consolidated statements of cash flows"]


def fetch_tenq_slice(case, length=20000, lead=1000) -> str:
    url = ((case.get("sources", {}) or {}).get("tenq", {}) or {}).get("url")
    if not url:
        return ""
    txt = _fetch_stripped(url)
    low = txt.lower()
    pos = min([p for p in (low.find(a) for a in _BS_ANCHORS) if p >= 0], default=-1)
    if pos < 0:
        pos = min([p for p in (low.find(a) for a in _STMT_ANCHORS) if p >= 0], default=-1)
    start = max(0, pos - lead) if pos >= 0 else 0
    return txt[start:start + length]


# ---------------- prompt ----------------
SCHEMA = """Return ONE JSON object with EXACTLY these keys (use null where the document does not
disclose a value; never invent a number). Aggregates in USD MILLIONS as plain numbers
(e.g. 1144.969); per-share in dollars (e.g. 0.35).

{
 "P1": {"issuer":"", "ticker":"", "fiscal_period_label":"", "period_end_date":"YYYY-MM-DD", "filing_type":"10-Q"},
 "P2": {"statement_scale":"thousands|millions", "reporting_currency":"USD", "per_share_in_dollars":true, "cross_doc_reconciled":true},
 "P3": {"consensus_basis":"non_gaap|gaap", "consensus_statistic":"mean|median"},
 "E1": {"figures": {"total_revenue":{"value_usd_mm":null}, "gross_profit":{"value_usd_mm":null},
        "operating_income":{"value_usd_mm":null}, "pretax_income":{"value_usd_mm":null},
        "income_tax_provision":{"value_usd_mm":null}, "net_income_gaap":{"value_usd_mm":null},
        "gaap_basic_eps":{"value":null}, "gaap_diluted_eps":{"value":null}}},
 "E2": {"segments":[{"name":"","revenue_usd_mm":null}], "corporate_eliminations":null,
        "wavg_basic_shares":{"value":null}, "wavg_gaap_diluted_shares":{"value":null},
        "wavg_nongaap_diluted_shares":{"value":null}, "prior_year_diluted_shares":{"value":null}},
 "E3": {"adjusted_eps":{"value":null}, "addbacks":[{"name":"","value_usd_mm":null}],
        "tax_effect_of_adjustments":{"value_usd_mm":null}, "operating_cash_flow":{"value_usd_mm":null}, "capex":{"value_usd_mm":null}},
 "E4": {"guidance":null, "not_disclosed":null},
 "E5": {"accounts_receivable_current":{"value_usd_mm":null}, "accounts_receivable_prior":{"value_usd_mm":null},
        "inventory_current":"N/A", "deferred_revenue_current":{"value_usd_mm":null}, "cogs":"N/A"},
 "E6": {"undisclosed_probe":{"answer":"NOT_DISCLOSED or a number","reason":""}, "answerable_twin":{"value":null}},
 "C1": {"yoy_revenue_pct":null, "qoq_revenue_pct":null, "yoy_diluted_share_change_pct":null, "signs_ok":true},
 "C2": {"gross_margin":null, "operating_margin":null, "net_margin":null,
        "margin_deltas_bps":{"operating":null,"net":null}, "fcf_usd_mm":null},
 "C3": {"final_nongaap_eps":null, "nongaap_diluted_shares_used":null},
 "C4": {"effective_tax_rate":null, "efftax_yoy_delta_pp":null, "dso":null, "ocf_to_net_income":null},
 "C5": {"revenue_beatmiss_abs_usd_mm":null, "eps_beatmiss_abs":null, "direction":{"revenue":"beat|in_line|miss","eps":"beat|in_line|miss"}},
 "S1": {"reported_direction":{"revenue":"beat|in_line|miss","eps":"beat|in_line|miss"}, "guidance_vs_street":"above|in_line|below|n/a"},
 "S2": {"material_changes":[""], "swing_factor":"", "qoe_flags":[""]},
 "S3": {"bottom_line":"", "not_determinable":[""]}
}"""


def build_messages(case, text, tenq_text=""):
    cons = case.get("consensus", {}) or {}
    e6 = case["gold"]["E6"]
    probe_q = (e6.get("undisclosed_probe", {}) or {}).get("question", "")
    twin_q = (e6.get("answerable_twin", {}) or {}).get("question", "")
    src = "the earnings press release" + (" and the 10-Q excerpt" if tenq_text else "")
    system = (f"You are a buy-side equity analyst. Read {src} and produce a structured JSON earnings "
              "memo. Extract figures exactly as reported; mark anything not in the documents as null "
              "(or 'NOT_DISCLOSED' for the E6 probe). DO NOT invent numbers. Pay attention to the "
              "statement scale header ('in thousands' vs 'in millions'); per-share figures are already "
              "in dollars. Benchmark beat/miss against the consensus given below, on the matching "
              "basis. Return ONLY the JSON object, no prose.")
    user = (f"{SCHEMA}\n\n"
            f"ORACLE-SUPPLIED CONSENSUS (not in the filing): revenue={cons.get('revenue',{}).get('value_usd_mm')} USD mm, "
            f"EPS={cons.get('eps',{}).get('value')} ({cons.get('eps',{}).get('basis')} basis, {cons.get('eps',{}).get('statistic')}).\n"
            f"E6 undisclosed probe (answer NOT_DISCLOSED if the documents do not break it out): {probe_q}\n"
            f"E6 answerable twin (this IS disclosed -- find it): {twin_q}\n\n"
            f"=== EARNINGS PRESS RELEASE ===\n{text}")
    if tenq_text:
        user += f"\n\n=== 10-Q EXCERPT (financial statements + footnotes) ===\n{tenq_text}"
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


# ---------------- tolerant JSON parse ----------------
def _repair_json(s: str) -> str:
    s = re.sub(r"(?<=\d),(?=\d{3}(?:\D|$))", "", s)                              # thousands separators inside numbers
    s = re.sub(r":\s*-?[\d.]+\s*[-+*/][-+*/\d.()\s]*(?=[,}\]\n])", ": null", s)  # un-evaluated arithmetic expr -> null
    s = re.sub(r",\s*([}\]])", r"\1", s)                                          # trailing commas
    return s


def parse_answer(content: str) -> dict:
    s = content.strip()
    s = re.sub(r"^```(?:json)?|```$", "", s, flags=re.MULTILINE).strip()
    a, b = s.find("{"), s.rfind("}")
    if a >= 0 and b > a:
        s = s[a:b + 1]
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        return json.loads(_repair_json(s))            # repair common LLM-JSON errors and retry


def answer(case, *, endpoint=DEFAULT_ENDPOINT, model_id=None, max_tokens=4000, with_tenq=False):
    text = fetch_release_text(case)
    tenq = fetch_tenq_slice(case) if with_tenq else ""
    msgs = build_messages(case, text, tenq)
    approx_tok = sum(len(m["content"]) for m in msgs) // 4
    content, used = chat(msgs, endpoint=endpoint, model_id=model_id, max_tokens=max_tokens)
    if not content.strip():
        raise RuntimeError(
            f"Model returned an EMPTY completion (prompt ~{approx_tok:,} tokens). This almost always "
            f"means the prompt exceeded the model's loaded context window in LM Studio. Reload the model "
            f"with a larger context length (>= {((approx_tok + max_tokens)//1024 + 4):d}k) and retry"
            + (" (or drop --tenq)." if with_tenq else "."))
    try:
        out = parse_answer(content)
    except json.JSONDecodeError:
        # one retry with a terse reminder
        msgs.append({"role": "assistant", "content": content[:2000]})
        msgs.append({"role": "user", "content": "That was not valid JSON. Return ONLY the JSON object."})
        content, used = chat(msgs, endpoint=endpoint, model_id=model_id, max_tokens=max_tokens)
        out = parse_answer(content)
    out["_model_id"] = used
    out["_raw"] = content
    return out
