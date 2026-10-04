# Changelog

All notable changes to RELIC are documented here.

---

## [1.1.0] — 2026-10-04

**Research remediation.** The evaluation was rebuilt; the 1.0.0 headline results are
withdrawn. Audit: `docs/remediation/PRE_REMEDIATION_AUDIT.md`; status:
`docs/FINAL_RESEARCH_READINESS_REPORT.md`.

### Added

- Source-level mutation benchmark (`relic_eval/`): 10 operators applied at every
  applicable site of three public JCL corpora (AWS CardDemo, OMP COBOL Programming
  Course, IBM CICS GenApp), with complete accounting of every candidate mutant.
- Independent JCL execution-semantics oracle (`jcl_oracle/`) as ground truth; shares
  no code with RELIC and never sees the mutation operator.
- Corrected LLM baselines C (LLM-only) and D (dependency + LLM): the model sees the
  original and modified JCL; no operator/label in the prompt; failed calls are never
  scored; every request/response cached; common-population comparison.
- Trivial "any non-comment change" reference detector; file-level cluster bootstrap CIs;
  sensitivity analyses; generated tables/figures/doc blocks; `make check`.
- `legacy_v1_0` switches that reproduce the released behaviour exactly; RELIC v1.1
  (spec-conformance fixes, reported separately as post hoc).

### Fixed (v1.1, post hoc)

- JCL continuation lines (IBM rule), columns 73–80, balanced `COND=` capture,
  `COND` without step name binds all previous steps, BCG diff compares guard
  parameters and flags weakened guards.
- Baseline B no longer receives the mutation location.
- Generated-block rendering and its consistency check (empty blocks were never
  matched; table row order depended on JSON key order).

### Withdrawn

- RQ2 F1 = 1.000 (BCG-level harness that deleted contracts from RELIC's own output),
  FPR = 0 on vacuous negatives, the "confidence-delta" finding, LLM F1 0.0377 / 0.1091
  (rate-limited calls scored as answers), RQ3 dynamic validation rate (self-generated
  traces), "empirically grounded" operator claims (unverifiable sources).

---

## [1.0.0] — 2025-08-17

> **Superseded.** The evaluation results listed for 1.0.0 below are withdrawn (see 1.1.0).

**Initial public research release.**

### Added

- Behavioral Contract Graph (BCG) implementation: `BCG = (V, E, C, P, D, Γ)` six-tuple
- JCL parser: 55/55 CardDemo JCL files parsed (136 EXEC, 547 DD constructs)
- COBOL parser: 44/44 CardDemo COBOL programs parsed
- Copybook parser: 62 copybooks resolved
- Static contract extractor: TEMPORAL, RESOURCE, and CONTROL_FLOW contracts with deterministic provenance
- Dynamic Evidence Adapter: GnuCOBOL trace adapter + JCL simulation adapter
- ArtifactMapper: deterministic program-name → JCL step-id resolution
- ReconciliationEngine: five-outcome static/dynamic reconciliation with SI-01 guard
- BCGDiff: confidence-delta differencing (detects both broken and weakened contracts)
- MutationEngine: 8 fault-grounded operators (F1/F2/F3 categories)
- NegativeMutationEngine: 5 semantics-preserving operators for false-positive evaluation
- Baselines A–E: structural dependency, complexity metrics, LLM-only, Dep+LLM, static BCG
- Full evaluation framework: RQ1, RQ2, RQ3, ablation experiments
- 305 tests (legacy suite): unit, integration, regression, scientific integrity (SI-01 through SI-12)
- Fault-grounded mutation benchmark (withdrawn): 104 evaluated positive + 144 negative mutations
- CardDemo evaluation (withdrawn — circular harness): BCG F1=1.000 vs structural baseline F1=0.8995
- LLM baselines (withdrawn — 245/248 and 241/248 calls failed and were scored): Groq llama-3.3-70b-versatile, v2_blinded prompts
- Dynamic validation (withdrawn — self-generated traces): 91.8% contracts SUPPORTED with 40 execution traces
- Reproducibility: `make reproduce-paper1` runs all deterministic experiments
- Docker support: single-command reproduction environment
- Research documentation: architecture, methodology, limitations, reproduction guides
- Paper manuscript (ACM sigconf format, double-blind ready): `paper/paper.tex`

### Fixed

- BCGDiff engine gap: `RiskDetector` previously inspected only `diff.broken`, missing
  mutations that weakened contracts without removing them. Fixed to also inspect
  `diff.modified`; ALTER_ERROR_BRANCH (8 mutations) now correctly detected.
- Reflexive-pair guard: duplicate step names in DEFCUST.jcl/TRANREPT.jcl created
  false self-ordering obligations. Guard added to both extractor and oracle;
  evaluated mutation count reduced from 109 to 104.
- RQ3 bugs (3 fixed): timestamp parsing, absolute vs. relative path entity-ID
  mismatch, ArtifactMapper misapplied to entity-ID traces.
- LLM baseline v1 prompts discarded (semantics-preserving context leak in negative
  descriptions); all reported LLM results use v2_blinded prompts.

### Research Status

All frozen results are in `results/FINAL_RESULTS_MANIFEST.json` (v1.4).
LLM baselines require `GROQ_API_KEY`. All other experiments are fully deterministic.
See `docs/reproducibility.md` for the complete reproduction guide.
