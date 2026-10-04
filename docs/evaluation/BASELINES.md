# Detectors and Baselines

All detectors implement `predict(original_text, mutated_text, path)` and see
nothing else (`relic_eval/detectors.py`, `relic_eval/llm_baselines.py`).

| Name | What it does | Parser | Notes |
|---|---|---|---|
| `relic_v1_0` | RELIC exactly as released (commit `024a3f2`): parse → extract contracts → build BCG for both texts → `RiskDetector.detect` | v1.0 (`legacy_v1_0=True`) | **primary, blind** result. The legacy switch reproduces v1.0.0 contract counts exactly on CardDemo (regression test). |
| `relic_v1_1` | RELIC with post-hoc spec-conformance fixes: IBM continuation rule, columns 73–80 ignored, balanced COND capture, COND without step name binds all previous steps, diff compares COND threshold/operator and flags *weakened* guards | v1.1 (default) | fixes were designed after the defects were found during the audit and after first benchmark runs — **not a blind result** |
| `static_bcg_E` | Baseline E: static BCG diff, broken contracts only (no "modified" branch) | v1.0 | |
| `structural_A` | Baseline A: structural dependency graph (CALLS, PRODUCES, CONSUMES, MUST_PRECEDE, …) edge removal | v1.0 | |
| `complexity_B` | Baseline B: weighted complexity score of the mutated file > 0.5 | v1.0 | change-agnostic by design; see corrections |
| `textdiff` | flags any difference outside comment statements and columns 73–80 | none | new trivial reference that calibrates benchmark difficulty |
| `llm_C` | Baseline C: LLM sees ORIGINAL and MODIFIED JCL | — | Groq `openai/gpt-oss-120b`; see protocol below |
| `llm_D` | Baseline D: as C plus an automatically extracted dependency summary of both versions | IBM-conformant (v1.1) | same model; see protocol below |

## Corrections to legacy baselines

* **Complexity (B).** The legacy harness passed `mutation.affected_entity_ids`
  (the answer key) and min-max normalised within a one-file IR, where every
  normalised metric is 0, so the baseline could never fire (legacy F1 = 0.000 by
  construction). It now gets a neutral record and normalises the mutated file
  against its subject corpus. Weights and the 0.5 threshold are unchanged (they were
  pre-specified).
* **Baseline E vs RELIC.** In the legacy harness RELIC beat E only because the
  harness lowered contract confidence by hand. With real source changes static
  confidences are always 1.0, so `relic_v1_0` and `static_bcg_E` make identical
  decisions; the results confirm this.

## LLM baselines — audit of the legacy numbers

| | Legacy C (LLM-only) | Legacy D (dep+LLM) |
|---|---|---|
| Model | Groq `llama-3.3-70b-versatile`, temperature 0, seed 42, max_tokens 400 | same |
| Prompt input | file name, operator name, one-line change description, contract count — **no JCL source, no diff** | as C + generic dependency text |
| Label leakage | operator names such as `REORDER_INDEPENDENT_STEPS` vs `REORDER_JOBS` reveal the label | same |
| Calls | 248 | 248 |
| Failed (HTTP 429) | 245 | 241 |
| Failed calls scored as | "no regression" (FN on positives, TN on negatives) | same |
| Successful calls correct | 3 / 3 | 7 / 7 |
| Reported F1 (withdrawn) | 0.0377 | 0.1091 |

The reported F1 values measure rate limiting, not model capability, and are
**withdrawn**. The raw records remain in `results/rq2/`.

## LLM baselines — corrected protocol

`python -m relic_eval.llm_baselines` (Makefile: `make llm-baselines`; needs `GROQ_API_KEY`).

| | Baseline C (LLM-only) | Baseline D (dependency + LLM) |
|---|---|---|
| Model | Groq `openai/gpt-oss-120b` (the legacy model `llama-3.3-70b-versatile` is no longer served) | same |
| Decoding | temperature 0, seed 42, `reasoning_effort` low, max_tokens 1024 (reasoning tokens count against it), one sample | same |
| Prompt (`source_diff_v4`) | full ORIGINAL and MODIFIED JCL; a definition of behaviour that matches the oracle's observables (which steps run, incl. after non-zero RC or abend; order; dataset create/read/write/delete; final dataset state; comments, formatting and MSGCLASS are not behaviour); JSON answer `{behavior_changed, confidence, reason}` | as C, plus a dependency summary of both versions (steps, programs, COND, datasets created/used, step order) extracted by RELIC's parser in IBM-conformant mode |
| Not in the prompt | operator name, mutation site, intent, label, file path, oracle output | same |
| Population | all EVALUABLE mutants of the three subjects, in a fixed seeded random order (seed 20261004); C and D for the same mutant are requested back to back | same |
| Failures | per-minute rate limits and 5xx are retried (honouring `retry-after`); a request larger than the account's per-minute token limit (HTTP 413) and answers that do not parse are recorded as `ERROR` / `INVALID_OUTPUT`; if the provider's daily quota is exhausted the run stops and the rest is `NOT_RUN`. **None of these is scored.** | same |
| Scoring | `flagged = behavior_changed`; compared with the oracle label | same |
| Audit | every request and response is cached in `results/final/raw/llm_cache/`; `raw/llm_records.jsonl` has one record per (mutant, baseline); `raw/llm_status.json` has coverage | same |

**Comparison population.** RELIC and the other detectors are scored on every
EVALUABLE mutant, but the LLM baselines only where they answered. To keep the
comparison fair, the LLM table in [RESULTS.md](RESULTS.md) scores *all* detectors
(C, D, RELIC v1.0.0, RELIC v1.1, Baseline A, reference) on the **common
population**: the mutants for which both C and D returned a valid answer. Because
mutants are processed in a seeded random order, an incomplete run is a uniform
random subsample of the population (apart from requests too large for the
account's per-minute token limit, which are systematically the largest files —
reported as `ERROR`).

**Known caveats.** The prompt's definition of behaviour tells the model that
MSGCLASS and comment changes are not behaviour; this is the same specification the
oracle implements, but it makes the two harmless operators easy for the model. The
inserted comment (`//* MIGRATION REVIEW: STEP ORDER VERIFIED`) is natural-language
text the model reads. Model choice, prompt and decoding were fixed before any LLM
answer was seen, except that `max_tokens` was raised from 300 and
`reasoning_effort` set after a single smoke-test call showed that the reasoning
model needs the larger budget.

Results and coverage: [RESULTS.md](RESULTS.md#llm-baselines-common-population)
(generated from `results/final/metrics.json`).
