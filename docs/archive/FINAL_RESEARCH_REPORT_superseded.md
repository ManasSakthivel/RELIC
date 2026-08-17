# FINAL RESEARCH REPORT
# LEGACY-CONTRACT: Execution-Grounded Behavioral Contract Recovery for Legacy Batch Modernization Risk Detection

**Status:** Research platform complete. Empirical validation partially blocked by external dependencies.  
**Date:** 2025-07 (post-remediation)  
**Platform:** Python 3.11 / GnuCOBOL 3.2.0 / AWS CardDemo dataset  

---

## Executive Summary

LEGACY-CONTRACT is a research platform for the automatic recovery, dynamic validation, and change-risk detection of implicit behavioral contracts embedded in COBOL/JCL batch systems. The platform formalizes behavioral obligations as a Behavioral Contract Graph (BCG), a six-tuple `BCG = (V, E, C, P, D, Γ)`, and evaluates the BCG against a fault-grounded mutation benchmark derived from documented real-world modernization failures.

**What is established:** The static BCG pipeline detects all 109 evaluated mutations on the CardDemo benchmark (F1=1.000 vs. structural baseline F1=0.889). The discriminating finding is that confidence-delta detection (`diff.modified`) catches `ALTER_ERROR_BRANCH` mutations — a class of behavioral weakening — invisible to both structural analysis and BCG-without-confidence-delta baselines. 49.2% of extracted contracts are dynamically validated by available execution traces.

**What is not yet established:** Independent contract-recovery accuracy (requires Level-3 human annotation). Full H2 evaluation (requires LLM API). H3 FPR reduction (requires GT-negative execution). Full CardDemo dynamic execution (requires DB2/CICS stubs).

**Negative mutation benchmark:** Five semantically-preserving negative operators implemented (`negative_mutations.py`). Ground-truth TN infrastructure in place — apply to all CardDemo BCGs to get ~50 TN cases and make H3 FPR testable without external data.

**Parser coverage:** JCL 55/55 (100%), COBOL 44/44 (100%) files parsed successfully. 136 EXEC cards, 547 DD cards, 44 PROCEDURE DIVISIONs recognized. See `results/parser_coverage.json`.

**Publication outlook:** Ready for workshop/preprint submission with current results, clearly scoped to CardDemo. MSR/ICSME-level submission requires Level-3 annotation and LLM baselines.

---

## Problem

Legacy mainframe batch systems encode implicit behavioral contracts distributed across JCL and COBOL artifacts:

- **Temporal contracts**: job step ordering obligations (`A ≺ B`)
- **Resource contracts**: dataset availability obligations (`produces(A,R) ≺ consumes(B,R)`)
- **Control-flow contracts**: return-code propagation guards (`RC(A) > T → ¬execute(B)`)

These contracts are never explicitly specified. When systems are modernized (migrated to cloud orchestration, translated to Java/Python, restructured for microservices), these obligations become invisible risks. Production failures caused by this class of error are well-documented and non-trivial.

---

## Research Gap

Prior work addresses parts of this problem separately:

- **Daikon** infers data-value invariants from OO execution traces — different contract type and domain
- **GIST** infers behavioral FSMs from traces — no static evidence, no cross-artifact scope, no reconciliation
- **Ammons et al.** mine temporal API protocols from OO traces — OO level, not batch/job level
- **Pessoa et al.** perform COBOL semantic diff — no temporal contracts, no JCL, no dynamic evidence
- **SYMDIFF** performs semantic diff at statement level — requires SMT encoding, infeasible for large COBOL

No prior system addresses **cross-artifact JCL+COBOL behavioral obligations** with **provenance-aware representation**, **static/dynamic reconciliation**, and **fault-grounded mutation evaluation** simultaneously.

---

## Research Questions

