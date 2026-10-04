# RELIC — Final Scientific Status
<!-- AUTHORITATIVE FINAL STATE | Final Closure Sprint | 2026-08-30 -->
<!-- This document supersedes all prior status documents. -->

---

## Research Questions

| RQ | Statement | Status |
|---|---|---|
| RQ1 | Can RELIC extract TEMPORAL behavioral contracts from JCL with high precision and recall against an independent oracle? | ANSWERED — with qualification |
| RQ2 | Does BCG confidence-delta differencing outperform structural dependency analysis in detecting modernization risk? | ANSWERED — on applicable cases |
| RQ3 | Do execution traces corroborate statically extracted contracts? | ANSWERED — simulation consistency only |

---

## Contributions

1. **A static analysis framework (RELIC)** that extracts behavioral contracts (TEMPORAL, RESOURCE, CONTROL_FLOW) from COBOL/JCL legacy systems using a Behavioral Contract Graph (BCG) and confidence-vector scoring.
2. **A confidence-delta differencing mechanism (BCGDiff)** that detects behavioral guard weakening across versions — catching violations that structural dependency analysis cannot see (demonstrated by ALTER_ERROR_BRANCH operator).
3. **A reproducible evaluation benchmark** for JCL behavioral contract extraction and risk detection (CardDemo, 55 JCL files, 440 mutation attempts, 8 operators).
4. **A scientific integrity methodology** including independent oracle, pre-registered hypotheses, split-based evaluation, sensitivity analysis, and adversarial self-review.

---

## Evaluated Systems

| System | Role | JCL Files | Programs | License | Source |
|---|---|---|---|---|---|
| AWS CardDemo | Primary (all RQs) | 55 | 44 COBOL | Apache 2.0 | github.com/aws-samples/aws-mainframe-modernization-carddemo |
| COBOL Programming Course | OOD only (no oracle) | 43 | 7 | Apache 2.0 | github.com/openmainframeproject/cobol-programming-course |

**Second subject system:** SECOND SYSTEM NOT SCIENTIFICALLY VALIDATED. No publicly available JCL+COBOL corpus provides sufficient multi-step JCL with behavioral guards and independent oracle feasibility. See `docs/secondary_system_selection.md`.

---

## Benchmark

| Parameter | Value |
|---|---|
| Primary dataset | AWS CardDemo |
| Held-out split (RQ1) | 11 JCL files, 21 TEMPORAL contracts, ZERO overlap with dev/validation |
| Dev split (RQ2) | 55 JCL files |
| Mutation attempts | 440 total (8 operators × 55 files) |
| Evaluated mutations | 104 (N/A rate: 76.4%) |
| N/A taxonomy | 208 zero-contract + 126 operator-inapplicable + 2 no-contract-effect |
| Negative mutations | 144 (semantics-preserving) |
| Dynamic traces (RQ3) | 40 total: 2 real GnuCOBOL + 38 EXECUTION_SIMULATED + 3 SYNTHETIC_STATIC (excluded) |
| Benchmark version | Level-2 DETERMINISTIC (no Level-3 human annotation) |
| Frozen commit | fed30a8 (split fix), b78b385 (final correction) |

---

## Oracle

| Aspect | Value |
|---|---|
| Oracle type | INDEPENDENT_REFERENCE_REGEX_IMPLEMENTATION |
| Code independence | YES — regex-based oracle vs IR-based SUT; zero shared code |
| Specification sharing | YES — both implement JCL PRECEDES specification (steps execute in textual order) |
| Scope | TEMPORAL contracts only |
| Limitation | Spec-sharing makes F1=1.0 expected for any correct deterministic implementation |
| Human annotation | NOT CONDUCTED (blocked — external dependency) |

---

## RQ1 Results

**Scope:** TEMPORAL PRECEDES contracts, 11 held-out JCL files (zero dev overlap), CardDemo.

| Metric | Value | Confidence Label |
|---|---|---|
| Micro-Precision | 1.0000 | DESCRIPTIVE — spec-fidelity |
| Micro-Recall | 1.0000 | DESCRIPTIVE — spec-fidelity |
| Micro-F1 | 1.0000 | DESCRIPTIVE — spec-fidelity |
| Macro-F1 | 0.5455 | ILLUSTRATIVE — n=11, MDD=42pp |
| 95% Bootstrap CI (macro-F1) | [0.2727, 0.8182] | Width=55pp (bimodal: 6 files F1=0, 5 files F1=1) |
| Total TP | 21 | — |
| Total FP | 0 | — |
| Total FN | 0 | — |
| H1 verdict | SUPPORTED | Conditional on scope qualification |

