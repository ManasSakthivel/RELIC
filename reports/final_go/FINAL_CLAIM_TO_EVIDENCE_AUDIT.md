# Final claim-to-evidence audit (narrowed short paper)

Scope: every substantive claim in `paper/RELIC_V2_PUBLICATION_FINAL/main.tex` as of 2026-11-21 (UTC ~02:30). Checks are commands in `REPRODUCTION.md`. Status: PASS (verified against an output file), PASS-BY-READING (verified by reading the cited code or data), OPEN (needs external fact or user action).

| # | Claim | Evidence | Check | Status |
|---|---|---|---|---|
| 1 | 180 pairs; 93 CHANGING, 87 PRESERVING | `benchmarks/sembench/cases.jsonl` | count by `expected_outcome` | PASS |
| 2 | 25 byte-identical pairs; 15 labelled CHANGING | cases.jsonl SHA-256 fields | byte-hash equality | PASS |
| 3 | 21 duplicate groups; ten CHANGING relabels cover eight distinct edits (117≡129, 118≡130) | cases.jsonl hash pairs | duplicate grouping | PASS |
| 4 | Table I: MCC of all detectors on L0–L3 | `results/sembench/predictions.jsonl`; `results/final/statistics/robustness_checks.json` | recomputed | PASS |
| 5 | Table II: MCC and CI for RELIC V2 and text B on L0–L3 | `results/final_go/bootstrap_original_method.json` | `verify_manuscript_text.py` (tie-safe) | PASS |
| 6 | Δ MCC and CI on each set (−0.201, −0.336, −0.250, −0.170) | bootstrap JSON | `verify_manuscript_text.py` | PASS |
| 7 | Exact cluster-swap p = 0.015, 0.002, 0.010, 0.089 | `results/final/statistics/robustness_checks.json` (`cluster_swap`) | `verify_manuscript_text.py` | PASS |
| 8 | Gap range −0.17 to −0.34 in abstract | bootstrap JSON | `verify_manuscript_text.py` | PASS |
| 9 | Gap on 155 unique pairs −0.338; leave-one-program-out −0.364 to −0.313 | `results/final_go/llm_bounds_dedup_loo.json` | `llm_bounds_dedup_loo.py` | PASS |
| 10 | RELIC V2 detects no changing case that text B misses | predictions | `complementarity_checks.py` | PASS |
| 11 | RELIC V2 misses 55 of 78 CHANGING pairs on L1 | predictions | recomputed (confusion counts 23 TP, 55 FN on L1 for RELIC; 78 CHANGING in L1) | PASS |
| 12 | Decomposition of L1→L3: +0.024, +0.135; ten relabels about 81% of narrowing | `results/final/statistics/l3_decomposition.json` | script | PASS (order-dependent; stated) |
| 13 | Two step renames alone move gap by +0.038 | `results/final/statistics/step_name_sensitivity.json` | script | PASS |
| 14 | Exhaustive range −0.350 to −0.163 over 2^13 labelings (172 kept) | `results/final/statistics/bounds_and_dedup.json` | script | PASS |
| 15 | Ten CHANGING cases flagged by text B and not by RELIC | predictions | recomputed | PASS |
| 16 | Oracle verdict rule as implemented (DIFFERENT / UNDETERMINED / EQUIVALENT); docstring stricter | `jcl_oracle/judge.py` compare_versions; `jcl_oracle/__init__.py` line 18 | code read | PASS-BY-READING |
| 17 | Case 036: PARM text enters dataset-version label read by BIND; z/OS equivalence unchecked | `jcl_oracle/simulate.py` write_key/base_sig; case files differ only in PARM quoting | code read and diff | PASS (equivalence OPEN, disclosed) |
| 18 | Staats et al. (ICSE 2011, 2012) are the closest oracle-observability work; this paper does not claim the effect as new | Crossref DOIs 10.1109/icse.2012.6227132 and 10.1145/1985793.1985847 | Crossref lookup | PASS |
| 19 | Earlier internal analysis exists, is not published externally, and is not cited | repository drafts `reports/v2/FINAL_SCIENTIFIC_VALIDITY_REPORT.md`, `paper/v2/FINAL_RESEARCH_DRAFT.md`; no DOI, arXiv id or venue found | repository search (no external record) | PASS (disclosed without citation); user may still wish to cite it if a publication exists |
| 20 | Earlier analysis reported ΔMCC −0.201 on the original labels | `reports/v2/FINAL_SCIENTIFIC_VALIDITY_REPORT.md` §2 | read | PASS-BY-READING |
| 21 | No human validation, held-out corpus or independent labels | manuscript Limitations; `reports/v2/review_package` (zero returned responses) | inspection | PASS |
| 22 | External run not blind; zero RELIC-only TP guaranteed; repository-clustered CI includes zero | `results/external/` | as reported in earlier sprint and recomputed by audit | PASS (as previously recorded; not re-run here) |
| 23 | Language-model run answered 155 of 180 pairs; the 25 unanswered are 21 CHANGING, 4 PRESERVING; worst case 0.603 vs text B 0.731 | `results/final/llm/matched_subset_v1/manifest.json`; `llm_bounds_dedup_loo.json` | script | PASS (no comparative claim made) |
| 24 | Category: Short paper, WIP with preliminary results | ResponsibleSE 2027 CFP (conf.researchr.org/home/icse-2027/responsiblese-2027) | web fetch | PASS (reasoning in GO_CRITERIA.md) |
| 25 | Page limit 4–6 for short papers; 6 pages used | CFP page; `main.pdf` | page count | PASS (references counted; conservative) |
| 26 | IEEE conference template | CFP text: "formatted according to the IEEE conference proceedings template" | class in `main.tex` | PASS |
| 27 | Double-blind | CFP: "Please don't include author names and identifying information in the paper" | text, PDF and figure metadata scan | PASS |
| 28 | Submission deadline and status | CFP: Fri 20 Nov 2026 AoE (UTC−12); HotCRP sign-in page: "Saturday Nov 21, 2026, 6:59:59 AM EST" (11:59 UTC) | web fetch; time check | OPEN until submitted; closes 11:59 UTC on 21 Nov 2026 |
| 29 | Camera-ready and notification dates | CFP: notification Fri 11 Dec 2026; camera-ready Fri 29 Jan 2027 | web fetch | PASS |

Summary: 24 PASS or PASS-BY-READING; 2 PASS with disclosed open part (17, 19); 1 OPEN that is a time constraint (28), not a content issue.
