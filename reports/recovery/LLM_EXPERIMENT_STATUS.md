# LLM experiment status (RELIC V2 recovery)

Scope: audit of the LLM baseline protocol, code, committed records and paper/README
wording, plus a credential check. No LLM was called. No output was generated or
substituted. The repo was not modified; git was not run. Only this file was written.

## 1. Bottom line

* **Credentials: NOT available.** `GROQ_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`
  and `NVIDIA_API_KEY` are all unset. The only matching variable name is
  `CLAUDE_CODE_MESSAGING_TOKEN`, which is not an LLM provider key for this code and was
  not used or printed.
* **No experiment was run.** Nothing was re-run, and no result was substituted.
* **The only LLM evidence is the committed run:** 383 of 566 mutants scored, produced by
  `nvidia` / `openai/gpt-oss-20b`. The code has no `nvidia` provider.
* **The LLM comparison is not essential to the paper's core claim and can be deferred,**
  but only if the paper's LLM statements are downgraded. The direction of the
  LLM-vs-RELIC difference is undetermined at full coverage (section 5).
* **A default no-key run would silently swap the model in the committed records** (section 2, row "Reproducibility hazard"). This is the most urgent fix.

## 2. Protocol and code assessment

File paths: `/Users/manassakthivel/Desktop/RELIC-RECOVERY/reports/v2/LLM_EVALUATION_PROTOCOL.md`,
`/Users/manassakthivel/Desktop/RELIC-RECOVERY/relic_eval/llm_baselines.py`.
The status file named in the request does not exist at `results/final/llm_status.json`;
the actual file is `results/final/raw/llm_status.json`.

| Item | Finding | Verdict |
|---|---|---|
| Model / provider | Code default: `groq` `openai/gpt-oss-120b`. `ENDPOINTS` and `KEY_VARS` have only groq, openai, anthropic. Committed records: `nvidia` / `openai/gpt-oss-20b` (1132 cache files). Groq 120b appears only in 93 orphan cache files (91 with answers, 2 cached HTTP 413). Paper/README say nvidia; the protocol doc says nvidia. | Unsound: the committed run cannot be reproduced by the code as written. `RELIC_LLM_PROVIDER=nvidia` skips all calls (`available` is False) and works only as cache re-scoring. |
| Model version pinning | `gpt-oss-20b` is not pinned to a provider snapshot or date. Code default `claude-sonnet-5-5` for anthropic is not verified here. | Weak. Freeze an exact served ID at pre-registration. |
| Prompt version | `source_diff_v4` in code and in all 1132 nvidia cache entries. The cache key recomputes from the stored prompt for the first 200 entries (200/200 match). | Sound. |
| Sampling | temperature 0, seed 42, one sample. Seed is only a hint on hosted APIs. | Single greedy sample; no variance estimate. |
| Output budget and reasoning | `max_tokens` 1024 for a reasoning model. Of 251 INVALID_OUTPUT records: 238 have an empty response; 13 have a non-empty response cut off mid-sentence or mid-JSON (no closing brace, e.g. `...,"reason":"Only a comment was added; all DD statements, step order`). Both patterns fit reasoning-budget exhaustion. `finish_reason` and reasoning-token usage are not stored, so this is inferred, not shown. The committed nvidia decoding record has no `reasoning_effort` at all, so the provider default applied. That is undocumented and a plausible contributor to the invalids. | Budget too small, and reasoning effort unpinned. Primary re-run: keep `source_diff_v4`, raise `max_tokens` to 4096, pin `reasoning_effort`, log `finish_reason`. |
| Coverage | All 566 EVALUABLE mutants attempted for C and D (1132 records). All 251 non-OK records are `INVALID_OUTPUT` (none are ERROR or NOT_RUN), and their cache entries have an empty error field, so the failures are not provider errors or quota. Scored coverage is 383/566 (67.7%). | Attempt coverage full. Scored coverage partial, for model-output reasons. |
| Invalid handling | Invalid outputs are excluded from scoring (`flagged` None). The unscored set is selection-biased: 89.6% positive vs 77.3% of scored cases (D-017). The bounds in the protocol are a useful correction. | Sound design, but paper text still attributes the gap to quota. |
| Repeated samples | 1 sample per prompt. The protocol asks for >= 3 at non-zero temperature. None exist. | Missing. |
| Blinding | Keyword search over all 1225 cache prompts for `operator`, `label`, `oracle`, `mutant`, `mutation`, `site`, `intent`: no hits. The only `category` hit is a JCL comment in the source. The prompt is blind to labels. It also states the benchmark's behaviour criteria (MSGCLASS and comments are "not behaviour"; abends count). That is a documented task specification, not label leakage, and it is needed for a fair comparison. | Blind to labels. Criteria are a disclosed design choice. |
| Retry policy | Code retries transport errors and 429/5xx up to 10 times with backoff, and does not retry invalid JSON. The protocol specifies up to 3 attempts including invalid JSON, with logging of each attempt. Only the final answer is cached. | Code and protocol disagree. Attempts not logged. |
| Cache | Cache keys are sha256(provider, model, prompt_version, prompt); decoding is not in the key. Permanent 4xx errors are cached. | Sound for audit; see the reproducibility hazard below. |
| Reproducibility hazard 1 (default run) | `run()` writes `llm_records.jsonl` and `llm_status.json` unconditionally. `make llm-baselines` (no `--offline-if-no-key`) with no key uses default provider groq and model `openai/gpt-oss-120b`. Its cache keys match the 93 orphan groq files, and those prompts are byte-identical to 93 of the 1132 nvidia prompts (checked). So about 91 records would come back OK from the groq 120b cache, 2 would be cached ERROR (HTTP 413), and about 1039 NOT_RUN. The committed records would be replaced by a mix of a different model's answers and NOT_RUN, and the status metadata would read groq/120b. This is a silent model swap. Read from code and checked against cache files; not executed. | Serious. Guard the write when no key is present, or require the offline flag. |
| Reproducibility hazard 2 (`--subjects`) | `rescore_committed` filters on `o.get("subject_system")`. `llm_records.jsonl` has no `subject_system` key (keys: baseline, cache_key, confidence, flagged, mutation_id, order_index, reason, status). Any `--subjects` value therefore drops every record and rewrites `llm_status.json` with empty counts and `overall` NOT_RUN. Read from code; not executed. | Serious. Join `subject_system` from `evaluation_records.jsonl` by `mutation_id`. |
| Paper/README wording | Paper line 29 and README line 102 say coverage was "limited by the provider quota" and the subset is "a random subsample". README 129-133 and the paper erratum say it is selection-biased. The "at least as accurate" claim (paper line 351) rests on the 383 subset. The generated block in `results/final/tables/` was intentionally not regenerated. | Contradictory. Needs a maintainer decision. |
| Pre-registration | `reports/recovery/PREREGISTRATION.md` contains no LLM entry. | The LLM analysis is not pre-registered. |
| Makefile | `reproduce` uses `--offline-if-no-key`, which is safe. The `llm-baselines` target does not. | Mismatch with the safe path. |
| Scope | SemBench (180 mutants) and the external set (824) have no LLM run and are outside the minimal protocol in section 4. | Stated. |

