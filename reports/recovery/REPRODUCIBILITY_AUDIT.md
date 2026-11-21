# Reproducibility audit (RELIC V2 publication recovery)

Audit date: 2026-11-20. Python 3.11.16 (uv-managed), macOS 26.7 arm64, no Linux run.

Commits tested:
- `828bc15` (local branch `research/relic-v2-publication-recovery`): the clean clone and all local reruns.
- `3352bf4` (pushed `origin/research/relic-v2-final-sprint`): a fresh GitHub clone (outsider path).
- Branch HEAD moved to `c51c1bc` during the audit. Commits `6595dbf`, `3dafc90`, `c51c1bc` change only `paper/`, `reports/` and `results/recovery/`. They touch no code, no build file, and no committed `results/` directory that this audit compares, so the results below apply to HEAD.

Nothing tracked was modified by this audit. Reruns wrote to new directories under `results/recovery/` or to clones under the session scratchpad. Logs are in `results/recovery/logs/`; the byte comparison is in `results/recovery/comparison_summary.txt`.

## 1. Verdict

| Claim | Status |
|---|---|
| Test suite: 500 passed | **Reproduced**: 3.11.16 original tree, clean clone and GitHub clone; 3.13 fresh venv also 500 passed (not byte-compared) |
| `check_consistency` passes | **Reproduced** (original, clean clone, GitHub clone) |
| SemBench manifest (360 entries) | **Reproduced**, 360/360 OK |
| `benchmarks/sembench/validate.py` (180 pairs) | **Reproduced**: 151 validated, 28 oracle disagreements, 1 abstention |
| `SUBJECT_FREEZE.json`: code, harness, development-corpus, per-file and licence hashes | **Reproduced**: 53/53 code files; harness hash; dev corpus 718 raw / 365 normalised with identical set hash; 398 repo files + 11 licence files after clone |
| 11 external repos cloned at frozen SHAs | **Reproduced**: all 11 HEADs equal `pinned_sha` |
| SemBench evaluation | **Reproduced byte-for-byte** (metrics, predictions, paired tests), from the original tree and the GitHub clone |
| External 11-repository rerun | **Reproduced byte-for-byte** (predictions, metrics, exclusions), from the frozen clones |
| Full `make reproduce` | **Reproduced** from a clean clone of `828bc15` (5 min 06 s) and from the GitHub clone of `3352bf4` (exit 0). Only metadata files differ |
| `make v2-eval`, `make reproduce-legacy` | **Reproduced** in the clean clone (timestamp, commit, platform, UUID fields only) |
| Docker build / `docker compose` | **Not reproduced**. Static finding: the Dockerfile is expected to fail as written. Not built (daemon not running) |
| LLM baselines C/D re-query | **Not run** (no API key; offline re-scoring only) |

Bottom line: the Python evaluation reproduces from the pushed branch and from a clean local clone on this machine. Docker does not, and several version and documentation statements are stale.

## 2. Commands run

| Command | Where | Result |
|---|---|---|
| `make test` (`pytest tests/ -q`) | original tree, 3.11.16 | 500 passed, 17.8 s |
| same | fresh 3.13 venv from `requirements.lock` | 500 passed, 629,460 warnings (not investigated) |
| `make check` (`check_consistency`) | original tree | passed |
| `python benchmarks/sembench/validate.py` | original tree | `[SUCCESS] JCL-SemBench verification passed completely.` |
| `relic_eval.sembench_eval --out results/recovery/sembench_rerun` | original tree | exit 0, about 2.5 s |
| `relic_eval.external_eval run --clones <scratch>/ext/rerun2 --out results/recovery/external_rerun --workers 4` | original tree | exit 0, about 5 min |
| `make setup PY_BOOT=<uv 3.11>`, `make test`, `make check`, `make reproduce` | clean clone of `828bc15` | all exit 0; 500 passed; reproduce 5 min 06 s |
| `make v2-eval`, `make reproduce-legacy` | clean clone of `828bc15` | exit 0 (about 4 s and under 1 s) |
| same four steps plus SemBench rerun | fresh GitHub clone of `3352bf4` | all exit 0; SemBench identical; reproduce only metadata changed |

Not run: `make llm-baselines` (needs an API key and rewrites `llm_records.jsonl`), Docker targets (daemon not reachable), `results/sembench/noop_sensitivity.py`, `make figures-legacy`.

## 3. Hash verification

