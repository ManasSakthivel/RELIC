# Table 7 — Fault-Grounded Mutation Taxonomy

| Category | Operator | Empirical Failure Source | N Evaluated | N Not Applicable |
|---|---|---|---|---|
| F1 — Job ordering | REORDER\_JOBS | Batch scheduler misconfiguration in mainframe-to-cloud lift (CardDemo ordering regressions) | 29 | 26 |
| F1 — Job ordering | REMOVE\_JOB\_DEPENDENCY | DAG dependency declaration dropped in cloud orchestration translation | 28 | 27 |
| F1 — Job ordering | ALTER\_STEP\_SEQUENCE | Step reorder when JCL steps translated to independent microservice calls | 28 | 27 |
| F2 — Resource | REMOVE\_DATASET\_INIT | Initialization step omitted when monolithic batch split into independently deployed microservices | 1 | 54 |
| F2 — Resource | CHANGE\_DATASET\_NAME | DD name / S3 path renamed only on producer side during migration | 1 | 54 |
| F2 — Resource | ALTER\_FILE\_DEPENDENCY\_ORDER | Consumer service deployed before producer in cloud-native DAG | 1 | 54 |
| F3 — RC propagation | SUPPRESS\_RETURN\_CODE\_CHECK | COND parameter dropped when JCL translated to CI/CD pipeline | 8 | 47 |
| F3 — RC propagation | ALTER\_ERROR\_BRANCH | RC threshold changed (usually raised) in COBOL-to-Java rewrite | 8 | 47 |
| **Total** | | | **104** | **336** |

All mutation categories are grounded in publicly documented modernization failures. See `docs/failure_taxonomy.md` for full citation trail. N Not Applicable = the BCG did not contain the structural prerequisite for that operator (e.g., REMOVE\_DATASET\_INIT requires a PRODUCES relation). N/A count increased from 331 to 336 after reflexive-pair guard fix removed 5 mutation sites with duplicate step names creating self-referential contracts.

**F2 representativeness note:** Only 3 of 104 evaluated mutations are F2 operators (each type with n=1), because CardDemo is a demonstration system with limited file producer/consumer structure. F2 results should be treated as preliminary. An enterprise JCL corpus with richer file dependency structure would be required for statistically robust F2 evaluation.
