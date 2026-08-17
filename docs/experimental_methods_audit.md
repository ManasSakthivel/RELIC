# Experimental Methods Audit
## LEGACY-CONTRACT — Pre-Execution Methodology Review

**Auditor:** Subagent E — Experimental Methods Auditor  
**Date:** 2025-07 (pre-execution)  
**Scope:** RQ1 / RQ2 / RQ3 experiment configs, runner.py, metrics.py, benchmark.py  
**Status:** BLOCKING issues found — do not run experiments until fixes in §7 are applied  

---

## Summary

Six files were read in full: `experiments/rq1/config.yaml`, `experiments/rq2/config.yaml`,
`experiments/rq3/config.yaml`, `experiments/ablation/config.yaml`,
`src/legacy_contract/evaluation/runner.py`, `src/legacy_contract/evaluation/metrics.py`,
`src/legacy_contract/evaluation/benchmark.py`, `docs/methodology.md`,
`docs/experimental_design_v2.md`, `docs/integrity_audit_v2.md`,
`config/confidence_weights.yaml`.

### Finding severity summary

| Severity | Count | Examples |
|----------|-------|---------|
| **CRITICAL** | 3 | FPR denominator is always 0, pairwise n_comparisons wrong, ground truth files absent |
| **MAJOR** | 6 | RQ3 uses wrong statistical test, Bonferroni n wrong in runner, hypothesis threshold mismatch (0.80 vs 0.70), no benchmark lock check, f1_scores key never populated, config_hash race condition |
| **MINOR** | 5 | Missing dataset_version/ground_truth_version fields, ablation conditions treated identically, 0% coverage not in coverage_levels list, effect_size_threshold not enforced, RQ3 multiple comparison correction absent |

---

## RQ1 Audit

### Metric alignment

**Status: Acceptable with one clarification needed.**

The config declares `precision`, `recall`, `f1`, `fpr`, and `fnr` as dependent variables.
This is appropriate for RQ1 (contract recovery). F1 as a single headline metric is
reasonable because the research question asks about "sufficient precision *and* recall", and
the hypothesis states both P ≥ 0.80 and R ≥ 0.80 individually — which means F1 ≥ 0.80
follows. Reporting macro-F1 and weighted-F1 separately (as the runner does in
`_result_to_dict`) is correct.

**Gap:** The config's `fail_threshold_f1: 0.80` (rq1/config.yaml line 60) is inconsistent
with both versions of the methodology:

- `docs/methodology.md` line 32: "F1 ≥ 0.70"
- `docs/experimental_design_v2.md` lines 32–43: "F1 ≥ 0.70, CI lower bound ≥ 0.60"
- `experiments/rq1/config.yaml` line 60: `fail_threshold_f1: 0.80`

The config is more stringent than the documented hypothesis. Before running, the team must
decide which threshold is canonical and update all three documents to agree.

### Ground truth dependency

**Status: CRITICAL — ground truth file does not exist.**

```
benchmark/ground_truth/level2_deterministic.json
```

`legacy-contract/benchmark/ground_truth/` is an **empty directory**. The runner correctly
checks for the file's existence (runner.py lines 330–335) and returns `[RESULT_PENDING]` if
missing. However, the experiment cannot produce any result until this file is constructed.
There is no fallback and no stub data. This is expected pre-execution, but is confirmed here
as a blocking prerequisite.

The runner does **not** check that the benchmark is locked before loading it. `Benchmark.load()`
accepts unlocked benchmarks silently (benchmark.py line 161:
`benchmark._locked = data.get("locked", False)`). There is no assertion in `_run_rq1` that
`benchmark.is_locked() == True` before using it for evaluation. This means experiments can
accidentally run against a benchmark that is still being modified.

**Fix required:** Add a lock check immediately after `Benchmark.load()` in all `_run_rq*`
methods. See §7.

### Statistical validity

**Status: Acceptable for bootstrap CI; minor concern on percentile indexing.**

Bootstrap n=10000 is standard and adequate (Efron & Tibshirani 1993; DiCiccio & Efron 1996).
The percentile bootstrap is appropriate for bounded metrics like F1.

The index computation in `bootstrap_ci` (metrics.py lines 305–308):

