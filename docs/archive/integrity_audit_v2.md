# Scientific Integrity & Reproducibility Audit — v2

**Auditor:** Automated static + dynamic code review  
**Date:** 2025-07  
**Scope:** `legacy-contract/` — all source, config, and test modules  
**Files read:** `tests/unit/test_all.py`, `tests/integration/test_pipeline.py`,
`tests/regression/test_known_contracts.py`, `config/confidence_weights.yaml`,
`src/legacy_contract/contracts/model.py`, `src/legacy_contract/reconciliation/engine.py`,
`src/legacy_contract/ir/model.py`, `src/legacy_contract/static_analysis/extractor.py`,
`src/legacy_contract/dynamic_analysis/model.py`, `src/legacy_contract/bcg/model.py`,
`src/legacy_contract/evaluation/runner.py`

---

## A. TEST COVERAGE GAPS

### A1 — Synthetic evidence (SYNTHETIC_STATIC) cannot upgrade to STATIC_DYNAMIC_SUPPORTED

**Finding: NOT TESTED. Gap is critical.**

`EventSourceType.SYNTHETIC_STATIC` exists and `ExecutionEvent.is_real_execution()` returns
`False` for it, yet **the `ReconciliationEngine` never checks `source_type`** before updating
`contract.validation_state` to `STATIC_DYNAMIC_SUPPORTED`. An event created with
`source_type=SYNTHETIC_STATIC` will pass through `_reconcile_precedes` exactly like a real
execution event, and `_update_contract` will promote the state to `STATIC_DYNAMIC_SUPPORTED`.

This is a **scientific integrity violation**: the upgrade to `STATIC_DYNAMIC_SUPPORTED` must
require `is_real_execution() == True`. No existing test verifies that synthetic events are
blocked from causing this promotion. See `tests/scientific/test_integrity.py::test_synthetic_static_cannot_upgrade_to_supported`.

---

### A2 — Provenance survives BCGDiff (contracts in the diff retain their provenance)

**Finding: NOT TESTED.**

`BCG.diff()` returns a `BCGDiff` containing direct references to the original `Contract`
objects (`preserved`, `broken`, `added` are lists of the same in-memory objects). Because
Python passes objects by reference, the provenance is technically preserved at the object
level — but there is **no test** that verifies this property.

If `BCGDiff` is ever serialized and deserialized (e.g., to JSON), provenance could be silently
dropped. No test round-trips the diff and checks that `c.provenance` is not `None` for every
contract in `broken` and `preserved`. Omission in a serialization path would be invisible.

---

### A3 — Confidence weights cannot be changed after being locked

**Finding: NOT TESTED — and the guard does not exist in implementation.**

`config/confidence_weights.yaml` has a `locked: false` field and a comment saying
"The ExperimentRunner checks this flag and refuses to run if weights were modified
after `locked_at`." **This guard is entirely absent from `ExperimentRunner`.**

The runner calls `config.config_hash()` but never reads `confidence_weights.yaml`, never
checks `locked`, and never rejects a run if weights changed post-lock. The only connection
between the YAML and the `ConfidenceVector` is the hard-coded default `_weights` dict inside
the dataclass, which duplicates the YAML values but ignores the lock. No test exercises or
enforces this boundary.

---

### A4 — The same contract is not extracted twice from the same source

**Finding: NOT TESTED.**

`StaticContractExtractor` delegates to three sub-extractors which each iterate over IR
relations independently. `IRGraph.add_entity` and `add_relation` deduplicate at the IR level,
but the **contract extraction layer has no deduplication**. Two calls to `.extract(ir)` on the
same `IRGraph` will produce doubled contract lists. Within a single call, if an IR graph
contains duplicate MUST_PRECEDE relations (e.g., from merging two parsers' outputs over the
same JCL), duplicate contracts will be emitted.

`BCG.add_contract` uses `contract_id` as the key, but `contract_id` is a random UUID
(generated fresh each call), not a deterministic hash of `(type, subject, predicate, object)`.
Therefore two extractions of the same structural fact will produce two distinct UUIDs and both
will be stored, resulting in duplicate semantic contracts.

---

### A5 — ConfidenceVector weight invariant (weights need not sum to 1.0 — is this intended?)

**Finding: Intentional but UNDOCUMENTED in tests.**

The YAML explicitly states:

> "Note: weights do not sum to 1.0 — this is intentional. The raw sum of weights =
> 0.25+0.30+0.15+0.10+0.20+0.10 = 1.10 (slight overcount compensated by
> ambiguity_penalty and clamping to [0,1])."