| RQ | Question | H | Status |
|---|---|---|---|
| RQ1 | Can temporal contracts be recovered with sufficient precision and recall? | H1: F1≥0.70, P≥0.75 | BLOCKED_FOR_INDEPENDENT_VALIDATION |
| RQ2 | Does BCG analysis improve risk detection vs. baselines? | H2: BCG+dynamic F1 > best baseline | UNTESTABLE_AS_STATED (ceiling + Baseline D missing) |
| RQ3 | Does dynamic evidence reduce false positives? | H3: FPR reduction ≥10pp | NOT_TESTABLE (FPR undefined in closed-set benchmark) |

---

## BCG Formalization

```
BCG = (V, E, C, P, D, Γ)
```

- **V**: typed entities — JOB, STEP, PROGRAM, DATASET, JCL_DD, COPYBOOK, etc.
- **E**: structural relations — CALLS, READS, WRITES, PRODUCES, CONSUMES, MUST_PRECEDE, etc.
- **C**: behavioral contracts — (contract_type, subject_id, predicate, object_id, natural_language)
- **P**: provenance — (source_artifact, source_location, extraction_method, evidence_items)
- **D**: dynamic observations — ExecutionEvents linked to entities via normalized artifact_id
- **Γ**: validation metadata — ConfidenceVector × ValidationState (7-state machine)

### Validation States

```
STATIC_CANDIDATE → STATIC_DYNAMIC_SUPPORTED   (real execution confirms)
                 → STATIC_DYNAMIC_CONFLICT    (execution contradicts)
                 → NOT_OBSERVED               (no execution coverage)
                 → UNRESOLVED                 (partial or ambiguous)
HUMAN_VALIDATED                               (terminal — human authority)
GROUND_TRUTH                                  (terminal — oracle authority)
```

### Scientific Invariants (Enforced in Code + Tests)

- `SYNTHETIC_STATIC ≠ EXECUTION` (SI-01): synthetic traces cannot promote to STATIC_DYNAMIC_SUPPORTED
- `NOT_OBSERVED ≠ CONTRADICTED` (SI-06): absence of evidence is not contradiction
- `HUMAN_VALIDATED` is terminal (SI-07): automated reconciliation cannot demote it
- `return_code=None` means "not captured", not RC=0 (SI-11)
- Entity IDs are deterministic: `MD5(artifact_path + entity_type + name)` (SI-10)

---

## Architecture

```
JCL / COBOL / Copybook artifacts
        ↓
JCLParser / COBOLParser / CopybookParser
        ↓
IRGraph (entities + relations)
        ↓
StaticContractExtractor
        ↓
BCG (contracts + provenance)
        ↓                          ↓ (optional)
BCGDiff + RiskDetector      ReconciliationEngine
        ↓                          ↓
RQ2 mutation results         RQ3 dynamic results
```

### Artifact Mapping (C1 Fix — now wired)

```
ExecutionEvent (artifact_id = program name)
        ↓
ArtifactMapper.resolve(artifact_id)
        ↓
EXACT → replace with step entity_id
AMBIGUOUS → keep original, log (never guess)
MISSING → keep original
PROC_EXPANDED → replace with resolved step entity_id
        ↓
ReconciliationEngine (now uses canonical entity IDs)
```

---

## Static Contract Recovery

Extraction rules:
- **TEMPORAL**: For each JCL EXEC step pair (A, B) where B follows A, extract `A PRECEDES B`
- **RESOURCE**: For DD with `DISP=(NEW,CATLG)` on step A and `DISP=OLD` on step B reading same DSN → `A produces(R) before B consumes(R)`
- **CONTROL_FLOW**: For `COND=(T,OP,stepname)` → `RC(stepname) OP T → ¬execute(step)` contract

All contracts carry: source_artifact, source_location, extraction_method=DETERMINISTIC, at least one EvidenceItem.

---

## Dynamic Evidence

