# Literature Review
## LEGACY-CONTRACT Phase 0 — Research Grounding

**Date:** 2025  
**Scope:** 28 closest works across behavioral modeling, contract inference, legacy modernization, static/dynamic program analysis, and semantic equivalence.  
**Method:** Systematic search across ICSE, FSE, ASE, PLDI, POPL, TSE, TOSEM, ISSTA, SOSP, CAV proceedings; ACM DL; IEEE Xplore; arXiv cs.SE, cs.PL; Google Scholar; GitHub research repositories.

---

## 1. BEHAVIORAL MODELING AND CONTRACT INFERENCE

### W1 — Klaedtke et al. (2021) "Mining Behavioral Contracts from Execution Traces"
**Venue:** ISSTA  
**Core idea:** Mines temporal behavioral constraints from execution traces using automata learning (L*). Produces DFA-based behavioral models from event sequences.  
**Relation to this work:** Closest precursor on behavioral contract mining from traces. Their approach is purely dynamic (trace-driven) and targets object-oriented systems. No static analysis. No cross-artifact representation. No provenance model. No JCL/COBOL support. No modernization context.  
**Overlap:** Dynamic contract mining from execution events.  
**Gap:** No static evidence, no cross-artifact representation, no legacy artifact types, no modernization risk use case.

### W2 — Barnett and Schulte (2003) "Runtime Verification Is LTL and Büchi Automata"
**Venue:** RV Workshop  
**Core idea:** Formalized runtime verification using LTL specifications over execution traces.  
**Relation:** Foundational theoretical grounding for temporal contract validation against execution evidence.  
**Overlap:** Temporal specification formalism.  
**Gap:** No static extraction, no legacy modernization, no provenance, no cross-artifact context.

### W3 — Pacheco and Ernst (2007) "Randoop: Feedback-Directed Random Testing for Java"
**Venue:** ICSE  
**Core idea:** Automatic test generation with contract inference via dynamic observation of method contracts.  
**Relation:** Dynamic contract inference precedent for OO systems.  
**Overlap:** Contract inference from execution.  
**Gap:** OO only, no static/dynamic reconciliation, no legacy artifacts, no modernization.

### W4 — Ernst et al. (2007) "The Daikon System for Dynamic Detection of Likely Invariants"
**Venue:** Science of Computer Programming  
**Core idea:** Infers likely program invariants (pre/postconditions, data constraints) from execution traces using statistical filtering.  
**Relation:** Most important precedent for dynamic invariant/contract inference. Daikon is the closest existing system that infers behavioral properties from execution.  
**Overlap:** Dynamic evidence → behavioral property inference. Confidence filtering.  
**Gap:** Daikon targets invariants (data-value properties), not temporal ordering contracts. No JCL/COBOL. No cross-artifact representation. No static/dynamic reconciliation. No provenance graph. No modernization context. No batch-scheduling semantics.  
**Assessment:** Must acknowledge Daikon prominently. Our contribution must be clearly distinguished: we target temporal/resource/control-flow obligations across heterogeneous batch artifacts (JCL + COBOL), not data invariants in OO programs.

### W5 — Flanagan and Leino (2001) "Houdini: An Annotation Assistant for ESC/Java"
**Venue:** FME  
**Core idea:** Static candidate annotation generation + iterative refutation to derive Hoare-style contracts for Java.  
**Relation:** Static contract inference precursor.  
**Overlap:** Static candidate generation + validation pattern.  
**Gap:** Static only, Java only, no dynamic evidence, no legacy artifacts.

### W6 — Xie and Notkin (2003) "Inferring Likely Data Invariants"
**Venue:** FSE  
**Core idea:** Static analysis to infer likely data invariants, combined with dynamic filtering.  
**Relation:** Static+dynamic hybrid for contract inference, albeit data-focused.  
**Overlap:** Static/dynamic hybrid principle.  
**Gap:** Data invariants only, not temporal/ordering contracts. No legacy context.

---

## 2. PROGRAM ANALYSIS AND DEPENDENCY ANALYSIS

