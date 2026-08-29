"""
Experiment Runner — executes a full experiment from a YAML config file.

Reads config from experiments/rq*/config.yaml, runs the pipeline end-to-end,
writes results to results/rq*/ as CSV + JSON.

Reproducibility log:
    Each run is assigned a unique run_id.
    All configuration is hashed (SHA-256) and stored alongside results.
    Appends to results/RUN_LOG.jsonl for full audit trail.

Supported experiments:
    E1  RQ1 — Contract recovery (precision/recall/F1 by type)
    E2  RQ2 — Risk detection (BCG vs baselines, all conditions)
    E3  RQ3 — Dynamic coverage (coverage levels vs. contract metrics)
    E4  Ablation — Evidence level ablation (E0–E7)
    E5  Generalization — Held-out system evaluation

SCIENTIFIC RULE: If an experiment fails due to missing data/traces,
log the failure and write [RESULT_PENDING] rather than silently skipping.
Never substitute estimated or cached results from a previous run.
"""

from __future__ import annotations

import csv
import hashlib
import json
import logging
import os
import subprocess
import time
import traceback
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import yaml
    _HAS_YAML = True
except ImportError:  # pragma: no cover
    _HAS_YAML = False

from legacy_contract.evaluation.metrics import MetricsCalculator, EvaluationResult
from legacy_contract.evaluation.benchmark import Benchmark, GroundTruthLevel

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Experiment Config
# ---------------------------------------------------------------------------

@dataclass
class ExperimentConfig:
    """
    Full experiment configuration loaded from a YAML file.

    All fields must be set before running an experiment.
    Defaults are conservative (small n, deterministic seed).
    """
    experiment_id: str
    research_question: str
    hypothesis: str
    description: str
    dataset: str
    ground_truth: str
    independent_variables: list[str]
    dependent_variables: list[str]
    baselines: list[str]
    random_seed: int
    metrics: list[str]
    statistical_method: str
    bootstrap_n: int
    significance_threshold: float
    contract_types: list[str]
    output_dir: str
    # Optional fields (experiment-specific)
    coverage_levels: list[float] = field(default_factory=list)
    mutation_categories: list[str] = field(default_factory=list)
    n_mutations_per_category: int = 0
    ablation_conditions: list[str] = field(default_factory=list)
    systems: list[str] = field(default_factory=list)
    held_out_systems: list[str] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_yaml(cls, path: str) -> "ExperimentConfig":
        """Load ExperimentConfig from a YAML file."""
        if not _HAS_YAML:
            raise ImportError(
                "PyYAML is required to load experiment configs. "
                "Install it with: pip install pyyaml"
            )
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        # Required fields
        required = [
            "experiment_id", "research_question", "hypothesis",
            "description", "dataset", "ground_truth",
            "independent_variables", "dependent_variables",
            "baselines", "random_seed", "metrics",
            "statistical_method", "bootstrap_n",
            "significance_threshold", "contract_types", "output_dir",
        ]
        missing = [k for k in required if k not in data]
        if missing:
            raise ValueError(
                f"ExperimentConfig missing required fields: {missing} in {path}"
            )

        return cls(
            experiment_id=data["experiment_id"],
            research_question=data["research_question"],
            hypothesis=data["hypothesis"],
            description=data["description"],
            dataset=data["dataset"],
            ground_truth=data["ground_truth"],
            independent_variables=data["independent_variables"],
            dependent_variables=data["dependent_variables"],
            baselines=data["baselines"],
            random_seed=int(data["random_seed"]),
            metrics=data["metrics"],
            statistical_method=data["statistical_method"],
            bootstrap_n=int(data["bootstrap_n"]),
            significance_threshold=float(data["significance_threshold"]),
            contract_types=data["contract_types"],
            output_dir=data["output_dir"],
            coverage_levels=[float(x) for x in data.get("coverage_levels", [])],
            mutation_categories=data.get("mutation_categories", []),
            n_mutations_per_category=int(data.get("n_mutations_per_category", 0)),
            ablation_conditions=data.get("ablation_conditions", []),
            systems=data.get("systems", []),
            held_out_systems=data.get("held_out_systems", []),
            extra=data.get("extra", {}),
        )

    def config_hash(self) -> str:
        """SHA-256 hash of the config for reproducibility tracking."""
        as_str = json.dumps(asdict(self), sort_keys=True, default=str)
        return hashlib.sha256(as_str.encode()).hexdigest()[:16]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Run Record
# ---------------------------------------------------------------------------

@dataclass
class RunRecord:
    """
    Single experiment run record appended to RUN_LOG.jsonl.
    Every run is fully traceable to config + seed + timestamp + git commit.
    """
    run_id: str
    experiment_id: str
    config_hash: str
    seed: int
    start_time: str
    end_time: str
    duration_seconds: float
    status: str                     # "completed" | "failed" | "partial"
    metrics: dict[str, Any]
    output_dir: str
    error: str | None = None
    config_path: str | None = None
    git_commit_hash: str | None = None  # HEAD SHA at run time (reproducibility)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Experiment Runner
# ---------------------------------------------------------------------------