**Key qualification:** Micro-F1=1.000 is a specification-fidelity result, not implicit-contract discovery. Oracle and SUT implement the same deterministic JCL step-ordering rule. F1=1.0 is guaranteed by construction for any correct implementation of a deterministic specification.

**Paper framing must say:** "RELIC correctly implements TEMPORAL contract extraction per the JCL step-ordering specification, achieving micro-F1=1.000 on a 11-file held-out split."

---

## RQ2 Results

**Scope:** BCG confidence-delta detection on 8 mutation operators, CardDemo dev split.

### Core Result (Applicable Only)

| Condition | F1 | TP | FN | Confidence |
|---|---|---|---|---|
| **BCGDiff proposed** | **1.0000** | **104** | **0** | INFERENTIAL, Wilson CI [0.965, 1.000] |
| Static BCG (no delta) | 0.9600 | 96 | 8 | INFERENTIAL |
| Structural dependency | 0.8995 | 85 | 19 | INFERENTIAL |
| LLM-only (lower bound†) | 0.0377 | 2 | 102 | DESCRIPTIVE — lower bound only |
| Dep+LLM (lower bound†) | 0.1091 | 6 | 98 | DESCRIPTIVE — lower bound only |
| Complexity metrics | 0.0000 | 0 | 104 | INFERENTIAL |

† 245/248 and 241/248 API calls failed. Infrastructure lower bounds — not valid capability comparisons.

### Sensitivity Analysis (N/A Treatment)

| N/A Treatment | F1 | N (denominator) | Label |
|---|---|---|---|
| Applicable only (default) | 1.000 | 104 | INFERENTIAL |
| Zero-contract as FN | 0.500 | 312 | ILLUSTRATIVE |
| All N/A as FN | 0.382 | 544 | ILLUSTRATIVE |

**Paper must report all three rows.**

### Statistical Test

BCGDiff vs Structural dependency (McNemar, paired observations): b=19, c=0, χ²=17.05, p<0.0001. Significant at Bonferroni-corrected α=0.01. MWU is incorrect for paired data.

### Negative Benchmark (Semantics-Preserving Mutations)

TN=144, FP=0, FPR=0.000, Specificity=1.000. Note: FPR=0 is a closed-set design property, not an open-world measurement.

### Key Discriminating Finding

`ALTER_ERROR_BRANCH` and `SUPPRESS_RETURN_CODE_CHECK`: BCGDiff F1=1.0 (n=8 each), Structural=0.0, Static-BCG=0.0. These operators change COND= threshold values without altering step topology — invisible to structural analysis. n=8 (ILLUSTRATIVE, domain-concentrated in CREADB21.jcl and TRANEXTR.jcl).

---

## LLM Baseline

| Item | Value |
|---|---|
| Model | Groq llama-3.3-70b-versatile |
| Prompt version | v2_blinded (v1 discarded — semantic leak) |
| Temperature | 0.0, seed=42 |
| LLM-C successful calls | 3/248 |
| LLM-C errors | 245/248 (HTTP 429 — Groq 100K TPD quota) |
| LLM-C F1 | 0.0377 (LOWER BOUND ONLY) |
| LLM-D successful calls | 7/248 |
| LLM-D errors | 241/248 |
| LLM-D F1 | 0.1091 (LOWER BOUND ONLY) |
| Claim validity | CANNOT claim RELIC outperforms LLMs — baselines never ran properly |
| Required paper treatment | Remove from main table; present in appendix as lower-bound investigation |

---

## OOD

| Item | Value |
|---|---|
| OOD dataset | public_cobol (43 JCL files, COBOL Programming Course) |
| Contracts extracted | 34 TEMPORAL |
| Oracle available | NO |
| OOD F1 | 0.0 (34 FP, 0 TP, 0 FN — by construction: no oracle) |
| Interpretation | BENCHMARK ARTIFACT — not extractor failure; 34 extracted contracts are structurally valid but unverifiable |
| Claim validity | CANNOT present OOD F1=0.0 as generalization failure |
| Required paper treatment | "Cross-system evaluation not possible — oracle unavailable for public_cobol" |

---

## Dynamic Validation

| Metric | Value | Label |
|---|---|---|
| JCL simulation corroboration rate | 56/61 = 91.8% | DESCRIPTIVE — pipeline consistency |
| STATIC_DYNAMIC_CONFLICT | 1/61 = 1.6% | — |
| NOT_OBSERVED | 4/61 = 6.6% | — |
| Real execution validation rate | 0/61 = 0.0% | CONFIRMED — EMPPAY/DEPTPAY entity IDs don't match JCL contracts |
| NOT_OBSERVED monotonicity | Verified safe — never becomes CONTRADICTED as traces increase | — |

