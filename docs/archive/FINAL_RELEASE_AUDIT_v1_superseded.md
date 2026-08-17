# LEGACY-CONTRACT
## Final Release Audit

> **SUPERSEDED — This document records the findings of the initial release audit.**
> **See `FINAL_RELEASE_AUDIT_V2.md` for the current authoritative audit.**
> This document is retained as a historical reference showing what was identified and what has since been resolved.

**Audit date:** 2025-07-15  
**Auditor:** Automated forensic audit (10 parallel subagent inspections)  
**Tests at audit time:** 265/265 passing  
**Research status:** Pre-submission — static experiments complete; dynamic experiments partially blocked  

---

### 1. Overall Status

**NOT READY FOR EXTERNAL REVIEW**

The repository contains a scientifically coherent and technically sound research platform. The static analysis pipeline, mutation engine, baselines A/B/E, and test suite are all production-quality. However, four blocking conditions prevent external release:

1. Ground truth circularity in RQ1 (acknowledged but not resolved)
2. Dynamic pipeline blocked by artifact_id mismatch (RQ3 entirely pending)
3. Eight bibliography entries in `references.bib` are not cited in `paper.md`
4. Three manuscript sections are empty placeholders (`[RESULT_PENDING]`)

These are research completeness issues, not code quality issues. The codebase does not contain fabricated results — all missing results are correctly marked `[RESULT_PENDING]`.

---

### 2. Repository Integrity

| Item | Status |
|------|--------|
| Directory structure | Clean with exceptions (13 empty stub dirs under `src/`) |
| `.gitignore` | Created this audit |
| No secrets committed | ✅ Verified |
| `.env.example` | Created this audit |
| Stale root documents | 2 stale `FINAL_*.md` files present |
| `__pycache__` dirs | Present and now gitignored |

---

### 3. Source Code

**Quality: Good. One critical structural issue.**

| Issue | Severity | Status |
|-------|----------|--------|
| Empty stub directories (`src/bcg/`, `src/contracts/`, etc.) | MAJOR | Not yet deleted |
| `StructuralDependencyGraph.edges` type mismatch (`default_factory=dict` for a `list`) | MAJOR | Not yet fixed |
| `f1_bootstrap_samples` dynamically assigned on dataclass (not declared in class) | CRITICAL | Not yet fixed |
| GnuCOBOL path hardcoded to `/opt/homebrew/bin/cobc` | MAJOR | Not yet fixed |
| Magic number `9999` in mutations engine | MINOR | Not yet fixed |
| Bare `except Exception: pass` in `runner._git_commit_hash()` | MINOR | Acceptable for optional feature |

The core research logic (parsers, IR, BCG, reconciliation, mutation engine, risk detector, evaluation) is well-implemented. Docstrings and inline comments are accurate. Scientific integrity guardrails (SI-01 through SI-12) are implemented and tested.

---

### 4. Tests

| Suite | Count | Quality | Issues |
|-------|-------|---------|--------|
| Unit | 207 | Excellent | None |
| Integration | 5 | Good | Assertions somewhat general |
| Regression | 5 | Good | Minimal coverage |
| Scientific integrity | 48 | Excellent | None |
| **Total** | **265** | **All pass** | — |

No fake tests. No `assert True`. No skipped tests. Scientific integrity tests (SI-01–SI-12) are meaningful and test real behavioral invariants.

---

### 5. Scientific Integrity

**Strong. The project explicitly enforces scientific integrity at the implementation level.**

- `[RESULT_PENDING]` discipline correctly applied — no fabricated results
- NOT_OBSERVED ≠ CONTRADICTED enforced in reconciliation engine and tested in 15+ test cases
- SYNTHETIC_STATIC traces prohibited from promoting validation states (SI-01)
- HUMAN_VALIDATED and GROUND_TRUTH states protected from automated override (SI-07, SI-12)
- Confidence scores explicitly documented as non-probabilities
- FPR correctly returned as `NaN` for open-set problem (statistical audit fix applied)

