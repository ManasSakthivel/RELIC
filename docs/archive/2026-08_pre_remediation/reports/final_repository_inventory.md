# Final Repository Inventory — LEGACY-CONTRACT

**Audit date:** 2025-07-15  
**Status:** Pre-submission research platform  
**Tests:** 265/265 passing  

---

## Directory Tree (Annotated)

```
legacy-contract/
├── README.md                          KEEP — primary entry point (rewritten this audit)
├── FINAL_PROJECT_STATE.md             KEEP — authoritative phase/status document
├── FINAL_EMPIRICAL_RESEARCH_REPORT.md DELETE — content duplicated in FINAL_PROJECT_STATE.md
├── FINAL_RESEARCH_DEVELOPMENT_REPORT.md DELETE — superseded status document
├── Makefile                           KEEP — 19 targets; experiment orchestration
├── Dockerfile                         KEEP — reproducible container
├── docker-compose.yml                 KEEP — 4 services (research, api, ui, db)
├── pyproject.toml                     KEEP — Poetry deps, linting config
├── .env.example                       KEEP — created this audit (LLM API key docs)
│
├── src/legacy_contract/               KEEP — primary source package
│   ├── api/                           KEEP — FastAPI research interface
│   ├── bcg/                           KEEP — BCG model + builder
│   ├── cli/                           KEEP — CLI entry points
│   ├── contracts/                     KEEP — contract model + provenance
│   ├── datasets/                      KEEP — dataset download utilities
│   ├── dynamic_analysis/              KEEP — GnuCOBOL adapter + event schema
│   ├── evaluation/                    KEEP — metrics, benchmark, runner
│   ├── evidence/                      KEEP — evidence sufficiency
│   ├── ingestion/                     KEEP — artifact ingestion
│   ├── ir/                            KEEP — IR model
│   ├── mutations/                     KEEP — 8 mutation operators
│   ├── parsers/                       KEEP — JCL, COBOL, copybook parsers
│   ├── reconciliation/                KEEP — static/dynamic reconciliation engine
│   ├── restoration/                   KEEP — counterfactual restoration
│   ├── risk/                          KEEP — BCGDiff + risk detector
│   └── static_analysis/              KEEP — contract extractor
│
├── src/bcg/                           DELETE — empty stub (no files)
├── src/contracts/                     DELETE — empty stub (no files)
├── src/dynamic_analysis/              DELETE — empty stub (no files)
├── src/evaluation/                    DELETE — empty stub (no files)
├── src/evidence/                      DELETE — empty stub (no files)
├── src/ingestion/                     DELETE — empty stub (no files)
├── src/ir/                            DELETE — empty stub (no files)
├── src/mutations/                     DELETE — empty stub (no files)
├── src/parsers/                       DELETE — empty stub (no files)
├── src/reconciliation/                DELETE — empty stub (no files)
├── src/restoration/                   DELETE — empty stub (no files)
├── src/risk/                          DELETE — empty stub (no files)
├── src/static_analysis/               DELETE — empty stub (no files)
│
├── baselines/
│   ├── base.py                        KEEP — BaselineResult interface
│   ├── complexity/complexity.py       KEEP — Baseline B
│   ├── dep_llm/dep_llm.py             KEEP — Baseline D (stub, needs API key)
│   ├── llm_only/llm_only.py           KEEP — Baseline C (stub, needs API key)
│   ├── static_bcg/static_bcg.py       KEEP — Baseline E
│   └── structural/structural.py       KEEP — Baseline A
│
├── benchmark/
│   ├── annotations/                   KEEP — annotation metadata
│   └── ground_truth/
│       └── level2_deterministic.json  KEEP — 463-item ground truth
│
├── config/
│   └── confidence_weights.yaml        KEEP — locked weight config
│
├── datasets/
│   ├── carddemo/                      KEEP — AWS CardDemo (Apache 2.0)
│   └── public_cobol/                  KEEP — public COBOL programs
│
├── experiments/
│   ├── rq1/config.yaml                KEEP — RQ1 experiment config
│   ├── rq2/config.yaml                KEEP — RQ2 experiment config
│   ├── rq3/config.yaml                KEEP — RQ3 experiment config
│   └── ablation/config.yaml           KEEP — ablation config
│
├── figures/
│   ├── fig_architecture.py            KEEP — BCG architecture diagram
│   ├── fig_baseline_comparison.py     KEEP — baseline comparison
│   ├── fig_bcg_formal.py              KEEP — BCG formal model
│   ├── fig_reconciliation.py          KEEP — reconciliation diagram
│   └── generate_all.py               KEEP — orchestrator
│
├── paper/
│   ├── paper.md                       KEEP — manuscript (in preparation)
│   ├── references.bib                 KEEP — 36 entries (W1–W28 cited; W29–W36 pending citation)
│   ├── table_source/                  KEEP — 13 LaTeX table sources
│   └── tables/                        KEEP — 17 Markdown table renderings
│
├── results/
│   ├── rq1/rq1_summary.json           KEEP — actual RQ1 results
│   ├── rq2/rq2_summary.json           KEEP — partial RQ2 results
│   ├── rq3/rq3_summary.json           KEEP — [RESULT_PENDING] (blocked)
│   ├── ablation/ablation_summary.json KEEP — partial ablation results
│   ├── generalization/                KEEP — generalization placeholder
│   ├── dataset_manifest.json          KEEP — dataset provenance
│   ├── execution_manifest.json        KEEP — trace provenance
│   ├── ground_truth_manifest.json     KEEP — GT provenance
│   └── experiment_lock.json           KEEP — frozen config hashes
│
├── reports/
│   ├── statistical_audit.md           KEEP — statistical methodology audit
│   ├── claim_evidence_matrix.md       KEEP — hypothesis tracking
│   ├── rq1_analysis.md               KEEP — RQ1 analysis
│   ├── rq2_analysis.md               KEEP — RQ2 analysis
│   ├── rq3_analysis.md               KEEP — RQ3 analysis
│   ├── error_analysis.md              KEEP — scientific integrity validation
│   ├── dynamic_validity_final.md      KEEP — dynamic evidence status
│   ├── behavioral_diff_analysis.md    INVESTIGATE — check if still current
│   ├── generalization.md              INVESTIGATE — check if complete
│   ├── impact_analysis.md             ARCHIVE — impact study (check relevance)
│   ├── mutation_analysis.md           ARCHIVE — superseded by experiment results
│   └── final_repository_inventory.md  KEEP — this file
│
├── scripts/
│   ├── build_ground_truth.py          KEEP — GT construction script
│   ├── generate_execution_traces.py   KEEP — GnuCOBOL trace generator (path issue to fix)
│   ├── run_dynamic_reconciliation.py  KEEP — dynamic reconciliation runner
│   └── run_rq2.py                     KEEP — RQ2 experiment runner
│
├── tests/
│   ├── unit/                          KEEP — 207 unit tests
│   ├── integration/                   KEEP — 5 integration tests
│   ├── regression/                    KEEP — 5 regression tests
│   └── scientific/                    KEEP — 48 scientific integrity tests
│
├── traces/
│   ├── dev/                           KEEP — development traces
│   └── validation/                    KEEP — validation traces
│
├── docs/
│   ├── architecture.md               KEEP — system architecture
│   ├── bcg_formalization.md          KEEP — BCG formal model
│   ├── bcg_formalization_v2.md       ARCHIVE — superseded by bcg_formalization.md
│   ├── methodology.md                KEEP — research methodology
│   ├── literature_review.md          KEEP — literature survey
│   ├── novelty_analysis.md           KEEP — novelty analysis
│   ├── novelty_analysis_v2.md        ARCHIVE — superseded by novelty_analysis.md
│   ├── failure_taxonomy.md           KEEP — mutation grounding
│   ├── threats_to_validity.md        KEEP — validity analysis
│   ├── limitations.md                KEEP — known limitations
│   ├── reproducibility.md            KEEP — reproduction guide
│   ├── dynamic_evidence.md           KEEP — dynamic evidence design
│   ├── dynamic_evidence_v2.md        ARCHIVE — superseded
│   ├── dataset_selection.md          KEEP — dataset justification
│   ├── annotation_protocol.md        KEEP — GT annotation protocol
│   ├── research_decisions.md         KEEP — decision log
│   ├── internal_peer_review.md       KEEP — review log
│   ├── terminology.md                KEEP — created this audit
│   ├── baseline_final_specification.md KEEP — baseline specs
│   ├── dataset_final_report.md       KEEP — dataset status
│   ├── ground_truth_final_report.md  KEEP — GT status
│   ├── dynamic_execution_report.md   KEEP — dynamic execution status
│   ├── experimental_design_v2.md     KEEP — experimental design
│   ├── experimental_methods_audit.md KEEP — methods audit
│   ├── integrity_audit_v2.md         KEEP — integrity audit
│   ├── final_reproducibility_report.md ARCHIVE — superseded by reproducibility.md
│   ├── final_closest_prior_art_audit.md ARCHIVE — superseded by literature_review.md
│   ├── final_hostile_review.md       KEEP — hostile review document
│   ├── reviewer_attack_v2.md         KEEP — hostile reviewer responses
│   └── research_state_v0.2.md        ARCHIVE — superseded by FINAL_PROJECT_STATE.md
│
└── ui/                                KEEP — React interface (not yet implemented)
```