The in-code `_weights` default in `ConfidenceVector` matches this (sum = 1.10). The
`aggregate()` method clamps the final result to `[0, 1]`. This is **architecturally
intentional** — the model is an evidence-strength score, not a probability.

**However**, there is no machine-readable test that enforces this invariant. If a future
developer "fixes" the weights to sum to 1.0 (a natural impulse), the semantic meaning of the
score would silently change and calibration would shift. A test pinning the weight sum to
a known value (≈1.10 ± ε) would catch accidental re-normalization.

Additionally, there is no test verifying that `ambiguity_penalty=1.0` collapses the score to
`0.0` regardless of other dimension values, nor that the clamping at `[0,1]` is tight.

---

### A6 — HUMAN_VALIDATED is NOT downgraded (tested) but IS upgraded if evidence is stronger

**Finding: Downgrade prevention is tested; upgrade path is NOT tested and the code does
not implement it.**

`test_reconciliation_does_not_downgrade_human_validated` (unit/test_all.py:440) correctly
tests that `HUMAN_VALIDATED` is not demoted to `NOT_OBSERVED` when traces are empty.

**But the upgrade case is unspecified:** The comment in `_update_contract` says
"Don't downgrade HUMAN_VALIDATED or GROUND_TRUTH" — it does not say what should happen
if `CONTRADICTED` evidence arrives. Currently, `ReconciliationOutcome.CONTRADICTED` will
**unconditionally overwrite** `HUMAN_VALIDATED` with `STATIC_DYNAMIC_CONFLICT`
(see engine.py line 417: `contract.validation_state = ValidationState.STATIC_DYNAMIC_CONFLICT`).
This is likely wrong: a human-validated contract should not be demoted by a single contradicting
trace without escalation to UNRESOLVED or a conflict flag.

The code has a guard for `SUPPORTED` but not for `CONTRADICTED`. A CONTRADICTED result on a
HUMAN_VALIDATED contract should at minimum set a conflict flag rather than silently overwriting
the human annotation. **No test covers this behavior.**

---

## B. DETERMINISTIC ID AUDIT

### Entity ID Scheme

```python
# ir/model.py:122-123
key = f"{self.artifact_path}::{self.entity_type.value}::{self.name}"
self.entity_id = hashlib.sha256(key.encode()).hexdigest()[:16]
```

The ID is a 16-hex-character (64-bit) prefix of SHA-256(`artifact_path::entity_type::name`).

### Risk: Cross-Artifact Name Collision

**This is intentional design, not a bug — but it carries a material scientific risk.**

If `artifact_path` is included in the key, two programs with the same name in *different*
artifacts will produce *different* entity IDs, which is correct.

However: the **JCL parser** and **COBOL parser** may assign the same artifact path string for
the same program name. For example, if JCL declares `EXEC PGM=CBACT01C` and the COBOL parser
parses `CBACT01C.cbl`, but the artifact path stored in the COBOL entity is `CBACT01C.cbl`
while the JCL entity uses `test.jcl`, the IDs differ and the two representations of the same
logical program are **not merged**. This is visible in `test_pipeline.py:_build_ir()`, where
the merge loop calls `combined.add_entity(e)` for both parsers — deduplication works only
if both entities have the *same* artifact path, which they typically do not.

**Consequence for reconciliation:** `ReconciliationEngine._reconcile_contract` looks up events
by `contract.subject_id`. If the static contract was extracted from the JCL entity (ID based
on `pipeline.jcl`) but the execution trace refers to the COBOL entity (ID based on
`PRODUCER.cbl`), no events will match and the contract will be `NOT_OBSERVED` when it should
be `SUPPORTED`. This is a silent evaluation error that inflates the false-negative rate.

**Recommendation:** The ID scheme is deterministic and reproducible, which is good. The gap
is at the **entity resolution** layer: a canonical cross-artifact entity resolver is needed to
unify `PROGRAM::CBACT01C` across all artifact paths that define or reference it. Until this
exists, the evaluation results for contracts involving COBOL programs referenced from JCL will
be systematically under-counted. This should be documented as a known limitation in
`docs/limitations.md` and measured in the ablation study.

### Hash Truncation Risk

The entity ID uses only the first 16 hex characters (64 bits) of SHA-256. With ~1,000 entities
per system this poses negligible collision risk (birthday bound ≈ 2^32 pairs), but for large
corpora (>100,000 entities) this should be reviewed.

---

## C. CONFIDENCE WEIGHT LOCK

### C1 — The `locked` field is not read anywhere in the implementation

**Finding: GUARD IS MISSING.**

`config/confidence_weights.yaml` states that the `ExperimentRunner` checks the `locked` flag
and refuses to run if weights were modified after `locked_at`. **This is false.**