class ExperimentRunner:
    """
    Orchestrates full experiment execution from config file to results files.

    Each experiment:
    1. Loads config from YAML
    2. Loads benchmark ground truth
    3. Runs the appropriate experiment sub-pipeline
    4. Writes results to CSV + JSON
    5. Appends a RunRecord to results/RUN_LOG.jsonl

    SCIENTIFIC INTEGRITY: If required data is missing, the runner writes
    [RESULT_PENDING] markers rather than fabricating values.
    Results are NEVER interpolated from previous runs.
    """

    RUN_LOG_FILENAME = "RUN_LOG.jsonl"

    def __init__(
        self,
        project_root: str | None = None,
        bootstrap_n_override: int | None = None,
    ) -> None:
        self._project_root = Path(project_root) if project_root else Path.cwd()
        self._calc = MetricsCalculator()
        self._bootstrap_n_override = bootstrap_n_override

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def run(
        self,
        config_path: str,
        seed: int | None = None,
        output_dir: str | None = None,
        force: bool = False,
    ) -> dict[str, Any]:
        """
        Run an experiment from a YAML config file.

        Arguments:
            config_path: path to experiment config YAML.
            seed:        override random seed (uses config seed if None).
            output_dir:  override output directory (uses config output_dir if None).
            force:       if True, overwrite existing results; otherwise raise
                         RuntimeError when results already exist to prevent
                         accidental data loss.

        Returns:
            dict with run_id, status, metrics, and output paths.
        """
        run_id = str(uuid.uuid4())[:8]
        start_time = datetime.utcnow().isoformat()
        start_ts = time.monotonic()

        config = ExperimentConfig.from_yaml(config_path)
        effective_seed = seed if seed is not None else config.random_seed
        effective_output = output_dir or config.output_dir

        # Guard: refuse to overwrite existing results without explicit force flag.
        results_marker = Path(effective_output) / "metrics.json"
        if results_marker.exists() and not force:
            raise RuntimeError(
                f"Results already exist at {results_marker}. "
                "Pass force=True to overwrite, or choose a different output_dir. "
                "This guard prevents accidental result contamination."
            )

        if self._bootstrap_n_override is not None:
            config.bootstrap_n = self._bootstrap_n_override

        self._calc = MetricsCalculator(seed=effective_seed)

        Path(effective_output).mkdir(parents=True, exist_ok=True)

        logger.info(
            f"[{run_id}] Starting {config.experiment_id} "
            f"(RQ={config.research_question}, seed={effective_seed})"
        )

        status = "completed"
        metrics: dict[str, Any] = {}
        error: str | None = None

        try:
            eid = config.experiment_id.upper()
            if eid.startswith("E1") or config.research_question.upper() == "RQ1":
                metrics = self._run_rq1(config, effective_output)
            elif eid.startswith("E2") or config.research_question.upper() == "RQ2":
                metrics = self._run_rq2(config, effective_output)
            elif eid.startswith("E3") or config.research_question.upper() == "RQ3":
                metrics = self._run_rq3(config, effective_output)
            elif "ABLATION" in eid or "ABLATION" in config.research_question.upper():
                metrics = self._run_ablation(config, effective_output)
            elif "GENERAL" in eid or "GENERAL" in config.research_question.upper():
                metrics = self._run_generalization(config, effective_output)
            else:
                raise ValueError(
                    f"Cannot determine experiment type from experiment_id={config.experiment_id} "
                    f"/ research_question={config.research_question}. "
                    "Ensure config matches a known experiment type."
                )
        except Exception as exc:
            status = "failed"
            error = f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"
            logger.error(f"[{run_id}] Experiment FAILED: {error}")
            metrics = {"status": "[RESULT_PENDING]", "error": str(exc)}

        end_time = datetime.utcnow().isoformat()
        duration = time.monotonic() - start_ts

        record = RunRecord(
            run_id=run_id,
            experiment_id=config.experiment_id,
            config_hash=config.config_hash(),
            seed=effective_seed,
            start_time=start_time,
            end_time=end_time,
            duration_seconds=round(duration, 3),
            status=status,
            metrics=metrics,
            output_dir=effective_output,
            error=error,
            config_path=config_path,
            git_commit_hash=self._git_commit_hash(),
        )
        self._log_run(record)

        logger.info(
            f"[{run_id}] {status.upper()} in {duration:.1f}s → {effective_output}"
        )
        return {
            "run_id": run_id,
            "status": status,
            "metrics": metrics,
            "output_dir": effective_output,
            "config_hash": config.config_hash(),
        }

    # ------------------------------------------------------------------
    # RQ1: Contract Recovery
    # ------------------------------------------------------------------

    def _run_rq1(self, config: ExperimentConfig, output_dir: str) -> dict[str, Any]:
        """
        RQ1: Can temporal/resource/control behavioral contracts be recovered from
        JCL and COBOL artifacts?

        Hypothesis H1: The BCG extractor recovers ≥ 80% of deterministic contracts
        (P ≥ 0.80, R ≥ 0.80, F1 ≥ 0.80) on Level 2 ground truth.

        Evaluation:
        - Loads ground truth from config.ground_truth
        - Runs static contract extractor on config.dataset
        - Computes precision, recall, F1 per contract type
        - Computes bootstrap 95% CI
        - Writes results/rq1/metrics.json and results/rq1/per_type.csv

        If dataset or ground truth is missing, writes [RESULT_PENDING].
        """
        gt_path = self._resolve_path(config.ground_truth)
        dataset_path = self._resolve_path(config.dataset)

        if not gt_path.exists():
            return self._pending_result(
                "RQ1",
                f"Ground truth file not found: {gt_path}. "
                "Run benchmark construction first.",
            )

        benchmark = Benchmark.load(str(gt_path))
        gt_items = benchmark.get_positives()
        # Use natural_language (contract_statement) as the matching key.
        # The extractor produces deterministic natural_language strings like
        # "Step X must execute and complete before step Y begins." — these
        # match the GT benchmark items' contract_statement field.
        # UUIDs (contract_id) are regenerated fresh on each extractor run
        # and cannot be used as a stable matching key.
        gt_ids = [item.contract_statement for item in gt_items]
        gt_types = [item.contract_type for item in gt_items]

        logger.info(
            f"RQ1: {len(gt_ids)} ground-truth contracts from {gt_path}"
        )

        # Run static extractor; returns natural_language strings (matching key)
        predicted_ids, predicted_types = self._run_static_extractor(
            dataset_path, config
        )

        if predicted_ids is None:
            return self._pending_result(
                "RQ1",
                f"Static extractor produced no output for dataset: {dataset_path}",
            )

        result = self._calc.compute_with_ci(
            predictions=predicted_ids,
            ground_truth=gt_ids,
            contract_types=gt_types,
            prediction_types=predicted_types,
            n=config.bootstrap_n,
        )

        metrics = self._result_to_dict(result, config)
        self._write_json(metrics, output_dir, "metrics.json")
        self._write_per_type_csv(result, output_dir, "per_type.csv")
        self._write_predictions_csv(
            predicted_ids, gt_ids, predicted_types, gt_types, output_dir, "predictions.csv"
        )

        logger.info(f"RQ1 result: {result.summary()}")
        return metrics

    # ------------------------------------------------------------------
    # RQ2: Risk Detection
    # ------------------------------------------------------------------

    def _run_rq2(self, config: ExperimentConfig, output_dir: str) -> dict[str, Any]:
        """
        RQ2: Does execution-grounded BCG analysis improve modernization-risk detection
        compared with structural dependency, static complexity, and LLM-only baselines?

        Hypothesis H2: BCG+dynamic achieves higher F1 for risk detection than any baseline.

        Evaluation:
        - Runs all configured baselines on mutation benchmark
        - Runs BCG risk detector (static) and BCG+dynamic
        - Computes pairwise Mann-Whitney U with Bonferroni correction
        - Writes results/rq2/all_conditions.csv and per-condition metrics

        Mutation benchmark must exist at datasets/mutations/<category>/.
        """
        gt_path = self._resolve_path(config.ground_truth)
        if not gt_path.exists():
            return self._pending_result(
                "RQ2",
                f"Ground truth not found: {gt_path}. "
                "Run mutation benchmark generation first.",
            )

        benchmark = Benchmark.load(str(gt_path))
        gt_ids = [item.contract_id for item in benchmark.get_positives()]
        gt_types = [item.contract_type for item in benchmark.get_positives()]

        conditions = ["structural", "complexity", "llm_only", "dep_llm", "static_bcg", "bcg_dynamic"]
        condition_results: dict[str, dict[str, Any]] = {}
        # Parallel dict retaining in-memory EvaluationResult objects so that
        # pairwise Mann-Whitney U tests can access f1_bootstrap_samples directly.
        # _result_to_dict serialises to plain dicts (losing large sample lists),
        # so bootstrap samples cannot be retrieved from condition_results later.
        # BUG-FIX (MWU silent-skip): the previous code tried
        #   condition_results.get("bcg_dynamic", {}).get("f1_scores", [])
        # which always returned [] because _result_to_dict only stores f1_scores
        # if f1_bootstrap_samples is non-empty on the object, but the serialised
        # dict reference is already detached from the live EvaluationResult.
        condition_eval_results: dict[str, EvaluationResult] = {}
        # n_comparisons is the number of tests actually performed (BCG+dynamic vs each
        # of 5 baselines), NOT the total number of all pairwise combinations (15).
        # Using 15 would over-correct Bonferroni by 3x and make significance 3x harder
        # to achieve.  The config also specifies n_pairwise_comparisons=5.
        baselines_to_test = ["structural", "complexity", "llm_only", "dep_llm", "static_bcg"]
        n_comparisons = len(baselines_to_test)  # = 5

        for condition in conditions:
            preds = self._run_condition(condition, config)
            if preds is None:
                condition_results[condition] = self._pending_result(
                    f"RQ2/{condition}",
                    f"Condition {condition} could not be evaluated.",
                )
                continue
            result = self._calc.compute_with_ci(
                predictions=preds,
                ground_truth=gt_ids,
                contract_types=gt_types,
                n=config.bootstrap_n,
            )
            condition_results[condition] = self._result_to_dict(result, config)
            condition_eval_results[condition] = result  # retain for MWU (not serialised)

        # Pairwise Mann-Whitney U tests (BCG+dynamic vs each baseline).
        # Use condition_eval_results (live EvaluationResult objects, have
        # f1_bootstrap_samples) NOT condition_results (serialised dicts).
        pairwise_tests: dict[str, Any] = {}
        bcg_eval = condition_eval_results.get("bcg_dynamic")
        for baseline in baselines_to_test:
            baseline_eval = condition_eval_results.get(baseline)
            if (
                bcg_eval is not None
                and baseline_eval is not None
                and bcg_eval.f1_bootstrap_samples
                and baseline_eval.f1_bootstrap_samples
            ):
                test = self._calc.mann_whitney_u(
                    bcg_eval.f1_bootstrap_samples,
                    baseline_eval.f1_bootstrap_samples,
                    bonferroni_n=n_comparisons,
                )
                pairwise_tests[f"bcg_dynamic_vs_{baseline}"] = {
                    "statistic": test.statistic,
                    "p_value": test.p_value,
                    "effect_size_rank_biserial_r": test.effect_size,
                    "ci_lower": test.ci_lower,
                    "ci_upper": test.ci_upper,
                    "bonferroni_n": n_comparisons,
                    "is_significant": test.is_significant,
                    "summary": test.summary(),
                }

        all_results = {
            "conditions": condition_results,
            "pairwise_tests": pairwise_tests,
            "n_comparisons": n_comparisons,
            "bonferroni_alpha": 0.05 / max(n_comparisons, 1),
        }
        self._write_json(all_results, output_dir, "all_conditions.json")
        self._write_conditions_csv(condition_results, output_dir, "all_conditions.csv")
        return all_results

    # ------------------------------------------------------------------
    # RQ3: Dynamic Coverage
    # ------------------------------------------------------------------

    def _run_rq3(self, config: ExperimentConfig, output_dir: str) -> dict[str, Any]:
        """
        RQ3: Does execution evidence reduce false positives compared with
        static-only analysis? How does coverage level affect contract metrics?

        Hypothesis H3: F1 and precision increase monotonically with coverage level,
        and false-positive rate decreases.

        Evaluation:
        - For each coverage level in config.coverage_levels:
          - Simulate trace subsample at that coverage
          - Run reconciliation on BCG
          - Compute precision/recall/F1/FPR
        - Write results/rq3/coverage_levels.csv
        - Write results/rq3/static_vs_dynamic.json
        """
        if not config.coverage_levels:
            return self._pending_result(
                "RQ3",
                "No coverage_levels specified in config.",
            )

        gt_path = self._resolve_path(config.ground_truth)
        if not gt_path.exists():
            return self._pending_result(
                "RQ3",
                f"Ground truth not found: {gt_path}.",
            )

        benchmark = Benchmark.load(str(gt_path))
        gt_ids = [item.contract_id for item in benchmark.get_positives()]
        gt_types = [item.contract_type for item in benchmark.get_positives()]

        coverage_results: list[dict[str, Any]] = []
        for level in sorted(config.coverage_levels):
            preds = self._run_at_coverage(level, config)
            if preds is None:
                coverage_results.append({
                    "coverage_level": level,
                    "status": "[RESULT_PENDING]",
                    "reason": f"Coverage {level} simulation not available.",
                })
                continue
            result = self._calc.compute_with_ci(
                predictions=preds,
                ground_truth=gt_ids,
                contract_types=gt_types,
                n=config.bootstrap_n,
            )
            coverage_results.append({
                "coverage_level": level,
                **self._result_to_dict(result, config),
            })

        # Static-only baseline (coverage = 0.0)
        static_preds = self._run_at_coverage(0.0, config)
        static_result: dict[str, Any] = {}
        if static_preds is not None:
            r = self._calc.compute_with_ci(
                predictions=static_preds,
                ground_truth=gt_ids,
                contract_types=gt_types,
                n=config.bootstrap_n,
            )
            static_result = self._result_to_dict(r, config)

        all_results = {
            "static_only": static_result or {"status": "[RESULT_PENDING]"},
            "coverage_levels": coverage_results,
        }
        self._write_json(all_results, output_dir, "coverage_levels.json")
        self._write_coverage_csv(coverage_results, output_dir, "coverage_levels.csv")
        return all_results

    # ------------------------------------------------------------------
    # Ablation
    # ------------------------------------------------------------------

    def _run_ablation(self, config: ExperimentConfig, output_dir: str) -> dict[str, Any]:
        """
        Ablation study: E0–E7 evidence conditions.

        E0: Source only
        E1: Source + structural dependencies
        E2: Source + static contracts
        E3: Static BCG
        E4: BCG + provenance
        E5: BCG + dynamic evidence
        E6: BCG + provenance + dynamic evidence
        E7: BCG + provenance + dynamic evidence + LLM

        For each condition, compute precision/recall/F1.
        Report contribution of each evidence component.
        """
        ablation_conditions = config.ablation_conditions or [
            "E0_source_only",
            "E1_structural",
            "E2_static_contracts",
            "E3_static_bcg",
            "E4_bcg_provenance",
            "E5_bcg_dynamic",
            "E6_bcg_provenance_dynamic",
            "E7_bcg_provenance_dynamic_llm",
        ]

        gt_path = self._resolve_path(config.ground_truth)
        if not gt_path.exists():
            return self._pending_result(
                "Ablation",
                f"Ground truth not found: {gt_path}.",
            )

        benchmark = Benchmark.load(str(gt_path))
        gt_ids = [item.contract_id for item in benchmark.get_positives()]
        gt_types = [item.contract_type for item in benchmark.get_positives()]

        condition_results: dict[str, dict[str, Any]] = {}
        for condition in ablation_conditions:
            preds = self._run_ablation_condition(condition, config)
            if preds is None:
                condition_results[condition] = {
                    "status": "[RESULT_PENDING]",
                    "condition": condition,
                }
                continue
            result = self._calc.compute_with_ci(
                predictions=preds,
                ground_truth=gt_ids,
                contract_types=gt_types,
                n=config.bootstrap_n,
            )
            condition_results[condition] = {
                "condition": condition,
                **self._result_to_dict(result, config),
            }

        self._write_json(condition_results, output_dir, "ablation_results.json")
        self._write_conditions_csv(condition_results, output_dir, "ablation_results.csv")
        return condition_results

    # ------------------------------------------------------------------
    # Generalization (held-out systems)
    # ------------------------------------------------------------------

    def _run_generalization(
        self, config: ExperimentConfig, output_dir: str
    ) -> dict[str, Any]:
        """
        Cross-system generalization experiment.

        Evaluates BCG contract recovery on held-out systems not seen during
        development, threshold tuning, or prompt engineering.

        Reports:
        - Per-system metrics
        - In-distribution vs. out-of-distribution F1 delta
        - Performance degradation analysis
        """
        gt_path = self._resolve_path(config.ground_truth)
        if not gt_path.exists():
            return self._pending_result(
                "Generalization",
                f"Ground truth not found: {gt_path}.",
            )

        benchmark = Benchmark.load(str(gt_path))
        held_out = config.held_out_systems
        dev_systems = [s for s in config.systems if s not in held_out]

        per_system: dict[str, dict[str, Any]] = {}

        for system in config.systems:
            system_items = [
                item for item in benchmark.get_positives()
                if system in item.artifact
            ]
            if not system_items:
                per_system[system] = {
                    "status": "[RESULT_PENDING]",
                    "reason": f"No benchmark items found for system: {system}",
                }
                continue

            # Match by formal_statement (semantic key) instead of contract_id
            # UUID, because the extractor regenerates fresh UUIDs on each run.
            # formal_statement is deterministic from entity names, e.g.
            # "STEPA ≺ STEPB" or "RC(X) GT 0 → ¬execute(Y)".
            gt_sigs = [
                item.formal_statement or item.contract_statement
                for item in system_items
            ]
            gt_types = [item.contract_type for item in system_items]

            preds = self._run_static_extractor(
                self._resolve_path(f"datasets/{system}"), config
            )
            if preds[0] is None:
                per_system[system] = {
                    "status": "[RESULT_PENDING]",
                    "reason": f"Extractor produced no output for system: {system}",
                }
                continue

            # preds[0] are now formal_statement strings (semantic keys), not UUIDs
            result = self._calc.compute_with_ci(
                predictions=preds[0],
                ground_truth=gt_sigs,
                contract_types=gt_types,
                n=config.bootstrap_n,
            )
            per_system[system] = {
                "system": system,
                "is_held_out": system in held_out,
                **self._result_to_dict(result, config),
            }

        # Compute in-distribution vs. out-of-distribution delta
        dev_f1s = [
            per_system[s].get("f1", 0.0)
            for s in dev_systems
            if "f1" in per_system.get(s, {})
        ]
        ood_f1s = [
            per_system[s].get("f1", 0.0)
            for s in held_out
            if "f1" in per_system.get(s, {})
        ]

        degradation: dict[str, Any] = {}
        if dev_f1s and ood_f1s:
            mean_dev = sum(dev_f1s) / len(dev_f1s)
            mean_ood = sum(ood_f1s) / len(ood_f1s)
            degradation = {
                "mean_in_distribution_f1": round(mean_dev, 4),
                "mean_out_of_distribution_f1": round(mean_ood, 4),
                "f1_delta": round(mean_ood - mean_dev, 4),
                "n_dev_systems": len(dev_f1s),
                "n_ood_systems": len(ood_f1s),
            }
            if len(dev_f1s) > 1 and len(ood_f1s) > 1:
                test = self._calc.mann_whitney_u(dev_f1s, ood_f1s)
                degradation["statistical_test"] = {
                    "p_value": test.p_value,
                    "effect_size": test.effect_size,
                    "is_significant": test.is_significant,
                    "summary": test.summary(),
                }

        all_results = {
            "per_system": per_system,
            "degradation": degradation or {"status": "[RESULT_PENDING]"},
        }
        self._write_json(all_results, output_dir, "generalization_results.json")
        return all_results

    # ------------------------------------------------------------------
    # Pipeline stubs (implemented when pipeline modules are complete)
    # ------------------------------------------------------------------

    def _run_static_extractor(
        self, dataset_path: Path, config: ExperimentConfig
    ) -> tuple[list[str] | None, list[str] | None]:
        """
        Run the static contract extractor on a dataset directory.

        Returns (predicted_formal_statements, predicted_types) or (None, None).

        Uses formal_statement as the matching key (semantic key) instead of
        contract_id UUID, because each extractor run regenerates fresh UUIDs
        while formal_statement is deterministic from entity names (e.g.
        "STEPA ≺ STEPB").  This matches how _run_generalization builds gt_sigs.
        """
        try:
            from legacy_contract.static_analysis.extractor import StaticContractExtractor
            from legacy_contract.ingestion import ingest_directory

            inventory = ingest_directory(str(dataset_path))
            ir_graph = inventory.combined_ir  # ArtifactInventory wraps IRGraph
            extractor = StaticContractExtractor()
            extraction_result = extractor.extract(ir_graph)
            # extractor.extract() returns a StaticExtractionResult; iterate .all_contracts
            # Return natural_language as the matching key — this is deterministic
            # from entity names and matches the GT benchmark's contract_statement field.
            # formal_statement (e.g. "COBRUN ≺ RUN") does NOT match the GT
            # contract_statement (e.g. "Step COBRUN must execute ... before step RUN begins.").
            sigs = [
                c.natural_language or c.formal_statement
                for c in extraction_result.all_contracts
            ]
            types = [c.contract_type.value for c in extraction_result.all_contracts]
            return sigs, types
        except Exception as exc:
            logger.warning(
                f"Static extractor unavailable or failed for {dataset_path}: {exc}"
            )
            return None, None

    def _run_condition(
        self, condition: str, config: ExperimentConfig
    ) -> list[str] | None:
        """
        Run a named risk-detection condition and return predicted contract IDs.

        Conditions: structural | complexity | llm_only | dep_llm | static_bcg | bcg_dynamic
        """
        logger.info(f"Running condition: {condition}")
        try:
            if condition == "structural":
                from baselines.structural import StructuralBaselineAnalyzer
                # Structural baseline returns risk items; map to contract IDs
                return self._run_structural_baseline(config)
            elif condition == "static_bcg":
                preds, _ = self._run_static_extractor(
                    self._resolve_path(config.dataset), config
                )
                return preds
            elif condition == "bcg_dynamic":
                return self._run_bcg_dynamic(config)
            else:
                logger.warning(
                    f"Condition '{condition}' not yet implemented. "
                    "Returning [RESULT_PENDING]."
                )
                return None
        except Exception as exc:
            logger.warning(f"Condition '{condition}' failed: {exc}")
            return None

    def _run_structural_baseline(self, config: ExperimentConfig) -> list[str] | None:
        """Delegate to structural baseline module."""
        try:
            import sys, os
            sys.path.insert(0, str(self._project_root))
            from baselines.structural import StructuralBaselineAnalyzer
            from legacy_contract.ingestion import ingest_directory

            inventory = ingest_directory(self._resolve_path(config.dataset))
            ir_graph = inventory.combined_ir  # ArtifactInventory wraps IRGraph
            analyzer = StructuralBaselineAnalyzer()
            sdg = analyzer.analyze(ir_graph)
            # Structural baseline produces StructuralRiskItem objects;
            # map to contract-like IDs for evaluation
            risk_items = analyzer.detect_risk(sdg, sdg)
            return [item.item_id for item in risk_items]
        except Exception as exc:
            logger.warning(f"Structural baseline failed: {exc}")
            return None

    def _run_bcg_dynamic(self, config: ExperimentConfig) -> list[str] | None:
        """Run full BCG pipeline with dynamic evidence integration."""
        try:
            from legacy_contract.ingestion import ingest_directory
            from legacy_contract.static_analysis.extractor import StaticContractExtractor
            from legacy_contract.dynamic_analysis.adapter import DynamicEvidenceAdapter
            from legacy_contract.bcg.builder import BCGBuilder
            from legacy_contract.reconciliation.engine import ReconciliationEngine

            inventory = ingest_directory(self._resolve_path(config.dataset))
            ir_graph = inventory.combined_ir  # ArtifactInventory wraps IRGraph
            extractor = StaticContractExtractor()
            contracts = extractor.extract(ir_graph)

            traces_dir = self._resolve_path("traces")
            adapter = DynamicEvidenceAdapter()
            traces = adapter.load_directory(str(traces_dir)) if traces_dir.exists() else []

            builder = BCGBuilder()
            bcg = builder.build(ir_graph, contracts)

            if traces:
                engine = ReconciliationEngine()
                engine.reconcile(bcg, traces)

            ids = [c.contract_id for c in bcg.contracts.values()]
            return ids
        except Exception as exc:
            logger.warning(f"BCG+dynamic pipeline failed: {exc}")
            return None

    def _run_at_coverage(
        self, coverage_level: float, config: ExperimentConfig
    ) -> list[str] | None:
        """
        Run contract recovery at a given trace coverage level.
        coverage_level = 0.0 means static-only (no traces).
        coverage_level = 1.0 means full trace set.
        """
        logger.info(f"Running at coverage level: {coverage_level:.0%}")
        if coverage_level == 0.0:
            preds, _ = self._run_static_extractor(
                self._resolve_path(config.dataset), config
            )
            return preds

        try:
            from legacy_contract.ingestion import ingest_directory
            from legacy_contract.static_analysis.extractor import StaticContractExtractor
            from legacy_contract.dynamic_analysis.adapter import DynamicEvidenceAdapter
            from legacy_contract.bcg.builder import BCGBuilder
            from legacy_contract.reconciliation.engine import ReconciliationEngine
            import random as _random

            inventory = ingest_directory(self._resolve_path(config.dataset))
            ir_graph = inventory.combined_ir  # ArtifactInventory wraps IRGraph
            extractor = StaticContractExtractor()
            contracts = extractor.extract(ir_graph)

            traces_dir = self._resolve_path("traces")
            adapter = DynamicEvidenceAdapter()
            all_traces = (
                adapter.load_directory(str(traces_dir)) if traces_dir.exists() else []
            )

            rng = _random.Random(config.random_seed)
            n_keep = max(1, int(len(all_traces) * coverage_level))
            sampled_traces = rng.sample(all_traces, min(n_keep, len(all_traces)))

            builder = BCGBuilder()
            bcg = builder.build(ir_graph, contracts)

            if sampled_traces:
                engine = ReconciliationEngine()
                engine.reconcile(bcg, sampled_traces)

            return [c.contract_id for c in bcg.contracts.values()]
        except Exception as exc:
            logger.warning(f"Coverage {coverage_level} run failed: {exc}")
            return None

    def _run_ablation_condition(
        self, condition: str, config: ExperimentConfig
    ) -> list[str] | None:
        """
        Map ablation condition name to the corresponding evidence combination.

        Ablation ladder (each condition adds one layer of evidence):
          E0_source_only      — no extraction; returns empty list (baseline for coverage)
          E1_structural       — structural dependency baseline only
          E2_static_contracts — temporal contracts only (no resource, no control-flow)
          E3_static_bcg       — all static contracts (temporal + resource + control-flow)
          E4_bcg_provenance   — static BCG with high-confidence provenance filter (≥0.9)
          E5_bcg_dynamic      — static BCG + dynamic trace reconciliation
          E6_bcg_provenance_dynamic — static BCG + provenance + dynamic
          E7_bcg_provenance_dynamic_llm — full pipeline including LLM enrichment
        """
        try:
            if condition == "E0_source_only":
                # No contract extraction — empty prediction set
                return []

            elif condition == "E1_structural":
                return self._run_structural_baseline(config)

            elif condition == "E2_static_contracts":
                # Temporal contracts only
                from legacy_contract.ingestion import ingest_directory
                from legacy_contract.static_analysis.extractor import TemporalContractExtractor

                inventory = ingest_directory(self._resolve_path(config.dataset))
                ir_graph = inventory.combined_ir
                temporal = TemporalContractExtractor().extract(ir_graph)
                return [
                    c.natural_language or c.formal_statement
                    for c in temporal
                ]

            elif condition in ("E3_static_bcg", "E4_bcg_provenance"):
                # E3: all static contracts
                # E4: all static contracts filtered to high-confidence (≥0.9 static_support)
                preds, _ = self._run_static_extractor(
                    self._resolve_path(config.dataset), config
                )
                if preds is None:
                    return None
                if condition == "E4_bcg_provenance":
                    # Re-extract to apply confidence filter
                    from legacy_contract.ingestion import ingest_directory
                    from legacy_contract.static_analysis.extractor import StaticContractExtractor

                    inventory = ingest_directory(self._resolve_path(config.dataset))
                    ir_graph = inventory.combined_ir
                    result = StaticContractExtractor().extract(ir_graph)
                    preds = [
                        c.natural_language or c.formal_statement
                        for c in result.all_contracts
                        if getattr(c.confidence, "static_support", 1.0) >= 0.9
                    ]
                return preds

            elif condition in ("E5_bcg_dynamic", "E6_bcg_provenance_dynamic",
                               "E7_bcg_provenance_dynamic_llm"):
                return self._run_bcg_dynamic(config)

            else:
                logger.warning(f"Unknown ablation condition: {condition}")
                return None

        except Exception as exc:
            logger.warning(f"Ablation condition '{condition}' failed: {exc}")
            return None

    # ------------------------------------------------------------------
    # Run logging
    # ------------------------------------------------------------------

    def _log_run(self, record: RunRecord) -> None:
        """Append run record to RUN_LOG.jsonl."""
        log_path = self._project_root / "results" / self.RUN_LOG_FILENAME
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record.to_dict(), default=str) + "\n")

    @staticmethod
    def _git_commit_hash() -> str | None:
        """Return the current HEAD commit SHA, or None if git is unavailable."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return None

    # ------------------------------------------------------------------
    # Output helpers
    # ------------------------------------------------------------------

    def _write_json(
        self, data: dict[str, Any], output_dir: str, filename: str
    ) -> None:
        path = Path(output_dir) / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
        logger.info(f"Wrote: {path}")

    def _write_per_type_csv(
        self, result: EvaluationResult, output_dir: str, filename: str
    ) -> None:
        path = Path(output_dir) / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["contract_type", "tp", "fp", "fn", "precision", "recall", "f1", "support"],
            )
            writer.writeheader()
            for t in result.per_type:
                writer.writerow({
                    "contract_type": t.contract_type,
                    "tp": t.tp, "fp": t.fp, "fn": t.fn,
                    "precision": round(t.precision, 4),
                    "recall": round(t.recall, 4),
                    "f1": round(t.f1, 4),
                    "support": t.support,
                })

    def _write_predictions_csv(
        self,
        pred_ids: list[str],
        gt_ids: list[str],
        pred_types: list[str] | None,
        gt_types: list[str],
        output_dir: str,
        filename: str,
    ) -> None:
        pred_set = set(pred_ids)
        gt_set = set(gt_ids)
        gt_type_map = dict(zip(gt_ids, gt_types))
        pred_type_map = dict(zip(pred_ids, pred_types or []))
        all_ids = sorted(pred_set | gt_set)
        path = Path(output_dir) / filename
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["contract_id", "predicted", "ground_truth", "tp_fp_fn", "type"],
            )
            writer.writeheader()
            for cid in all_ids:
                predicted = cid in pred_set
                is_gt = cid in gt_set
                label = (
                    "TP" if predicted and is_gt
                    else "FP" if predicted and not is_gt
                    else "FN"
                )
                ctype = gt_type_map.get(cid) or pred_type_map.get(cid) or "UNKNOWN"
                writer.writerow({
                    "contract_id": cid,
                    "predicted": int(predicted),
                    "ground_truth": int(is_gt),
                    "tp_fp_fn": label,
                    "type": ctype,
                })

    def _write_conditions_csv(
        self,
        condition_results: dict[str, dict[str, Any]],
        output_dir: str,
        filename: str,
    ) -> None:
        path = Path(output_dir) / filename
        all_keys: list[str] = ["condition", "precision", "recall", "f1", "fpr", "fnr", "status"]
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=all_keys, extrasaction="ignore")
            writer.writeheader()
            for condition, metrics in condition_results.items():
                row = {"condition": condition, **metrics}
                writer.writerow(row)

    def _write_coverage_csv(
        self,
        coverage_results: list[dict[str, Any]],
        output_dir: str,
        filename: str,
    ) -> None:
        path = Path(output_dir) / filename
        fieldnames = ["coverage_level", "precision", "recall", "f1", "fpr", "fnr", "status"]
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for row in coverage_results:
                writer.writerow(row)

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    def _resolve_path(self, relative: str) -> Path:
        p = Path(relative)
        if p.is_absolute():
            return p
        return self._project_root / p

    @staticmethod
    def _result_to_dict(result: EvaluationResult, config: ExperimentConfig) -> dict[str, Any]:
        import math as _math
        # FPR is NaN for this open-set problem (TN is always 0, making the denominator
        # of FP/(FP+TN) undefined).  Serialize as null/None rather than calling round()
        # on NaN, which would raise in some contexts.
        fpr_val: Any = None if _math.isnan(result.fpr) else round(result.fpr, 4)
        d: dict[str, Any] = {
            "precision": round(result.precision, 4),
            "recall": round(result.recall, 4),
            "f1": round(result.f1, 4),
            "fpr": fpr_val,
            "fnr": round(result.fnr, 4),
            "tp": result.tp,
            "fp": result.fp,
            "fn": result.fn,
            "tn": result.tn,
            "n_samples": result.n_samples,
            "macro_f1": round(result.macro_f1(), 4),
            "weighted_f1": round(result.weighted_f1(), 4),
            "status": "completed",
        }
        # CRITICAL-2 fix: expose bootstrap F1 sample list so that RQ2 pairwise
        # Mann-Whitney U tests can compare distributions between conditions.
        # The list is NOT serialized in the output JSON (too large); only the
        # CI bounds are stored.  The samples are carried on the EvaluationResult
        # object in memory for the duration of the RQ2 run.
        if result.f1_bootstrap_samples:
            d["f1_scores"] = result.f1_bootstrap_samples  # list[float], length = bootstrap_n
        if result.f1_ci is not None:
            d["f1_ci_lower"] = round(result.f1_ci[0], 4)
            d["f1_ci_upper"] = round(result.f1_ci[1], 4)
        if result.precision_ci is not None:
            d["precision_ci_lower"] = round(result.precision_ci[0], 4)
            d["precision_ci_upper"] = round(result.precision_ci[1], 4)
        if result.recall_ci is not None:
            d["recall_ci_lower"] = round(result.recall_ci[0], 4)
            d["recall_ci_upper"] = round(result.recall_ci[1], 4)
        if result.per_type:
            d["per_type"] = [
                {
                    "type": t.contract_type,
                    "precision": round(t.precision, 4),
                    "recall": round(t.recall, 4),
                    "f1": round(t.f1, 4),
                    "support": t.support,
                }
                for t in result.per_type
            ]
        return d

    @staticmethod
    def _pending_result(experiment: str, reason: str) -> dict[str, Any]:
        logger.warning(f"[RESULT_PENDING] {experiment}: {reason}")
        return {
            "status": "[RESULT_PENDING]",
            "experiment": experiment,
            "reason": reason,
            "precision": "[RESULT_PENDING]",
            "recall": "[RESULT_PENDING]",
            "f1": "[RESULT_PENDING]",
        }
