# LEGACY-CONTRACT — Final Release Checklist

**Audit date:** 2025-07-15  
**Project:** Execution-Grounded Behavioral Contract Recovery for Legacy Batch Modernization  

Checked items (✅) are verified complete. Unchecked items (☐) require action before external release.

---

## Repository Structure

- [x] Repository structure logical and navigable
- [x] Primary source package under `src/legacy_contract/`
- [ ] Empty stub directories under `src/` removed (`src/bcg/`, `src/contracts/`, etc.)
- [x] `datasets/`, `experiments/`, `results/`, `paper/`, `docs/` all present and populated
- [ ] Stale root documents removed (`FINAL_EMPIRICAL_RESEARCH_REPORT.md`, `FINAL_RESEARCH_DEVELOPMENT_REPORT.md`)
- [ ] Duplicate legacy table files removed (`paper/tables/table_1.md`, `table_2.md`, `table_3.md`)
- [ ] Development-log-style documents archived (`docs/research_state_v0.2.md`, `docs/final_closest_prior_art_audit.md`, `docs/final_reproducibility_report.md`)

---

## No Stale Artifacts

- [ ] `__pycache__/` directories removed (gitignored going forward)
- [ ] `.pytest_cache/` committed contents removed (gitignored going forward)
- [x] No binary or compiled outputs in source directories
- [x] No debug logs committed
- [x] No temporary CSV or notebook files committed

---

## Security / Secrets

- [x] No API keys, tokens, or passwords in any committed file
- [x] No hardcoded credentials in source code
- [x] `.env` file not committed
- [x] `.env.example` present (created this audit)
- [x] `.gitignore` present (created this audit)
- [ ] Absolute local paths in generated data artifacts relativized (`benchmark/ground_truth/level2_deterministic.json`, `traces/dev/*.json`)

---

## README Complete

- [x] One-paragraph project description
- [x] Research question stated
- [x] Why the problem matters explained
- [x] Contributions listed
- [x] Architecture described
- [x] Repository structure described
- [x] Dataset provenance documented
- [x] Installation instructions present
- [x] Experiment execution instructions present
- [x] Results table present (with [RESULT_PENDING] where applicable)
- [x] Limitations prominently stated
- [x] Research status honestly described
- [x] License stated
- [ ] Citation updated (pending submission)

---

## Documentation Consistent

- [x] `docs/terminology.md` created (canonical terms)
- [x] `docs/methodology.md` consistent with experiments
- [x] `docs/architecture.md` consistent with source code structure
- [x] `docs/threats_to_validity.md` complete
- [x] `docs/limitations.md` complete
- [x] `docs/reproducibility.md` complete
- [ ] Versioned docs (`*_v2.md`) archived or merged into primary docs

---

## Terminology Consistent

- [x] `docs/terminology.md` defines canonical terms
- [x] Validation states (STATIC_CANDIDATE, STATIC_DYNAMIC_SUPPORTED, STATIC_DYNAMIC_CONFLICT, NOT_OBSERVED, etc.) used consistently in code
- [x] Contract types (TEMPORAL, RESOURCE, CONTROL_FLOW) used consistently
- [ ] Full terminology consistency pass across all docs not yet done

---

## Literature References Valid

- [x] All 28 works cited in `paper.md` (W1–W28) have entries in `references.bib`
- [x] BibTeX entries are properly formatted with complete metadata
- [x] No `[?]` or `??` placeholder citations
- [x] No invented bibliography entries
- [ ] W29–W36 (Lo 2006, Ammons 2002, GIST/Lorenzoli 2008, etc.) cited in `paper.md` §5 (Related Work)
- [ ] DySy (2009), Allamanis (2018), CodeBERT (2020) in TABLE_1 added to `references.bib` or removed from table

---

## Novelty Claims Defensible