## 3. Problems, ranked

1. **Default no-key run silently swaps the model** in the committed records (hazard 1).
2. **`--subjects` run blanks the status file** (hazard 2).
3. **Unreproducible provider**: nvidia is not in code, so the committed run cannot be regenerated without editing code.
4. **Budget too small, reasoning effort unpinned**: 251/1132 (22.2%) invalid at 1024 tokens; 238 empty and 13 truncated.
5. **Selection bias**: 183 unscored, 89.6% positive. Scored F1 (0.985 / 0.967) is not a full-population result. Full-population bounds from the protocol doc (not recomputed here): llm_C 0.808 to 0.972; llm_D 0.847 to 0.954. RELIC v1.0.0 is 0.908 on the 383 set; V2 is 0.979 on the same set per the protocol doc (not recomputed here).
6. **Contradictory paper/README text** on quota and random subsample.
7. **One sample, one model, one prompt; no pre-registration.**

## 4. Recommended actions

Immediate (no credentials needed):
1. Guard the write in `run()`: with no provider key, exit without writing records or status unless `--offline-if-no-key` is given. Make `llm-baselines` use the offline guard by default.
2. Fix `rescore_committed` to join `subject_system` from `results/final/raw/evaluation_records.jsonl` by `mutation_id`.
3. Either add an nvidia endpoint and key entry, or document that the committed run is cache-only reproducible with `RELIC_LLM_PROVIDER=nvidia RELIC_LLM_MODEL=openai/gpt-oss-20b` (cache-key scheme verified).
4. Paper text: replace the quota and random-subsample sentences in `paper/paper.md` line 29 and `README.md` line 102 with the selection-bias statement, or regenerate `results/final/tables/` under a maintainer decision. Soften the LLM claims (paper.md lines 351-353 and 429; README 129) to: "On the 383-mutant selection-biased subset, LLM-only F1 0.985 and dependency+LLM F1 0.967, versus RELIC v1.0.0 0.908 and RELIC V2 0.979 (protocol doc, not recomputed). Over all 566 mutants, the LLM result is undetermined: F1 0.808 to 0.972 (LLM-only) depending on how invalid outputs are scored." Do not claim the LLM is "at least as accurate" as RELIC, nor that it is less accurate.
5. Record `finish_reason`, completion tokens and reasoning tokens for every future call.

