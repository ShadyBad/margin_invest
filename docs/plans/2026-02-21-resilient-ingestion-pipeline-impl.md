# Resilient Ingestion Pipeline Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix the Railway ingestion cascade failure by adding the missing `lxml` dependency, fixing rate limiting, wiring error classification, adding circuit breaker/retry patterns, implementing FMP fallback provider, and adding observability.

**Architecture:** The ingestion pipeline lives in `engine/src/margin_engine/ingestion/` (pure Python, no web deps) and is orchestrated by `api/src/margin_api/cli.py` and `api/src/margin_api/workers.py`. We fix the immediate root cause (missing lxml), then layer on resilience (circuit breaker, retry, multi-provider fallback) and observability (per-category logging, dead-letter tracking, alerting).

**Tech Stack:** Python 3.13, yfinance, FMP REST API (httpx), Pydantic, SQLAlchemy 2.0, FastAPI, pytest, aiosqlite (tests)

**Design doc:** `docs/plans/2026-02-21-resilient-ingestion-pipeline-design.md`

---

## Task 1: Add `lxml` Dependency

**Files:**
- Modify: `engine/pyproject.toml:6-12`

**Step 1: Add lxml to engine dependencies**

In `engine/pyproject.toml`, add `"lxml>=5.0"` to the `dependencies` list:

```toml
dependencies = [
    "pydantic>=2.10",
    "numpy>=2.2",
    "scipy>=1.15",
    "yfinance>=1.1.0",
    "pyyaml>=6.0.3",
    "lxml>=5.0",
]
```

**Step 2: Sync the lockfile**

Run: `uv sync`
Expected: lxml installs successfully

**Step 3: Verify earnings_dates works**

Run: `uv run python -c "import yfinance; t = yfinance.Ticker('AAPL'); print(len(t.earnings_dates), 'earnings dates')"`
Expected: `25 earnings dates` (or similar positive number)

**Step 4: Commit**

```bash
git add engine/pyproject.toml uv.lock
git commit -m "fix: add lxml dependency for yfinance earnings_dates"
```

---

## Task 2: Circuit Breaker

**Files:**
- Create: `engine/src/margin_engine/ingestion/circuit_breaker.py`
- Create: `engine/tests/ingestion/test_circuit_breaker.py`

**Step 1: Write failing tests**

Create `engine/tests/ingestion/test_circuit_breaker.py`:

```python
"""Tests for the circuit breaker."""
from __future__ import annotations

import time
from unittest.mock import patch

import pytest
from margin_engine.ingestion.circuit_breaker import CircuitBreaker, CircuitState


class TestCircuitBreakerStates:
    def test_starts_closed(self):
        cb = CircuitBreaker(failure_threshold=3, cooldown_seconds=10)
        assert cb.state == CircuitState.CLOSED

    def test_stays_closed_below_threshold(self):
        cb = CircuitBreaker(failure_threshold=3, cooldown_seconds=10)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.CLOSED

    def test_opens_at_threshold(self):
        cb = CircuitBreaker(failure_threshold=3, cooldown_seconds=10)
        cb.record_failure()
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

    def test_allow_request_blocked_when_open(self):
        cb = CircuitBreaker(failure_threshold=3, cooldown_seconds=10)
        for _ in range(3):
            cb.record_failure()
        assert cb.allow_request() is False

    def test_allow_request_allowed_when_closed(self):
        cb = CircuitBreaker(failure_threshold=3, cooldown_seconds=10)
        assert cb.allow_request() is True

    def test_success_resets_failure_count(self):
        cb = CircuitBreaker(failure_threshold=3, cooldown_seconds=10)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        assert cb.state == CircuitState.CLOSED
        assert cb._consecutive_failures == 0


class TestCircuitBreakerCooldown:
    def test_half_open_after_cooldown(self):
        cb = CircuitBreaker(failure_threshold=3, cooldown_seconds=0.1)
        for _ in range(3):
            cb.record_failure()
        assert cb.state == CircuitState.OPEN
        time.sleep(0.15)
        assert cb.state == CircuitState.HALF_OPEN

    def test_half_open_allows_one_probe(self):
        cb = CircuitBreaker(failure_threshold=3, cooldown_seconds=0.1)
        for _ in range(3):
            cb.record_failure()
        time.sleep(0.15)
        assert cb.allow_request() is True  # probe allowed
        assert cb.allow_request() is False  # second blocked

    def test_probe_success_closes_breaker(self):
        cb = CircuitBreaker(failure_threshold=3, cooldown_seconds=0.1)
        for _ in range(3):
            cb.record_failure()
        time.sleep(0.15)
        cb.allow_request()  # enter half-open
        cb.record_success()
        assert cb.state == CircuitState.CLOSED
        assert cb.allow_request() is True

    def test_probe_failure_reopens_breaker(self):
        cb = CircuitBreaker(failure_threshold=3, cooldown_seconds=0.1)
        for _ in range(3):
            cb.record_failure()
        time.sleep(0.15)
        cb.allow_request()  # enter half-open
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest engine/tests/ingestion/test_circuit_breaker.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'margin_engine.ingestion.circuit_breaker'`

**Step 3: Implement circuit breaker**

Create `engine/src/margin_engine/ingestion/circuit_breaker.py`:

```python
"""Circuit breaker for provider health tracking.

Prevents wasting API calls on a provider that is consistently failing
(e.g., IP-blocked, outage). Trips after N consecutive failures, then
enters a cooldown period before allowing a single probe request.
"""
from __future__ import annotations

import logging
import threading
import time
from enum import StrEnum

logger = logging.getLogger(__name__)


class CircuitState(StrEnum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Per-provider circuit breaker with three states.

    - CLOSED: requests flow through normally.
    - OPEN: all requests are blocked (provider is down).
    - HALF_OPEN: one probe request is allowed after cooldown.

    Thread-safe via :class:`threading.Lock`.
    """

    def __init__(
        self,
        failure_threshold: int = 10,
        cooldown_seconds: float = 900.0,
    ) -> None:
        self._failure_threshold = failure_threshold
        self._cooldown_seconds = cooldown_seconds
        self._consecutive_failures = 0
        self._last_failure_time: float = 0.0
        self._state = CircuitState.CLOSED
        self._probe_in_flight = False
        self._lock = threading.Lock()

    @property
    def state(self) -> CircuitState:
        with self._lock:
            if self._state == CircuitState.OPEN:
                elapsed = time.monotonic() - self._last_failure_time
                if elapsed >= self._cooldown_seconds:
                    return CircuitState.HALF_OPEN
            return self._state

    def allow_request(self) -> bool:
        """Check whether a request should be allowed through."""
        with self._lock:
            if self._state == CircuitState.CLOSED:
                return True

            if self._state == CircuitState.OPEN:
                elapsed = time.monotonic() - self._last_failure_time
                if elapsed >= self._cooldown_seconds:
                    # Transition to half-open, allow one probe
                    self._state = CircuitState.HALF_OPEN
                    self._probe_in_flight = True
                    return True
                return False

            # HALF_OPEN: only allow if no probe is in flight
            if self._state == CircuitState.HALF_OPEN:
                if not self._probe_in_flight:
                    self._probe_in_flight = True
                    return True
                return False

            return False

    def record_success(self) -> None:
        """Record a successful request — resets the breaker."""
        with self._lock:
            self._consecutive_failures = 0
            self._state = CircuitState.CLOSED
            self._probe_in_flight = False

    def record_failure(self) -> None:
        """Record a failed request — may trip the breaker."""
        with self._lock:
            self._consecutive_failures += 1
            self._last_failure_time = time.monotonic()

            if self._state == CircuitState.HALF_OPEN:
                # Probe failed — reopen
                self._state = CircuitState.OPEN
                self._probe_in_flight = False
                logger.warning(
                    "Circuit breaker probe failed, re-opening (failures=%d)",
                    self._consecutive_failures,
                )
                return

            if self._consecutive_failures >= self._failure_threshold:
                self._state = CircuitState.OPEN
                logger.warning(
                    "Circuit breaker tripped after %d consecutive failures",
                    self._consecutive_failures,
                )
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest engine/tests/ingestion/test_circuit_breaker.py -v`
Expected: All 10 tests PASS