```python
lower_idx = int(math.floor((alpha / 2) * n))          # = floor(0.025 * 10000) = 250
upper_idx = int(math.ceil((1 - alpha / 2) * n)) - 1   # = ceil(0.975 * 10000) - 1 = 9749
```

This is correct: indices 250 and 9749 in a sorted 10000-element array give the 2.5th and
97.5th percentiles. The clipping guards on lines 307–308 are defensive and correct.

No issue here.

### Code correctness issues found

#### CRITICAL-1 — FPR denominator is always zero

**File:** `src/legacy_contract/evaluation/metrics.py`  
**Lines:** 187, 196

```python
# Current code
tn = 0  # open-set problem; TN meaningless without explicit negative universe
...
fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
```

**What is wrong:** `tn` is hard-coded to 0. Therefore `fp + tn == fp`. If any FPs exist,
the branch `(fp + tn) > 0` is true and `fpr = fp / fp = 1.0`, which is wrong. If no FPs
exist, the guard triggers and `fpr = 0.0`, which happens to be correct by coincidence.

The formula `FPR = FP / (FP + TN)` requires TN (true negatives = items correctly predicted
as non-contracts). In an open-set recovery problem TN is ill-defined, but the convention
for contract recovery is to treat the evaluation universe as all predicted + all ground-truth
items. In that universe `TN = |universe| - TP - FP - FN`.

However the current code does not implement this: it permanently sets `tn = 0` and then
attempts to compute FPR, producing 1.0 for any run with false positives.

The FPR metric is reported in all three RQ configs and is a primary dependent variable in
RQ3 (H3 tests FPR reduction). This bug would make H3 trivially false in many runs and make
the FPR comparison meaningless.

**Fix:**
```python
# Option A: use explicit negative universe from prediction ∪ ground_truth
all_items = pred_set | gt_set
tn = len(all_items) - tp - fp - fn
fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0

# Option B: report FPR as a precision complement (FP / (FP + TP)),
# which is (1 - precision), and relabel it in outputs.
# This is simpler for open-set but must be clearly documented.
```

Option A is recommended because it preserves consistency with the RQ3 description.
The same fix is needed in `_compute_per_type` (metrics.py line 530: `tn = 0`).

---

#### MAJOR-1 — `f1_scores` key is never populated in `_result_to_dict`

**File:** `src/legacy_contract/evaluation/runner.py`  
**Lines:** 428–431

```python
# Current code (runner.py lines 428-431)
f1_scores_bcg = condition_results.get("bcg_dynamic", {}).get("f1_scores", [])
for baseline in ["structural", "complexity", "llm_only", "dep_llm", "static_bcg"]:
    f1_scores_baseline = condition_results.get(baseline, {}).get("f1_scores", [])
    if f1_scores_bcg and f1_scores_baseline:
        test = self._calc.mann_whitney_u(...)
```

**What is wrong:** `_result_to_dict` (runner.py lines 1018–1053) never sets a `"f1_scores"`
key. It sets `"f1"` (a single float), but never a list of F1 scores. Therefore
`f1_scores_bcg` and `f1_scores_baseline` will always be empty lists `[]`, and the
`if f1_scores_bcg and f1_scores_baseline` guard will always be False. **The Mann-Whitney U
pairwise tests will silently never execute.** The `pairwise_tests` dict will be empty for
every run, and no statistical comparison between BCG+dynamic and any baseline will ever
happen. H2 can never be tested.

The design intent is to collect per-item or per-mutation F1 scores from each condition so
that a distribution-level comparison is possible. A single aggregate F1 per condition is
not sufficient for Mann-Whitney U.

**Fix:** The runner must collect a list of per-instance outcome scores (one per mutation in
RQ2, one per contract in other RQs) per condition. The `compute_with_ci` result should be
extended to return the bootstrap distribution or per-instance scores:

```python
# In _result_to_dict, add:
d["f1_scores"] = getattr(result, "f1_bootstrap_scores", [])
```

And `MetricsCalculator.compute_with_ci` must store the bootstrap distribution:

```python
# In compute_with_ci, after bootstrap:
result.f1_bootstrap_scores = bootstrap_scores  # store distribution
```

Alternatively, for RQ2, the "distribution" should be the per-mutation binary outcomes
(RISKY/NOT_RISKY detected correctly or not), not bootstrap resamples of a single aggregate
score. This is a design decision that must be resolved before running.

