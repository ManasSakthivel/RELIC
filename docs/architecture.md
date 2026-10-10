# Architecture

> **Note.** The diagram below shows the full RELIC codebase structure.
> The **evaluated system** is strictly the JCL-only static analysis path:
> `JCL text → JCL Parser → IR → Contract Extractor → BCG → BCGDiff → Risk Detector`.
> COBOL and copybook parsers exist in the codebase but are not part of the evaluated pipeline.
> The dynamic-evidence reconciliation component is also present but has not been validated
> with real execution evidence (see [limitations.md](limitations.md) §L11).
> The UI, Neo4j storage, and restoration components are exploratory scaffolding.

## RELIC — System Architecture

---

## SYSTEM OVERVIEW

RELIC is a research prototype that extracts behavioral contracts from JCL and detects
whether a changed job still satisfies them. The implemented and evaluated path is
static analysis only: JCL text in, a risk report out. The codebase also contains
COBOL parsing, dynamic evidence reconciliation, and a UI — these are not part of the
reported evaluation.

```
┌─────────────────────────────────────────────────────────────────────┐
│                             RELIC                                       │
│                                                                     │
│  ┌─────────────┐    ┌──────────────┐    ┌──────────────────────┐   │
│  │  INGESTION  │───▶│   PARSERS    │───▶│  IR (Intermediate    │   │
│  │             │    │  JCL / COBOL │    │     Representation)  │   │
│  └─────────────┘    │  / Copybook  │    └──────────┬───────────┘   │
│                     └──────────────┘               │               │
│                                                    ▼               │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │               BEHAVIORAL CONTRACT GRAPH (BCG)               │   │
│  │   V (entities)  E (relations)  C (contracts)  P (prov.)     │   │
│  │   D (dynamic observations)    Γ (validation)                │   │
│  └─────────────┬───────────────────────────┬───────────────────┘   │
│                │                           │                       │
│                ▼                           ▼                       │
│  ┌──────────────────┐         ┌───────────────────────┐           │
│  │  STATIC ANALYSIS │         │   DYNAMIC ANALYSIS    │           │
│  │  Contract extrac-│         │   Trace adapter       │           │
│  │  tion from IR    │         │   Event normalization  │           │
│  └────────┬─────────┘         └──────────┬────────────┘           │
│           │                              │                         │
│           └──────────────┬───────────────┘                         │
│                          ▼                                          │
│              ┌───────────────────────┐                             │
│              │   RECONCILIATION      │                             │
│              │   Static vs Dynamic   │                             │
│              │   Conflict detection  │                             │
│              └──────────┬────────────┘                             │
│                         │                                          │
│           ┌─────────────┼─────────────┐                           │
│           ▼             ▼             ▼                            │
│  ┌──────────────┐ ┌──────────┐ ┌──────────────┐                  │
│  │  MUTATIONS   │ │  RISK    │ │ RESTORATION  │                  │
│  │  Empirically │ │ DETECTION│ │ Counterfact. │                  │
│  │  grounded    │ │          │ │ analysis     │                  │
│  └──────────────┘ └──────────┘ └──────────────┘                  │
│                                                                     │
│  ┌─────────────────┐   ┌──────────────────┐                       │
│  │   EVALUATION    │   │       UI          │                       │
│  │   Benchmark     │   │  React + D3.js   │                       │
│  │   Baselines     │   │  BCG visualization│                       │
│  │   Experiments   │   │  Trace overlay   │                       │
│  └─────────────────┘   └──────────────────┘                       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## MODULE INTERFACES

### ingestion/
**Input:** File paths to legacy artifacts (JCL, COBOL, copybooks)  
**Output:** Normalized artifact records in ingestion queue  
**Key classes:** `ArtifactIngester`, `ArtifactRecord`

### parsers/
**Input:** Raw artifact content  
**Output:** Parser-specific ASTs/parse results  
**Key classes:** `JCLParser`, `COBOLParser`, `CopybookParser`  
**Design:** Each parser produces a normalized ParseResult; no parser-specific types leak into IR.

### ir/
**Input:** Parser results from all artifact types  
**Output:** Common IR nodes — programs, jobs, steps, files, fields, records  
**Key classes:** `IRBuilder`, `IREntity`, `IRRelation`, `IRGraph`  
**Note:** The IR is the structural representation. The BCG builds on top of the IR.

### static_analysis/
**Input:** IR graph  
**Output:** Static evidence records, candidate contracts (STATIC_CANDIDATE)  
**Key classes:** `TemporalContractExtractor`, `ResourceContractExtractor`, `ControlFlowContractExtractor`

### dynamic_analysis/
**Input:** Raw execution logs/traces  
**Output:** Normalized ExecutionEvent stream linked to IR entities  
**Key classes:** `DynamicEvidenceAdapter`, `GnuCOBOLTraceAdapter`, `JCLSimulatorAdapter`, `EventNormalizer`

### contracts/
**Input:** Static candidates + dynamic events  
**Output:** Contract objects with type, provenance, confidence  
**Key classes:** `Contract`, `ContractTaxonomy`, `ProvenanceRecord`, `ConfidenceVector`

### bcg/
**Input:** Contracts, IR, dynamic observations  
**Output:** Populated BCG (V, E, C, P, D, Γ)  
**Key classes:** `BCG`, `BCGBuilder`, `BCGQuery`, `BCGSerializer`  
**Storage:** SQLite (development) / Neo4j (production) via adapter

### reconciliation/
**Input:** BCG with STATIC_CANDIDATE contracts + D (dynamic observations)  
**Output:** Updated Γ (validation states, confidence updates)  
**Key classes:** `ReconciliationEngine`, `ConflictAnalyzer`, `ValidationState`

### mutations/
**Input:** BCG (original)  
**Output:** Mutated BCG + mutation record  
**Key classes:** `MutationEngine`, `MutationOperator`, `MutationRecord`

### risk/
**Input:** Original BCG + Mutated BCG  
**Output:** Risk report with contract violations, evidence chains, confidence  
**Key classes:** `RiskDetector`, `RiskReport`, `RiskExplanation`

### evidence/
**Input:** Contracts, artifacts, execution events  
**Output:** Evidence strength assessment per contract  
**Key classes:** `EvidenceSufficiencyAnalyzer`, `EvidenceRecord`

### restoration/
**Input:** Original BCG + mutation + violated contracts  
**Output:** Candidate structural restorations  
**Key classes:** `RestorationEngine`, `RestorationCandidate`

### evaluation/
**Input:** System output, ground truth benchmark  
**Output:** Precision, recall, F1, calibration, error analysis  
**Key classes:** `BenchmarkEvaluator`, `BaselineRunner`, `ExperimentRunner`

---

## DATA FLOW

```
Artifacts
   │
   ▼ [ingestion]