Sources:
- `EXECUTION`: Real GnuCOBOL execution (2 traces: EMPPAY, DEPTPAY)
- `EXECUTION_SIMULATED`: JCL parser-derived step ordering (11 traces: all major CardDemo JCL files)
- `SYNTHETIC_STATIC`: Statically derived (3 traces: excluded by SI-01 from promotion)

**IMPORTANT:** GnuCOBOL execution is NOT z/OS execution. All evidence is labeled accordingly. "Mainframe production execution" is not claimed.

### CardDemo Environment Limitation

| Component | Status |
|---|---|
| Standalone COBOL programs (EMPPAY, DEPTPAY) | EXECUTED |
| JCL step ordering | EXECUTION_SIMULATED |
| CardDemo COBOL programs (CBACT01C, etc.) | UNEXECUTABLE_IN_CURRENT_ENVIRONMENT (requires DB2/CICS/IMS) |
| z/OS execution | UNAVAILABLE |

---

## Reconciliation Algorithm

For each contract `c ∈ BCG.contracts`:
1. Find events for `c.subject_id` and `c.object_id` via artifact_mapping
2. Pre-compute `all_synthetic` flag before reconciliation (SI-01)
3. Apply predicate-specific reconciliation:
   - PRECEDES: timestamp ordering check
   - PRODUCES_BEFORE_CONSUMES: produce-event before consume-event
   - MUST_NOT_FOLLOW_ON_ERROR: B does not execute after A's error RC
4. If `all_synthetic` and outcome=SUPPORTED → demote to NOT_OBSERVED (SI-01)
5. Update contract.validation_state

**Conflict taxonomy:**
- STATIC_FALSE_POSITIVE: static extraction wrong
- DYNAMIC_INCOMPLETE: execution path not covered
- HIDDEN_STATE: environment dependency
- INSTRUMENTATION_LIMIT: trace capture missed events
- PARSER_LIMIT: static parser structural gap

---

## Mutation Framework

| Operator | Category | Applicable | Applicable Rate | Static BCG F1 | Structural F1 |
|---|---|---|---|---|---|
| REORDER_JOBS | F1 | 30 | 54% | 1.000 | 0.9655 |
| REMOVE_JOB_DEPENDENCY | F1 | 30 | 54% | 1.000 | 1.000 |
| ALTER_STEP_SEQUENCE | F1 | 30 | 54% | 1.000 | 0.9655 |
| REMOVE_DATASET_INIT | F2 | 1 | 2% | 1.000 | 1.000 |
| CHANGE_DATASET_NAME | F2 | 1 | 2% | 1.000 | 0.000 |
| ALTER_FILE_DEPENDENCY_ORDER | F2 | 1 | 2% | 1.000 | 0.000 |
| SUPPRESS_RC_CHECK | F3 | 8 | 15% | 1.000 | 0.000 |
| ALTER_ERROR_BRANCH | F3 | 8 | 15% | 1.000 | 0.000 |
| **Total** | | **109** | **24.8%** | **1.000** | **0.8878** |

N/A rate: 331/440 = 75.2% — expected given CardDemo's demonstration-level JCL complexity.

**Benchmark type:** CLOSED-SET. All mutations violate contracts. No ground-truth negatives. Precision=1.0 is by design; FNR comparisons are the scientifically informative metric.

---

## Experimental Design

| Parameter | Value |
|---|---|
| Primary dataset | AWS CardDemo (Apache 2.0, commit main 2024-Q4) |
| Split | 60/20/20 (train/dev/test) |
| Random seed | 42 (locked in experiment_lock.json) |
| Bootstrap iterations | 10,000 |
| Python version | 3.11 |
| GnuCOBOL | 3.2.0 |

---

## Baselines