---

#### MAJOR-2 — Wrong Bonferroni n in `_run_rq2`

**File:** `src/legacy_contract/evaluation/runner.py`  
**Line:** 408

```python
# Current code
n_comparisons = len(conditions) * (len(conditions) - 1) // 2   # = 6*5/2 = 15
```

**What is wrong:** This computes all pairwise comparisons among 6 conditions (C(6,2) = 15).
But the experiment only performs 5 pairwise tests (BCG+dynamic vs each of 5 baselines), not
all 15 pairwise combinations. The Bonferroni correction should use n=5, not n=15.

Using n=15 inflates the Bonferroni correction (corrected α = 0.05/15 = 0.0033 instead of
0.05/5 = 0.01). This makes the test more conservative than declared in the config
(`bonferroni_alpha: 0.01`) and in the methodology (`experimental_design_v2.md`, Part 2).
A real effect that passes the n=5 threshold (p < 0.01) might be reported as non-significant
because the runner uses n=15. This is a false-negative risk for H2.

The `bonferroni_alpha` stored in `all_results` (line 450) is computed as `0.05 / 15 = 0.0033`
and would be misreported in the JSON output.

**Fix:**
```python
# Replace line 408:
n_comparisons = len(config.extra.get("n_pairwise_comparisons", 5))
# Or simply:
n_comparisons = 5  # BCG+dynamic vs each of 5 baselines
```

The `mann_whitney_u` call on line 432 passes `bonferroni_n=n_comparisons`, so fixing line
408 will cascade correctly to the significance decision.

---

#### MAJOR-3 — RQ3 uses Mann-Whitney U; should use paired Wilcoxon signed-rank

**File:** `src/legacy_contract/evaluation/runner.py` / `experiments/rq3/config.yaml`

**What is wrong:** `rq3/config.yaml` line 47 specifies `statistical_method: bootstrap_ci`
with no pairwise test configured. The runner (`_run_rq3`) computes independent bootstrap CIs
at each coverage level but performs no statistical test comparing coverage levels. More
importantly, `docs/experimental_design_v2.md` Part 2 (H3a, lines 119–144) explicitly states:

> "Tested with: PAIRED Wilcoxon signed-rank test (NOT Mann-Whitney U)"  
> "Why paired test (NOT Mann-Whitney U): The same contracts are evaluated at each coverage
> level. This is a repeated-measures design."

The rq3/config.yaml does not specify paired Wilcoxon and the runner never calls it. If a
researcher were to use `mann_whitney_u` from `MetricsCalculator` for RQ3 comparisons (as is
natural from the available API), this would be wrong: Mann-Whitney U assumes independent
groups, but the same contracts appear at every coverage level — this is a repeated-measures
(paired) design.

Additionally, `experimental_design_v2.md` line 287 specifies Bonferroni n=15 for RQ3
(5 coverage comparisons × 3 contract types). Neither the config nor the runner implements this.

**Fix:**
1. Add `statistical_method: paired_wilcoxon` to `rq3/config.yaml`.
2. Add `bonferroni_n: 15` to `rq3/config.yaml`.
3. Implement `paired_wilcoxon` in `MetricsCalculator` (can use `scipy.stats.wilcoxon`).
4. Call it in `_run_rq3` on paired (contract × coverage_level) vectors.

---

#### MAJOR-4 — `config_hash` computed after experiment runs (race condition)

**File:** `src/legacy_contract/evaluation/runner.py`  
**Lines:** 232, 283

```python
# Current code
config = ExperimentConfig.from_yaml(config_path)   # line 232
...
record = RunRecord(
    config_hash=config.config_hash(),               # line 283 — computed AFTER run
    ...
)
```

**What is wrong:** If the config YAML is modified during a long run (by another process, an
editor, or a CI script), the stored hash reflects the post-modification state, not the state
that was actually used. The config is loaded into memory on line 232 and not re-read, so the
`config_hash()` on line 283 hashes the in-memory dict — which is stable. However,
`config_hash()` re-serializes `asdict(self)` which could reflect in-place mutations of the
config object (e.g., the `bootstrap_n` override on line 237). This is low-severity in
isolation but is a documented reproducibility gap (integrity_audit_v2.md, Section E1).

