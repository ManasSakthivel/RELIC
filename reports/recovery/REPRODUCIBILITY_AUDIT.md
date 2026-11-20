# Reproducibility audit (RELIC V2 publication recovery)

Audit date: 2026-11-20. Repository HEAD: `828bc15` on `research/relic-v2-publication-recovery`.
Python 3.11.16 (uv-managed, macOS 26.7 arm64). Scope: documented commands, hash manifests, a
SemBench rerun, the 11-repository external rerun, a clean-clone reproduction, and static
review of Docker and dependency files.

Nothing tracked was modified. All reruns wrote to new directories under `results/recovery/`
or to a clean clone of HEAD under the session scratchpad. Logs are in `results/recovery/logs/`
and the byte comparison is in `results/recovery/comparison_summary.txt`.

## 1. Verdict

| Claim | Status |
|---|---|
| Test suite: 500 passed | **Reproduced** (3.11.16: 500 passed; 3.13.x in a fresh venv: 500 passed) |
| `check_consistency` passes | **Reproduced** (original tree and clean clone) |
| SemBench manifest (360 entries) verifies | **Reproduced** (360/360 OK) |
| `benchmarks/sembench/validate.py` | **Reproduced** (180 pairs; 151 validated, 28 oracle disagreements, 1 abstention) |
| `results/external/SUBJECT_FREEZE.json` code and file hashes | **Reproduced** (53/53 frozen code files; 398 repo files + 11 licence files after clone) |
| SemBench evaluation (`relic_eval.sembench_eval`) | **Reproduced byte-for-byte** (metrics, predictions, paired tests) |
| External 11-repository rerun | **Reproduced byte-for-byte** (predictions, metrics, exclusions), from clones at the frozen SHAs |
| Full `make reproduce` | **Reproduced** in a clean clone of HEAD (5 min 06 s, exit 0). Only metadata files differ |
| `make v2-eval`, `make reproduce-legacy` | **Reproduced** in the clean clone (metadata and UUID/timestamp fields only) |
| Docker build / `docker compose` | **Not reproduced**. Dockerfile cannot install the project as written (static finding; the Docker daemon is not running, so no build was attempted) |
| LLM baselines C/D re-query | **Not run** (no API key; offline re-scoring path only) |

Bottom line: the Python evaluation pipeline reproduces from a clean clone on this machine.
The Docker path does not, and several version and documentation statements are stale.

## 2. Documented commands run

| Command | Where | Result |
|---|---|---|
| `python -m pytest tests/ -q` (`make test`) | original tree, 3.11.16 | 500 passed in 17.8 s |
| same | fresh 3.13 venv from `requirements.lock` | 500 passed, 629,460 warnings (not investigated) |
| `python -m relic_eval.check_consistency` (`make check`) | original tree | "Consistency check passed" |
| `python benchmarks/sembench/validate.py` | original tree | `[SUCCESS] JCL-SemBench verification passed completely.` |
| `python -m relic_eval.sembench_eval --out results/recovery/sembench_rerun` | original tree | exit 0, about 2.5 s |
| `python -m relic_eval.external_eval run --clones <ext>/rerun2 --out results/recovery/external_rerun --workers 4` | original tree | exit 0, about 5 min |
| `make setup PY_BOOT=<3.11>`, `make test`, `make check`, `make reproduce` | clean clone of HEAD (`scratchpad/clean/relic1`) | all exit 0; 500 passed; check passed; reproduce 5 m 06 s |
| `make v2-eval` | clean clone | exit 0, about 4 s |
| `make reproduce-legacy` | clean clone | exit 0, under 1 s |

Not run: `make llm-baselines` (needs API key, rewrites `llm_records.jsonl`), Docker targets
(daemon not reachable), `results/sembench/noop_sensitivity.py`, `make figures-legacy`.

## 3. Hash verification

- `benchmarks/sembench/MANIFEST.sha256`: `shasum -a 256 -c` gives 360 OK, 0 failures.
- `results/external/SUBJECT_FREEZE.json` `frozen_code_sha256` (53 files): all match the working tree.
  `harness_sha256` (`relic_eval/external_eval.py`) matches `a4c378...`.
