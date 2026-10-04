# Results

**Authoritative results live in `results/final/`** and are produced by
`make reproduce` (`relic_eval/pipeline.py`). Everything else in this directory is
pre-remediation output kept for provenance only; its headline numbers are
withdrawn (see [docs/remediation/PRE_REMEDIATION_AUDIT.md](../docs/remediation/PRE_REMEDIATION_AUDIT.md)).

## Current results (generated)

<!-- BEGIN GENERATED:results-summary -->
- **Benchmark:** 656 candidate source-level mutants over 3 subject systems (566 evaluable, 86.3%); ground truth from an independent JCL execution-semantics oracle.
- **Primary result (CardDemo, RELIC v1.0.0 as released):** precision 1.000, recall 0.850, F1 0.919 (95% CI [0.88, 0.95]; TP 216, FP 0, FN 38, TN 61; n = 315).
- **RELIC v1.1** (spec-conformance fixes made *after* seeing these results): F1 0.982 on CardDemo.
- **Reference detector** that flags any non-comment text change: F1 0.943 (specificity 0.492); RELIC v1.0.0 − reference F1 difference 95% CI [-0.07, 0.02].
- **Structural baseline A:** F1 0.896.
- **All three subjects pooled:** RELIC v1.0.0 F1 0.905 (n = 566).
- **LLM baselines** (`openai/gpt-oss-120b`; scored only where both LLM baselines answered — 39 of 566 evaluable mutants (6.9%), all subjects): LLM-only F1 0.898 (P 0.957, R 0.846, specificity 0.923); dependency + LLM F1 0.980 (P 1.000, R 0.962, specificity 1.000); RELIC v1.0.0 on the same mutants F1 0.894 (RELIC v1.0.0 − LLM-only F1 difference 95% CI [-0.30, 0.15]; − dependency + LLM [-0.30, 0.00]). Coverage is limited by the provider quota of the API key used; the answered mutants are the first ones of a seeded random order, i.e. a random subsample. The earlier F1 0.0377 / 0.1091 figures were artifacts of rate-limited calls scored as negatives and are withdrawn.
<!-- END GENERATED:results-summary -->

Full tables: [docs/evaluation/RESULTS.md](../docs/evaluation/RESULTS.md).

## `results/final/` — authoritative

```
results/final/
├── raw/evaluation_records.jsonl   one record per candidate mutant: diff, status + reason,
│                                  oracle label and evidence, every detector's decision
├── raw/llm_records.jsonl          one record per (mutant, LLM baseline): status, answer
├── raw/llm_status.json            LLM run configuration, coverage and status counts
├── raw/llm_cache/                 every LLM request/response (offline re-scoring, audit)
├── evaluation_manifest.csv        flat view of evaluation_records.jsonl
├── contract_recovery.json         RQ1: contract recovery against oracle-derived facts
├── metrics.json                   every reported number (computed from raw records only)
├── run_info.json                  commit, platform, Python version of the benchmark run
└── tables/*.md                    Markdown tables rendered from metrics.json
```

`make check` recomputes `metrics.json` from the raw records and verifies every
table, LaTeX file, figure and generated documentation block against it.

## Legacy directories — withdrawn, kept for provenance

| Path | What it is | Status |
|---|---|---|
| `rq2/` | BCG-level mutation benchmark (legacy F1 = 1.000 on 104 of 440 attempts), negative benchmark, legacy LLM baselines | **Withdrawn.** Circular: the harness edited RELIC's own contract graph; the LLM numbers counted rate-limited calls as answers. |
| `rq1/` | RQ1 against a regex re-implementation of the extractor's own rule | Superseded by `final/contract_recovery.json`. The macro-F1 bug (0/0 files scored as F1 = 0) was fixed in the legacy script. |
| `rq3/` | "Dynamic validation" with 38 of 40 traces simulated from RELIC's own parser output (legacy rate reported: 91.8%) | **Withdrawn.** Self-confirming; not evidence. |
| `ablation/`, `generalization/` | Legacy ablation and generalization runs on the circular harness | Withdrawn. |
| `legacy/` | Machine-readable accounting of every legacy mutation attempt and why it is not valid evidence | Current (describes the legacy results). |
| `dataset_manifest.json`, `execution_manifest.json`, `parser_coverage.json` | Legacy inventories | Provenance only. |

`make reproduce-legacy` re-runs the legacy scripts (RELIC in v1.0.0 mode).
