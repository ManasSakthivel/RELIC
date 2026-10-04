Population: all subjects, EVALUABLE mutants (n = 566: 460 behaviour-changing, 106 behaviour-preserving; 66 files)

| Detector | TP | FP | FN | TN | Precision | Recall | F1 | F1 95% CI (file bootstrap) | Specificity |
|---|---:|---:|---:|---:|---:|---:|---:|---|---:|
| **RELIC v1.0.0 (as released; primary)** | 380 | 0 | 80 | 106 | 1.000 | 0.826 | 0.905 | [0.84, 0.95] | 1.000 |
| RELIC v1.1 (post-hoc spec fixes) | 417 | 0 | 43 | 106 | 1.000 | 0.906 | 0.951 | [0.89, 0.99] | 1.000 |
| Baseline E: static BCG, broken-only | 380 | 0 | 80 | 106 | 1.000 | 0.826 | 0.905 | [0.84, 0.95] | 1.000 |
| Baseline A: structural edge diff | 368 | 0 | 92 | 106 | 1.000 | 0.800 | 0.889 | [0.81, 0.95] | 1.000 |
| Baseline B: complexity score | 162 | 33 | 298 | 73 | 0.831 | 0.352 | 0.495 | [0.21, 0.69] | 0.689 |
| Reference: any non-comment text change | 460 | 41 | 0 | 65 | 0.918 | 1.000 | 0.957 | [0.94, 0.97] | 0.613 |