| Baseline | Description | Status | F1 |
|---|---|---|---|
| A | Structural dependency analysis (program slicing) | COMPLETE | 0.8878 |
| B | Static complexity metrics | COMPLETE | 0.0000 |
| C | LLM-only (GPT-4) | BLOCKED_EXTERNAL_DEPENDENCY | [RESULT_PENDING] |
| D | Dependency graph + LLM | BLOCKED_EXTERNAL_DEPENDENCY | [RESULT_PENDING] |
| E | Static BCG without MODIFIED detection | COMPLETE | 0.9619 |
| Proposed | Static BCG with confidence-delta | COMPLETE | 1.0000 |

---

## Results

### RQ1: Contract Recovery

F1=1.000 on Level-2 DETERMINISTIC benchmark. **SELF-CONSISTENCY ONLY.**  
Level-3 independent annotation: NOT CONDUCTED. `benchmark/annotations/` is empty.  
H1 status: **BLOCKED_FOR_INDEPENDENT_VALIDATION**

### RQ2: Modernization Risk Detection (Static Conditions)

| Condition | F1 | vs. Proposed |
|---|---|---|
| Baseline B (complexity) | 0.000 | −1.000 |
| Baseline A (structural) | 0.888 | −0.112 |
| Baseline E (BCG, broken-only) | 0.962 | −0.038 |
| Proposed (BCG, full) | 1.000 | — |

Key finding: `ALTER_ERROR_BRANCH` operator — Proposed F1=1.00 vs. Baseline E F1=0.00 vs. Baseline A F1=0.00. Confidence-delta detection is the architectural discriminator.

H2 status: **UNTESTABLE_AS_STATED** (Baseline D missing; F1=1.0 ceiling)

### RQ3: Dynamic Evidence Value

Dynamic validation rate: **49.2%** (31/63 contracts STATIC_DYNAMIC_SUPPORTED)  
STATIC_DYNAMIC_CONFLICT: **1** (CONTROL_FLOW contract contradicted by GnuCOBOL trace)  
NOT_OBSERVED: **31** (DB2/CICS environment limitation)

H3 status: **NOT_TESTABLE** (FPR undefined; no ground-truth negatives)

---

## Ablation Study

| Condition | F1 | Delta |
|---|---|---|
| A1: Full static BCG (proposed) | 1.000 | — |
| A3: Structural edges only (Baseline A) | 0.888 | −0.112 |
| A4: Complexity metrics only (Baseline B) | 0.000 | −1.000 |
| A5: BCG without MODIFIED detection (Baseline E) | 0.962 | −0.038 |
| A6: BCG without confidence-delta (same as A5) | 0.962 | −0.038 |
| A2, A7: LLM conditions | [RESULT_PENDING] | — |

**Key finding:** The single architectural discriminator between A1 and A5 is `diff.modified` (confidence-delta detection for `ALTER_ERROR_BRANCH` mutations).

---

## Generalization

| System | GT Available | F1 | Interpretation |
|---|---|---|---|
| CardDemo (in-dist.) | Level-2 (circular) | 1.000 | Self-consistency |
| OMP public COBOL (OOD) | NOT BUILT | 0.000 | GT gap, not extraction failure |

Generalization evaluation status: **BLOCKED_BY_GROUND_TRUTH** — OMP GT not constructed.

---

## Statistical Analysis

| Test | Status | Note |
|---|---|---|
| Bootstrap CI (n=10,000, seed=42) | IMPLEMENTED | CI=[1.00,1.00] for F1=1.0 (degenerate — homogeneous eval) |
| Mann-Whitney U | IMPLEMENTED, NOT FIRED | f1_scores list empty (aggregate scalars only) |
| Rank-biserial r | IMPLEMENTED | Ready when per-instance scores populated |
| Bonferroni (n=5) | IMPLEMENTED | Correctly n=5, not n=15 |
| FPR | null everywhere | Open-set; no ground-truth negatives |

---

## Threats to Validity

**Internal:** parser errors (medium risk), dynamic instrumentation limits (medium), mutation co-design (low — taxonomy derived before BCG finalized), LLM nondeterminism (low for deterministic components).