**Fix:**
```python
config = ExperimentConfig.from_yaml(config_path)
initial_hash = config.config_hash()   # ← compute before any mutation
if self._bootstrap_n_override is not None:
    config.bootstrap_n = self._bootstrap_n_override
# ... run ...
assert config.config_hash() == initial_hash  # sanity check (bootstrap_n is excluded from hash intent)
record = RunRecord(config_hash=initial_hash, ...)
```

---

#### MINOR-1 — Hypothesis threshold mismatch between config and methodology

**File:** `experiments/rq1/config.yaml` line 60 vs `docs/methodology.md` line 32

- Config: `fail_threshold_f1: 0.80`
- methodology.md: "F1 ≥ 0.70"
- experimental_design_v2.md: "F1 ≥ 0.70, CI lower bound ≥ 0.60"

There is also a discrepancy in the config description itself (lines 8–9): "P ≥ 0.80, R ≥ 0.80,
F1 ≥ 0.80" versus the methodology's 0.70 threshold. This needs resolution before running.

---

#### MINOR-2 — RQ3 config missing 0.0 coverage level entry

**File:** `experiments/rq3/config.yaml` lines 31–37

The `coverage_levels` list contains `[0.10, 0.25, 0.50, 0.75, 1.00]`. The static-only
baseline (coverage = 0.0) is described as a baseline but is not in the list. The runner
handles this separately (lines 515–524) by calling `_run_at_coverage(0.0, config)` outside
the loop. This works correctly but means the static baseline bootstrap CI is computed
separately with a different code path. The paired comparison for H3a needs coverage=0.0
as an explicit element so it can be paired with coverage=1.0 per-contract. Consider adding
`0.0` to `coverage_levels` and removing the separate static_only computation.

---

## RQ2 Audit

### Baseline completeness

**Status: All 5 baselines specified. One implementation gap.**

`experiments/rq2/config.yaml` lines 25–31 correctly lists all five baselines:
- A: `structural`
- B: `complexity`
- C: `llm_only`
- D: `dep_llm`
- E: `static_bcg`

The proposed method (`bcg_dynamic`) is commented out in the config (line 33) but is
hard-coded into the runner (runner.py line 406). This is fine for execution but should be
uncommented for documentation clarity.

**Implementation gap:** In `_run_condition` (runner.py lines 748–767), only `structural`,
`static_bcg`, and `bcg_dynamic` have implementations. `complexity`, `llm_only`, and
`dep_llm` fall through to:

```python
logger.warning(f"Condition '{condition}' not yet implemented. Returning [RESULT_PENDING].")
return None
```

This means baselines B, C, D will produce `[RESULT_PENDING]` markers for every condition
result, and the pairwise tests against those conditions will silently not run (due to
MAJOR-1 above). The paper cannot claim H2b (BCG > Baseline D) if Baseline D is never
evaluated.

### Statistical validity

**Status: MAJOR issues (Bonferroni n wrong; f1_scores never populated).**

See CRITICAL-1, MAJOR-1, and MAJOR-2 above.

Additional concern: the Mann-Whitney U test is applied to **bootstrap distributions** of F1
(if f1_scores were correctly populated). However, bootstrap resamples of a point estimate
are not the same as independent per-item measurements. A bootstrap distribution of F1 is not
the right input to Mann-Whitney U; it would produce artificially narrow confidence and an
inflated sample size.

The correct input to Mann-Whitney U for RQ2 is **per-mutation binary outcomes** (did the
system correctly flag mutation i as risky?), one score per mutation per condition. This
gives a distribution of per-item scores that is appropriate for a non-parametric test. The
runner's current design collapses all mutations into a single aggregate F1, discarding the
per-item distribution entirely.

**Fix:** Compute per-mutation precision, recall, or binary hit/miss scores for each condition
and pass those lists to `mann_whitney_u`. This requires changes to `_run_condition` to return
per-mutation results, not just aggregate contract-level predictions.

### Unit of analysis

**Status: Correct in config; misaligned in runner implementation.**

`docs/experimental_design_v2.md` Part 2 correctly defines the unit of analysis as "a
mutation evaluation event" (each of 150 injected mutations). The rq2 config specifies
`n_mutations_per_category: 50` (line 53) for 150 total. This is the right unit.

