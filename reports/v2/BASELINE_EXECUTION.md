# RELIC V2 — Baseline execution report

Engineering Lead record. Everything below was executed in a **fresh clone** of
`https://github.com/ManasSakthivel/RELIC`; no other local copy was read or used.
Machine-readable companion: [`BASELINE_METRICS.json`](BASELINE_METRICS.json).

## 1. Repository state

| Item | Value |
|---|---|
| Baseline commit | `aee230921bc929eb28ff82edf36919e4a823fa95` (`origin/main`, identical to `origin/relic/final-research-remediation`) |
| Tag present on remote | `v1.0.0` |
| Work branch | `research/relic-v2-development` (created from the baseline commit) |
| Working tree at baseline | clean |
| Python | 3.11.15, venv built from `requirements.lock` (`.venv` is git-ignored) |
| Platform | macOS arm64 |

## 2. Commands executed and actual results

| # | Command (from clone root, `PYTHONPATH=$PWD/src:$PWD`) | Result |
|---|---|---|
| 1 | `python -m pytest tests/ -q` | **391 passed**, 0 failed (≈4 s). Matches the README claim of 391. |
| 2 | `python -m relic_eval.check_consistency` | **passed** (metrics, tables, figures and doc blocks agree with raw records). |
| 3 | Full reproduction in a scratch export of the clean clone: `relic_eval.pipeline` → `relic_eval.llm_baselines --offline-if-no-key` → `relic_eval.pipeline --skip-benchmark` → `relic_eval.check_consistency` (= `make reproduce`) | completed in **347 s**; consistency check **passed**. |
| 4 | Hash comparison of every tracked file under `results/` (1277 files) before vs after reproduction | **1276 identical**; only `results/final/run_info.json` differs (timestamp/commit — by design). |
| 5 | Mutant regeneration (`relic_eval.mutate.generate`) vs committed `mutant_sha256` | 0 mismatches over all evaluable mutants; recomputed RELIC v1.1 predictions equal the committed predictions exactly. (This is now enforced on every run of `relic_eval.v2_eval`.) |

Not executed: the LLM baselines were **not re-queried** (no provider credentials
were used). Only the committed records and the 1225-file cache were analysed.

## 3. Existing benchmark outputs (committed, `results/final`)

Candidates 656 → **566 evaluable** (460 behaviour-changing, 106 behaviour-preserving),
26 `INVALID_MUTATION`, 64 `OUT_OF_SCOPE`.

| Population | Detector | TP | FP | FN | TN | F1 |
|---|---|---:|---:|---:|---:|---:|
| CardDemo (primary, n=315) | RELIC v1.0.0 (primary) | 216 | 0 | 38 | 61 | 0.919 |
| CardDemo | RELIC v1.1 (post-hoc fixes) | 245 | 0 | 9 | 61 | 0.982 |
| CardDemo | any-non-comment-text-change | 254 | 31 | 0 | 30 | 0.943 |
| Pooled (n=566) | RELIC v1.0.0 | 380 | 0 | 80 | 106 | 0.905 |
| Pooled | RELIC v1.1 | 417 | 0 | 43 | 106 | 0.951 |
| Pooled | any-non-comment-text-change | 460 | 41 | 0 | 65 | 0.957 |

Full table with SHA-256 of every key result file: `BASELINE_METRICS.json`.

## 4. Reproducibility status

* **Reproducible:** tests, consistency check, mutant generation, oracle labels,
  detector predictions, metrics, tables and figures regenerate byte-identically
  (except `run_info.json`).
* **Not reproducible offline / without credentials:** fresh LLM answers. The
  committed cache allows offline re-scoring of the stored answers only.
* **Caveat — "byte-identical":** holds for data files only; `run_info.json`
  always changes.
* **Caveat — "RELIC v1.0.0 as released":** this is `legacy_v1_0=True` code in the
  current source tree (comment cites commit `024a3f2`), not a checkout of the
  original release commit `db51c84`.

## 5. After the V2 work

* Full suite: **439 passed** (391 original + 48 new V2 tests); consistency check passes.
* All 1277 tracked `results/` files are **byte-identical** to the baseline hashes
  (V2 output lives only in the new `results/v2/`).
