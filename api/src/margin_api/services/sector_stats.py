"""Sector statistics computation for V4 scoring pipeline.

Includes filter pass rates and sub-factor distributions (P10/P50/P90)
per sector. These are injected into the V4Score detail JSONB so the
frontend can render sector context sparklines.
"""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from margin_api.services.scoring import RawScoringResult


def compute_sector_filter_pass_rates(
    filter_data: list[tuple[str, list[dict]]],
) -> dict[str, dict[str, float]]:
    """Compute pass rate for each (sector, filter_name) pair.

    Args:
        filter_data: List of (sector, filters_passed_list) tuples.
            Each filters_passed_list is a list of dicts with 'name' and 'passed' keys.

    Returns:
        Nested dict: sector -> filter_name -> pass_rate (0.0-1.0)
    """
    counts: dict[tuple[str, str], list[bool]] = defaultdict(list)

    for sector, filters in filter_data:
        for f in filters:
            key = (sector, f["name"])
            counts[key].append(bool(f.get("passed", False)))

    result: dict[str, dict[str, float]] = {}
    for (sector, filter_name), passed_list in counts.items():
        if sector not in result:
            result[sector] = {}
        result[sector][filter_name] = sum(passed_list) / len(passed_list)

    return result


def compute_sector_distribution(
    raw_values: list[float],
) -> dict[str, float] | None:
    """Compute P10, P50, P90 and count for a list of raw values.

    Args:
        raw_values: Raw sub-factor values for stocks in a sector.

    Returns:
        Dict with p10, p50, p90, count. None if empty.
    """
    if not raw_values:
        return None

    sorted_vals = sorted(raw_values)
    n = len(sorted_vals)

    if n == 1:
        v = sorted_vals[0]
        return {"p10": v, "p50": v, "p90": v, "count": 1}

    def _percentile(data: list[float], pct: float) -> float:
        k = (len(data) - 1) * (pct / 100.0)
        f = int(k)
        c = f + 1
        if c >= len(data):
            return data[f]
        return data[f] + (k - f) * (data[c] - data[f])

    return {
        "p10": round(_percentile(sorted_vals, 10), 4),
        "p50": round(_percentile(sorted_vals, 50), 4),
        "p90": round(_percentile(sorted_vals, 90), 4),
        "count": n,
    }


def compute_all_sector_distributions(
    raw_results: list[RawScoringResult],
) -> dict[str, dict[str, dict]]:
    """Compute P10/P50/P90 per (sector, sub-factor) from raw scoring results.

    Args:
        raw_results: List of RawScoringResult from the scoring pipeline.

    Returns:
        Dict mapping sector -> factor_name -> {p10, p50, p90, count}
    """
    sector_values: dict[tuple[str, str], list[float]] = defaultdict(list)

    for result in raw_results:
        for list_attr in ("quality_scores", "value_scores", "momentum_scores"):
            for score in getattr(result, list_attr):
                key = (result.sector, score.name)
                sector_values[key].append(score.raw_value)

    distributions: dict[str, dict[str, dict]] = defaultdict(dict)
    for (sector, factor_name), values in sector_values.items():
        dist = compute_sector_distribution(values)
        if dist is not None:
            distributions[sector][factor_name] = dist

    return dict(distributions)
