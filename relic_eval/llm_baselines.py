"""
LLM baselines on the source-level benchmark.

  llm_C  (LLM-only)        the model sees the ORIGINAL and MODIFIED JCL text
  llm_D  (dependency+LLM)  as C, plus an automatically extracted dependency
                           summary (steps, programs, COND, datasets by DISP)
                           of both versions, produced by RELIC's JCL parser in
                           its IBM-conformant mode (continuation lines merged),
                           so the baseline is not handicapped by the v1.0
                           continuation defect

Differences from the legacy baselines (see docs/remediation/PRE_REMEDIATION_AUDIT.md, P6):
  * the model sees the actual code and change (the legacy prompt contained
    only the file name, a one-line description and the operator name, which
    leaked the label);
  * no operator name, site, intent or label is included in the prompt;
  * failed calls (HTTP errors, unparseable output) are NEVER scored — they
    are excluded and reported as coverage (the legacy harness scored 245/248
    rate-limited calls as "no regression");
  * every request/response is cached under results/final/raw/llm_cache/, so a
    completed run can be re-scored offline and audited;
  * mutants are processed in a fixed, seeded random order (C and D for the same
    mutant back to back). If the provider quota runs out, the completed part is
    a uniform random subsample of the population, never a hand-picked one; the
    run can be resumed later from the cache.

Configuration (environment):
  RELIC_LLM_PROVIDER   groq (default) | openai | anthropic
  RELIC_LLM_MODEL      default: openai/gpt-oss-120b (groq), gpt-4o (openai),
                       claude-sonnet-5-5 (anthropic). (llama-3.3-70b-versatile,
                       the earlier default, is no longer served by Groq.)
  GROQ_API_KEY / OPENAI_API_KEY / ANTHROPIC_API_KEY
  RELIC_LLM_MIN_INTERVAL  seconds between calls (default 2.0)

Decoding: temperature 0, one sample per prompt, max_tokens 1024 (gpt-oss is a
reasoning model; reasoning tokens count against max_tokens), reasoning_effort
"low" on Groq gpt-oss models.

Usage:
  python -m relic_eval.llm_baselines [--subjects carddemo] [--limit N]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

from loguru import logger

from legacy_contract.ir.model import EntityType, RelationType
from legacy_contract.parsers.jcl_parser import JCLParser
from relic_eval.subjects import ROOT

logger.remove()

RAW = ROOT / "results" / "final" / "raw"
CACHE = RAW / "llm_cache"
RECORDS = RAW / "llm_records.jsonl"
STATUS = RAW / "llm_status.json"          # deterministic: derived from cache + records
RUN_LOG = RAW / "llm_last_run.json"       # run-specific: calls made, quota events, time
PROMPT_VERSION = "source_diff_v4"
MAX_TOKENS = 1024
ORDER_SEED = 20261004
# A rate-limit wait longer than this means a daily quota is exhausted.
QUOTA_WAIT_LIMIT_S = 600.0

DEFAULT_MODELS = {
    "groq": "openai/gpt-oss-120b",
    "openai": "gpt-4o",
    "anthropic": "claude-sonnet-5-5",
}
ENDPOINTS = {
    "groq": "https://api.groq.com/openai/v1/chat/completions",
    "openai": "https://api.openai.com/v1/chat/completions",
}
KEY_VARS = {"groq": "GROQ_API_KEY", "openai": "OPENAI_API_KEY", "anthropic": "ANTHROPIC_API_KEY"}

SYSTEM = ("You are an expert z/OS JCL engineer reviewing a change made while migrating a batch "
          "job. You answer only with a JSON object.")

TASK = """Below are two versions of the same JCL job: ORIGINAL and MODIFIED.

Decide whether the MODIFIED version can behave differently from the ORIGINAL when it is
executed. Behaviour means: which steps run (including when a step ends with a non-zero
return code or abends), the order in which steps run, which datasets each step creates,
reads, writes or deletes, which data a step reads, and the final state of the datasets.
Comments, formatting and job output-class (MSGCLASS) changes are not behaviour.

Answer with exactly one JSON object:
{{"behavior_changed": true or false, "confidence": number between 0 and 1, "reason": "one sentence"}}

ORIGINAL:
```
{original}
```

