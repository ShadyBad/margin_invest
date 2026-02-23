"""Portfolio correlation computation."""

from __future__ import annotations

import math
from datetime import UTC, datetime
from typing import Literal

import numpy as np
from pydantic import BaseModel

from margin_engine.models.financial import PriceBar
from margin_engine.models.scoring import FactorBreakdown
from margin_engine.risk.covariance import compute_covariance
from margin_engine.risk.returns import returns_from_price_bars


class ExcludedTicker(BaseModel):
    """A ticker excluded from the correlation matrix with reason."""

    ticker: str
    reason: str


class CorrelationMatrix(BaseModel):
    """NxN correlation matrix for a set of tickers."""

    tickers: list[str]
    method: Literal["returns", "factors"]
    matrix: list[list[float | None]]
    sample_sizes: list[list[int]]
    excluded: list[ExcludedTicker]
    window_days: int
    computed_at: datetime


def _pearson(xs: list[float], ys: list[float]) -> float | None:
    """Compute Pearson correlation coefficient. Returns None if undefined."""
    n = len(xs)
    if n < 2 or n != len(ys):
        return None
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    cov = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    var_x = sum((x - mean_x) ** 2 for x in xs)
    var_y = sum((y - mean_y) ** 2 for y in ys)
    denom = math.sqrt(var_x * var_y)
    if denom == 0.0:
        return None
    return cov / denom


def _log_returns(bars: list[PriceBar]) -> dict[str, float]:
    """Compute daily log returns keyed by date string."""
    returns: dict[str, float] = {}
    for i in range(1, len(bars)):
        prev_close = float(bars[i - 1].adj_close or bars[i - 1].close)
        curr_close = float(bars[i].adj_close or bars[i].close)
        if prev_close > 0 and curr_close > 0:
            returns[bars[i].date] = math.log(curr_close / prev_close)
    return returns


def compute_return_correlations(
    price_data: dict[str, list[PriceBar]],
    window_days: int = 252,
    min_overlap: int = 30,
    min_bars: int = 10,
) -> CorrelationMatrix:
    """Compute Pearson correlations on daily log returns."""
    excluded: list[ExcludedTicker] = []
    valid_tickers: list[str] = []
    returns_by_ticker: dict[str, dict[str, float]] = {}

    for ticker in sorted(price_data.keys()):
        bars = price_data[ticker][-window_days:]
        if len(bars) < min_bars:
            excluded.append(
                ExcludedTicker(ticker=ticker, reason=f"only {len(bars)} bars (need {min_bars})")
            )
            continue
        returns_by_ticker[ticker] = _log_returns(bars)
        valid_tickers.append(ticker)

    n = len(valid_tickers)
    if n < 2:
        return CorrelationMatrix(
            tickers=valid_tickers,
            method="returns",
            matrix=[[1.0]] if n == 1 else [],
            sample_sizes=[[len(returns_by_ticker.get(valid_tickers[0], {}))]] if n == 1 else [],
            excluded=excluded,
            window_days=window_days,
            computed_at=datetime.now(UTC),
        )

    matrix: list[list[float | None]] = [[None] * n for _ in range(n)]
    sample_sizes: list[list[int]] = [[0] * n for _ in range(n)]

    for i in range(n):
        matrix[i][i] = 1.0
        ret_i = returns_by_ticker[valid_tickers[i]]
        sample_sizes[i][i] = len(ret_i)
        for j in range(i + 1, n):
            ret_j = returns_by_ticker[valid_tickers[j]]
            common_dates = sorted(set(ret_i.keys()) & set(ret_j.keys()))
            overlap = len(common_dates)
            sample_sizes[i][j] = overlap
            sample_sizes[j][i] = overlap
            if overlap < min_overlap:
                matrix[i][j] = None
                matrix[j][i] = None
            else:
                xs = [ret_i[d] for d in common_dates]
                ys = [ret_j[d] for d in common_dates]
                r = _pearson(xs, ys)
                matrix[i][j] = r
                matrix[j][i] = r

    return CorrelationMatrix(
        tickers=valid_tickers,
        method="returns",
        matrix=matrix,
        sample_sizes=sample_sizes,
        excluded=excluded,
        window_days=window_days,
        computed_at=datetime.now(UTC),
    )


