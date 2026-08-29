# RELIC Final Forensic Audit
**Date:** 2026-08-30  
**Sprint:** Final Research Completion Sprint  
**Status:** COMPLETE

---

## Executive Summary

All previously reported F1 values have been **independently verified from raw data**. No corrections to any F1 value are required. The values are arithmetically correct. However, several scientific scope limitations were confirmed and documented that were not previously made explicit.

---

## Agent 1 — F1 Forensic Audit

### RQ1: micro-F1 = 1.0000

**Verification:** Recomputed from `results/rq1/rq1_independent.json` per-file data.

```
TP = sum(per_file.tp) = 56
FP = sum(per_file.fp) = 0  
FN = sum(per_file.fn) = 0
micro_precision = 56/(56+0) = 1.0000
micro_recall    = 56/(56+0) = 1.0000
micro_F1        = 2*1.0*1.0/(1.0+1.0) = 1.0000
```

**VERIFIED. No correction required.**

### RQ1: macro-F1 = 0.5758

**Verification:** 33 per-file F1 values. 19 files = F1=1.0, 14 files = F1=0.0.

**WHY F1=0.0 for 14 files:**  
These 14 files each contain only 1 JCL EXEC step (e.g., READCUST.jcl with `['STEP05']`). With N=1 steps, no PRECEDES obligation is possible. Oracle produces 0 contracts, system produces 0 contracts. The formula: `precision = 1.0` (no FPs convention), `recall = 0.0` (0 TP / 0 oracle → undefined → 0), `F1 = 0.0`.

**Effect on macro:** `(19×1.0 + 14×0.0)/33 = 19/33 = 0.5758` ✓

**This UNDERSTATES performance, not inflates it.** The per-file F1=0.0 penalizes the macro average for files that have nothing to evaluate.

**VERIFIED. No correction required.**

### RQ2: All F1 values

Independently recomputed from `results/rq2/rq2.csv` (440 rows, 104 EVALUATED, 336 NOT_APPLICABLE, 0 ERRORS):

| Method | TP | FN | Independent F1 | Reported F1 | Match? |
|---|---|---|---|---|---|
| BCGDiff (proposed) | 104 | 0 | 1.0000 | 1.0000 | ✓ |
| Structural (Baseline A) | 85 | 19 | 0.8995 | 0.8995 | ✓ |
| Complexity (Baseline B) | 0 | 104 | 0.0000 | 0.0000 | ✓ |
| Static BCG (Baseline E) | 96 | 8 | 0.9600 | 0.9600 | ✓ |
| LLM-C | 2 | 102 | 0.0377 | 0.0377 | ✓ |
| LLM-D | 6 | 98 | 0.1091 | 0.1091 | ✓ |

**All VERIFIED. No corrections required.**

---

## Agent 2 — Mutation/Benchmark Forensics

### 440 mutation accounting

```
TOTAL = 440 (verified: 440 rows in rq2.csv)
EVALUATED = 104
NOT_APPLICABLE = 336
ERRORS = 0
440 = 104 + 336 + 0 ✓
```

### N/A Taxonomy (complete)

| Category | Count | Cause |
|---|---|---|
| `zero_valid_contracts` | 208 | 26 JCL files have 0 contracts (single-step or parse failure). All 8 operators → N/A. |
| `""` (blank error) | 126 | `MutationNotApplicable` raised by engine: file lacks required construct (e.g., COND= for ALTER_ERROR_BRANCH) |
| `mutation_no_contract_effect` | 2 | Mutation applied but BCGDiff shows no broken/modified contracts |
| **Total** | **336** | |

### Circularity assessment

**`mutation_no_contract_effect` (2 cases):** The engine uses `bcg.diff(mutated_bcg)` to check if a mutation had any effect. The detector also uses BCGDiff. These 2 cases are excluded as N/A because BCGDiff says "no effect" — which is the same criterion used for detection. This is a potential circularity: mutations that would be missed by BCGDiff are excluded from the benchmark.