However, the runner evaluates RQ2 by comparing predicted contract IDs against the
mutations ground-truth benchmark (runner.py lines 402–424). This conflates *contract-level
identification* with *mutation-level risk detection*. A mutation is flagged as RISKY if a
contract associated with it is predicted as positive. The runner does not implement this
indirection — it compares predicted IDs directly against the ground-truth IDs as if they
were the same namespace. If the mutation ground truth uses mutation IDs while the system
produces contract IDs, all comparisons will yield zero TP.

This is a design gap that must be resolved: either (a) the mutations ground truth must map
each mutation to the contract IDs it violates, or (b) the runner must implement a
mutation-to-contract lookup layer.

---

## RQ3 Audit

### Coverage operationalization

**Status: Acceptable but with one ambiguity requiring documentation.**

`experiments/rq3/config.yaml` extra section (lines 59–62) defines coverage as:

> "subsampling is done by randomly selecting (coverage_level × N_total_traces) traces."

The runner implements this in `_run_at_coverage` (lines 851–853):

```python
rng = _random.Random(config.random_seed)
n_keep = max(1, int(len(all_traces) * coverage_level))
sampled_traces = rng.sample(all_traces, min(n_keep, len(all_traces)))
```

This is reproducible (seeded RNG, same sample across runs). Coverage is defined as a
fraction of the total trace corpus — each trace is a program execution event, not a contract
or a program. This is reasonable.

**Ambiguity:** "10% coverage" means 10% of available traces, not 10% of unique contracts or
programs observed. If the trace corpus is biased (e.g., 90% of traces are for one program),
then "10% coverage" may provide 0% coverage for some programs. The scientific note in the
config (lines 69–72) correctly warns about the simulated-vs-production trace distinction,
but does not address sampling bias. This should be documented in the paper's threats
to validity.

**Monotonicity claim:** H3 claims "Precision and F1 increase monotonically." This is an
empirical assumption, not a logical guarantee. The runner sorts `coverage_levels` (line 494)
which ensures the results are reported in ascending order, but does not test or assert
monotonicity. The monotonicity check must be performed post-hoc in the analysis scripts.

### Diminishing-returns test

**Status: Not implemented in runner; needs post-hoc analysis script.**

The config notes (lines 65–66) ask: "at what coverage level do returns become diminishing?"
The runner does not compute a diminishing-returns metric. This is an analysis step beyond
the raw metrics collection, but there is no script or notebook that performs it. Before
submitting the paper, a trend analysis (e.g., marginal F1 gain per coverage increment) must
be implemented.

### Correctness

**Status: Functional with MAJOR-3 (wrong statistical test) as the primary concern.**

The trace subsampling in `_run_at_coverage` uses `max(1, int(...))` to guarantee at least
one trace is selected even at coverage=0.10 when the trace corpus is small. This could
produce misleadingly high metrics for small corpora: if there are only 2 traces and
10% coverage selects 1, the "10%" condition is actually 50% of available data. The
`n_not_observed` dependent variable (in RQ3 config line 26) is never computed by the runner
— it is listed in the config but absent from `_result_to_dict` and `EvaluationResult`.

---

## Cross-cutting Issues

### CCX-1 — Ground truth files do not exist

`benchmark/ground_truth/` is empty. Both `level2_deterministic.json` (used by RQ1, RQ3,
ablation) and `mutations_ground_truth.json` (used by RQ2) are absent. All experiments will
return `[RESULT_PENDING]` immediately. This is the primary blocker.

The runner's ground-truth existence check (lines 330–335, 394–398, 482–487) correctly handles
this case, but there is no pre-flight check that warns the user before starting a run. A
pre-flight validation step would improve usability.

### CCX-2 — Benchmark lock not checked before evaluation

**File:** `src/legacy_contract/evaluation/runner.py`  
**Lines:** 337, 402, 489, 572, 625

In all five `_run_*` methods, after `benchmark = Benchmark.load(...)` there is no assertion:

```python
if not benchmark.is_locked():
    raise RuntimeError("Benchmark must be locked before running experiments.")
```

`Benchmark.load()` silently loads an unlocked benchmark. If a researcher runs an experiment
while the benchmark is still being modified, results will be computed against a changing
ground truth, and the `RUN_LOG.jsonl` will record a hash of the config but not of the
benchmark state. This is a leakage risk.

