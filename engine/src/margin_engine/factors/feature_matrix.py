"""Feature matrix construction from scoring results."""

from __future__ import annotations

import numpy as np

from margin_engine.factors.registry import FactorRegistry
from margin_engine.models.scoring import CompositeScore


def build_feature_matrix(
    composites: list[CompositeScore],
    registry: FactorRegistry,
) -> tuple[np.ndarray, list[str], list[str]]:
    """Build (N, F) feature matrix from scoring results.

    Extracts raw_value from each FactorScore found in each CompositeScore's
    FactorBreakdown pillars (quality, value, momentum, growth, capital_allocation, catalyst).

    Args:
        composites: List of CompositeScore objects.
        registry: Factor registry (used only for feature_names ordering).

    Returns:
        Tuple of (feature_matrix shaped (N, F), ticker_list, feature_name_list).
        Missing factors get NaN. Features are sorted by name.
    """
    feature_names = registry.to_feature_names()
    feature_index = {name: i for i, name in enumerate(feature_names)}
    n_features = len(feature_names)
    n_assets = len(composites)

    matrix = np.full((n_assets, n_features), np.nan)
    tickers: list[str] = []

    for row, composite in enumerate(composites):
        tickers.append(composite.ticker)

        # Iterate over all pillar breakdowns
        pillars = [composite.quality, composite.value, composite.momentum]
        for optional_pillar in [
            composite.growth,
            composite.capital_allocation,
            composite.catalyst,
        ]:
            if optional_pillar is not None:
                pillars.append(optional_pillar)

        for breakdown in pillars:
            for score in breakdown.sub_scores:
                col = feature_index.get(score.name)
                if col is not None:
                    matrix[row, col] = score.raw_value

    return matrix, tickers, feature_names
