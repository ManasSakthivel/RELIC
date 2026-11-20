# AGENT 6 — Reproducibility and Release Audit (RELIC V2)

Audited: branch `research/relic-v2-integration`, HEAD `b690039c66f3bbd2e13600a7bf58442f4724d3d0`
(parent chain `b690039 → aaa81d0 → d79d449 → 997611d → aee2309`). Clone: `/Users/manassakthivel/Desktop/finalSBG/RELIC`.
Interpreter: `.venv/bin/python` (CPython 3.11.15, macOS arm64), `PYTHONPATH=$PWD/src:$PWD`.
Nothing was committed or pushed. No tracked file was modified (see §6, final `git status --short`).

## 1. Executed-commands table

| # | Command | Exit | Key output |
|---|---|---|---|
| 1 | `git branch --show-current; git rev-parse HEAD` | 0 | `research/relic-v2-integration`; `b690039c66f3bbd2e13600a7bf58442f4724d3d0` |
| 2 | `git fetch` | 0 | no output (nothing new) |
| 3 | `git ls-remote origin` | 0 | `refs/heads/research/relic-v2-development = b690039c…` (== HEAD); `refs/heads/main = aee2309…`; `refs/heads/relic/final-research-remediation = aee2309…`; `refs/tags/v1.0.0 = 9d29311…` (peeled `db51c84…`); **no** `research/relic-v2-integration` on remote |
| 4 | `git rev-parse origin/research/relic-v2-development` | 0 | `b690039c66f3bbd2e13600a7bf58442f4724d3d0` |
| 5 | `git tag` | 0 | only `v1.0.0` |
| 6 | `python -m pytest tests -q` (work tree) | 0 | **439 passed, 0 failed, 0 skipped**, 12.67 s (pytest) / 12.86 s wall; no warnings summary |
| 7 | `make v2-eval PYTHON=$PWD/.venv/bin/python` (work tree) | 0 | wall 4.7 s; relic_v1_0 F1 0.9048, relic_v1_1 0.951, **relic_v2 TP 442 FP 0 FN 18 TN 106, P 1.0 R 0.9609 F1 0.98**, textdiff F1 0.9573 |
| 8 | `sha256sum results/v2/*` before/after run | 0 | `v2_metrics.json` f71056f0…2ec0 and `v2_predictions.jsonl` 60411f27…3ac **identical before/after**; `v2_run_info.json` changed (timestamp) → restored with `git checkout -- results/v2/v2_run_info.json` |
| 9 | `python -m relic_eval.check_consistency` | 0 | "Consistency check passed: metrics, tables, figures and documentation agree with raw results." |
| 10 | `git clone /Users/…/RELIC /tmp/relic_fresh_check; git checkout research/relic-v2-integration` | 0 | HEAD `b690039c…` |
| 11 | `make -n reproduce v2-eval test check` (fresh clone) | 0 | expands to pipeline → llm_baselines `--offline-if-no-key` → pipeline `--skip-benchmark` → check_consistency → v2_eval → pytest tests/ -q → check_consistency (all targets resolve; default `PYTHON` falls back to `/opt/homebrew/bin/python3.11` when no `.venv`) |
| 12 | `make v2-eval PYTHON=<abs venv python>` (fresh clone) | 0 | same metrics; `v2_metrics.json`/`v2_predictions.jsonl` sha256 equal to committed; only `v2_run_info.json` differs (restored) |
| 13 | `make test PYTHON=<abs venv python>` (fresh clone) | 0 | **439 passed**, 13.08 s |
| 14 | `make check PYTHON=…` (fresh clone) | 0 | consistency check passed |
| 15 | `pytest tests/v2 -q` (fresh clone, `PYTHONPATH=$PWD/src:$PWD`) | 0 | **48 passed**, 11.84 s |
| 16 | `git status --short --ignored`, size/`.DS_Store`/`__pycache__` checks | 0 | see §6 |
| 17 | secret pattern scans (`git grep` on HEAD tree; `git log -p aee2309..HEAD`; `git log --all -p -G…`; llm_cache grep) | 0 | no hits for any secret pattern; see §7 |
| 18 | `git diff aee2309 --stat -- results/final results/legacy paper/paper.md paper/references.bib` | 0 | empty (no differences) |
| 19 | per-file `git diff --quiet aee2309 HEAD -- <f>` for all 1 277 tracked files under `results/` except `results/v2/` | 0 | checked=1277, changed=0; file set identical to aee2309 |
| 20 | `git diff --name-status aee2309 HEAD` | 0 | 19 files: 13 A, 6 M; outside v2 directories only `CHANGELOG.md`, `Makefile`, `docs/reproducibility.md`, `relic_eval/detectors.py`, `relic_eval/v2_eval.py` (A), `src/legacy_contract/parsers/jcl_parser.py`, `src/legacy_contract/static_analysis/extractor.py` |

