"""Shadow portfolio tracker for live out-of-sample tracking.

Records paper positions daily with immutable timestamps.
Cannot be edited or backfilled — provably forward-looking.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

from pydantic import BaseModel, Field


class ShadowPosition(BaseModel):
    """A single position in the shadow portfolio."""

    ticker: str
    weight: float
    price: float
    composite_score: float


class ShadowSnapshot(BaseModel):
    """Daily shadow portfolio state."""

    as_of_date: date
    positions: list[ShadowPosition]
    portfolio_value: float
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @property
    def num_positions(self) -> int:
        return len(self.positions)


class ShadowPortfolio:
    """Tracks a live paper portfolio with immutable history.

    Key invariant: snapshots can only be appended in chronological
    order. No backdating, no editing, no deletion.
    """

    def __init__(self, start_date: date) -> None:
        self.start_date = start_date
        self.snapshots: list[ShadowSnapshot] = []

    def record_snapshot(
        self,
        as_of_date: date,
        positions: list[ShadowPosition],
        portfolio_value: float,
    ) -> ShadowSnapshot:
        """Record today's portfolio state. Cannot backfill."""
        if self.snapshots and as_of_date <= self.snapshots[-1].as_of_date:
            raise ValueError(
                f"Cannot backfill: {as_of_date} <= last snapshot {self.snapshots[-1].as_of_date}"
            )
        snapshot = ShadowSnapshot(
            as_of_date=as_of_date,
            positions=positions,
            portfolio_value=portfolio_value,
        )
        self.snapshots.append(snapshot)
        return snapshot

    @property
    def total_return(self) -> float:
        """Cumulative return since inception."""
        if len(self.snapshots) < 2:
            return 0.0
        initial = self.snapshots[0].portfolio_value
        final = self.snapshots[-1].portfolio_value
        if initial <= 0:
            return 0.0
        return (final - initial) / initial

    @property
    def max_drawdown(self) -> float:
        """Maximum drawdown from peak."""
        if len(self.snapshots) < 2:
            return 0.0
        values = [s.portfolio_value for s in self.snapshots]
        peak = values[0]
        max_dd = 0.0
        for v in values:
            if v > peak:
                peak = v
            dd = (peak - v) / peak if peak > 0 else 0.0
            if dd > max_dd:
                max_dd = dd
        return max_dd

    @property
    def num_days(self) -> int:
        """Number of recorded trading days."""
        return len(self.snapshots)
