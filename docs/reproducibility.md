# Reproducibility

## What to install
- Python ≥ 3.11 on macOS or Linux (tested: macOS 26 / arm64, CPython 3.11.15).
- `make setup` creates `.venv` and installs `requirements.lock` (pinned; generated
  from `requirements.in` in a fresh environment). Alternative:
  `uv venv --python 3.11 && uv pip install -r requirements.lock`.
- Not needed: z/OS, GnuCOBOL, Docker, or API keys for the basic workflow.
  `make reproduce` without an API key re-scores the committed 383-mutation LLM
  results from `results/final/raw/llm_records.jsonl` without issuing any API
  calls (`--offline-if-no-key`). The committed request/response cache
  (`results/final/raw/llm_cache/`, 1 225 files) also allows independent
  verification of every cached answer. Re-querying the model to extend coverage
  requires an API key for the configured provider (see `relic_eval/llm_baselines.py`
  for expected environment variables); pass keys through the environment only,
  never in a file.
- If no Python ≥ 3.11 is on PATH, `make setup` uses one managed by `uv`, or set
  `PY_BOOT=/path/to/python3.11`.

## What to run
| Command | What it does | API key required | Time |
|---|---|---|---|
| `make test` | full test suite (RELIC unit/integration, oracle semantics, evaluation, regression, results integrity) | no | seconds |
| `make reproduce` | generates all mutants, labels them with the oracle, runs every detector, writes raw records, manifest, metrics, tables, LaTeX tables, figures and generated doc blocks; LLM step re-scores from committed records (offline, no API calls) | no | 5–25 min |
| `make metrics` | recomputes metrics, tables, figures and doc blocks from the committed raw records only | no | ~1 s |
| `make check` | fails if any reported number disagrees with the raw records, or active docs contain withdrawn numbers | no | ~2 s |
| `make llm-baselines` | queries the model for every EVALUABLE mutant not yet in the cache (seeded random order; stops cleanly when the provider quota is exhausted) and recomputes metrics | **yes** | API-bound (hours on a free-tier key) |
| `make reproduce-legacy` | re-runs the pre-remediation scripts in v1.0.0 mode (provenance only; reproduces the legacy numbers exactly, apart from timestamps/UUIDs) | no | ~10 s |

### make reproduce vs make llm-baselines

`make reproduce` calls the LLM step with `--offline-if-no-key`.  Without an API
key it reads `results/final/raw/llm_records.jsonl` (committed, 1 132 lines, 566
mutants × 2 baselines C/D) and recomputes `llm_status.json` — the JSONL file is
not overwritten.  This preserves the committed 383-mutation results and allows a
full offline re-run.

`make llm-baselines` (no `--offline-if-no-key`) always calls `run()`, which
rewrites `llm_records.jsonl` with results for all EVALUABLE mutants.  Mutants
not in the cache and not reachable (no key, or quota exhausted) are written as
`NOT_RUN`.  Run this only with a live API key; once quota is exhausted the run
stops cleanly and the partial results are saved.

## Where outputs appear
- `results/final/raw/evaluation_records.jsonl` — one record per candidate mutant:
  diff, oracle verdict and evidence, every prediction.
- `results/final/evaluation_manifest.csv` — one row per candidate mutant
  (mutation_id, mutation_type, contract_type, subject_system, status, status_reason,
  expected_violation, oracle_result, relic_result, evaluable_for_metrics, …).
- `results/final/metrics.json` — every reported number.
- `results/final/contract_recovery.json` — RQ1 per-file results.
- `results/final/tables/*.md`, `paper/generated/*.tex`, `figures/final/*.svg`.
- `results/final/run_info.json` — timestamp, Python, platform, git commit.
- `results/legacy/` — accounting of the legacy run.

## How metrics are generated
`relic_eval/metrics.py` (formulas and consistency assertions) ←
`relic_eval/report.py` (populations, breakdowns, sensitivity analyses, rendering).
README, paper and docs contain metrics only inside
`<!-- BEGIN GENERATED:… -->` blocks, which `report.py` rewrites and
`check_consistency.py` verifies.

## Determinism

LLM answers are not deterministic across providers or model versions. The cache
makes the reported LLM results reproducible; a fresh query may give different
answers.

No randomness in mutant generation (exhaustive site enumeration), oracle or
detectors. The bootstrap uses a fixed seed (20261004). Raw records and
`metrics.json` contain no timestamps or random identifiers, so two runs produce
byte-identical files (verified during the remediation by running the pipeline
twice and comparing hashes).

## Known environment assumptions
- File reading uses `errors="replace"`; all subject files are ASCII.
- The pipeline imports with `PYTHONPATH=src:.` (set by the Makefile) or after
  `pip install -e .`.
