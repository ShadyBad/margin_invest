"""Tests for retry decorator for transient provider failures."""

from margin_engine.ingestion.retry import retry_transient
from margin_engine.ingestion.types import DataCategory, FetchResult


def _make_result(
    success: bool = True,
    error: str | None = None,
) -> FetchResult:
    """Helper to build a FetchResult with minimal boilerplate."""
    return FetchResult(
        provider_name="test",
        category=DataCategory.FUNDAMENTALS,
        ticker="AAPL",
        raw_data={} if success else {},
        fetched_at="2026-02-21T00:00:00Z",
        success=success,
        error=error,
    )


class TestRetryNoRetryOnSuccess:
    """No retry when the function returns a successful result."""

    def test_returns_immediately_on_success(self):
        call_count = 0

        @retry_transient(max_retries=3, base_delay=0.0)
        def fetch(ticker: str) -> FetchResult:
            nonlocal call_count
            call_count += 1
            return _make_result(success=True)

        result = fetch("AAPL")
        assert result.success is True
        assert call_count == 1


class TestRetryOnTransientError:
    """Retries when the error message contains transient keywords."""

    def test_retries_on_429_then_succeeds(self):
        call_count = 0

        @retry_transient(max_retries=3, base_delay=0.0)
        def fetch(ticker: str) -> FetchResult:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                return _make_result(success=False, error="HTTP 429 Too Many Requests")
            return _make_result(success=True)

        result = fetch("AAPL")
        assert result.success is True
        assert call_count == 3

    def test_retries_on_rate_limit(self):
        call_count = 0

        @retry_transient(max_retries=3, base_delay=0.0)
        def fetch(ticker: str) -> FetchResult:
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                return _make_result(success=False, error="Rate limit exceeded")
            return _make_result(success=True)

        result = fetch("AAPL")
        assert result.success is True
        assert call_count == 2

    def test_retries_on_500_server_error(self):
        call_count = 0

        @retry_transient(max_retries=3, base_delay=0.0)
        def fetch(ticker: str) -> FetchResult:
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                return _make_result(success=False, error="500 Internal Server Error")
            return _make_result(success=True)

        result = fetch("AAPL")
        assert result.success is True
        assert call_count == 2

    def test_retries_on_timeout(self):
        call_count = 0

        @retry_transient(max_retries=3, base_delay=0.0)
        def fetch(ticker: str) -> FetchResult:
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                return _make_result(success=False, error="Request timed out")
            return _make_result(success=True)

        result = fetch("AAPL")
        assert result.success is True
        assert call_count == 2


class TestNoRetryOnPermanentError:
    """No retry when the error is permanent (not transient)."""

    def test_no_retry_on_ticker_not_found(self):
        call_count = 0

        @retry_transient(max_retries=3, base_delay=0.0)
        def fetch(ticker: str) -> FetchResult:
            nonlocal call_count
            call_count += 1
            return _make_result(success=False, error="Ticker not found")

        result = fetch("INVALID")
        assert result.success is False
        assert result.error == "Ticker not found"
        assert call_count == 1


class TestNoRetryOnDataUnavailable:
    """No retry when data is unavailable (not transient)."""

    def test_no_retry_on_no_financial_data(self):
        call_count = 0

        @retry_transient(max_retries=3, base_delay=0.0)
        def fetch(ticker: str) -> FetchResult:
            nonlocal call_count
            call_count += 1
            return _make_result(success=False, error="No financial data available")

        result = fetch("AAPL")
        assert result.success is False
        assert result.error == "No financial data available"
        assert call_count == 1


class TestExhaustsRetries:
    """Returns the last failed result after exhausting retries."""

    def test_returns_last_result_after_max_retries(self):
        call_count = 0

        @retry_transient(max_retries=3, base_delay=0.0)
        def fetch(ticker: str) -> FetchResult:
            nonlocal call_count
            call_count += 1
            return _make_result(
                success=False,
                error=f"503 Service Unavailable (attempt {call_count})",
            )

        result = fetch("AAPL")
        assert result.success is False
        # 1 initial + 3 retries = 4 total calls
        assert call_count == 4
        assert "attempt 4" in result.error

    def test_default_max_retries_is_3(self):
        call_count = 0

        @retry_transient(base_delay=0.0)
        def fetch(ticker: str) -> FetchResult:
            nonlocal call_count
            call_count += 1
            return _make_result(success=False, error="502 Bad Gateway")

        fetch("AAPL")
        assert call_count == 4  # 1 initial + 3 retries


class TestRetryOnTransientException:
    """Retries when the function raises a transient exception."""

    def test_retries_on_connection_error_then_succeeds(self):
        call_count = 0

        @retry_transient(max_retries=3, base_delay=0.0)
        def fetch(ticker: str) -> FetchResult:
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("Connection refused")
            return _make_result(success=True)

        result = fetch("AAPL")
        assert result.success is True
        assert call_count == 2

    def test_retries_on_timeout_error(self):
        call_count = 0

        @retry_transient(max_retries=3, base_delay=0.0)
        def fetch(ticker: str) -> FetchResult:
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise TimeoutError("Operation timed out")
            return _make_result(success=True)

        result = fetch("AAPL")
        assert result.success is True
        assert call_count == 2

    def test_retries_on_os_error(self):
        call_count = 0

        @retry_transient(max_retries=3, base_delay=0.0)
        def fetch(ticker: str) -> FetchResult:
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise OSError("Network unreachable")
            return _make_result(success=True)

        result = fetch("AAPL")
        assert result.success is True
        assert call_count == 2

    def test_exhausts_retries_on_persistent_exception(self):
        call_count = 0

        @retry_transient(max_retries=2, base_delay=0.0)
        def fetch(ticker: str) -> FetchResult:
            nonlocal call_count
            call_count += 1
            raise ConnectionError("Connection refused")

        result = fetch("AAPL")
        assert result.success is False
        assert "Connection refused" in result.error
        assert call_count == 3  # 1 initial + 2 retries


class TestNoRetryOnNonTransientException:
    """Returns FetchResult(success=False) on non-transient exceptions."""

    def test_no_retry_on_value_error(self):
        call_count = 0

        @retry_transient(max_retries=3, base_delay=0.0)
        def fetch(ticker: str) -> FetchResult:
            nonlocal call_count
            call_count += 1
            raise ValueError("Invalid argument")

        result = fetch("AAPL")
        assert result.success is False
        assert "Invalid argument" in result.error
        assert call_count == 1

    def test_no_retry_on_key_error(self):
        call_count = 0

        @retry_transient(max_retries=3, base_delay=0.0)
        def fetch(ticker: str) -> FetchResult:
            nonlocal call_count
            call_count += 1
            raise KeyError("missing_key")

        result = fetch("AAPL")
        assert result.success is False
        assert call_count == 1
