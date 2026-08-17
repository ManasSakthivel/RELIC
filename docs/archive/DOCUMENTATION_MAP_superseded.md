# DOCUMENTATION MAP
# LEGACY-CONTRACT Research Platform
# This file is the authoritative navigation guide for a new reader.

---

## Start Here

| Document | Purpose |
|---|---|
| `README.md` | Project overview, architecture, reproduction instructions |
| `FINAL_RESEARCH_REPORT.md` | Complete research report (executive summary through conclusion) |
| `FINAL_RELEASE_AUDIT_V3.md` | Release audit: what is ready, what is partial, what is blocked |

---

## Research Paper

| Document | Purpose |
|---|---|
| `paper/paper.md` | Full manuscript (work in progress) |
| `paper/references.bib` | BibTeX reference list |
| `paper/tables/` | Generated result tables |
| `paper/figures/` | Generated figures |

---

## Experiment Results (Authoritative)

| File | Description |
|---|---|
| `results/FINAL_RESULTS_MANIFEST.json` | Manifest of all result files, status, hashes |
| `results/experiment_lock.json` | Locked experiment parameters (seed, config hashes) |
| `results/rq1/rq1_summary.json` | RQ1 result — SELF_CONSISTENCY_ONLY |
| `results/rq1/rq1.csv` | RQ1 per-type CSV |
| `results/rq2/rq2_summary.json` | RQ2 result — static conditions complete; LLM/dynamic BLOCKED |
| `results/rq2/rq2.csv` | RQ2 per-condition CSV |
| `results/rq3/rq3_dynamic_results.json` | RQ3 full result (49.2% dynamic validation rate) |
| `results/rq3/rq3_summary.json` | RQ3 summary + H3 testability note |
| `results/ablation/` | Ablation study results |
| `results/generalization/` | Generalization results (BLOCKED — OMP GT not available) |

---

## Reports (Analysis, Not Raw Results)

| Document | Purpose |
|---|---|
| `reports/pre_remediation_state.md` | Snapshot before final remediation pass |
| `reports/final_claim_evidence_matrix.md` | Every claim → evidence mapping |
| `reports/claim_evidence_matrix.md` | Claim evidence matrix (earlier version) |
| `reports/result_traceability.md` | Every number in the paper traced to source file |
| `reports/rq1_analysis.md` | RQ1 deep analysis |
| `reports/rq2_analysis.md` | RQ2 deep analysis |
| `reports/rq3_analysis.md` | RQ3 deep analysis |
| `reports/mutation_analysis.md` | Mutation framework analysis |
| `reports/statistical_audit.md` | Statistical methods audit |
| `reports/behavioral_diff_analysis.md` | BCGDiff case studies |
| `reports/error_analysis.md` | Error analysis |
| `reports/generalization.md` | Generalization evaluation |
| `reports/ground_truth_independence.md` | GT independence analysis |
| `reports/impact_analysis.md` | Impact analysis |
| `reports/dynamic_validity_final.md` | Dynamic evidence validity |

---

## Architecture & Technical Design

| Document | Purpose |
|---|---|
| `docs/architecture.md` | System architecture |
| `docs/bcg_formalization.md` | Formal BCG model specification |
| `docs/dynamic_evidence.md` | Dynamic evidence design |
| `docs/methodology.md` | Research methodology |
| `docs/research_decisions.md` | Documented design decisions (D-001 through D-009) |
| `docs/terminology.md` | Term definitions |
| `docs/failure_taxonomy.md` | Mutation failure taxonomy |
| `docs/baseline_final_specification.md` | Baseline specification |

---

## Ground Truth & Annotation

| Document | Purpose |
|---|---|
| `docs/annotation_protocol_final.md` | Authoritative annotation protocol |
| `docs/annotation_blinding_protocol.md` | Blinding procedure for Level-3 annotation |
| `docs/ground_truth_final_report.md` | GT assessment |
| `benchmark/annotations/` | **EMPTY** — Level-3 annotation not yet conducted |
| `scripts/export_blinded_annotation.py` | Generate blinded annotation package |
| `scripts/import_annotation_results.py` | Import and score annotation results |

---

## Reproducibility

| Document | Purpose |
|---|---|
| `docs/reproducibility.md` | Reproducibility design |
| `docs/final_reproducibility_report.md` | Final reproducibility audit |
| `Dockerfile` | Container build (GnuCOBOL + Python 3.11) |
| `docker-compose.yml` | Container orchestration |
| `pyproject.toml` | Python dependencies |
| `requirements.lock` | Pinned pip freeze (runtime environment snapshot) |
| `Makefile` | Experiment targets |

---

## Evaluation Infrastructure

| Document | Purpose |
|---|---|
| `benchmark/` | Ground truth, splits, mutation benchmark |
| `datasets/` | CardDemo and public COBOL datasets |
| `traces/dev/` | Execution traces (EXECUTION + EXECUTION_SIMULATED) |
| `baselines/` | Baseline implementation code |
| `experiments/` | Experiment configuration YAML files |
| `config/` | Global configuration |

---

## Tests

| Path | Description |
|---|---|
| `tests/unit/` | Unit tests (parser, contract model, reconciliation, baselines) |
| `tests/scientific/test_integrity.py` | Scientific integrity tests (SI-01 through SI-12) |
| `tests/scientific/test_si01_synthetic_guard.py` | SI-01 extended 10-variant regression suite |
| `tests/integration/test_pipeline.py` | End-to-end pipeline integration |
| `tests/integration/test_artifact_mapping_pipeline.py` | ArtifactMapper production wiring proof |
| `tests/regression/test_known_contracts.py` | Known-contract regression tests |

---

## Archive (Superseded, Historical)

| Path | Purpose |
|---|---|
| `docs/archive/` | Superseded documentation drafts |
| `docs/archive/FINAL_RELEASE_AUDIT_v1_superseded.md` | V1 audit (superseded by FINAL_RELEASE_AUDIT_V3.md) |
| `docs/archive/FINAL_RELEASE_CHECKLIST_superseded.md` | Old checklist (superseded) |
| `docs/archive/FINAL_PROJECT_STATE_superseded.md` | Old project state (superseded) |

---

## Not Research-Critical

| Path | Purpose |
|---|---|
| `ui/` | Experimental React UI — not part of core research contribution |
| `docs/literature_review.md` | Phase-0 literature doc (W-numbering differs from paper §5) |

---

*DOCUMENTATION_MAP.md — navigate LEGACY-CONTRACT for research review.*