**Critical disclosure:** All 56 SUPPORTED promotions come from EXECUTION_SIMULATED traces generated by the same JCL parser that builds the BCG. Entity ID match is near-guaranteed by construction. This is simulation circularity, not independent dynamic validation. The 91.8% figure must be labeled "JCL step-ordering simulation corroboration rate."

---

## Second-System Results

**SECOND SYSTEM NOT SCIENTIFICALLY VALIDATED**

No second system evaluation was conducted. See `docs/secondary_system_selection.md` for full candidate audit.

---

## Mutation Results

**Covered under RQ2.** Summary for mutation methodology:
- 8 operators: REORDER_JOBS, REMOVE_JOB_DEPENDENCY, ALTER_STEP_SEQUENCE (F1/TEMPORAL), REMOVE_DATASET_INIT, CHANGE_DATASET_NAME, ALTER_FILE_DEPENDENCY_ORDER (F2/RESOURCE), SUPPRESS_RETURN_CODE_CHECK, ALTER_ERROR_BRANCH (F3/CONTROL_FLOW)
- F1/TEMPORAL operators: n=28-29 each (INFERENTIAL)
- F3/CONTROL_FLOW operators: n=8 each (ILLUSTRATIVE)
- F2/RESOURCE operators: n=1 each (ILLUSTRATIVE/ANECDOTAL)
- N/A taxonomy: 208 zero-contract + 126 operator-inapplicable + 2 no-contract-effect

---

## Statistics

| Claim | Test | Result | Label | Valid |
|---|---|---|---|---|
| BCGDiff > Structural (RQ2) | McNemar (corrected — not MWU) | χ²=17.05, p<0.0001, α_Bonferroni=0.01 | INFERENTIAL | YES |
| Macro-F1 CI (RQ1) | Bootstrap n=10,000, seed=42 | [0.2727, 0.8182] verified from raw data | ILLUSTRATIVE | YES |
| BCGDiff F1=1.0 CI (RQ2) | Wilson interval | [0.965, 1.000] | INFERENTIAL | YES |
| ALTER_ERROR_BRANCH (n=8) | — | ILLUSTRATIVE only | — | LABELED CORRECTLY |
| n=1 operators | — | ANECDOTAL only | — | LABELED CORRECTLY |
| RQ3 91.8% | Descriptive proportion | n=61 | DESCRIPTIVE | YES |
| Power analysis (RQ1, n=11) | MDD calculation | ~42pp — underpowered for macro-F1 inference | — | YES |

**Critical correction:** Mann-Whitney U test is incorrect for RQ2 (paired observations). McNemar's test is the correct test. Both yield the same directional conclusion; McNemar result is stronger (p<0.0001).

---

## Failure Analysis

See `docs/final_failure_analysis.md` for complete taxonomy.

Top failures by impact on paper:
- **F-04 (CRITICAL):** RQ3 simulation circularity — all 56 SUPPORTED from same-parser traces → rename RQ3
- **F-07 (HIGH):** LLM infrastructure failure → remove from main table
- **F-09 (HIGH):** N/A rate 76.4% → report all three sensitivity F1 values
- **F-10 (HIGH):** OOD no oracle → do not present as generalization failure
- **F-01 (MEDIUM):** Macro-F1 diluted by 6 zero-contract files → explain bimodal distribution

---

## Limitations

(Scoped and final. All 14 items from evidence_ledger.md v4.0.)

1. RQ1 split key fix (resolved)
2. RQ3 simulation circularity (framing issue — no new experiments possible)
3. RQ1 oracle spec-sharing (defensible — requires framing fix in paper)
4. OOD benchmark no oracle (framing issue — no fix possible)
5. LLM baselines are infrastructure lower bounds (framing issue — remove from main table)
6. N/A rate 76.4% with three-tier sensitivity (paper must report all three)
7. RQ1 Level-2 only, no human annotation (blocked — external)
8. Second system not available (blocked — no public corpus; no internet access)
9. LLM root cause: Groq 100K TPD quota (documented)
10. F2/F3 operator n=1 (illustrative only)
11. ALTER_ERROR_BRANCH n=8 domain-clustered
12. McNemar correction applied (was MWU — incorrect test)
13. Statistical claim labels: micro-F1=DESCRIPTIVE, macro-F1=ILLUSTRATIVE, n=104 INFERENTIAL
14. PROC expansion not implemented; 0 IF/ENDIF in CardDemo (disclosed — scope boundary)

---

## Generalization Verdict

**INSUFFICIENT EVIDENCE**

Single subject system (CardDemo). No second system evaluated. OOD result is oracle artifact, not generalization measurement. All claims must be scoped to "CardDemo-scale demonstration systems."

