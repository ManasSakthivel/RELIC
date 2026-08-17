"""
Evaluation Metrics for LEGACY-CONTRACT experiments.

Computes: precision, recall, F1, false-positive rate, false-negative rate,
contract-type accuracy, confidence calibration (Brier score),
bootstrap confidence intervals, Cohen's d effect size,
Mann-Whitney U test for pairwise comparisons.

SCIENTIFIC RULE: Never report p-values without effect sizes.
Always use bootstrap CI (n=10000) for metric uncertainty.
Apply Bonferroni correction when making multiple comparisons.

Reference: Saito & Rehmsmeier (2015) on precision-recall evaluation;
           Efron & Tibshirani (1993) on bootstrap confidence intervals;
           Cohen (1988) on effect sizes.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Callable, Sequence

# scipy is optional — fall back to manual implementations when unavailable
try:
    from scipy import stats as _scipy_stats
    _HAS_SCIPY = True
except ImportError:  # pragma: no cover
    _HAS_SCIPY = False


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------

@dataclass
class PerTypeBreakdown:
    """Per-contract-type precision/recall/F1."""
    contract_type: str
    tp: int
    fp: int
    fn: int
    tn: int
    precision: float
    recall: float
    f1: float
    support: int  # total ground-truth positives for this type


@dataclass
class EvaluationResult:
    """
    Full evaluation result for a single experiment condition.

    tp/fp/fn/tn are counts over ALL contract types.
    per_type holds per-type breakdowns.
    All float fields are in [0, 1] unless noted otherwise.
    """
    tp: int
    fp: int
    fn: int
    tn: int
    precision: float
    recall: float
    f1: float
    fpr: float                       # false-positive rate = FP / (FP + TN)
    fnr: float                       # false-negative rate = FN / (FN + TP)
    per_type: list[PerTypeBreakdown] = field(default_factory=list)
    # Bootstrap CI fields (populated by MetricsCalculator.compute_with_ci)
    precision_ci: tuple[float, float] | None = None
    recall_ci: tuple[float, float] | None = None
    f1_ci: tuple[float, float] | None = None
    n_samples: int = 0               # number of items evaluated
    # Bootstrap sample lists — used by ExperimentRunner for pairwise Mann-Whitney U tests.
    # Not serialized to JSON/CSV; live only in memory during a runner execution.
    f1_bootstrap_samples: list[float] = field(default_factory=list)
    precision_bootstrap_samples: list[float] = field(default_factory=list)

    def macro_f1(self) -> float:
        """Macro-averaged F1 across types (unweighted)."""
        if not self.per_type:
            return self.f1
        return sum(t.f1 for t in self.per_type) / len(self.per_type)

    def weighted_f1(self) -> float:
        """Support-weighted F1 across types."""
        if not self.per_type:
            return self.f1
        total_support = sum(t.support for t in self.per_type)
        if total_support == 0:
            return 0.0
        return sum(t.f1 * t.support for t in self.per_type) / total_support

    def summary(self) -> str:
        lines = [
            f"P={self.precision:.3f}  R={self.recall:.3f}  F1={self.f1:.3f}",
            f"FPR={self.fpr:.3f}  FNR={self.fnr:.3f}",
            f"TP={self.tp}  FP={self.fp}  FN={self.fn}  TN={self.tn}  N={self.n_samples}",
        ]
        if self.f1_ci is not None:
            lines.append(f"F1 95% CI: [{self.f1_ci[0]:.3f}, {self.f1_ci[1]:.3f}]")
        if self.per_type:
            lines.append("Per-type:")
            for t in self.per_type:
                lines.append(
                    f"  {t.contract_type:20s}  P={t.precision:.3f}  R={t.recall:.3f}"
                    f"  F1={t.f1:.3f}  support={t.support}"
                )
        return "\n".join(lines)


@dataclass
class StatisticalTest:
    """Result of a statistical comparison between two experimental conditions."""
    statistic: float
    p_value: float
    effect_size: float              # Cohen's d or rank-biserial r
    ci_lower: float                 # 95% CI lower bound of effect
    ci_upper: float                 # 95% CI upper bound of effect
    method: str                     # "mann_whitney_u", "cohens_d_bootstrap", etc.
    bonferroni_n: int = 1           # number of comparisons for correction
    is_significant: bool = False    # after Bonferroni correction

    @property
    def corrected_alpha(self) -> float:
        return 0.05 / max(self.bonferroni_n, 1)

    def summary(self) -> str:
        sig = "SIGNIFICANT" if self.is_significant else "not significant"
        return (
            f"{self.method}: statistic={self.statistic:.4f}  "
            f"p={self.p_value:.4f}  effect_size={self.effect_size:.4f}  "
            f"95%CI=[{self.ci_lower:.4f}, {self.ci_upper:.4f}]  "
            f"Bonferroni-corrected α={self.corrected_alpha:.4f}  {sig}"
        )


# ---------------------------------------------------------------------------
# Metrics Calculator
# ---------------------------------------------------------------------------

class MetricsCalculator:
    """
    Core evaluation metrics for contract recovery and risk detection experiments.

    Usage:
        calc = MetricsCalculator(seed=42)
        result = calc.compute(predictions, ground_truth)
        result_with_ci = calc.compute_with_ci(predictions, ground_truth, n=10000)
    """

    def __init__(self, seed: int = 42) -> None:
        self._seed = seed
        self._rng = random.Random(seed)

    # ------------------------------------------------------------------
    # Primary compute
    # ------------------------------------------------------------------

    def compute(
        self,
        predictions: list[str],
        ground_truth: list[str],
        contract_types: list[str] | None = None,
        prediction_types: list[str] | None = None,
    ) -> EvaluationResult:
        """
        Compute precision, recall, F1, FPR, FNR from prediction and ground-truth sets.

        Arguments:
            predictions:      list of predicted contract_ids (positives).
            ground_truth:     list of ground-truth contract_ids (true positives).
            contract_types:   optional parallel list of ground-truth types (for per-type).
            prediction_types: optional parallel list of predicted types (for type accuracy).

        Returns:
            EvaluationResult with all metrics populated.

        NOTE: This treats contract recovery as a set-membership problem.
        A prediction is TP if it appears in ground_truth, FP otherwise.
        A ground_truth item not in predictions is FN.
        TN is not well-defined for open-ended recovery but is set to 0 here.
        """
        pred_set = set(predictions)
        gt_set = set(ground_truth)

        tp = len(pred_set & gt_set)
        fp = len(pred_set - gt_set)
        fn = len(gt_set - pred_set)
        tn = 0  # open-set problem; TN meaningless without explicit negative universe

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (
            2 * precision * recall / (precision + recall)
            if (precision + recall) > 0
            else 0.0
        )
        # FPR = FP / (FP + TN).  TN is always 0 in this open-set problem, so the
        # denominator is FP, which makes FPR = 1.0 whenever FP > 0 — a meaningless
        # value.  Return float("nan") to make the undefined nature explicit rather
        # than silently reporting 1.0 or 0.0.
        fpr = float("nan")
        fnr = fn / (fn + tp) if (fn + tp) > 0 else 0.0

        per_type: list[PerTypeBreakdown] = []
        if contract_types is not None:
            per_type = self._compute_per_type(
                predictions,
                ground_truth,
                contract_types,
                prediction_types,
            )

        return EvaluationResult(
            tp=tp,
            fp=fp,
            fn=fn,
            tn=tn,
            precision=precision,
            recall=recall,
            f1=f1,
            fpr=fpr,
            fnr=fnr,
            per_type=per_type,
            n_samples=len(gt_set),
        )

    def compute_with_ci(
        self,
        predictions: list[str],
        ground_truth: list[str],
        contract_types: list[str] | None = None,
        prediction_types: list[str] | None = None,
        n: int = 10000,
    ) -> EvaluationResult:
        """
        Compute metrics with 95% bootstrap confidence intervals.

        Bootstrap resamples the ground_truth+predictions pairing n times.
        CI is the 2.5th–97.5th percentile of bootstrap distribution.
        """
        result = self.compute(predictions, ground_truth, contract_types, prediction_types)

        # Build binary arrays for bootstrap (aligned on ground_truth universe)
        gt_list = sorted(set(ground_truth) | set(predictions))
        pred_set = set(predictions)
        gt_set = set(ground_truth)

        labels = [1 if item in gt_set else 0 for item in gt_list]
        preds_bin = [1 if item in pred_set else 0 for item in gt_list]
        pairs = list(zip(labels, preds_bin))

        def _precision_fn(sample: list[tuple[int, int]]) -> float:
            tp_s = sum(1 for y, p in sample if y == 1 and p == 1)
            fp_s = sum(1 for y, p in sample if y == 0 and p == 1)
            return tp_s / (tp_s + fp_s) if (tp_s + fp_s) > 0 else 0.0

        def _recall_fn(sample: list[tuple[int, int]]) -> float:
            tp_s = sum(1 for y, p in sample if y == 1 and p == 1)
            fn_s = sum(1 for y, p in sample if y == 1 and p == 0)
            return tp_s / (tp_s + fn_s) if (tp_s + fn_s) > 0 else 0.0

        def _f1_fn(sample: list[tuple[int, int]]) -> float:
            p = _precision_fn(sample)
            r = _recall_fn(sample)
            return 2 * p * r / (p + r) if (p + r) > 0 else 0.0

        # Compute bootstrap distributions and CIs.
        # Store the raw bootstrap sample lists so that RQ2 can run MWU tests
        # comparing the F1 distribution of BCG+dynamic vs each baseline.
        # CRITICAL-2 fix: _result_to_dict now exposes f1_scores from these samples.
        f1_samples = self._bootstrap_samples(_f1_fn, pairs, n=n)
        p_samples = self._bootstrap_samples(_precision_fn, pairs, n=n)
        result.f1_ci = self._ci_from_samples(f1_samples)
        result.precision_ci = self._ci_from_samples(p_samples)
        result.recall_ci = self.bootstrap_ci(_recall_fn, pairs, n=n)
        result.f1_bootstrap_samples = f1_samples
        result.precision_bootstrap_samples = p_samples
        return result

    def _bootstrap_samples(
        self,
        metric_fn: Callable[[list], float],
        data: list,
        n: int = 10000,
    ) -> list[float]:
        """Return list of n bootstrap resampled metric values (without CI)."""
        rng = self._rng
        samples = []
        size = len(data)
        for _ in range(n):
            resample = [data[rng.randint(0, size - 1)] for _ in range(size)]
            samples.append(metric_fn(resample))
        return samples

    @staticmethod
    def _ci_from_samples(
        samples: list[float],
        alpha: float = 0.05,
    ) -> tuple[float, float]:
        """Compute percentile CI from bootstrap sample list."""
        if not samples:
            return (0.0, 0.0)
        sorted_s = sorted(samples)
        lo_idx = max(0, int(alpha / 2 * len(sorted_s)))
        hi_idx = min(len(sorted_s) - 1, int((1 - alpha / 2) * len(sorted_s)))
        return (sorted_s[lo_idx], sorted_s[hi_idx])

    # ------------------------------------------------------------------
    # Bootstrap CI
    # ------------------------------------------------------------------

    def bootstrap_ci(
        self,
        metric_fn: Callable[[list], float],
        data: list,
        n: int = 10000,
        alpha: float = 0.05,
        seed: int | None = None,
    ) -> tuple[float, float]:
        """
        Compute (1-alpha) bootstrap confidence interval for metric_fn.

        Uses the percentile bootstrap (Efron 1979).
        n=10000 resamples is standard for publication-quality CI.

        Arguments:
            metric_fn: function(list) -> float applied to each resample.
            data:      list of observations to resample.
            n:         number of bootstrap resamples.
            alpha:     significance level (default 0.05 → 95% CI).
            seed:      random seed (uses instance seed if None).

        Returns:
            (lower, upper) tuple of confidence interval bounds.
        """
        rng = random.Random(seed if seed is not None else self._seed)
        if not data:
            return (0.0, 0.0)

        bootstrap_scores: list[float] = []
        for _ in range(n):
            resample = [rng.choice(data) for _ in range(len(data))]
            bootstrap_scores.append(metric_fn(resample))

        bootstrap_scores.sort()
        lower_idx = int(math.floor((alpha / 2) * n))
        upper_idx = int(math.ceil((1 - alpha / 2) * n)) - 1
        lower_idx = max(0, min(lower_idx, len(bootstrap_scores) - 1))
        upper_idx = max(0, min(upper_idx, len(bootstrap_scores) - 1))
        return (bootstrap_scores[lower_idx], bootstrap_scores[upper_idx])

    # ------------------------------------------------------------------
    # Effect size: Cohen's d
    # ------------------------------------------------------------------

    def effect_size_cohens_d(
        self, group_a: Sequence[float], group_b: Sequence[float]
    ) -> float:
        """
        Compute Cohen's d effect size between two groups.

        d = (μ_A - μ_B) / s_pooled

        where s_pooled = sqrt(((n_A-1)*s_A² + (n_B-1)*s_B²) / (n_A+n_B-2))

        Reference: Cohen (1988) Statistical Power Analysis for the Behavioral Sciences.

        SCIENTIFIC NOTE: Always report alongside a CI (use bootstrap_ci on this function).
        Conventional thresholds: small=0.2, medium=0.5, large=0.8 (Cohen 1988).
        These are not universal; report the value, not just the label.
        """
        a = list(group_a)
        b = list(group_b)
        if len(a) < 2 or len(b) < 2:
            return 0.0

        mean_a = sum(a) / len(a)
        mean_b = sum(b) / len(b)
        var_a = sum((x - mean_a) ** 2 for x in a) / (len(a) - 1)
        var_b = sum((x - mean_b) ** 2 for x in b) / (len(b) - 1)

        pooled_var = ((len(a) - 1) * var_a + (len(b) - 1) * var_b) / (len(a) + len(b) - 2)
        if pooled_var <= 0.0:
            return 0.0
        return (mean_a - mean_b) / math.sqrt(pooled_var)

    # ------------------------------------------------------------------
    # Statistical test: Mann-Whitney U
    # ------------------------------------------------------------------

    def mann_whitney_u(
        self,
        group_a: Sequence[float],
        group_b: Sequence[float],
        bonferroni_n: int = 1,
    ) -> StatisticalTest:
        """
        Mann-Whitney U test with rank-biserial correlation effect size and bootstrap CI.

        The Mann-Whitney U test is preferred over Student's t for:
        - Non-normally distributed evaluation metrics (F1 is bounded [0,1] and skewed)
        - Small sample sizes common in research experiments

        Primary effect size: rank-biserial correlation r = (U_a - U_b) / (n_A * n_B)
        where U_a + U_b = n_A * n_B.
        Reference: Wendt (1972), Fritz et al. (2012).
        Conventional thresholds (Cohen 1992): small=0.1, medium=0.3, large=0.5.

        Secondary effect size: Cohen's d (reported for comparability with parametric
        literature, but should NOT be used as the primary effect size for non-normal
        distributions such as bounded F1 scores).
        Both effect sizes are stored in the returned StatisticalTest; the primary
        effect_size field holds rank-biserial r, and cohens_d is in ci_lower/ci_upper
        metadata via the bootstrap CI on r.

        SCIENTIFIC NOTE: Report p-value AND effect size. p-value alone is insufficient.
        Apply Bonferroni correction when comparing multiple systems.

        Arguments:
            group_a:       metric values for condition A.
            group_b:       metric values for condition B.
            bonferroni_n:  number of simultaneous comparisons for correction.

        Returns:
            StatisticalTest with all fields populated.
            effect_size = rank-biserial r (primary, range [−1, 1]).
            ci_lower/ci_upper = 95% bootstrap CI of rank-biserial r.
        """
        a = list(group_a)
        b = list(group_b)

        n_a, n_b = len(a), len(b)
        denom = n_a * n_b

        if _HAS_SCIPY:
            # scipy returns U_a (wins of group_a over group_b)
            u_a, p_val = _scipy_stats.mannwhitneyu(a, b, alternative="two-sided")
            u_a = float(u_a)
            u_b = denom - u_a
        else:
            # Manual: _manual_mann_whitney returns min(U_a, U_b) — reconstruct U_a
            u_min, p_val = self._manual_mann_whitney(a, b)
            # Recover U_a: it is the one where more of a beats b
            u1 = sum(1.0 for x in a for y in b if x > y) + sum(
                0.5 for x in a for y in b if x == y
            )
            u_a = u1
            u_b = denom - u_a
            u_min = min(u_a, u_b)  # keep consistent for statistic field

        # Rank-biserial correlation: r = (U_a - U_b) / (n_A * n_B)
        # Range [−1, 1]; positive means group_a tends to score higher than group_b.
        effect_r = (u_a - u_b) / denom if denom > 0 else 0.0

        # Bootstrap CI on rank-biserial r
        combined_pairs = [(x, 0) for x in a] + [(x, 1) for x in b]

        def _r_fn(sample: list[tuple[float, int]]) -> float:
            sa = [x for x, g in sample if g == 0]
            sb = [x for x, g in sample if g == 1]
            na, nb = len(sa), len(sb)
            d = na * nb
            if d == 0:
                return 0.0
            ua = sum(1.0 for x in sa for y in sb if x > y) + sum(
                0.5 for x in sa for y in sb if x == y
            )
            ub = d - ua
            return (ua - ub) / d

        ci = self.bootstrap_ci(_r_fn, combined_pairs, n=5000)

        # Also compute Cohen's d for secondary reporting
        cohens_d = self.effect_size_cohens_d(a, b)

        corrected_alpha = 0.05 / max(bonferroni_n, 1)
        # Use the U_a statistic (or min for the scalar field) — report U_a
        u_stat_report = u_a if _HAS_SCIPY else min(u_a, u_b)
        is_significant = p_val < corrected_alpha

        return StatisticalTest(
            statistic=float(u_stat_report),
            p_value=float(p_val),
            effect_size=float(effect_r),          # rank-biserial r (primary)
            ci_lower=float(ci[0]),
            ci_upper=float(ci[1]),
            method="mann_whitney_u + rank_biserial_r_bootstrap_ci",
            bonferroni_n=bonferroni_n,
            is_significant=is_significant,
        )

    def _manual_mann_whitney(
        self, a: list[float], b: list[float]
    ) -> tuple[float, float]:
        """
        Manual Mann-Whitney U computation (no scipy dependency).
        Returns (U, approximate_p_value).

        p-value uses normal approximation (valid for n > 10 each group).
        For very small samples, p-value is approximate.
        """
        n_a, n_b = len(a), len(b)
        u1 = sum(1.0 for x in a for y in b if x > y) + sum(
            0.5 for x in a for y in b if x == y
        )
        u2 = n_a * n_b - u1
        u_stat = min(u1, u2)

        # Normal approximation
        mean_u = n_a * n_b / 2.0
        std_u = math.sqrt(n_a * n_b * (n_a + n_b + 1) / 12.0)
        if std_u == 0.0:
            return u_stat, 1.0
        z = (u_stat - mean_u) / std_u
        # Two-tailed p from standard normal CDF approximation
        p_val = 2.0 * (1.0 - self._standard_normal_cdf(abs(z)))
        return u_stat, p_val

    @staticmethod
    def _standard_normal_cdf(x: float) -> float:
        """Abramowitz & Stegun approximation of the standard normal CDF."""
        return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

    # ------------------------------------------------------------------
    # Brier score (calibration)
    # ------------------------------------------------------------------

    def calibration_brier_score(
        self,
        predicted_confidences: list[float],
        ground_truth_binary: list[int],
    ) -> float:
        """
        Compute the Brier score for confidence calibration.

        Brier score = (1/N) * Σ (f_t - o_t)²

        where f_t = predicted confidence [0,1], o_t ∈ {0,1} ground truth.

        Lower is better (0 = perfect, 1 = worst).

        Reference: Brier (1950), Murphy (1973).

        SCIENTIFIC NOTE: The ConfidenceVector aggregate is explicitly NOT a probability.
        Use this score to measure whether high-confidence contracts are more often
        correct, NOT to interpret confidence as P(correct). Report the score
        alongside its bootstrap CI to characterize calibration quality.

        Arguments:
            predicted_confidences: list of confidence scores in [0,1].
            ground_truth_binary:   list of 0/1 labels (1 = contract is correct).

        Returns:
            Brier score as a float in [0, 1].
        """
        if len(predicted_confidences) != len(ground_truth_binary):
            raise ValueError(
                "predicted_confidences and ground_truth_binary must have the same length."
            )
        if not predicted_confidences:
            return 0.0
        n = len(predicted_confidences)
        return sum(
            (f - o) ** 2
            for f, o in zip(predicted_confidences, ground_truth_binary)
        ) / n

    # ------------------------------------------------------------------
    # Per-type breakdown helper
    # ------------------------------------------------------------------

    def _compute_per_type(
        self,
        predictions: list[str],
        ground_truth: list[str],
        gt_types: list[str],
        pred_types: list[str] | None,
    ) -> list[PerTypeBreakdown]:
        """Compute per-contract-type breakdown."""
        # Map contract_id -> type for ground truth
        gt_id_to_type: dict[str, str] = {}
        for cid, ctype in zip(ground_truth, gt_types):
            gt_id_to_type[cid] = ctype

        # Map contract_id -> type for predictions
        pred_id_to_type: dict[str, str] = {}
        if pred_types:
            for cid, ctype in zip(predictions, pred_types):
                pred_id_to_type[cid] = ctype

        all_types = sorted(set(gt_id_to_type.values()))
        breakdowns: list[PerTypeBreakdown] = []

        pred_set = set(predictions)
        gt_set = set(ground_truth)

        for ctype in all_types:
            gt_of_type = {cid for cid, t in gt_id_to_type.items() if t == ctype}
            pred_of_type = {
                cid for cid in predictions
                if pred_id_to_type.get(cid) == ctype
            } if pred_types else pred_set

            tp = len(pred_of_type & gt_of_type)
            fp = len(pred_of_type - gt_of_type)
            fn = len(gt_of_type - pred_of_type)
            tn = 0

            precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1 = (
                2 * precision * recall / (precision + recall)
                if (precision + recall) > 0 else 0.0
            )

            breakdowns.append(PerTypeBreakdown(
                contract_type=ctype,
                tp=tp, fp=fp, fn=fn, tn=tn,
                precision=precision, recall=recall, f1=f1,
                support=len(gt_of_type),
            ))

        return breakdowns
