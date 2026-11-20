# LLM baseline: inconsistency resolution and a fair re-evaluation protocol

Status: **protocol only. The LLM baselines were NOT re-run in V2** (no API credentials
in this environment). No new LLM number is reported anywhere in V2.

## 1. What the committed records actually show (resolution of the model/provider inconsistency)

Source: `results/final/raw/llm_status.json`, `results/final/metrics.json` (`llm.status`),
`results/final/raw/llm_records.jsonl` (all read-only, unchanged).

| Fact | Value |
|---|---|
| Provider / model that produced the committed records | nvidia, `openai/gpt-oss-20b` |
| Prompt version | `source_diff_v4` |
| Decoding | temperature 0, seed 42, `max_tokens` 1024, one sample per prompt, reasoning effort n/a |
| Population attempted | all 566 EVALUABLE mutants (not a random subsample) |
| llm_C (original + modified JCL) | 418 OK, 148 `INVALID_OUTPUT` |
| llm_D (same + dependency summary) | 463 OK, 103 `INVALID_OUTPUT` |
| Scored on both ("common set") | 383 of 566 (67.7%) |
| Unscored 183 | 89.6% positive vs 77.3% for the scored ones (selection bias; D-017) |
| Overall status | `PARTIAL` |

**Resolution.** The Groq `openai/gpt-oss-120b` statements in the original hand-written
`paper/paper.md` (abstract, section on baselines, limitations, conclusion) and the
phrase "quota-limited random subsample" were inconsistent with the records. Groq
`gpt-oss-120b` appears only as 93 orphaned cache files not referenced by any record
(`docs/limitations.md`) and in the legacy `results/rq2` files. The V2 documentation fix
changed the four hand-written passages of `paper/paper.md` to the model and subset actually
used. A fifth instance, the generated sentence "a random subsample" produced by
`relic_eval/report.py` (appears in `paper/paper.md` and `README.md` inside
`GENERATED:results-summary`), is **not** corrected: changing the template would rewrite
`results/final/tables/` under the no-overwrite rule. An erratum next to the block states
the accurate description. **Open item:** a maintainer decision to regenerate.

The legacy numbers (Groq `llama-3.3-70b-versatile`, F1 0.0377 / 0.1091) remain withdrawn
(failed HTTP 429 calls scored as negatives); see `docs/evaluation/BASELINES.md`.

## 2. What the existing comparison supports (and does not)

* Supports: on the **selection-biased** 383-mutant common set, `gpt-oss-20b` (one prompt,
  one model) had higher F1 than RELIC v1.0.0 (llm_C 0.985, llm_D 0.967, v1.0 0.908; v1.1 0.958; V2 0.979 on the same set per `DEFECT_REGISTER.md` D-017).
* Bounds over the full 566 if invalid output is treated as "not flagged" / "flagged":
  llm_C F1 0.808 / 0.972, llm_D 0.847 / 0.954. These bounds are not a substitute for a re-run.
* Does **not** support: any statement that an LLM generalises, that RELIC is inferior to
  LLMs in general, or the reverse. One model, one prompt, no repeats, partial coverage.
* On JCL-SemBench and the external set no LLM was run at all (**[PENDING EXPERIMENT]**).

## 3. Fair re-evaluation protocol (to be executed when credentials exist)

1. **Freeze before running:** model id and provider, prompt text hash, decoding parameters,
   output schema, retry rule, population, order seed. Record in a `LLM_FREEZE.json`
   with a SHA-256, committed before the first call.
2. **One documented model per report line.** A different provider/model is a separate run
   with its own freeze file; never merge records across models. Prefer at least two
   models (one open-weight, one frontier) and report each separately.
3. **Full-population reporting.** Attempt every EVALUABLE mutant (old benchmark: 566;
   SemBench: 180; external: 824). The primary denominator is the whole population.
4. **Invalid, missing and refused outputs stay visible.** Report counts per status
   (`OK`, `INVALID_OUTPUT`, `HTTP_ERROR`, `RATE_LIMITED`, `REFUSED`). Report two bounds
   (invalid → "not flagged" and invalid → "flagged") next to every headline metric, plus
   the metric on the scored subset **with** the positive-rate of the unscored cases.
   Never score an error as a negative prediction without that bound.
5. **Retry policy (fixed in advance):** at most 3 attempts per prompt; retry only on
   transport errors, HTTP 429/5xx (honouring `retry-after`) and unparseable JSON; same
   prompt, same seed; raise `max_tokens` once (e.g. 1024 → 4096) for reasoning models if
   the failure is truncation. Log every attempt. No cherry-picking among attempts.
6. **Blinding:** the prompt contains no operator name, category, label, site or oracle
   verdict (as in `source_diff_v4`). Input = original and modified text only.
7. **Uncertainty:** ≥ 3 independent samples per prompt at non-zero temperature for the
   variance estimate in addition to the temperature-0 run; clustered bootstrap by base
   program (SemBench has only 16 clusters; say so).
8. **Comparisons:** paired exact McNemar with Holm correction over the comparison family,
   against RELIC V2, `normalized_text_B` and `textdiff_ignore_job_parameters`, on the
   identical case set; cases where the LLM is invalid enter as a separate row.
9. **Data contamination caveat:** SemBench cases are derived from public IBM sample JCL;
   state that pre-training exposure cannot be excluded.
10. **Cost/credential hygiene:** keys come from the environment only; never written to
    records, caches or logs. Scan the diff for secrets before committing.

## 4. Status

| Item | Status |
|---|---|
| Model/provider inconsistency in hand-written docs | Fixed (paper.md ×4); README already correct |
| Generated "random subsample" sentence | Documented via erratum; template change deferred (would touch `results/final/tables`) |
| Fair re-run on old benchmark | **[PENDING EXPERIMENT]** (credentials required) |
| LLM on SemBench / external | **[PENDING EXPERIMENT]** |