**⚠️ Ground truth circularity:** Level-2 ground truth was annotated by the extraction algorithm itself. RQ1 F1=1.0 is a mathematical identity, not an empirical measurement of recovery quality. This is fully acknowledged in the paper, manuscript, and results files — but it is a fundamental limitation that cannot be resolved without Level-3 human annotation.

---

### 6. Dataset

| Dataset | Status | License |
|---------|--------|---------|
| AWS CardDemo | ✅ Downloaded, extracted | Apache 2.0 |
| Public COBOL programs | ✅ Downloaded | Various open source |
| Ground truth (Level-2) | ✅ 463 items | Derived from CardDemo |
| Ground truth (Level-3) | ❌ Not yet annotated | Future work |

Dataset documentation: `docs/dataset_selection.md`, `docs/dataset_final_report.md`, `results/dataset_manifest.json`.  
Train/validation/held-out split defined in `datasets/carddemo/SPLITS_60_20_20.json`.

---

### 7. Ground Truth

463-item Level-2 DETERMINISTIC ground truth exists and is used for RQ1 evaluation. The tautology is fully acknowledged. Level-3 human annotation (required for non-circular RQ1 validation) does not yet exist and is documented as future work in `docs/annotation_protocol.md`.

---

### 8. Dynamic Evidence

Infrastructure complete: GnuCOBOL 3.2.0 adapter, normalized ExecutionEvent schema, reconciliation engine, 13+ traces generated for standalone COBOL programs. 

Blocked by artifact_id mismatch: traces carry `artifact_id=program_name` but contracts are indexed by `artifact_id=jcl_step_id`. Until this mapping is implemented (Phase 7), dynamic contract promotion rate = 0%.

CardDemo COBOL programs that use DB2/CICS/IMS cannot execute under GnuCOBOL without stubs. This is documented as a limitation.

---

### 9. Experiments

| Experiment | Status | Completeness |
|-----------|--------|--------------|
| RQ1 (static recovery) | ✅ Complete | F1=1.0, all types |
| RQ2 (Baselines A, B, E) | ✅ Complete | 109 mutations, 3/6 conditions |
| RQ2 (Baselines C, D) | ❌ Blocked | Requires OPENAI_API_KEY |
| RQ2 (BCG+dynamic) | ❌ Blocked | artifact_id mismatch |
| RQ3 (coverage experiment) | ❌ Blocked | No trace coverage; artifact_id mismatch |
| Ablation (E0–E6 static) | ✅ Complete | All F1=1.0 (undifferentiated) |
| Ablation (E7 LLM) | ❌ Blocked | Requires LLM API key |
| Generalization | ❌ Not started | Held-out systems not evaluated |

---

### 10. Results

Available results are genuine numerical measurements, not fabricated values. Missing results are correctly marked `[RESULT_PENDING]`. No `[RESULT_PENDING]` appears unintentionally in any location intended for a published value.

Key confirmed results:
- RQ1: P=1.00, R=1.00, F1=1.00 (tautological, see §5)
- RQ2 static_bcg: F1=1.00 vs. Baseline A (structural) F1=0.8878
- Key finding: 4/8 mutation operators completely invisible to structural analysis

---

### 11. Statistical Analysis

Four statistical bugs were identified and fixed in a prior audit (documented in `reports/statistical_audit.md`):
1. FPR bug (always returned 1.0 or 0.0 for open-set problems) — **fixed**
2. Wrong effect size formula for rank-biserial r — **fixed**
3. Bonferroni n_comparisons overcorrection (15 instead of 5) — **fixed**
4. Missing git commit hash in RunRecord — **fixed**

Remaining gap: Mann-Whitney pairwise tests require per-mutation F1 score lists. These are not yet populated because `bcg_dynamic` condition is blocked. Tests will fire when Phase 7 is resolved.

---

### 12. Literature

28 works cited in `paper.md` (W1–W28) all have entries in `references.bib`. ✅  
8 works in `references.bib` (W29–W36: Lo 2006, Ammons 2002, GIST/Lorenzoli 2008, etc.) are not yet cited in `paper.md`. ❌  
TABLE_1 references 3 systems (DySy, Allamanis, CodeBERT) without corresponding bibliography entries. ❌

