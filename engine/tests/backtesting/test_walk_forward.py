"""Tests for walk-forward out-of-sample partitioning."""

from datetime import date

from margin_engine.backtesting.walk_forward import (
    generate_walk_forward_partitions,
)


class TestWalkForwardPartitions:
    def test_generates_correct_partitions(self):
        partitions = generate_walk_forward_partitions(
            start_date=date(2006, 1, 1),
            end_date=date(2020, 12, 31),
            train_years=5,
            test_years=1,
        )
        # 2006-2010 train, 2011 test; 2007-2011 train, 2012 test; etc.
        assert len(partitions) == 10

    def test_partition_dates_correct(self):
        partitions = generate_walk_forward_partitions(
            start_date=date(2006, 1, 1),
            end_date=date(2020, 12, 31),
            train_years=5,
            test_years=1,
        )
        first = partitions[0]
        assert first.train_start == date(2006, 1, 1)
        assert first.train_end == date(2010, 12, 31)
        assert first.test_start == date(2011, 1, 1)
        assert first.test_end == date(2011, 12, 31)

    def test_no_overlap_between_train_and_test(self):
        partitions = generate_walk_forward_partitions(
            start_date=date(2006, 1, 1),
            end_date=date(2020, 12, 31),
            train_years=5,
            test_years=1,
        )
        for p in partitions:
            assert p.train_end < p.test_start

    def test_short_period_returns_fewer_partitions(self):
        partitions = generate_walk_forward_partitions(
            start_date=date(2018, 1, 1),
            end_date=date(2020, 12, 31),
            train_years=2,
            test_years=1,
        )
        assert len(partitions) == 1

    def test_insufficient_data_returns_empty(self):
        partitions = generate_walk_forward_partitions(
            start_date=date(2020, 1, 1),
            end_date=date(2020, 12, 31),
            train_years=5,
            test_years=1,
        )
        assert len(partitions) == 0
