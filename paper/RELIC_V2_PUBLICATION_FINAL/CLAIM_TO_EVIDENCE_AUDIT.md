# Claim-to-evidence audit: RELIC V2 negative empirical study

Every substantive claim in `main.tex`, traced to the file that supports it. Status: **Verified** (recomputed from raw files and matched), **Verified-with-caveat** (checked by an audit agent, not re-run by me), **Exploratory** (post hoc), or **Removed/softened**.

Sources:
- `reports/recovery/scripts/canonical_numbers.py` → `reports/recovery/CANONICAL_NUMBERS.json`
- `reports/recovery/scripts/stats_reanalysis.py` → `results/recovery/stats_reanalysis.json` (10,000 resamples, seed 20261004)
- `reports/recovery/scripts/complementarity.py` → `results/recovery/complementarity.json`
- Frozen inputs, not modified: `benchmarks/sembench/cases.jsonl`, `results/sembench/predictions.jsonl`, `results/external/predictions.jsonl`
- Audit reports: `reports/recovery/RED_TEAM_AUDIT.md`, `BENCHMARK_ORACLE_AUDIT.md`, `ALGORITHM_IMPROVEMENT_REPORT.md`, `BASELINE_AND_LITERATURE_AUDIT.md`, `LLM_EXPERIMENT_STATUS.md`

