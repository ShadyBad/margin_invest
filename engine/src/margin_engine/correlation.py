"""Portfolio correlation computation."""

from __future__ import annotations

import math
from datetime import datetime
from typing import Literal

from pydantic import BaseModel


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
