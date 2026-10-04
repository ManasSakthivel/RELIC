| Quantity | Legacy harness (WITHDRAWN: BCG-level, circular) | Source-level benchmark (this version) |
|---|---|---|
| Mutants scored | 104 of 440 attempts | 315 of 356 candidates (CardDemo) |
| Ground truth | 'mutation was applied' (always positive) | independent JCL semantics oracle |
| Negatives | 144 BCG edits that touch no contract | oracle-equivalent mutants (incl. fault operators) |
| RELIC F1 | 1.000 | 0.919 (v1.0.0) / 0.982 (v1.1) |
| Baseline E F1 | 0.960 | 0.919 |
| Baseline A F1 | 0.899 | 0.896 |
| Baseline B F1 | 0.000 | 0.522 |
| Baseline C: LLM-only | F1 0.0377, but 245/248 calls failed (HTTP 429) and were scored as 'no regression'; 3/3 successful calls were correct | F1 0.898 on the 39 mutants (all subjects) both LLM baselines answered (of 566 evaluable; see LLM table) |
| Baseline D: dependency + LLM | F1 0.1091, but 241/248 calls failed (HTTP 429) and were scored as 'no regression'; 7/7 successful calls were correct | F1 0.980 on the 39 mutants (all subjects) both LLM baselines answered (of 566 evaluable; see LLM table) |
