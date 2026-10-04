# Baseline Final Specification

**BASELINE PARAMETERS ARE FROZEN AS OF THIS DOCUMENT. NO POST-HOC TUNING.**

Version: 1.0
Date: 2025-01
Status: Frozen for evaluation

---

## 1. Summary Table of All Methods

| ID | Method Name | File | Input | Output | Primary Metric | LLM Dependency | Execution Cost |
|----|-------------|------|-------|--------|----------------|---------------|----------------|
| A | Structural Dependency | `baselines/structural/structural.py` | IRGraph (original + mutated) | `list[StructuralRiskItem]` — one per missing structural edge | Recall of structural edge deletions | None | O(E) — linear in edges |
| B | Complexity Metrics | `baselines/complexity/complexity.py` | IRGraph, MutationRecord, contract_ids | `BaselineResult` — per-contract bool + confidence | F1 on contract violation detection | None | O(E + V) |
| C | LLM-Only | `baselines/llm_only/llm_only.py` | original_code, modified_code, change_description | `LLMAnalysisRecord` — per-artifact is_regression verdict | F1; report mean ± std across N_RUNS=5 | Required (OpenAI) | ~1–5 API calls/item |
| D | Dependency + LLM | `baselines/dep_llm/dep_llm.py` | IRGraph, MutationRecord, contract_ids | `BaselineResult` — per-contract bool + confidence | F1 on contract violation detection | Required (OpenAI) | 1 API call/mutation |
| E | Static BCG Only | `baselines/static_bcg/static_bcg.py` | IRGraph (original + mutated), MutationRecord | `BaselineResult` — per-contract bool + confidence | F1 on contract violation detection; comparator for RQ3 | None | O(V + E + C) |
| Proposed | BCG + Dynamic | `src/legacy_contract/bcg/`, `reconciliation/engine.py` | IRGraph + ExecutionTraces | BCG with validated contracts, BCGDiff | F1, precision, recall per contract type | None | O(V + E + C + T) |

**Key:**
- V = entities, E = relations/edges, C = contracts, T = trace events

---

## 2. Per-Method Specification

### Baseline A — Structural Dependency Analysis

**File:** [`baselines/structural/structural.py`](../baselines/structural/structural.py)

**Input:** `IRGraph` (original and mutated versions)

**Output:** `list[StructuralRiskItem]` — one item per structural edge present in original but absent in mutated graph.

**Method:** Builds a `StructuralDependencyGraph` from the IR and calls `detect_risk(original_sdg, mutated_sdg)` to find missing edges.

**Metric:** Used in RQ2 as structural lower-bound. Evaluated for precision/recall/F1 of risk detection against ground-truth mutation benchmark.

**Limitations (by design):**
- No behavioral semantics — all dependency edges treated as equivalent
- No contract types — cannot distinguish temporal from resource dependencies
- No confidence calibration — binary presence/absence
- No provenance — cannot explain why risk was flagged
- No dynamic grounding — purely static

**LLM Dependency:** None

**Execution Cost:** O(E) where E = number of structural edges

**Common result schema gap:** Returns `list[StructuralRiskItem]`, NOT a `BaselineResult`. See Section 5 (Adapter Requirements).

---

### Baseline B — Complexity Metrics

**File:** [`baselines/complexity/complexity.py`](../baselines/complexity/complexity.py)

**Input:** `IRGraph`, `MutationRecord`, `list[str]` (contract_ids)

**Output:** `BaselineResult(method="complexity_metrics", predictions, confidence, metadata)`

**Method:** Computes five per-artifact metrics, min-max normalizes them across all artifacts, computes a weighted risk_score, and flags contracts as predicted-violated if the affected artifact's risk_score exceeds `RISK_THRESHOLD`.

**Metrics computed:**

| ID | Metric | Weight | Rationale |
|----|--------|--------|-----------|
| M1 | `structural_complexity` | 0.20 | Entity count is a proxy for surface area |
| M2 | `dependency_count` | 0.30 | Coupling is the primary blast-radius driver |
| M3 | `step_count` | 0.20 | More steps → more ordering obligations |
| M4 | `dataset_reference_count` | 0.15 | Dataset usage is a source of resource contracts |
| M5 | `condition_count` | 0.15 | COND parameters are a source of control-flow contracts |