MODIFIED:
```
{modified}
```
"""

DEP_BLOCK = """
DEPENDENCY SUMMARY (extracted automatically from each version):
ORIGINAL:
{dep_original}
MODIFIED:
{dep_modified}
"""


def dependency_summary(text: str, path: str) -> str:
    _r, ir = JCLParser().parse_lines(text.splitlines(), path)
    lines = []
    steps = [e for e in ir.entities.values() if e.entity_type == EntityType.STEP]
    for s in steps:
        calls = [r.target.name for r in ir.relations
                 if r.source.entity_id == s.entity_id and r.relation_type == RelationType.CALLS]
        prod = [r.target.name for r in ir.relations
                if r.source.entity_id == s.entity_id and r.relation_type == RelationType.PRODUCES]
        cons = [r.target.name for r in ir.relations
                if r.source.entity_id == s.entity_id and r.relation_type == RelationType.CONSUMES]
        cond = s.attributes.get("cond", "")
        lines.append(f"- step {s.name}: runs {','.join(calls) or '?'}"
                     + (f"; COND={cond}" if cond else "")
                     + (f"; creates {', '.join(prod)}" if prod else "")
                     + (f"; uses {', '.join(cons)}" if cons else ""))
    order = [r for r in ir.relations if r.relation_type == RelationType.MUST_PRECEDE]
    if order:
        lines.append("- order: " + ", ".join(f"{r.source.name}<{r.target.name}" for r in order))
    return "\n".join(lines) or "- (no steps)"


def build_prompt(baseline: str, original: str, modified: str, path: str) -> str:
    p = TASK.format(original=original.rstrip(), modified=modified.rstrip())
    if baseline == "D":
        p += DEP_BLOCK.format(dep_original=dependency_summary(original, path),
                              dep_modified=dependency_summary(modified, path))
    return p


def parse_answer(text: str) -> tuple[bool | None, float | None, str]:
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return None, None, "no JSON object in response"
    try:
        obj = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None, None, "invalid JSON"
    v = obj.get("behavior_changed")
    if not isinstance(v, bool):
        return None, None, "behavior_changed missing or not boolean"
    conf = obj.get("confidence")
    return v, float(conf) if isinstance(conf, (int, float)) else None, str(obj.get("reason", ""))[:300]


class QuotaExhausted(Exception):
    """The provider asked us to wait longer than QUOTA_WAIT_LIMIT_S (daily quota)."""


class Client:
    def __init__(self) -> None:
        self.provider = os.environ.get("RELIC_LLM_PROVIDER", "groq").lower()
        self.model = os.environ.get("RELIC_LLM_MODEL", DEFAULT_MODELS.get(self.provider, ""))
        self.key = os.environ.get(KEY_VARS.get(self.provider, ""), "")
        self.min_interval = float(os.environ.get("RELIC_LLM_MIN_INTERVAL", "2.0"))
        self._last = 0.0

    @property
    def available(self) -> bool:
        return bool(self.key) and self.provider in KEY_VARS

    @property
    def params(self) -> dict:
        p: dict = {"temperature": 0, "max_tokens": MAX_TOKENS}
        if self.provider == "groq" and "gpt-oss" in self.model:
            p["reasoning_effort"] = "low"
        return p

    def _request(self, prompt: str) -> str:
        if self.provider == "anthropic":
            body = {"model": self.model, "max_tokens": MAX_TOKENS, "temperature": 0,
                    "system": SYSTEM, "messages": [{"role": "user", "content": prompt}]}
            req = urllib.request.Request(
                "https://api.anthropic.com/v1/messages", data=json.dumps(body).encode(),
                headers={"x-api-key": self.key, "anthropic-version": "2023-06-01",
                         "content-type": "application/json"})
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read())
            return "".join(b.get("text", "") for b in data.get("content", []))
        body = {"model": self.model, "seed": 42, **self.params,
                "messages": [{"role": "system", "content": SYSTEM},
                             {"role": "user", "content": prompt}]}
        req = urllib.request.Request(
            ENDPOINTS[self.provider], data=json.dumps(body).encode(),
            headers={"Authorization": f"Bearer {self.key}", "Content-Type": "application/json",
                     "User-Agent": "relic-eval/1.1"})
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read())
        return data["choices"][0]["message"]["content"] or ""

    @staticmethod
    def _retry_after(e: urllib.error.HTTPError, body: str) -> float | None:
        ra = e.headers.get("retry-after") if e.headers else None
        if ra:
            try:
                return float(ra)
            except ValueError:
                pass
        m = re.search(r"try again in (?:(\d+)h)?(?:(\d+)m)?([\d.]+)s", body)
        if m:
            h, mi, sec = m.groups()
            return int(h or 0) * 3600 + int(mi or 0) * 60 + float(sec)
        return None

    def complete(self, prompt: str) -> tuple[str | None, str]:
        """
        Return (text, error). Retries per-minute rate limits and server errors
        with backoff; raises QuotaExhausted when the provider's requested wait
        exceeds QUOTA_WAIT_LIMIT_S. Non-retryable errors (e.g. HTTP 413, request
        larger than the account's per-minute token limit) are returned as errors.
        """
        delay = 5.0
        last_err = ""
        for _attempt in range(10):
            wait = self.min_interval - (time.time() - self._last)
            if wait > 0:
                time.sleep(wait)
            self._last = time.time()
            try:
                return self._request(prompt), ""
            except urllib.error.HTTPError as e:
                body = e.read().decode(errors="replace")[:500] if e.fp else ""
                code = (re.search(r'"code"\s*:\s*"([^"]+)"', body) or [None, ""])[1]
                last_err = f"HTTP {e.code} {code}".strip()
                if e.code in (429, 500, 502, 503, 529):
                    ra = self._retry_after(e, body)
                    if ra is not None and ra > QUOTA_WAIT_LIMIT_S:
                        raise QuotaExhausted(f"{last_err}: provider asked to wait {ra:.0f}s")
                    time.sleep((ra + 1.0) if ra is not None else delay)
                    delay = min(delay * 2, 120)
                    continue
                return None, last_err
            except (urllib.error.URLError, TimeoutError, KeyError, IndexError,
                    json.JSONDecodeError) as e:
                last_err = repr(e)[:200]
                time.sleep(delay)
                delay = min(delay * 2, 120)
        return None, last_err or "retries exhausted"


def population_order(population: list[dict]) -> list[dict]:
    """Fixed, seeded random order (independent of file order and of outcomes)."""
    import random
    ordered = sorted(population, key=lambda r: r["mutation_id"])
    random.Random(ORDER_SEED).shuffle(ordered)
    return ordered


def cache_key(provider: str, model: str, prompt: str) -> str:
    return hashlib.sha256(f"{provider}|{model}|{PROMPT_VERSION}|{prompt}".encode()).hexdigest()[:24]


def run(subjects: list[str] | None, limit: int | None) -> dict:
    records_path = RAW / "evaluation_records.jsonl"
    records = [json.loads(line) for line in open(records_path)]
    population = population_order([r for r in records if r["status"] == "EVALUABLE"
                                   and (not subjects or r["subject_system"] in subjects)])
    if limit:
        population = population[:limit]
    client = Client()
    status = {
        "prompt_version": PROMPT_VERSION,
        "provider": client.provider,
        "model": client.model,
        "decoding": {**client.params, "seed": 42},
        "samples_per_prompt": 1,
        "order_seed": ORDER_SEED,
        "population": "EVALUABLE mutants" + (f" of {subjects}" if subjects else " of all subjects"),
        "n_population": len(population),
    }
    CACHE.mkdir(parents=True, exist_ok=True)
    from relic_eval.subjects import SUBJECTS
    out = []
    n_called = 0
    quota_note = ""
    started = time.time()
    for i, r in enumerate(population):
        subj = SUBJECTS[r["subject_system"]]
        original = (subj.root / r["file"]).read_text(errors="replace")
        modified = _apply_diff(original, r)
        for baseline in ("C", "D"):
            prompt = build_prompt(baseline, original, modified, r["artifact_path"])
            key = cache_key(client.provider, client.model, prompt)
            cpath = CACHE / f"{key}.json"
            if cpath.exists():
                cached = json.loads(cpath.read_text())
                text, err = cached.get("response"), cached.get("error") or ""
            elif quota_note:
                text, err = None, "NOT_RUN: no cached answer"
            elif client.available:
                try:
                    text, err = client.complete(prompt)
                except QuotaExhausted as exc:
                    quota_note = f"provider quota exhausted ({exc})"
                    text, err = None, "NOT_RUN: no cached answer"
                n_called += 1
                # Cache answers and permanent request errors (4xx other than 429, e.g.
                # 413 request larger than the per-minute token limit), so that a
                # re-run without a key re-scores exactly the same records.
                # Transient failures are not cached and are retried by a later run.
                permanent = text is None and bool(re.match(r"HTTP 4(?!29)\d\d", err))
                if text is not None or permanent:
                    cpath.write_text(json.dumps({"provider": client.provider, "model": client.model,
                                                 "prompt_version": PROMPT_VERSION,
                                                 "decoding": status["decoding"], "prompt": prompt,
                                                 "response": text, "error": err}, indent=1))
            else:
                text, err = None, "NOT_RUN: no cached answer"
            if text is None:
                st, flag, conf, reason = ("NOT_RUN" if err.startswith("NOT_RUN") else "ERROR"), None, None, err
            else:
                flag, conf, reason = parse_answer(text)
                st = "OK" if flag is not None else "INVALID_OUTPUT"
            out.append({"mutation_id": r["mutation_id"], "baseline": f"llm_{baseline}", "status": st,
                        "flagged": flag, "confidence": conf, "reason": reason, "cache_key": key,
                        "order_index": i})
        if client.available and (i + 1) % 25 == 0:
            print(f"[{time.strftime('%H:%M:%S')}] {i + 1}/{len(population)} mutants, "
                  f"{n_called} calls, {time.time() - started:.0f}s", flush=True)
    RAW.mkdir(parents=True, exist_ok=True)
    with open(RECORDS, "w") as fh:
        for o in sorted(out, key=lambda x: (x["mutation_id"], x["baseline"])):
            fh.write(json.dumps(o, sort_keys=True) + "\n")
    counts: dict[str, dict[str, int]] = {}
    for o in out:
        counts.setdefault(o["baseline"], {}).setdefault(o["status"], 0)
        counts[o["baseline"]][o["status"]] += 1
    status["status_counts"] = counts
    ok_both = {o["mutation_id"] for o in out if o["status"] == "OK" and o["baseline"] == "llm_C"} & \
              {o["mutation_id"] for o in out if o["status"] == "OK" and o["baseline"] == "llm_D"}
    status["n_scored_both"] = len(ok_both)
    if all(o["status"] == "NOT_RUN" for o in out):
        status["overall"] = "NOT_RUN"
    elif all(o["status"] == "OK" for o in out):
        status["overall"] = "RUN"
    else:
        status["overall"] = "PARTIAL"
    with open(STATUS, "w") as fh:
        json.dump(status, fh, indent=2, sort_keys=True)
    if n_called or not RUN_LOG.exists():
        # Only a run that queried the provider replaces the run log.
        with open(RUN_LOG, "w") as fh:
            json.dump({"finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                       "api_key_present": client.available, "api_calls_made": n_called,
                       "seconds": round(time.time() - started), "quota_note": quota_note,
                       "errors": sorted({o["reason"] for o in out if o["status"] == "ERROR"})},
                      fh, indent=2, sort_keys=True)
    return status


def _apply_diff(original: str, record: dict) -> str:
    """Re-create the mutant text deterministically and check it against the record's hash."""
    from relic_eval.mutate import generate
    idx = int(record["mutation_id"].rsplit("/", 1)[1])
    op = record["mutation_type"]
    mutants = [m for m in generate(original) if m.operator == op]
    text = mutants[idx].text
    assert text is not None
    if record.get("mutant_sha256"):
        assert hashlib.sha256(text.encode()).hexdigest()[:16] == record["mutant_sha256"], record["mutation_id"]
    return text


def load_llm_predictions() -> dict:
    """{'status': {...}, 'predictions': {mutation_id: {'llm_C': bool|None, 'llm_D': ...}}}"""
    status = json.loads(STATUS.read_text()) if STATUS.exists() else {"overall": "NOT_RUN",
                                                                     "reason": "llm_baselines not executed"}
    preds: dict[str, dict] = {}
    if RECORDS.exists():
        for line in open(RECORDS):
            o = json.loads(line)
            preds.setdefault(o["mutation_id"], {})[o["baseline"]] = o["flagged"] if o["status"] == "OK" else None
    return {"status": status, "predictions": preds}


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--subjects", default="")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args(argv)
    st = run([s for s in args.subjects.split(",") if s] or None, args.limit or None)
    print(json.dumps(st, indent=2))


if __name__ == "__main__":
    main()
