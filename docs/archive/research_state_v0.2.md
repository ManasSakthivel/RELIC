# Research State Audit v0.2
## LEGACY-CONTRACT — Comprehensive Implementation Status

**Version:** 0.2.0  
**Date:** 2025  
**Purpose:** Answer the 10 research state questions before making v0.2 improvements

---

## 1. WHAT HAS ACTUALLY BEEN IMPLEMENTED?

### Core Infrastructure — IMPLEMENTED ✓

| Component | Module | Status | Notes |
|---|---|---|---|
| IR model (V, E) | `ir/model.py` | ✓ Complete | EntityType, RelationType, IREntity, IRRelation, IRGraph |
| BCG model | `bcg/model.py` | ✓ Complete | BCG = (V,E,C,P,D,Γ), BCGDiff |
| BCG builder | `bcg/builder.py` | ✓ Complete | Pipeline: IR → contracts → observations → reconcile |
| Contract model | `contracts/model.py` | ✓ Complete | ContractType, ValidationState, ConfidenceVector, ProvenanceRecord |
| Dynamic event model | `dynamic_analysis/model.py` | ✓ Complete | ExecutionEvent, ExecutionTrace, EventSourceType |
| JCL parser | `parsers/jcl_parser.py` | ✓ Complete (with gaps) | JOB/EXEC/DD/COND; missing GDG, multi-COND |
| COBOL parser | `parsers/cobol_parser.py` | ✓ Complete | PROGRAM-ID/CALL/PERFORM/READ/WRITE/COPY |
| Copybook parser | `parsers/copybook_parser.py` | ✓ Complete | Level/PICTURE/USAGE/OCCURS/REDEFINES |
| Static extractor | `static_analysis/extractor.py` | ✓ Complete | Temporal, Resource, ControlFlow extractors |
| Reconciliation engine | `reconciliation/engine.py` | ✓ Complete (with bugs) | TEMPORAL/RESOURCE/CONTROL_FLOW reconciliation |
| GnuCOBOL adapter | `dynamic_analysis/gnucobol_adapter.py` | ✓ Complete | Parses NDJSON execution logs |
| Mutation engine | `mutations/engine.py` | ✓ Complete | F1/F2/F3 operators, 8 operators total |
| Risk detector | `risk/detector.py` | ✓ Complete | Full evidence chain, RiskReport |
| Restoration engine | `restoration/engine.py` | ✓ Complete | Structural suggestions only |
| Evidence sufficiency | `evidence/sufficiency.py` | ✓ Complete | E0-E7 framework |
| BCG ingester | `ingestion/ingester.py` | ✓ Complete | JCL/COBOL/copybook detection and parsing |
| Dataset downloader | `datasets/download.py` | ✓ Complete | CardDemo + OMP COBOL |
| Evaluation metrics | `evaluation/metrics.py` | ✓ Complete | Bootstrap CI, Cohen's d, Mann-Whitney U |
| Benchmark framework | `evaluation/benchmark.py` | ✓ Complete | GroundTruthLevel, IAA, lock/unlock |
| Experiment runner | `evaluation/runner.py` | ✓ Complete | RQ1/RQ2/RQ3/ablation/generalization |
| Baseline A (structural) | `baselines/structural/` | ✓ Complete | Structural dependency analysis |
| Baseline C (LLM) | `baselines/llm_only/` | ✓ Complete | GPT-4 based with provenance |
| FastAPI backend | `api/main.py`, `api/models.py` | ✓ Complete | 10 REST endpoints |
| React UI | `ui/src/` | ✓ Complete | 6 views with D3.js graph |
| Test suite (39 tests) | `tests/` | ✓ 39/39 passing | Unit/integration/regression |

### Identified Gaps — NOT YET IMPLEMENTED

| Gap | Severity | Where Needed |
|---|---|---|
| Scientific integrity tests | HIGH | `tests/scientific/` |
| Confidence weights sum to 1.0 | MEDIUM | `config/confidence_weights.yaml` |
| Referential integrity enforcement in BCG | MEDIUM | `bcg/model.py` |
| Asymmetric evidence handling in reconciliation | HIGH | `reconciliation/engine.py` |
| SYNTHETIC_STATIC guard in reconciliation | HIGH | `reconciliation/engine.py` |
| New reconciliation states (INSUFFICIENT_EVIDENCE, ENVIRONMENT_DEPENDENT) | MEDIUM | `reconciliation/engine.py` |
| Impact radius computation | HIGH | `risk/detector.py` |
| BCGDiff MODIFIED category | MEDIUM | `bcg/model.py` |
| Baselines B, D, E | MEDIUM | `baselines/` |

---

## 2. WHAT HAS ACTUALLY BEEN TESTED?

### Passing Tests (39/39)

- JCL parser: JOB/STEP/program extraction, DISP=NEW/OLD (PRODUCES/CONSUMES), MUST_PRECEDE ordering, COND extraction, comment handling, continuation merging
- COBOL parser: PROGRAM-ID, CALL, PERFORM, READ, COPY, SELECT, fixed/free format
- Contract model: creation, validation states, confidence aggregate, provenance tracking
- Reconciliation: SUPPORTED, CONTRADICTED, NOT_OBSERVED (confirmed ≠ CONTRADICTED), confidence update, HUMAN_VALIDATED protection
- Regression: 5 known contracts always detectable (temporal, resource, control-flow, COBOL CALL, ordering chain)
- Integration: full pipeline JCL+COBOL → IR → BCG → trace → reconciliation