Evidence: a complete search of `evaluation/runner.py` finds zero references to
`confidence_weights.yaml`, `locked`, or `locked_at`. The `ConfidenceVector._weights` dict is
hard-coded as a default factory inside the dataclass and is never populated from the YAML at
runtime — neither in the runner, nor in the extractor, nor in any test.

The YAML is a human governance document with no machine enforcement.

### C2 — Weight derivation is duplicated and can diverge

Two places define the weights:
1. `config/confidence_weights.yaml` (the authoritative governance document)
2. `ConfidenceVector._weights` default factory in `contracts/model.py:165-172`

These currently agree (both sum to 1.10 with the same per-key values). But there is no test
that loads the YAML and asserts it matches the in-code defaults. A future change to the YAML
without updating the code (or vice versa) would be silent.

### C3 — Remediation required

To enforce the lock, the following must be added:

1. `ExperimentRunner.__init__` or `run()` should load `confidence_weights.yaml`, check
   `locked`, and if `locked: true`, verify that no weight has changed from the `locked_at`
   snapshot (or reject the run).
2. A startup test should assert that the YAML weights match `ConfidenceVector` defaults.
3. `ConfidenceVector` should accept weights as a constructor argument loaded from YAML, not
   as a hard-coded default, so there is a single source of truth.

---

## D. SCIENTIFIC INTEGRITY TESTS NEEDED

The following 10 tests are required in `tests/scientific/test_integrity.py`:

| # | Test name | What it tests | Why it matters | Expected assertion |
|---|-----------|--------------|----------------|--------------------|
| 1 | `test_synthetic_static_cannot_upgrade_to_supported` | SYNTHETIC_STATIC events must not cause `STATIC_DYNAMIC_SUPPORTED` | Confusing synthetic derivation with real execution inflates the dynamic-evidence F1 score | `assert contract.validation_state != ValidationState.STATIC_DYNAMIC_SUPPORTED` |
| 2 | `test_provenance_survives_bcgdiff` | Every contract in `BCGDiff.broken` and `BCGDiff.preserved` has a non-None `provenance` | Provenance is the audit trail; dropping it in a diff makes regression analysis non-reproducible | `assert c.provenance is not None for c in diff.broken + diff.preserved` |
| 3 | `test_weight_lock_yaml_matches_code_defaults` | Loaded YAML weights == `ConfidenceVector._weights` defaults | Weight drift between governance doc and runtime is a silent calibration error | `assert yaml_weights == ConfidenceVector()._weights` |
| 4 | `test_confidence_weight_sum_invariant` | `sum(ConfidenceVector()._weights.values()) ≈ 1.10` | Accidental renormalization changes the score semantics without breaking any existing test | `assert abs(total - 1.10) < 0.01` |
| 5 | `test_not_observed_ne_contradicted_all_contract_types` | Parametrized over all `ContractType` values: NOT_OBSERVED ≠ STATIC_DYNAMIC_CONFLICT | The distinction is the paper's core scientific claim; it must hold for every contract type | `assert state == NOT_OBSERVED; assert not c.has_conflict()` |
| 6 | `test_human_validated_not_overwritten_by_contradiction` | A HUMAN_VALIDATED contract subjected to a contradicting trace must not silently become STATIC_DYNAMIC_CONFLICT without trace | Silently overwriting human annotation with a single trace violates annotation primacy | `assert contract.validation_state != ValidationState.STATIC_DYNAMIC_CONFLICT` (or documents the expected override) |
| 7 | `test_duplicate_extraction_produces_no_duplicate_contracts` | Two calls to `StaticContractExtractor.extract(ir)` on the same IR produce semantically unique contracts | Duplicate contracts in the BCG inflate precision/recall denominators | `assert len({(c.contract_type, c.subject_id, c.predicate, c.object_id) for c in all_contracts}) == len(all_contracts)` |
| 8 | `test_ambiguity_penalty_one_collapses_score` | `ConfidenceVector(static_support=1.0, ..., ambiguity_penalty=1.0).aggregate() == 0.0` | Maximum ambiguity should eliminate confidence regardless of evidence strength | `assert score == 0.0` |
| 9 | `test_extraction_method_recorded_in_provenance` | Contracts extracted by `StaticContractExtractor` have `provenance.extraction_method == DETERMINISTIC` | Mislabelling extraction method contaminates the evidence-strength score | `assert c.provenance.extraction_method == ExtractionMethod.DETERMINISTIC` |
| 10 | `test_entity_id_is_cross_artifact_stable` | `IREntity` with the same `(artifact_path, entity_type, name)` produces the same `entity_id` across two instantiations | Stable IDs are required for reconciliation trace matching; instability means contracts are permanently `NOT_OBSERVED` | `assert e1.entity_id == e2.entity_id` |

