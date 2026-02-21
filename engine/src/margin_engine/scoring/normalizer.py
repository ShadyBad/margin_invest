"""Percentile ranking normalizer for batches of factor scores.

Provides sector-neutral percentile ranking: scores are ranked within
their GICS sector first, so a stock's percentile reflects how it compares
to sector peers rather than the entire universe.
"""

from __future__ import annotations

import statistics

from margin_engine.models.scoring import CompositeScore, FactorScore, InvestmentStyle


def compute_percentile_ranks(
    scores: list[FactorScore],
    invert: bool = False,
) -> list[FactorScore]:
    """Assign percentile ranks to a batch of FactorScores.

    Takes scores for a single factor across multiple stocks.
    Returns new FactorScore objects with percentile_rank filled in.

    If invert=True, lower raw_value gets higher percentile
    (for factors where lower = better like EV/FCF).

    Algorithm:
        1. Sort scores by raw_value (ascending for normal, descending for inverted)
        2. Assign percentile = (rank / total) * 100 where rank is 1-based position
        3. Handle ties: average the percentile ranks for tied values
        4. If only 1 score: assign percentile 50.0
    """
    if not scores:
        return []

    n = len(scores)

    if n == 1:
        s = scores[0]
        return [
            FactorScore(
                name=s.name,
                raw_value=s.raw_value,
                percentile_rank=50.0,
                detail=s.detail,
            )
        ]

    # If all values are identical, no meaningful ranking is possible
    if all(s.raw_value == scores[0].raw_value for s in scores):
        return [
            FactorScore(
                name=s.name,
                raw_value=s.raw_value,
                percentile_rank=50.0,
                detail=s.detail,
            )
            for s in scores
        ]

    # Build (index, raw_value) pairs and sort
    indexed = list(enumerate(scores))
    indexed.sort(key=lambda pair: pair[1].raw_value, reverse=invert)

    # Assign 1-based ranks, then handle ties by averaging
    # ranks[i] will hold the final rank for sorted position i
    ranks = list(range(1, n + 1))

    # Group tied values and average their ranks
    i = 0
    while i < n:
        j = i
        # Find the end of the tie group
        while j < n and indexed[j][1].raw_value == indexed[i][1].raw_value:
            j += 1
        # Average rank for this tie group
        avg_rank = sum(ranks[k] for k in range(i, j)) / (j - i)
        for k in range(i, j):
            ranks[k] = avg_rank
        i = j

    # Convert ranks to percentiles: (rank / total) * 100
    # Map back to original indices
    result_map: dict[int, float] = {}
    for sorted_pos, (orig_idx, _score) in enumerate(indexed):
        result_map[orig_idx] = (ranks[sorted_pos] / n) * 100.0

    # Build output in original order
    return [
        FactorScore(
            name=scores[idx].name,
            raw_value=scores[idx].raw_value,
            percentile_rank=result_map[idx],
            detail=scores[idx].detail,
        )
        for idx in range(n)
    ]


def rerank_composites(
    composites: list[CompositeScore],
) -> list[CompositeScore]:
    """Re-rank composite scores across the full universe.

    Takes the weighted-average composite_raw_score values and converts them
    to proper percentile ranks (0-100) across all tickers. This ensures
    the top 1% actually get >= 99, top 5% get >= 95, etc.

    Uses the same ranking algorithm as compute_percentile_ranks():
    - Empty list: returns []
    - Single ticker: percentile = 50.0
    - All identical: percentile = 50.0
    - Otherwise: (rank / n) * 100 with averaged ties

    Returns new CompositeScore objects; originals are not mutated.
    """
    if not composites:
        return []

    n = len(composites)

    if n == 1:
        return [composites[0].model_copy(update={"composite_percentile": 50.0})]

    raw_scores = [c.composite_raw_score for c in composites]

    # All identical → 50.0
    if all(s == raw_scores[0] for s in raw_scores):
        return [c.model_copy(update={"composite_percentile": 50.0}) for c in composites]

    # Sort by raw_score ascending
    indexed = sorted(enumerate(raw_scores), key=lambda pair: pair[1])

    # Assign 1-based ranks with tie averaging
    ranks = list(range(1, n + 1))
    i = 0
    while i < n:
        j = i
        while j < n and indexed[j][1] == indexed[i][1]:
            j += 1
        avg_rank = sum(ranks[k] for k in range(i, j)) / (j - i)
        for k in range(i, j):
            ranks[k] = avg_rank
        i = j

    # Map back to original indices
    result_map: dict[int, float] = {}
    for sorted_pos, (orig_idx, _raw) in enumerate(indexed):
        result_map[orig_idx] = (ranks[sorted_pos] / n) * 100.0

    return [
        composites[idx].model_copy(update={"composite_percentile": result_map[idx]})
        for idx in range(n)
    ]