### NOT YET TESTED

- Scientific integrity invariants (see Phase 5)
- Impact radius computation (not yet implemented)
- BCGDiff MODIFIED contracts (not yet implemented)
- Baseline B, D implementations
- Experiment runner end-to-end
- Dataset downloader (requires network)
- UI components (no browser tests)

---

## 3. WHAT HAS ACTUALLY BEEN EMPIRICALLY VALIDATED?

**NONE of the primary research claims have been empirically validated yet.**

All experiment results are marked [RESULT_PENDING].

What IS empirically grounded:
- The failure taxonomy (F1-F7) has documented real-world evidence sources
- The mutation operators trace to empirical failure categories
- Parser correctness is tested on synthetic inputs (not CardDemo)

---

## 4. WHAT REMAINS HYPOTHETICAL?

Everything that depends on experimental results:
- H1: F1 ≥ 0.70 on deterministic contracts — **hypothetical**
- H2: BCG outperforms baselines — **hypothetical**
- H3: Dynamic evidence reduces FPR — **hypothetical**
- The claim that execution-grounded BCG is better than static BCG — **hypothetical**
- Confidence score calibration — **hypothetical**
- Generalization across systems — **hypothetical**

---

## 5. STRONGEST SCIENTIFIC CONTRIBUTIONS

1. **BCG as formal IR for cross-artifact behavioral obligations** — novel representation; justified by domain gap; formally specified
2. **Static/dynamic reconciliation with explicit conflict taxonomy** — operationally precise; includes NOT_OBSERVED≠CONTRADICTED; environment validity distinction
3. **Empirically grounded fault model** — failure taxonomy traced to real-world sources; each mutation cites evidence
4. **Per-contract provenance audit trail** — enables challenge, reproducibility, and trust calibration
5. **Evidence sufficiency framework (E0-E7)** — enables ablation study; tests whether dynamic evidence adds value

---

## 6. ENGINEERING-ONLY CONTRIBUTIONS

- React UI with D3.js visualization — engineering deliverable; not a research contribution
- FastAPI backend — infrastructure
- Dataset downloader — infrastructure
- GnuCOBOL trace adapter — infrastructure (necessary for empirical work)

---

## 7. BIGGEST SCIENTIFIC RISKS

| Risk | Likelihood | Severity | Mitigation |
|---|---|---|---|
| H3 fails (dynamic evidence doesn't help) | Medium | HIGH | Negative result is reportable; design allows honest reporting |
| H2 fails (dep+LLM matches BCG) | Medium | HIGH | H2 falsification would be a significant finding itself |
| Benchmark circularity | HIGH if protocol not followed | CRITICAL | Benchmark construction protocol (experimental_design_v2.md) |
| GnuCOBOL/z/OS differences invalidate dynamic evidence | Low for Paper 1 scope | HIGH | Formal equivalence characterization (dynamic_evidence_v2.md) |
| CardDemo too simple | Medium | HIGH | Generalization experiment; explicit scoping |

---

## 8. ASSUMPTIONS NEEDING EVIDENCE

| Assumption | Required Evidence | Status |
|---|---|---|
| JCL COND semantics are correctly extracted | Test on CardDemo JCL with known COND patterns | NOT DONE |
| GnuCOBOL execution represents batch mainframe timing | Formal equivalence characterization | DOCUMENTED |
| F1-F3 mutations represent real failures | git timestamps confirming taxonomy predates BCG | NOT VERIFIED |
| Confidence weights are appropriate | Ablation A4 (no confidence model) | EXPERIMENT NOT RUN |
| CardDemo has sufficient contract density | Contract density characterization of CardDemo | NOT DONE |

---

## 9. WHAT SHOULD REMAIN UNCHANGED

- BCG formal model (V, E, C, P, D, Γ) — correct structure, needs minor invariant additions
- Three paper 1 contract types (TEMPORAL, RESOURCE, CONTROL_FLOW) — correct scope
- Five baselines (A-E) — correct comparison set; add F (Daikon) as stretch goal
- GnuCOBOL instrumentation approach — best available public dynamic evidence
- Evidence sufficiency E0-E7 framework — well-designed, scientifically sound
- 39 existing tests — all must continue to pass after any changes

---

## 10. WHAT DESERVES RESEARCH EXPANSION

In priority order:

1. **Impact radius computation** — formally defined; must be implemented for risk detection to be complete
2. **BCGDiff MODIFIED contracts** — improves behavioral diff completeness
3. **Daikon baseline (F)** — directly answers "is this just Daikon?" objection
4. **GnuCOBOL/z/OS equivalence characterization** — formally done in docs; needs implementation of ENVIRONMENT_DEPENDENT tagging
5. **Confidence weight calibration** — requires ground truth; design for future work
6. **Asymmetric evidence fix in reconciliation** — high-value fix; low implementation cost
