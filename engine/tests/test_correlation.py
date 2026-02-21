import datetime as dt
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from margin_engine.correlation import CorrelationMatrix, ExcludedTicker, _pearson
from margin_engine.correlation import compute_factor_correlations, compute_return_correlations
from margin_engine.models.financial import PriceBar
from margin_engine.models.scoring import FactorBreakdown, FactorScore


class TestCorrelationModels:
    def test_excluded_ticker_fields(self):
        et = ExcludedTicker(ticker="AAPL", reason="insufficient data")
        assert et.ticker == "AAPL"
        assert et.reason == "insufficient data"

    def test_correlation_matrix_valid(self):
        m = CorrelationMatrix(
            tickers=["AAPL", "MSFT"],
            method="returns",
            matrix=[[1.0, 0.5], [0.5, 1.0]],
            sample_sizes=[[252, 250], [250, 252]],
            excluded=[],
            window_days=252,
            computed_at=datetime.now(UTC),
        )
        assert len(m.tickers) == 2
        assert m.matrix[0][1] == 0.5
        assert m.method == "returns"

    def test_correlation_matrix_allows_none_cells(self):
        m = CorrelationMatrix(
            tickers=["AAPL", "MSFT"],
            method="returns",
            matrix=[[1.0, None], [None, 1.0]],
            sample_sizes=[[252, 10], [10, 252]],
            excluded=[],
            window_days=252,
            computed_at=datetime.now(UTC),
        )
        assert m.matrix[0][1] is None

    def test_method_must_be_returns_or_factors(self):
        with pytest.raises(ValidationError):
            CorrelationMatrix(
                tickers=["AAPL"],
                method="invalid",
                matrix=[[1.0]],
                sample_sizes=[[252]],
                excluded=[],
                window_days=252,
                computed_at=datetime.now(UTC),
            )


class TestPearsonCorrelation:
    def test_perfect_positive(self):
        assert _pearson([1.0, 2.0, 3.0], [1.0, 2.0, 3.0]) == pytest.approx(1.0)

    def test_perfect_negative(self):
        assert _pearson([1.0, 2.0, 3.0], [3.0, 2.0, 1.0]) == pytest.approx(-1.0)

    def test_no_correlation(self):
        r = _pearson([1.0, -1.0, 1.0, -1.0], [1.0, 1.0, -1.0, -1.0])
        assert r == pytest.approx(0.0)

    def test_known_value(self):
        r = _pearson([10.0, 20.0, 30.0], [12.0, 25.0, 28.0])
        assert r == pytest.approx(0.94063, abs=1e-4)

    def test_constant_series_returns_none(self):
        assert _pearson([5.0, 5.0, 5.0], [1.0, 2.0, 3.0]) is None

    def test_too_short_returns_none(self):
        assert _pearson([1.0], [2.0]) is None

    def test_empty_returns_none(self):
        assert _pearson([], []) is None


def _bar(date_str: str, close: float) -> PriceBar:
    """Helper: minimal PriceBar."""
    p = Decimal(str(close))
    return PriceBar(date=date_str, open=p, high=p, low=p, close=p, volume=100_000)


def _daily_bars(start: str, prices: list[float]) -> list[PriceBar]:
    """Generate bars from a list of closing prices, one per business day."""
    base = dt.date.fromisoformat(start)
    bars = []
    d = base
    for price in prices:
        bars.append(_bar(d.isoformat(), price))
        d += dt.timedelta(days=1)
        # skip weekends
        while d.weekday() >= 5:
            d += dt.timedelta(days=1)
    return bars