- Clones of the 11 external repos (shallow fetch of each frozen SHA into a new directory):
  all 11 HEADs equal the frozen `pinned_sha`. Per-file SHA-256 for all 398 eligible/robustness
  `.jcl` files and all 11 licence files match the freeze (409 OK, 0 mismatch, 0 missing).
- The external run's `run_info.json` records `frozen_code_unchanged_since_freeze: true`.

## 4. Rerun results

### 4.1 SemBench
`results/recovery/sembench_rerun/` versus `results/sembench/`:
- `metrics.json`, `predictions.jsonl`, `paired_tests.json`: byte-identical.
- `run_info.json`: differs in timestamp, `git_commit` (committed run `f435029`; rerun `828bc15`),
  platform patch level and Python patch level. Expected, and ignored per the brief.

### 4.2 External (11 repositories, frozen SHAs)
`results/recovery/external_rerun/` versus `results/external/`:
- `predictions.jsonl` (1,005 records): byte-identical.
- `metrics.json`, `exclusions.json`: byte-identical.
- `run_info.json`: differs in timestamp, `relic_commit_at_run`, platform and Python patch level only.

Timing: the rerun took about 5 minutes after the clones were in place, comfortably under
the 20-minute budget. The clone phase (11 shallow fetches by SHA) took about 2 minutes.

### 4.3 Clean clone of HEAD `828bc15`
`git clone --no-hardlinks` of the committed repository, then the documented commands in order.
No file from the original working tree was copied in (the untracked `reports/recovery/scripts/`
and `results/recovery/` are absent from the clone, as intended):
- `make setup PY_BOOT=<uv CPython 3.11>`: exit 0, 8 s (PyPI network access used).
- `make test`: 500 passed.
- `make check`: passed.
- `make reproduce`: exit 0, 5 min 06 s, LLM step offline (no keys set).
  Result: `git status` shows **one** modified tracked file, `results/final/run_info.json`
  (timestamp, platform, Python patch, git_commit). Every other tracked output regenerated
  byte-identically, and there are no new untracked outputs.
- `make v2-eval`: only `results/v2/v2_run_info.json` changed (timestamp, git_commit, platform, Python patch).
- `make reproduce-legacy`: `results/rq1`, `rq2`, `rq3` JSON changed only in `run_timestamp`.
  `results/rq2/negative_mutations.csv` changed only in its UUID column (column 10; verified
  row-by-row, 145 rows, 0 differences elsewhere). This matches the docs' "apart from
  timestamps/UUIDs" statement.

## 5. Mismatches and stale statements

Ordered by how much they affect a reader trying to reproduce.

1. **Docker path does not work as written (static finding, not built).**
   - `Dockerfile` runs `pip install poetry==1.7.1` then `poetry install`. `pyproject.toml` has
     no `[tool.poetry]` section; Poetry 1.x does not read the PEP 621 `[project]` table. The
     build is expected to fail or install no project dependencies.
   - `COPY pyproject.toml poetry.lock* ./`: no `poetry.lock` exists, so the image never uses
     `requirements.lock` and gets unpinned ranges.
   - `docker-compose.yml`: `api` runs `legacy_contract.api.main` which imports `fastapi`,
     `pydantic`, `uvicorn` (only in the `api` extra, not in `requirements.lock`); no test imports
     it, so this is unverified at runtime. `db` (neo4j 5.13) is not referenced by any Python file.
   - `research` mounts `./results:/workspace/results` read-write and runs `make reproduce-paper1`.
     Running the container overwrites tracked `results/` on the host. The reproducibility doc
     already says Docker is "not needed"; the compose file should say the same or be removed.
   - The compose `version: "3.9"` key is obsolete in Compose v2+ (inferred from the spec; `docker compose config` not run).
   - Dockerfile `LABEL version="0.1.0"` vs `pyproject` 1.1.0.
2. **Version fields disagree.** `pyproject.toml` and `CITATION.cff` say 1.1.0;
   `src/legacy_contract/__init__.py` `__version__` says 0.1.0; Dockerfile label says 0.1.0;
   the only git tag is `v1.0.0`. CHANGELOG has a 1.1.0 entry. No version is being chosen here.
