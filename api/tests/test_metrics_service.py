"""Tests for institutional metrics calculation service."""

from __future__ import annotations

import math
import pytest
from margin_api.services.metrics import (
    compute_sharpe_ratio,
    compute_max_drawdown,
    compute_volatility,
    compute_avg_profit_margin,
    classify_risk,
)


class TestSharpeRatio:
    def test_known_series(self):
        closes = [100.0, 101.0, 100.5, 102.0, 101.5, 103.0, 102.5, 104.0, 103.5, 105.0]
        result = compute_sharpe_ratio(closes)
        assert result is not None
        assert result > 0

    def test_flat_series_returns_none(self):
        closes = [100.0] * 20
        result = compute_sharpe_ratio(closes)
        assert result is None

    def test_too_few_bars(self):
        closes = [100.0, 101.0, 102.0]
        result = compute_sharpe_ratio(closes)
        assert result is None


class TestMaxDrawdown:
    def test_known_drawdown(self):
        closes = [90.0, 100.0, 95.0, 80.0, 85.0, 90.0]
        result = compute_max_drawdown(closes)
        assert result == pytest.approx(-0.20, abs=0.001)

    def test_monotonic_increase(self):
        closes = [100.0, 101.0, 102.0, 103.0, 104.0]
        result = compute_max_drawdown(closes)
        assert result == 0.0


class TestVolatility:
    def test_known_series(self):
        closes = [100.0, 101.0, 99.5, 102.0, 98.0, 103.0, 97.5, 104.0, 96.0, 105.0]
        result = compute_volatility(closes)
        assert result is not None
        assert result > 0

    def test_too_few_bars(self):
        closes = [100.0, 101.0]
        result = compute_volatility(closes)
        assert result is None


class TestAvgProfitMargin:
    def test_single_period(self):
        income_data = [{"net_income": 20.0, "total_revenue": 100.0}]
        result = compute_avg_profit_margin(income_data)
        assert result == pytest.approx(20.0, abs=0.1)

    def test_multi_period(self):
        income_data = [
            {"net_income": 20.0, "total_revenue": 100.0},
            {"net_income": 30.0, "total_revenue": 100.0},
            {"net_income": 10.0, "total_revenue": 100.0},
            {"net_income": 40.0, "total_revenue": 200.0},
        ]
        result = compute_avg_profit_margin(income_data)
        assert result == pytest.approx(20.0, abs=0.1)

    def test_empty_data(self):
        result = compute_avg_profit_margin([])
        assert result is None

    def test_zero_revenue_skipped(self):
        income_data = [
            {"net_income": 20.0, "total_revenue": 100.0},
            {"net_income": 0.0, "total_revenue": 0.0},
        ]
        result = compute_avg_profit_margin(income_data)
        assert result == pytest.approx(20.0, abs=0.1)

    def test_missing_fields(self):
        income_data = [{"operating_income": 50.0}]
        result = compute_avg_profit_margin(income_data)
        assert result is None


class TestRiskClassification:
    def test_conservative(self):
        assert classify_risk(10.0) == "Conservative"

    def test_moderate(self):
        assert classify_risk(20.0) == "Moderate"

    def test_moderate_high(self):
        assert classify_risk(30.0) == "Moderate-High"

    def test_aggressive(self):
        assert classify_risk(50.0) == "Aggressive"

    def test_none_volatility(self):
        assert classify_risk(None) == "Unknown"