---

## Source Module Summary

| Module | Files | Lines (approx.) | Status |
|--------|-------|-----------------|--------|
| parsers (JCL, COBOL, copybook) | 3 | ~1,800 | Complete |
| ir | 1 | ~300 | Complete |
| static_analysis | 1 | ~600 | Complete |
| dynamic_analysis | 2 | ~500 | Infrastructure complete; blocked by CardDemo |
| bcg | 2 | ~800 | Complete |
| reconciliation | 1 | ~700 | Complete; pipeline blocked |
| mutations | 1 | ~1,200 | Complete (8 operators) |
| risk | 1 | ~500 | Complete |
| evaluation | 3 | ~2,000 | Complete; statistical fixes applied |
| evidence | 1 | ~300 | Complete |
| restoration | 1 | ~200 | Complete |
| contracts | 1 | ~400 | Complete |
| baselines | 5 | ~1,500 | A, B, E complete; C, D need API key |

---

## Test Summary

| Suite | Count | Quality |
|-------|-------|---------|
| unit/test_all.py | 27 | High |
| unit/test_baselines.py | 33 | High |
| unit/test_cobol_parser.py | 34 | Excellent |
| unit/test_contracts.py | 47 | Excellent |
| unit/test_jcl_parser.py | 36 | Excellent |
| unit/test_reconciliation.py | 30 | Excellent |
| integration/test_pipeline.py | 5 | Good |
| regression/test_known_contracts.py | 5 | Good |
| scientific/test_integrity.py | 48 | Excellent |
| **Total** | **265** | **All passing** |