### CCX-3 — Confidence weight lock not enforced in runner

**File:** `src/legacy_contract/evaluation/runner.py`  
**File:** `config/confidence_weights.yaml` line 47 (`locked: false`)

`config/confidence_weights.yaml` states:

> "The ExperimentRunner checks this flag and refuses to run if weights were modified
> after `locked_at`."

A search of `runner.py` finds **zero references** to `confidence_weights.yaml`, `locked`,
or `locked_at`. The guard described in the YAML comment does not exist in code. This is
confirmed by `docs/integrity_audit_v2.md` Section C. The weights are currently `locked: false`
and no experiment will refuse to run regardless of weight changes.

Additionally, the `ConfidenceVector._weights` defaults in `contracts/model.py` duplicate the
values from `confidence_weights.yaml` with no runtime connection. If the YAML is updated
without updating the code (or vice versa), the running system will silently use stale weights.

### CCX-4 — Ablation conditions E0–E5 all route to `_run_static_extractor`

**File:** `src/legacy_contract/evaluation/runner.py`  
**Lines:** 871–888

```python
static_conditions = {
    "E0_source_only",
    "E1_structural",
    "E2_static_contracts",
    "E3_static_bcg",
    "E4_bcg_provenance",
}
...
if condition in static_conditions:
    preds, _ = self._run_static_extractor(...)
```

All five static ablation conditions call the same `_run_static_extractor` and will produce
identical results. The ablation study claims to test the contribution of each evidence
component (provenance, cross-artifact, etc.) but the runner makes no distinction between
E0 (raw source) and E4 (BCG + provenance). This means the ablation table will show identical
metrics for all static conditions, which is scientifically meaningless. Each ablation
condition must invoke the pipeline with the specific evidence combination it is meant to test.

### CCX-5 — Traces directory is empty

`legacy-contract/traces/dev/` exists but contains no files. All dynamic coverage runs
(`_run_at_coverage` for level > 0.0) will silently use `all_traces = []` because
`traces_dir.exists()` is true but `adapter.load_directory(...)` will return an empty list.
The code path `if sampled_traces:` (line 858) will be False, so no reconciliation runs.
The system will return static-only predictions for all non-zero coverage levels, making
the RQ3 coverage curve trivially flat. This is a pre-execution data gap, not a code bug,
but it must be resolved before RQ3 has any scientific value.

### CCX-6 — `dataset_version` and `ground_truth_version` missing from all configs

`docs/experimental_design_v2.md` Part 8 requires:
```yaml
dataset_version: [git commit hash or checksum]
ground_truth_version: [git commit hash]
```

None of the four experiment configs include these fields. Without them, the `RunRecord`
cannot be traced back to the exact dataset state, and results are not fully reproducible
if the dataset is ever updated.

### CCX-7 — `effect_size_threshold` not in configs or enforced in runner

`docs/experimental_design_v2.md` Part 6 requires `effect_size_threshold: 0.3` and Part 2
states "Cohen's d ≥ 0.3 required for any positive claim." None of the experiment configs
declare this field, and `ExperimentRunner` never checks whether the effect size of a
significant test meets the threshold before reporting `is_significant: True`. A test could
pass p < 0.01 with Cohen's d = 0.05 and be incorrectly labeled as significant.

---

## Recommended Fixes (Before Running Experiments)

Listed in priority order. Items marked [BLOCKING] must be fixed before any experiment run.

### Fix 1 [BLOCKING] — Construct ground truth files

Create `benchmark/ground_truth/level2_deterministic.json` and
`benchmark/ground_truth/mutations_ground_truth.json` following the protocol in
`docs/experimental_design_v2.md` Part 3. Lock both benchmarks before running.

### Fix 2 [BLOCKING] — Repair FPR computation (CRITICAL-1)

**File:** `src/legacy_contract/evaluation/metrics.py` lines 187, 196, 530

Change:
```python
tn = 0
fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
```
To:
```python
# In compute(): all_items = pred_set | gt_set is already computed; pass it in
tn = len(all_items) - tp - fp - fn
fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
```
Apply the identical fix in `_compute_per_type` (line 530).

### Fix 3 [BLOCKING] — Populate `f1_scores` in results dict (MAJOR-1)