class TestReturnCorrelations:
    def test_two_identical_series_correlation_is_one(self):
        prices = [100.0, 102.0, 101.0, 105.0, 103.0] * 10  # 50 points
        bars_a = _daily_bars("2025-01-02", prices)
        bars_b = _daily_bars("2025-01-02", prices)
        result = compute_return_correlations(
            {"AAPL": bars_a, "COPY": bars_b}, window_days=252
        )
        assert result.tickers == ["AAPL", "COPY"]
        assert result.matrix[0][0] == pytest.approx(1.0)
        assert result.matrix[1][1] == pytest.approx(1.0)
        assert result.matrix[0][1] == pytest.approx(1.0, abs=1e-6)
        assert result.matrix[1][0] == pytest.approx(1.0, abs=1e-6)

    def test_inversely_correlated(self):
        # Build prices from alternating returns: when one goes up, the other goes down
        import random

        rng = random.Random(42)
        shocks = [rng.gauss(0, 0.02) for _ in range(49)]
        prices_a = [100.0]
        prices_b = [100.0]
        for s in shocks:
            prices_a.append(prices_a[-1] * (1 + s))
            prices_b.append(prices_b[-1] * (1 - s))  # opposite return
        bars_a = _daily_bars("2025-01-02", prices_a)
        bars_b = _daily_bars("2025-01-02", prices_b)
        result = compute_return_correlations({"UP": bars_a, "DOWN": bars_b})
        assert result.matrix[0][1] is not None
        assert result.matrix[0][1] < -0.9

    def test_symmetric(self):
        bars_a = _daily_bars("2025-01-02", [100 + i * 0.5 for i in range(50)])
        bars_b = _daily_bars("2025-01-02", [50 + i * 0.3 for i in range(50)])
        bars_c = _daily_bars("2025-01-02", [200 - i * 0.2 for i in range(50)])
        result = compute_return_correlations({"A": bars_a, "B": bars_b, "C": bars_c})
        for i in range(3):
            for j in range(3):
                assert result.matrix[i][j] == pytest.approx(
                    result.matrix[j][i], abs=1e-10
                )

    def test_sample_sizes_populated(self):
        bars_a = _daily_bars("2025-01-02", [100 + i for i in range(50)])
        bars_b = _daily_bars("2025-01-02", [50 + i for i in range(50)])
        result = compute_return_correlations({"A": bars_a, "B": bars_b})
        # 50 prices = 49 returns
        assert result.sample_sizes[0][1] == 49

    def test_insufficient_overlap_returns_none(self):
        bars_a = _daily_bars("2025-01-02", [100 + i for i in range(10)])
        bars_b = _daily_bars("2025-01-02", [50 + i for i in range(10)])
        result = compute_return_correlations(
            {"A": bars_a, "B": bars_b}, min_overlap=30
        )
        assert result.matrix[0][1] is None

    def test_ticker_with_too_few_bars_excluded(self):
        bars_good = _daily_bars("2025-01-02", [100 + i for i in range(50)])
        bars_short = _daily_bars("2025-01-02", [50.0, 51.0])
        result = compute_return_correlations(
            {"GOOD": bars_good, "SHORT": bars_short}, min_bars=10
        )
        assert "SHORT" in [e.ticker for e in result.excluded]
        assert result.tickers == ["GOOD"]

    def test_fewer_than_two_valid_tickers_returns_empty(self):
        bars = _daily_bars("2025-01-02", [100.0, 101.0])
        result = compute_return_correlations({"ONLY": bars}, min_bars=10)
        assert result.tickers == []
        assert result.matrix == []

    def test_method_is_returns(self):
        bars_a = _daily_bars("2025-01-02", [100 + i for i in range(50)])
        bars_b = _daily_bars("2025-01-02", [50 + i for i in range(50)])
        result = compute_return_correlations({"A": bars_a, "B": bars_b})
        assert result.method == "returns"


def _factor(name: str, percentiles: list[float]) -> FactorBreakdown:
    """Helper: build a FactorBreakdown with given sub-score percentiles."""
    return FactorBreakdown(
        factor_name=name,
        weight=1.0,
        sub_scores=[
            FactorScore(name=f"metric_{i}", raw_value=0.0, percentile_rank=p, detail="")
            for i, p in enumerate(percentiles)
        ],
    )


def _factors(
    quality: list[float], value: list[float], momentum: list[float]
) -> dict[str, FactorBreakdown]:
    """Helper: build the 3-factor dict for a ticker."""
    return {
        "quality": _factor("quality", quality),
        "value": _factor("value", value),
        "momentum": _factor("momentum", momentum),
    }


class TestFactorCorrelations:
    def test_identical_profiles_correlation_one(self):
        profiles = {
            "AAPL": _factors([80, 70, 60], [50, 40, 30], [90, 85, 80]),
            "COPY": _factors([80, 70, 60], [50, 40, 30], [90, 85, 80]),
        }
        result = compute_factor_correlations(profiles)
        assert result.method == "factors"
        assert result.matrix[0][1] == pytest.approx(1.0)

    def test_opposite_profiles_negative(self):
        profiles = {
            "HIGH": _factors([90, 90, 90], [90, 90, 90], [90, 90, 90]),
            "LOW": _factors([10, 10, 10], [10, 10, 10], [10, 10, 10]),
        }
        result = compute_factor_correlations(profiles)
        # Constant vectors -> None (zero variance)
        assert result.matrix[0][1] is None

    def test_varied_profiles(self):
        profiles = {
            "A": _factors([90, 50, 30], [70, 60, 40], [80, 20, 50]),
            "B": _factors([85, 55, 25], [65, 65, 35], [75, 25, 45]),
        }
        result = compute_factor_correlations(profiles)
        assert result.matrix[0][1] is not None
        assert result.matrix[0][1] > 0.9

    def test_symmetric(self):
        profiles = {
            "A": _factors([90, 50], [70, 60], [80, 20]),
            "B": _factors([20, 80], [30, 90], [50, 50]),
            "C": _factors([50, 50], [50, 50], [50, 60]),
        }
        result = compute_factor_correlations(profiles)
        for i in range(3):
            for j in range(3):
                if result.matrix[i][j] is not None and result.matrix[j][i] is not None:
                    assert result.matrix[i][j] == result.matrix[j][i]

    def test_single_ticker_returns_minimal(self):
        profiles = {"ONLY": _factors([80, 70], [50, 40], [90, 85])}
        result = compute_factor_correlations(profiles)
        assert result.tickers == ["ONLY"]
        assert result.matrix == [[1.0]]