- [x] Novelty matrix in `docs/novelty_analysis.md` completed
- [x] Prior art acknowledged honestly (Daikon, Klaedtke, Pessoa, Sneed)
- [x] What is established vs. incremental vs. novel clearly distinguished
- [x] No unsupported superlatives in manuscript
- [ ] Daikon capability comparison table added to `paper.md` §5.1
- [ ] GIST (Lorenzoli 2008) directly compared in Related Work text

---

## All Tests Passing

- [x] Unit tests: 207 passing
- [x] Integration tests: 5 passing
- [x] Regression tests: 5 passing
- [x] Scientific integrity tests: 48 passing
- [x] **Total: 265/265 passing**

---

## Scientific Integrity Tests Passing

- [x] SI-01: SYNTHETIC_STATIC traces cannot promote validation state
- [x] SI-02: Provenance survives BCGDiff
- [x] SI-03: Weight sum invariant (sums to 1.0)
- [x] SI-04: YAML weights match code constants
- [x] SI-05: Ambiguity penalty applied
- [x] SI-06: NOT_OBSERVED ≠ CONTRADICTED (all contract types)
- [x] SI-07: HUMAN_VALIDATED state protected
- [x] SI-08: No duplicate extraction
- [x] SI-09: DETERMINISTIC provenance correct
- [x] SI-10: Entity ID determinism
- [x] SI-11: return_code=None semantics correct
- [x] SI-12: GROUND_TRUTH state protected

---

## Experiment Configuration Frozen

- [x] `results/experiment_lock.json` contains config/GT/split hashes
- [x] `config/confidence_weights.yaml` locked (`locked: true`)
- [x] Random seeds documented (seed=42 throughout)
- [x] Train/validation/held-out split defined before system built

---

## Results Reproducible

- [x] RQ1 results reproducible from `experiments/rq1/config.yaml` + `scripts/`
- [x] RQ2 static conditions reproducible from `scripts/run_rq2.py`
- [ ] RQ3 reproducible (blocked: artifact_id mismatch)
- [ ] RQ2 LLM baselines reproducible (blocked: API key required)
- [ ] Full end-to-end clean-room reproduction attempted

---

## No Fabricated Results

- [x] All unavailable results marked `[RESULT_PENDING]`
- [x] No numerical values inserted without corresponding experiment execution
- [x] Result files include config hash, seed, and timestamp for every run
- [x] Git commit hash recorded in `RunRecord` (added in statistical audit)

---

## No Unintentional `[RESULT_PENDING]`

- [x] All `[RESULT_PENDING]` instances are intentional (blocked experiments)
- [x] No `[RESULT_PENDING]` in sections that claim to have completed results
- [x] RQ1 results section contains actual numbers, not `[RESULT_PENDING]`
- [x] RQ2 static conditions section contains actual numbers

---

## Tables Generated

- [x] TABLE_1 (prior art): complete with real comparisons
- [x] TABLE_2 (datasets): complete
- [x] TABLE_3 (contract taxonomy): complete
- [x] TABLE_4 (RQ1 recovery): complete with actual numbers
- [ ] TABLE_5 (baseline comparison): 2/6 conditions complete; 4 pending
- [ ] TABLE_6 (per-operator): partial (static operators only)
- [ ] TABLE_7 (mutation taxonomy): complete (design table)
- [ ] TABLE_8 (ablation): static conditions only; dynamic pending
- [ ] TABLE_9 (computational cost): partial
- [ ] TABLE_10 (error analysis): pending

---

## Figures Generated

- [ ] Fig 1 — BCG architecture diagram (script ready; `make figures` not run)
- [ ] Fig 2 — BCG formal model (script ready)
- [ ] Fig 3 — Reconciliation state machine (script ready)
- [ ] Fig 4 — Baseline comparison (script ready; static conditions only)

---

## Manuscript Compiled

