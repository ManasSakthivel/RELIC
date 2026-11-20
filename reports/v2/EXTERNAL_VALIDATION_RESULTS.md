# RELIC V2 — External validation results (frozen subjects, same oracle)

Author: Agent 3 (External Validation), final sprint. Date of run: 2026-11-20 (system clock).
Harness: [`relic_eval/external_eval.py`](../../relic_eval/external_eval.py) · freeze: [`results/external/SUBJECT_FREEZE.json`](../../results/external/SUBJECT_FREEZE.json) · outputs: `results/external/{metrics.json,predictions.jsonl,exclusions.json,run_info.json}` · tests: `tests/external/test_external_eval.py` (12 pass).
Scratch clones: `/tmp/relic_ext_final` (nothing external was copied into the repository; only hashes/paths are recorded).

## 0. Read this first (what this is and is not)

* **Labels come from the SAME, non-independent oracle (`jcl_oracle`) used in development, and the mutants from the same generator.** This run tests **generalisation of the parser/detector to files RELIC never saw in development**, *not* agreement with independent ground truth, human review, or real z/OS behaviour.
* **No external repository is blind.** All are **"screened by aggregate counts/fragments"**: Agent 3 of the earlier sprint saw aggregate counts for every candidate and text fragments of `mapa/test0100.jcl` and `zopeneditor-sample/JCL/ALLOCATE.jcl`; in this sprint I additionally saw file listings and lexer-level file/EXEC/line counts *before* the freeze. No oracle label or detector output on any external file existed at freeze time.
* **71 % of the evaluable mutants (589 / 824) come from one repository** (`yetacp/mvs_sysgen`, MVS 3.8j system-programmer JCL, upstream provenance unverified). Only 7 repositories contribute evaluable mutants. **No repository-level generalisation claim is made.**
* **Negatives are almost entirely cosmetic** (130 of 133 are comment insertions or `MSGCLASS` edits, the other 3 are oracle-equivalent fault mutants). Specificity therefore measures "does not fire on cosmetic edits", as in development.
* **Headline, stated plainly:** on the external pool, **`textdiff_ignore_job_parameters` (F1 0.9978) beats RELIC V2 (F1 0.9755)**; the paired file-level bootstrap difference RELIC V2 − that baseline is **−0.042 … −0.008 (excludes 0)**. This reproduces the development result (0.9978 vs 0.980) and is a **negative result for "RELIC beats a trivial rule"**. RELIC does beat the *raw* `textdiff` on F1 (+0.0010 … +0.0356 CI) purely through specificity (1.00 vs 0.53) — the same "not fire on JOB-card/comment edits" effect.

## 1. Subjects (frozen before running)

Pinned SHA = `git rev-parse HEAD` of a `--depth 1` clone (all four SHAs of the earlier protocol were re-obtained identically). Licence = text of the licence file read at that SHA (first line / sha256 in the freeze file). "Eligible" = frozen criteria (§2). RELIC commit at freeze: `f435029213fcb2b3034a7d76f8c00ef01749f3f9` (HEAD; frozen detector/oracle/mutator/metrics/pipeline/subjects/`src/` files had **no uncommitted diff**, run_info: `frozen_code_unchanged_since_freeze: true`).