| # | Claim (location in paper) | Evidence | Status | Confirmatory? | Limitation |
|---|---|---|---|---|---|
| 1 | RELIC V2 MCC 0.324 vs normalized text B 0.525, SemBench (Abstract; Table I) | `stats_reanalysis.json` ALL_180; matches `results/sembench/metrics.json` | Verified | No (development data) | Same-author oracle |
| 2 | Paired ΔMCC −0.201 [−0.299, −0.102] (RQ1) | `comparisons.normalized_text_B.diff_boot` | Verified | Rule post hoc | 16 clusters; CI likely optimistic |
| 3 | H1 rejected (Table III) | Stated rule: CI entirely below 0 | Verified | Rule-bound, post hoc | — |
| 4 | RELIC precision 0.920 (23 of 25 flags), recall 0.247 (Table I) | `detectors.relic_v2` | Verified | No | — |
| 5 | Text B recall 0.839, precision 0.736 (Table I) | `detectors.normalized_text_B` | Verified | No | — |
| 6 | External RELIC precision 1.000, recall 0.952, F1 0.976, MCC 0.874 (Table I) | `external.pooled_file_cluster.detectors.relic_v2` | Verified | No | Not blind; same oracle |
| 7 | External text comparator recall 1.000, precision 0.996, F1 0.998, MCC 0.987 (Table I) | `…detectors.textdiff_ignore_job_parameters` | Verified | No | Comparator is operator-shaped (row 30) |
| 8 | Plain text diff F1 0.957, MCC 0.700 (Table I) | `…detectors.textdiff` | Verified | No | — |
| 9 | External ΔF1 −0.022 [−0.042, −0.008], file cluster (RQ1) | `external.pooled_file_cluster.comparisons` | Verified | No | — |
| 10 | External repo-clustered ΔF1 interval includes 0 [−0.032, 0.004] (RQ1) | `external.pooled_repo_cluster` | Verified | Descriptive only (7 clusters) | — |
| 11 | Excluding yetacp: ΔF1 −0.005 [−0.027, 0.010]; ΔMCC −0.027 [−0.124, 0.060] (RQ1) | `external.pooled_excl_yetacp_file_cluster.comparisons.textdiff_ignore_job_parameters.diff_boot` (checked against the JSON; the statistics report's prose misquoted the ΔF1 interval) | Verified | Exploratory | 235 mutants; 24 files |
| 12 | Per-case McNemar tracks class balance; vs plain text diff ΔMCC +0.148 but p = 0.85 (RQ1) | `comparisons.textdiff` | Verified | — | — |
| 13 | RELIC V2 ΔMCC +0.148 [0.038, 0.247] over plain text diff (RQ1) | same | Verified | Exploratory | Plain diff flags 60 of 87 PRESERVING pairs |
| 14 | vs normalized text A: ΔMCC −0.127 [−0.219, −0.033]; raw McNemar p 0.025; not significant under Holm over 86 tests (RQ1) | `comparisons.normalized_text_A`; `holm_global` | Verified | Exploratory | — |
| 15 | Holm p = 0.020 (14-test family), 0.029 (27 distinct published tests), 0.054 (42 distinct reanalysed tests) (RQ1; Threats) | `reproduction.headline_relic_vs_textB`; `STATISTICAL_REANALYSIS.md` §4, final version on disk | Verified; family choice is a judgement | Exploratory | An earlier version of the same report gave 0.069/0.123 with duplicates counted, which the final version calls wrong. The paper uses the de-duplicated values only |
| 16 | The text baseline's advantage depends on keyword-operand sorting; B differs from A on 7 cases (RQ1) | `BASELINE_AND_LITERATURE_AUDIT.md` | Verified-with-caveat | Exploratory | Not independently recomputed by me |
| 17 | RELIC-only true positives = 0 in every population and against every text baseline (RQ2; Abstract) | `comparisons.*.relic_only_tp`; `hypotheses.H2` | Verified | H2 rule | RELIC's flags are a strict subset of text flags |
| 18 | 26 correct RELIC rejections of harmless edits the text baseline flags (RQ2) | `comparisons.normalized_text_B.a_right_b_wrong` = 26 | Verified | — | — |
| 19 | Changing-case overlap: both 23, text only 55, neither 15 (Fig. 1b) | `comparisons.normalized_text_B.baseline_only_tp` = 55; `make_figures.py` asserts the total of 93 | Verified | — | — |
| 20 | The 15 neither-caught CHANGING cases are byte-identical no-ops (RQ2) | `cases.jsonl` sha256 equality | Verified | — | — |
| 21 | Excluding 25 identical pairs: ΔMCC −0.319 [−0.431, −0.230] (Table II) | `populations.EXCL_25_IDENTICAL` | Verified | Exploratory | — |
| 22 | Clean core (no identical, no disputed or abstained): ΔMCC −0.230 [−0.370, −0.129] (Table II) | `populations.CLEAN_CORE` | Verified | Exploratory | 67 changing cases |
| 23 | Excluding 13 oracle disagreements: ΔMCC −0.123 [−0.239, −0.022]; RELIC FP = 0 (RQ3; Table II) | `populations.SENS_EXCL_13_NONIDENT_ORACLE_DISAGREES` | Verified | Exploratory | Same-author oracle |
| 24 | 15 identical CHANGING and 10 identical PRESERVING pairs (Fig. 2) | `cases.jsonl`; `make_figures.py` asserts | Verified | — | — |
| 25 | 13 oracle disagreements and 1 abstention among non-identical pairs (Fig. 2) | `cases.jsonl`: 14 non-identical disagreement-flagged rows, including abstention sembench_172; 29 with identical | Verified | — | Reports disagree (13, 14, 28, 29). The paper states 13 + 1 + 15 identical |
| 26 | 21 duplicate groups covering 46 cases; 5 with contradictory labels, all among byte-identical pairs; 12 non-identical groups (24 cases) with consistent labels (Results; Abstract) | `cases.jsonl` grouped by (original sha, transformed sha), with and without identical pairs | Verified | — | Grouping key is the byte pair |
| 27 | 16 distinct base programs (Methods) | `cases.jsonl` `base_id` | Verified | — | — |
| 28 | Of 87 PRESERVING pairs, 46 are comment/whitespace/JOB-card edits; the normalizer rejects 44 of them; it rejects 15 of 41 structural negatives (Results) | `stats_reanalysis.json` per-category counts; category sums 17+17+12 and 21+14+6 checked against `cases.jsonl` | Verified (category-based; replaces the earlier "28 of 87" count, which was circular) | — | Categories are the benchmark's own labels |
| 29 | Five pairs labelled as step inversions are appended steps (Benchmark audit) | `RED_TEAM_AUDIT.md` M4; `build.py:992-1003` | Verified-with-caveat | — | Not yet in `DEFECT_REGISTER.md` |
| 30 | One operator rule matches 821 of 824 external labels (Abstract; Results) | Recomputed from `results/external/predictions.jsonl`: positive unless operator ∈ {INSERT_COMMENT, CHANGE_MSGCLASS}; the 3 errors are the 3 non-cosmetic negatives | Verified | — | Operator identity |
| 31 | Only 3 evaluable external negatives are non-cosmetic (Results) | `RED_TEAM_AUDIT.md` C2 | Verified-with-caveat | — | — |
| 32 | 163 RENAME_OUTPUT_DATASET mutants excluded; oracle labels 144 changing; text catches 144, RELIC 3; post hoc recall 0.792, F1 0.884, text F1 0.997 (Results) | `RED_TEAM_AUDIT.md` M1 | Verified-with-caveat | Exploratory | Scope policies differ across benchmarks |
| 33 | H3 not rejected: lowest per-repo Wilson lower bound 0.912 (Table III) | `stats_reanalysis.json` `hypotheses.H3` | Verified | Post hoc | Wilson, unclustered |
| 34 | H4 rejected on SemBench (23.6–25.0% avoided); met on external (94.8%) (Table III) | `complementarity.json`; `COMPLEMENTARITY_ANALYSIS.md` | Verified | Post hoc; external not blind | Pre-registration does not fix the denominator |
| 35 | H5 untested (Table III) | Binary flags; no explanation audit run | Verified | — | — |
| 36 | 11 listed repositories, 7 contribute evaluable mutants (Abstract; Threats) | `stats_reanalysis.json` `external.repos_with_evaluable` | Verified | — | — |
| 37 | yetacp supplies 589 of 824 (71.5%) (Methods; Threats) | `external.per_repo.yetacp_mvs_sysgen.n` | Verified | — | Provenance not fully verified |
| 38 | Every reported number reproduces from raw predictions; external and SemBench reruns reproduce byte-for-byte (Methods; Reproducibility) | `stats_reanalysis.py` reproduction table; `RED_TEAM_AUDIT.md` §1; `REPRODUCIBILITY_AUDIT.md` §1; `results/recovery/comparison_summary.txt` | Verified | — | Docker build not reproduced (stated in paper) |
| 39 | Oracle is code-independent but same-author and unvalidated (Discussion; Threats) | `reports/v2/ORACLE_INDEPENDENCE_AUDIT.md`; `RED_TEAM_AUDIT.md` C1 | Verified | — | — |
| 40 | No human validation; 60-case package has zero returned responses (Limitations) | `reports/v2/review_package` | Verified | — | — |
| 41 | No LLM baseline run; no credentials (Limitations) | `LLM_EXPERIMENT_STATUS.md`: credential variables unset | Verified | — | LLM comparison untested |
| 42 | Post hoc exclusions are sensitivity analyses (RQ3; Limitations) | `PREREGISTRATION.md` | Verified | — | — |
| 43 | External comparator chosen after development operator set was known (Discussion) | `RED_TEAM_AUDIT.md` M2, C2; `relic_eval/v2_eval.py` docstring says post hoc | Verified | — | Disclosed |
| 44 | Text baseline code hash matches freeze record (Methods) | `RED_TEAM_AUDIT.md` (sha256 check) | Verified | — | Whether the rule author saw the taxonomy is unverifiable |
| 45 | Papadakis 2016 and Tian 2024 metadata (References) | Crossref DOIs in `LITERATURE_MATRIX.csv` | Verified metadata; Tian abstract only partly read; author list abbreviated | — | Marked in bibliography |
| 46 | ChangeGuard venue Proc. ACM Softw. Eng. (References) | Crossref container | Verified | — | — |
| 47 | Kalohia 2026 covers legacy COBOL/PL/I analysis (Background) | ACL Anthology record | Verified (abstract read) | — | — |
| 48 | Deknop 2022 is static COBOL control-flow work (Background) | Semantic Scholar abstract | Verified (abstract read) | — | — |
| 49 | No peer-reviewed JCL contract-checking work found (Background) | Four JCL-focused searches | Verified as an incomplete search | — | Stated as incomplete |

## Claims removed or softened
- "Independent oracle" → "same-author, unvalidated oracle".
- "Holm-significant" → the family-dependent range.
- "11 repositories" → "7 contributing repositories".
- "Text baseline is significantly better than RELIC" → stated per comparator (normalized text B beats RELIC; plain text diff does not; the JOB-ignoring text rule ties).
- "Specificity advantage" → RELIC avoids 26 false alarms of text B, reported together with its lower recall.
- The earlier "random subsample" wording for the LLM subset is not used in the paper.

## Open items before submission
1. Reconcile the two statistics-report Holm values into one definition (row 15).
2. Docker build remains unreproduced (row 38; stated in the paper).
3. Register the appended-step generator defect (row 29).
4. Row 30 is now verified; no further action.

## Rows added in revision (after reviewer comments)

| # | Claim (location) | Evidence | Status | Confirmatory? | Limitation |
|---|---|---|---|---|---|
| 50 | Exact cluster sign-flip p = 0.002 for RELIC V2 vs text B (RQ1) | `comparisons.normalized_text_B.p_cluster_signflip` = 0.00195 | Verified | Exploratory | 16 clusters; exact enumeration over 2^12 sign patterns |
| 51 | MCC of text A 0.451, JOB-insensitive diff 0.302, plain text diff 0.176 (RQ1) | Derived from published ΔMCC values (RELIC 0.324 minus each ΔMCC): −0.127, +0.022, +0.148; cross-checked against `textdiff` MCC 0.176 in CANONICAL_NUMBERS.json | Verified (text A and JOB-insensitive values derived, not read directly) | — | — |
| 52 | Text B is the strongest text rule on SemBench by MCC (RQ1) | Ranking of rows 1 and 51 | Verified | — | Choice of primary comparator was made after results |
| 53 | Oracle returns EQUIVALENT for all 15 byte-identical CHANGING pairs (Results; Discussion) | `cases.jsonl` `oracle_verdict.label` = EQUIVALENT for all 15, all `ORACLE_DISAGREES` | Verified | — | — |
| 54 | 13 disagreements are non-identical pairs (Results) | `cases.jsonl`: disagreements among non-identical = 14 incl. abstention sembench_172 | Verified | — | — |
| 55 | Oracle definition: scenarios, DIFFERENT/EQUIVALENT/UNDETERMINED (Methods) | `jcl_oracle/__init__.py` docstring; `jcl_oracle/judge.py` | Verified (code) | — | Observables are documented in `docs/evaluation/ORACLE_SPECIFICATION.md`, not re-read here |
| 56 | 70 SemBench misses = 15 no-ops + 16 DISP + 12 COND + 9 DSN redirects + 8 in-stream + 5 program substitution + 5 appended (RQ2) | `reports/recovery/ALGORITHM_IMPROVEMENT_REPORT.md` (error table, `algo_fn_trace.py`) | Verified-with-caveat (agent categorisation; sums to 70) | — | Categorisation is a judgement |
| 57 | External zero RELIC-only TP is guaranteed because text recall = 1.000 there (RQ2) | `external.pooled_file_cluster.detectors.textdiff_ignore_job_parameters.recall` = 1.0 | Verified | — | — |
| 58 | Bibliography authors: Tian et al. 2024 (Z. Tian, H. Shu, D. Wang, X. Cao, Y. Kamei, J. Chen) and Papadakis et al. 2016 (five authors incl. Y. Le Traon) | Crossref `api.crossref.org/works/10.1145/3650212.3680395` and `…/10.1145/2931037.2931040` | Verified | — | — |
| 59 | Ferrante et al. 1984 and Horwitz et al. 1988 cited for program dependence graphs (Background) | Literature matrix rows (Crossref metadata) | Verified metadata; abstracts not read | — | — |
| 60 | Venue: ResponsibleSE 2027 short papers 4–6 pages; research papers 6–8; IEEE template; double-blind; submission deadline Fri 20 Nov 2026 AoE (Publication strategy) | Official researchr page, read 2026-11-20 (web-fetch agent) | Verified for categories, template, blinding and deadline; **reference counting and archival status NOT STATED** | — | The negative-results category is not listed on the page; choose the short-paper WIP/position category |

| 61 | Docker image cannot be built as written; `research` service mounts results read-write (Reproducibility) | `reports/recovery/REPRODUCIBILITY_AUDIT.md` item 5: no `[tool.poetry]` section or `poetry.lock`; `api` service packages absent from lock; compose mount. Docker daemon not running, so no build attempted | Verified by reading config; build not attempted | — | Build not run; claim limited to config inspection |
