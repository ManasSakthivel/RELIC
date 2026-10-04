# Archive — superseded documents (do not cite)

Everything under `docs/archive/` predates the October 2026 research remediation
and is kept **only for provenance**. These documents report results from the
legacy BCG-level mutation harness, which was circular (mutations edited RELIC's
own contract graph and RELIC's diff then detected the edit), and LLM-baseline
numbers that were artifacts of rate-limited API calls scored as negatives.

**None of the numbers in this directory are valid results.** In particular,
"F1 = 1.000", "104/104", "FPR = 0 on 144 negatives", "LLM F1 = 0.0377 / 0.1091",
"91.8% dynamic validation" and the static-BCG/structural F1 values of 0.960 / 0.900
are withdrawn. Why: `docs/remediation/PRE_REMEDIATION_AUDIT.md`.
Current results: `docs/evaluation/RESULTS.md` and `results/final/metrics.json`.

- `2026-08_pre_remediation/docs/` — sprint status reports, audits, hostile reviews,
  protocols and specifications from August 2026.
- `2026-08_pre_remediation/reports/` — analysis reports for the legacy RQ1–RQ3.
- `2026-08_pre_remediation/bob_artifacts/` — HTML sprint reports.
- the remaining files at this level were already marked superseded before August 2026.
