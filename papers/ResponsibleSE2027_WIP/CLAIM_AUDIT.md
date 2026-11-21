# Claim audit (final)

Status: VERIFIED (recomputed from a source file), VERIFIED-READING (code or report), PROPOSED (framework), NOT DONE (future work).

| # | Claim | Evidence | Status |
|---|---|---|---|
| 1 | 180 pairs; 93 CHANGING, 87 PRESERVING | cases.jsonl | VERIFIED |
| 2 | 25 byte-identical pairs, 15 CHANGING and 10 PRESERVING | SHA-256 equality | VERIFIED |
| 3 | 21 duplicate groups covering 46 pairs; 5 groups with conflicting labels | cases.jsonl | VERIFIED |
| 4 | Oracle disagrees with 28 author labels (15 identical, 13 not); 1 abstention | validation_status and oracle_agrees fields | VERIFIED |
| 5 | 13 non-identical disagreements and one abstention remain without independent adjudication | as 4 | VERIFIED |
| 6 | 10 of 93 CHANGING labels returned EQUIVALENT (8 distinct edits): 4 SHR→OLD labels (3 distinct), 1 record-count label, 5 CATLG→KEEP labels (4 distinct) | cases.jsonl and judge output; catalogue treatment in simulate.py lines 548–550 | VERIFIED (reading); whether these are label errors or oracle blindness is not decided |
| 7 | Oracle treats CATLG and KEEP alike | simulate.py: DELETE and UNCATLG only affect the catalogue | VERIFIED-READING |
| 8 | 55 of 78 CHANGING pairs missed on L1 (16 disposition, 12 condition, 12 return-code, 10 dataset, 5 reorder) | predictions and cases category field | VERIFIED |
| 9 | Table 2 MCC, intervals and Δ | bootstrap_original_method.json; tie-safe check | VERIFIED |
| 10 | Exact cluster p = 0.015, 0.002, 0.010, 0.089 | robustness_checks.json | VERIFIED |
| 11 | L3 exact test does not reject (p = 0.089); bootstrap interval excludes zero | Table 2 | VERIFIED |
| 12 | Gap −0.17 to −0.34; point-estimate sign unchanged | Table 2 | VERIFIED |
| 13 | Leave-one-program-out −0.364 to −0.313; deduplicated −0.338 | llm_bounds_dedup_loo.json | VERIFIED |
| 14 | RELIC V2 has no true positive that text B misses | complementarity_checks.json | VERIFIED |
| 15 | LLM: L1 worst 0.603, best 0.890, against text B 0.731; 21 of 25 unanswered are CHANGING | llm_bounds_dedup_loo.json; manifest | VERIFIED (no comparative claim made) |
| 16 | 16 base programs; one contributes 30 pairs; four corpus programs contribute seven pairs | base_id recount | VERIFIED |
| 17 | 151 pairs marked validated by oracle and written argument (same group) | validation_status | VERIFIED |
| 18 | Earlier internal analysis reached ΔMCC −0.2008 on original labels; unpublished | reports/v2/FINAL_SCIENTIFIC_VALIDITY_REPORT.md; no external record | VERIFIED-READING |
| 19 | Review package has no returned responses | repository record | VERIFIED |
| 20 | Literature statements | Crossref and arXiv records; title-level | PARTLY VERIFIED (see REFERENCE_VERIFICATION.md) |
| 21 | Framework's five dimensions | derived from items 1–17 | PROPOSED |
| 22 | Framework dimensions 3 and 5 incomplete | no review, no consequence analysis | NOT DONE (disclosed) |
| 23 | Decomposition step +0.024 | l3_decomposition.json steps (unrounded 0.02446); not cited in paper | VERIFIED (not cited); artifact field L3_recomputed_gap is a defect |
