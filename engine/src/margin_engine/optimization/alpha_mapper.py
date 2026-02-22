"""Score-to-return calibration for portfolio optimization.

Maps composite scores to expected alpha (excess return) proxies
suitable for mean-variance optimization.
"""

from __future__ import annotations

import numpy as np
from scipy.stats import rankdata

from margin_engine.models.scoring import CompositeScore
from margin_engine.optimization.models import PortfolioCandidate


def calibrate_alpha(
    composites: list[CompositeScore],
    target_spread: float = 0.10,
) -> dict[str, float]:
    """Calibrate expected alpha from composite scores via z-scored ranks.

    Step 1: Rank composite_raw_score within universe -> rank percentile.
    Step 2: Z-score the rank: z = (rank - mean_rank) / std_rank.
    Step 3: Scale to annualized alpha range:
            alpha = z * target_spread / 4
            (target_spread=10% means top gets ~+2.5%, bottom ~-2.5%)

    Args:
        composites: List of CompositeScore objects.
        target_spread: Total spread of alpha range (default 10% = 0.10).

    Returns:
        Dict mapping ticker -> calibrated expected alpha.
    """
    if not composites:
        return {}

    tickers = [c.ticker for c in composites]
    scores = np.array([c.composite_raw_score for c in composites])

    if len(scores) == 1:
        return {tickers[0]: 0.0}

    # Rank scores (higher score = higher rank)
    ranks = rankdata(scores, method="average")

    # Z-score the ranks
    mean_rank = np.mean(ranks)
    std_rank = np.std(ranks, ddof=0)
    if std_rank < 1e-10:
        return {t: 0.0 for t in tickers}

    z_scores = (ranks - mean_rank) / std_rank

    # Scale to alpha range
    alphas = z_scores * target_spread / 4.0

    return {t: float(a) for t, a in zip(tickers, alphas)}


def calibrate_alpha_from_backtest(
    score_history: dict[str, list[float]],
    return_history: dict[str, list[float]],
    n_buckets: int = 10,
) -> dict[int, float]:
    """Empirical calibration: E[forward_return | score_bucket].

    Buckets scores into deciles and computes average forward return
    per bucket. Used when historical data is available.

    Args:
        score_history: ticker -> list of historical composite scores.
        return_history: ticker -> list of corresponding forward returns.
        n_buckets: Number of score buckets (default 10 = deciles).

    Returns:
        Dict mapping bucket_index (0 to n_buckets-1) -> average forward return.
    """
    all_scores: list[float] = []
    all_returns: list[float] = []
    for ticker in score_history:
        if ticker in return_history:
            scores = score_history[ticker]
            returns = return_history[ticker]
            n = min(len(scores), len(returns))
            all_scores.extend(scores[:n])
            all_returns.extend(returns[:n])

    if not all_scores:
        return {}

    scores_arr = np.array(all_scores)
    returns_arr = np.array(all_returns)

    # Create buckets using percentile edges
    bucket_edges = np.percentile(scores_arr, np.linspace(0, 100, n_buckets + 1))

    result: dict[int, float] = {}
    for i in range(n_buckets):
        low = bucket_edges[i]
        high = bucket_edges[i + 1]
        if i == n_buckets - 1:
            mask = (scores_arr >= low) & (scores_arr <= high)
        else:
            mask = (scores_arr >= low) & (scores_arr < high)

        if np.any(mask):
            result[i] = float(np.mean(returns_arr[mask]))
        else:
            result[i] = 0.0

    return result


def v4_to_candidates(
    v4_results: list[dict],
    composites: list[CompositeScore],
    calibrated_alphas: dict[str, float],
    ml_alphas: dict[str, float] | None = None,
    vae_predictions: dict[str, tuple[float, float]] | None = None,
    ml_weight: float = 0.30,
    vae_weight: float = 0.0,
) -> list[PortfolioCandidate]:
    """Convert V4 scoring results to optimizer candidates.

    Args:
        v4_results: List of V4Result-like dicts with ticker, opportunity_type,
                    conviction fields.
        composites: Corresponding CompositeScore objects.
        calibrated_alphas: From calibrate_alpha().
        ml_alphas: Optional ML-predicted alphas (Phase 5).
        vae_predictions: Optional VAE (mean, variance) per ticker (Phase 5).
        ml_weight: Weight for ML alpha in blend (default 0.30).
        vae_weight: Weight for VAE alpha in blend (default 0.0 = disabled).

    Returns:
        List of PortfolioCandidate objects ready for the optimizer.
    """
    composite_map = {c.ticker: c for c in composites}
    candidates: list[PortfolioCandidate] = []

    for v4 in v4_results:
        ticker = v4.get("ticker", "")
        if ticker not in calibrated_alphas:
            continue

        base_alpha = calibrated_alphas[ticker]

        # Blend with ML if available
        if ml_alphas and ticker in ml_alphas:
            remaining = 1.0 - ml_weight - vae_weight
            blended = remaining * base_alpha + ml_weight * ml_alphas[ticker]
        else:
            blended = base_alpha

        # Blend with VAE if available
        uncertainty = None
        if vae_predictions and ticker in vae_predictions:
            vae_mean, vae_var = vae_predictions[ticker]
            blended += vae_weight * vae_mean
            uncertainty = float(vae_var)

        composite = composite_map.get(ticker)
        sector = "unknown"
        if composite and composite.growth_stage:
            sector = str(composite.growth_stage)

        candidates.append(
            PortfolioCandidate(
                ticker=ticker,
                expected_alpha=blended,
                uncertainty=uncertainty,
                track=v4.get("opportunity_type", "unknown"),
                conviction=v4.get("conviction", "none"),
                sector=v4.get("sector", sector),
            )
        )

    return candidates