- `benchmarks/sembench/MANIFEST.sha256`: `shasum -a 256 -c` gives 360 OK, 0 failures.
- `results/external/SUBJECT_FREEZE.json`:
  - `frozen_code_sha256` (53 files): all match the working tree.
  - `harness_sha256` (`relic_eval/external_eval.py`): matches.
  - `development_corpus` (`datasets/`, computed by `external_eval.dev_hashes()`): 718 raw and 365 normalised hashes, set hash `4fefe23d…` identical to the freeze.
  - Clones of the 11 repos: HEAD equals each `pinned_sha`. Per-file SHA-256 for all 398 `.jcl` files in the freeze (182 effectiveness, 216 robustness) and all 11 licence files match: 409 OK, 0 mismatch, 0 missing.
  - The external `run_info.json` records `frozen_code_unchanged_since_freeze: true`.

## 4. Rerun results

### 4.1 SemBench
- `results/recovery/sembench_rerun/` vs `results/sembench/`: `metrics.json`, `predictions.jsonl`, `paired_tests.json` byte-identical. The same holds for the GitHub clone's rerun.
- `run_info.json` differs in timestamp, `git_commit`, platform patch level and Python patch level.

### 4.2 External (11 repositories)
- `results/recovery/external_rerun/` vs `results/external/`: `predictions.jsonl` (1,005 lines), `metrics.json`, `exclusions.json` byte-identical.
- `run_info.json` differs in timestamp, `relic_commit_at_run`, platform and Python patch level.
- Timing: about 5 minutes for the run after the clones were in place, plus about 2 minutes for 11 shallow fetches by SHA. Within the 20-minute budget.

### 4.3 Clean clone of `828bc15`
A `git clone --no-hardlinks` of the committed repository, then the documented commands. No file from the original working tree was copied in.
- `make setup PY_BOOT=<uv CPython 3.11>`: exit 0, 8 s. The pip/uv caches were warm, so a fresh machine will be slower.
- `make test`: 500 passed. `make check`: passed.
- `make reproduce`: exit 0, 5 min 06 s, LLM step offline. `git status` shows **one** modified tracked file, `results/final/run_info.json` (timestamp, platform, Python patch, git_commit). Every other tracked output regenerated byte-identically.
- `make v2-eval`: only `results/v2/v2_run_info.json` changed (timestamp, git_commit, platform, Python patch).
- `make reproduce-legacy`: `results/rq1`, `rq2`, `rq3` JSON changed only in `run_timestamp`. `results/rq2/negative_mutations.csv` changed only in its UUID column (column 10; 145 rows checked, 0 differences elsewhere). The UUIDs come from `src/legacy_contract/mutations/negative_mutations.py` and `engine.py`, which generate them.

### 4.4 Outsider path: fresh GitHub clone of `origin/research/relic-v2-final-sprint` at `3352bf4`
- `make setup`, `make test` (500 passed), `make check`: pass.
- SemBench rerun: identical to `results/sembench/`.
- `make reproduce`: exit 0; only `results/final/run_info.json` changed.

This is the path an outside researcher would actually take, because `828bc15` is not on the remote. Its only difference from `3352bf4` is files under `reports/recovery/`.

## 5. Mismatches and stale statements

Ordered by how much they affect a reader trying to reproduce.

1. **Docker path does not work as written (static finding; not built).**
   - `Dockerfile` runs `poetry install`, but `pyproject.toml` has no `[tool.poetry]` section. Poetry 1.x does not read the PEP 621 `[project]` table. The build is expected to fail or install no project dependencies.
   - `COPY pyproject.toml poetry.lock* ./`: no `poetry.lock` exists, so the image never uses `requirements.lock` and gets unpinned ranges.
   - `docker-compose.yml`: the `api` service runs `legacy_contract.api.main`, which imports `fastapi`, `pydantic` and `uvicorn`. Those are only in the `api` extra, not in `requirements.lock`, and no test imports the API. `db` (neo4j 5.13) is not referenced by any Python file.
   - The `research` service mounts `./results:/workspace/results` read-write and runs `make reproduce-paper1`. A container run overwrites tracked `results/` on the host.
   - The compose `version: "3.9"` key is obsolete in Compose v2+ (inferred from the spec; `docker compose config` not run).
   - Dockerfile `LABEL version="0.1.0"` disagrees with `pyproject` 1.1.0.