ArtifactRecord
   │
   ▼ [parsers]
ParseResult (JCL-AST | COBOL-AST | Copybook-AST)
   │
   ▼ [ir/IRBuilder]
IRGraph (entities + structural relations)
   │
   ├──▶ [static_analysis] ──▶ StaticCandidateContracts
   │
   ├──▶ [dynamic_analysis] ──▶ ExecutionEvents (from traces)
   │
   ▼ [contracts]
ContractSet (with provenance P)
   │
   ▼ [bcg/BCGBuilder]
BCG = (V, E, C, P, D, Γ)  [D empty until reconciliation]
   │
   ▼ [reconciliation]
BCG with Γ updated (ValidationState per contract)
   │
   ├──▶ [mutations] ──▶ MutatedBCG
   │       │
   │       ▼ [risk]
   │   RiskReport (violations + evidence chains)
   │
   ├──▶ [restoration] ──▶ RestorationCandidates
   │
   └──▶ [evaluation] ──▶ Precision/Recall/F1 + Ablations
```

---

## STORAGE ARCHITECTURE

> **Caveat.** The storage layer is exploratory scaffolding and is not exercised by the
> evaluation pipeline or tests. The evaluation stores results as JSONL/JSON flat files
> in `results/final/raw/`.

Development: SQLite database `bcg_store.db`
Production-scale: Neo4j graph database
Adapter pattern: `BCGStorage` abstract class with `SQLiteBCGStorage` and `Neo4jBCGStorage`

Schema defined in `src/bcg/schema.sql` and `src/bcg/schema_neo4j.cypher`

---

## UI (EXPLORATORY)

> **Caveat.** The UI is exploratory scaffolding. It is not part of the evaluated system
> and has not been described in the reported results.

**Stack:** React + TypeScript + D3.js (graph) + Vite (build)

**Views:**
1. **System View** — high-level artifact graph
2. **Contract View** — behavioral relationships with evidence panel
3. **Execution Overlay View** — dynamic trace overlaid on BCG
4. **Modernization Diff View** — original vs. modernized with affected contracts
5. **Risk Explanation View** — full evidence chain for a risk item
6. **Timeline View** — execution event timeline with BCG linkage

**API:** FastAPI backend serving BCG data to React frontend via REST endpoints
