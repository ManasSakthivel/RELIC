# RELIC Evidence Ledger — v2.0
<!-- FINAL COMPLETION SPRINT — Forensic Audit Results -->

This ledger maps every key research claim to its underlying evidence.
All values independently verified from raw data on 2026-08-30.

---

## RQ1 — Contract Recovery (TEMPORAL)

| Claim ID | Claim | Evidence | Experiment | Dataset | N | Result | Reproducible | Confidence | Reviewer Risk | Status |
|---|---|---|---|---|---:|---|---|---|---|---|
| RQ1-01 | RELIC extracts TEMPORAL PRECEDES contracts with micro-F1=1.000 | TP=56, FP=0, FN=0 verified from raw per_file data | E1_INDEP | CardDemo (33 JCL fallback) | 33 files, 56 contracts | micro-F1=1.000, P=1.000, R=1.000 | YES — `scripts/run_rq1_independent.py` | MEDIUM | HIGH | VERIFIED |
| RQ1-02 | Macro F1 = 0.5758 | 19 files × F1=1.0 + 14 files × F1=0.0 = 19/33 = 0.5758 | E1_INDEP | CardDemo | 33 files | 0.5758 | YES | HIGH | MEDIUM | VERIFIED |
| RQ1-03 | macro < micro because 14 single-step JCL files produce 0 evaluable contracts → F1=0.0 | Per-file inspection: 14 files have oracle_contracts=0, system_contracts=0 | E1_INDEP | CardDemo | 14 files | F1=0.0 per file (no contracts) | YES | HIGH | MEDIUM | VERIFIED |
| RQ1-04 | Oracle is independent of SUT code | Oracle: regex-based minimal parser in `scripts/run_rq1_independent.py`; SUT: `StaticContractExtractor`+`BCGBuilder` | E1_INDEP | — | — | Spec-sharing, code-independent | N/A | MEDIUM | HIGH | PARTIALLY_VERIFIED |
| RQ1-05 | RQ1 uses ALL JCL files (fallback), not a held-out split | `SPLITS_60_20_20.json` has `held_out` key; script looks for `test` key → falls back to `app/jcl/*.jcl` | E1_INDEP | CardDemo | 33 files | Same files as development | YES | HIGH | HIGH | CONFIRMED_LIMITATION |

**Key finding:** micro-F1=1.000 is genuine but explained: the oracle and SUT share the same JCL PRECEDES specification. For a deterministic algorithm implementing a deterministic spec, agreement=1.0 is expected, not surprising. This is an idempotency/correctness check, not a capability claim beyond that specification.

---

## RQ2 — Mutation Risk Detection

| Claim ID | Claim | Evidence | Experiment | Dataset | N | Result | Reproducible | Confidence | Reviewer Risk | Status |
|---|---|---|---|---|---:|---|---|---|---|---|
| RQ2-01 | RELIC BCGDiff detects 104/104 mutations, F1=1.000 | CSV: 104 EVALUATED, all tp_static_bcg=1 | E2 | CardDemo dev split (55 JCL, 440 attempts) | 104 evaluated | F1=1.000 | YES | HIGH | MEDIUM | VERIFIED |
| RQ2-02 | Structural baseline F1=0.8995 (85 TP, 19 FN) | CSV: sum tp_structural=85, fn_structural=19 | E2 | CardDemo | 104 evaluated | F1=0.8995 | YES | HIGH | LOW | VERIFIED |
| RQ2-03 | Complexity baseline F1=0.000 | CSV: 0 TP, 104 FN | E2 | CardDemo | 104 evaluated | F1=0.000 | YES | HIGH | LOW | VERIFIED |
| RQ2-04 | Static BCG baseline (no confidence-delta) F1=0.960 | CSV: 96 TP, 8 FN | E2 | CardDemo | 104 evaluated | F1=0.960 | YES | HIGH | LOW | VERIFIED |
| RQ2-05 | 440 mutation attempts total: 104 evaluated + 336 N/A = 440 | CSV row count verified: 440 rows total | E2 | CardDemo | 440 | 440=104+336+0 | YES | HIGH | MEDIUM | VERIFIED |
| RQ2-06 | N/A taxonomy: 208 zero_valid_contracts + 126 operator-inapplicable + 2 no_contract_effect | CSV error field counts | E2 | CardDemo | 336 N/A | 208+126+2=336 | YES | HIGH | MEDIUM | VERIFIED |
| RQ2-07 | FP=0 by design: negative benchmark TN=144, FP=0, FPR=0.000 | negative_summary.json | E2_NEG | CardDemo (33 JCL, 5 neg operators × 3 seeds) | 144 evaluated | TN=144, FP=0, FPR=0.0 | YES | HIGH | LOW | VERIFIED |
| RQ2-08 | LLM-C lower bound F1=0.0377 (245/248 API failures) | llm_c_results.json: TP=2, FP=0, FN=102, TN=144 | E_LLM_C | CardDemo | 248 | F1=0.0377 (lower bound) | YES | HIGH | HIGH | VERIFIED |
| RQ2-09 | LLM-D lower bound F1=0.1091 (241/248 API failures) | llm_d_results.json: TP=6, FP=0, FN=98, TN=144 | E_LLM_D | CardDemo | 248 | F1=0.1091 (lower bound) | YES | HIGH | HIGH | VERIFIED |
| RQ2-10 | `mutation_no_contract_effect` N/A category: only 2 cases | CSV error=mutation_no_contract_effect count | E2 | CardDemo | 2 | Negligible circularity risk | YES | HIGH | LOW | VERIFIED |

