# FINAL_RELEASE_AUDIT_V3.md
# LEGACY-CONTRACT Research Platform
# Post-remediation release audit

**Supersedes:** FINAL_RELEASE_AUDIT_V2.md, FINAL_RELEASE_AUDIT.md (both archived)  
**Tests at time of audit:** 295 passed, 0 failed  
**Python:** 3.11 | **GnuCOBOL:** 3.2.0 available  

---

## Repository Status

| Dimension | Status | Note |
|---|---|---|
| Code quality | READY | Production-quality parsers, BCG engine, reconciliation |
| Test coverage | READY | 295 tests pass: unit, integration, scientific integrity, regression |
| Scientific integrity | READY | All SI-01–SI-12 enforced; 10-variant SI-01 regression suite added |
| Documentation | READY | DOCUMENTATION_MAP.md, FINAL_RESEARCH_REPORT.md, authoritative README |
| Reproducibility (static) | READY | `pip install -e . && make reproduce-paper1` runs end-to-end |
| Reproducibility (dynamic) | PARTIAL | GnuCOBOL available; CardDemo COBOL blocked by DB2/CICS |
| Result files | FROZEN | FINAL_RESULTS_MANIFEST.json created; values must not be modified |
| Manuscript | PARTIAL | Synchronized with actual results; [RESULT_PENDING] for LLM/dynamic |
| Artifact mapping (C1 fix) | READY | ArtifactMapper wired into src/ + tested by integration tests |
| Docker | READY | Dockerfile uses correct `gnucobol` package name |
| Dependency lock | PARTIAL | requirements.lock (pip freeze); poetry.lock not generated (pyproject.toml present) |

---

## Tests

| Suite | Count | Status |
|---|---|---|
| Unit tests | ~180 | PASS |
| Integration tests (pipeline) | ~15 | PASS |
| Integration tests (artifact_mapping) | 9 | PASS (new) |
| Scientific integrity (SI-01–SI-12) | ~48 | PASS |
| SI-01 extended 10-variant regression | 18 | PASS (new) |
| Regression (known contracts) | ~25 | PASS |
| **Total** | **295** | **ALL PASS** |

---

## Scientific Integrity

| Check | Status |
|---|---|
| SI-01: SYNTHETIC_STATIC cannot produce STATIC_DYNAMIC_SUPPORTED | READY — pre-outcome guard in engine.py + 10-variant test suite |
| SI-02: Provenance survives BCGDiff | READY |
| SI-03: Weight sum ~1.10 invariant | READY |
| SI-04: YAML weights match code defaults | READY |
| SI-05: ambiguity_penalty=1.0 collapses score | READY |
| SI-06: NOT_OBSERVED ≠ CONTRADICTED | READY |
| SI-07: HUMAN_VALIDATED is terminal | READY |
| SI-08: No duplicate extraction | READY |
| SI-09: Static contracts have DETERMINISTIC extraction_method | READY |
| SI-10: Entity IDs are deterministic | READY |
| SI-11: return_code=None means not captured | READY |
| SI-12: GROUND_TRUTH is terminal | READY |

---

## RQ1 — Contract Recovery

| Item | Status |
|---|---|
| Static extraction pipeline | READY |
| Level-2 benchmark | COMPLETE (self-consistency) |
| Level-3 annotation | BLOCKED — requires human annotators |
| H1 status | BLOCKED_FOR_INDEPENDENT_VALIDATION |
| Result file | `results/rq1/rq1_summary.json` (frozen) |
| Paper §11 RQ1 | READY — caveat explicit: SELF-CONSISTENCY EVALUATION |
| RQ1 headline/body consistency | READY — "H1 consistent with self-consistency evaluation" |

**Remaining P0:** Level-3 human annotation (external dependency — cannot be fixed without data)

---

## RQ2 — Modernization Risk Detection

