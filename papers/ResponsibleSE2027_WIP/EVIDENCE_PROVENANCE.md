# Evidence provenance

Repository: RELIC-RECOVERY working tree, branch `research/relic-v2-publication-recovery`, HEAD `3c84a34`. Only RELIC V2 / JCL-SemBench evidence is used. RELIC V1.0.0 (three corpora, 566 evaluable cases) is not used and not merged.

| Evidence | Version | File | Git status | SHA-256 (first 16) | Status | Permitted use |
|---|---|---|---|---|---|---|
| 180 pairs, labels, SHA-256 of both file versions, oracle verdicts | V2 SemBench | `benchmarks/sembench/cases.jsonl` | tracked; last changed in commit 3ebec2b | fc8e64ba9999cb38 | Verified and reproducible (recounted) | Table 1 counts; identical pairs; duplicate groups; oracle verdicts |
| Frozen detector predictions (RELIC V1.0/V1.1/V2, text variants) | V2 SemBench | `results/sembench/predictions.jsonl` | tracked | 7f1809e42eda1ada | Verified and reproducible (MCC recomputed) | Table 2 MCC; complementarity |
| Cluster-bootstrap intervals (16 base programs, seed 20261004) | V2 SemBench | `results/final_go/bootstrap_original_method.json` | UNTRACKED (new this campaign) | 5a48908499df169d | Verified from script `reports/final_go/bootstrap_reproduction.py`; reproduces the repository's published L0 intervals | Table 2 intervals |
| Exact cluster-swap p-values (2^16 assignments) | V2 SemBench | `results/final/statistics/robustness_checks.json` | UNTRACKED | dc2964aa5c559c09 | Verified and reproducible (script `reports/final/scripts/robustness_checks.py`) | Table 2 p-values |
| L3 decomposition | V2 SemBench | `results/final/statistics/l3_decomposition.json` | UNTRACKED | 7a6fe8ad5c823a7b | Verified and reproducible; step value 0.0245 printed, unrounded 0.02446 → +0.024 | Gap decomposition sentence |
| Leave-one-program-out, deduplicated gap (−0.338), LLM bounds | V2 SemBench | `results/final_go/llm_bounds_dedup_loo.json` | UNTRACKED | 964e4e1eb263fa4c | Verified and reproducible (script `reports/final_go/llm_bounds_dedup_loo.py`) | Sensitivity sentence |
| Oracle verdict rule | V2 code | `jcl_oracle/judge.py` (compare_versions), `jcl_oracle/simulate.py` | tracked | — | Verified by reading code | Background paragraph |
| Earlier internal analysis (ΔMCC −0.2008 on original labels) | V2 internal report | `reports/v2/FINAL_SCIENTIFIC_VALIDITY_REPORT.md` §2 | tracked | — | Verified from file; not published | Limitations sentence only |
| Oracle-observable classification of the 14 disputed cases | V2 | `reports/final_go/...` audit tables and `paper/RELIC_V2_PUBLICATION_FINAL/main.tex` Table V | tracked as draft text; classification by one author | — | Disclosed as author classification, not independently checked | Oracle-scope paragraph (case names only) |
| 60-case review package, zero returned responses | V2 | `reports/v2/review_package` | tracked | — | Verified (zero responses) | Limitations |
| External run (824 mutants, not blind) | V2 | `results/external/` | tracked | — | Not re-verified in this pass | Limitations mention only |
| LLM partial run (155 of 180) | V2 | `results/final/llm/matched_subset_v1/` | committed rows 153; two rows uncommitted | — | Not reported in the results; mentioned as excluded | Limitations mention only |

## Discrepancies found and resolved
1. The earlier paper said "14 disputed labels". This is correct for the non-identical set only: 13 non-identical oracle disagreements plus 1 abstention. The oracle disagrees with the author label on 28 pairs in total, 15 of which are the identical CHANGING pairs. The new paper reports both numbers.
2. The earlier manuscript said "21 duplicate groups covering 46 cases". Recomputed: 21 groups, 46 pairs. Confirmed.
3. "Five contradictory groups": recomputed as 5 duplicate groups whose members carry different labels. Confirmed.
4. The earlier Table II value 0.487 for RELIC L2 was 0.4875 unrounded, which rounds to 0.488. The new paper prints 0.488.
5. The earlier paper described Ferrante et al. as a 1984 LNCS paper. Crossref shows TOPLAS 1987. Removed from the new paper (not needed).

## Not used
- Python `random`-based intervals in `paired_sensitivity.json` (superseded).
- Any LLM result as a claim.
- Any V1 metric.