- [x] Abstract: complete with actual results
- [x] Introduction: complete
- [x] Background: complete
- [x] Research Questions: complete
- [ ] Related Work: needs W29–W36 citations and Daikon comparison table
- [x] Formal Model: complete
- [x] Methodology: complete
- [x] Reconciliation: complete
- [x] Mutation Framework: complete
- [x] Experimental Methodology: complete
- [ ] Results: partial (3 conditions pending)
- [ ] Ablation Study: empty (blocked)
- [ ] Discussion: empty (blocked)
- [x] Threats to Validity: complete
- [x] Limitations: complete
- [x] Reproducibility: complete
- [ ] Conclusion: partial (summary claims pending)
- [x] References: W1–W28 complete; W29–W36 to be added

---

## Citations Resolve

- [x] W1–W28: all have valid BibTeX entries
- [ ] W29–W36: present in `.bib` but not yet cited in paper
- [ ] DySy, Allamanis, CodeBERT: referenced in TABLE_1 but not in `.bib`

---

## Limitations Documented

- [x] Ground truth circularity (Level-2 tautology) explicitly acknowledged in paper
- [x] Single benchmark system (CardDemo) — generalization limitation stated
- [x] GnuCOBOL scope limitation documented
- [x] CardDemo DB2/CICS/IMS dependency limitation documented
- [x] Confidence score ≠ probability explicitly stated
- [x] Open-set FPR problem documented

---

## Threats to Validity Documented

- [x] Internal validity: parser errors, annotation errors, mutation bias, benchmark leakage, LLM nondeterminism
- [x] External validity: limited system count, GnuCOBOL vs. IBM COBOL, public vs. enterprise JCL
- [x] Construct validity: ground truth tautology documented
- [x] Statistical validity: bootstrap CI, Bonferroni correction, Mann-Whitney U

---

## Reproducibility Instructions Work

- [x] `poetry install` installs all dependencies
- [x] `make download-carddemo` downloads and extracts dataset
- [x] `make rq1` runs RQ1 experiment (static)
- [x] `make rq2` runs RQ2 static conditions
- [ ] `make generate-traces` requires GnuCOBOL (platform-dependent, path issue)
- [ ] `make rq3` blocked (artifact_id mismatch)
- [x] `docker-compose up research` executes static pipeline

---

## Clean-Room Reproduction Attempted

- [ ] Not yet attempted — blocked by dynamic pipeline issues

---

## Hostile Review Completed

- [x] `docs/final_hostile_review.md` completed
- [x] `docs/reviewer_attack_v2.md` contains specific responses
- [x] Five fatal problems identified and documented
- [x] Eleven major problems identified and documented
- [ ] Fixes for N1, N2, N3 (paper text fixes) not yet applied to manuscript

---

## Final Claim-Evidence Matrix Completed

- [x] `reports/claim_evidence_matrix.md` present
- [x] `reports/result_traceability.md` created this audit
- [x] All result claims traceable to generating experiment and result file

---

## No Unsupported Claims

- [x] F1=1.0 RQ1 result accompanied by tautology caveat in paper
- [x] No claim that BCG+dynamic outperforms baselines (pending result)
- [x] No claim that dynamic evidence reduces FPR (pending result)
- [x] Partial RQ2 results presented as partial, not complete

---

## Repository Presentation Coherent

- [x] README is the correct entry point
- [x] README does not require prior knowledge of the project
- [x] Architecture is described at the right level of abstraction
- [x] Results are honest about what is and is not yet measured
- [ ] Stale documents removed from root and `docs/`
- [ ] Development-phase artifacts separated from research artifacts

---

## Project Ready for External Review

**☐ NOT READY**

Blocking items:
1. Dynamic pipeline (RQ3) blocked by artifact_id mismatch — core claim of the paper unvalidated
2. Paper Discussion and Conclusion sections empty
3. W29–W36 not cited in Related Work despite being in bibliography
4. Several manuscript sections contain [RESULT_PENDING] that will be visible to reviewers

When these four items are resolved, change this checkbox to `[x] READY`.
