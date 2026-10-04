# Novelty Analysis
## LEGACY-CONTRACT — Prior-Art Capability Matrix, Novelty Map, Gap Analysis

---

## PART 1: PRIOR-ART CAPABILITY MATRIX

Each cell: ✓ (fully addressed), ~ (partially addressed), ✗ (not addressed)

| Capability Dimension | Daikon (W4) | Klaedtke (W1) | Flanagan (W5) | Naik (W10) | Sneed (W11) | Pessoa (W28) | Meyer DbC (W19) | Tonella (W24) | **This Work** |
|---|---|---|---|---|---|---|---|---|---|
| Behavioral contracts (not just invariants) | ~ | ✓ | ~ | ✗ | ✗ | ~ | ✓ | ✗ | **✓** |
| Temporal ordering contracts (A ≺ B) | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | **✓** |
| Resource dependency contracts | ✗ | ✗ | ✗ | ✗ | ~ | ✗ | ✗ | ✗ | **✓** |
| Control-flow obligation contracts | ✗ | ~ | ✓ | ✗ | ✗ | ~ | ✓ | ✗ | **✓** |
| Cross-artifact (multi-language) | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | **✓** |
| JCL artifact support | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | **✓** |
| COBOL artifact support | ✗ | ✗ | ✗ | ✗ | ✓ | ✓ | ✗ | ✗ | **✓** |
| Copybook / record structure support | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | **✓** |
| Formal intermediate representation (IR) | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | **✓** |
| Static evidence extraction | ~ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ~ | **✓** |
| Dynamic evidence extraction | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ | ✓ | **✓** |
| Static/dynamic reconciliation | ~ | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ | **✓** |
| Explicit conflict detection (S vs D) | ✗ | ✗ | ✗ | ~ | ✗ | ✗ | ✗ | ✗ | **✓** |
| Contract provenance tracking | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | **✓** |
| Contract confidence model | ~ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | **✓** |
| Contract validation states | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | **✓** |
| Modernization-risk use case | ✗ | ✗ | ✗ | ✗ | ~ | ✓ | ✗ | ✗ | **✓** |
| Fault-grounded mutation engine | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | **✓** |
| Counterfactual contract preservation | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | **✓** |
| Evidence sufficiency analysis | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | **✓** |
| Execution oracle for ground truth | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | **✓** |
| Dynamic coverage variation experiment | ✗ | ~ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | **✓** |

---

## PART 2: NOVELTY MAP

### 2.1 — ESTABLISHED (Do Not Claim as Novel)

The following components are established prior art and must be acknowledged:

| Component | Established by | Notes |
|-----------|---------------|-------|
| Behavioral contract concept | Meyer 1992, Leavens+Weihl 1990 | DbC paradigm |
| Dynamic invariant inference | Daikon (Ernst et al. 2007) | Data invariants, OO |
| Temporal specification formalism | LTL (Clarke et al. 1986), Barnett+Schulte 2003 | Foundations |
| Static dependency analysis | Tip 1995 | Program slicing |
| COBOL static analysis | Sneed 2008, Pessoa et al. 2022 | Precedent exists |
| Execution trace → source mapping | Tonella et al. 2003 | Feature location |
| DFA-based behavioral mining | Klaedtke et al. 2021 | Pure-dynamic |
| Static+dynamic for false-positive reduction | Naik et al. 2006 | Race detection |
| LLM for code understanding | Hou et al. 2024, Fan et al. 2023 | Widely studied |

### 2.2 — INCREMENTALLY NOVEL (Acknowledge Individually)

| Component | Prior Context | Incremental Contribution |
|-----------|--------------|--------------------------|
| Cross-artifact static analysis (JCL+COBOL) | Sneed 2008 does COBOL alone | Extending to JCL-COBOL joint analysis is new |
| Contract extraction from JCL | No prior work identified | Mechanistic extraction of temporal facts from JCL grammar |
| COBOL behavioral contract extraction | Pessoa does semantic diff, not contracts | Contract-form extraction (pre/post/ordering) from COBOL |
| Evidence normalization schema | No standardized schema found | Normalizing heterogeneous legacy execution events |

### 2.3 — POTENTIALLY NOVEL (The Claimed Contribution)

These dimensions have no direct precedent in the literature:

| Dimension | Justification |
|-----------|--------------|
| **Cross-artifact behavioral contract graph (BCG) for JCL+COBOL** | No prior work represents behavioral obligations jointly across JCL jobs and COBOL programs in a formal IR |
| **Provenance-aware contract intermediate representation** | No prior contract IR tracks evidence source, extraction method, confidence, and validation state per contract |
| **Static/dynamic reconciliation with explicit conflict taxonomy** | Naik et al. reconcile for race detection; no work applies this pattern to cross-artifact behavioral contracts |
| **Execution-grounded contract validation for legacy batch** | Daikon validates invariants dynamically for OO; no equivalent for legacy batch temporal contracts |
| **Fault-grounded mutation engine from empirical modernization failures** | No prior mutation framework derives operators from documented real-world mainframe modernization regressions |
| **Counterfactual contract preservation analysis** | No prior work frames modernization as: "which contracts are preserved/violated and what minimal change restores them?" |
| **Contract confidence calibration with evidence-dimension model** | No prior work defines a calibrated multi-dimensional confidence model for behavioral contracts |

---

## PART 3: GAP ANALYSIS

### Gap 1 — Cross-artifact behavioral representation
No existing system represents behavioral obligations that span JCL job scheduling, COBOL program execution, and file-level resource dependencies in a single formal graph. Existing tools are siloed: COBOL analyzers do not model JCL semantics; JCL analyzers do not model COBOL behavioral contracts.

### Gap 2 — Execution-grounded contract validation for batch legacy
Daikon and related tools perform dynamic contract inference for OO systems. No equivalent exists for mainframe batch systems where "execution" means a JCL job stream producing output files, triggering COBOL programs in sequence. The execution model is fundamentally different.

### Gap 3 — Static/dynamic reconciliation with explicit status
Naik et al. combine static and dynamic evidence for race detection. No work applies this pattern to behavioral contracts across heterogeneous legacy artifacts with explicit reconciliation outcomes (SUPPORTED, CONTRADICTED, UNOBSERVED, AMBIGUOUS, PARTIALLY_SUPPORTED).

### Gap 4 — Provenance-aware contract IR
No existing contract IR maintains fine-grained provenance: source artifact, line number, extraction method, model version, confidence dimensions, and validation state simultaneously per contract.

### Gap 5 — Empirically grounded fault model for mainframe modernization
No prior mutation testing framework derives operators from documented public evidence of mainframe-to-cloud modernization failures. Existing mutation frameworks (e.g., Offutt et al.) target general program mutation, not semantic contract violations introduced during legacy-to-modern platform migration.

### Gap 6 — Contract preservation as a modernization criterion
No prior work frames the modernization problem as: "Does the modernized system preserve the behavioral contract set of the original?" Pessoa et al. perform semantic differencing but without a contract-level abstraction.

---

## PART 4: SMALLEST DEFENSIBLE NOVELTY CLAIM

To satisfy a skeptical reviewer, the minimum claim is:

> **We present the first formal intermediate representation (BCG) that jointly encodes behavioral obligations extracted from heterogeneous legacy batch artifacts (JCL + COBOL), reconciles static and dynamic evidence with explicit provenance and conflict detection, and applies this representation to modernization-risk detection using an empirically grounded fault model.**

This claim is defensible because:
1. No prior IR spans JCL+COBOL behavioral contracts simultaneously.
2. No prior system reconciles static vs. dynamic evidence for such contracts with explicit conflict status.
3. No prior mutation framework derives operators from documented mainframe modernization regressions.
4. The combination has not been published.

---

## PART 5: WHAT NOT TO CLAIM

Do NOT claim:
- "First behavioral contract system" — Meyer 1992 predates.
- "First dynamic contract inference" — Daikon 2007 predates.
- "First static+dynamic analysis" — Naik et al. 2006 predates.
- "First COBOL analysis tool" — Sneed 2008, Pessoa et al. 2022 predate.
- "First legacy modernization analysis" — Comella-Dorda 2000 survey shows decades of prior work.
- "First graph-based program representation" — PDG, CDG, SDG all predate.

The novelty is in the **combination, the specific application domain, the formal IR design, and the experimental investigation of whether execution grounding improves behavioral contract quality for modernization risk detection.**