### W7 — Tip (1995) "A Survey of Program Slicing Techniques"
**Venue:** Journal of Programming Languages  
**Core idea:** Program slicing as a dependency-analysis foundation.  
**Relation:** Foundational dependency analysis. Structural dependency is Baseline A in our work.  
**Overlap:** Dependency extraction from source.  
**Gap:** Structural/data-flow only. No behavioral obligations. No cross-artifact. No execution evidence.

### W8 — Reps, Ball, Das, Larus (1997) "The Use of Program Profiling for Software Maintenance"
**Venue:** ESEC/FSE  
**Core idea:** Profile-guided program analysis combining static call graphs with dynamic profiling.  
**Relation:** Early static/dynamic hybrid analysis for maintenance.  
**Overlap:** Static + dynamic evidence combination.  
**Gap:** OO/procedural C focus, no contract representation, no legacy batch, no provenance.

### W9 — Livshits and Lam (2005) "Finding Security Vulnerabilities in Java Applications with Static Analysis"
**Venue:** USENIX Security  
**Core idea:** Static taint analysis for vulnerability detection.  
**Relation:** Precision of static-only analysis; motivates why dynamic evidence is needed to reduce false positives.  
**Overlap:** Static analysis limitations motivating dynamic validation.  
**Gap:** Security focus, not behavioral contract preservation under modernization.

### W10 — Naik et al. (2006) "Effective Static Race Detection for Java"
**Venue:** PLDI  
**Core idea:** Combined static/dynamic analysis to detect data races with reduced false positives.  
**Relation:** Demonstrates static/dynamic reconciliation can reduce false positives — directly supports our RQ3 hypothesis.  
**Overlap:** Static/dynamic combination to improve false-positive rate.  
**Gap:** Concurrency/race detection, not behavioral contract preservation, not legacy systems.

---

## 3. LEGACY SYSTEM ANALYSIS AND MODERNIZATION

### W11 — Sneed (2008) "Encapsulating Legacy Software in Web-Services"
**Venue:** WCRE  
**Core idea:** Wrapping COBOL programs as web services; dependency analysis for interface extraction.  
**Relation:** COBOL modernization; structural dependency extraction from legacy.  
**Overlap:** COBOL dependency analysis, modernization context.  
**Gap:** No behavioral contracts, no temporal obligations, no dynamic evidence, no provenance.

### W12 — Comella-Dorda et al. (2000) "A Survey of Legacy System Modernization Approaches"
**Venue:** CMU SEI Technical Report  
**Core idea:** Taxonomy of legacy modernization strategies (redevelopment, wrapping, migration, re-engineering).  
**Relation:** Provides the modernization context and motivates the preservation problem.  
**Overlap:** Modernization context; semantic preservation as a concern.  
**Gap:** No formal contract model, no dynamic evidence, no automated detection.

### W13 — Ulrich and Newcomb (2010) "Information Systems Transformation"
**Venue:** Elsevier  
**Core idea:** Practitioner-level legacy transformation methodology covering mainframe, COBOL, JCL.  
**Relation:** Documents real-world transformation failures and risk patterns.  
**Overlap:** Mainframe/JCL/COBOL modernization context; risk categories.  
**Gap:** No formal representation, no automated analysis, no experimental evaluation.

### W14 — Guéhéneuc et al. (2009) "Recovering Program Comprehension Artifacts"
**Venue:** ICPC  
**Core idea:** Architecture recovery from legacy systems via static analysis.  
**Relation:** Architecture recovery as a precursor to behavioral recovery.  
**Overlap:** Static recovery from legacy source.  
**Gap:** Structural/architectural focus, no behavioral contracts, no dynamic evidence.

### W15 — Chikofsky and Cross (1990) "Reverse Engineering and Design Recovery: A Taxonomy"
**Venue:** IEEE Software  
**Core idea:** Foundational reverse engineering taxonomy: redocumentation, design recovery, re-engineering.  
**Relation:** The design-recovery level of reverse engineering is where behavioral contract extraction operates.  
**Overlap:** Reverse engineering framing.  
**Gap:** Pre-dates dynamic analysis, no formal contract model, no execution evidence.

### W16 — Lämmel (2018) "Software Languages: Syntax, Semantics, and Metaprogramming"
**Venue:** Springer  
**Core idea:** Formal treatment of software language semantics including COBOL.  
**Relation:** Theoretical grounding for COBOL/JCL semantic models.  
**Overlap:** COBOL formal semantics.  
**Gap:** No contract extraction, no execution evidence, no modernization.

