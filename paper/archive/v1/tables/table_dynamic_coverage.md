# Table: Dynamic Coverage Experiment (RQ3)

| Trace Coverage | Traces Used | SUPPORTED | CONFLICT | NOT\_OBSERVED | Validation Rate |
|---:|---:|---:|---:|---:|---:|
| 10% | 4 | 1 | 0 | 60 | 1.6% |
| 25% | 10 | 15 | 0 | 46 | 24.6% |
| 50% | 20 | 26 | 0 | 35 | 42.6% |
| 75% | 30 | 39 | 0 | 22 | 63.9% |
| 100% | 40 | 56 | 1 | 4 | 91.8% |

**Source:** `results/rq3/coverage_experiment.json`  
**Seed:** 42 (random trace selection)  
**Finding:** Validation rate increases monotonically from 1.6% (10% coverage) to 91.8% (100%).  
NOT\_OBSERVED contracts do not become CONTRADICTED as traces are added (monotonicity confirmed).