**Pre-specified risk threshold:** `RISK_THRESHOLD = 0.50`

**Threshold rationale:** The mid-point of the normalized score range [0, 1] is chosen as the threshold. This is the least-informative prior — it does not bias toward recall (low threshold) or precision (high threshold). The value was decided BEFORE any evaluation data was observed, as required by the experimental protocol.

**Limitations:**
- Treats all complexity as homogeneous — a JCL with many short steps gets the same score as one with few long steps
- Single-artifact normalization degrades to zero when only one artifact is present (no relative comparison possible)
- Risk propagation is binary — either the affected artifact is high-risk or not
- Does not distinguish which specific contracts are at risk

**LLM Dependency:** None

**Execution Cost:** O(V + E) where V = entities, E = relations

---

### Baseline C — LLM-Only Semantic Analysis

**File:** [`baselines/llm_only/llm_only.py`](../baselines/llm_only/llm_only.py)

**Input:** `artifact_name`, `artifact_type`, `original_code`, `modified_code`, `change_description`

**Output:** `LLMAnalysisRecord` — one record per item with `is_regression`, `contract_type`, `llm_confidence`, `explanation`, `violated_contract`, full provenance.

**Method:** Sends artifact source text + mutation description to LLM (OpenAI Chat Completions). Parses JSON response. Repeats N_RUNS=5 times per item to characterize LLM variance.

**Metric:** F1 on is_regression detection; must report mean ± std across N_RUNS. UNAVAILABLE results must be excluded from metric computation.

**Limitations:**
- LLM nondeterminism — results vary across runs even at temperature=0.0
- No structural grounding — LLM must infer dependencies from source text
- Token window limits source to first 3000 characters (truncated)
- No explicit contract structure — cannot map verdicts to specific contract IDs
- Cost: ~5 API calls per mutation item × N_RUNS

**LLM Dependency:** Required. OpenAI API key + `openai` package. Graceful degradation returns `LLMVerdict.UNAVAILABLE`.

**Execution Cost:** ~5 API calls per evaluation item (N_RUNS=5)

**Common result schema gap:** Returns `LLMAnalysisRecord`, NOT a `BaselineResult`. See Section 5 (Adapter Requirements).

---

### Baseline D — Dependency + LLM

**File:** [`baselines/dep_llm/dep_llm.py`](../baselines/dep_llm/dep_llm.py)

**Input:** `IRGraph`, `MutationRecord`, `list[str]` (contract_ids)

**Output:** `BaselineResult(method="dep_llm", predictions, confidence, metadata)` including `prompt_version`, `model`, `dependency_context_length`

**Method:**
1. Runs `StructuralBaselineAnalyzer.analyze()` to build a `StructuralDependencyGraph`
2. Renders a textual dependency context (affected entities, predecessors, successors)
3. Passes context + mutation description to LLM with `prompt_version = "dep_llm_v1"`
4. Maps LLM verdict to all requested contract_ids

**Prompt version:** `dep_llm_v1` (frozen — increment on any prompt text change)

**LLM call record fields:** `model`, `prompt_version`, `temperature`, `seed`, `input_hash`, `output`, `timestamp`, `latency_ms`, `error`

**Stub mode:** When LLM is unavailable returns `predictions={}`, `metadata["llm_available"]=False`

**Limitations:**
- Single LLM call per mutation — does not repeat N_RUNS times (unlike Baseline C)
- Dependency context is truncated at 4000 characters to avoid token overflow
- All contract IDs receive the same prediction (same LLM call)
- LLM nondeterminism applies

**LLM Dependency:** Required for real predictions. Graceful stub mode when unavailable.

**Execution Cost:** 1 API call per mutation (no N_RUNS repetition)

---

### Baseline E — Static BCG Only

**File:** [`baselines/static_bcg/static_bcg.py`](../baselines/static_bcg/static_bcg.py)