**Step 5: Commit**

```bash
git add engine/src/margin_engine/ingestion/circuit_breaker.py engine/tests/ingestion/test_circuit_breaker.py
git commit -m "feat(engine): add circuit breaker for provider health tracking"
```

---

## Task 3: Retry Decorator

**Files:**
- Create: `engine/src/margin_engine/ingestion/retry.py`
- Create: `engine/tests/ingestion/test_retry.py`

**Step 1: Write failing tests**

Create `engine/tests/ingestion/test_retry.py`:

```python
"""Tests for the retry decorator."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from margin_engine.ingestion.retry import retry_transient
from margin_engine.ingestion.types import DataCategory, FetchResult


def _make_result(success: bool, error: str | None = None) -> FetchResult:
    return FetchResult(
        provider_name="test",
        category=DataCategory.FUNDAMENTALS,
        ticker="AAPL",
        raw_data={} if not success else {"data": True},
        fetched_at="2026-01-01T00:00:00Z",
        success=success,
        error=error,
    )


class TestRetryTransient:
    def test_no_retry_on_success(self):
        fn = MagicMock(return_value=_make_result(True))
        wrapped = retry_transient(max_retries=3, base_delay=0.0)(fn)
        result = wrapped("AAPL")
        assert result.success is True
        assert fn.call_count == 1

    def test_retries_on_transient_error(self):
        fn = MagicMock(side_effect=[
            _make_result(False, "429 Too Many Requests"),
            _make_result(True),
        ])
        wrapped = retry_transient(max_retries=3, base_delay=0.0)(fn)
        result = wrapped("AAPL")
        assert result.success is True
        assert fn.call_count == 2

    def test_no_retry_on_permanent_error(self):
        fn = MagicMock(return_value=_make_result(False, "Ticker not found"))
        wrapped = retry_transient(max_retries=3, base_delay=0.0)(fn)
        result = wrapped("AAPL")
        assert result.success is False
        assert fn.call_count == 1

    def test_no_retry_on_data_unavailable(self):
        fn = MagicMock(return_value=_make_result(False, "No financial data available"))
        wrapped = retry_transient(max_retries=3, base_delay=0.0)(fn)
        result = wrapped("AAPL")
        assert result.success is False
        assert fn.call_count == 1

    def test_exhausts_retries(self):
        fn = MagicMock(return_value=_make_result(False, "503 Service Unavailable"))
        wrapped = retry_transient(max_retries=3, base_delay=0.0)(fn)
        result = wrapped("AAPL")
        assert result.success is False
        assert fn.call_count == 4  # 1 initial + 3 retries

    def test_retries_on_exception(self):
        fn = MagicMock(side_effect=[
            ConnectionError("refused"),
            _make_result(True),
        ])
        wrapped = retry_transient(max_retries=3, base_delay=0.0)(fn)
        result = wrapped("AAPL")
        assert result.success is True
        assert fn.call_count == 2

    def test_no_retry_on_non_transient_exception(self):
        fn = MagicMock(side_effect=ValueError("bad input"))
        wrapped = retry_transient(max_retries=3, base_delay=0.0)(fn)
        result = wrapped("AAPL")
        assert result.success is False
        assert "bad input" in result.error
        assert fn.call_count == 1
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest engine/tests/ingestion/test_retry.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Implement retry decorator**

Create `engine/src/margin_engine/ingestion/retry.py`:

```python
"""Retry decorator for transient provider failures.

Wraps provider fetch methods to automatically retry on transient errors
(timeouts, rate limits, server errors) with exponential backoff.
Non-transient errors (permanent, data unavailable) are returned immediately.
"""
from __future__ import annotations

import functools
import logging
import time
from datetime import UTC, datetime
from typing import Callable

from margin_engine.ingestion.types import DataCategory, FetchResult

logger = logging.getLogger(__name__)

_TRANSIENT_KEYWORDS = frozenset({
    "429", "rate limit", "too many requests",
    "500", "502", "503",
    "timeout", "timed out",
})

_TRANSIENT_EXCEPTIONS = (TimeoutError, ConnectionError, OSError)


def _is_transient_error(error: str) -> bool:
    """Check if an error message indicates a transient failure."""
    lower = error.lower()
    return any(kw in lower for kw in _TRANSIENT_KEYWORDS)


def _is_transient_exception(exc: Exception) -> bool:
    """Check if an exception type indicates a transient failure."""
    return isinstance(exc, _TRANSIENT_EXCEPTIONS)


def retry_transient(
    max_retries: int = 3,
    base_delay: float = 2.0,
) -> Callable:
    """Decorator that retries a fetch function on transient errors.

    Args:
        max_retries: Maximum number of retry attempts.
        base_delay: Base delay in seconds (doubles each retry).
    """
    def decorator(fn: Callable[..., FetchResult]) -> Callable[..., FetchResult]:
        @functools.wraps(fn)
        def wrapper(*args, **kwargs) -> FetchResult:
            last_result: FetchResult | None = None

            for attempt in range(1 + max_retries):
                try:
                    result = fn(*args, **kwargs)
                    if result.success:
                        return result

                    last_result = result
                    # Only retry if the error looks transient
                    if not result.error or not _is_transient_error(result.error):
                        return result

                    if attempt < max_retries:
                        delay = base_delay * (2 ** attempt)
                        logger.info(
                            "Transient error (attempt %d/%d): %s — retrying in %.1fs",
                            attempt + 1, 1 + max_retries, result.error, delay,
                        )
                        time.sleep(delay)

                except Exception as exc:
                    if not _is_transient_exception(exc):
                        return FetchResult(
                            provider_name="",
                            category=DataCategory.FUNDAMENTALS,
                            ticker=str(args[0]) if args else "unknown",
                            raw_data={},
                            fetched_at=datetime.now(UTC).isoformat(),
                            success=False,
                            error=str(exc),
                        )

                    if attempt < max_retries:
                        delay = base_delay * (2 ** attempt)
                        logger.info(
                            "Transient exception (attempt %d/%d): %s — retrying in %.1fs",
                            attempt + 1, 1 + max_retries, exc, delay,
                        )
                        time.sleep(delay)
                    else:
                        return FetchResult(
                            provider_name="",
                            category=DataCategory.FUNDAMENTALS,
                            ticker=str(args[0]) if args else "unknown",
                            raw_data={},
                            fetched_at=datetime.now(UTC).isoformat(),
                            success=False,
                            error=str(exc),
                        )

            # Exhausted all retries
            return last_result  # type: ignore[return-value]

        return wrapper
    return decorator
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest engine/tests/ingestion/test_retry.py -v`
Expected: All 7 tests PASS

**Step 5: Commit**

```bash
git add engine/src/margin_engine/ingestion/retry.py engine/tests/ingestion/test_retry.py
git commit -m "feat(engine): add retry decorator for transient provider failures"
```

---

## Task 4: Symbol Mapper

**Files:**
- Create: `engine/src/margin_engine/ingestion/symbol_mapper.py`
- Create: `engine/symbol_overrides.yaml`
- Create: `engine/tests/ingestion/test_symbol_mapper.py`

**Step 1: Write failing tests**

Create `engine/tests/ingestion/test_symbol_mapper.py`:

```python
"""Tests for the symbol mapper."""
from __future__ import annotations