**File:** `src/legacy_contract/evaluation/metrics.py` and `runner.py`

In `MetricsCalculator.compute_with_ci`, store the bootstrap F1 distribution on the result:
```python
result.f1_bootstrap_scores = list(bootstrap_scores_f1)  # after sort
```

In `EvaluationResult` dataclass, add:
```python
f1_bootstrap_scores: list[float] = field(default_factory=list)
```

In `_result_to_dict` (runner.py), add:
```python
d["f1_scores"] = result.f1_bootstrap_scores
```

Note: also resolve the design question of whether bootstrap scores or per-mutation scores
are the right input to Mann-Whitney U (see §RQ2 statistical validity discussion).

### Fix 4 [BLOCKING] — Fix Bonferroni n in `_run_rq2` (MAJOR-2)

**File:** `src/legacy_contract/evaluation/runner.py` line 408

Change:
```python
n_comparisons = len(conditions) * (len(conditions) - 1) // 2
```
To:
```python
n_comparisons = int(config.extra.get("n_pairwise_comparisons", 5))
```

### Fix 5 [BLOCKING] — Add benchmark lock enforcement in all `_run_*` methods

**File:** `src/legacy_contract/evaluation/runner.py`

After every `benchmark = Benchmark.load(str(gt_path))` call (lines 337, 402, 489, 572, 625),
add:
```python
if not benchmark.is_locked():
    raise RuntimeError(
        f"Benchmark at {gt_path} is not locked. "
        "Lock the benchmark (benchmark.lock(); benchmark.save(...)) "
        "before running experiments to prevent ground truth leakage."
    )
```

### Fix 6 [BLOCKING] — Implement paired Wilcoxon for RQ3

**File:** `src/legacy_contract/evaluation/metrics.py` and `rq3/config.yaml`

Add to `MetricsCalculator`:
```python
def paired_wilcoxon(
    self,
    group_a: Sequence[float],
    group_b: Sequence[float],
    bonferroni_n: int = 1,
) -> StatisticalTest:
    """Paired Wilcoxon signed-rank test for repeated-measures RQ3 design."""
    if _HAS_SCIPY:
        stat, p_val = _scipy_stats.wilcoxon(list(group_a), list(group_b))
    else:
        raise NotImplementedError("Paired Wilcoxon requires scipy.")
    # effect size: matched-pairs rank biserial
    ...
```

Update `rq3/config.yaml`:
```yaml
statistical_method: paired_wilcoxon
bonferroni_n: 15   # 5 coverage levels × 3 contract types
```

### Fix 7 [RECOMMENDED] — Resolve H1 threshold inconsistency

Decide canonical threshold (0.70 from methodology.md or 0.80 from rq1/config.yaml) and
update all three locations: `docs/methodology.md` line 32, `docs/experimental_design_v2.md`
lines 32–43, `experiments/rq1/config.yaml` lines 8–9 and 60.

### Fix 8 [RECOMMENDED] — Implement confidence weight lock check in runner

**File:** `src/legacy_contract/evaluation/runner.py`

In `ExperimentRunner.__init__` or `run()`, add:
```python
import yaml as _yaml
weights_path = self._project_root / "config" / "confidence_weights.yaml"
if weights_path.exists():
    with weights_path.open() as f:
        wcfg = _yaml.safe_load(f)
    if wcfg.get("locked") and wcfg.get("locked_at"):
        # Verify runtime weights match YAML
        from legacy_contract.contracts.model import ConfidenceVector
        runtime_weights = ConfidenceVector()._weights
        yaml_weights = wcfg["weights"]
        if runtime_weights != yaml_weights:
            raise RuntimeError(
                "ConfidenceVector weights diverge from locked config/confidence_weights.yaml. "
                "Restore weights or intentionally update both sources."
            )
```

### Fix 9 [RECOMMENDED] — Add `dataset_version` and `ground_truth_version` to all configs

**Files:** all four experiment configs

Add before `output_dir`:
```yaml
dataset_version: null   # fill with git commit hash before locking
ground_truth_version: null   # fill with git commit hash of benchmark file
```

And update `ExperimentConfig.from_yaml` to load (but not require) these fields.

### Fix 10 [RECOMMENDED] — Fix config_hash race condition

