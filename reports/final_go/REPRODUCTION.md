# Reproducing the numbers in the paper

Run from the root of the analysis archive (the repository layout is preserved). Python 3 with numpy; matplotlib for figures; tectonic for the PDF. Each command was run on 2026-11-21 and exited 0.

| Paper element | Command | Output |
|---|---|---|
| Table I (all detectors, MCC) and Table II (MCC, CIs, confusion counts) | `python3 reports/final/scripts/robustness_checks.py` and `python3 reports/final_go/bootstrap_reproduction.py` | `results/final/statistics/robustness_checks.json`, `results/final_go/bootstrap_original_method.json` |
| Exact cluster-swap p-values (0.015, 0.002, 0.010, 0.089) | `python3 reports/final/scripts/robustness_checks.py` | `results/final/statistics/robustness_checks.json` (key `cluster_swap`) |
| RQ2 complementarity (no RELIC-only true positives) | `python3 reports/final/scripts/complementarity_checks.py` | `results/final/statistics/complementarity_checks.json` |
| RQ3 decomposition and sensitivity | `python3 reports/final/scripts/l3_decomposition.py`, `step_name_sensitivity.py`, `bounds_and_dedup.py` | `results/final/statistics/*.json` |
| Deduplicated L1 gap, leave-one-program-out range, bounds | `python3 reports/final_go/llm_bounds_dedup_loo.py` | `results/final_go/llm_bounds_dedup_loo.json` |
| Paper numbers against outputs (text) | `python3 reports/final_go/verify_manuscript_text.py` | prints `failures: 0` |
| Paper numbers against outputs (tabular) | `python3 reports/final_go/verify_manuscript_numbers.py` | 32 PASS lines, `FAILURES: none` |
| Figures | `python3 paper/RELIC_V2_PUBLICATION_FINAL/scripts/make_figures.py` (run from the root) | `paper/RELIC_V2_PUBLICATION_FINAL/figures/*.pdf` |
| Manuscript | `cd paper/RELIC_V2_PUBLICATION_FINAL && tectonic main.tex` | `main.pdf`, 6 pages |

Inputs: `benchmarks/sembench/cases.jsonl` (180 pairs with labels and SHA-256 of both files), `results/sembench/predictions.jsonl` (frozen predictions of six detectors), `results/recovery/stats_reanalysis.json` (the repository's original published statistics, used to check the bootstrap).

Intervals: percentile cluster bootstrap over 16 base programs, 10,000 resamples, seed 20261004 (numpy default generator), reproduced by `bootstrap_reproduction.py`. JSON values are stored to four decimals; the text checker accepts a printed value within half a unit of the fourth decimal because a few values sit on a rounding tie.

Not included in this archive:
- The language-model run and its raw responses (not part of the paper's claim; see the Limitations section). The frozen subset files are included only to reproduce the bound in `llm_bounds_dedup_loo.py`.
- The Docker image (not built).