These are pre-submission gaps. The hostile review document (`docs/final_hostile_review.md`) identifies them explicitly and provides the required citation text.

---

### 13. Novelty

The novelty analysis (`docs/novelty_analysis.md`, `docs/novelty_analysis_v2.md`) is thorough, balanced, and honest. The work does not overclaim. The novelty matrix correctly identifies what is established prior art vs. incremental contribution vs. potentially novel.

Principal novelty claim: The BCG as a cross-artifact, provenance-aware, static/dynamic-reconciled behavioral contract representation for legacy JCL+COBOL systems has no direct prior. This claim is defensible but requires the W29–W36 citations (GIST, Ammons, Lo) to be added to the paper before submission, and the Daikon capability comparison table must appear in §5.

---

### 14. Manuscript

| Section | Status |
|---------|--------|
| Abstract | ✅ Complete with actual results |
| Introduction | ✅ Complete |
| Background | ✅ Complete |
| Related Work | ⚠️ Missing W29–W36 citations; missing Daikon capability table |
| Research Questions | ✅ Complete |
| Formal Model (BCG) | ✅ Complete |
| Methodology | ✅ Complete |
| Reconciliation | ✅ Complete |
| Mutation Framework | ✅ Complete |
| Experimental Methodology | ✅ Complete |
| Results | ⚠️ Partial — 3 conditions pending |
| Ablation Study | ❌ [RESULT_PENDING] — section is empty |
| Dynamic Evidence Analysis | ✅ Complete (partial results present) |
| Error Analysis | ⚠️ Skeleton only |
| Discussion | ❌ [RESULT_PENDING] — section is empty |
| Threats to Validity | ✅ Complete |
| Limitations | ✅ Complete |
| Reproducibility | ✅ Complete |
| Conclusion | ⚠️ Partial — [RESULT_PENDING] for summary claims |
| References | ✅ 28 cited; ⚠️ W29–W36 not cited |

No marketing language, no superlatives, no AI-style filler detected. Tone is appropriately technical.

---

### 15. Figures

Figure generation scripts exist for all 4 figures. No PDF figures are generated yet (requires `make figures`). Scripts correctly output placeholders when result data is missing. All architecture and formal model figures are ready to generate without experimental results.

---

### 16. Tables

10 tables exist in both Markdown (`paper/tables/`) and LaTeX (`paper/table_source/`) formats.  
TABLE_1 (prior art) and TABLE_4 (RQ1) have real data. ✅  
TABLE_5 (baselines) has 2/6 conditions complete. ⚠️  
TABLE_6–TABLE_10 have partial or pending data. ⚠️  
Duplicate legacy table files exist (`table_1.md`, `table_2.md`, `table_3.md`) alongside canonical `TABLE_1_prior_art.md` etc. These should be removed.

---

### 17. Reproducibility

Static experiments (RQ1, partial RQ2): reproducible with `poetry install && make rq1 && make rq2`.  
Dynamic experiments (RQ3): not reproducible — requires Phase 7 fix.  
LLM baselines: not reproducible without OPENAI_API_KEY.  
Docker: `docker-compose up research` will execute the static pipeline.  
`.env.example` created this audit.

---

### 18. Security / Secrets

No API keys, passwords, tokens, or credentials committed. ✅  
Absolute local filesystem paths (`/Users/manassakthivel/...`) present in generated data artifacts (ground truth JSON, trace files) — these are data artifacts, not code, and do not expose credentials. Non-critical but should be relativized before public release.  
Neo4j runs with `NEO4J_AUTH=none` in development — acceptable for local research environment, not for production.

---

### 19. Documentation

Documentation is comprehensive and well-organized. The `docs/` directory contains 28 files covering all aspects of the research. Some versioned files (`*_v2.md`) should be archived. The new `docs/terminology.md` (created this audit) establishes canonical terminology.

One concern: the `docs/` directory contains several documents with dates suggesting an active development log rather than a curated research archive. For external review, the development-log-style documents (`research_state_v0.2.md`, `final_closest_prior_art_audit.md`, etc.) should be archived or removed.

