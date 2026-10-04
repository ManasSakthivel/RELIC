# Legacy result artifacts (pre-remediation, kept for provenance)

| File | What it is | Valid? |
|---|---|---|
| `../rq2/*` | raw output of the legacy BCG-level mutation harness and legacy LLM runs | raw evidence preserved; metrics withdrawn (circular harness; failed LLM calls scored as negatives) |
| `../rq1/*` | legacy TEMPORAL-only contract recovery on 11 held-out files | numbers are correct after the macro-F1 fix, but the test only checks that consecutive EXEC statements are ordered |
| `../rq3/*`, `../ablation/*`, `../generalization/*` | legacy dynamic-reconciliation runs | self-consistency only: 38/40 traces were derived from RELIC's own parser |
| `FINAL_RESULTS*.{md,json}`, `experiment_lock.json`, `ground_truth_manifest.json`, `secondary_system_candidates.json` | legacy summaries | superseded; `secondary_system_candidates.json` contains factual errors (see audit P12) |
| `legacy_mutation_accounting.csv` | machine-readable classification of all 440 legacy mutation rows (generated) | valid accounting of the legacy run |
| `legacy_accounting_summary.json` | summary of the above (generated) | valid |

Authoritative results: `../final/`.