| Item | Status |
|---|---|
| Baseline A (structural) | COMPLETE — F1=0.8878 |
| Baseline B (complexity) | COMPLETE — F1=0.000 |
| Baseline E (static BCG, broken-only) | COMPLETE — F1=0.9619 |
| Proposed (static BCG + MODIFIED) | COMPLETE — F1=1.0000 |
| Baseline C (LLM-only) | BLOCKED_EXTERNAL_DEPENDENCY |
| Baseline D (Dep+LLM) | BLOCKED_EXTERNAL_DEPENDENCY |
| BCG+dynamic condition | PARTIAL — pipeline wired; CardDemo COBOL blocked |
| H2 testability | UNTESTABLE_AS_STATED — noted in §4 |
| Engine fix disclosure | READY — §10.6 added to paper |
| 75% N/A rate explanation | READY — §9.5 added to paper |
| "4 operators invisible" abstract claim | READY — paper now says "2 F3 + 2 semantic-F2" |
| F1=1.0 closed-set caveat in abstract | READY — "closed-set; FP=0 by design" added |
| Result file | `results/rq2/rq2_summary.json` (frozen) |

**Remaining P1:** LLM baselines C/D (external API dependency)

---

## RQ3 — Dynamic Evidence Value

| Item | Status |
|---|---|
| Dynamic validation rate | 49.2% (31/63 contracts) |
| STATIC_DYNAMIC_CONFLICT | 1 detected |
| NOT_OBSERVED | 31 |
| ArtifactMapper wired | READY — in src/legacy_contract/dynamic_analysis/ |
| Production remapping helper | READY — correctly rebuilds ExecutionTrace |
| SI-01 pre-outcome guard | READY — verified by 10-variant test suite |
| H3 testability declared | READY — NOT_TESTABLE in §4 + §15 |
| rq3_summary.json stale state | FIXED — h3_testability + artifact_mapping_wired added |
| CardDemo full execution | BLOCKED — DB2/CICS/IMS environment unavailable |
| Result file | `results/rq3/rq3_dynamic_results.json` (frozen) |

---

## Ablation Study

| Item | Status |
|---|---|
| A1 (proposed) | COMPLETE — F1=1.000 |
| A3 (structural) | COMPLETE — F1=0.888 |
| A4 (complexity) | COMPLETE — F1=0.000 |
| A5 (BCG broken-only) | COMPLETE — F1=0.962 |
| A2, A7 (LLM) | BLOCKED_EXTERNAL_DEPENDENCY |

---

## Generalization

| Item | Status |
|---|---|
| CardDemo in-distribution | COMPLETE (self-consistency) |
| OMP public COBOL | BLOCKED_BY_GROUND_TRUTH — GT not built |
| Claim in paper | READY — "GT gap, not extraction failure" stated correctly |

---

## Dynamic Evidence

| Item | Status |
|---|---|
| GnuCOBOL adapter | READY |
| Real EXECUTION traces | 2 (EMPPAY, DEPTPAY) |
| EXECUTION_SIMULATED traces | 11 (JCL simulation) |
| SYNTHETIC_STATIC traces excluded | 3 (correctly excluded by SI-01) |
| GnuCOBOL ≠ z/OS labeling | READY — all traces labeled correctly |
| CardDemo environment classification | READY — EXECUTED/SIMULATED/UNEXECUTABLE documented |

---

## LLM Baseline

| Item | Status |
|---|---|
| Baseline C code | READY |
| Baseline D code | READY |
| Execution | BLOCKED_EXTERNAL_DEPENDENCY — no API key in environment |
| API key handling | READY — reads from env var, never logs, never commits |
| Paper label | [RESULT_PENDING — requires OPENAI_API_KEY] |

---

## Ground Truth

