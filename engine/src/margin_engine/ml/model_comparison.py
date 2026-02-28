"""Model comparison using the Wilcoxon signed-rank test.

Compares paired metric samples (e.g., rank IC from multiple seeds) between
a current and previous model to determine if there is a statistically
significant difference in performance.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from statistics import stdev

from scipy.stats import wilcoxon

logger = logging.getLogger(__name__)

MIN_SAMPLES_FOR_TEST = 3


@dataclass(frozen=True)
class ModelComparisonResult:
    """Result of a paired model comparison."""

    p_value: float
    effect_size: float
    significant: bool
    label: str
    n_compared: int
    mean_difference: float

    def to_dict(self) -> dict:
        """Serialize to a plain dictionary."""
        return asdict(self)


def compare_model_groups(
    current_metrics: list[float],
    previous_metrics: list[float],
    alpha: float = 0.05,
) -> ModelComparisonResult:
    """Compare paired metric samples using the Wilcoxon signed-rank test.

    Args:
        current_metrics: Metric values (e.g., rank IC) for the current model
            across multiple seeds.
        previous_metrics: Metric values for the previous model across the
            same seeds.
        alpha: Significance threshold (default 0.05).

    Returns:
        A :class:`ModelComparisonResult` summarising the comparison.
    """
    n_current = len(current_metrics)
    n_previous = len(previous_metrics)

    # Truncate to equal length if needed.
    n = min(n_current, n_previous)
    if n_current != n_previous:
        logger.warning(
            "Sample sizes differ (current=%d, previous=%d); "
            "comparing first %d paired observations.",
            n_current,
            n_previous,
            n,
        )

    # Gate: not enough samples to run the test.
    if n < MIN_SAMPLES_FOR_TEST:
        return ModelComparisonResult(
            p_value=1.0,
            effect_size=0.0,
            significant=False,
            label="insufficient_data",
            n_compared=n,
            mean_difference=0.0,
        )

    current = current_metrics[:n]
    previous = previous_metrics[:n]
    differences = [c - p for c, p in zip(current, previous)]
    mean_diff = sum(differences) / n

    # If all differences are exactly zero, there is nothing to test.
    if all(d == 0.0 for d in differences):
        return ModelComparisonResult(
            p_value=1.0,
            effect_size=0.0,
            significant=False,
            label="no_significant_difference",
            n_compared=n,
            mean_difference=0.0,
        )

    # Run the Wilcoxon signed-rank test.
    try:
        stat_result = wilcoxon(current, previous)
        p_value = float(stat_result.pvalue)
    except ValueError:
        # wilcoxon can raise ValueError when inputs are degenerate.
        logger.warning("Wilcoxon test raised ValueError; treating as non-significant.")
        return ModelComparisonResult(
            p_value=1.0,
            effect_size=0.0,
            significant=False,
            label="no_significant_difference",
            n_compared=n,
            mean_difference=mean_diff,
        )

    # Effect size: Cohen's d-like measure = mean(diff) / std(diff).
    diff_std = stdev(differences) if n > 1 else 0.0
    effect_size = mean_diff / diff_std if diff_std > 0 else 0.0

    significant = p_value < alpha

    if significant and mean_diff > 0:
        label = "significantly_better"
    elif significant and mean_diff < 0:
        label = "significantly_worse"
    else:
        label = "no_significant_difference"

    return ModelComparisonResult(
        p_value=p_value,
        effect_size=effect_size,
        significant=significant,
        label=label,
        n_compared=n,
        mean_difference=mean_diff,
    )