**External:** single primary dataset (HIGH — CardDemo is demo-scale); COBOL/JCL focus only; public datasets simpler than enterprise.

**Construct:** contract–behavior correspondence (requires Level-3 annotation); mutation realism (all operators empirically grounded).

**Dynamic:** incomplete execution coverage; GnuCOBOL ≠ z/OS; trace fidelity medium.

---

## Limitations

1. **L1:** Single primary dataset (CardDemo). All results must be scoped to "CardDemo-scale systems."
2. **L2:** GnuCOBOL ≠ z/OS. Dynamic evidence is NOT z/OS production data.
3. **L3:** Paper 1 scope: temporal, resource, control-flow contracts only.
4. **L4:** Confidence scores are evidence-strength scores, not calibrated probabilities.
5. **L5:** LLM nondeterminism — core BCG results are deterministic and unaffected.
6. **L6:** Level-3 annotation subjectivity — not yet conducted.
7. **L7:** F1=1.0 on closed-set benchmark is a design consequence, not an independently measured achievement.
8. **L8:** H2 and H3 are structurally untestable with the current evaluation design.

---

## Novelty

**Defensible narrow claim:** To our knowledge, LEGACY-CONTRACT is the first system to formalize implicit behavioral obligations across both JCL and COBOL artifacts simultaneously, with per-contract provenance, an explicit static/dynamic reconciliation taxonomy, and a fault-grounded mutation evaluation framework derived from documented real-world modernization failures.

**We do NOT claim novelty for:** behavioral contracts (Meyer 1992), dynamic invariant inference (Daikon), trace-based specification mining (Ammons, GIST, Lo), semantic differencing (SYMDIFF, Pessoa), LLM code analysis.

---

## Reproducibility

```bash
# Install
pip install -e .

# Run all experiments (static)
make reproduce-paper1

# Run specific experiments
python3.11 scripts/run_rq2.py          # RQ2 static conditions
python3.11 scripts/run_dynamic_reconciliation.py  # RQ3

# Run tests
python3.11 -m pytest tests/ -q        # 295 tests should pass
```

**Blocked reproduction:** LLM baselines require `OPENAI_API_KEY`. Full CardDemo dynamic experiment requires DB2/CICS environment. Level-3 annotation requires qualified human domain experts.

---

## Future Work

1. **Level-3 human annotation** — use `scripts/export_blinded_annotation.py`, recruit 2 JCL/COBOL domain experts, follow `docs/annotation_protocol_final.md`
2. **LLM baselines C and D** — set `OPENAI_API_KEY`, run `scripts/run_rq2.py --conditions llm,dep_llm`
3. **Ground-truth negative set** — create JCL mutations that do NOT violate contracts; enables H3 FPR test
4. **z/OS execution traces** — minimum 10 traces from z/OS sandbox to reduce EXECUTION_SIMULATED dominance
5. **Additional COBOL corpora** — build GT for OMP COBOL to support generalization claims
6. **Reformulate H2** — reframe as FPR reduction or extended benchmark with true negatives
7. **Paper 2–4** — data contracts, state contracts, error contracts (BCG extensions)

---

## Conclusion

LEGACY-CONTRACT demonstrates that behavioral semantic representation captures modernization obligations invisible to structural analysis. The `ALTER_ERROR_BRANCH` finding — confidence-delta detection catching 8 mutations missed by all other baselines — is a genuine architectural insight with practical implications for modernization engineers.

The platform is complete. The annotation infrastructure is ready. The dynamic pipeline is wired. The manuscript is synchronized with actual results. The remaining work is data collection (human annotation, LLM baseline execution, z/OS traces) rather than platform development.

---

*FINAL_RESEARCH_REPORT.md — authoritative research summary for LEGACY-CONTRACT.*  
*Generated post-remediation. All numerical claims sourced from frozen result files in `results/`.*