**Input:** `IRGraph` (original + mutated) or pre-built `BCG` pair, `MutationRecord`

**Output:** `BaselineResult(method="static_bcg", predictions, confidence, metadata)`

**Method:**
1. Runs `StaticContractExtractor.extract(ir)` — temporal, resource, control-flow contracts
2. Calls `BCGBuilder.build(ir, static_result, traces=None)` — no dynamic evidence
3. Calls `original_bcg.diff(mutated_bcg)` — finds broken contracts
4. Maps `diff.broken` → `predictions[cid] = True`; remaining contracts → `False`
5. Confidence = `contract.confidence_score()` from original BCG (static_support only ≈ 0.25)

**RQ3 role:** Direct comparator for the full BCG+dynamic system. The difference in F1 between Baseline E and the proposed method measures the contribution of dynamic evidence (ReconciliationEngine).

**Invariants enforced:**
- `ReconciliationEngine` is never called
- `dynamic_observations` is always empty
- No contract may have `validation_state == STATIC_DYNAMIC_SUPPORTED`

**Limitations:**
- Static confidence only — dynamic_support = 0.0 for all contracts
- Cannot distinguish STATIC_CANDIDATE from truly validated contracts
- Confidence scores are homogeneous (all ≈ 0.25)
- May miss contracts that require dynamic observation to identify
- Subject to false positives from structural mutations without semantic impact

**LLM Dependency:** None

**Execution Cost:** O(V + E + C) where C = contracts extracted

---

### Proposed Method — BCG + Dynamic (Full System)

**Files:** `src/legacy_contract/bcg/`, `src/legacy_contract/static_analysis/`, `src/legacy_contract/reconciliation/`

**Input:** IRGraph + `list[ExecutionTrace]`

**Output:** BCG with validated contracts, BCGDiff with regression candidates

**Method:** Full pipeline: static extraction → BCGBuilder → ReconciliationEngine → BCG.diff(). Contracts are elevated to `STATIC_DYNAMIC_SUPPORTED` or `STATIC_DYNAMIC_CONFLICT` based on dynamic evidence.

**Limitations:**
- Requires execution traces — not always available
- Reconciliation engine may introduce false positives from trace noise
- Cross-artifact contracts depend on correct entity ID stability across parsers

---

## 3. Pre-specified Parameters (Frozen)

| Parameter | Value | Component | Rationale |
|-----------|-------|-----------|-----------|
| `RISK_THRESHOLD` | 0.50 | Baseline B | Mid-point of [0, 1]; no information-theoretic bias |
| `METRIC_WEIGHTS["structural_complexity"]` | 0.20 | Baseline B | Secondary tier |
| `METRIC_WEIGHTS["dependency_count"]` | 0.30 | Baseline B | Highest weight; coupling drives blast radius |
| `METRIC_WEIGHTS["step_count"]` | 0.20 | Baseline B | Secondary tier |
| `METRIC_WEIGHTS["dataset_reference_count"]` | 0.15 | Baseline B | Tertiary tier; higher parser noise |
| `METRIC_WEIGHTS["condition_count"]` | 0.15 | Baseline B | Tertiary tier; COND extraction is noisy |
| `PROMPT_VERSION` (Baseline C) | `"v1.0.0"` | Baseline C | Frozen before held-out evaluation |
| `PROMPT_VERSION` (Baseline D) | `"dep_llm_v1"` | Baseline D | Frozen before held-out evaluation |
| `temperature` (all LLM baselines) | 0.0 | C, D | Maximum determinism |
| `seed` (all LLM baselines) | 42 | C, D | Reproducibility seed |
| `N_RUNS` (Baseline C) | 5 | Baseline C | Per-item repetition for variance estimation |

---

## 4. Audit Findings for Existing Baselines A and C

### Baseline A (Structural Dependency) — Audit Findings