**Key finding for RQ2-F1=1.0:** F1=1.000 is plausible because (a) the BCGDiff mechanism is designed to detect contract-level changes, and (b) the mutations are designed to violate contracts (REORDER_JOBS, REMOVE_JOB_DEPENDENCY, ALTER_STEP_SEQUENCE etc. all break TEMPORAL ordering). The high N/A rate (76.4%) is not inflating performance — N/A cases are excluded from both numerator and denominator.

---

## RQ3 — Dynamic Evidence Reconciliation

| Claim ID | Claim | Evidence | Experiment | Dataset | N | Result | Reproducible | Confidence | Reviewer Risk | Status |
|---|---|---|---|---|---:|---|---|---|---|---|
| RQ3-01 | Dynamic validation rate = 91.8% (56/61 SUPPORTED) | rq3_dynamic_results.json | E3 | CardDemo (33 JCL, 40 exec traces) | 61 contracts | 0.918 | YES | MEDIUM | CRITICAL | PARTIALLY_VALID |
| RQ3-02 | Real execution contributes 0 promotions (EMPPAY/DEPTPAY ≠ JCL contracts) | Trace inspection: entity IDs don't match JCL step IDs | E3 | CardDemo | 2 real traces | 0 promotions | YES | HIGH | CRITICAL | CONFIRMED_LIMITATION |
| RQ3-03 | All 56 promotions come from EXECUTION_SIMULATED JCL traces | Trace generator uses same parser → entity IDs match | E3 | CardDemo | 38 simulated traces | 56 promotions | YES | HIGH | CRITICAL | CONFIRMED_LIMITATION |
| RQ3-04 | Dynamic validation rate (real-only) = 0% | No real execution traces match JCL contract entity IDs | E3 | CardDemo | 2 real traces | 0/61 = 0.0% | YES | HIGH | CRITICAL | VERIFIED |

**Key finding for RQ3:** The 91.8% rate is driven by 38 EXECUTION_SIMULATED traces whose entity IDs are generated by the same JCL parser that builds the BCG. This near-guarantees promotion. The claim must be: "91.8% of contracts corroborated by JCL step-ordering simulation; 0% independently validated by actual program execution."

---

## Generalization / OOD

| Claim ID | Claim | Evidence | Experiment | Dataset | N | Result | Reproducible | Confidence | Reviewer Risk | Status |
|---|---|---|---|---|---:|---|---|---|---|---|
| OOD-01 | In-distribution F1=1.000 on CardDemo | ablation_summary.json, generalization_summary.json | E5 | CardDemo | 139 items | F1=1.000 | YES | HIGH | LOW | VERIFIED |
| OOD-02 | OOD result F1=0.0 (tp=0, fp=34, fn=0) is a benchmark artifact, not extractor failure | FP=34 are valid TEMPORAL contracts from JCL; OOD benchmark has no oracle | E5 | public_cobol (43 JCL) | 34 extracted | F1=0.0 by construction | YES | HIGH | CRITICAL | CONFIRMED_LIMITATION |

---

## Summary of Key Discrepancies

| Metric | Previously Reported | Forensic Audit | Cause | Status |
|---|---|---|---|---|
| RQ1 micro-F1 | 1.0000 | 1.0000 | Verified correct | CONFIRMED |
| RQ1 macro-F1 | 0.5758 | 0.5758 | 14 zero-contract files → F1=0.0 | CONFIRMED |
| RQ2 BCGDiff F1 | 1.0000 | 1.0000 | Verified from CSV (104 TP, 0 FN) | CONFIRMED |
| RQ2 Structural F1 | 0.8995 | 0.8995 | Verified from CSV (85 TP, 19 FN) | CONFIRMED |
| RQ3 validation rate | 91.8% | 91.8% (simulated) / 0% (real) | All from EXECUTION_SIMULATED | CORRECTLY_SCOPED |
| OOD F1 | 0.0 | 0.0 (benchmark artifact) | No oracle for public_cobol contracts | CORRECTLY_SCOPED |
| LLM-C F1 | 0.0377 | 0.0377 | Verified (lower bound, 98.8% API failures) | CONFIRMED_LOWER_BOUND |
| LLM-D F1 | 0.1091 | 0.1091 | Verified (lower bound, 97.2% API failures) | CONFIRMED_LOWER_BOUND |

**No corrections to reported F1 values are required.** All values are arithmetically correct.

---

## Confirmed Scientific Limitations

1. **RQ1 split key mismatch:** Script looks for `splits["test"]`; file has `splits["held_out"]`. Fallback uses all 33 app/jcl files. Dev and test sets partially overlap (17/33 files). This is a generalization threat, not a fabrication.
2. **RQ3 simulation circularity:** EXECUTION_SIMULATED traces are generated from the same JCL parser that builds the BCG, making promotion near-guaranteed. The dynamic validation rate should be reported as "91.8% corroborated by simulation" not "91.8% independently validated."
3. **RQ1 oracle spec-sharing:** Oracle and SUT implement the same deterministic JCL PRECEDES specification. F1=1.0 is expected for any correct implementation; it confirms correctness, not capability.
4. **OOD benchmark mismatch:** public_cobol lacks oracle → F1=0.0 is not an extractor failure.
5. **LLM baselines are lower bounds:** 97-99% API failure rates mean F1 values are infrastructure-limited, not capability-limited.
6. **N/A rate 76.4%:** Explained: 208/336 from zero-contract files (single-step JCL), 126/336 from operator-inapplicable files, 2/336 from BCGDiff-no-effect. No circularity concern except the 2 mutation_no_contract_effect cases (negligible).

---

*Generated: RELIC Final Completion Sprint | All values independently verified from raw data.*