| Repo | Role | Licence (read) | Pinned SHA | `.jcl` files | with JOB | **eligible** | excluded (reasons) | Exposure |
|---|---|---|---|---:|---:|---:|---|---|
| IBM/dbb | effectiveness | Apache-2.0 | `251b4750…` | 3 | 3 | **2** | 1 <2 EXEC | aggregate counts; NOT blind |
| IBM/zopeneditor-sample | effectiveness | Apache-2.0 (headers say "PROPERTY OF IBM": consistency unverified) | `8f983530…` | 10 | 8 | **7** | 3 <2 EXEC, 2 no JOB | aggregate counts **+ fragment** (ALLOCATE.jcl head); named as rejected candidate in archived docs; NOT blind |
| mainframed/Enumeration | effectiveness | MIT | `f893a0df…` | 12 | 12 | **5** | 7 <2 EXEC | aggregate counts (this sprint); NOT blind |
| vlachoudis/brexx | effectiveness | GPL-2.0 (analysis only, no redistribution) | `027afc0c…` | 8 | 8 | **6** | 1 <2 EXEC, 1 >40 EXEC | aggregate counts (this sprint); NOT blind |
| walmartlabs/zECS | effectiveness | Apache-2.0 | `6d6bcbbc…` | 10 | 10 | **5** | 4 <2 EXEC, 1 >40 EXEC | aggregate counts (this sprint); NOT blind |
| yetacp/mvs_sysgen | effectiveness (+sensitivity) | MIT on a derivative; **upstream provenance UNVERIFIED** | `91a532a8…` | 106 | 103 | **49** | 44 <2 EXEC, 16 >2000 lines, 5 >40 EXEC, 3 no JOB (overlapping) | aggregate counts; NOT blind |
| zowe/zowe-cli | effectiveness | EPL-2.0 | `8d0561c2…` | 7 | 7 | **2** | 5 <2 EXEC | aggregate counts; NOT blind |
| zowe/zowe-install-packaging (`v3.x/staging`) | effectiveness | EPL-2.0 | `07c2f91f…` | 14 | 8 | **0** | 12 <2 EXEC, 6 no JOB | aggregate counts; NOT blind |
| MartinPacker/Db2-DDF-Analysis-Tool | effectiveness | MIT | `516d0f85…` | 10 | 0 | **0** | 10 no JOB | aggregate counts (this sprint); NOT blind |
| zosconnect/zosconnect-sample-wola-batch | effectiveness | Apache-2.0 | `c9b208bb…` | 2 | 0 | **0** | 2 no JOB | aggregate counts (this sprint); NOT blind |
| cschneid-the-elder/mapa | **robustness only** | MIT | `d05705af…` | 216 | 199 | 0 | synthetic parser-stress data → excluded from every effectiveness metric | aggregate counts **+ fragment** (test0100.jcl); NOT blind |
| **Total effectiveness repos** | | | | **182** | | **76** | | |

Not acquired / excluded for licence (recorded in the freeze): `MVS-sysgen/sysgen` (GitHub licence = null; clone aborted), `MVS-sysgen/NETSOL`, `moshix/mvs`, `mainframed/{usstable,logica,DC30_Workshop}`, `zedsec390/NJElib` (all licence null), `mvslovers/jcc` (NOASSERTION), `pdos-project/pdos` (licence null; a public-domain statement was not verified), `IBM/IBM-Z-zOS` (clone aborted; 0 expected eligible per the earlier protocol). **Overlap with development corpora:** 0 of 398 `.jcl` files match any file under `datasets/` by raw or normalised sha256 (all non-zip files under `datasets/` hashed; 775 files incl. the two source zips); 0 within-pool duplicates among eligible files. RELIC-repo grep (`datasets/ docs/ relic_eval/ reports/`, excluding vendored `extracted/`/`source/`) finds the repo names only in the earlier protocol/integration report and the archived "rejected candidate" notes for `zopeneditor` (+ the future-work sentence "Zowe/IBM samples"); `Enumeration` matched only the English word in `docs/reproducibility.md`.