#### Finding A-1: Non-conforming result schema
**Severity:** HIGH  
**Detail:** `StructuralBaselineAnalyzer.analyze()` returns a `StructuralDependencyGraph`; `detect_risk()` returns `list[StructuralRiskItem]`. Neither returns a `BaselineResult`. The evaluation harness cannot compute metrics using the same code path as Baselines B, D, E.  
**Gap:** `StructuralRiskItem` has `item_id` (a UUID prefix) but not a `contract_id`. Mapping from risk items to ground-truth contract IDs requires an explicit adapter.  
**Adapter needed:** See Section 5.

#### Finding A-2: No per-contract predictions
**Severity:** HIGH  
**Detail:** The baseline produces structural edge diffs, not per-contract predictions. It has no concept of `contract_id`. When compared to ground truth contracts, an adapter must map `StructuralRiskItem` objects to contract IDs by matching `source_entity` + `target_entity` to BCG contract `subject_id` + `object_id`.  
**Adapter needed:** See Section 5.

#### Finding A-3: Binary confidence (always 1.0)
**Severity:** MEDIUM  
**Detail:** `StructuralRiskItem.confidence` is hardcoded to 1.0 for all items. This prevents calibration analysis and confidence-threshold experiments. No weighted scoring is possible.  
**Mitigation:** For RQ2, use binary predictions only. Do not attempt confidence-based AUC for Baseline A without implementing a confidence model.

#### Finding A-4: `StructuralDependencyGraph.edges` type annotation mismatch
**Severity:** LOW  
**Detail:** Field default annotated as `dict` but `__post_init__` converts to `list`. The `# type: ignore[assignment]` comments throughout indicate this is known. No functional impact.

#### Finding A-5: No `run_id` or `timestamp` in output
**Severity:** LOW  
**Detail:** Risk items do not carry a run_id or timestamp. Reproducibility tracing requires the caller to inject these from outside.

---

### Baseline C (LLM-Only) — Audit Findings

#### Finding C-1: Non-conforming result schema
**Severity:** HIGH  
**Detail:** `LLMOnlyAnalyzer.analyze_item()` returns an `LLMAnalysisRecord`, not a `BaselineResult`. The evaluation harness uses `predictions_to_ids()` to convert records to a list of predicted IDs, but this returns `record_id` (internal UUID) not `contract_id`.  
**Gap:** There is no path from `LLMAnalysisRecord` to a specific `contract_id` in the BCG. The LLM verdict is per-artifact/per-change, not per-contract.  
**Adapter needed:** See Section 5.

#### Finding C-2: `model_version` field never populated
**Severity:** MEDIUM  
**Detail:** `LLMAnalysisRecord.model_version` is initialized to `""` and never set by `analyze_item()`. The `LLMAdapter.call()` does not retrieve or store the actual model version from the API response. API response objects contain this via `response.model` (OpenAI) but it is not extracted.  
**Recommendation:** In `LLMAdapter.call()`, extract `response.model` and return it alongside the response text.

#### Finding C-3: Per-artifact granularity mismatch
**Severity:** MEDIUM  
**Detail:** Baseline C operates at the level of (artifact, change_description) tuples, producing one verdict per tuple. The evaluation framework operates at the level of `contract_id`. If one artifact contains multiple contracts, the single LLM verdict is shared across all contracts in that artifact — this inflates true positives when one relevant contract exists alongside irrelevant ones.

#### Finding C-4: `predictions_to_ids()` uses `record_id`, not `contract_id`
**Severity:** HIGH  
**Detail:** `LLMOnlyAnalyzer.predictions_to_ids()` returns `r.record_id` values, which are internal UUIDs for LLM call tracking. These cannot be matched against BCG `contract_id` values. Ground-truth comparison using this method will always produce F1=0 unless the adapter translates IDs.  
**Adapter needed:** See Section 5.

#### Finding C-5: Model provenance complete for all other fields
**Severity:** INFO (good)  
**Detail:** `model`, `temperature`, `seed`, `prompt_version`, `llm_input`, `llm_output`, `timestamp`, `latency_ms` are all populated correctly. The `input_hash()` method is correct. UNAVAILABLE/ERROR handling is correct. This baseline records provenance well for what it captures.

---

## 5. Adapter Code Required for Common Evaluation Interface