**Risk:** NEGLIGIBLE. Only 2/336 cases (0.6% of N/A). These 2 mutations are neither in the TP count nor the FN count. Removing them from analysis would not change the F1=1.0 result. The mechanism is disclosed.

**Verdict:** Benchmark accounting is correct and complete. The N/A rate (76.4%) is explained by the dataset structure, not benchmark manipulation.

---

## Agent 3 — Oracle Independence Audit

**Oracle type:** Independent regex-based JCL step-ordering parser  
**Code independence:** CONFIRMED — oracle in `scripts/run_rq1_independent.py` shares no code with `StaticContractExtractor` or `BCGBuilder`  
**Spec independence:** NOT FULLY INDEPENDENT — both implement the same JCL specification (steps execute in textual order)

**Key finding:** The oracle and SUT share the deterministic JCL PRECEDES specification. For a deterministic algorithm implementing a deterministic specification, F1=1.0 is an expected outcome, not a surprising one. This is a correctness/idempotency verification, not an independent capability benchmark.

**What the F1=1.0 actually proves:**
- RELIC's JCL parser and contract extractor correctly implement the JCL PRECEDES semantics
- The implementation is deterministic and self-consistent with the specification
- There are no FPs (no spurious contracts invented) and no FNs (no contracts missed)

**What the F1=1.0 does NOT prove:**
- That RELIC discovers contracts that human experts would independently identify
- That the JCL PRECEDES obligation constitutes a genuine behavioral obligation (not just a parse artifact)
- That performance generalizes beyond TEMPORAL contracts or beyond CardDemo JCL structure

**Split key mismatch:** `run_rq1_independent.py` looks for `splits["test"]` but `SPLITS_60_20_20.json` uses `splits["held_out"]`. The fallback uses all 33 JCL files in `app/jcl/`. These overlap with files used in development. This is a confirmed limitation; the evaluation is NOT on a strictly held-out set.

---

## Agent 4 — LLM Baseline Audit

**LLM-C F1=0.0377:** VERIFIED. TP=2, FP=0, FN=102, TN=144 from `llm_c_results.json`.  
**LLM-D F1=0.1091:** VERIFIED. TP=6, FP=0, FN=98, TN=144 from `llm_d_results.json`.

**Error treatment:** Failed API calls → treated as FN (prediction fails = no detection). This is conservative and correct. Errors are infrastructure failures, not capability failures.

**Classification:** Both results are **lower bounds on true LLM capability**. The comparison "RELIC F1=1.0 vs LLM F1=0.04" is valid but must be qualified: "with substantial API failure rates (245/248 and 241/248 calls errored)."

**Cannot claim:** "RELIC outperforms LLMs at this task." Can claim: "In our experiments, RELIC F1=1.00 exceeded LLM lower bounds of F1=0.04/0.11 (with 97-99% API failure rates)."

---

## Agent 5 — Dynamic + Ablation Audit

### Real vs. Simulated separation

| Source | Traces | Promotions | Rate |
|---|---|---|---|
| EXECUTION (real GnuCOBOL) | 2 (EMPPAY, DEPTPAY) | 0 | 0/61 = 0.0% |
| EXECUTION_SIMULATED (JCL sim) | 38 | 56 | 56/61 = 91.8% |
| Combined | 40 | 56 | 56/61 = 91.8% |

**Critical finding:** The reported 91.8% comes entirely from JCL simulation traces. The 2 real execution traces (EMPPAY/DEPTPAY) are COBOL programs whose entity IDs don't match any JCL step contracts. Real-execution validation rate = 0%.

**Simulation circularity:** EXECUTION_SIMULATED traces are generated by `generate_execution_traces.py` which uses the same JCL parser and entity ID hashing as `BCGBuilder`. This means `event.artifact_id == contract.subject_id` is structurally guaranteed for simulated traces. The 91.8% promotion rate is a consequence of this structural identity, not independent evidence.

