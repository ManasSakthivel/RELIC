# Table: Static vs. Dynamic Analysis Results (RQ3)

| Validation State | Count | Rate |
|---|---:|---:|
| STATIC_DYNAMIC_SUPPORTED | 56 | 91.8% |
| STATIC_DYNAMIC_CONFLICT | 1 | 1.6% |
| NOT_OBSERVED | 4 | 6.6% |
| **Total contracts** | **61** | — |

**Source:** `results/rq3/rq3_dynamic_results.json`  
**Traces:** 40 total (2 real GnuCOBOL EXECUTION + 38 EXECUTION\_SIMULATED). NOT z/OS.  
**Key finding:** 56/61 contracts validated by available traces.  
**Note:** NOT\_OBSERVED ≠ CONTRADICTED (absence of evidence ≠ contradiction).