3. **Test counts in the docs are stale.** `reports/v2/EVALUATION_SUMMARY.md` says 439 passed;
   other docs say 391. The collected suite is 500 (`pytest --collect-only`): the difference is
   the SemBench (39) and external-eval (12) tests added since, plus others.
4. **Branch names disagree.** `CHANGELOG.md` and `docs/reproducibility.md:80` say
   `research/relic-v2-development`; `README.md:165` and `docs/reproducibility.md:98` say
   `research/relic-v2-final-sprint`; the actual branch is `research/relic-v2-publication-recovery`.
5. **The freeze commit does not contain the harness.** `results/external/SUBJECT_FREEZE.json`
   records `relic_commit` `f435029`, but `relic_eval/external_eval.py`, `relic_eval/sembench_eval.py`
   and `relic_eval/text_baselines.py` are not in that commit (they first appear in later commits,
   up to `828bc15`). The harness's own hash matches the file at HEAD, so the results are valid,
   but a checkout of `f435029` cannot run the external harness.
6. **Dependency sources are split.** `requirements.in` includes `pytest>=7.4`; `pyproject.toml`
   puts pytest in the `dev` extra and omits it from base dependencies. `requirements.lock` is
   generated from `requirements.in` (per its header) and has no hashes. Two sources of truth.
7. **Python version is not pinned in practice.** `pyproject` says `requires-python = ">=3.11"`
   with no upper bound. The lock was generated and tested under 3.11. `make setup` with no
   `python3.11` on PATH picks the first uv-managed CPython >= 3.11: here that is **3.13**, not 3.11.
   The suite passes on 3.13 (500 passed) but emits 629,460 warnings, which were not investigated.
8. **Minor.** `docs/reproducibility.md` says "tested: CPython 3.11.15"; the audit run and the
   committed `results/final` run used 3.11.15/3.11.16 (no effect on outputs). `relic_eval/detectors.py`
   imports `uuid` but never uses it. `Makefile` `reproduce` target is described as "5-25 min"
   (observed 5 min 06 s on this machine).

## 6. Environment-dependent behaviour

- **Timestamps.** Only in `run_info.json` (and `frozen_at_utc`/`timestamp_utc` fields) across
  `pipeline`, `v2_eval`, `sembench_eval`, `external_eval`, and the legacy `rq*` JSON. All
  committed scientific outputs compared were otherwise timestamp-free. The legacy `rq2` CSV has  random UUIDs in one column (written by `scripts/run_negative_mutations.py` via `make reproduce-legacy`; not inspected further).
- **Randomness.** All seeded: bootstrap seed `20261004` (`relic_eval/metrics.py`,
  `sembench_eval.py` via `np.random.default_rng`); LLM candidate order `ORDER_SEED`
  (`relic_eval/llm_baselines.py`). No unseeded random in the scored path.
- **Sort order.** Scored paths sort their file lists (`subjects.py`, `external_eval.py`,
  `check_consistency.py`). Exception: `relic_eval/legacy.py:71` builds
  `{p.name: p for p in rglob("*")}`; with duplicate basenames the winner depends on filesystem
  enumeration order (APFS vs ext4). Affects the legacy path only.
- **Hash seed.** `external_eval` records `PYTHONHASHSEED` but does not set it; outputs were
  identical across the two runs, so the scored output does not depend on it.
- **OS.** Every run here is macOS 26 arm64. The Makefile and docs claim Linux support, and
  this was not tested. `run_info.json` records the platform and nothing in the compared outputs
  changed between macOS patch versions.
- **Network.** The external rerun needs GitHub access (public, unauthenticated, shallow fetch
  by SHA worked). Setup needs PyPI. Neither is needed for the SemBench or the core pipeline
  once the environment exists.
- **LLM.** No provider keys in the environment, so the offline path ran. With a key,
  `make llm-baselines` would re-query the model and results would differ (documented).

## 7. Clean-clone steps that worked (for an independent researcher)