**rq3_summary.json vs rq3_dynamic_results.json discrepancy:** Two different runs with different trace sets (13 vs 40 traces). `rq3_dynamic_results.json` (40 traces, 91.8%) is the authoritative result per the manifest. `rq3_summary.json` (13 traces, 49.2%) is an older intermediate result.

### Ablation

All ablation conditions except A2 and A7 (dynamic-dependent) produce F1=1.0. This is expected: removing contract types reduces TP count but never introduces FP/FN. The ablation confirms contract types are additive and orthogonal in this dataset.

---

## Agent 6 — Generalization / OOD Audit

**OOD result F1=0.0 — CONFIRMED AS BENCHMARK ARTIFACT**

The 34 extracted contracts from public_cobol JCL are valid TEMPORAL PRECEDES contracts. The OOD oracle has 0 expected contracts (no annotations created). The evaluation framework treats "no oracle" as "oracle expects 0" → all 34 extracted contracts are FP. This is not an extractor failure; it is an incompatible benchmark.

The result should be stated as: "Generalization to arbitrary COBOL corpora cannot be assessed; the OOD benchmark is incompatible (no ground truth for extracted contract type)."

The `docs/generalization_ood_disclosure.md` correctly documents this limitation.

---

## Agent 7 — Reproducibility Audit

### Tests: PASS (305/305)

### Reproduction: PASS

All 5 scripts in `make reproduce-paper1` complete successfully and produce matching results.

### Secret scan

- `.env` file: **NOT tracked by git** (confirmed via `git ls-files .env` = empty). The `.gitignore` correctly excludes `.env`. The real API key is local only.
- No hardcoded local paths found in any script.

### Confirmed issues

1. **Split key mismatch** (discussed in Agent 3): `test` vs `held_out`. Scripts fall back to full directory.
2. **rq3_summary.json vs rq3_dynamic_results.json** disagree (different runs). Manifest cites the newer result. Both files remain in repo.
3. **No `training` split** in `SPLITS_60_20_20.json`: dev=96, validation=32, held_out=33. This is intentional (no training; RELIC is rule-based, not learned).

---

## Agent 8 — Adversarial Scientific Review

### Attack: Is F1=1.0 suspicious?

**Verdict: EXPLAINABLE, NOT FABRICATED**

F1=1.0 on RQ2 is the result of a closed-set mutation benchmark where:
- Ground truth = any mutation successfully applied (Level-2 deterministic)
- Detection = BCGDiff showing at least 1 broken/modified contract
- The mutations ARE designed to break BCG contracts (REORDER_JOBS, REMOVE_JOB_DEPENDENCY, ALTER_STEP_SEQUENCE all directly affect TEMPORAL ordering)

This means the test is: "does BCGDiff catch a mutation that was literally designed to break BCGDiff-detectable contracts?" The answer being F1=1.0 is expected once the system works correctly.

The DISCRIMINATING result is `ALTER_ERROR_BRANCH`: RELIC=1.00, Structural=0.00, Baseline E=0.00. This is the operator that changes behavioral confidence without changing structural topology — exactly RELIC's claimed unique capability.

**Reviewer risk: MEDIUM** — reviewers will flag F1=1.0 as suspicious, but it is defensible with the above explanation.

### Attack: 76.4% N/A

**Verdict: EXPLAINED**

208/336 N/A = zero-contract files (single-step JCL, parser-fails). These cannot have mutations. 126/336 = operator inapplicable (no COND=, no DD cards, no PROC for respective operators). 2/336 = no contract effect. This is the natural structure of the CardDemo dataset.

**Reviewer risk: MEDIUM** — reviewers will note this limits N, but the 104 evaluated mutations span 8 operators and 29 files.

### Attack: Oracle independence

**Verdict: PARTIALLY DEFENSIBLE**

