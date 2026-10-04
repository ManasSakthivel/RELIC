# Table 8 — Ablation Study Results

Evidence conditions E0–E7 on contract recovery and mutation detection.

| Condition | Evidence Components | F1 (RQ1 Recovery) | F1 (RQ2 Detection) | Status |
|---|---|---|---|---|
| E0 — source only | Source text | [RESULT\_PENDING] | [RESULT\_PENDING] | Blocked |
| E1 — structural | Source + structural deps | [RESULT\_PENDING] | 0.8995 (Baseline A) | Partial |
| E2 — static contracts | Source + static contracts | [RESULT\_PENDING] | [RESULT\_PENDING] | Blocked |
| E3 — static BCG | Full static BCG | 1.0000 (independent oracle†) | 1.0000 | ✓ Complete |
| E4 — BCG + provenance | Static BCG + provenance | [RESULT\_PENDING] | [RESULT\_PENDING] | Blocked |
| E5 — BCG + dynamic | Static + dynamic evidence | [RESULT\_PENDING] | [RESULT\_PENDING] | Blocked — CardDemo execution |
| E6 — BCG + prov + dyn | Static + provenance + dynamic | [RESULT\_PENDING] | [RESULT\_PENDING] | Blocked |
| E7 — full system | E6 + LLM enrichment | [RESULT\_PENDING] | [RESULT\_PENDING] | Blocked — LLM API key |

† E3 F1=1.0 on RQ1 is from the independent oracle evaluation (56 TP, 0 FP, 0 FN, 33 held-out JCL files, TEMPORAL scope only). This is NOT the deprecated self-consistency result. See Table 4 and `results/rq1/rq1_independent.json`. Dynamic conditions (E5–E7) require CardDemo execution environment with DB2/CICS stubs. LLM condition (E7) requires OpenAI API key. These remain as future work.
