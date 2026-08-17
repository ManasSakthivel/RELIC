# FINAL PROJECT STATE — LEGACY-CONTRACT

> Last updated: 2026-08-15 | Run by: empirical validation pipeline
> All experimental numbers sourced from results/*.json, results/*.csv

---

## Implementation
**DONE**

Core pipeline fully implemented:
- JCL + COBOL parser → IR → StaticContractExtractor → BCGBuilder → ReconciliationEngine → BCGDiff → RiskDetector
- 8 mutation operators (F1/F2/F3 taxonomy)
- 5 baselines (A=structural, B=complexity, C=llm_only stub, D=dep_llm stub, E=static_bcg)
- Evaluation framework (benchmark, metrics, bootstrap CI, runner)
- 265/265 tests pass: `PYTHONPATH=src:. python3 -m pytest tests/ -q`

---

## Scientific Integrity
**DONE**

- 48 scientific integrity rules enforced (docs/integrity_audit_v2.md)
- Configuration locked: results/experiment_lock.json (2026-08-14T17:00:28Z, seed=42)
- No post-hoc threshold tuning
- All results sourced from executable code and saved artifacts
- GT circularity acknowledged explicitly in all reports

---

## Dataset
**DONE**

- CardDemo (AWS, Apache-2.0): 58 JCL, 85 COBOL, 15 copybooks — 158 artifacts
- Public COBOL/OMP (Apache-2.0): 43 JCL, 104 COBOL, 18 copybooks — 165 artifacts
- Strict 60/20/20 dev/validation/held-out splits
- Manifest: results/dataset_manifest.json

---

## Ground Truth
**PARTIAL**

- Level-2 DETERMINISTIC: 463 items (139 positive, 324 negative) — COMPLETE
- Level-1 (real z/OS execution oracle): NOT AVAILABLE (requires mainframe)
- Level-3 (human annotation): NOT ATTEMPTED — annotation protocol documented
- **Circularity threat**: Level-2 GT built by same extractor family — F1=1.0 is idempotency, not behavioral correctness

---

## Dynamic Evidence
**PARTIAL**

- GnuCOBOL 3.2.0 available ✓
- 16 traces: 2 real EXECUTION (EMPPAY, DEPTPAY), 11 EXECUTION_SIMULATED, 3 SYNTHETIC_STATIC (excluded)
- Reconciliation achieved: 31/63 contracts SUPPORTED (49.2%), 1 CONFLICT, 31 NOT_OBSERVED
- Blocked: CardDemo COBOL requires DB2/CICS/IMS runtime not available in GnuCOBOL environment

---

## RQ1 — Contract Recovery
**HYPOTHESIS_SUPPORTED** *(with circularity caveat)*

- F1=1.0000, P=1.0000, R=1.0000 on Level-2 DETERMINISTIC GT
- 139/139 contracts recovered (TEMPORAL=113, RESOURCE=3, CONTROL_FLOW=23)
- H1 (F1≥0.70, P≥0.75): **SUPPORTED**
- **Caveat**: Level-2 GT is circular. This proves idempotency, not behavioral correctness.
- Requires Level-3 human annotation before non-circular validity claim.

---

## RQ2 — Risk Detection
**PARTIALLY_SUPPORTED** *(static conditions only; dynamic pending)*

Full results (run 2026-08-15T01:24:32Z, seed=42, 109 evaluated mutations):

| Condition | F1 | Status |
|---|---|---|
| complexity (Baseline B) | 0.0000 | Complete |
| structural (Baseline A) | 0.8878 | Complete |
| static_bcg_only (Baseline E) | 0.9619 | Complete |
| llm_only (Baseline C) | [RESULT_PENDING] | No API key |
| dep_llm (Baseline D) | [RESULT_PENDING] | No API key |
| **static_bcg (Proposed)** | **1.0000** | **Complete** |
| bcg_dynamic (Proposed+dyn) | [RESULT_PENDING] | Dynamic pending |

- H2 (BCG+dynamic F1 ≥ static_bcg F1 + 10pp): **CANNOT_BE_EVALUATED** — static_bcg F1=1.0 makes the 10pp threshold mathematically unreachable from static conditions alone. The relevant comparison is static_bcg vs baselines, where BCG dominates.
- Critical finding: ALTER_ERROR_BRANCH discriminates proposed from Baseline E (MODIFIED vs BROKEN detection).

---

## RQ3 — Dynamic Evidence Value
**PARTIAL_EVIDENCE_AVAILABLE**

- Dynamic validation rate: 49.2% (31/63 SUPPORTED)
- H3 (FPR reduction ≥15pp at ≥50% coverage): **CANNOT_BE_EVALUATED** — FPR=null in mutation benchmark (FP=0 by design); coverage = 49.2% < 50% threshold.
- 1 CONFLICT detected (CONTROL_FLOW contract contradicted by EXECUTION_SIMULATED trace)

---

## Ablations
**PARTIAL**

- Static conditions (A1, A3, A4, A5, A6): all F1=1.0 — complete
- Dynamic conditions (A2, A7): [RESULT_PENDING] — blocked by dynamic evidence gap

---

## Generalization
**PARTIAL**

- In-distribution (CardDemo): F1=1.0
- Out-of-distribution (OMP/public_cobol): F1=0.0 (GT coverage gap, not extraction failure)
- F1 delta: -1.0 — requires Level-2 GT construction for OMP to interpret correctly

---

## Manuscript
**PARTIAL**

- paper/paper.md: complete skeleton with all actual results filled in
- All [RESULT_PENDING] items correspond to genuinely blocked conditions (LLM API, dynamic pipeline)
- 10 paper tables in paper/tables/
- Figures: directory exists, generation scripts available

---

## Reproducibility
**DONE**

- `PYTHONPATH=src:. python3 -m pytest tests/ -q` → 265/265 pass
- `python3 scripts/run_rq2.py` → results/rq2/rq2_summary.json
- `python3 scripts/run_dynamic_reconciliation.py` → results/rq3/rq3_dynamic_results.json
- All seeds, configs, and thresholds locked in results/experiment_lock.json

---

## Publication Readiness
**NEEDS_REVISION**

Required before submission:
1. Level-3 human annotation (removes GT circularity — CRITICAL)
2. LLM baseline C/D results (requires OPENAI_API_KEY — MAJOR)
3. Larger dataset or multi-system evaluation (MAJOR)
4. Figure generation from actual results (MINOR)
5. Full dynamic evidence pipeline with DB2/CICS stubs (MAJOR for H3)
