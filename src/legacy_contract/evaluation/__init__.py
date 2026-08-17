"""
Evaluation package for LEGACY-CONTRACT experiments.

Exports:
  metrics   — precision/recall/F1/FPR/FNR, bootstrap CI, statistical tests
  benchmark — ground-truth management, IAA, annotation export
  runner    — full experiment pipeline from YAML config to results files
"""

from legacy_contract.evaluation.metrics import (
    EvaluationResult,
    PerTypeBreakdown,
    StatisticalTest,
    MetricsCalculator,
)
from legacy_contract.evaluation.benchmark import (
    Benchmark,
    BenchmarkItem,
    GroundTruthLevel,
)
from legacy_contract.evaluation.runner import (
    ExperimentConfig,
    ExperimentRunner,
    RunRecord,
)

__all__ = [
    # metrics
    "EvaluationResult",
    "PerTypeBreakdown",
    "StatisticalTest",
    "MetricsCalculator",
    # benchmark
    "Benchmark",
    "BenchmarkItem",
    "GroundTruthLevel",
    # runner
    "ExperimentConfig",
    "ExperimentRunner",
    "RunRecord",
]
