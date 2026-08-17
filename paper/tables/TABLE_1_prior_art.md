# Table 1 — Prior Art Comparison Matrix

| System | Year | Behavioral Contracts | Cross-Artifact | Dynamic Evidence | Static+Dynamic Reconciliation | Provenance | Formal IR | Modernization Risk |
|---|---|---|---|---|---|---|---|---|
| Daikon [W4] | 2007 | ✓ (data-value invariants) | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ |
| GIST (Lorenzoli et al.) [W31] | 2008 | Partial (FSM models) | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ |
| Ammons et al. (API specs) [W30] | 2002 | ✓ (temporal safety) | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ |
| Lo et al. (SMArTIC) [W29] | 2006 | ✓ (control-flow patterns) | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ |
| SYMDIFF (Lahiri et al.) [W35] | 2012 | ✗ | ✗ | ✗ | ✗ | ✗ | Partial | ✓ |
| Pessoa et al. (COBOL semantic diff) [W28] | 2022 | ✗ (semantic diff, not contract) | Partial (COBOL only) | ✗ | ✗ | ✗ | ✗ | Partial |
| Hou et al. (LLM for SE survey) [W24] | 2024 | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| **LEGACY-CONTRACT (This Work)** | **2024** | **✓** | **✓** | **Partial†** | **✓** | **✓** | **✓** | **✓** |

† GnuCOBOL 3.2.0 available; CardDemo execution blocked by DB2/CICS dependencies. 13 traces generated (2 EXECUTION + 11 EXECUTION\_SIMULATED). Full dynamic validation is future work.

**Legend:** ✓ = fully supported, Partial = partially supported, ✗ = not supported.

**Note:** DySy (Fraser et al. 2009) and CodeBERT (Feng et al. 2020) were listed in previous
versions of this table as entries. They were removed because (a) DySy addresses test input
generation, not behavioral contract recovery, and its inclusion here would misrepresent its
scope; (b) CodeBERT is a pre-trained model for code understanding tasks and has no direct
relationship to contract recovery or modernization risk detection — listing it as a comparable
system would be misleading. The Allamanis reference was also removed for the same reason.
For LLM-based code analysis context, see Hou et al. [W24] above.