import pytest
from margin_engine.ingestion.symbol_mapper import SymbolMapper


@pytest.fixture
def mapper() -> SymbolMapper:
    overrides = {
        "BRK-B": {"fmp": "BRK-B", "polygon": "BRK.B"},
        "BF-B": {"fmp": "BF-B", "polygon": "BF.B"},
    }
    return SymbolMapper(overrides=overrides)


class TestSymbolMapper:
    def test_passthrough_default(self, mapper: SymbolMapper):
        assert mapper.to_provider("AAPL", "fmp") == "AAPL"
        assert mapper.to_provider("MSFT", "polygon") == "MSFT"

    def test_override_to_provider(self, mapper: SymbolMapper):
        assert mapper.to_provider("BRK-B", "polygon") == "BRK.B"
        assert mapper.to_provider("BRK-B", "fmp") == "BRK-B"

    def test_override_missing_provider_passthrough(self, mapper: SymbolMapper):
        assert mapper.to_provider("BRK-B", "unknown_provider") == "BRK-B"

    def test_from_provider_roundtrip(self, mapper: SymbolMapper):
        assert mapper.from_provider("BRK.B", "polygon") == "BRK-B"
        assert mapper.from_provider("BF.B", "polygon") == "BF-B"

    def test_from_provider_passthrough(self, mapper: SymbolMapper):
        assert mapper.from_provider("AAPL", "fmp") == "AAPL"

    def test_from_yaml(self, tmp_path):
        yaml_path = tmp_path / "overrides.yaml"
        yaml_path.write_text(
            'overrides:\n'
            '  BRK-B:\n'
            '    polygon: "BRK.B"\n'
        )
        m = SymbolMapper.from_yaml(yaml_path)
        assert m.to_provider("BRK-B", "polygon") == "BRK.B"
        assert m.to_provider("AAPL", "polygon") == "AAPL"
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest engine/tests/ingestion/test_symbol_mapper.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Implement symbol mapper**

Create `engine/src/margin_engine/ingestion/symbol_mapper.py`:

```python
"""Cross-provider symbol translation.

Uses yfinance format as canonical (matches DB storage).
Most symbols are identical across providers — only known
exceptions need overrides, loaded from YAML.
"""
from __future__ import annotations

from pathlib import Path

import yaml


class SymbolMapper:
    """Translates ticker symbols between providers.

    Default behavior is pass-through. Overrides are loaded from a dict
    or YAML file for known exceptions (e.g., BRK-B vs BRK.B).
    """

    def __init__(self, overrides: dict[str, dict[str, str]] | None = None) -> None:
        # canonical_ticker -> {provider_name: provider_ticker}
        self._to_provider: dict[str, dict[str, str]] = overrides or {}
        # Build reverse map: (provider_name, provider_ticker) -> canonical_ticker
        self._from_provider: dict[tuple[str, str], str] = {}
        for canonical, provider_map in self._to_provider.items():
            for provider_name, provider_ticker in provider_map.items():
                self._from_provider[(provider_name, provider_ticker)] = canonical

    @classmethod
    def from_yaml(cls, path: Path) -> SymbolMapper:
        """Load overrides from a YAML file."""
        if not path.exists():
            return cls()
        with open(path) as f:
            data = yaml.safe_load(f) or {}
        return cls(overrides=data.get("overrides", {}))

    def to_provider(self, ticker: str, provider_name: str) -> str:
        """Convert canonical ticker to provider-specific format."""
        provider_map = self._to_provider.get(ticker)
        if provider_map is None:
            return ticker
        return provider_map.get(provider_name, ticker)

    def from_provider(self, ticker: str, provider_name: str) -> str:
        """Convert provider-specific ticker back to canonical format."""
        return self._from_provider.get((provider_name, ticker), ticker)
```

Create `engine/symbol_overrides.yaml`:

```yaml
# Symbol overrides for cross-provider translation.
# Canonical format is yfinance (dash-separated).
# Only add entries where providers differ.

overrides:
  BRK-B:
    polygon: "BRK.B"
  BF-B:
    polygon: "BF.B"
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest engine/tests/ingestion/test_symbol_mapper.py -v`
Expected: All 6 tests PASS

**Step 5: Commit**

```bash
git add engine/src/margin_engine/ingestion/symbol_mapper.py engine/symbol_overrides.yaml engine/tests/ingestion/test_symbol_mapper.py
git commit -m "feat(engine): add symbol mapper for cross-provider translation"
```

---

## Task 5: Refactor YFinanceProvider — `fetch_all` + Provider-Owned Rate Limiting

This is the largest task. We refactor `YFinanceProvider` to:
- Add a `fetch_all()` method that reuses one `yf.Ticker` object
- Add a `fetch_info()` method (extracts info dict from cli.py)
- Accept an optional `RateLimiter` and gate each HTTP call internally
- Apply `retry_transient` to each fetch method

**Files:**
- Modify: `engine/src/margin_engine/ingestion/providers/yfinance_provider.py`
- Modify: `engine/tests/ingestion/providers/test_yfinance_provider.py`

**Step 1: Write the new tests**

Add to `engine/tests/ingestion/providers/test_yfinance_provider.py`:

```python
# Add these imports at the top:
from margin_engine.ingestion.rate_limiter import RateLimiter

# Add these test classes:

class TestFetchInfo:
    @patch("margin_engine.ingestion.providers.yfinance_provider.yf")
    def test_fetch_info_success(self, mock_yf: MagicMock, provider: YFinanceProvider) -> None:
        mock_ticker = MagicMock()
        mock_ticker.info = {
            "shortName": "Apple Inc.",
            "sector": "Technology",
            "country": "United States",
            "marketCap": 3000000000000,
            "sharesOutstanding": 15000000000,
        }
        mock_yf.Ticker.return_value = mock_ticker

        result = provider.fetch_info("AAPL")

        assert result.success is True
        assert result.raw_data["shortName"] == "Apple Inc."
        assert result.raw_data["country"] == "United States"

    @patch("margin_engine.ingestion.providers.yfinance_provider.yf")
    def test_fetch_info_empty(self, mock_yf: MagicMock, provider: YFinanceProvider) -> None:
        mock_ticker = MagicMock()
        mock_ticker.info = {}
        mock_yf.Ticker.return_value = mock_ticker

        result = provider.fetch_info("BAD")

        assert result.success is True
        assert result.raw_data == {}


class TestFetchAll:
    @patch("margin_engine.ingestion.providers.yfinance_provider.yf")
    def test_fetch_all_returns_all_categories(self, mock_yf: MagicMock, provider: YFinanceProvider) -> None:
        mock_ticker = MagicMock()
        mock_ticker.financials = pd.DataFrame(
            {"2024-01-01": [100_000]}, index=["Total Revenue"]
        )
        mock_ticker.balance_sheet = pd.DataFrame(
            {"2024-01-01": [500_000]}, index=["Total Assets"]
        )
        mock_ticker.cashflow = pd.DataFrame(
            {"2024-01-01": [40_000]}, index=["Operating Cash Flow"]
        )
        mock_ticker.history.return_value = pd.DataFrame(
            {"Open": [150.0], "High": [155.0], "Low": [149.0], "Close": [154.0], "Volume": [1_000_000]},
            index=pd.to_datetime(["2024-01-01"]),
        )
        mock_ticker.earnings_dates = pd.DataFrame(
            {"Reported EPS": [1.52], "EPS Estimate": [1.50]},
            index=pd.to_datetime(["2024-01-25"]),
        )
        mock_ticker.info = {"shortName": "Apple Inc.", "country": "United States"}
        mock_yf.Ticker.return_value = mock_ticker

        results = provider.fetch_all("AAPL")

        assert "fundamentals" in results
        assert "price" in results
        assert "earnings" in results
        assert "info" in results
        assert results["fundamentals"].success is True
        assert results["price"].success is True
        assert results["earnings"].success is True
        assert results["info"].success is True
        # Should only create ONE yf.Ticker instance
        mock_yf.Ticker.assert_called_once_with("AAPL")

    @patch("margin_engine.ingestion.providers.yfinance_provider.yf")
    def test_fetch_all_partial_failure(self, mock_yf: MagicMock, provider: YFinanceProvider) -> None:
        mock_ticker = MagicMock()
        mock_ticker.financials = pd.DataFrame()
        mock_ticker.balance_sheet = pd.DataFrame()
        mock_ticker.cashflow = pd.DataFrame()
        mock_ticker.history.return_value = pd.DataFrame()
        type(mock_ticker).earnings_dates = property(
            lambda self: (_ for _ in ()).throw(RuntimeError("lxml missing"))
        )
        mock_ticker.info = {"shortName": "Test"}
        mock_yf.Ticker.return_value = mock_ticker

        results = provider.fetch_all("TEST")

        assert results["fundamentals"].success is True  # empty but valid
        assert results["earnings"].success is False
        assert "lxml" in results["earnings"].error
        assert results["info"].success is True


class TestProviderRateLimiting:
    @patch("margin_engine.ingestion.providers.yfinance_provider.yf")
    def test_rate_limiter_called_per_fetch(self, mock_yf: MagicMock) -> None:
        limiter = MagicMock(spec=RateLimiter)
        provider = YFinanceProvider(rate_limiter=limiter)

        mock_ticker = MagicMock()
        mock_ticker.financials = pd.DataFrame()
        mock_ticker.balance_sheet = pd.DataFrame()
        mock_ticker.cashflow = pd.DataFrame()
        mock_yf.Ticker.return_value = mock_ticker

        provider.fetch_fundamentals("AAPL")

        # Rate limiter should be called once for the fetch
        limiter.wait_and_acquire.assert_called()
```

**Step 2: Run tests to verify new tests fail**

