"""Tests for failure audit computation."""

from datetime import date

from margin_engine.backtesting.failure_audit import (
    compute_failure_audit,
)
from margin_engine.backtesting.models import HoldingRecord, MonthlySnapshot
from margin_engine.backtesting.regime_classifier import MarketRegimeHistorical


class TestFailureAudit:
    def _make_snapshots(self) -> list[MonthlySnapshot]:
        """Build 12 months of snapshots with varying performance."""
        snapshots = []
        portfolio_value = 1_000_000.0
        benchmark_value = 1_000_000.0

        returns_data = [
            (0.02, 0.01),  # Jan: good
            (-0.15, -0.10),  # Feb: bad — underperformed by 5%
            (-0.08, -0.02),  # Mar: bad — underperformed by 6%
            (0.05, 0.03),  # Apr: good
            (0.01, 0.04),  # May: bad — underperformed by 3%
            (0.03, 0.02),  # Jun: good
            (-0.10, -0.01),  # Jul: very bad — underperformed by 9%
            (0.04, 0.03),  # Aug: good
            (0.02, 0.05),  # Sep: bad — underperformed by 3%
            (-0.05, 0.02),  # Oct: worst — underperformed by 7%
            (0.06, 0.04),  # Nov: good
            (0.03, 0.01),  # Dec: good
        ]

        for i, (pr, br) in enumerate(returns_data):
            month = i + 1
            portfolio_value *= 1 + pr
            benchmark_value *= 1 + br
            snapshots.append(
                MonthlySnapshot(
                    date=date(2020, month, 1),
                    holdings=[
                        HoldingRecord(
                            ticker="AAPL",
                            weight=0.5,
                            entry_price=150.0,
                            composite_score=85.0,
                        ),
                        HoldingRecord(
                            ticker="MSFT",
                            weight=0.5,
                            entry_price=300.0,
                            composite_score=80.0,
                        ),
                    ],
                    portfolio_value=portfolio_value,
                    benchmark_value=benchmark_value,
                    portfolio_return=pr,
                    benchmark_return=br,
                    turnover=0.1,
                    transaction_costs=100.0,
                )
            )

        return snapshots

    def test_returns_worst_periods(self):
        snapshots = self._make_snapshots()
        regimes = [MarketRegimeHistorical.BULL] * 12
        audit = compute_failure_audit(snapshots, regimes, n_worst=5)
        assert len(audit) == 5

    def test_worst_period_is_most_underperforming(self):
        snapshots = self._make_snapshots()
        regimes = [MarketRegimeHistorical.BULL] * 12
        audit = compute_failure_audit(snapshots, regimes, n_worst=3)
        # July was worst (-10% vs -1% = -9% relative)
        assert audit[0].rebalance_date == date(2020, 7, 1)

    def test_includes_holdings(self):
        snapshots = self._make_snapshots()
        regimes = [MarketRegimeHistorical.BULL] * 12
        audit = compute_failure_audit(snapshots, regimes, n_worst=1)
        assert len(audit[0].holdings) == 2

    def test_empty_snapshots(self):
        audit = compute_failure_audit([], [], n_worst=10)
        assert len(audit) == 0