Discovery note: additional repositories were found with `gh search code --extension jcl` (read-only, using the user's existing `gh` login because unauthenticated API quota was exhausted). Only a handful of licensed hits were acquired; the list is a lower bound, not a survey.
Discrepancy to note: the earlier protocol (regex) counted 2 multi-step files in `zowe-install-packaging`; RELIC's lexer finds 0 files with a JOB and ≥2 `EXEC` statements (not investigated).

## 2. Freeze (design decided before results)

Eligible file: `.jcl`; ≥1 JOB; **≥2 EXEC**; **≤2000 lines**; **≤40 EXEC** (bounds in-stream data and oracle cost); not a duplicate of a development file; first occurrence kept in the pool. Repositories need a licence text read at the pinned SHA; mapa is robustness-only. Populations pre-declared: pooled effectiveness, per repository, pooled **without yetacp** (provenance sensitivity), leave-one-repository-out. Detectors: `relic_v1_0`, `relic_v1_1`, `relic_v2` (exactly as in `relic_eval/detectors.py`) plus `textdiff` and `textdiff_ignore_job_parameters` (from `v2_eval.py`). Detector ERRORs are scored "not flagged" **and** counted; the freeze also pre-registers an error-as-wrong bound. A per-file 900 s infrastructure timeout was fixed in advance (0 timeouts occurred). Full text: `design_decision_before_results` in the freeze file.

## 3. Accounting (statuses as in `relic_eval/pipeline.py`)

| Repo | files run | files with ≥1 evaluable | candidate mutants | EVALUABLE | OUT_OF_SCOPE | INVALID | INFRA_FAIL | OTHER |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| IBM/dbb | 2 | 2 | 8 | 8 | 0 | 0 | 0 | 0 |
| IBM/zopeneditor-sample | 7 | 7 | 108 | 54 | 54 | 0 | 0 | 0 |
| mainframed/Enumeration | 5 | 5 | 66 | 62 | 3 | 1 | 0 | 0 |
| vlachoudis/brexx | 6 | 3 | 57 | 56 | 1 | 0 | 0 | 0 |
| walmartlabs/zECS | 5 | 5 | 56 | 49 | 0 | 7 | 0 | 0 |
| yetacp/mvs_sysgen | 49 | 47 | 702 | 589 | 105 | 7 | 0 | 1 |
| zowe/zowe-cli | 2 | 2 | 8 | 6 | 0 | 2 | 0 | 0 |
| zowe-install-packaging, Db2-DDF, wola-batch | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| **Total** | **76** | **71** | **1005** | **824** | **163** | **17** | **0** | **1** |

**Coverage** = evaluable / candidate mutants = **824 / 1005 = 82.0 %**; files: 71 of 76 eligible files (93 %) and **71 of 182 `.jcl` files (39 %)** of the effectiveness repositories yield ≥1 evaluable mutant. 0 file-level timeouts/exceptions, **0 oracle crashes (INFRASTRUCTURE_FAILURE = 0), 0 generator crashes, 0 detector ERRORs** for every detector, so the "errors as not-flagged" and error-as-wrong results coincide.
Reasons: OUT_OF_SCOPE = `RENAME_OUTPUT_DATASET` with no consumer inside the file (163/163; cross-file effect only). INVALID: renamed DSN would exceed 44 characters (14), COND has no numeric test (1), mutant identical to original (2). **Oracle abstentions:** 18 mutants were labelled UNDETERMINED (all in yetacp); 17 of them were already OUT_OF_SCOPE, 1 is counted as OTHER. Oracle model errors on the *original* file: 0 in effectiveness files (4 in mapa).

## 4. Unsupported / out-of-scope syntax prevalence (project lexer; files)

Denominator: `.jcl` files with a JOB statement (eligible files in brackets). Counts of files containing the feature.

| Repo (files with JOB / eligible) | PROC use | PROC def. | INCLUDE | IF/THEN/ELSE | multi-JOB | in-stream `//` data | symbolics `&X` | GDG `(+1)` | JCLLIB | `COND=` |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| IBM/dbb (3/2) | 1 [1] | 1 [1] | 0 | 0 | 0 | 0 | 1 [1] | 0 | 0 | 2 [1] |
| IBM/zopeneditor-sample (8/7) | 1 [0] | 0 | 1 [0] | 0 | 0 | 0 | 8 [7] | 7 [7] | 1 [0] | 4 [4] |
| mainframed/Enumeration (12/5) | 0 | 0 | 0 | 0 | 0 | 0 | 12 [5] | 0 | 0 | 4 [4] |
| vlachoudis/brexx (8/6) | 7 [6] | 7 [6] | 0 | 0 | 0 | 0 | 7 [6] | 3 [3] | 0 | 2 [1] |
| walmartlabs/zECS (10/5) | 1 [1] | 0 | 0 | 0 | 0 | 0 | 1 [0] | 0 | 1 [1] | 0 |
| yetacp/mvs_sysgen (103/49) | 47 [25] | 14 [10] | 0 | 0 | 7 [0] | 23 [12] | 15 [8] | 0 | 0 | 20 [11] |
| zowe/zowe-cli (7/2) | 1 [1] | 1 [1] | 0 | 0 | 0 | 0 | 4 [1] | 0 | 0 | 0 |
| zowe/zowe-install-packaging (8/0) | 0 | 0 | 0 | 0 | 0 | 0 | 6 [0] | 0 | 2 [0] | 1 [0] |
| mapa, robustness only (199/0) | 28 | 4 | 2 | 5 | 16 | 5 | 110 | 2 | 5 | 16 |

Among the **76 eligible files**: PROC use 34 (45 %), in-stream PROC definition 18, symbolic parameters 28 (37 %), `COND=` 21 (28 %), GDG 10, in-stream `//` data 12, JCLLIB 1, **INCLUDE 0, IF/THEN/ELSE 0, multi-JOB 0** → `REMOVE_IF_GUARD` has **0 candidates**, exactly as in development. The eligibility rule (≥2 EXEC, ≤2000 lines) systematically removes the multi-job and IF-heavy files; this is a **selection effect of the frozen criteria**, not evidence that such syntax is absent from the repositories.

**Robustness (no mutation; 398 `.jcl` files incl. mapa's 216):** lexer, oracle `build_model`, mutator, and the three RELIC parsers raised **0 exceptions** on any file (`detector_parse_ERRORs` 0). Caveat: the detector wrapper turns exceptions into ERROR, and "no exception" does **not** mean "parsed correctly" — mapa's synthetic stress files give 4 files with oracle model errors on the original.

## 5. Results (EVALUABLE mutants of effectiveness repositories)

Pooled: **n = 824 mutants (691 positives / 133 negatives) from 71 files in 7 repositories.** Wilson 95 % CIs are mutant-level (optimistic); F1 CIs are file-level cluster-bootstrap percentile (10,000 resamples, seed 20261004). Precision CI of all RELIC variants: [0.994, 1.000].

| Detector | TP | FP | FN | TN | Precision | Recall (Wilson) | Specificity (Wilson) | F1 (bootstrap by file) | MCC |
|---|---:|---:|---:|---:|---:|---|---|---|---:|
| relic_v1_0 | 612 | 0 | 79 | 133 | 1.000 | 0.886 [0.860, 0.907] | 1.000 [0.972, 1.000] | 0.9394 [0.911, 0.961] | 0.745 |
| relic_v1_1 | 643 | 0 | 48 | 133 | 1.000 | 0.931 [0.909, 0.947] | 1.000 [0.972, 1.000] | 0.9640 [0.943, 0.981] | 0.827 |
| **relic_v2** | 658 | 0 | 33 | 133 | 1.000 | 0.952 [0.934, 0.966] | 1.000 [0.972, 1.000] | **0.9755 [0.956, 0.989]** | 0.874 |
| textdiff (raw) | 691 | 62 | 0 | 71 | 0.918 | 1.000 [0.995, 1.000] | 0.534 [0.449, 0.617] | 0.9571 [0.943, 0.967] | 0.700 |
| textdiff_ignore_job_parameters | 691 | 3 | 0 | 130 | 0.996 | 1.000 [0.995, 1.000] | 0.977 [0.936, 0.992] | **0.9978 [0.994, 1.000]** | 0.987 |

Paired F1 differences (bootstrap by file): RELIC V2 − v1.0 **+0.023 … +0.053**; V2 − v1.1 **+0.004 … +0.021**; V2 − textdiff **+0.001 … +0.036**; **V2 − textdiff_ignore_job_parameters −0.042 … −0.008** (i.e. the trivial rule is better). The 3 false positives of that rule are oracle-EQUIVALENT *fault* mutants (2 `COND` edits in `Enumeration/release/package.jcl`, 1 step swap in `mvs02.jcl`); RELIC handles those 3 correctly, but loses 33 true positives.

**Sensitivity — pooled without yetacp/mvs_sysgen** (n = 235, 197 pos / 38 neg, 24 files, 6 repos): v1.0 F1 0.9465 (R 0.899); **v1.1 = V2: F1 0.9897 (R 0.980, 4 FN)**; textdiff 0.9657; textdiff_ignore_job_parameters 0.9949 (V2 − that baseline: −0.027 … +0.010, CI includes 0). **V2's gain over v1.1 on the pooled external data comes entirely from yetacp** (V2 − v1.1 = 0 elsewhere). Leave-one-repo-out V2 F1: 0.9735 – 0.9777 when dropping any repo other than yetacp, 0.9897 when dropping yetacp.

**Per repository (V2 / v1.1 / v1.0 / textdiff_ignore_job_parameters, F1):** dbb 1.000 / 1.000 / 0.909 / 1.000 (n = 8); zopeneditor-sample 1.000 / 1.000 / 0.947 / 1.000 (n = 54); Enumeration 0.990 / 0.990 / 0.864 / 0.980 (n = 62); brexx 1.000 on all (n = 56, 3 negatives only); zECS 1.000 on all (n = 49, 5 negatives only); yetacp 0.970 / 0.953 / 0.937 / 0.999 (n = 589); **zowe-cli 0.400 / 0.400 / 0.400 / 1.000 (n = 6, 2 files)**. Per-repo CIs are in `metrics.json` and are wide for every repo except yetacp.

**Residual V2 false negatives (33):** yetacp 29 (SPLIT_JOB 11, SWAP 8, RENAME_OUTPUT 6, ALTER_COND 2, REMOVE_COND 2), zowe-cli 3 (SPLIT_JOB), Enumeration 1 (REMOVE_COND). **Not diagnosed** (no tuning permitted); the zowe-cli files are test templates (`{{JOBNAME}}` placeholders, three identically named `STEP1` steps, no dataset/COND relations), which looks like a realism artefact but was not verified.

**Per operator (V2 TP/FN):** SWAP 260/8 (+1 TN), SPLIT_JOB 260/14, DELETE_PRODUCER 40/0, MOVE_CONSUMER 25/0, RENAME_OUTPUT 23/6, REMOVE_COND 25/3, ALTER_COND 25/2; negatives INSERT_COMMENT 71/71 and CHANGE_MSGCLASS 59/59 correctly not flagged.

### Comparison with development results (`results/v2/v2_metrics.json`, 566 mutants / 66 files)

| Detector | Dev F1 | External F1 (CI) | Dev recall | External recall | Dev spec. | External spec. |
|---|---:|---|---:|---:|---:|---:|
| relic_v1_0 | 0.9048 | 0.9394 [0.911, 0.961] | 0.826 | 0.886 | 1.000 | 1.000 |
| relic_v1_1 | 0.9510 | 0.9640 [0.943, 0.981] | 0.907 | 0.931 | 1.000 | 1.000 |
| relic_v2 | 0.9800 | 0.9755 [0.956, 0.989] | 0.961 | 0.952 | 1.000 | 1.000 |
| textdiff | 0.9573 | 0.9571 | 1.000 | 1.000 | 0.613 | 0.534 |
| textdiff_ignore_job_parameters | 0.9978 | 0.9978 | 1.000 | 1.000 | 0.981 | 0.977 |

V2 recall/F1 is slightly **lower** on external files (0.952 vs 0.961; F1 0.9755 vs 0.980) with overlapping intervals; the ranking v1.0 < v1.1 < V2 and the ranking against the text baselines are preserved. Note that v1.0/v1.1 score *higher* externally than in development (0.939/0.964 vs 0.905/0.951), so part of any difference is the different file mix (largely sysgen jobs), not the detector. **I cannot separate "generalises" from "easier mix" with this data.**

## 6. What this does and does NOT show

**Shows (within the stated caveats):**
1. The frozen parser/detector/oracle pipeline runs without crashes on 398 foreign `.jcl` files (0 exceptions, 0 INFRASTRUCTURE_FAILURE, 0 detector ERROR) — including 216 synthetic stress files — and 824 evaluable mutants were produced from 71 unseen files.
2. Against the *oracle*, RELIC V2 keeps precision 1.000 / specificity 1.000 on cosmetic negatives and recall ≈ 0.95 on unseen files, a small drop from development (0.961), with overlapping CIs.
3. The V2 fixes do not harm external behaviour (no new FP; V2 ≥ v1.1 in every repository) and helped on one repository (yetacp).
4. The finding of the development phase — a trivial rule (`textdiff_ignore_job_parameters`) matches or beats RELIC on this mutation benchmark — **reproduces externally** and is statistically distinguishable from RELIC at file level.

**Does NOT show:**
* Agreement with independent ground truth — oracle, mutator and lexer are shared, authored by the same project; their common-mode errors are invisible here.
* Blind generalisation (repositories screened by aggregate counts/fragments), nor repository-level generalisation (7 contributing repositories, one supplying 71 % of mutants; 4 of them with ≤5 negatives).
* Behaviour on realistic enterprise batch: the pool is dominated by MVS 3.8j system-generation, build/install and test-fixture JCL; **no IF/THEN/ELSE, INCLUDE or multi-job file was eligible**; 163 mutants are out of scope.
* Any superiority over trivial text rules on semantic-equivalence cases (only 3 non-cosmetic negatives in 133).
* Anything about LLM baselines (not run).

## 7. Pending / next steps

* **Independent ground truth:** two blinded mainframe-qualified annotators on a stratified sample (oversampling the 3 non-cosmetic negatives and RELIC misses) with Cohen's κ; not done.
* **Human review** of the 33 residual false negatives and of OUT_OF_SCOPE/UNDETERMINED cases; not done.
* **Real z/OS (or ZD&T / partner LPAR) execution** of a calibration sample; Hercules/TK4- could cover only the `COND=`/utility subset; not done.
* A truly **blind** pool (files unseen by any author, licensed, ≥10 repositories, with IF/INCLUDE/PROC realism), strong behaviour-preserving negatives (benign reorders, symbolic renames, whitespace/continuation) and a code-search-based enlargement of the pool; not done.
* `MVS-sysgen/sysgen` (richest in `COND=`) remains unusable until its licence is confirmed; upstream provenance of `yetacp/mvs_sysgen` must be resolved before it is used in a publication.

## 8. Reproduction, determinism, deviations

```
cd RELIC && export PYTHONPATH=$PWD/src:$PWD
# clones at the pinned SHAs under /tmp/relic_ext_final/<owner>_<repo> (git clone --depth 1; HEAD must equal the frozen SHA)
.venv/bin/python -m relic_eval.external_eval freeze --clones /tmp/relic_ext_final   # write-once; already done
PYTHONHASHSEED=0 .venv/bin/python -m relic_eval.external_eval run --clones /tmp/relic_ext_final --workers 4
.venv/bin/python -m pytest tests/external -q
```
* **Determinism:** a second full run into a scratch directory produced byte-identical `metrics.json` (sha256 `3b39ae3b…`), `predictions.jsonl` (`3b09313f…`) and `exclusions.json` (`a2f3d959…`); only `run_info.json` differs (timestamp). The harness verifies each clone SHA and each file sha256 against the freeze before running.
* **Fidelity:** `tests/external` checks that the harness's statuses, oracle labels and predictions equal `relic_eval.pipeline.run_benchmark` on a generated tiny subject.
* **Deviations log:** (1) two launches of the first run were killed when the tool session ended (no outputs written; no code or freeze change) and the identical command was re-launched in a background process; (2) one test fixture bug (sequence-number columns) was fixed in the *test* while the run was in progress; the harness hash at run time equals the hash at freeze (`a4c37871…`); (3) clones of `MVS-sysgen/sysgen` and `IBM/IBM-Z-zOS` timed out and were removed; (4) code search used the user's `gh` credential read-only. Nothing in `src/`, `jcl_oracle/` or any other `relic_eval` file was modified; no git state was changed.