Run: `uv run pytest engine/tests/ingestion/providers/test_yfinance_provider.py -v`
Expected: New tests FAIL (fetch_info, fetch_all, rate limiting don't exist yet)

**Step 3: Implement the refactored provider**

Rewrite `engine/src/margin_engine/ingestion/providers/yfinance_provider.py`:

```python
"""Yahoo Finance data provider via the yfinance library.

This is a free, no-API-key provider that supports fundamentals, price
history, and earnings data.  It serves as a low-priority fallback for
paid providers.
"""

from __future__ import annotations

from datetime import UTC, datetime

import yfinance as yf

from margin_engine.ingestion.rate_limiter import RateLimiter
from margin_engine.ingestion.types import (
    DataCategory,
    DataProvider,
    FetchResult,
    ProviderInfo,
)

_DAYS_TO_PERIOD: list[tuple[int, str]] = [
    (30, "1mo"),
    (90, "3mo"),
    (180, "6mo"),
    (365, "1y"),
    (730, "2y"),
]
"""Mapping thresholds: if *days* <= threshold, use the corresponding yfinance period string."""


def _days_to_period(days: int) -> str:
    """Convert a requested number of days to a yfinance ``period`` parameter."""
    for threshold, period in _DAYS_TO_PERIOD:
        if days <= threshold:
            return period
    return "5y"


def _df_most_recent_column_to_dict(df) -> dict:
    """Extract the first (most recent) column of a DataFrame as a flat dict.

    Returns an empty dict when the DataFrame is empty.
    """
    if df is None or df.empty:
        return {}
    first_col = df.iloc[:, 0]
    return {
        str(k): _safe_scalar(v)
        for k, v in first_col.items()
    }


def _safe_scalar(value):
    """Convert numpy/pandas scalar types to native Python types."""
    try:
        # Handle NaN
        if hasattr(value, "item"):
            return value.item()
        return value
    except (ValueError, TypeError):
        return value


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


class YFinanceProvider(DataProvider):
    """Concrete data provider backed by Yahoo Finance (yfinance library).

    Free, no-API-key provider with moderate rate limits.  Used as a
    fallback when premium providers are unavailable.
    """

    def __init__(self, rate_limiter: RateLimiter | None = None) -> None:
        self._rate_limiter = rate_limiter

    def _acquire_rate_limit(self) -> None:
        """Block until rate limit allows a request."""
        if self._rate_limiter is not None:
            self._rate_limiter.wait_and_acquire()

    @property
    def info(self) -> ProviderInfo:
        return ProviderInfo(
            name="yfinance",
            supported_categories=[
                DataCategory.FUNDAMENTALS,
                DataCategory.PRICE,
                DataCategory.EARNINGS,
            ],
            requests_per_minute=60,
            requires_api_key=False,
            priority=10,
        )

    # ------------------------------------------------------------------
    # Fundamentals
    # ------------------------------------------------------------------

    def fetch_fundamentals(self, ticker: str) -> FetchResult:
        """Fetch income statement, balance sheet, and cash flow.

        Returns the most recent annual period for each statement.
        """
        self._acquire_rate_limit()
        try:
            t = yf.Ticker(ticker)
            raw_data = {
                "income_statement": _df_most_recent_column_to_dict(t.financials),
                "balance_sheet": _df_most_recent_column_to_dict(t.balance_sheet),
                "cash_flow": _df_most_recent_column_to_dict(t.cashflow),
            }
            return FetchResult(
                provider_name=self.info.name,
                category=DataCategory.FUNDAMENTALS,
                ticker=ticker,
                raw_data=raw_data,
                fetched_at=_now_iso(),
            )
        except Exception as exc:
            return FetchResult(
                provider_name=self.info.name,
                category=DataCategory.FUNDAMENTALS,
                ticker=ticker,
                raw_data={},
                fetched_at=_now_iso(),
                success=False,
                error=str(exc),
            )

    # ------------------------------------------------------------------
    # Price history
    # ------------------------------------------------------------------

    def fetch_price_history(self, ticker: str, days: int = 365) -> FetchResult:
        """Fetch OHLCV price bars for the requested look-back window."""
        self._acquire_rate_limit()
        try:
            t = yf.Ticker(ticker)
            period = _days_to_period(days)
            hist = t.history(period=period)

            bars: list[dict] = []
            if hist is not None and not hist.empty:
                # Reset index so date becomes a column
                hist_reset = hist.reset_index()
                bars = hist_reset.to_dict(orient="records")
                # Convert Timestamps and numpy types to JSON-friendly values
                for bar in bars:
                    for key, val in bar.items():
                        if hasattr(val, "isoformat"):
                            bar[key] = val.isoformat()
                        elif hasattr(val, "item"):
                            bar[key] = val.item()

            return FetchResult(
                provider_name=self.info.name,
                category=DataCategory.PRICE,
                ticker=ticker,
                raw_data={"bars": bars},
                fetched_at=_now_iso(),
            )
        except Exception as exc:
            return FetchResult(
                provider_name=self.info.name,
                category=DataCategory.PRICE,
                ticker=ticker,
                raw_data={},
                fetched_at=_now_iso(),
                success=False,
                error=str(exc),
            )

    # ------------------------------------------------------------------
    # Earnings
    # ------------------------------------------------------------------

    def fetch_earnings(self, ticker: str) -> FetchResult:
        """Fetch historical earnings dates with actual/estimated EPS."""
        self._acquire_rate_limit()
        try:
            t = yf.Ticker(ticker)
            df = t.earnings_dates

            earnings: list[dict] = []
            if df is not None and not df.empty:
                for date_idx, row in df.iterrows():
                    entry: dict = {
                        "quarter": str(date_idx),
                    }
                    if "Reported EPS" in row:
                        entry["actual_eps"] = _safe_scalar(row["Reported EPS"])
                    if "EPS Estimate" in row:
                        entry["expected_eps"] = _safe_scalar(row["EPS Estimate"])
                    earnings.append(entry)

            return FetchResult(
                provider_name=self.info.name,
                category=DataCategory.EARNINGS,
                ticker=ticker,
                raw_data={"earnings": earnings},
                fetched_at=_now_iso(),
            )
        except Exception as exc:
            return FetchResult(
                provider_name=self.info.name,
                category=DataCategory.EARNINGS,
                ticker=ticker,
                raw_data={},
                fetched_at=_now_iso(),
                success=False,
                error=str(exc),
            )

    # ------------------------------------------------------------------
    # Info (asset metadata)
    # ------------------------------------------------------------------

    def fetch_info(self, ticker: str) -> FetchResult:
        """Fetch asset metadata (name, sector, country, market cap, etc.)."""
        self._acquire_rate_limit()
        try:
            t = yf.Ticker(ticker)
            info = t.info or {}
            return FetchResult(
                provider_name=self.info.name,
                category=DataCategory.FUNDAMENTALS,  # reuse category
                ticker=ticker,
                raw_data=info,
                fetched_at=_now_iso(),
            )
        except Exception as exc:
            return FetchResult(
                provider_name=self.info.name,
                category=DataCategory.FUNDAMENTALS,
                ticker=ticker,
                raw_data={},
                fetched_at=_now_iso(),
                success=False,
                error=str(exc),
            )

    # ------------------------------------------------------------------
    # Fetch all (single Ticker object, all categories)
    # ------------------------------------------------------------------

    def fetch_all(self, ticker: str, price_days: int = 365) -> dict[str, FetchResult]:
        """Fetch all data categories using a single yf.Ticker instance.

        Reuses one Ticker object to benefit from yfinance's internal caching.
        Each category is fetched independently — a failure in one does not
        block the others.

        Returns a dict keyed by category name: fundamentals, price, earnings, info.
        """
        self._acquire_rate_limit()
        t = yf.Ticker(ticker)

        results: dict[str, FetchResult] = {}

        # Fundamentals
        try:
            raw_data = {
                "income_statement": _df_most_recent_column_to_dict(t.financials),
                "balance_sheet": _df_most_recent_column_to_dict(t.balance_sheet),
                "cash_flow": _df_most_recent_column_to_dict(t.cashflow),
            }
            results["fundamentals"] = FetchResult(
                provider_name=self.info.name,
                category=DataCategory.FUNDAMENTALS,
                ticker=ticker,
                raw_data=raw_data,
                fetched_at=_now_iso(),
            )
        except Exception as exc:
            results["fundamentals"] = FetchResult(
                provider_name=self.info.name,
                category=DataCategory.FUNDAMENTALS,
                ticker=ticker,
                raw_data={},
                fetched_at=_now_iso(),
                success=False,
                error=str(exc),
            )

        # Price
        try:
            period = _days_to_period(price_days)
            hist = t.history(period=period)
            bars: list[dict] = []
            if hist is not None and not hist.empty:
                hist_reset = hist.reset_index()
                bars = hist_reset.to_dict(orient="records")
                for bar in bars:
                    for key, val in bar.items():
                        if hasattr(val, "isoformat"):
                            bar[key] = val.isoformat()
                        elif hasattr(val, "item"):
                            bar[key] = val.item()
            results["price"] = FetchResult(
                provider_name=self.info.name,
                category=DataCategory.PRICE,
                ticker=ticker,
                raw_data={"bars": bars},
                fetched_at=_now_iso(),
            )
        except Exception as exc:
            results["price"] = FetchResult(
                provider_name=self.info.name,
                category=DataCategory.PRICE,
                ticker=ticker,
                raw_data={},
                fetched_at=_now_iso(),
                success=False,
                error=str(exc),
            )

        # Earnings
        try:
            df = t.earnings_dates
            earnings: list[dict] = []
            if df is not None and not df.empty:
                for date_idx, row in df.iterrows():
                    entry: dict = {"quarter": str(date_idx)}
                    if "Reported EPS" in row:
                        entry["actual_eps"] = _safe_scalar(row["Reported EPS"])
                    if "EPS Estimate" in row:
                        entry["expected_eps"] = _safe_scalar(row["EPS Estimate"])
                    earnings.append(entry)
            results["earnings"] = FetchResult(
                provider_name=self.info.name,
                category=DataCategory.EARNINGS,
                ticker=ticker,
                raw_data={"earnings": earnings},
                fetched_at=_now_iso(),
            )
        except Exception as exc:
            results["earnings"] = FetchResult(
                provider_name=self.info.name,
                category=DataCategory.EARNINGS,
                ticker=ticker,
                raw_data={},
                fetched_at=_now_iso(),
                success=False,
                error=str(exc),
            )

        # Info
        try:
            info = t.info or {}
            results["info"] = FetchResult(
                provider_name=self.info.name,
                category=DataCategory.FUNDAMENTALS,
                ticker=ticker,
                raw_data=info,
                fetched_at=_now_iso(),
            )
        except Exception as exc:
            results["info"] = FetchResult(
                provider_name=self.info.name,
                category=DataCategory.FUNDAMENTALS,
                ticker=ticker,
                raw_data={},
                fetched_at=_now_iso(),
                success=False,
                error=str(exc),
            )

        return results
```

**Step 4: Run all provider tests**

Run: `uv run pytest engine/tests/ingestion/providers/test_yfinance_provider.py -v`
Expected: All tests PASS (old and new)

**Step 5: Commit**

```bash
git add engine/src/margin_engine/ingestion/providers/yfinance_provider.py engine/tests/ingestion/providers/test_yfinance_provider.py
git commit -m "feat(engine): refactor YFinanceProvider with fetch_all, fetch_info, rate limiting"
```

---

## Task 6: FMP Provider

**Files:**
- Create: `engine/src/margin_engine/ingestion/providers/fmp_provider.py`
- Create: `engine/tests/ingestion/providers/test_fmp_provider.py`

**Step 1: Add httpx dependency**

Add `"httpx>=0.27"` to `engine/pyproject.toml` dependencies.

Run: `uv sync`

**Step 2: Write failing tests**

Create `engine/tests/ingestion/providers/test_fmp_provider.py`:

```python
"""Tests for the FMP data provider.

All tests mock httpx to avoid real network calls.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from margin_engine.ingestion.providers.fmp_provider import FMPProvider
from margin_engine.ingestion.types import DataCategory, FetchResult


@pytest.fixture
def provider() -> FMPProvider:
    return FMPProvider(api_key="test_key_123")


class TestProviderInfo:
    def test_info(self, provider: FMPProvider) -> None:
        info = provider.info
        assert info.name == "fmp"
        assert DataCategory.FUNDAMENTALS in info.supported_categories
        assert DataCategory.EARNINGS in info.supported_categories
        assert info.requires_api_key is True
        assert info.priority == 5  # lower than yfinance's 10 since it's fallback

    def test_no_api_key_raises(self):
        with pytest.raises(ValueError, match="API key"):
            FMPProvider(api_key="")


class TestFetchFundamentals:
    @patch("margin_engine.ingestion.providers.fmp_provider.httpx")
    def test_success(self, mock_httpx: MagicMock, provider: FMPProvider) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "date": "2024-06-30",
                "revenue": 85777000000,
                "netIncome": 21448000000,
                "operatingIncome": 25370000000,
            }
        ]
        mock_response.raise_for_status = MagicMock()
        mock_httpx.get.return_value = mock_response

        result = provider.fetch_fundamentals("AAPL")

        assert result.success is True
        assert result.provider_name == "fmp"
        assert result.raw_data["income_statement"]["revenue"] == 85777000000

    @patch("margin_engine.ingestion.providers.fmp_provider.httpx")
    def test_api_error(self, mock_httpx: MagicMock, provider: FMPProvider) -> None:
        mock_httpx.get.side_effect = Exception("403 Forbidden")

        result = provider.fetch_fundamentals("BAD")

        assert result.success is False
        assert "403" in result.error


class TestFetchEarnings:
    @patch("margin_engine.ingestion.providers.fmp_provider.httpx")
    def test_success(self, mock_httpx: MagicMock, provider: FMPProvider) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "date": "2024-01-25",
                "eps": 2.18,
                "epsEstimated": 2.10,
                "revenue": 119580000000,
            }
        ]
        mock_response.raise_for_status = MagicMock()
        mock_httpx.get.return_value = mock_response

        result = provider.fetch_earnings("AAPL")

        assert result.success is True
        earnings = result.raw_data["earnings"]
        assert len(earnings) == 1
        assert earnings[0]["actual_eps"] == 2.18
        assert earnings[0]["expected_eps"] == 2.10
```

**Step 3: Run tests to verify they fail**

Run: `uv run pytest engine/tests/ingestion/providers/test_fmp_provider.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 4: Implement FMP provider**

Create `engine/src/margin_engine/ingestion/providers/fmp_provider.py`:

```python
"""Financial Modeling Prep (FMP) data provider.

Paid provider used as fallback when yfinance fails for specific categories.
Requires FMP_API_KEY environment variable.

API docs: https://site.financialmodelingprep.com/developer/docs
"""
from __future__ import annotations

from datetime import UTC, datetime

import httpx

from margin_engine.ingestion.rate_limiter import RateLimiter
from margin_engine.ingestion.types import (
    DataCategory,
    DataProvider,
    FetchResult,
    ProviderInfo,
)

_BASE_URL = "https://financialmodelingprep.com/api/v3"


class FMPProvider(DataProvider):
    """Concrete data provider backed by Financial Modeling Prep API.

    Supports fundamentals and earnings. Used as a fallback when yfinance
    fails for specific data categories.
    """

    def __init__(
        self,
        api_key: str,
        rate_limiter: RateLimiter | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("FMP API key is required")
        self._api_key = api_key
        self._rate_limiter = rate_limiter

    def _acquire_rate_limit(self) -> None:
        if self._rate_limiter is not None:
            self._rate_limiter.wait_and_acquire()

    def _now_iso(self) -> str:
        return datetime.now(UTC).isoformat()

    @property
    def info(self) -> ProviderInfo:
        return ProviderInfo(
            name="fmp",
            supported_categories=[
                DataCategory.FUNDAMENTALS,
                DataCategory.EARNINGS,
            ],
            requests_per_minute=300,
            requires_api_key=True,
            priority=5,
        )

    def fetch_fundamentals(self, ticker: str) -> FetchResult:
        """Fetch income statement from FMP."""
        self._acquire_rate_limit()
        try:
            url = f"{_BASE_URL}/income-statement/{ticker}"
            resp = httpx.get(url, params={"apikey": self._api_key, "limit": 1})
            resp.raise_for_status()
            data = resp.json()

            if not data:
                return FetchResult(
                    provider_name=self.info.name,
                    category=DataCategory.FUNDAMENTALS,
                    ticker=ticker,
                    raw_data={},
                    fetched_at=self._now_iso(),
                    success=False,
                    error="No data returned",
                )

            row = data[0]
            return FetchResult(
                provider_name=self.info.name,
                category=DataCategory.FUNDAMENTALS,
                ticker=ticker,
                raw_data={
                    "income_statement": row,
                    "balance_sheet": {},
                    "cash_flow": {},
                },
                fetched_at=self._now_iso(),
            )
        except Exception as exc:
            return FetchResult(
                provider_name=self.info.name,
                category=DataCategory.FUNDAMENTALS,
                ticker=ticker,
                raw_data={},
                fetched_at=self._now_iso(),
                success=False,
                error=str(exc),
            )

    def fetch_earnings(self, ticker: str) -> FetchResult:
        """Fetch earnings calendar/history from FMP."""
        self._acquire_rate_limit()
        try:
            url = f"{_BASE_URL}/historical/earning_calendar/{ticker}"
            resp = httpx.get(url, params={"apikey": self._api_key, "limit": 25})
            resp.raise_for_status()
            data = resp.json()

            earnings: list[dict] = []
            for row in data:
                entry = {"quarter": row.get("date", "")}
                if "eps" in row and row["eps"] is not None:
                    entry["actual_eps"] = row["eps"]
                if "epsEstimated" in row and row["epsEstimated"] is not None:
                    entry["expected_eps"] = row["epsEstimated"]
                earnings.append(entry)

            return FetchResult(
                provider_name=self.info.name,
                category=DataCategory.EARNINGS,
                ticker=ticker,
                raw_data={"earnings": earnings},
                fetched_at=self._now_iso(),
            )
        except Exception as exc:
            return FetchResult(
                provider_name=self.info.name,
                category=DataCategory.EARNINGS,
                ticker=ticker,
                raw_data={},
                fetched_at=self._now_iso(),
                success=False,
                error=str(exc),
            )
```

**Step 5: Run tests to verify they pass**

Run: `uv run pytest engine/tests/ingestion/providers/test_fmp_provider.py -v`
Expected: All tests PASS

**Step 6: Commit**

```bash
git add engine/pyproject.toml uv.lock engine/src/margin_engine/ingestion/providers/fmp_provider.py engine/tests/ingestion/providers/test_fmp_provider.py
git commit -m "feat(engine): add FMP fallback provider for earnings and fundamentals"
```

---

## Task 7: SeedResult Dataclass + Wire Error Classification into `seed_ticker_data`

This task rewrites `seed_ticker_data` to use `fetch_all`, wire error classification, return a `SeedResult`, and add per-category logging.

**Files:**
- Modify: `api/src/margin_api/cli.py:131-245` (seed_ticker_data)
- Modify: `api/src/margin_api/cli.py:262-321` (run_seed)
- Create: `api/src/margin_api/services/seed_result.py`
- Modify: `api/tests/test_ingestion_service.py` (add integration tests)

**Step 1: Create SeedResult**

Create `api/src/margin_api/services/seed_result.py`:

```python
"""Result type for seed operations."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SeedResult:
    """Rich result from seeding a single ticker."""

    status: str  # "ok", "partial", "failed", "foreign", "skipped"
    categories_succeeded: list[str] = field(default_factory=list)
    categories_failed: list[str] = field(default_factory=list)
    error_message: str | None = None
    provider_used: str = "yfinance"

    @property
    def is_success(self) -> bool:
        return self.status in ("ok", "partial")

    @property
    def data_categories_present(self) -> dict[str, bool]:
        """Category presence map for storage."""
        categories = {}
        for cat in self.categories_succeeded:
            categories[cat] = True
        for cat in self.categories_failed:
            categories[cat] = False
        return categories
```

**Step 2: Rewrite `seed_ticker_data` in `cli.py`**

Replace `seed_ticker_data` (lines 131-245) with a version that:
- Uses `provider.fetch_all()` instead of 4 separate calls
- Extracts info from the fetch_all results (no direct yfinance import)
- Logs per-category status
- Returns `SeedResult` instead of `str`
- Calls `classify_error` and `update_failure_status` on failure

Key changes to `cli.py`:
- Add imports: `from margin_api.services.seed_result import SeedResult`
- Add imports: `from margin_api.services.ingestion import classify_error, should_ingest_ticker, update_failure_status`
- Remove: `import yfinance` (no longer used directly)
- Replace `seed_ticker_data` function body
- Update `run_seed` loop to use `SeedResult` and call `should_ingest_ticker`

The full implementation is long — the executor should modify `cli.py` to:

1. Replace `seed_ticker_data` signature: return `SeedResult` instead of `str`
2. Call `provider.fetch_all(ticker)` to get all results from one Ticker object
3. Extract info from `results["info"].raw_data` instead of calling `yfinance.Ticker(ticker).info`
4. Log each category: `fundamentals=ok price=ok earnings=FAIL(error) info=ok`
5. On exception: call `classify_error(exc)` and `update_failure_status(session, asset, ...)`
6. Return `SeedResult(status="ok"|"partial"|"failed", categories_succeeded=[...], categories_failed=[...])`

In `run_seed`:
1. Before seeding, pre-fetch asset to check `should_ingest_ticker()`
2. Replace `if result == "ok"` with `if result.status == "ok"` etc.
3. Track `partial_count` alongside `successes` and `failures`
4. Remove the per-ticker rate limiter gate (provider handles it internally now)

**Step 3: Run existing tests**

Run: `uv run pytest api/tests/ -v -k "ingest"`
Expected: All existing tests PASS (the service tests don't touch cli.py)

**Step 4: Commit**

```bash
git add api/src/margin_api/services/seed_result.py api/src/margin_api/cli.py
git commit -m "feat(api): wire error classification into seed flow, add SeedResult, per-category logging"
```

---

## Task 8: Extend DB Models for Observability

**Files:**
- Modify: `api/src/margin_api/db/models.py:47-66` (IngestionRun)
- Modify: `api/src/margin_api/db/models.py:114-137` (FinancialData)

**Step 1: Add fields to IngestionRun**

Add these columns to the `IngestionRun` model (after line 62):

```python
    tickers_partial: Mapped[int] = mapped_column(default=0)
    provider_stats: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
    circuit_breaker_trips: Mapped[int] = mapped_column(default=0)
```

**Step 2: Add `data_categories_present` to FinancialData**

Add after `earnings_data` (line 127):

```python
    data_categories_present: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
```

**Step 3: Generate and apply migration**

Note for executor: this project uses SQLAlchemy with alembic. Check if alembic is configured:
- Run: `ls api/alembic/` or `ls api/migrations/`
- If no migrations directory, the models are created via `Base.metadata.create_all()` — just update the models and Railway will pick them up on next deploy (or use `--drop-tables` flag if available).

**Step 4: Run tests to verify models work**

Run: `uv run pytest api/tests/test_ingestion_service.py -v`
Expected: All PASS (tests use `create_all` with in-memory SQLite)

**Step 5: Commit**

```bash
git add api/src/margin_api/db/models.py
git commit -m "feat(api): extend IngestionRun and FinancialData models for observability"
```

---

## Task 9: Wire Changes into ARQ Worker

**Files:**
- Modify: `api/src/margin_api/workers.py:40-151` (full_ingest)

**Step 1: Update `full_ingest` to use new seed flow**

Update `workers.py:full_ingest` to:
1. Create `YFinanceProvider(rate_limiter=limiter)` — pass rate limiter to provider
2. Remove the per-ticker `limiter.wait_and_acquire()` call (provider handles it)
3. Handle `SeedResult` return type from `seed_ticker_data`
4. Track `partial_count`, `provider_stats`, `circuit_breaker_trips`
5. Write `IngestionTickerStatus` rows with `data_fetched` JSONB
6. Update `IngestionRun` with new fields
7. Add threshold-based alerting log at end of run

**Step 2: Add alerting helper**

Add to `workers.py` after the imports:

```python
def _log_run_alerts(
    total: int, succeeded: int, failed: int, partial: int, cb_trips: int,
) -> None:
    """Log alerts based on run outcome thresholds."""
    if total == 0:
        return
    fail_rate = failed / total
    partial_rate = partial / total

    if fail_rate > 0.20:
        logger.error(
            "[ingest] ALERT: %.0f%% of tickers failed (%d/%d)",
            fail_rate * 100, failed, total,
        )
    if partial_rate > 0.10:
        logger.warning(
            "[ingest] ALERT: %.0f%% of tickers had partial data (%d/%d)",
            partial_rate * 100, partial, total,
        )
    if cb_trips > 0:
        logger.warning(
            "[ingest] ALERT: Circuit breaker tripped %d time(s) during run",
            cb_trips,
        )
```

**Step 3: Run tests**

Run: `uv run pytest api/tests/ -v`
Expected: All PASS

**Step 4: Commit**

```bash
git add api/src/margin_api/workers.py
git commit -m "feat(api): wire resilient ingestion into ARQ worker with alerting"
```

---

## Task 10: Quarantine Review Endpoint

**Files:**
- Modify: `api/src/margin_api/routes/admin.py`
- Create: `api/tests/routes/test_admin_quarantine.py`

**Step 1: Write failing test**

Create `api/tests/routes/test_admin_quarantine.py`:

```python
"""Tests for the quarantine review endpoint."""
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from margin_api.app import create_app


@pytest.mark.asyncio
async def test_quarantined_endpoint_returns_quarantined_assets(
    test_app_with_db,
):
    """GET /api/v1/admin/ingestion/quarantined returns assets with
    ingestion_status in ('quarantined', 'permanently_skipped')."""
    # This test depends on the test_app_with_db fixture seeding
    # a quarantined asset. The executor should check existing test
    # fixtures and adapt accordingly.
    pass  # Executor fills in based on existing test patterns
```

**Step 2: Add endpoint to admin.py**

Add to `api/src/margin_api/routes/admin.py`:

```python
@router.get("/ingestion/quarantined")
async def get_quarantined_assets(
    x_admin_key: str = Header(),
    session: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Return all quarantined and permanently skipped assets."""
    _verify_admin_key(x_admin_key)

    from margin_api.db.models import Asset

    result = await session.execute(
        select(Asset)
        .where(Asset.ingestion_status.in_(["quarantined", "permanently_skipped"]))
        .order_by(Asset.ticker)
    )
    assets = result.scalars().all()

    return [
        {
            "ticker": a.ticker,
            "name": a.name,
            "ingestion_status": a.ingestion_status,
            "consecutive_failures": a.consecutive_failures,
            "last_failure_reason": a.last_failure_reason,
            "quarantined_at": a.quarantined_at.isoformat() if a.quarantined_at else None,
            "last_retry_at": a.last_retry_at.isoformat() if a.last_retry_at else None,
        }
        for a in assets
    ]
```

Add `from sqlalchemy import select` to the imports if not already present.

**Step 3: Run tests**

Run: `uv run pytest api/tests/ -v`
Expected: All PASS

**Step 4: Commit**

```bash
git add api/src/margin_api/routes/admin.py api/tests/routes/test_admin_quarantine.py
git commit -m "feat(api): add GET /admin/ingestion/quarantined endpoint"
```

---

## Task 11: Update `__init__.py` Exports

**Files:**
- Modify: `engine/src/margin_engine/ingestion/__init__.py`

**Step 1: Add new exports**

Update `engine/src/margin_engine/ingestion/__init__.py` to export new modules:

```python
from margin_engine.ingestion.circuit_breaker import CircuitBreaker, CircuitState
from margin_engine.ingestion.retry import retry_transient
from margin_engine.ingestion.symbol_mapper import SymbolMapper
```

Add them to `__all__` as well.

**Step 2: Run all engine tests**

Run: `uv run pytest engine/tests/ -v`
Expected: All PASS

**Step 3: Commit**

```bash
git add engine/src/margin_engine/ingestion/__init__.py
git commit -m "feat(engine): export circuit breaker, retry, and symbol mapper from ingestion package"
```

---

## Task 12: Integration Test — Full Pipeline with Mocked Providers

**Files:**
- Create: `api/tests/test_resilient_ingestion.py`

**Step 1: Write integration tests**

Create `api/tests/test_resilient_ingestion.py`:

```python
"""Integration tests for the resilient ingestion pipeline.

Tests the full flow: seed_ticker_data with mocked yfinance, error
classification wiring, partial success, and SeedResult.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
import pytest_asyncio
from margin_api.db.base import Base
from margin_api.db.models import Asset, FinancialData
from margin_api.services.seed_result import SeedResult
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest_asyncio.fixture()
async def async_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture()
async def session(async_engine):
    factory = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as sess:
        yield sess


class TestSeedTickerDataIntegration:
    @pytest.mark.asyncio
    async def test_successful_seed_returns_ok(self, session):
        """Full successful seed returns SeedResult with status='ok'."""
        # Executor: mock YFinanceProvider.fetch_all to return all-success results
        # Call seed_ticker_data and assert result.status == "ok"
        # Verify Asset and FinancialData rows created
        pass

    @pytest.mark.asyncio
    async def test_partial_seed_returns_partial(self, session):
        """Seed with earnings failure returns SeedResult with status='partial'."""
        # Executor: mock fetch_all with earnings failing
        # Assert result.status == "partial"
        # Assert "earnings" in result.categories_failed
        # Verify FinancialData.earnings_data is None
        # Verify FinancialData.data_categories_present shows earnings=False
        pass

    @pytest.mark.asyncio
    async def test_permanent_error_marks_permanently_skipped(self, session):
        """Seed that raises permanent error updates asset status."""
        # Executor: mock to raise ValueError("Ticker not found")
        # Assert result.status == "failed"
        # Assert asset.ingestion_status == "permanently_skipped"
        pass

    @pytest.mark.asyncio
    async def test_quarantined_ticker_skipped(self, session):
        """Quarantined ticker within 7 days is skipped."""
        # Executor: create asset with ingestion_status="quarantined"
        # Call seed and assert it returns SeedResult(status="skipped")
        pass
```

Note: These tests are intentionally stubbed — the executor should fill in the mock setup based on the final `seed_ticker_data` implementation from Task 7.

**Step 2: Run tests**

Run: `uv run pytest api/tests/test_resilient_ingestion.py -v`
Expected: All PASS (once executor fills in implementations)

**Step 3: Commit**

```bash
git add api/tests/test_resilient_ingestion.py
git commit -m "test(api): add integration tests for resilient ingestion pipeline"
```

---

## Task 13: Final Verification

**Step 1: Run all engine tests**

Run: `uv run pytest engine/tests/ -v`
Expected: All PASS (784+ tests)

**Step 2: Run all API tests**

Run: `uv run pytest api/tests/ -v`
Expected: All PASS (294+ tests)

**Step 3: Verify lxml fixes earnings locally**

Run: `uv run python -c "import yfinance; t = yfinance.Ticker('FSLR'); print(len(t.earnings_dates), 'earnings dates for FSLR')"`
Expected: `25 earnings dates for FSLR`

**Step 4: Final commit (if any cleanup needed)**

```bash
git add -A
git commit -m "chore: final cleanup for resilient ingestion pipeline"
```