2. **Direct commands fail without `PYTHONPATH`.** `python -m relic_eval.sembench_eval` run without `PYTHONPATH=src:.` fails with `ModuleNotFoundError: legacy_contract`. The Makefile exports `PYTHONPATH`, but `docs/reproducibility.md` lists the bare commands. The repo has no editable install.
3. **Version fields disagree.** `pyproject.toml` and `CITATION.cff` say 1.1.0. `src/legacy_contract/__init__.py` `__version__` says 0.1.0, and the Dockerfile label says 0.1.0. The only git tag is `v1.0.0`. CHANGELOG has a 1.1.0 entry. No version is being chosen here.
4. **Test counts in the docs are stale.** `reports/v2/EVALUATION_SUMMARY.md` says 439 passed, and other docs say 391. The collected suite is 500 (`pytest --collect-only`). The difference is the SemBench (39) and external-eval (12) tests added since, plus others.
5. **Branch names disagree.** `CHANGELOG.md` and `docs/reproducibility.md:80` say `research/relic-v2-development`. `README.md:165` and `docs/reproducibility.md:98` say `research/relic-v2-final-sprint`. The pushed branch is `research/relic-v2-final-sprint`; the local branch is `research/relic-v2-publication-recovery`.
6. **Recorded commits do not identify the producing code.**
   - `SUBJECT_FREEZE.json` records `relic_commit` `f435029` and `frozen_code_uncommitted_diff_vs_HEAD: "none"`. But `relic_eval/external_eval.py`, `sembench_eval.py` and `text_baselines.py` are not in `f435029`; they were added later.
   - The committed `results/sembench/run_info.json` and `results/external/run_info.json` also record `f435029`.
   - The harness files on `origin/research/relic-v2-final-sprint` are byte-identical to HEAD's, and the freeze's per-file hashes match. The outputs are therefore valid. But "none" in `frozen_code_uncommitted_diff_vs_HEAD` is misleading: the code was uncommitted at `f435029`.
7. **Dependency sources are split.** `requirements.in` includes `pytest>=7.4`. `pyproject.toml` puts pytest in the `dev` extra and omits it from base dependencies. `requirements.lock` is generated from `requirements.in` (per its header) and has no hashes.
8. **Python version is not pinned in practice.** `pyproject` says `requires-python = ">=3.11"` with no upper bound. The lock was generated and tested under 3.11. `make setup` with no `python3.11` on PATH picks the first uv-managed CPython >= 3.11, which here is **3.13**. The suite passes on 3.13 (500 passed) but emits 629,460 warnings. Only test results were compared on 3.13, not outputs.
9. **Minor.**
   - `docs/reproducibility.md` says "tested: CPython 3.11.15". The committed `results/final` run used 3.11.15 and the audit used 3.11.16; no effect on outputs.
   - `docs/reproducibility.md` gives `make reproduce` as "5–25 min" (observed 5 min 06 s).
   - `relic_eval/detectors.py` imports `uuid` and never uses it.

## 6. Environment-dependent behaviour

- **Timestamps.** Only in `run_info.json`-style metadata (`pipeline`, `v2_eval`, `sembench_eval`, `external_eval`, and the legacy `rq*` JSON `run_timestamp`). Other committed outputs compared are timestamp-free. The legacy `results/rq2/negative_mutations.csv` has UUIDs in one column, generated in `src/legacy_contract/mutations/`.
- **Randomness.** All seeded: bootstrap seed `20261004` in `relic_eval/metrics.py` and `sembench_eval.py` (`np.random.default_rng`); LLM candidate order `ORDER_SEED` in `relic_eval/llm_baselines.py`. No unseeded random in the scored path.
- **Hash seed.** `external_eval.py` calls `os.environ.setdefault("PYTHONHASHSEED", "0")` at run start. That changes only child processes started afterwards (the worker pool), not the running interpreter, so the seed is recorded as `"0"` even when the shell has it unset. Outputs were identical across runs.
- **Sort order.** Scored paths sort their file lists (`subjects.py`, `external_eval.py`, `check_consistency.py`). Exception: `relic_eval/legacy.py:71` builds `{p.name: p for p in rglob("*")}`. With duplicate basenames, the winner depends on filesystem enumeration order (APFS vs ext4). Affects the legacy path only.
- **OS.** Every run here was macOS 26 arm64. The docs claim Linux support; it was not tested. Changes between macOS patch versions did not affect compared outputs.
- **Network.** The external rerun needs GitHub (public, unauthenticated; shallow fetch by SHA worked). Setup needs PyPI.
- **LLM.** No provider keys in the environment, so the offline path ran. With a key, `make llm-baselines` would re-query the model and results would differ, as documented.

## 7. Clean-clone steps that worked (for an independent researcher)