All six methods must produce a `BaselineResult` for the evaluation harness. Baselines B, D, and E already conform. Baselines A and C require adapter wrappers.

### Adapter for Baseline A

```python
# baselines/structural/adapter.py  (TO BE IMPLEMENTED)
from baselines.base import BaselineResult
from baselines.structural.structural import StructuralBaselineAnalyzer, StructuralDependencyGraph
from legacy_contract.bcg.model import BCG

def structural_to_baseline_result(
    original_sdg: StructuralDependencyGraph,
    mutated_sdg: StructuralDependencyGraph,
    bcg: BCG,                    # needed to map entity_ids to contract_ids
    contract_ids: list[str],
    run_id: str = "",
) -> BaselineResult:
    """
    Adapter: converts StructuralBaselineAnalyzer output to BaselineResult.

    A contract is predicted-violated if ANY of its (subject_id, object_id) edges
    are detected as broken by the structural diff.
    Confidence = 1.0 (binary structural baseline).
    """
    analyzer = StructuralBaselineAnalyzer()
    risk_items = analyzer.detect_risk(original_sdg, mutated_sdg)
    broken_entity_pairs = {
        (item.source_entity, item.target_entity)
        for item in risk_items
    }
    predictions = {}
    confidence = {}
    for cid in contract_ids:
        contract = bcg.contracts.get(cid)
        if contract:
            pair = (contract.subject_id, contract.object_id)
            predictions[cid] = pair in broken_entity_pairs
            confidence[cid] = 1.0 if predictions[cid] else 0.0
        else:
            predictions[cid] = False
            confidence[cid] = 0.0
    return BaselineResult(
        method="structural",
        predictions=predictions,
        confidence=confidence,
        run_id=run_id,
    )
```

### Adapter for Baseline C

```python
# baselines/llm_only/adapter.py  (TO BE IMPLEMENTED)
from baselines.base import BaselineResult
from baselines.llm_only.llm_only import LLMAnalysisRecord, LLMVerdict
from legacy_contract.bcg.model import BCG

def llm_records_to_baseline_result(
    records: list[LLMAnalysisRecord],
    bcg: BCG,
    contract_ids: list[str],
    artifact_to_contracts: dict[str, list[str]],  # artifact_name -> [contract_id]
    run_id: str = "",
) -> BaselineResult:
    """
    Adapter: converts LLMAnalysisRecord list to BaselineResult.

    Maps LLM per-artifact verdicts to per-contract predictions.
    All contracts in an artifact share the artifact's verdict.
    UNAVAILABLE and ERROR records are treated as no-prediction (excluded).

    artifact_to_contracts: caller must supply this mapping.
    """
    artifact_verdict: dict[str, bool] = {}
    artifact_confidence: dict[str, float] = {}
    for rec in records:
        if rec.verdict in {LLMVerdict.UNAVAILABLE, LLMVerdict.ERROR}:
            continue
        artifact_verdict[rec.artifact_name] = rec.is_regression
        artifact_confidence[rec.artifact_name] = rec.llm_confidence

    predictions = {}
    confidence = {}
    for cid in contract_ids:
        # Find which artifact owns this contract
        owning_artifact = None
        for artifact_name, cids in artifact_to_contracts.items():
            if cid in cids:
                owning_artifact = artifact_name
                break
        if owning_artifact and owning_artifact in artifact_verdict:
            predictions[cid] = artifact_verdict[owning_artifact]
            confidence[cid] = artifact_confidence[owning_artifact]
        # else: no prediction available → exclude from evaluation
    return BaselineResult(
        method="llm_only",
        predictions=predictions,
        confidence=confidence,
        metadata={"n_records": len(records), "n_unavailable": sum(
            1 for r in records if r.verdict in {LLMVerdict.UNAVAILABLE, LLMVerdict.ERROR}
        )},
        run_id=run_id,
    )
```

---

## 6. Evaluation Interface Contract

All baselines must be callable via the following interface for `ExperimentRunner._run_condition()`:

```python
result: BaselineResult = baseline.predict(
    ir=ir_graph,
    mutation=mutation_record,
    contract_ids=list_of_contract_ids,
)
assert isinstance(result.predictions, dict)   # contract_id -> bool
assert isinstance(result.confidence, dict)    # contract_id -> float in [0, 1]
assert result.method in {"structural", "complexity_metrics", "llm_only",
                          "dep_llm", "static_bcg"}
```

Baselines A and C require adapters (Section 5) to conform to this interface.

---

## 7. Experiment-to-Baseline Mapping

| Experiment | Research Question | Baselines Used | Notes |
|------------|------------------|----------------|-------|
| RQ1 | Contract recovery precision/recall | Proposed (BCG) only | No baselines used |
| RQ2 | Risk detection vs. baselines | A, B, C, D, E, Proposed | Pairwise Mann-Whitney U |
| RQ3 | Static-only vs. static+dynamic | **E (primary comparator)**, Proposed | E vs. Proposed isolates dynamic evidence contribution |
| Ablation | Evidence level contribution | E0–E7 conditions | E3 = Baseline E |
| Generalization | Cross-system transfer | Proposed, E | Held-out systems |

---

## 8. Scientific Integrity Statement

**Baseline parameters are frozen as of this document. No post-hoc tuning.**

Specifically:
- `RISK_THRESHOLD = 0.50` for Baseline B was set before any evaluation data was observed.
- All metric weights for Baseline B were set before any evaluation data was observed.
- `PROMPT_VERSION = "v1.0.0"` and `"dep_llm_v1"` are frozen; any prompt changes require incrementing the version and re-running affected experiments.
- `temperature = 0.0` and `seed = 42` for all LLM baselines are frozen.
- These values will not be adjusted to improve reported metrics.

Deviations from this policy must be documented with a rationale, a new version string, and must be reported as a modification in any publication using these results.

---

## 9. Implementation Decisions and Deviations from Spec

### Decision D-1: Baseline B — affected artifact mapping fallback
**Spec:** Flags the affected artifact if its risk_score > threshold.  
**Implementation:** When `mutation.affected_entity_ids` cannot be mapped to any known artifact path (e.g., the entity was in a mutated IR and is no longer accessible), the baseline falls back to using ALL artifacts and takes the maximum risk_score. This ensures a prediction is always produced even when entity mapping fails.  
**Rationale:** Fail-open (produce a prediction) is safer than fail-closed (return no predictions) for evaluation completeness.

### Decision D-2: Baseline B — single artifact normalizes to zero
**Spec:** "Normalizes scores to [0, 1]."  
**Implementation:** When only one artifact exists, min==max for all metrics, so all normalized scores are 0.0 and risk_score = 0.0. This means a single-artifact system will never trigger `risk_score > 0.5` and all predictions will be `False`.  
**Rationale:** With a single data point there is no relative complexity comparison to make. This is the correct behavior; the threshold was designed for multi-artifact systems.

### Decision D-3: Baseline D — single LLM call per mutation (not N_RUNS)
**Spec:** Baseline D specification did not specify N_RUNS.  
**Implementation:** One LLM call per mutation (no repetition). The variance quantification requirement (N_RUNS=5) applies to Baseline C only per spec.  
**Rationale:** Keeping cost proportional to Baseline C's single-call mode for the dep_llm variant. The caller may wrap `DepLLMBaseline.predict()` in a loop for variance analysis.

### Decision D-4: Baseline E — contract ID list optional
**Spec:** "returns all broken contracts as predicted violations."  
**Implementation:** `contract_ids` parameter is optional. When `None`, all contracts in the original BCG are used. This allows calling `predict_from_bcgs()` without maintaining a separate ID list.

### Decision D-5: BaselineResult — no input_hash field
**Spec:** `BaselineResult` dataclass as specified.  
**Implementation:** The spec did not include `input_hash` in `BaselineResult`. Input hashing is done at the individual call record level (in `DepLLMCallRecord.input_hash`) and stored in `metadata`. This avoids coupling the shared `BaselineResult` dataclass to LLM-specific concerns.