---

## Reproducibility

| Component | Status |
|---|---|
| Test suite | 305/305 passing, 1 benign warning |
| Primary reproduction | `make reproduce-paper1` / `scripts/run_rq1_independent.py` |
| Dependency lock | `requirements.lock` present |
| Docker | `Dockerfile` + `docker-compose.yml` present |
| Secrets | `.env.example` provided; no secrets in repository |
| Absolute paths | None identified (all paths relative to workspace) |
| Seed | 42 throughout |
| Bootstrap n | 10,000 |
| Second-system reproduction | N/A — no second system evaluated |

---

## Reviewer Risks

(Ranked by severity and fixability for paper writing)

| Risk | Reviewer | Severity | Fix Required |
|---|---|---|---|
| Single system — no generalization | A, B, C | REJECT (full track) | Venue choice; honest scope in abstract |
| RQ3 "execution-grounded" framing | A, B, C | DEAL_BREAKER | Remove from title/abstract |
| RQ1 F1=1.0 framing | A, B, C | MAJOR_REVISION | Reframe as spec-fidelity |
| LLM baselines broken | A, C | MAJOR_REVISION | Remove from main table |
| N/A sensitivity not prominent | A, C | MAJOR_REVISION | Three-row F1 in main table |
| PROC/COND= scope | B | MAJOR_REVISION (enterprise) | Threats to Validity entry |
| n=8 domain-clustered | A, B | MAJOR_REVISION | Label illustrative |
| Statistical labels | A | MAJOR_REVISION | Apply DESCRIPTIVE/ILLUSTRATIVE/INFERENTIAL |

---

## Claims We CAN Make

1. RELIC correctly implements TEMPORAL contract extraction per the JCL step-ordering specification (micro-F1=1.000, macro-F1=0.5455 [0.27, 0.82], n=11 held-out files).
2. BCGDiff detects 104/104 applicable mutations with F1=1.000 — Wilson CI [0.965, 1.000] — outperforming structural analysis (F1=0.900) and static BCG without confidence-delta (F1=0.960).
3. BCGDiff specifically detects behavioral guard weakening (ALTER_ERROR_BRANCH, SUPPRESS_RETURN_CODE_CHECK) that structural analysis cannot see — the core discriminating contribution.
4. McNemar's test confirms BCGDiff vs Structural is statistically significant (p<0.0001, α_Bonferroni=0.01).
5. The BCG correctly captures 144 semantics-preserving mutations without false positives (TN=144, FP=0, FPR=0.000).
6. JCL step-ordering simulation corroborates 91.8% of statically extracted contracts (simulation consistency, not independent execution).
7. NOT_OBSERVED contracts do not become CONTRADICTED as trace coverage increases (monotonicity confirmed).
8. The methodology is fully reproducible from a clean repository checkout.

---

## Claims We CANNOT Make

1. ❌ "RELIC discovers implicit behavioral contracts" — RQ1 is specification-fidelity, not discovery.
2. ❌ "91.8% of contracts are dynamically validated" — this is simulation corroboration, not independent execution validation. Real execution rate is 0%.
3. ❌ "RELIC substantially outperforms LLM approaches" — LLM baselines never ran (97-99% API failure).
4. ❌ "RELIC generalizes across COBOL/JCL systems" — single system, no second-system evaluation.
5. ❌ "OOD F1=0.0 demonstrates generalization failure" — oracle unavailable; F1=0.0 is a benchmark artifact.
6. ❌ "The system is execution-grounded" — execution groundedness requires real execution traces, which are 0/61.
7. ❌ "The F1=1.0 result on mutations demonstrates superior detection capability" — without sensitivity analysis disclosure (three-tier F1 required).
8. ❌ "ALTER_ERROR_BRANCH detection generalizes beyond CardDemo transaction-batch domain" — n=8, domain-clustered.

---

## Final Status

**COMPLETE WITH EXPLICIT LIMITATIONS — READY FOR PAPER WRITING**

The remaining weaknesses require either: (a) unavailable external resources (human annotators, second system, z/OS environment, paid LLM API), or (b) paper-writing framing decisions that are now fully specified. All feasible experimental and engineering work within the current sprint is complete. The evidence base is honest, self-consistent, and reproducible. The paper writing phase can begin.

**Venue recommendation:** ICSE/FSE tool track or ICSME short paper as immediate submission. Full research track after second-system acquisition or human annotation study.

---

*Created: RELIC Final Closure Sprint | 2026-08-30*
*Supersedes: docs/final_hostile_review.md, docs/experimental_methods_audit.md (for paper-writing guidance)*
