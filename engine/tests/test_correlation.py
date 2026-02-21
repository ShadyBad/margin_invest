from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from margin_engine.correlation import CorrelationMatrix, ExcludedTicker, _pearson


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