If credentials are later provided, with the protocol pre-registered:
* **Primary arm (one variable changed):** frozen `source_diff_v4` prompt, unchanged. Raise `max_tokens` from 1024 to 4096. Pin `reasoning_effort` explicitly, with the value recorded. This tests the budget-exhaustion hypothesis directly.
* **Models:** (a) `openai/gpt-oss-120b` on Groq (the code default, with `reasoning_effort` pinned and logged), and (b) one frontier model. Pin an exact served ID and date at freeze time. The code default `claude-sonnet-5-5` is unverified here. Each model is a separate freeze file and a separate report line.
* **Secondary arm:** a revised prompt, `source_diff_v5`, that removes the behaviour criteria or moves them to a neutral section. Report it separately. It does not replace the primary arm.
* **Decoding:** temperature 0 for the greedy primary. Record `finish_reason`, completion and reasoning tokens for every call.
* **Samples:** greedy primary, plus 2 samples at temperature 0.7 with recorded seeds (n = 3) for variance. Primary metric = greedy.
* **Population (minimal run):** all 566 EVALUABLE mutants of the old benchmark, both C and D. SemBench (180) and the external set (824) are out of scope here. If included, add 1004 x 2 x 3 = 6,024 calls per model.
* **Budget (calls):** the minimal run is 566 x 2 x 3 = 3,396 calls per model before retries. Two models is 6,792 calls. Retry cap is 3 attempts per prompt, so the worst case is 20,376 calls for two models. Run a 20-mutant pilot first (about 120 calls per model) to measure tokens per call. No cost estimate is possible here because prices and token counts are unavailable.
* **Primary analysis (one only):** bootstrap 95% CI on the paired difference ΔF1 = F1(RELIC V2) minus F1(LLM), clustered by base program, on the identical 566 cases. The invalid outputs are scored as "not flagged" for the primary bound and as "flagged" for the sensitivity bound.
* **Pre-registered equivalence margin δ = 0.03 F1.** Outcomes, judged under both invalid bounds:
  * "Equivalent": the CI lies entirely within (-δ, +δ).
  * "RELIC V2 superior": the CI lies entirely above +δ.
  * "LLM superior": the CI lies entirely below -δ.
  * "Inconclusive": anything else.
  * If the two bounds disagree, report "inconclusive".
* **Validity gate:** if the greedy invalid rate exceeds 5% after the budget change, report that model as inconclusive and do not score it as a primary result.
* **Secondary (not decisive):** McNemar exact tests, with Holm correction across 2 models x 2 baselines x 3 comparators (RELIC V2, `normalized_text_B`, `textdiff_ignore_job_parameters`).
* **Blinding check:** keyword scan of every prompt before the run, recorded in the freeze file.
* **Freeze:** `LLM_FREEZE.json` with SHA-256 of the prompt template, model IDs, decoding, retry rule and population, committed before the first call.

## 5. Deferral decision

An LLM baseline is **not essential** to the paper's central claim. The paper's contribution is the deterministic detector, evaluated against the oracle and against the deterministic baselines A, B, E and the normalised-text reference. The LLM comparison is a secondary, selection-biased, single-model result.

Deferral is acceptable only if the paper:
* downgrades the LLM statements (action 4), giving both the RELIC V2 figure and the v1.0.0 figure;
* says explicitly that the LLM-vs-RELIC direction is undetermined at full coverage;
* states that no LLM result is pre-registered or fully covered.

Keeping "LLM at least as accurate" without a full-population re-run is not acceptable.

Risk: reviewers are likely to expect an LLM comparison, and a deferred one will invite that question. Deferral is a judgement for the maintainers. If a comparison is wanted for the submission, run the minimal protocol above, not the current committed run.

## 6. Tests and checks run

* Read: `reports/v2/LLM_EVALUATION_PROTOCOL.md`, `relic_eval/llm_baselines.py`, `results/final/raw/llm_status.json`, `results/final/raw/llm_last_run.json`, `results/final/raw/llm_records.jsonl` (via script), and the paper and README LLM passages. `reports/recovery/PREREGISTRATION.md` and the Makefile LLM targets were also read.
* Credential check: variable names only, via `env | grep -E 'API_KEY|_TOKEN' | cut -d= -f1`, plus `printenv` presence checks for four named keys. No values were printed.
* Read-only analysis scripts:
  * record and cache counts;
  * INVALID breakdown (empty vs truncated, and the empty error field on all 251 entries);
  * orphan-cache count and orphan-prompt overlap with the 1132 referenced nvidia prompts (93 of 93 identical);
  * prompt keyword scan over 1225 prompts;
  * cache-key recomputation (200 of 1225 sampled, 200 match);
  * `subject_system` key check on `llm_records.jsonl` (absent) and `evaluation_records.jsonl` (present);
  * grep for `nvidia` in code (none);
  * Makefile target check; preregistration grep (no LLM entry).
* Not run: any `relic_eval.llm_baselines` invocation. Both hazards are from code reading and cache checks only.

## 7. Remaining uncertainty

* The cause of the 251 invalid outputs (reasoning-budget exhaustion, plus unpinned reasoning effort) is inferred from the text. `finish_reason` and usage were not stored.
* The protocol's bounds (0.808 / 0.972 and 0.847 / 0.954) and the V2 figure 0.979 on the 383 set were not recomputed here.
* The nvidia endpoint and its model availability could not be checked (no credentials, no network use).
* The keyword blinding check cannot detect semantic leakage, for example oracle-like phrasing in JCL comments.
* Whether the committed nvidia answers would reproduce byte-for-byte on re-query is unknown.
* Both reproducibility hazards are from code reading and cache checks. They have not been demonstrated by execution.