def sector_neutral_ranks(
    scores_by_sector: dict[str, list[FactorScore]],
    invert: bool = False,
) -> list[FactorScore]:
    """Compute sector-neutral percentile ranks.

    Ranks within each sector first, then returns all scores
    with sector-relative percentile ranks.
    """
    result: list[FactorScore] = []
    for _sector, sector_scores in scores_by_sector.items():
        ranked = compute_percentile_ranks(sector_scores, invert=invert)
        result.extend(ranked)
    return result


def style_sector_neutral_ranks(
    scores_by_bucket: dict[tuple[str, InvestmentStyle], list[FactorScore]],
    invert: bool = False,
    min_bucket_size: int = 5,
) -> list[FactorScore]:
    """Compute percentile ranks within (sector, style) buckets.

    Stage 1 of two-stage style-aware normalization.
    Uses existing compute_percentile_ranks() for each bucket.
    Returns all scores concatenated in bucket insertion order.

    Buckets smaller than min_bucket_size are still ranked (they just
    may have less statistical power). The min_bucket_size parameter
    is advisory and does not filter out small buckets.
    """
    if not scores_by_bucket:
        return []

    result: list[FactorScore] = []
    for _bucket_key, bucket_scores in scores_by_bucket.items():
        ranked = compute_percentile_ranks(bucket_scores, invert=invert)
        result.extend(ranked)
    return result


def calibrate_cross_bucket(
    scores: list[FactorScore],
) -> list[FactorScore]:
    """Z-score calibration across all buckets.

    z = (percentile - mean) / std, then map back to 0-100.
    Single score -> 50.0. All identical -> 50.0. Zero std -> 50.0.
    Maps z-score to 0-100 using: 50 + z * 16.67 (clamped to [0, 100]).
    """
    if not scores:
        return []

    if len(scores) == 1:
        s = scores[0]
        return [
            FactorScore(
                name=s.name,
                raw_value=s.raw_value,
                percentile_rank=50.0,
                detail=s.detail,
                weight=s.weight,
            )
        ]

    percentiles = [s.percentile_rank for s in scores]

    # Check for zero variance (all identical percentiles)
    if all(p == percentiles[0] for p in percentiles):
        return [
            FactorScore(
                name=s.name,
                raw_value=s.raw_value,
                percentile_rank=50.0,
                detail=s.detail,
                weight=s.weight,
            )
            for s in scores
        ]

    mean = statistics.mean(percentiles)
    std = statistics.stdev(percentiles)

    if std == 0.0:
        return [
            FactorScore(
                name=s.name,
                raw_value=s.raw_value,
                percentile_rank=50.0,
                detail=s.detail,
                weight=s.weight,
            )
            for s in scores
        ]

    result: list[FactorScore] = []
    for s in scores:
        z = (s.percentile_rank - mean) / std
        calibrated = 50.0 + z * 16.67
        calibrated = max(0.0, min(100.0, calibrated))
        result.append(
            FactorScore(
                name=s.name,
                raw_value=s.raw_value,
                percentile_rank=calibrated,
                detail=s.detail,
                weight=s.weight,
            )
        )
    return result