---

### 20. Human Researcher Presentation

**Score: 7/10**

The writing is technically accurate and avoids superlatives. The scientific integrity discipline is genuine and well-implemented. The codebase structure is logical.

Areas for improvement:
- Root-level clutter (`FINAL_EMPIRICAL_RESEARCH_REPORT.md`, `FINAL_RESEARCH_DEVELOPMENT_REPORT.md`) suggests active development rather than a curated release
- The `docs/` directory contains too many documents for a first-time reader to navigate; a reading guide would help
- Some documents use "This document..." as their opening sentence, which is fine but could be varied
- The `[RESULT_PENDING]` discipline is correct and honest, but a reviewer encountering it for the first time may not understand its purpose without reading the README first

---

### 21. Remaining Issues

**CRITICAL (must fix before external review):**

| # | Issue | Location | Fix |
|---|-------|----------|-----|
| C1 | Dynamic pipeline blocked by artifact_id mismatch | `scripts/run_dynamic_reconciliation.py` | Map execution artifact_id → JCL step_id in Phase 7 |
| C2 | RQ3 entirely pending — no dynamic evidence results | `results/rq3/` | Requires C1 fix |
| C3 | Three manuscript sections empty | `paper/paper.md` §12, §15, §19 | Write after experiments complete |
| C4 | W29–W36 not cited in paper despite being in bibliography | `paper/paper.md` §5 | Add 8 citations to Related Work |
| C5 | Ground truth circularity — Level-3 annotation not available | `benchmark/ground_truth/` | Commission human annotation (future work) |

**MAJOR (fix before submission):**

| # | Issue | Location | Fix |
|---|-------|----------|-----|
| M1 | `f1_bootstrap_samples` not declared in `EvaluationResult` dataclass | `src/legacy_contract/evaluation/metrics.py` | Add fields to dataclass |
| M2 | `StructuralDependencyGraph.edges` type mismatch | `baselines/structural/structural.py:67` | Change `default_factory=dict` to `default_factory=list` |
| M3 | 13 empty stub directories under `src/` | `src/bcg/`, `src/contracts/`, etc. | Delete all empty stubs |
| M4 | GnuCOBOL path hardcoded macOS-only | `scripts/generate_execution_traces.py` | Replace with PATH lookup |
| M5 | TABLE_1 references 3 systems without bibliography entries | `paper/tables/TABLE_1_prior_art.md` | Add BibTeX entries or remove rows |
| M6 | Daikon capability comparison table missing from paper §5.1 | `paper/paper.md` §5.1 | Add side-by-side table (specified in hostile review) |
| M7 | 2 stale root-level FINAL_*.md documents | Repository root | Delete before external release |

**MINOR:**

| # | Issue |
|---|-------|
| mn1 | Magic number `9999` in mutations engine should be a named constant |
| mn2 | Import aliasing inconsistency (`_math`, `_random` prefix) |
| mn3 | Absolute local paths in generated data artifacts |
| mn4 | Duplicate legacy table files (`table_1.md`, `table_2.md`, `table_3.md`) |
| mn5 | Development-log-style documents in `docs/` visible to external reviewer |
| mn6 | UI not implemented (noted in status; not blocking) |

---

### 22. Final Recommendation

**NOT READY FOR EXTERNAL REVIEW**

The project is research-complete for the static pipeline and demonstrates genuine scientific integrity, but three conditions must be met before external release:

1. **Phase 7 completion:** Resolve the artifact_id mismatch to enable dynamic contract promotion. This unblocks RQ3 and the BCG+dynamic RQ2 condition — the core empirical claims of the paper.

2. **Paper completion:** Write the Discussion, Ablation Study, and Conclusion sections with actual experimental results. Add W29–W36 citations and the Daikon comparison table to Related Work.

3. **Repository cleanup:** Remove stale documents, empty stub directories, and commit a clean `.gitignore`.

After these three steps, the repository would be ready for external peer review. The fundamental research artifacts (parsers, BCG, reconciliation, mutation engine, evaluation framework, test suite) are of publication quality.
