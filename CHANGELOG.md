# Changelog

All notable changes to RELIC are documented here.

---

## [1.0.0] — 2025-08-17

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
- 305 tests: unit, integration, regression, scientific integrity (SI-01 through SI-12)
- Fault-grounded mutation benchmark: 104 evaluated positive + 144 negative mutations
- CardDemo evaluation: BCG F1=1.000 vs structural baseline F1=0.8995
- LLM baselines evaluated: Groq llama-3.3-70b-versatile, v2_blinded prompts
- Dynamic validation: 91.8% contracts SUPPORTED with 40 execution traces
- Reproducibility: `make reproduce-paper1` runs all deterministic experiments
- Docker support: single-command reproduction environment
- Research documentation: architecture, methodology, limitations, reproduction guides
- Paper manuscript (ACM sigconf format, double-blind ready): `paper/paper.tex`

### Research Status

All frozen results are in `results/FINAL_RESULTS_MANIFEST.json` (v1.4).
LLM baselines require `GROQ_API_KEY`. All other experiments are fully deterministic.
See `docs/reproduction.md` for the complete reproduction guide.
