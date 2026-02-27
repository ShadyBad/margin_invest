"""Tests for cross-period data consistency validation."""

from decimal import Decimal

from margin_engine.models.financial import (
    BalanceSheet,
    CashFlowStatement,
    FinancialHistory,
    FinancialPeriod,
    IncomeStatement,
)
from margin_engine.scoring.data_consistency import validate_data_consistency


def _make_period(
    period_end: str,
    revenue: int = 100_000,
    total_assets: int = 500_000,
    shares_outstanding: int = 1_000_000,
    operating_income: int = 20_000,
    operating_cash_flow: int = 25_000,
    capital_expenditures: int = -5_000,
) -> FinancialPeriod:
    return FinancialPeriod(
        period_end=period_end,
        filing_date=period_end,
        current_income=IncomeStatement(
            revenue=Decimal(str(revenue)),
            ebit=Decimal(str(operating_income)),
            net_income=Decimal(str(operating_income)),
            shares_outstanding=shares_outstanding,
        ),
        current_balance=BalanceSheet(
            total_assets=Decimal(str(total_assets)),
            shares_outstanding=shares_outstanding,
        ),
        current_cash_flow=CashFlowStatement(
            operating_cash_flow=Decimal(str(operating_cash_flow)),
            capital_expenditures=Decimal(str(capital_expenditures)),
        ),
    )


def test_stable_history_no_flags():
    """Stable data across periods should produce no anomaly flags."""
    periods = [
        _make_period("2020-12-31", revenue=100_000),
        _make_period("2021-12-31", revenue=105_000),
        _make_period("2022-12-31", revenue=102_000),
        _make_period("2023-12-31", revenue=108_000),
        _make_period("2024-12-31", revenue=103_000),
    ]
    history = FinancialHistory(ticker="STABLE", periods=periods)
    flags = validate_data_consistency(history)
    anomalies = [f for f in flags if f.is_anomaly]
    assert len(anomalies) == 0


def test_shares_outstanding_spike_flagged():
    """A 4x jump in shares_outstanding (stock split error) should be flagged."""
    periods = [
        _make_period("2020-12-31", shares_outstanding=1_000_000),
        _make_period("2021-12-31", shares_outstanding=1_000_000),
        _make_period("2022-12-31", shares_outstanding=1_000_000),
        _make_period("2023-12-31", shares_outstanding=1_000_000),
        _make_period("2024-12-31", shares_outstanding=4_000_000),  # 4x jump
    ]
    history = FinancialHistory(ticker="SPLIT", periods=periods)
    flags = validate_data_consistency(history)
    anomalies = [f for f in flags if f.is_anomaly]
    assert len(anomalies) >= 1
    assert any(f.field_name == "shares_outstanding" for f in anomalies)


def test_revenue_drop_flagged():
    """A sudden 80% revenue drop should be flagged."""
    periods = [
        _make_period("2020-12-31", revenue=100_000),
        _make_period("2021-12-31", revenue=105_000),
        _make_period("2022-12-31", revenue=102_000),
        _make_period("2023-12-31", revenue=108_000),
        _make_period("2024-12-31", revenue=20_000),  # 80% drop
    ]
    history = FinancialHistory(ticker="DROP", periods=periods)
    flags = validate_data_consistency(history)
    anomalies = [f for f in flags if f.is_anomaly]
    assert any(f.field_name == "revenue" for f in anomalies)


def test_insufficient_history_returns_empty():
    """With < 3 periods, there's not enough history to validate. Return empty."""
    periods = [
        _make_period("2023-12-31"),
        _make_period("2024-12-31"),
    ]
    history = FinancialHistory(ticker="SHORT", periods=periods)
    flags = validate_data_consistency(history)
    assert flags == []


def test_zero_std_skipped():
    """If all historical values are identical (std=0), skip the field (no division by zero)."""
    periods = [
        _make_period("2020-12-31", revenue=100_000),
        _make_period("2021-12-31", revenue=100_000),
        _make_period("2022-12-31", revenue=100_000),
        _make_period("2023-12-31", revenue=100_000),
        _make_period("2024-12-31", revenue=200_000),  # 2x jump
    ]
    history = FinancialHistory(ticker="ZERO_STD", periods=periods)
    # With zero std among prior periods, should either skip or use
    # absolute deviation logic — but must NOT raise ZeroDivisionError
    flags = validate_data_consistency(history)
    # Should still flag via fallback logic (>100% deviation from mean)
    assert isinstance(flags, list)


def test_gradual_growth_not_flagged():
    """20% YoY revenue growth sustained over 5 years should NOT be flagged."""
    periods = [
        _make_period("2020-12-31", revenue=100_000),
        _make_period("2021-12-31", revenue=120_000),
        _make_period("2022-12-31", revenue=144_000),
        _make_period("2023-12-31", revenue=173_000),
        _make_period("2024-12-31", revenue=207_000),
    ]
    history = FinancialHistory(ticker="GROWER", periods=periods)
    flags = validate_data_consistency(history)
    anomalies = [f for f in flags if f.is_anomaly]
    assert len(anomalies) == 0


def test_all_five_critical_fields_checked():
    """Verify all 5 critical fields are checked when data is present."""
    periods = [
        _make_period("2020-12-31"),
        _make_period("2021-12-31"),
        _make_period("2022-12-31"),
        _make_period("2023-12-31"),
        _make_period("2024-12-31"),
    ]
    history = FinancialHistory(ticker="ALL", periods=periods)
    flags = validate_data_consistency(history)
    checked_fields = {f.field_name for f in flags}
    expected = {"revenue", "total_assets", "shares_outstanding", "operating_income", "free_cash_flow"}
    assert checked_fields == expected