def compute_shrunk_return_correlations(
    price_data: dict[str, list[PriceBar]],
    window_days: int = 252,
    min_bars: int = 10,
    method: str = "auto",
) -> CorrelationMatrix:
    """Compute correlations using shrunk covariance estimation.

    Uses the risk.covariance module for better-conditioned covariance
    estimates, then converts to correlation form: D^{-1/2} @ Sigma @ D^{-1/2}.

    Falls back to compute_return_correlations() if fewer than 2 tickers
    have sufficient data.
    """
    # Identify tickers with sufficient bars
    excluded: list[ExcludedTicker] = []
    valid_price_data: dict[str, list[PriceBar]] = {}

    for ticker in sorted(price_data.keys()):
        bars = price_data[ticker][-window_days:]
        if len(bars) < min_bars:
            excluded.append(
                ExcludedTicker(ticker=ticker, reason=f"only {len(bars)} bars (need {min_bars})")
            )
        else:
            valid_price_data[ticker] = price_data[ticker]

    if len(valid_price_data) < 2:
        # Fall back to the simple correlation for 0 or 1 tickers
        return compute_return_correlations(price_data, window_days, min_bars=min_bars)

    # Build return matrix via risk.returns
    returns_matrix, tickers = returns_from_price_bars(valid_price_data, window_days)

    if len(tickers) < 2:
        return compute_return_correlations(price_data, window_days, min_bars=min_bars)

    # Compute shrunk covariance
    cov_result = compute_covariance(returns_matrix, tickers, method=method)

    # Convert covariance to correlation: corr = D^{-1/2} @ Sigma @ D^{-1/2}
    sigma = cov_result.matrix
    d = np.sqrt(np.diag(sigma))
    # Guard against zero variance
    d[d == 0] = 1.0
    d_inv = 1.0 / d
    corr = sigma * np.outer(d_inv, d_inv)

    # Ensure diagonal is exactly 1.0 and clip to [-1, 1]
    np.fill_diagonal(corr, 1.0)
    corr = np.clip(corr, -1.0, 1.0)

    # Build sample_sizes (uniform since return matrix is aligned)
    n_obs = returns_matrix.shape[0]
    n_tickers = len(tickers)
    sample_sizes = [[n_obs] * n_tickers for _ in range(n_tickers)]

    # Convert to list-of-lists
    matrix = corr.tolist()

    return CorrelationMatrix(
        tickers=list(tickers),
        method="returns",
        matrix=matrix,
        sample_sizes=sample_sizes,
        excluded=excluded,
        window_days=window_days,
        computed_at=datetime.now(UTC),
    )


def _factor_vector(factors: dict[str, FactorBreakdown]) -> list[float]:
    """Flatten factor breakdowns into a single percentile vector."""
    vector: list[float] = []
    for key in sorted(factors.keys()):
        for sub in factors[key].sub_scores:
            vector.append(sub.percentile_rank)
    return vector


def compute_factor_correlations(
    profiles: dict[str, dict[str, FactorBreakdown]],
) -> CorrelationMatrix:
    """Compute Pearson correlations on factor score vectors."""
    tickers = sorted(profiles.keys())
    vectors = {t: _factor_vector(profiles[t]) for t in tickers}
    n = len(tickers)

    if n < 2:
        return CorrelationMatrix(
            tickers=tickers,
            method="factors",
            matrix=[[1.0]] if n == 1 else [],
            sample_sizes=[[len(vectors[tickers[0]])]] if n == 1 else [],
            excluded=[],
            window_days=0,
            computed_at=datetime.now(UTC),
        )

    matrix: list[list[float | None]] = [[None] * n for _ in range(n)]
    sample_sizes: list[list[int]] = [[0] * n for _ in range(n)]

    for i in range(n):
        vec_i = vectors[tickers[i]]
        matrix[i][i] = 1.0
        sample_sizes[i][i] = len(vec_i)
        for j in range(i + 1, n):
            vec_j = vectors[tickers[j]]
            size = min(len(vec_i), len(vec_j))
            sample_sizes[i][j] = size
            sample_sizes[j][i] = size
            r = _pearson(vec_i[:size], vec_j[:size])
            matrix[i][j] = r
            matrix[j][i] = r

    return CorrelationMatrix(
        tickers=tickers,
        method="factors",
        matrix=matrix,
        sample_sizes=sample_sizes,
        excluded=[],
        window_days=0,
        computed_at=datetime.now(UTC),
    )