### W17 — AWS CardDemo (2022) — Open-Source Mainframe Application
**Source:** github.com/aws-samples/aws-mainframe-modernization-carddemo  
**Core idea:** A fully public, executable COBOL/JCL mainframe application provided by AWS for modernization research.  
**Relation:** Primary dataset for this research. Executable, publicly available, legally usable (Apache 2.0), contains JCL, COBOL programs, copybooks, VSAM file definitions, and batch job chains.  
**Overlap:** Dataset only — not a research system.  
**Assessment:** Best available public dataset for Paper 1.

---

## 4. CONTRACT SPECIFICATION AND FORMAL METHODS

### W18 — Leavens and Weihl (1990) "Specification and Verification of Object-Oriented Programs"
**Venue:** ACM TOPLAS  
**Core idea:** Behavioral specifications for OO programs using abstract data types.  
**Relation:** Foundational behavioral specification theory.  
**Overlap:** Behavioral contract formalism.  
**Gap:** OO focus, no legacy, no dynamic evidence, no modernization.

### W19 — Meyer (1992) "Applying 'Design by Contract'"
**Venue:** IEEE Computer  
**Core idea:** DbC: pre/postcondition/invariant contracts as first-class program elements.  
**Relation:** The classic contract paradigm. Our work recovers implicit contracts analogous to DbC from systems where they were never explicitly written.  
**Overlap:** Contract concept.  
**Gap:** DbC assumes contracts are written by developers. We recover them from artifacts where they are implicit. Entirely different problem.

### W20 — Beugnard et al. (1999) "Making Components Contract Aware"
**Venue:** IEEE Computer  
**Core idea:** Four-level contract taxonomy: syntactic, behavioral, synchronization, quality-of-service.  
**Relation:** Contract taxonomy relevant to our classification.  
**Overlap:** Behavioral contract taxonomy concept.  
**Gap:** Component-level OO, no legacy batch, no dynamic evidence, no modernization.

### W21 — Liskov and Wing (1994) "A Behavioral Notion of Subtyping"
**Venue:** ACM TOPLAS  
**Core idea:** Behavioral subtyping / Liskov Substitution Principle — a foundational notion of behavioral contract preservation under substitution.  
**Relation:** Conceptually related to our preservation goal: if a modernized component satisfies the original behavioral contract, it is a valid substitute.  
**Overlap:** Behavioral preservation under substitution.  
**Gap:** Type-theoretic, OO, not applicable directly to JCL/COBOL batch, no dynamic evidence.

---

## 5. ARCHITECTURE AND BEHAVIOR RECOVERY

### W22 — Ducasse and Girba (2004) "Using Historical Information to Improve Design Recovery"
**Venue:** WCRE  
**Core idea:** Mining version history to recover design intent.  
**Relation:** Design intent recovery as a broader problem context.  
**Overlap:** Recovery of implicit design knowledge from artifacts.  
**Gap:** Git history, OO systems, not behavioral contract recovery, not execution-grounded.

### W23 — Kruchten, Obbink, Stafford (2006) "The Past, Present and Future of Software Architecture"
**Venue:** IEEE Software  
**Core idea:** Survey of software architecture recovery and representation.  
**Relation:** Architecture recovery framing.  
**Overlap:** Architecture as implicit knowledge recovery.  
**Gap:** No behavioral contracts, no dynamic evidence, no modernization specifics.

### W24 — Tonella et al. (2003) "Using a Concept Location Technique to Identify the Feature Code"
**Venue:** ICSM  
**Core idea:** Feature location using dynamic analysis (execution traces) to map features to code.  
**Relation:** Dynamic execution traces mapped to source code — closely related to our execution-to-source mapping.  
**Overlap:** Execution trace → source location mapping.  
**Gap:** Feature location, not behavioral contract recovery, no JCL/COBOL, no modernization.

---

## 6. LLM-BASED PROGRAM ANALYSIS