```
git clone <repo> relic && cd relic            # committed HEAD 828bc15 (branch research/relic-v2-publication-recovery)
make setup PY_BOOT=/path/to/python3.11        # ~10 s; requires PyPI; omit PY_BOOT only if python3.11 is on PATH
make test                                     # 500 passed (~35 s)
make check                                    # consistency passed
make reproduce                                # ~5 min, offline LLM; expect results/final/run_info.json to differ only in metadata
make v2-eval                                  # ~4 s; results/v2 identical except v2_run_info.json metadata
python benchmarks/sembench/validate.py        # SemBench manifest + oracle re-run
python -m relic_eval.sembench_eval --out <new_dir>        # byte-identical to results/sembench except run_info.json
# External (network): clone each repo in results/external/SUBJECT_FREEZE.json into a new dir named by 'dir',
# checkout pinned_sha, then:
python -m relic_eval.external_eval run --clones <dir> --out <new_dir>   # byte-identical to results/external except run_info.json
```

Important: `sembench_eval` and `external_eval` write to `results/` by default. Pass `--out`.
`make reproduce` and `make reproduce-legacy` write tracked files in place; run them only in a clone.

## 8. Recommended actions

1. Fix or remove the Docker path: add `[tool.poetry]` or switch the Dockerfile to
   `pip install -r requirements.lock`; drop `poetry.lock*`; mount `results/` read-only or
   write to a separate volume; document the api/db services or remove them. Build it once
   before claiming it works.
2. Pick one version (`pyproject`, `src/legacy_contract/__init__.py`, Dockerfile label,
   CITATION.cff, a git tag) and make them agree. This needs the maintainer's decision.
3. Reconcile test counts and branch names in README, CHANGELOG, `docs/reproducibility.md`,
   and `reports/v2/EVALUATION_SUMMARY.md` with the 500-test figure.
4. Record in `SUBJECT_FREEZE.json` (or the docs) that the harness first appears after
   `f435029`, and name the commit that contains it.
5. Make `make setup` default to 3.11 explicitly (for example `uv python find 3.11`), or document
   that 3.13 is also supported and tested. Decide whether to investigate the 629,460 warnings.
6. Unify the dependency sources: generate `requirements.lock` from `pyproject` or state
   `requirements.in` as canonical; consider `--require-hashes`.
7. Add a Linux run (GitHub Actions or a container with a documented image) before claiming Linux support.
8. Change `legacy.py` to key on full relative paths, or sort the rglob output.

## 9. Tests and checks run (summary)

- pytest 500 (3.11.16 original tree; 3.11.16 clean clone; 3.13 fresh venv).
- `check_consistency` (original and clean clone).
- SemBench manifest (360) and `validate.py` (180 pairs).
- Freeze hashes: 53 code files, harness hash, 11 SHAs, 398 + 11 per-file/licence hashes.
- SemBench rerun, external rerun, `make reproduce`, `make v2-eval`, `make reproduce-legacy`
  (all in clean clone or new directories).
- Static review: Dockerfile, docker-compose.yml, requirements.in/lock, pyproject, Makefile,
  README, CHANGELOG, CITATION.cff, docs/reproducibility.md.

## 10. Remaining uncertainty

- Docker: not built; the Poetry failure is inferred from the file contents, not observed.
- Linux: not tested. Only macOS arm64 was used.
- Independent machine: the "clean clone" is a clone of the same machine's toolchain (same
  Homebrew cobc, same uv, same network). A second machine could differ.
- External: the clones were fetched today from GitHub. Repository contents at a pinned SHA
  are immutable in practice, but the verification relied on the per-file hashes, not on
  git history of the upstream repos.
- LLM baselines: not re-queried; the reported LLM numbers rest on the committed cache only.
- The 629,460 warnings on Python 3.13 were not analysed; they may be harmless.
- Scientific validity (oracle correctness, ground truth) was not assessed. This audit only
  checks that committed numbers are reproducible.

## 11. Files produced

- `reports/recovery/REPRODUCIBILITY_AUDIT.md` (this file)
- `results/recovery/sembench_rerun/` (SemBench rerun output)
- `results/recovery/external_rerun/` (external rerun output)
- `results/recovery/comparison_summary.txt` (byte-comparison summary)
- `results/recovery/logs/` (pytest, consistency, sembench, external, clone, validate, clean-clone, v2, legacy logs)
- Scratch (not in repo): `/private/tmp/claude-502/-Users-manassakthivel-Desktop/79925786-d69d-4e70-b66b-2090a0914b34/scratchpad/ext/rerun2/` (11 external clones) and `.../scratchpad/clean/relic1/` (clean clone)