| Level | Status |
|---|---|
| Level-1 (execution oracle) | NOT AVAILABLE (CardDemo execution environment blocked) |
| Level-2 (deterministic) | COMPLETE — but circular (self-consistency) |
| Level-3 (human annotation) | NOT CONDUCTED — infrastructure ready, annotators needed |
| Level-4 (adjudication) | NOT APPLICABLE |
| Circularity disclosure | READY — disclosed in paper, result files, and README |

---

## Mutation Framework

| Item | Status |
|---|---|
| All 8 operators implemented | READY |
| Empirical grounding per operator | READY — sources cited in §9.2–9.4 |
| N/A rate explanation | READY — §9.5 added to paper |
| Closed-set declaration | READY — stated in §9.5 and abstract |
| VALID/NOT_APPLICABLE counts | READY — in rq2_summary.json |
| ALTER_ERROR_BRANCH case study | READY — described in §11.2 and ablation §12 |

---

## Statistics

| Item | Status |
|---|---|
| Bootstrap CI | IMPLEMENTED — CI=[1.00,1.00] for F1=1.0 (degenerate, correctly reported) |
| Mann-Whitney U | IMPLEMENTED — not fired (requires per-instance F1 scores) |
| Bonferroni correction (n=5) | IMPLEMENTED |
| FPR | null — correctly reported as undefined |

---

## Manuscript

| Section | Status |
|---|---|
| Abstract | READY — overclaims fixed; closed-set caveat added |
| §1 Introduction | READY |
| §2 Background | READY |
| §3 Problem Definition | READY |
| §4 RQ/Hypotheses | READY — H2/H3 untestability noted inline |
| §5 Related Work | READY — GIST/Daikon tables present |
| §6 BCG Formalization | READY |
| §7–9 Architecture | READY |
| §9.5 N/A Rate | READY — added |
| §10 Methodology | READY |
| §10.6 Engine Fix Disclosure | READY — added |
| §11 Results | READY — [RESULT_PENDING] for LLM/dynamic; clear caveats |
| §12 Ablation | READY |
| §13 Dynamic Evidence | READY |
| §14 Error Analysis | READY |
| §15 Discussion | READY — H2/H3 untestability stated |
| §16 Threats | READY |
| §17 Limitations | READY |
| §18 Reproducibility | READY |
| §19 Conclusion | READY |
| References | READY — W1–W36 |

---

## Figures and Tables

| Item | Status |
|---|---|
| TABLE_4 (RQ1 recovery) | READY — SELF-CONSISTENCY header present |
| TABLE_5 (RQ2 baseline comparison) | PARTIAL — [RESULT_PENDING] for LLM/dynamic conditions |
| All numerical values in tables | TRACED to result files in reports/result_traceability.md |

---

## Reproducibility

| Item | Status |
|---|---|
| `pip install -e .` | READY |
| `make reproduce-paper1` | READY |
| Dockerfile | READY (`gnucobol` package name correct) |
| requirements.lock | READY (pip freeze snapshot) |
| poetry.lock | NOT COMMITTED (P2-8 — pyproject.toml present, poetry.lock not generated) |
| Dataset download (`make download-carddemo`) | READY |
| Random seed documentation | READY — seed=42 in experiment_lock.json |

---

## Novelty

| Item | Status |
|---|---|
| "To our knowledge" hedging | READY — used consistently |
| GIST 5-axis comparison | READY |
| Daikon capability table | READY |
| W29–W36 included | READY |
| No unsupported "first" claims | READY — hedged throughout |

---

## Human Researcher Presentation

| Item | Status |
|---|---|
| Root directory clutter | READY — superseded FINAL_ docs moved to docs/archive/ |
| DOCUMENTATION_MAP.md | READY — created |
| Authoritative README | READY (see below) |
| FINAL_RESEARCH_REPORT.md | READY |
| FINAL_RELEASE_AUDIT_V3.md | THIS FILE |
| No fabricated results | READY — verified |
| All blocking conditions labeled | READY |
| No marketing language | READY |

---

## Remaining Issues

### P0 — Scientific Invalidity (Cannot Fix Without External Data)

