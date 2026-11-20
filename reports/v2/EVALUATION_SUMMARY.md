# RELIC V2 — Evaluation summary

Machine-readable: `results/v2/v2_metrics.json`, `results/v2/v2_predictions.jsonl`
(deterministic; `v2_run_info.json` holds a timestamp). Produced by
`python -m relic_eval.v2_eval` (`make v2-eval`).

> **Validation status: DEVELOPMENT ONLY.** CardDemo, the OMP COBOL course and
> GenApp were all inspected while diagnosing defects and choosing fixes. There is
> no genuinely held-out dataset and no independent reviewer. **External
> validation remains pending.** Nothing below supports a claim of independent
> validation or of production JCL compatibility.

## 1. Method

Replay of the committed benchmark (`results/final/raw/evaluation_records.jsonl`)
without altering it:

1. regenerate every mutant with `relic_eval.mutate.generate`; abort unless its
   SHA-256 equals the committed `mutant_sha256` (0 mismatches);
2. keep the committed oracle labels and statuses untouched (oracle not re-run,
   never sees detector output);
3. recompute RELIC v1.1 and abort unless it equals the committed predictions
   (it does for all 566);
4. add `relic_v2` and one-fix-off ablations; reuse committed predictions for
   v1.0.0, structural A/E, complexity B and the text-change reference.

No labels, ground truth or mutants were changed.

## 2. Detection results (pooled evaluable n = 566; 460 positive, 106 negative)

| Detector | TP | FP | FN | TN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| RELIC v1.0.0 (legacy mode) | 380 | 0 | 80 | 106 | 1.000 | 0.826 | 0.9048 |
| RELIC v1.1 | 417 | 0 | 43 | 106 | 1.000 | 0.907 | 0.9510 |
| **RELIC V2** (D-001…D-004) | **442** | **0** | **18** | 106 | 1.000 | 0.961 | **0.9800** |
| V2 without D-001 | 419 | 0 | 41 | 106 | 1.000 | 0.911 | 0.9534 |
| V2 without D-002 | 441 | 0 | 19 | 106 | 1.000 | 0.959 | 0.9789 |
| V2 without D-003 | 442 | 0 | 18 | 106 | 1.000 | 0.961 | 0.9800 |
| V2 without D-004 | 444 | 0 | 16 | 106 | 1.000 | 0.965 | 0.9823 |
| Structural baseline A | 368 | 0 | 92 | 106 | 1.000 | 0.800 | 0.8889 |
| Text-change reference (any non-comment change) | 460 | 41 | 0 | 65 | 0.918 | 1.000 | 0.9573 |
| *Diagnostic:* text diff ignoring JOB-card parameters | 460 | 2 | 0 | 104 | 0.996 | 1.000 | 0.9978 |

Per subject F1 (v1.0 / v1.1 / V2): CardDemo 0.919 / 0.982 / 0.990;
GenApp 0.883 / 0.905 / 0.966; OMP 0.947 / 1.000 / 1.000. (GenApp text-change
reference: 0.975 — higher than V2.)

Cluster bootstrap over files (66 clusters, 10 000 reps, seed 20261004), paired
F1 difference, 95 % CI: V2 − v1.1 **[0.0034, 0.0688]**; V2 − v1.0
[0.0379, 0.1273]; V2 − text-change [0.0039, 0.0432]; V2 − V2 w/o D-004
[−0.0060, 0.0]. These intervals describe sampling variation across *these* files
only; they do not address selection of fixes on the same files.

**Flips v2 vs v1.1:** 27 gained flags (all true positives, **0 gained false
positives**), 2 lost flags (both true positives; the D-004 trade-off, see
`DEFECT_REGISTER.md`). Recall on files with repeated step names: 0.391 → 0.766;
on files without: 0.990 → 0.992.

**The trivial-rule caveat.** The post-hoc diagnostic (which was constructed after
inspecting the benchmark and is not a competing detector) exceeds RELIC on this
benchmark. The benchmark does not establish a RELIC advantage over a normalised
text rule; see D-014.

