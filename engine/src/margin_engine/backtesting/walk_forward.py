"""Walk-forward out-of-sample partitioning.

Generates rolling train/test windows for walk-forward analysis.
All reported metrics come from the test (out-of-sample) periods only.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class WalkForwardPartition(BaseModel):
    """A single train/test window in walk-forward analysis."""

    train_start: date
    train_end: date
    test_start: date
    test_end: date
    partition_index: int

    @property
    def train_years(self) -> float:
        return (self.train_end - self.train_start).days / 365.25

    @property
    def test_years(self) -> float:
        return (self.test_end - self.test_start).days / 365.25


def generate_walk_forward_partitions(
    start_date: date,
    end_date: date,
    train_years: int = 5,
    test_years: int = 1,
) -> list[WalkForwardPartition]:
    """Generate rolling walk-forward train/test windows.

    Rolls forward by test_years each iteration:
    - Window 1: train [start, start+train), test [start+train, start+train+test)
    - Window 2: train [start+1, start+1+train), test [start+1+train, start+1+train+test)
    - ...until test_end exceeds end_date.
    """
    partitions: list[WalkForwardPartition] = []
    idx = 0
    current_train_start = start_date

    while True:
        train_end_year = current_train_start.year + train_years
        train_end = date(train_end_year - 1, 12, 31)

        test_start = date(train_end_year, 1, 1)
        test_end_year = train_end_year + test_years
        test_end = date(test_end_year - 1, 12, 31)

        if test_end > end_date:
            break

        partitions.append(WalkForwardPartition(
            train_start=current_train_start,
            train_end=train_end,
            test_start=test_start,
            test_end=test_end,
            partition_index=idx,
        ))

        idx += 1
        current_train_start = date(current_train_start.year + test_years, 1, 1)

    return partitions