Note on the per-file sha256 comparison (task 8): git blob identity (`git diff --quiet` between two commits) is
content-hash equivalent; the working tree was additionally compared with `git diff --quiet aee2309 -- results/final results/legacy paper/paper.md paper/references.bib` (exit 0).

## 2. PASS / FAIL for items 1–10

| Item | Verdict | Evidence / caveat |
|---|---|---|
| 1. Branch, HEAD, fetch, tag state | **PASS** | Branch/HEAD as expected; `origin/research/relic-v2-development` == HEAD; only tag is `v1.0.0` (no V2 tag; `main` still `aee2309`). |
| 2. Full test suite | **PASS** | 439 passed in 12.67 s; also 439 passed in the fresh clone. |
| 3. `make v2-eval` byte-identity | **PASS** | metrics + predictions sha256 identical to committed; `v2_run_info.json` restored. |
| 4. `check_consistency` | **PASS** | exit 0, in work tree and fresh clone. |
| 5. Reproduction instructions (Makefile / docs/reproducibility.md) | **PASS (partial scope)** | `make -n reproduce v2-eval test check`, `make v2-eval`, `make test`, `make check`, `pytest tests/v2` all work from a fresh clone. **NOT VERIFIED:** `make setup` (venv creation + pip install of `requirements.lock`), full `make reproduce` (≈6 min; prior reproduction on d79d449 reported passing in scratch, not re-run here), `make reproduce-legacy`, `make llm-baselines` (needs API key). |
| 6. Repository cleanliness | **PASS with notes** | No tracked changes, no tracked `.DS_Store`/`__pycache__`/`.pyc`/`.env`; no `.DS_Store` on disk. Notes: two tracked files > 5 MB (see §6). |
| 7. Secret exposure | **PASS** | No secret patterns found in tree, history since `aee2309`, whole history, or `llm_cache`. Archives not scanned (see §7). |
| 8. Historical results unchanged | **PASS** | 0 of 1 277 non-v2 result files differ from `aee2309`; `paper/paper.md` and `paper/references.bib` unchanged. |
| 9. Remote synchronised | **PASS (with caveat)** | HEAD == `origin/research/relic-v2-development`. The local branch name `research/relic-v2-integration` does **not** exist on `origin` (it points at the same commit; nothing unpushed). |
| 10. Release blockers | **See §8** — several blockers/near-blockers found. |

## 3. Reproducibility details

- `make v2-eval` takes ≈ 4.7 s; it verifies regenerated mutants against committed `mutant_sha256` and recomputed v1.1 predictions against committed ones (per docs; code path executed successfully, exit 0).
- `results/v2/v2_run_info.json` is committed with `git_commit: d79d44955a9a…` (the commit at which the results were generated), not HEAD, and a timestamp; it changes on every run, so a clean `make v2-eval` always dirties the tree by exactly this file. Documented in `docs/reproducibility.md` ("holds a timestamp").
- Observation (not a defect of reproducibility): in `v2_eval` output `relic_v2_wo_D004` (F1 0.9823, FN 16) scores **higher** than full `relic_v2` (F1 0.98, FN 18), i.e. D-004 reduces recall on this development set. Any text describing D-004 as an improvement should be checked against this (NOT VERIFIED whether `reports/v2/EVALUATION_SUMMARY.md` states this).
- Tests use only pytest `tmp_path`/`tmp_path_factory`; grep found no network access (`urllib`, `requests`, `socket`, `http`) and no hard-coded `/tmp` paths in `tests/`. Tests passed from a fresh clone in a different directory, so they do not depend on the original checkout path or untracked files.

## 4. Remote / tag state

```
origin HEAD                              aee2309 (main)
refs/heads/main                          aee2309
refs/heads/relic/final-research-remediation  aee2309
refs/heads/research/relic-v2-development b690039 (== local HEAD)
refs/tags/v1.0.0                         9d29311 (annotated) -> db51c84
```
Local branches: `main` (aee2309, tracks origin/main), `research/relic-v2-development` (b690039), `research/relic-v2-integration` (b690039, no upstream configured).

## 5. Changes since aee2309

13 added, 6 modified files (6 593 insertions, 28 deletions). All V2 code changes are opt-in (`v2_fixes=False`, `v2=False` defaults). `all_detectors()` is unchanged and **deliberately excludes** `relic_v2` (guarded by `tests/v2/test_v2_fixes.py:362`), so `make reproduce` keeps regenerating published v1.0.0/v1.1 results.

## 6. Repository cleanliness