---

## E. EXPERIMENT REPRODUCIBILITY

### E1 — config_hash: computed AFTER experiment runs

**Finding: RACE CONDITION — config_hash is computed post-run.**

In `ExperimentRunner.run()` (runner.py:279-304):

```python
config = ExperimentConfig.from_yaml(config_path)   # line 232 — config loaded
# ... experiment runs (lines 252-274)
record = RunRecord(
    config_hash=config.config_hash(),               # line 283 — hash computed AFTER run
    ...
)
```

The `config_hash` is stored in the `RunRecord` but is computed **after** the experiment
completes, not before. If the config YAML is modified during a run (e.g., by another process
or an editor), the stored hash will reflect the state at the end of the run, not the state
that was actually used. This creates a reproducibility gap: the hash in `RUN_LOG.jsonl` may
not match the config that produced the results.

**Recommendation:** Compute `config_hash` immediately after loading the config (before the
experiment runs) and store it in a local variable. Assert at the end that the hash has not
changed. This is a one-line fix:

```python
config = ExperimentConfig.from_yaml(config_path)
initial_hash = config.config_hash()   # ← compute HERE, before any run
# ...
assert config.config_hash() == initial_hash  # ← sanity check at end
```

### E2 — Result bleed-across experiments

**Finding: MODERATE RISK.**

`ExperimentRunner` stores a `MetricsCalculator` instance as `self._calc`. The `run()` method
re-initializes it with `self._calc = MetricsCalculator(seed=effective_seed)` on every call.
This prevents bleed if `.run()` is called multiple times on the same runner instance.

However, bootstrap sampling inside `MetricsCalculator` is seeded per-run, which is correct.
The risk is in `_run_rq3`, which calls `_run_at_coverage(0.0, config)` as a "static baseline"
**in addition to** iterating over `config.coverage_levels`. If `0.0` also appears in
`coverage_levels`, this baseline is computed twice with the same seed, which is correct
but wasteful. More importantly, the two calls share the same `_calc` instance, meaning
bootstrap RNG state after the first coverage-level call affects subsequent calls unless
`MetricsCalculator` is re-initialized between calls. This should be verified.

### E3 — Random seed coverage

**Finding: PARTIAL — seed is applied to `MetricsCalculator` but not to all random components.**

The `random_seed` from config is applied to `MetricsCalculator(seed=effective_seed)` which
controls bootstrap resampling. However:

1. In `_run_at_coverage`, a local `_random.Random(config.random_seed)` is created, which is
   correct — it does not share state with the global `random` module.
2. **No seed is applied to numpy/scipy** if those libraries are used internally in
   `MetricsCalculator` (this depends on the implementation of that class, which was not
   reviewed here).
3. The `uuid.uuid4()` calls for `contract_id`, `event_id`, etc. use the system PRNG, not the
   experiment seed. This means entity IDs and contract UUIDs are non-reproducible across runs.
   For evaluation purposes this does not matter (contracts are matched semantically, not by
   UUID), but it means the `RUN_LOG.jsonl` will have different contract IDs on each run,
   making exact reproduction of intermediate state impossible.
4. LLM-based extraction (when enabled) has `llm_temperature` recorded per `EvidenceItem` but
   **no seed or determinism guarantee** is enforced by the runner for LLM calls.

**Recommendation:** Document which components are seeded and which are intentionally
non-deterministic (e.g., UUIDs). Add a `reproducibility_notes` field to `RunRecord`.

---

## Summary Table

| Issue | Severity | Has Test | Has Guard |
|-------|----------|----------|-----------|
| SYNTHETIC_STATIC can upgrade state | **Critical** | ✗ | ✗ |
| Provenance survival in BCGDiff | Medium | ✗ | N/A (object ref) |
| Weight lock not enforced | **High** | ✗ | ✗ |
| Weight YAML ≠ code defaults possible | Medium | ✗ | ✗ |
| Duplicate contract extraction | Medium | ✗ | ✗ |
| HUMAN_VALIDATED overwritten by CONTRADICTED | **High** | ✗ | ✗ |
| config_hash computed post-run | Medium | ✗ | ✗ |
| Cross-artifact entity non-resolution | Medium | ✗ | Documented risk |
| NOT_OBSERVED ≠ CONTRADICTED (all types) | Low (tested for TEMPORAL) | Partial | In code |
| Seed not applied to LLM calls | Low | ✗ | ✗ |

---

*This audit was produced from static code reading. All findings should be verified against
the live test suite before filing issues.*
