"""Percentile ranking normalizer for batches of factor scores.

Provides sector-neutral percentile ranking: scores are ranked within
their GICS sector first, so a stock's percentile reflects how it compares
to sector peers rather than the entire universe.
"""

from __future__ import annotations

from margin_engine.models.scoring import FactorScore


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
