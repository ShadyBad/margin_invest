from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from margin_engine.correlation import CorrelationMatrix, ExcludedTicker


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