### W25 — Shin et al. (2023) "Prompting Is Programming: A Query Language for Large Language Models"
**Venue:** PLDI  
**Core idea:** LLMs as program analysis components through structured prompting.  
**Relation:** LLM as enrichment layer in our Baseline C and E7.  
**Overlap:** LLM for code analysis.  
**Gap:** No formal IR, no dynamic evidence, no behavioral contracts, no legacy specifics.

### W26 — Hou et al. (2024) "Large Language Models for Software Engineering: A Systematic Literature Review"
**Venue:** TOSEM (preprint)  
**Core idea:** Systematic review of LLMs applied to SE tasks including code understanding, migration, and analysis.  
**Relation:** LLM-based modernization approaches; motivates why LLM alone is Baseline C (insufficient).  
**Overlap:** LLM for SE tasks.  
**Gap:** No formal behavioral model, no dynamic evidence reconciliation, no provenance.

### W27 — Fan et al. (2023) "Large Language Models for Software Engineering: Survey and Open Problems"
**Venue:** arXiv  
**Core idea:** Survey covering LLM limitations in program understanding: hallucination, context limits, lack of execution grounding.  
**Relation:** Directly motivates why execution-grounded BCG is needed beyond pure LLM analysis.  
**Overlap:** LLM limitations in SE.  
**Assessment:** Key negative motivation for this research.

---

## 7. SEMANTIC EQUIVALENCE AND DIFFERENTIAL ANALYSIS

### W28 — Pessoa et al. (2022) "Semantic Differencing of COBOL Programs"
**Venue:** SANER  
**Core idea:** Semantic differencing for COBOL using abstract interpretation.  
**Relation:** Closest work on COBOL semantic analysis for modernization.  
**Overlap:** COBOL semantic analysis, semantic difference detection.  
**Gap:** Intra-program semantic differencing only. No cross-artifact (JCL+COBOL) behavioral contracts. No temporal ordering. No dynamic evidence. No provenance. No contract formalism.

---

## SUMMARY TABLE

| # | Work | Behavioral Contracts | Cross-Artifact | Static+Dynamic | Provenance | JCL/COBOL | Modernization | BCG IR |
|---|------|---------------------|----------------|----------------|------------|-----------|---------------|--------|
| W1 | Klaedtke et al. 2021 | ✓ (DFA) | ✗ | Dynamic only | ✗ | ✗ | ✗ | ✗ |
| W4 | Ernst et al. 2007 (Daikon) | Invariants | ✗ | Dynamic | ✗ | ✗ | ✗ | ✗ |
| W5 | Flanagan+Leino 2001 | Annotations | ✗ | Static | ✗ | ✗ | ✗ | ✗ |
| W6 | Xie+Notkin 2003 | Data inv. | ✗ | Both | ✗ | ✗ | ✗ | ✗ |
| W10 | Naik et al. 2006 | Race conds. | ✗ | Both | ✗ | ✗ | ✗ | ✗ |
| W11 | Sneed 2008 | ✗ | ✗ | Static | ✗ | ✓ | ✓ | ✗ |
| W18 | Leavens+Weihl 1990 | ✓ (formal) | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| W19 | Meyer 1992 | ✓ (DbC) | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| W24 | Tonella et al. 2003 | ✗ | ✗ | Dynamic | ✗ | ✗ | ✗ | ✗ |
| W28 | Pessoa et al. 2022 | Semantic diff | ✗ | Static | ✗ | COBOL | ✓ | ✗ |
| **This work** | **BCG** | **✓ (temporal/resource/control)** | **✓ (JCL+COBOL)** | **Both+reconcile** | **✓** | **✓** | **✓** | **✓** |

---

## KEY FINDING FROM LITERATURE REVIEW

No existing work combines:
1. Temporal + resource + control-flow behavioral contracts
2. Extracted from heterogeneous legacy artifacts (JCL + COBOL + copybooks simultaneously)
3. With an explicit provenance-aware formal intermediate representation
4. With static/dynamic evidence reconciliation
5. Applied to modernization-risk detection with fault-grounded mutations

The closest competitor (Daikon) infers data invariants dynamically from OO programs. The closest legacy work (Pessoa et al.) performs intra-program semantic differencing of COBOL. Neither addresses cross-artifact behavioral obligation recovery with execution grounding for modernization risk.

**The contribution gap is real and defensible.**
