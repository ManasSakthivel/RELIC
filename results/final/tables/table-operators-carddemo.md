| Operator | Contract type | n | violating | RELIC v1.0.0 TP/FN/FP/TN | RELIC v1.1 TP/FN/FP/TN | Baseline A TP/FN/FP/TN | Reference TP/FN/FP/TN |
|---|---|---:|---:|---|---|---|---|
| SWAP_ADJACENT_STEPS | TEMPORAL | 81 | 81 | 78/3/0/0 | 78/3/0/0 | 79/2/0/0 | 81/0/0/0 |
| SPLIT_JOB | TEMPORAL | 81 | 81 | 79/2/0/0 | 79/2/0/0 | 81/0/0/0 | 81/0/0/0 |
| DELETE_PRODUCER_STEP | RESOURCE | 28 | 28 | 26/2/0/0 | 27/1/0/0 | 28/0/0/0 | 28/0/0/0 |
| RENAME_OUTPUT_DATASET | RESOURCE | 11 | 11 | 1/10/0/0 | 8/3/0/0 | 7/4/0/0 | 11/0/0/0 |
| MOVE_CONSUMER_BEFORE_PRODUCER | RESOURCE | 11 | 11 | 11/0/0/0 | 11/0/0/0 | 11/0/0/0 | 11/0/0/0 |
| REMOVE_COND | CONTROL_FLOW | 22 | 21 | 21/0/0/1 | 21/0/0/1 | 0/21/0/1 | 21/0/1/0 |
| ALTER_COND_THRESHOLD | CONTROL_FLOW | 22 | 21 | 0/21/0/1 | 21/0/0/1 | 0/21/0/1 | 21/0/1/0 |
| INSERT_COMMENT | NONE | 30 | 0 | 0/0/0/30 | 0/0/0/30 | 0/0/0/30 | 0/0/0/30 |
| CHANGE_MSGCLASS | NONE | 29 | 0 | 0/0/0/29 | 0/0/0/29 | 0/0/0/29 | 0/0/29/0 |