```
git clone --branch research/relic-v2-final-sprint https://github.com/ManasSakthivel/RELIC.git relic   # tested at 3352bf4
cd relic
make setup PY_BOOT=/path/to/python3.11      # needs PyPI; omit PY_BOOT only if python3.11 is on PATH (else uv picks 3.13)
make test                                   # 500 passed
make check                                  # consistency passed
PYTHONPATH=src:. python benchmarks/sembench/validate.py
PYTHONPATH=src:. python -m relic_eval.sembench_eval --out <new_dir>      # identical to results/sembench except run_info.json
make reproduce                              # ~5 min, offline LLM; only results/final/run_info.json changes (metadata)
make v2-eval                                # ~4 s; only results/v2/v2_run_info.json changes (metadata)
# External (network): clone each repo listed in results/external/SUBJECT_FREEZE.json into a new dir named by its 'dir',
# checkout its pinned_sha (verify HEAD), then:
PYTHONPATH=src:. python -m relic_eval.external_eval run --clones <dir> --out <new_dir>   # identical to results/external except run_info.json
```

Use `--out` with `sembench_eval` and `external_eval`; by default they write into `results/`. `make reproduce` and `make reproduce-legacy` write tracked files in place, so run them in a clone.

## 8. Recommended actions

1. Fix or remove the Docker path: use `pip install -r requirements.lock` (or add `[tool.poetry]`); drop the `poetry.lock*` glob; mount `results/` read-only or into a separate volume; document or remove the `api`/`db` services. Build the image once before claiming it works.
2. Add `PYTHONPATH=src:.` (or an editable install) to every direct command in `docs/reproducibility.md`.
3. Pick one version (`pyproject`, `src/legacy_contract/__init__.py`, Dockerfile label, `CITATION.cff`, a tag) and make them agree. This needs the maintainer's decision.
4. Reconcile test counts and branch names in README, CHANGELOG, `docs/reproducibility.md` and `reports/v2/EVALUATION_SUMMARY.md` with the 500-test figure and the pushed branch.
5. Correct `SUBJECT_FREEZE.json`'s provenance: name the commit that contains the harness (on `origin/research/relic-v2-final-sprint`, not `f435029`), and do not present `frozen_code_uncommitted_diff_vs_HEAD: "none"` as evidence of a clean freeze.
6. Pin the interpreter: make `make setup` select 3.11 explicitly (for example via `uv python find 3.11`), or document 3.13 as supported. Decide whether the 629,460 warnings matter, and compare outputs on 3.13 if 3.13 is to be claimed.
7. Unify dependency sources: generate `requirements.lock` from `pyproject`, or name `requirements.in` as canonical. Consider `--require-hashes`.
8. Run on Linux (GitHub Actions or a documented container) before claiming Linux support.
9. Change `legacy.py` to key on full relative paths, or sort the `rglob` output.

## 9. Tests and checks run (summary)

- pytest 500: 3.11.16 original tree, clean clone of `828bc15`, GitHub clone of `3352bf4`; 3.13 fresh venv (test results only).
- `check_consistency`: original tree, clean clone, GitHub clone.
- SemBench manifest (360) and `validate.py` (180 pairs).
- Freeze hashes: 53 code files, harness hash, dev corpus (718/365), 11 SHAs, 398 + 11 per-file and licence hashes.
- SemBench rerun (original tree and GitHub clone), external rerun, `make reproduce` (clean and GitHub clones), `make v2-eval`, `make reproduce-legacy` (clean clone).
- Static review: Dockerfile, docker-compose.yml, `requirements.in`/`.lock`, `pyproject.toml`, Makefile, README, CHANGELOG, CITATION.cff, `docs/reproducibility.md`.

## 10. Remaining uncertainty

- Docker: not built. The Poetry failure is inferred from file contents, not observed.
- Linux: not tested. All runs were macOS arm64.
- Second machine: the clones share this machine's toolchain (Homebrew `cobc`, uv, network). Another machine could differ.
- External: the clones were fetched on 2026-11-20. The per-file hashes verify content at each pinned SHA; upstream git history was not checked.
- LLM baselines: not re-queried. The reported LLM numbers rest on the committed cache only.
- Python 3.13: only the test results were checked, not output bytes; the 629,460 warnings are uninvestigated.
- Scientific validity (oracle correctness, ground truth, adequacy of the benchmark) was not assessed. This audit checks only that the committed numbers are reproducible.

## 11. Files produced

- `reports/recovery/REPRODUCIBILITY_AUDIT.md` (this file)
- `results/recovery/sembench_rerun/` (SemBench rerun output)
- `results/recovery/external_rerun/` (external rerun output)
- `results/recovery/comparison_summary.txt` (byte-comparison summary, including the GitHub-clone path)
- `results/recovery/logs/` (pytest, consistency, sembench, external, clone, validate, clean-clone, outsider, v2, legacy logs)
- Scratch, not in the repo: the 11 external clones under `scratchpad/ext/rerun2/`, the clean clone at `scratchpad/clean/relic1/`, and the GitHub clone at `scratchpad/clean/outsider/relic/`.
