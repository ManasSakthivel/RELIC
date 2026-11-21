"""LLM baseline on JCL-SemBench v1.1 pairs via the Groq OpenAI-compatible API.

Model: openai/gpt-oss-120b. Temperature 0. One request per pair, both files shown.
The model is asked for a behaviour verdict. This is a baseline detector, not a ground-truth source.
Key: read from env GROQ_API_KEY only; never written to disk or logged.
Outputs: results/final/llm/groq_gpt_oss_120b_raw.jsonl (every response), and metrics JSON.
"""
import json, os, re, sys, time, threading, urllib.request, urllib.error
MODEL = "openai/gpt-oss-120b"
KEY = os.environ["GROQ_API_KEY"]
PROMPT = (
    "You are checking a z/OS JCL change. Below are an ORIGINAL and a TRANSFORMED job stream. "
    "Decide whether the transformed job changes observable behaviour: which steps run, their order or "
    "conditions (COND/IF), dataset inputs/outputs or DISP, or return codes. Comment and whitespace edits "
    "do not change behaviour. Answer with JSON only: {\"verdict\": \"CHANGING\" or \"PRESERVING\", \"reason\": \"<one sentence>\"}.\n\n"
    "=== ORIGINAL ===\n{orig}\n=== TRANSFORMED ===\n{trans}\n"
)
cases = [json.loads(l) for l in open("benchmarks/sembench/cases.jsonl")]
os.makedirs("results/final/llm", exist_ok=True)
raw_path = "results/final/llm/groq_gpt_oss_120b_raw.jsonl"
done = {}
if os.path.exists(raw_path):
    done = {json.loads(l)["id"]: json.loads(l) for l in open(raw_path)}

MIN_INTERVAL = float(os.environ.get("GROQ_MIN_INTERVAL_S", "25"))  # keeps under 8,000 tokens/min
_last = [0.0]
_rate_lock = threading.Lock()
def ask(msg):
    body = json.dumps({"model": MODEL, "temperature": 0, "max_completion_tokens": 4000,
                       "messages": [{"role": "user", "content": msg}]}).encode()
    req = urllib.request.Request("https://api.groq.com/openai/v1/chat/completions", data=body,
        headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json",
                 "User-Agent": "research-benchmark-client/1.0"})
    for attempt in range(8):
        with _rate_lock:
            wait = _last[0] + MIN_INTERVAL - time.time()
            if wait > 0: time.sleep(wait)
            _last[0] = time.time()
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                content = json.load(r)["choices"][0]["message"]["content"] or ""
            if content.strip():
                return content
            time.sleep(2)
            continue
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503) and attempt < 7:
                time.sleep(min(60, 5 * (attempt + 1))); continue
            raise
    return ""  # recorded as unparsed, never guessed

import threading
from concurrent.futures import ThreadPoolExecutor
lock = threading.Lock()
def work(c):
    d = f"benchmarks/sembench/cases/{c['id']}"
    orig = open(f"{d}/original.jcl", encoding="utf-8", errors="replace").read()
    trans = open(f"{d}/transformed.jcl", encoding="utf-8", errors="replace").read()
    t0 = time.time()
    try:
        text = ask(PROMPT.replace("{orig}", orig).replace("{trans}", trans))
    except Exception as e:  # not written, so a resume retries this pair
        print("FAILED", c["id"], type(e).__name__, flush=True)
        return
    latency = round(time.time() - t0, 2)
    m = re.search(r"\{.*\}", text, re.S)
    verdict, reason = None, text[:200]
    if m:
        try:
            j = json.loads(m.group(0)); verdict = j.get("verdict"); reason = j.get("reason", "")
        except json.JSONDecodeError:
            pass
    rec = {"id": c["id"], "verdict": verdict, "reason": reason, "raw": text[:800], "latency_s": latency}
    with lock:
        with open(raw_path, "a") as f:
            f.write(json.dumps(rec) + "\n")
    print(c["id"], verdict, flush=True)
todo = [c for c in cases if c["id"] not in done]
with ThreadPoolExecutor(max_workers=1) as ex:
    list(ex.map(work, todo))
