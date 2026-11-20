# RELIC V2: negative empirical study (ResponsibleSE short paper, draft)

Title: *Benchmark and Oracle Reliability in Evaluating Semantic Change Detection for Legacy Software: A Negative Empirical Study*

## Contents
- `main.tex`: IEEEtran conference manuscript, anonymous. Compiles to 5 pages with tectonic.
- `main.pdf`: compiled output.
- `figures/fig1_mcc_and_overlap.pdf`: SemBench MCC across populations, and changing-case overlap.
- `figures/fig2_benchmark_composition.pdf`: mutually exclusive SemBench composition (180 pairs).
- `scripts/make_figures.py`: generates both figures from `results/recovery/stats_reanalysis.json` and `benchmarks/sembench/cases.jsonl`. Asserts the composition totals.
- `CLAIM_TO_EVIDENCE_AUDIT.md`: every substantive claim, its source file, status, and limitation.

## Rebuild
```
# from the repository root, after the statistics script has run
PYTHONPATH=src python reports/recovery/scripts/stats_reanalysis.py
python paper/RELIC_V2_PUBLICATION_FINAL/scripts/make_figures.py
cd paper/RELIC_V2_PUBLICATION_FINAL && tectonic main.tex
```

## Status
- Compiles with no errors. Five pages including references, within the 4–6 page range.
- Minor overfull boxes (2–3 pt) remain in the hypothesis table.
- Not yet checked against the venue's official template files or page rules. Those must be re-checked against the current ResponsibleSE call before submission.
- Anonymised: no author names, affiliations or repository links.

## Known open items
1. The Holm values for the SemBench headline differ between the two statistics reports. The paper reports the range and names the definitions. Reconcile before camera-ready.
2. The external run reproduced byte-for-byte in a clean clone (`reports/recovery/REPRODUCIBILITY_AUDIT.md`). The Docker build did not reproduce; the paper says so.
3. The appended-step generator defect is not yet in the defect register.
4. No human validation, held-out corpus or LLM baseline exists. The paper says so.