**File:** `src/legacy_contract/evaluation/runner.py` lines 232–283

Move hash computation to immediately after config load:
```python
config = ExperimentConfig.from_yaml(config_path)
initial_hash = config.config_hash()   # before any mutation
if self._bootstrap_n_override is not None:
    config.bootstrap_n = self._bootstrap_n_override
...
record = RunRecord(config_hash=initial_hash, ...)
```

### Fix 11 [RECOMMENDED] — Differentiate ablation conditions E0–E5

**File:** `src/legacy_contract/evaluation/runner.py` lines 871–892

Replace the `static_conditions` set with condition-specific pipeline calls:
```python
if condition == "E0_source_only":
    return self._run_source_only(config)
elif condition == "E1_structural":
    return self._run_structural_baseline(config)
elif condition == "E2_static_contracts":
    return self._run_static_contracts_only(config)
elif condition == "E3_static_bcg":
    preds, _ = self._run_static_extractor(...)
    return preds
elif condition == "E4_bcg_provenance":
    return self._run_bcg_with_provenance(config)
...
```

---

## Items That Are Acceptable As-Is

The following design decisions were reviewed and found acceptable without changes:

1. **Bootstrap CI with n=10000** — Standard and adequate. Percentile bootstrap is correct
   for bounded metrics. Index computation is correctly implemented.

2. **Mann-Whitney U for RQ2** — Correct for independent-groups baseline comparisons.
   The manual fallback (`_manual_mann_whitney`) correctly uses the normal approximation
   with tie handling. This is appropriate when scipy is unavailable.

3. **Effect size pairing (rank-biserial r + Cohen's d)** — Reporting both is correct.
   `StatisticalTest.effect_size` stores Cohen's d with a bootstrap CI, while `effect_r`
   (rank-biserial) is computed but not stored in the returned object. Consider also storing
   `effect_r` in `StatisticalTest` for completeness.

4. **All 5 baselines specified in rq2/config.yaml** — Confirmed complete (A–E).

5. **RQ3 coverage subsample is seeded and reproducible** — `_random.Random(config.random_seed)`
   creates an isolated RNG that does not pollute global state. Correct.

6. **Per-type breakdown in `_compute_per_type`** — Logic is correct for precision/recall/F1
   when `pred_types` is provided. The fallback to `pred_set` when `pred_types` is None
   (line 525) is a reasonable default for conditions where type labels are unavailable.

7. **`Benchmark.add_item` raises on locked benchmark** — Correct leakage prevention at the
   data layer. The issue is only that the runner doesn't check the lock before reading.

8. **RQ2 `n_mutations_per_category: 50` (150 total)** — Appropriate sample size for
   mutation-based evaluation in the literature (50 per fault category is standard).

9. **Separate H1a/H1b/H1c sub-hypotheses in experimental_design_v2.md** — Methodologically
   sound. Per-type thresholds prevent a single strong contract type from masking poor
   performance on another. The multi-part decision rule (FULLY/PARTIALLY/NOT SUPPORTED) is
   appropriate for a conjunctive hypothesis.

10. **`_pending_result` as failure mode** — Returning `[RESULT_PENDING]` rather than raising
    or fabricating results is correct scientific practice. The runner will not silently produce
    misleading numbers when data is missing.

11. **`RUN_LOG.jsonl` append-only audit trail** — Correct. Append-only prevents retrospective
    modification of the experiment log.

12. **Bonferroni correction (not Holm-Bonferroni) for RQ2** — Bonferroni is more conservative
    but simpler and widely accepted. For n=5 comparisons, the power difference from
    Holm-Bonferroni is small. Acceptable as-is; Holm-Bonferroni would be a minor improvement.

13. **`random_seed: 42` across all experiments** — Using the same seed across experiments is
    acceptable. Seeds are applied to isolated RNG instances (`random.Random(seed)`) and do
    not share state across experiments.

14. **`abort_if_gt_empty: true` in rq1 config** — Correct guard. The runner already handles
    this via the `[RESULT_PENDING]` mechanism.

---

## Confirmation

This audit report has been written to:

```
legacy-contract/docs/experimental_methods_audit.md
```

The audit was conducted as a static code and config reading exercise. No experiments were
run, no result files were created or modified, and no data was synthesized.