- `git status --short` at the end of the audit (tracked changes): **empty for tracked files**. The only entries are other agents' untracked files (reported separately below). Immediately after my `git checkout -- results/v2/v2_run_info.json`, `git status --short` showed no ` M` lines.
- Untracked (other agents; not touched, not judged): `paper/v2/` (`abstract.tex`, `introduction.tex`, `references.bib`, … at the time of the check). Other agents' files under `reports/v2/` and `research/v2/` may appear; they are not part of the audited HEAD.
- Ignored on disk: `.venv/`, `.pytest_cache/`, `__pycache__/` directories (all matched by `.gitignore`). `.gitignore` also covers `.env`, `.env.*` (except `.env.example`), `.DS_Store`.
- Tracked: 2 426 files. No tracked `.DS_Store`, `__pycache__`, `*.pyc`, `*.egg-info`, `.env`, `.pem`, `.key`.
- Files > 5 MB tracked (both pre-existing since v1.0.0 initial release `db51c84` / present in `aee2309`, not introduced by V2):
  - `datasets/public_cobol/cobol-programming-course-master.zip` (33.8 MB)
  - `datasets/public_cobol/extracted/cobol-programming-course-master/COBOL Programming Course #3 - Advanced Topics/Images/cobolchClaims-img6.gif` (7.0 MB)
  - Also > 1 MB: `datasets/carddemo/aws-mainframe-modernization-carddemo-main.zip` (4.2 MB), `results/final/raw/evaluation_records.jsonl` (1.6 MB). Datasets directory totals 81 MB. No blobs > 1 MB were added in `aee2309..HEAD`.
- No CI configuration (`.github/` absent) — no automated check protects `make test`/`make check`.

## 7. Secret exposure scan (names/types only)

Patterns scanned over the HEAD tree (zip files excluded as binary), added lines of `git log -p aee2309..HEAD`, and (for key/private-key formats) the whole history: Groq `gsk_…`, NVIDIA `nvapi-…`, `sk-…`, AWS `AKIA…`, `Bearer <token>`, `-----BEGIN … PRIVATE KEY`, GitHub `ghp_`, Slack `xox*-`, Google `AIza…`, `password = "<value>"`, key-variable assignments with values.

- Hits for real credentials: **none** in any category.
- Keyword-only hits (benign): `relic_eval/llm_baselines.py` (constructs `Authorization: Bearer` header at runtime from an environment variable — no literal key); `datasets/carddemo/.../app-authorization-ims-db2-mq/README.md` (third-party doc, word "authorization"); `results/final/raw/*` mutation IDs containing `app-authorization-ims-db2-mq`.
- `.env.example` is the only `.env*` file ever committed; values are empty placeholders.
- `results/final/raw/llm_cache/` (1 225 JSON files): no `authorization`, `api_key`, `bearer`, `gsk_`, `nvapi`, `sk-…` matches; files contain provider, model, decoding, prompt and response only.
- **NOT VERIFIED:** contents of the two dataset `.zip` archives (binary, excluded from grep; they are upstream open-source snapshots also present extracted). No dedicated scanner (gitleaks/trufflehog) was run.

## 8. Release blockers and issues

Severity: **B** = blocks a release/tag; **M** = should fix before release; **L** = minor/informational.

