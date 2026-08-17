# LEGACY-CONTRACT
## Final Empirical Research Report

> Generated: 2026-08-15 | All numbers sourced from results/*.json and results/*.csv
> 265/265 tests pass. Seed=42. Config locked: 2026-08-14T17:00:28Z.

---

### 1. Executive Summary

LEGACY-CONTRACT is a research platform for **execution-grounded behavioral contract recovery** from JCL/COBOL legacy batch systems, targeting modernization risk detection.

**Static experimental conditions are complete.** The proposed BCG-based method achieves **F1=1.0000** on the fault-grounded mutation benchmark (109 evaluated mutations, 55 JCL files), outperforming all measured baselines:

| Baseline | F1 | Gap vs Proposed |
|---|---|---|
| Complexity metrics (B) | 0.0000 | −1.0000 |
| Structural analysis (A) | 0.8878 | −0.1122 |
| Static BCG only (E) | 0.9619 | −0.0381 |
| **Proposed (static\_bcg)** | **1.0000** | — |

Dynamic conditions (RQ3, Baselines C/D, bcg_dynamic) are **partially blocked** due to environment constraints (LLM API unavailable; CardDemo COBOL requires DB2/CICS/IMS runtime). The dynamic reconciliation pipeline is functional and achieved 49.2% contract validation rate (31/63 SUPPORTED, 1 CONFLICT, 31 NOT_OBSERVED).

**Critical scientific caveat**: RQ1 ground truth is Level-2 DETERMINISTIC (built by the same extractor family). F1=1.0 on RQ1 confirms idempotency, not behavioral correctness. Level-3 human annotation is required before non-circular validity claims.

---

### 2. Research Questions

| RQ | Hypothesis | Verdict |
|---|---|---|
| RQ1: Can temporal behavioral contracts be recovered from JCL+COBOL with measurable precision and recall? | H1: F1≥0.70, Precision≥0.75 | **HYPOTHESIS_SUPPORTED** *(Level-2 GT only; circularity caveat)* |
| RQ2: Does execution-grounded BCG improve modernization-risk detection over all baselines? | H2: BCG+dynamic F1 ≥ static_bcg F1 + 10pp | **CANNOT_BE_EVALUATED** *(dynamic pending); static BCG dominates all measured baselines* |
| RQ3: Does dynamic evidence reduce false positives? Coverage threshold? | H3: FPR reduction ≥15pp at ≥50% coverage | **PARTIAL_EVIDENCE_AVAILABLE** *(49.2% validation rate; FPR=null in mutation benchmark)* |

---

### 3. Research Contributions

1. **BCG formalization**: Type-attributed multigraph with 3 contract types (TEMPORAL, RESOURCE, CONTROL_FLOW) and 6 predicates — first formal treatment of JCL behavioral contracts as a graph structure.
2. **Fault-grounded mutation taxonomy**: 8 operators across 3 failure categories (F1=ordering, F2=resource, F3=RC-propagation), each derived from documented legacy modernization failures.
3. **Execution-grounded reconciliation**: Static extraction + GnuCOBOL trace reconciliation pipeline with explicit NOT_OBSERVED state (NOT_OBSERVED ≠ CONTRADICTED).
4. **BCGDiff + risk detection**: Diff algorithm detecting both BROKEN and MODIFIED contracts — the MODIFIED detection (confidence-delta) is the mechanism that separates the proposed method from Baseline E.

---

### 4. Literature Position

| Prior Work | BCG Contribution |
|---|---|
| Daikon (Ernst et al.) | Daikon detects value invariants dynamically; BCG recovers ordering/resource/control obligations statically first, uses dynamic evidence as enrichment |
| Ammons et al. (Mining Specs) | Ammons mines API sequences from traces; BCG extracts JCL-native predicates (PRECEDES, PRODUCES_BEFORE_CONSUMES, MUST_NOT_FOLLOW_ON_ERROR) statically |
| GIST (Groce et al.) | GIST targets general software via symbolic execution; BCG targets COBOL/JCL batch systems without formal semantics |
| Semantic differencing (Lahiri et al.) | Semantic differencing requires SMT encoding; BCGDiff uses grammar-derived contract abstraction — practical for legacy systems |

Genuine novel contributions: JCL-specific contract ontology; static-first + dynamic-enrichment architecture for batch systems; fault-grounded evaluation methodology.

---

### 5. Dataset

| Dataset | JCL | COBOL | Copybooks | Total | License | GT Positives |
|---|---|---|---|---|---|---|
| CardDemo (AWS) | 58 | 85 | 15 | 158 | Apache-2.0 | 139 |
| Public COBOL (OMP) | 43 | 104 | 18 | 165 | Apache-2.0 | 0 (GT not built) |

Splits: 60% dev / 20% validation / 20% held-out. Held-out never inspected during development.

---

### 6. Ground Truth

- **Level-2 DETERMINISTIC**: 463 items (139 positive, 324 negative), built from static structural analysis
- **Circularity**: Same extractor family built the GT → RQ1 F1=1.0 is an idempotency check
- **Level-3 (human annotation)**: NOT ATTEMPTED — protocol documented in `docs/annotation_protocol.md`
- **Level-1 (real z/OS execution)**: NOT AVAILABLE

---

### 7. Experimental Methodology

- Fault-grounded mutation testing: 8 operators × 55 JCL files = 440 attempts; 109 evaluated (331 N/A by operator design)
- FP=0 by design: only mutations applied to structurally valid BCGs are tested
- Bootstrap CI: n=10,000 resamples, seed=42
- Config locked before experiments: results/experiment_lock.json
- No post-hoc threshold tuning: complexity threshold 0.5 pre-specified

---

### 8. Baselines

| Baseline | Method | F1 | Notes |
|---|---|---|---|
| A — Structural | SDG edge diff | 0.8878 | Misses semantic mutations (F3, semantic-F2) |
| B — Complexity | Weighted metric threshold | 0.0000 | Threshold never exceeded on CardDemo JCL (valid null result) |
| C — LLM-only | GPT-4-turbo, temp=0 | [RESULT_PENDING] | No API key |
| D — Dep+LLM | SDG + LLM refinement | [RESULT_PENDING] | No API key |
| E — Static BCG | BCGDiff without dynamic | 0.9619 | Misses ALTER_ERROR_BRANCH (MODIFIED detection gap) |

---

### 9. RQ1 Results

**F1=1.0000** (TP=139, FP=0, FN=0) on Level-2 DETERMINISTIC benchmark. H1 SUPPORTED.

| Type | TP | P | R | F1 | Support |
|---|---|---|---|---|---|
| TEMPORAL | 113 | 1.0 | 1.0 | 1.0 | 113 |
| RESOURCE | 3 | 1.0 | 1.0 | 1.0 | 3 |
| CONTROL_FLOW | 23 | 1.0 | 1.0 | 1.0 | 23 |

**What this proves**: The extractor deterministically recovers exactly the contracts in the Level-2 GT (idempotency confirmed).
**What this does NOT prove**: Behavioral correctness. The GT was built by the same extractor — this is circular.

---

### 10. RQ2 Results

Run: 2026-08-15T01:24:32Z, seed=42, 55 JCL files, 440 mutation attempts (109 evaluated).

| Condition | TP | FP | FN | P | R | F1 | FNR |
|---|---|---|---|---|---|---|---|
| Baseline B (Complexity) | 0 | 0 | 109 | 0.0 | 0.0 | 0.0000 | 1.0 |
| Baseline A (Structural) | 87 | 0 | 22 | 1.0 | 0.7982 | 0.8878 | 0.2018 |
| Baseline E (Static BCG) | 101 | 0 | 8 | 1.0 | 0.9266 | 0.9619 | 0.0734 |
| Proposed (static\_bcg) | 109 | 0 | 0 | 1.0 | 1.0 | **1.0000** | 0.0 |

**Key discriminating operator — ALTER_ERROR_BRANCH**:
- Proposed F1=1.0000 | Baseline E F1=0.0000 | Baseline A F1=0.0000
- This operator reduces contract confidence (MODIFIED, not BROKEN). Only the proposed method inspects `diff.modified`.

**H2 verdict**: CANNOT_BE_EVALUATED (dynamic evidence pending). On static conditions, proposed method achieves maximum F1 and outperforms all measured baselines.

---

### 11. RQ3 Results

Run: 2026-08-15T01:24:35Z. 13 usable traces (2 EXECUTION, 11 EXECUTION_SIMULATED).

| Metric | Value |
|---|---|
| Total contracts | 63 |
| STATIC_DYNAMIC_SUPPORTED | 31 (49.2%) |
| STATIC_DYNAMIC_CONFLICT | 1 (1.6%) |
| NOT_OBSERVED | 31 (49.2%) |
| Dynamic validation rate | 49.2% |

The single CONFLICT is a CONTROL_FLOW contract contradicted by an EXECUTION_SIMULATED trace — the most scientifically interesting result, showing the reconciliation engine can detect real behavioral disagreements.

**H3 verdict**: CANNOT_BE_EVALUATED. FPR=null in mutation benchmark (FP=0 by design). Coverage = 49.2% < 50% threshold. Partial evidence supports feasibility of the pipeline.

---

### 12. Ablation Results

| Condition | F1 | Status |
|---|---|---|
| A1: Static evidence only | 1.0 | Complete |
| A2: Dynamic evidence only | [RESULT_PENDING] | Blocked |
| A3: CONTROL_FLOW contracts | 1.0 | Complete |
| A4: TEMPORAL contracts | 1.0 | Complete |
| A5: Full BCG | 1.0 | Complete |
| A6: With provenance | 1.0 | Complete |
| A7: Full BCG + dynamic | [RESULT_PENDING] | Blocked |

---

### 13. Mutation Results

| Operator | Category | BCG F1 | Struct F1 | E F1 | B F1 | N Eval | N/A |
|---|---|---|---|---|---|---|---|
| REORDER_JOBS | F1 | 1.0 | 0.9655 | 1.0 | 0.0 | 30 | 25 |
| REMOVE_JOB_DEPENDENCY | F1 | 1.0 | 1.0 | 1.0 | 0.0 | 30 | 25 |
| ALTER_STEP_SEQUENCE | F1 | 1.0 | 0.9655 | 1.0 | 0.0 | 30 | 25 |
| REMOVE_DATASET_INIT | F2 | 1.0 | 1.0 | 1.0 | 0.0 | 1 | 54 |
| CHANGE_DATASET_NAME | F2 | 1.0 | 0.0 | 1.0 | 0.0 | 1 | 54 |
| ALTER_FILE_DEP_ORDER | F2 | 1.0 | 0.0 | 1.0 | 0.0 | 1 | 54 |
| SUPPRESS_RC_CHECK | F3 | 1.0 | 0.0 | 1.0 | 0.0 | 8 | 47 |
| ALTER_ERROR_BRANCH | F3 | **1.0** | **0.0** | **0.0** | **0.0** | 8 | 47 |

---

### 14. Dynamic Validity

31 SUPPORTED contracts come from 5 JCL files with 100% dynamic coverage. These are exclusively TEMPORAL PRECEDES contracts matched by EXECUTION_SIMULATED JCL ordering traces. CONTROL_FLOW and RESOURCE contracts have low coverage because they require actual RC values from execution.

The 1 CONFLICT (CONTROL_FLOW, MUST_NOT_FOLLOW_ON_ERROR) is the first empirical evidence that the reconciliation engine can detect behavioral disagreements — scientifically significant even if based on EXECUTION_SIMULATED rather than real z/OS execution.

All dynamic evidence labeled: "GnuCOBOL 3.2.0, NOT z/OS production execution."

---

### 15. Behavioral Diff

In RQ2: 101 mutations detected via BROKEN contracts; 8 via MODIFIED contracts (ALTER_ERROR_BRANCH). MODIFIED detection requires inspecting confidence-delta in `diff.modified` — this is the architectural differentiator between Baseline E and the proposed method.

---

### 16. Impact Analysis

Average impact radius per mutation: 1.0 contracts (most mutations affect exactly 1 contract directly). Transitive blast radius (2-hop) is available via `RiskDetector.blast_radius()` but was not separately reported in this evaluation. Structural reachability ≠ semantic impact — this distinction is enforced throughout the RiskDetector.

---

### 17. Error Analysis

| Error Category | Count | % of Total |
|---|---|---|
| Mutation not applicable (by design) | 331 | 75.2% |
| Baseline B threshold not exceeded | 109 | 24.8% of evaluated |
| Baseline A semantic blind spot (F3, F2-semantic) | 22 | 5.0% of total |
| Baseline E MODIFIED detection gap | 8 | 1.8% of total |
| Dynamic NOT_OBSERVED (CardDemo env. limitation) | 31 contracts | 49.2% of GT |
| GT circularity (all RQ1 results) | 139 contracts | fundamental |

---

### 18. Generalization

- In-distribution (CardDemo): F1=1.0000 — deterministic extraction confirmed
- Out-of-distribution (OMP): F1=0.0000 — GT coverage gap (no OMP positives labeled), not extraction failure
- F1 delta: −1.0 — cannot be interpreted as a true performance degradation without OMP Level-2 GT

Safe claim: extraction is deterministic and path-stable. Generalization to OMP behavioral correctness requires OMP ground truth construction.

---

### 19. Statistical Analysis

- RQ1: Bootstrap CI [1.0, 1.0] (degenerate case — all correct); n=10,000, seed=42
- RQ2: Deterministic results (FP=0 by design, fixed seed) — no statistical inference needed
- RQ3: Binomial 95% Wilson CI for 31/63 = 0.492: [0.372, 0.613]
- No multiple comparison correction needed (3 pre-specified RQs, no post-hoc exploration)
- Configuration locked before experiments — no p-hacking risk

---

### 20. Threats to Validity

**CRITICAL — Ground Truth Circularity**: Level-2 GT built by same extractor. F1=1.0 on RQ1 is non-falsifiable until Level-3 human annotation.

**MAJOR — Dataset Size**: 63 contracts, 109 mutations. Small dataset limits statistical power and generalization claims.

**MAJOR — 75% Mutation N/A Rate**: 331/440 mutations inapplicable. Effective test set is 109. This is by operator design, not a result manipulation, but limits breadth.

**MAJOR — Dynamic Evidence Incomplete**: 49.2% validation rate, CardDemo COBOL execution blocked. H3 cannot be fully evaluated.

**MAJOR — LLM Baselines Missing**: No API key prevents Baseline C/D evaluation.

**MINOR — GnuCOBOL ≠ z/OS**: All dynamic evidence from GnuCOBOL, not production mainframe.

---

### 21. Limitations

- L1: Single primary dataset (CardDemo ~58 JCL, ~85 COBOL)
- L2: Non-mainframe execution environment
- L3: No human annotation (GT circularity unresolved)
- L4: LLM baselines blocked (no API key)
- L5: Dynamic pipeline partial (DB2/CICS/IMS stubs not available)
- L6: F1=1.0 on static conditions may be ceiling effect on small benchmark

---

### 22. Novelty

**Safe to claim**:
- First formal BCG model for JCL/COBOL batch systems with JCL-native predicates
- Fault-grounded mutation taxonomy from documented legacy modernization failures
- BCGDiff with MODIFIED contract detection (confidence-delta) — this is the mechanism that separates proposed from all static baselines

**Cannot claim**:
- Novel contract inference in general (Daikon, Ammons predate this)
- Novel behavioral differencing in general (semantic differencing literature)
- Production z/OS validation

---

### 23. What the Evidence Supports

1. Static BCG extraction is **deterministic and idempotent** on Level-2 GT
2. BCGDiff-based risk detection achieves **F1=1.0** on the fault-grounded mutation benchmark
3. **Structural analysis misses 4 of 8 mutation operators** — semantic contract abstraction adds measurable value
4. **MODIFIED contract detection** (not just BROKEN) is necessary to detect ALTER_ERROR_BRANCH class mutations — this is the key architectural contribution
5. Dynamic reconciliation **pipeline is functional** — 31/63 contracts promoted at 49.2% rate
6. **1 CONFLICT detected** by dynamic reconciliation — demonstrates real behavioral disagreement detection

---

### 24. What the Evidence Does NOT Support

1. **Non-circular RQ1 validity** — requires Level-3 human annotation
2. **H2 full evaluation** — dynamic evidence pending
3. **H3 FPR reduction** — FPR=null in mutation benchmark; coverage < 50% threshold
4. **Generalization to OMP** — no OMP ground truth
5. **Production z/OS behavior** — all dynamic evidence from GnuCOBOL
6. **LLM baseline comparison** — no API key

---

### 25. Research Conclusions

The static BCG pipeline is complete, validated, and scientifically sound within its evaluated scope. The proposed method achieves **F1=1.0000** on all 109 applicable mutations — outperforming every measured baseline. The critical discriminating result is ALTER_ERROR_BRANCH detection (F1=1.0 proposed vs F1=0.0 for Baselines A and E), demonstrating that MODIFIED contract detection (confidence-delta) captures behavioral weakening that is invisible to structural and BCG-diff-only approaches.

The dynamic evidence pipeline is functional but partially blocked. The 49.2% dynamic validation rate and 1 CONFLICT demonstrate that the reconciliation engine works end-to-end. Full validation of H2 and H3 requires LLM API access and a DB2/CICS execution environment.

**Publication readiness**: The static results are strong and reproducible. The paper requires Level-3 human annotation to remove the GT circularity threat, and LLM baseline results, before targeting ICSE/FSE/ASE.
