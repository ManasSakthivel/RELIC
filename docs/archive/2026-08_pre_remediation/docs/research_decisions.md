# Research Decisions Log
## LEGACY-CONTRACT — Every Important Decision With Rationale

---

## Decision Format

Each decision is recorded as:

```
DECISION-ID
QUESTION
OPTIONS CONSIDERED
DECISION TAKEN
RATIONALE
TRADE-OFF
RESEARCH CONSEQUENCE
DATE
```

---

## D-001: BCG Formulation Selection

**QUESTION:** Which formal representation for BCG?

**OPTIONS:**
- F-I: Labeled Attributed Multi-Graph
- F-II: Temporal Logic Contract Hypergraph
- F-III: Relational Contract Database with Graph View
- Hybrid F-I + F-III storage

**DECISION:** Hybrid F-I (conceptual model) + relational storage with graph projection

**RATIONALE:** F-I provides formal clarity; F-III provides queryability and provenance richness. F-II is theoretically strongest but impractical for Paper 1 scope (LTL model checking overhead not justified).

**TRADE-OFF:** Lose formal LTL verification; gain implementability and queryability.

**RESEARCH CONSEQUENCE:** Cannot claim LTL-level formal verification. Can claim formal behavioral contract representation with provenance and evidence. Future work: extend `formal_statement` field to LTL formulas.

---

## D-002: Primary Dataset Selection

**QUESTION:** Which public legacy dataset to use?

**OPTIONS:**
- AWS CardDemo (Apache 2.0, fully public, JCL+COBOL+copybooks)
- Open Mainframe Project samples (limited JCL, mostly COBOL)
- Custom synthetic dataset
- IBM sample programs (license ambiguous — REJECTED)

**DECISION:** AWS CardDemo as primary dataset; OMPS as held-out supplement.

**RATIONALE:** CardDemo is the only publicly available, legally clear, realistic JCL+COBOL+copybook system with documented modernization use cases. OMPS supplements generalization testing.

**TRADE-OFF:** One primary system limits generalization claims.

**RESEARCH CONSEQUENCE:** Generalization evaluation must be limited to available public systems. Explicitly reported as a threat to external validity.

---

## D-003: Dynamic Evidence Generation Strategy

**QUESTION:** How to obtain execution evidence for public systems?

**OPTIONS:**
- Real z/OS execution (requires mainframe — unavailable)
- GnuCOBOL instrumented execution (feasible, open-source)
- Pure synthetic trace generation
- JCL batch simulation

**DECISION:** GnuCOBOL instrumented execution (primary) + JCL batch simulation (job-level ordering evidence)

**RATIONALE:** GnuCOBOL provides real execution of COBOL logic. JCL simulation captures batch job ordering. Together they cover both COBOL-level and job-level behavioral evidence.

**TRADE-OFF:** GnuCOBOL ≠ z/OS. Subtle mainframe-specific COBOL behaviors may differ. Must document as threat.

**RESEARCH CONSEQUENCE:** All dynamic evidence labeled `EXECUTION (GnuCOBOL environment)`. Never claimed as production mainframe traces.

---

## D-004: Confidence Score Interpretation

**QUESTION:** Should confidence be a probability?

**OPTIONS:**
- Statistical probability (requires calibration study)
- Normalized evidence-strength score
- Ordinal levels (HIGH/MEDIUM/LOW)

**DECISION:** Normalized evidence-strength score in [0,1] with transparent dimension weights.

**RATIONALE:** Interpreting as probability requires a calibration study with ground truth — feasible but would require substantially more annotated data than Paper 1 scope allows. Ordinal levels lose information. Evidence-strength score is transparent and non-misleading.

**TRADE-OFF:** Cannot make probabilistic claims about contract validity.

**RESEARCH CONSEQUENCE:** All results must say "confidence score" not "probability". The calibration question becomes a future-work item or Paper 2 contribution.

---

## D-005: LLM Role

**QUESTION:** Should LLM be central or optional?

**OPTIONS:**
- Central (LLM as primary extraction engine)
- Optional enrichment layer
- No LLM

**DECISION:** Optional enrichment layer. System must operate fully without LLM.

**RATIONALE:** LLM-only analysis is Baseline C. If BCG requires LLM to work, we cannot claim that the BCG representation itself is the contribution. The deterministic extraction must provide the core BCG; LLM adds optional enrichment.

**TRADE-OFF:** Deterministic extraction from JCL+COBOL requires good parsers; more engineering work.

**RESEARCH CONSEQUENCE:** Two experimental conditions: BCG (no LLM) vs BCG+LLM. This directly tests the LLM contribution independently.

---

## D-006: Paper 1 Scope Boundary

**QUESTION:** Which contract types in Paper 1?

**OPTIONS:**
- Temporal only (narrower, cleaner)
- Temporal + Resource + Control (three types, richer)
- All seven types (too broad)

**DECISION:** Temporal + Resource + Control-flow contracts for Paper 1.

**RATIONALE:** Three types map directly to the three most common real-world modernization failures (F1, F2, F3). Data and state contracts require copybook-level analysis infrastructure that would expand Paper 1 beyond a single coherent contribution.

**TRADE-OFF:** Narrower evaluation scope. Data contracts must wait for Paper 2.

**RESEARCH CONSEQUENCE:** Paper 1 claims are scoped to temporal/resource/control behavioral contract recovery for legacy batch systems.

---

## D-007: Mutation Empirical Grounding

**QUESTION:** How to ensure mutations are realistic?

**OPTIONS:**
- Derive from intuition
- Derive from literature only
- Derive from documented real-world failures (preferred)
- Derive from random program transformation

**DECISION:** Derive from documented real-world modernization failures (failure taxonomy docs/failure_taxonomy.md).

**RATIONALE:** Mutations derived from intuition create benchmark bias toward the proposed method. Empirically grounded mutations from documented real failures provide external validity.

**TRADE-OFF:** Fewer mutation operators (only what is empirically documented). More credible evaluation.

**RESEARCH CONSEQUENCE:** Each mutation must cite its empirical source. Reviewers can challenge the taxonomy on empirical grounds, not just design choices.
