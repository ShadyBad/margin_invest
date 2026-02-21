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