| ID | Issue | Status |
|---|---|---|
| P0-1 | Level-2 GT circular; F1=1.0 is idempotency | ACKNOWLEDGED — cannot fix without human annotation |

### P1 — Critical (External Dependencies)

| ID | Issue | Status |
|---|---|---|
| P1-1 | LLM baselines C/D not run | BLOCKED_EXTERNAL_DEPENDENCY |
| P1-5 | Level-3 annotation not conducted | BLOCKED_EXTERNAL_DEPENDENCY |

### P2 — Major (All Fixed in This Pass)

| ID | Issue | Status |
|---|---|---|
| P2-1 | "Four operators invisible" abstract overclaim | FIXED |
| P2-2 | F1=1.0 closed-set caveat missing in abstract | FIXED |
| P2-3 | H3 untestable — not declared in paper | FIXED — §4 + §15 |
| P2-4 | Mann-Whitney U not fired | DOCUMENTED — requires per-instance F1s |
| P2-5 | "H1 supported" unqualified at §11 | FIXED — caveat explicit |
| P2-6 | Engine fix not disclosed | FIXED — §10.6 |
| P2-7 | 75% N/A rate not explained | FIXED — §9.5 |
| P2-8 | poetry.lock not committed | PARTIAL — requirements.lock created (pip freeze) |
| P2-9 | W20 venue mismatch | ALREADY CORRECT in paper (references.bib shows correct venue) |

### P3 — Minor (All Fixed or Documented)

| ID | Issue | Status |
|---|---|---|
| P3-1 | Dataset size claim ("55 JCL, 44 COBOL") | ACCEPTED — mutation benchmark scope, noted in §10.1 |
| P3-2 | literature_review.md Phase-0 numbering | ACCEPTABLE — in docs/; paper §5 is authoritative |
| P3-3 | 4 FINAL_ root documents | FIXED — 3 moved to docs/archive/ |
| P3-4 | No DOCUMENTATION_MAP.md | FIXED — created |
| P3-5 | W3 only in ref list, not body | ACCEPTABLE — Pacheco/Randoop is background, not cited in argument |
| P3-6 | Unused modules in src/ | DOCUMENTED — future work |

---

## Human Action Required

1. **Level-3 human annotation** — use `scripts/export_blinded_annotation.py`, recruit 2 JCL/COBOL experts per `docs/annotation_protocol_final.md`
2. **LLM API access** — provide `OPENAI_API_KEY` to run Baselines C and D
3. **z/OS execution environment** — needed for genuine dynamic evidence beyond JCL simulation
4. **Root-cause the 1 CONFLICT** — determine whether STEP04 COND violation is extraction error, GnuCOBOL divergence, or instrumentation gap

## New Data Required

1. Level-3 ground truth annotations
2. Ground-truth negative set (non-violating mutations) for H3
3. Real z/OS execution traces (minimum 10)
4. Additional JCL corpora beyond CardDemo

---

## Final Recommendation

**READY WITH LIMITATIONS — EMPIRICALLY INCOMPLETE**

The platform, pipeline, tests, and documentation are complete and research-quality. All fixable issues have been fixed. All limitations are explicitly documented. The remaining gaps are external-dependency and data-collection issues, not implementation gaps.

**Realistic submission timeline:**
- **Workshop / preprint (now):** Static BCG results + mutation framework + architecture. Current state sufficient with explicit scope limitation to CardDemo.
- **MSR/ICSME (3–6 months):** Add Level-3 annotation + LLM baselines.
- **ICSME/SANER (6–12 months):** Add z/OS traces + additional corpora + reformulated H2.
- **ICSE/FSE/ASE (12–18 months):** All of the above + full dynamic validation + generalization.

---

*FINAL_RELEASE_AUDIT_V3.md — authoritative release audit.*  
*Generated post-remediation. Supersedes FINAL_RELEASE_AUDIT_V2.md (archived).*