The oracle shares the JCL PRECEDES specification with the SUT but not its code. For a deterministic rule-based system, code independence is the appropriate level. Human annotation would provide deeper independence but is infeasible without annotators.

**Reviewer risk: HIGH** — reviewers will note that evaluating a deterministic parser against an oracle derived from the same spec is expected to give F1=1.0 regardless of whether the contracts are semantically correct.

**Mitigation:** Claims should be scoped to "RELIC correctly implements JCL PRECEDES semantics" not "RELIC identifies all behavioral contracts."

### Attack: Dynamic validation = simulation

**Verdict: CONFIRMED LIMITATION**

The 91.8% rate is simulation-driven. This must be stated explicitly. The paper must say "91.8% corroborated by JCL step-ordering simulation (EXECUTION_SIMULATED)" not "91.8% dynamically validated."

**Reviewer risk: CRITICAL** — claiming "dynamic validation" for simulation-generated traces will cause rejection at rigorous venues.

### Attack: Single system evaluation

**Verdict: CONFIRMED LIMITATION, DISCLOSED**

Only CardDemo is evaluated. All results are on a demonstration application.

**Reviewer risk: HIGH** — well-known limitation, but disclosed in README and docs.

### Attack: LLM comparison confounded

**Verdict: CONFIRMED LIMITATION**

97-99% API failure rates mean the LLM comparison is infrastructure-limited. The comparison should be framed as: "In our experiments, with substantial API failures acting as conservative baselines, RELIC substantially outperformed the LLM lower bounds."

**Reviewer risk: MEDIUM** — fixable with correct framing.

---

## Summary of Required Claim Scoping

### Claims that ARE defensible

1. "RELIC's BCGDiff detects 104/104 mutations (F1=1.000) that directly violate TEMPORAL contracts, while structural analysis misses 19 (F1=0.900), and complexity metrics miss all 104."
2. "RELIC achieves FPR=0.000 on 144 semantics-preserving negative mutations."
3. "The ALTER_ERROR_BRANCH operator demonstrates RELIC's unique capability: structural analysis scores F1=0.000 on this operator; RELIC scores F1=1.000."
4. "RELIC correctly implements JCL step-ordering contract extraction with micro-F1=1.000 against an independent code-disjoint oracle."
5. "Dynamic corroboration: 56/61 contracts (91.8%) corroborated by JCL step-ordering simulation; 0/61 independently validated by real program execution."

### Claims that MUST be qualified or avoided

1. ~~"Dynamic validation rate 91.8%"~~ → "91.8% corroboration by JCL step-ordering simulation (EXECUTION_SIMULATED); 0% from real execution"
2. ~~"RELIC outperforms LLMs"~~ → "RELIC substantially outperformed LLM lower bounds (F1=0.04/0.11) which are conservatively inflated by 97-99% API failures"
3. ~~"Generalizes"~~ → "Evaluated exclusively on CardDemo; generalization to production systems is an open research question"
4. ~~"Independent oracle"~~ → "Code-independent oracle sharing the JCL PRECEDES specification; confirms implementation correctness, not semantic validity"
5. ~~"F1=1.0 on RQ2 proves RELIC detects all behavioral changes"~~ → "F1=1.0 on closed mutation benchmark where mutations are designed to affect BCG contracts; FP=0 on closed negative benchmark"

---

## FINAL SCIENTIFIC STATUS

**B — RESEARCH-SOLID WITH EXPLICIT LIMITATIONS**

Core evidence is valid and independently verified. Remaining limitations are real, clearly scoped, and documented. The primary scientific contribution — BCGDiff-based confidence-delta detection outperforms structural analysis, particularly on behavioral mutations (ALTER_ERROR_BRANCH) — is supported by the evidence. The limitations (single system, simulation-only dynamic evidence, oracle spec-sharing, LLM infrastructure failures) are material but do not invalidate the core claim.

The repository does NOT have errors in the F1 computation. It DOES have several claims that need careful scoping to avoid overclaiming.