## 3. Contract recovery against oracle facts

Per-family P/R for v1.1 vs V2 is in `results/v2/v2_metrics.json → contract_recovery`.

| Family | Subject | v1.1 | V2 |
|---|---|---|---|
| TEMPORAL | CardDemo | P 1.0 / R 1.0 (79) | unchanged |
| CONTROL_FLOW | CardDemo | P 1.0 / R 1.0 (55) | unchanged |
| RESOURCE | CardDemo | 9 TP / 9 FP / 13 FN (P 0.50, R 0.41) | 11 TP / 0 FP / 11 FN (P 1.00, R 0.50) |
| RESOURCE | GenApp | 0 / 2 / 4 | 2 / 3 / 2 |
| RESOURCE | OMP course | 0 / 0 / 23 | 0 / 0 / 23 |

RESOURCE ablation on CardDemo (FP): V2 0; without D-002 4; without D-003 3;
without D-004 3; without D-003 and D-004 8. The remaining RESOURCE misses are
mostly program/utility I/O invisible to JCL parsing (D-007); GenApp gains one
additional RESOURCE false positive relative to v1.1 (3 vs 2): `asmmap` now yields
`COPY → ASMDSECT` while the oracle attributes that dataset flow to `ASMMAP → ASMDSECT`
(producer attribution differs; the oracle pair was not recovered). Not analysed further.

## 4. LLM comparison — NOT a fair comparison; not re-run

No credentials were used and no model was queried. Only committed records were
analysed (`llm_selection_analysis` in `v2_metrics.json`):

* 183 of 566 mutants are unscored for at least one baseline because the model
  returned no parseable JSON (not a quota-limited random subsample); they are
  89.6 % positive vs 77.3 % for the scored 383.
* On the selection-biased 383-mutant common subset: llm_C F1 0.985,
  llm_D 0.967, v1.0 0.908, v1.1 0.958, V2 0.979, text-change 0.944.
* Bounds on all 566 (invalid output = not flagged / flagged): llm_C 0.808 / 0.972;
  llm_D 0.847 / 0.954.
* Conclusion: the committed records neither show RELIC beating nor losing to the
  LLM baselines. A fair comparison needs a credentialed re-run with an
  invalid-output retry policy and a single documented model/provider (D-016, D-017).

## 5. Test and regression evidence (executed)

| Check | Result |
|---|---|
| Full suite after V2 | **439 passed** (391 original + 48 V2) |
| `tests/v2` | 48 passed (regression for D-001…D-004, documented limitations, results integrity: committed `results/v2` equals a fresh deterministic run; v1.1 recomputation equals committed predictions) |
| `relic_eval.check_consistency` | passed |
| `results/` tracked files vs baseline hashes | 1277 / 1277 identical |
| Full `make reproduce` on the V2 commit `d79d449` (scratch export, 349 s) | pipeline exit 0; consistency check passed; 1276 / 1277 tracked `results/` files byte-identical to the committed ones (only `results/final/run_info.json` differs: timestamp, commit) |

## 6. Post-change reproduction of the historical pipeline

Executed on a `git archive` export of commit `d79d449` (parser/extractor changes included):
`relic_eval.pipeline` → `llm_baselines --offline-if-no-key` → `pipeline --skip-benchmark` →
`check_consistency`: all exit 0, 349 s. Headline unchanged (CardDemo v1.0.0 F1 0.919,
v1.1 0.982, text-change 0.943; 656 candidates / 566 evaluable). Every tracked file under
`results/` except `run_info.json` is byte-identical to the committed version, i.e. the opt-in
refactor did not change v1.0.0/v1.1 behaviour.

## 7. Ablation and what was not done

* Ablations: done for each fix (table above).
* Not done: fair LLM re-run (credentials), held-out evaluation (no dataset),
  step-content fingerprint (D-005; cost unmeasurable), PROC/INCLUDE/IF support
  (D-006), new contract families.
