# Table 1: Prior-Art Comparison

Capability matrix across the 8 most closely related prior systems.
Each cell: ✓ (fully addressed), ~ (partially addressed), ✗ (not addressed).

This table justifies the claimed research contribution by identifying
dimensions not addressed by any single prior work.

| Capability Dimension | Daikon [W4] | Klaedtke [W1] | Flanagan [W5] | Naik [W10] | Sneed [W11] | Pessoa [W28] | Meyer DbC [W19] | **This Work** |
|---------------------|:-----------:|:-------------:|:-------------:|:-----------:|:-----------:|:------------:|:---------------:|:-------------:|
| Behavioral contracts (not just invariants) | ~ | ✓ | ~ | ✗ | ✗ | ~ | ✓ | **✓** |
| Temporal ordering contracts (A ≺ B) | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | **✓** |
| Resource dependency contracts | ✗ | ✗ | ✗ | ✗ | ~ | ✗ | ✗ | **✓** |
| Control-flow obligation contracts | ✗ | ~ | ✓ | ✗ | ✗ | ~ | ✓ | **✓** |
| Cross-artifact (multi-language) | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | **✓** |
| JCL artifact support | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | **✓** |
| COBOL artifact support | ✗ | ✗ | ✗ | ✗ | ✓ | ✓ | ✗ | **✓** |
| Copybook / record structure support | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | **✓** |
| Formal intermediate representation (IR) | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | **✓** |
| Static evidence extraction | ~ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | **✓** |
| Dynamic evidence extraction | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ | **✓** |
| Static/dynamic reconciliation | ~ | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ | **✓** |
| Explicit S/D conflict detection | ✗ | ✗ | ✗ | ~ | ✗ | ✗ | ✗ | **✓** |
| Contract provenance tracking | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | **✓** |
| Contract confidence model | ~ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | **✓** |
| Contract validation states | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | **✓** |
| Modernization-risk use case | ✗ | ✗ | ✗ | ✗ | ~ | ✓ | ✗ | **✓** |
| Fault-grounded mutation engine | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | **✓** |
| Counterfactual contract preservation | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | **✓** |
| Evidence sufficiency analysis | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | **✓** |
| Execution oracle for ground truth | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | **✓** |
| NOT_OBSERVED ≠ CONTRADICTED distinction | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | **✓** |

## Key Distinctions

**vs. Daikon [W4]:** Daikon infers data-value invariants from OO program execution.
This work targets temporal/resource/control-flow obligations across batch artifacts.
Neither the artifact types (JCL/COBOL), the contract forms (ordering/resource),
nor the modernization use case are addressed by Daikon.

**vs. Klaedtke et al. [W1]:** Pure-dynamic trace mining via automata learning.
No static analysis, no JCL, no cross-artifact representation, no provenance,
no modernization context.

**vs. Pessoa et al. [W28]:** COBOL semantic differencing without formal contract
representation, without dynamic evidence, and without JCL.

**vs. Naik et al. [W10]:** Static/dynamic hybrid for Java race detection.
The reconciliation principle is analogous; the artifact domain, contract types,
and evaluation context are entirely different.

## Claims Summary

**Established (do not claim as novel):**
- Behavioral contract concept (Meyer 1992)
- Dynamic invariant inference (Daikon)
- Temporal specification formalism (LTL)
- Static dependency analysis
- Static/dynamic hybrid principle

**Incrementally novel:**
- Cross-artifact (JCL+COBOL) static analysis
- JCL behavioral contract extraction
- Normalized execution event schema for legacy batch

**Potentially novel (central contribution):**
- Provenance-aware BCG as behavioral obligation IR for JCL+COBOL
- Static/dynamic reconciliation with explicit conflict taxonomy for batch
- Fault-grounded mutation framework from real modernization failures
- NOT_OBSERVED ≠ CONTRADICTED as a first-class validation principle
- Counterfactual contract preservation framing of modernization verification