| ID | Sev | Finding | Evidence |
|---|---|---|---|
| R-1 | B | **Paper and docs contradict the raw LLM records on model/provider.** `paper/paper.md:162` and `docs/limitations.md:62` (L10) say the LLM baselines were "Groq `openai/gpt-oss-120b`"; `paper/paper.md:29,286`, `README.md:102,151`, `docs/evaluation/RESULTS.md`, `docs/evaluation/BASELINES.md` and the raw record `results/final/raw/llm_status.json` say nvidia `openai/gpt-oss-20b` (1 132 of the 1 225 cache files are nvidia/gpt-oss-20b; 93 are groq/gpt-oss-120b, i.e. the separate quota-limited subsample referenced at `paper.md:38`). `check_consistency` passes, so it does not guard this claim. `paper/paper.md` is byte-identical to `aee2309`, so the inconsistency pre-exists V2 but remains unfixed. |
| R-2 | B | **V2 is not discoverable or released.** `README.md` contains zero mentions of V2, `make v2-eval` or `results/v2` (only `docs/reproducibility.md`, `CHANGELOG.md` `[Unreleased]` mention it). No V2 tag; `CITATION.cff` (`version: 1.1.0`, `date-released: 2026-10-04`) and `pyproject.toml` (`version = 1.1.0`) do not describe V2; CHANGELOG lists V2 as `[Unreleased]`. Repository tag `v1.0.0` only, so even the cited 1.1.0 has no tag. |
| R-3 | M | **Version fields inconsistent:** `src/legacy_contract/__init__.py:11` `__version__ = "0.1.0"`, `Dockerfile` `LABEL version="0.1.0"`, `pyproject.toml`/`CITATION.cff` `1.1.0`, git tag `v1.0.0`. |
| R-4 | M | **Dockerfile / docker-compose are stale and almost certainly non-working (NOT VERIFIED, not built):** Dockerfile installs Poetry 1.7.1 and runs `poetry install`, but `pyproject.toml` uses setuptools (`[build-system] setuptools`, `[tool.setuptools…]`, no `[tool.poetry]` seen) and there is no `poetry.lock`; label says "LEGACY-CONTRACT Research Platform"; `docker-compose.yml` runs `make reproduce-paper1` (deprecated alias) and sets `PYTHONPATH=/workspace/src` only (Makefile adds `$(CURDIR)` itself). `docs/reproducibility.md` states Docker is not needed, but README/docs should either drop or fix these files. |
| R-5 | M | **`results/v2/v2_run_info.json` is stale/ non-reproducible by design:** committed `git_commit` is `d79d449` (not HEAD) with a timestamp; every `make v2-eval` dirties the tree. Consider excluding it or documenting a `git checkout --` step. Also `tests/v2` integrity test passes because it compares only metrics/predictions (confirmed byte-identical). |
| R-6 | M | **Dataset licensing / size:** README (L231–235) lists CardDemo Apache-2.0, OMP COBOL course "CC-BY-4.0 / Apache-2.0" (ambiguous dual statement), GenApp EPL-2.0. Per-dataset `LICENSE` files exist for all three (`datasets/*/…/LICENSE`, `datasets/genapp/source/LICENSE`) and GenApp has `PROVENANCE.md`; the CardDemo and public_cobol top-level directories have no `PROVENANCE.md`, only `README.md`/`ARTIFACTS.json`/`DATASET_VERSION.txt`. NOT VERIFIED: that the OMP course license text actually permits redistribution of the 33.8 MB zip and 7 MB GIF; redundant `.zip` + `extracted/` copies double the repository size. |
| R-7 | M | **Full pipeline not re-run on HEAD in this audit.** `make setup` and `make reproduce` (≈6 min) are NOT VERIFIED here. Since `aee2309..HEAD` leaves `results/final` and `all_detectors()` unchanged and `relic_eval/detectors.py` defaults are legacy, risk is low, but the claim "`make reproduce` regenerates published numbers" at HEAD rests on a prior run on d79d449 (not independently re-checked) plus 439 passing tests including results-integrity tests. |
| R-8 | M | **V2 claims need the development-set caveat visible everywhere**: docs correctly say V2 numbers are development-set results; the F1 of `relic_v2_wo_D004` (0.9823) exceeds `relic_v2` (0.98), so D-004 lowers recall on this set (see §3). NOT VERIFIED whether `reports/v2/EVALUATION_SUMMARY.md` discloses this. |
| R-9 | L | Branch `research/relic-v2-integration` is local-only (no upstream; `origin` has `…-development` at the same SHA). Push/PR strategy needs a decision. |
| R-10 | L | No CI workflow (`.github/` absent). |
| R-11 | L | `.env.example` header references "Baseline C … llama-3.3-70b-versatile via Groq" and "Paper 1"; `CHANGELOG.md:107` says "LLM baselines require `GROQ_API_KEY`", whereas the committed cache is nvidia-based; `llm_baselines.py` default is Groq `openai/gpt-oss-120b`. Re-running with a Groq key would not reproduce the committed nvidia results (docs already say fresh queries may differ). |
| R-12 | L | Legacy-named package (`src/legacy_contract`, "LEGACY-CONTRACT") vs project name RELIC in pyproject/Dockerfile. |
| R-13 | L | Tests: no network, no `/tmp` hard-coding; confirmed passing from a clone in `/tmp`. Not a blocker. |

Items explicitly checked and **not** blockers: V2 detector absent from `all_detectors()` (intentional, tested); no secrets; historical results byte-identical; `.gitignore` adequate; `CITATION.cff` valid-looking YAML with Apache-2.0 matching `LICENSE`/`pyproject.toml`.

## 9. NOT VERIFIED list

- `make setup` (venv + `pip install -r requirements.lock`) from scratch; `uv`-based alternative.
- Full `make reproduce` / `python -m relic_eval.pipeline` at HEAD (explicitly out of scope per instructions; scratch `git archive` re-run not performed).
- `make reproduce-legacy`, `make llm-baselines`, `make figures-legacy`.
- Docker image build / `docker compose` (Docker not run).
- Secret content inside the two dataset `.zip` archives; external scanners.
- Contents of other agents' untracked files under `reports/v2/`, `research/v2/`, `paper/v2/`.
- Linux behaviour (audit run on macOS arm64, CPython 3.11.15 only).

## 10. Cleanup

`/tmp/relic_fresh_check` (fresh clone) and `/tmp/a6_*` scratch files remain outside the repository. In the work tree only `reports/v2/AGENT_6_RELEASE_AUDIT.md` was created by this agent.