---

## Suspicious Files Explained

| File | Explanation |
|------|-------------|
| `src/bcg/`, `src/contracts/`, etc. | Empty scaffold directories. All code is under `src/legacy_contract/`. These should be removed. |
| `FINAL_EMPIRICAL_RESEARCH_REPORT.md` | Status document from development phase. Content duplicated in `FINAL_PROJECT_STATE.md`. Should be removed before external review. |
| `FINAL_RESEARCH_DEVELOPMENT_REPORT.md` | Earlier status document. Superseded. Should be removed. |
| `docs/*_v2.md` files | Version artifacts from iterative documentation. The base versions are authoritative; v2 files should be archived or merged. |
| `paper/tables/table_1.md`, `table_2.md`, `table_3.md` | Legacy table names alongside canonical `TABLE_1_prior_art.md` etc. Check for duplicates. |
| `.pytest_cache/` | Test cache committed to repository. Should be in `.gitignore`. |
| `baselines/__pycache__/` | Compiled bytecode committed. Should be in `.gitignore`. |
| `benchmark/ground_truth/level2_deterministic.json` | Contains absolute local paths in `evidence` fields. Non-blocking but should be relativized. |

---

## Remaining Cleanup Actions

| Priority | Action | Effort |
|----------|--------|--------|
| CRITICAL | Remove empty stub dirs under `src/` | 5 min |
| HIGH | Delete `FINAL_EMPIRICAL_RESEARCH_REPORT.md` | 1 min |
| HIGH | Delete `FINAL_RESEARCH_DEVELOPMENT_REPORT.md` | 1 min |
| HIGH | Add `__pycache__/`, `.pytest_cache/` to `.gitignore` | 5 min |
| MEDIUM | Archive or merge `docs/*_v2.md` files | 30 min |
| MEDIUM | Fix hardcoded GnuCOBOL path in `scripts/generate_execution_traces.py` | 30 min |
| MEDIUM | Relativize absolute paths in generated data artifacts | 30 min |
| LOW | Investigate `reports/behavioral_diff_analysis.md`, `reports/impact_analysis.md` | 15 min |
