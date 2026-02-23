# Resilient Ingestion Pipeline Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix systematic ingestion failures (incorrect delisting, missing lxml, rate limiting) by implementing circuit breakers, retry logic, FMP fallback provider, and proper ticker skip/resume logic.

**Architecture:** Per-request rate limiting in providers, circuit breaker state machine per provider, exponential backoff retry for transient errors, FMP as fallback for failed yfinance categories, IngestionTickerStatus audit trail per ticker per run.

**Tech Stack:** Python 3.13, yfinance, httpx (for FMP), pydantic, SQLAlchemy 2.0, pytest

**Design doc:** `docs/plans/2026-02-21-resilient-ingestion-pipeline-design.md`

**Already implemented (do NOT re-implement):**
- lxml dependency in engine/pyproject.toml
- `YFinanceProvider.fetch_all()` reuses single `yf.Ticker` instance
- `SeedResult` dataclass with categories tracking (`api/src/margin_api/services/seed_result.py`)
- Error classification wiring in `seed_ticker_data` (calls `classify_error` + `update_failure_status`)
- Per-category logging in `seed_ticker_data`
- `IngestionRun` model has `tickers_partial`, `provider_stats`, `circuit_breaker_trips`
- `IngestionTickerStatus` model exists in DB (but not populated yet)
- `_log_run_alerts()` alerting in `workers.py`
- `GET /admin/ingestion/quarantined` endpoint
- Tests: SeedResult, classify_error, should_ingest_ticker, update_failure_status, alerting

---

## Task 1: Per-Request Rate Limiting in YFinanceProvider

Currently `fetch_all()` calls `_acquire_rate_limit()` once at the top (line 260). yfinance makes 4+ HTTP calls internally. The rate limiter gates once per ticker but the effective rate is 4-5x higher.

**Files:**
- Modify: `engine/src/margin_engine/ingestion/providers/yfinance_provider.py:249-376`
- Test: `engine/tests/ingestion/test_yfinance_rate_limit.py`

**Step 1: Write the failing test**

```python
"""Tests for per-request rate limiting in YFinanceProvider.fetch_all."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from margin_engine.ingestion.providers.yfinance_provider import YFinanceProvider
from margin_engine.ingestion.rate_limiter import RateLimiter


class TestFetchAllRateLimiting:
    def test_fetch_all_acquires_rate_limit_per_section(self):
        """fetch_all should acquire rate limit before each section, not just once."""
        limiter = MagicMock(spec=RateLimiter)
        provider = YFinanceProvider(rate_limiter=limiter)

        with patch("margin_engine.ingestion.providers.yfinance_provider.yf") as mock_yf:
            mock_ticker = MagicMock()
            mock_ticker.financials = MagicMock(empty=True)
            mock_ticker.balance_sheet = MagicMock(empty=True)
            mock_ticker.cashflow = MagicMock(empty=True)
            mock_ticker.history.return_value = MagicMock(empty=True)
            mock_ticker.earnings_dates = None
            mock_ticker.info = {}
            mock_yf.Ticker.return_value = mock_ticker

            provider.fetch_all("AAPL")

        # Should be called 4 times: fundamentals, price, earnings, info
        assert limiter.wait_and_acquire.call_count == 4

    def test_fetch_all_without_limiter_still_works(self):
        """fetch_all with no limiter should work (no gating)."""
        provider = YFinanceProvider(rate_limiter=None)

        with patch("margin_engine.ingestion.providers.yfinance_provider.yf") as mock_yf:
            mock_ticker = MagicMock()
            mock_ticker.financials = MagicMock(empty=True)
            mock_ticker.balance_sheet = MagicMock(empty=True)
            mock_ticker.cashflow = MagicMock(empty=True)
            mock_ticker.history.return_value = MagicMock(empty=True)
            mock_ticker.earnings_dates = None
            mock_ticker.info = {}
            mock_yf.Ticker.return_value = mock_ticker

            results = provider.fetch_all("AAPL")

        assert "fundamentals" in results
        assert "price" in results
        assert "earnings" in results
        assert "info" in results
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest engine/tests/ingestion/test_yfinance_rate_limit.py -v`
Expected: FAIL — `test_fetch_all_acquires_rate_limit_per_section` fails because `wait_and_acquire` is only called once.

**Step 3: Implement per-section rate limiting**

In `yfinance_provider.py`, modify `fetch_all()`:
- Remove the single `self._acquire_rate_limit()` call at line 260
- Add `self._acquire_rate_limit()` inside each section's try block (before accessing yfinance data)

```python
def fetch_all(self, ticker: str, price_days: int = 365) -> dict[str, FetchResult]:
    t = yf.Ticker(ticker)
    results: dict[str, FetchResult] = {}

    # --- fundamentals ---
    self._acquire_rate_limit()  # <-- gate before fundamentals
    try:
        raw_fundamentals = { ... }
        ...

    # --- price ---
    self._acquire_rate_limit()  # <-- gate before price
    try:
        ...

    # --- earnings ---
    self._acquire_rate_limit()  # <-- gate before earnings
    try:
        ...

    # --- info ---
    self._acquire_rate_limit()  # <-- gate before info
    try:
        ...

    return results
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest engine/tests/ingestion/test_yfinance_rate_limit.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add engine/src/margin_engine/ingestion/providers/yfinance_provider.py engine/tests/ingestion/test_yfinance_rate_limit.py
git commit -m "fix(ingestion): per-request rate limiting in fetch_all (4 gates instead of 1)"
```

---

## Task 2: Wire should_ingest_ticker Into Seed Loops

`should_ingest_ticker()` exists in `ingestion.py` but is never called before `seed_ticker_data` in `run_seed` (cli.py) or `full_ingest` (workers.py). Quarantined/permanently-skipped tickers waste API calls.

**Files:**
- Modify: `api/src/margin_api/cli.py:352-425` (run_seed)
- Modify: `api/src/margin_api/workers.py:82-207` (full_ingest)
- Test: `api/tests/test_should_ingest_wiring.py`

**Step 1: Write the failing test**

```python
"""Tests for should_ingest_ticker wiring in run_seed and full_ingest."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestRunSeedSkipsQuarantined:
    @pytest.mark.asyncio
    async def test_run_seed_skips_permanently_skipped_ticker(self):
        """run_seed should skip tickers with ingestion_status='permanently_skipped'."""
        from margin_api.cli import run_seed

        # Mock the session factory to return a session with a permanently_skipped asset
        mock_engine = MagicMock()
        mock_session_factory = MagicMock()
        mock_session = AsyncMock()

        # Asset with permanently_skipped status
        asset = MagicMock()
        asset.ingestion_status = "permanently_skipped"
        asset.consecutive_failures = 10
        asset.last_retry_at = None

        asset_result = MagicMock()
        asset_result.scalar_one_or_none.return_value = asset
        mock_session.execute.return_value = asset_result

        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__.return_value = mock_session
        mock_session_ctx.__aexit__.return_value = None
        mock_session_factory.return_value = mock_session_ctx

        with (
            patch("margin_api.cli.get_engine", return_value=mock_engine),
            patch("margin_api.cli.get_session_factory", return_value=mock_session_factory),
            patch("margin_api.cli._load_foreign_skips", return_value=set()),
            patch("margin_api.cli.seed_ticker_data") as mock_seed,
        ):
            await run_seed(tickers=["DLST"])

        # seed_ticker_data should NOT have been called
        mock_seed.assert_not_called()
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/test_should_ingest_wiring.py -v`
Expected: FAIL — `seed_ticker_data` is called because there's no skip check.

**Step 3: Implement skip check in run_seed and full_ingest**

In `cli.py:run_seed`, before calling `seed_ticker_data`, pre-fetch the asset and check:

```python
from margin_api.services.ingestion import should_ingest_ticker

# Inside the for loop, before seed_ticker_data:
async with session_factory() as session:
    # Check if ticker should be ingested
    asset_check = await session.execute(select(Asset).where(Asset.ticker == ticker))
    existing_asset = asset_check.scalar_one_or_none()
    if existing_asset and not should_ingest_ticker(
        existing_asset.ingestion_status,
        existing_asset.consecutive_failures,
        existing_asset.last_retry_at,
    ):
        logger.info("  %s SKIPPED (status=%s)", ticker, existing_asset.ingestion_status)
        continue

async with session_factory() as session:
    result = await seed_ticker_data(...)
```

Apply the same pattern in `workers.py:full_ingest`. Add a `skipped_count` counter and log it.

**Step 4: Run test to verify it passes**

Run: `uv run pytest api/tests/test_should_ingest_wiring.py -v`
Expected: PASS

**Step 5: Run all existing tests**

Run: `uv run pytest api/tests/ -v --tb=short -q`
Expected: All pass (no regressions)

**Step 6: Commit**

```bash
git add api/src/margin_api/cli.py api/src/margin_api/workers.py api/tests/test_should_ingest_wiring.py
git commit -m "feat(ingestion): wire should_ingest_ticker to skip quarantined/permanent tickers"
```

---

## Task 3: Circuit Breaker State Machine

New file implementing circuit breaker per provider with states: closed (normal) → open (tripped) → half-open (probe).

**Files:**
- Create: `engine/src/margin_engine/ingestion/circuit_breaker.py`
- Create: `engine/tests/ingestion/test_circuit_breaker.py`

**Step 1: Write the failing tests**

```python
"""Tests for circuit breaker state machine."""

from __future__ import annotations

import time

from margin_engine.ingestion.circuit_breaker import CircuitBreaker


class TestCircuitBreakerClosedState:
    def test_starts_closed(self):
        cb = CircuitBreaker(failure_threshold=3, cooldown_seconds=10)
        assert cb.state == "closed"
        assert cb.allow_request() is True

    def test_single_failure_stays_closed(self):
        cb = CircuitBreaker(failure_threshold=3, cooldown_seconds=10)
        cb.record_failure()
        assert cb.state == "closed"
        assert cb.allow_request() is True

    def test_success_resets_failure_count(self):
        cb = CircuitBreaker(failure_threshold=3, cooldown_seconds=10)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        assert cb.consecutive_failures == 0
        assert cb.state == "closed"


class TestCircuitBreakerOpenState:
    def test_trips_after_threshold_failures(self):
        cb = CircuitBreaker(failure_threshold=3, cooldown_seconds=10)
        cb.record_failure()
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "open"
        assert cb.allow_request() is False

    def test_open_rejects_all_requests(self):
        cb = CircuitBreaker(failure_threshold=3, cooldown_seconds=10)
        for _ in range(3):
            cb.record_failure()
        # Multiple checks should all be rejected
        for _ in range(5):
            assert cb.allow_request() is False


class TestCircuitBreakerHalfOpenState:
    def test_transitions_to_half_open_after_cooldown(self):
        cb = CircuitBreaker(failure_threshold=3, cooldown_seconds=0.1)
        for _ in range(3):
            cb.record_failure()
        assert cb.state == "open"

        time.sleep(0.15)
        assert cb.allow_request() is True  # probe request
        assert cb.state == "half_open"

    def test_half_open_success_returns_to_closed(self):
        cb = CircuitBreaker(failure_threshold=3, cooldown_seconds=0.1)
        for _ in range(3):
            cb.record_failure()
        time.sleep(0.15)
        cb.allow_request()  # transitions to half_open
        cb.record_success()
        assert cb.state == "closed"
        assert cb.consecutive_failures == 0

    def test_half_open_failure_returns_to_open(self):
        cb = CircuitBreaker(failure_threshold=3, cooldown_seconds=0.1)
        for _ in range(3):
            cb.record_failure()
        time.sleep(0.15)
        cb.allow_request()  # transitions to half_open
        cb.record_failure()
        assert cb.state == "open"


class TestCircuitBreakerTripCount:
    def test_trip_count_increments_on_each_trip(self):
        cb = CircuitBreaker(failure_threshold=2, cooldown_seconds=0.1)
        cb.record_failure()
        cb.record_failure()
        assert cb.trip_count == 1

        time.sleep(0.15)
        cb.allow_request()  # half_open
        cb.record_failure()  # back to open
        assert cb.trip_count == 2
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest engine/tests/ingestion/test_circuit_breaker.py -v`
Expected: FAIL — module not found

**Step 3: Implement circuit breaker**

```python
"""Circuit breaker state machine for provider health tracking.

States:
    closed  — Normal operation, requests flow through
    open    — Tripped, all requests rejected until cooldown
    half_open — After cooldown, allow one probe request
"""

from __future__ import annotations

import time
import threading


class CircuitBreaker:
    """Per-provider circuit breaker with configurable thresholds."""

    def __init__(
        self,
        failure_threshold: int = 10,
        cooldown_seconds: float = 900.0,  # 15 minutes
    ) -> None:
        self._failure_threshold = failure_threshold
        self._cooldown_seconds = cooldown_seconds
        self._consecutive_failures = 0
        self._state = "closed"
        self._opened_at: float | None = None
        self._trip_count = 0
        self._lock = threading.Lock()

    @property
    def state(self) -> str:
        with self._lock:
            if self._state == "open" and self._opened_at is not None:
                if time.monotonic() - self._opened_at >= self._cooldown_seconds:
                    return "half_open"
            return self._state

    @property
    def consecutive_failures(self) -> int:
        with self._lock:
            return self._consecutive_failures

    @property
    def trip_count(self) -> int:
        with self._lock:
            return self._trip_count

    def allow_request(self) -> bool:
        with self._lock:
            if self._state == "closed":
                return True
            if self._state == "open":
                if self._opened_at is not None and (
                    time.monotonic() - self._opened_at >= self._cooldown_seconds
                ):
                    self._state = "half_open"
                    return True
                return False
            if self._state == "half_open":
                return False  # Only one probe allowed
            return True

    def record_success(self) -> None:
        with self._lock:
            self._consecutive_failures = 0
            self._state = "closed"
            self._opened_at = None

    def record_failure(self) -> None:
        with self._lock:
            self._consecutive_failures += 1
            if self._state == "half_open":
                self._state = "open"
                self._opened_at = time.monotonic()
                self._trip_count += 1
            elif self._consecutive_failures >= self._failure_threshold:
                if self._state != "open":
                    self._state = "open"
                    self._opened_at = time.monotonic()
                    self._trip_count += 1
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest engine/tests/ingestion/test_circuit_breaker.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add engine/src/margin_engine/ingestion/circuit_breaker.py engine/tests/ingestion/test_circuit_breaker.py
git commit -m "feat(ingestion): add circuit breaker state machine per provider"
```

---

## Task 4: Retry Decorator With Exponential Backoff

Decorator for transient-error retry on provider fetch methods.

**Files:**
- Create: `engine/src/margin_engine/ingestion/retry.py`
- Create: `engine/tests/ingestion/test_retry.py`

**Step 1: Write the failing tests**

```python
"""Tests for retry with exponential backoff."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from margin_engine.ingestion.retry import retry_transient


class TestRetryTransient:
    def test_succeeds_on_first_try(self):
        call_count = 0

        @retry_transient(max_retries=3, base_delay=0.01)
        def always_succeeds():
            nonlocal call_count
            call_count += 1
            return "ok"

        assert always_succeeds() == "ok"
        assert call_count == 1

    def test_retries_on_transient_error(self):
        call_count = 0

        @retry_transient(max_retries=3, base_delay=0.01)
        def fails_then_succeeds():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("timeout")
            return "ok"

        assert fails_then_succeeds() == "ok"
        assert call_count == 3

    def test_raises_after_max_retries(self):
        @retry_transient(max_retries=3, base_delay=0.01)
        def always_fails():
            raise ConnectionError("timeout")

        with pytest.raises(ConnectionError, match="timeout"):
            always_fails()

    def test_does_not_retry_non_transient_error(self):
        call_count = 0

        @retry_transient(max_retries=3, base_delay=0.01)
        def raises_value_error():
            nonlocal call_count
            call_count += 1
            raise ValueError("Ticker not found")

        with pytest.raises(ValueError, match="not found"):
            raises_value_error()
        assert call_count == 1  # no retry

    def test_retries_on_429_rate_limit(self):
        call_count = 0

        @retry_transient(max_retries=3, base_delay=0.01)
        def rate_limited():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("429 Too Many Requests")
            return "ok"

        assert rate_limited() == "ok"
        assert call_count == 2
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest engine/tests/ingestion/test_retry.py -v`
Expected: FAIL — module not found

**Step 3: Implement retry decorator**

```python
"""Retry decorator with exponential backoff for transient errors."""

from __future__ import annotations

import functools
import logging
import time

from margin_api.services.ingestion import classify_error

logger = logging.getLogger(__name__)

# Classify transient errors without importing from api package
_TRANSIENT_TYPES = (TimeoutError, ConnectionError, OSError)
_TRANSIENT_KEYWORDS = {"429", "rate limit", "too many requests", "503", "502", "500"}


def _is_transient(exc: Exception) -> bool:
    """Check if an exception is transient (worth retrying)."""
    if isinstance(exc, _TRANSIENT_TYPES):
        return True
    msg = str(exc).lower()
    return any(kw in msg for kw in _TRANSIENT_KEYWORDS)


def retry_transient(
    max_retries: int = 3,
    base_delay: float = 2.0,
):
    """Decorator: retry on transient errors with exponential backoff.

    Non-transient errors (permanent, data_unavailable) are raised immediately.

    Args:
        max_retries: Maximum number of retry attempts.
        base_delay: Base delay in seconds (doubled each retry).
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exc: Exception | None = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as exc:
                    if not _is_transient(exc):
                        raise
                    last_exc = exc
                    if attempt < max_retries:
                        delay = base_delay * (2 ** attempt)
                        logger.info(
                            "Retry %d/%d for %s after %.1fs: %s",
                            attempt + 1,
                            max_retries,
                            func.__name__,
                            delay,
                            exc,
                        )
                        time.sleep(delay)
            raise last_exc  # type: ignore[misc]

        return wrapper

    return decorator
```

Note: The `_is_transient()` check is self-contained (no cross-package import) — it duplicates the transient-check logic from `classify_error` to keep the engine package independent of the api package.

**Step 4: Run tests to verify they pass**

Run: `uv run pytest engine/tests/ingestion/test_retry.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add engine/src/margin_engine/ingestion/retry.py engine/tests/ingestion/test_retry.py
git commit -m "feat(ingestion): add retry decorator with exponential backoff for transient errors"
```

---

## Task 5: Run-Level Resume (Skip Already-Seeded Tickers)

Before fetching, check if `FinancialData` already exists with today's `period_end`. If so, skip — no API calls needed. Makes the pipeline idempotent and resumable.

**Files:**
- Modify: `api/src/margin_api/cli.py` (seed_ticker_data or run_seed)
- Test: `api/tests/test_run_resume.py`

**Step 1: Write the failing test**

```python
"""Tests for run-level resume — skip tickers already seeded today."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestRunLevelResume:
    @pytest.mark.asyncio
    async def test_skips_ticker_already_seeded_today(self):
        """run_seed skips ticker that has FinancialData with today's period_end."""
        from margin_api.cli import run_seed

        mock_engine = MagicMock()
        mock_session_factory = MagicMock()
        mock_session = AsyncMock()

        # First execute: check should_ingest_ticker — no asset yet (new ticker)
        no_asset_result = MagicMock()
        no_asset_result.scalar_one_or_none.return_value = None

        # Second execute: check resume — FinancialData exists for today
        today_iso = datetime.now(UTC).strftime("%Y-%m-%d")
        resume_result = MagicMock()
        resume_result.scalar_one_or_none.return_value = MagicMock(period_end=today_iso)

        mock_session.execute.side_effect = [no_asset_result, resume_result]

        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__.return_value = mock_session
        mock_session_ctx.__aexit__.return_value = None
        mock_session_factory.return_value = mock_session_ctx

        with (
            patch("margin_api.cli.get_engine", return_value=mock_engine),
            patch("margin_api.cli.get_session_factory", return_value=mock_session_factory),
            patch("margin_api.cli._load_foreign_skips", return_value=set()),
            patch("margin_api.cli.seed_ticker_data") as mock_seed,
        ):
            await run_seed(tickers=["AAPL"])

        mock_seed.assert_not_called()
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/test_run_resume.py -v`
Expected: FAIL — seed_ticker_data gets called

**Step 3: Implement resume check in run_seed**

In `cli.py:run_seed`, after the `should_ingest_ticker` check and before `seed_ticker_data`:

```python
from margin_api.db.models import Asset, FinancialData

# Check resume: does today's data already exist?
today_iso = datetime.now(UTC).strftime("%Y-%m-%d")
resume_check = await session.execute(
    select(FinancialData)
    .join(Asset, FinancialData.asset_id == Asset.id)
    .where(Asset.ticker == ticker, FinancialData.period_end == today_iso)
    .limit(1)
)
if resume_check.scalar_one_or_none() is not None:
    logger.info("  %s SKIPPED (already seeded today)", ticker)
    continue
```

Apply in both `run_seed` and `full_ingest`.

**Step 4: Run tests**

Run: `uv run pytest api/tests/test_run_resume.py api/tests/ -v --tb=short -q`
Expected: All pass

**Step 5: Commit**

```bash
git add api/src/margin_api/cli.py api/src/margin_api/workers.py api/tests/test_run_resume.py
git commit -m "feat(ingestion): run-level resume — skip tickers already seeded today"
```

---

## Task 6: FMP Provider Implementation

New provider for Financial Modeling Prep API as fallback for failed yfinance categories.

**Files:**
- Create: `engine/src/margin_engine/ingestion/providers/fmp_provider.py`
- Create: `engine/tests/ingestion/test_fmp_provider.py`

**Step 1: Write the failing tests**

```python
"""Tests for FMP data provider."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from margin_engine.ingestion.types import DataCategory


class TestFMPProviderInfo:
    def test_provider_info(self):
        from margin_engine.ingestion.providers.fmp_provider import FMPProvider

        provider = FMPProvider(api_key="test_key")
        info = provider.info
        assert info.name == "fmp"
        assert DataCategory.FUNDAMENTALS in info.supported_categories
        assert DataCategory.EARNINGS in info.supported_categories
        assert DataCategory.PRICE in info.supported_categories
        assert info.requires_api_key is True
        assert info.priority == 20  # higher than yfinance (10)

    def test_no_api_key_raises(self):
        from margin_engine.ingestion.providers.fmp_provider import FMPProvider

        with pytest.raises(ValueError, match="FMP_API_KEY"):
            FMPProvider(api_key="")


class TestFMPFetchFundamentals:
    def test_fetch_fundamentals_success(self):
        from margin_engine.ingestion.providers.fmp_provider import FMPProvider

        provider = FMPProvider(api_key="test_key")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "revenue": 394328000000,
                "grossProfit": 170782000000,
                "operatingIncome": 114301000000,
                "netIncome": 96995000000,
            }
        ]

        with patch("httpx.get", return_value=mock_response):
            result = provider.fetch_fundamentals("AAPL")

        assert result.success is True
        assert result.provider_name == "fmp"
        assert result.category == DataCategory.FUNDAMENTALS
        assert "income_statement" in result.raw_data

    def test_fetch_fundamentals_api_error(self):
        from margin_engine.ingestion.providers.fmp_provider import FMPProvider

        provider = FMPProvider(api_key="test_key")

        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Invalid API key"
        mock_response.raise_for_status.side_effect = Exception("401 Unauthorized")

        with patch("httpx.get", return_value=mock_response):
            result = provider.fetch_fundamentals("AAPL")

        assert result.success is False


class TestFMPFetchEarnings:
    def test_fetch_earnings_success(self):
        from margin_engine.ingestion.providers.fmp_provider import FMPProvider

        provider = FMPProvider(api_key="test_key")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "date": "2024-01-25",
                "eps": 2.18,
                "epsEstimated": 2.10,
                "revenue": 119575000000,
            }
        ]

        with patch("httpx.get", return_value=mock_response):
            result = provider.fetch_earnings("AAPL")

        assert result.success is True
        assert result.category == DataCategory.EARNINGS
        earnings = result.raw_data.get("earnings", [])
        assert len(earnings) == 1
        assert earnings[0]["actual_eps"] == 2.18


class TestFMPFetchPriceHistory:
    def test_fetch_price_history_success(self):
        from margin_engine.ingestion.providers.fmp_provider import FMPProvider

        provider = FMPProvider(api_key="test_key")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "historical": [
                {
                    "date": "2024-01-25",
                    "open": 150.0,
                    "high": 155.0,
                    "low": 149.0,
                    "close": 153.0,
                    "volume": 5000000,
                }
            ]
        }

        with patch("httpx.get", return_value=mock_response):
            result = provider.fetch_price_history("AAPL", days=30)

        assert result.success is True
        assert result.category == DataCategory.PRICE
        bars = result.raw_data.get("bars", [])
        assert len(bars) == 1
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest engine/tests/ingestion/test_fmp_provider.py -v`
Expected: FAIL — module not found

**Step 3: Implement FMP provider**

```python
"""Financial Modeling Prep (FMP) data provider.

Paid/free-tier provider used as fallback for failed yfinance categories.
Requires FMP_API_KEY environment variable.
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


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


class FMPProvider(DataProvider):
    """FMP data provider for fundamentals, earnings, and price history."""

    def __init__(
        self,
        api_key: str,
        rate_limiter: RateLimiter | None = None,
        timeout: float = 30.0,
    ) -> None:
        if not api_key:
            raise ValueError("FMP_API_KEY is required for FMPProvider")
        self._api_key = api_key
        self._rate_limiter = rate_limiter
        self._timeout = timeout

    def _acquire_rate_limit(self) -> None:
        if self._rate_limiter is not None:
            self._rate_limiter.wait_and_acquire()

    def _get(self, path: str, params: dict | None = None) -> httpx.Response:
        self._acquire_rate_limit()
        all_params = {"apikey": self._api_key}
        if params:
            all_params.update(params)
        return httpx.get(f"{_BASE_URL}{path}", params=all_params, timeout=self._timeout)

    @property
    def info(self) -> ProviderInfo:
        return ProviderInfo(
            name="fmp",
            supported_categories=[
                DataCategory.FUNDAMENTALS,
                DataCategory.PRICE,
                DataCategory.EARNINGS,
            ],
            requests_per_minute=300,
            requires_api_key=True,
            priority=20,
        )

    def fetch_fundamentals(self, ticker: str) -> FetchResult:
        try:
            income_resp = self._get(f"/income-statement/{ticker}", {"limit": 1})
            income_resp.raise_for_status()
            balance_resp = self._get(f"/balance-sheet-statement/{ticker}", {"limit": 1})
            balance_resp.raise_for_status()
            cashflow_resp = self._get(f"/cash-flow-statement/{ticker}", {"limit": 1})
            cashflow_resp.raise_for_status()

            return FetchResult(
                provider_name="fmp",
                category=DataCategory.FUNDAMENTALS,
                ticker=ticker,
                raw_data={
                    "income_statement": income_resp.json()[0] if income_resp.json() else {},
                    "balance_sheet": balance_resp.json()[0] if balance_resp.json() else {},
                    "cash_flow": cashflow_resp.json()[0] if cashflow_resp.json() else {},
                },
                fetched_at=_now_iso(),
            )
        except Exception as exc:
            return FetchResult(
                provider_name="fmp",
                category=DataCategory.FUNDAMENTALS,
                ticker=ticker,
                raw_data={},
                fetched_at=_now_iso(),
                success=False,
                error=str(exc),
            )

    def fetch_earnings(self, ticker: str) -> FetchResult:
        try:
            resp = self._get(f"/historical/earning_calendar/{ticker}", {"limit": 20})
            resp.raise_for_status()
            raw_earnings = resp.json() or []

            earnings = []
            for e in raw_earnings:
                entry = {"quarter": e.get("date", "")}
                if "eps" in e and e["eps"] is not None:
                    entry["actual_eps"] = e["eps"]
                if "epsEstimated" in e and e["epsEstimated"] is not None:
                    entry["expected_eps"] = e["epsEstimated"]
                earnings.append(entry)

            return FetchResult(
                provider_name="fmp",
                category=DataCategory.EARNINGS,
                ticker=ticker,
                raw_data={"earnings": earnings},
                fetched_at=_now_iso(),
            )
        except Exception as exc:
            return FetchResult(
                provider_name="fmp",
                category=DataCategory.EARNINGS,
                ticker=ticker,
                raw_data={},
                fetched_at=_now_iso(),
                success=False,
                error=str(exc),
            )

    def fetch_price_history(self, ticker: str, days: int = 365) -> FetchResult:
        try:
            resp = self._get(f"/historical-price-full/{ticker}", {"timeseries": days})
            resp.raise_for_status()
            data = resp.json()
            raw_bars = data.get("historical", []) if isinstance(data, dict) else []

            bars = []
            for bar in raw_bars:
                bars.append({
                    "date": bar.get("date", ""),
                    "open": bar.get("open"),
                    "high": bar.get("high"),
                    "low": bar.get("low"),
                    "close": bar.get("close"),
                    "volume": bar.get("volume"),
                })

            return FetchResult(
                provider_name="fmp",
                category=DataCategory.PRICE,
                ticker=ticker,
                raw_data={"bars": bars},
                fetched_at=_now_iso(),
            )
        except Exception as exc:
            return FetchResult(
                provider_name="fmp",
                category=DataCategory.PRICE,
                ticker=ticker,
                raw_data={},
                fetched_at=_now_iso(),
                success=False,
                error=str(exc),
            )
```

**Step 4: Run tests**

Run: `uv run pytest engine/tests/ingestion/test_fmp_provider.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add engine/src/margin_engine/ingestion/providers/fmp_provider.py engine/tests/ingestion/test_fmp_provider.py
git commit -m "feat(ingestion): add FMP fallback provider for fundamentals, earnings, price"
```

---

## Task 7: Symbol Mapper

Cross-provider symbol translation for known exceptions (BRK-B vs BRK.B, etc.).

**Files:**
- Create: `engine/src/margin_engine/ingestion/symbol_mapper.py`
- Create: `engine/symbol_overrides.yaml`
- Create: `engine/tests/ingestion/test_symbol_mapper.py`

**Step 1: Write the failing tests**

```python
"""Tests for cross-provider symbol mapper."""

from __future__ import annotations

from margin_engine.ingestion.symbol_mapper import SymbolMapper


class TestSymbolMapperPassthrough:
    def test_normal_ticker_passes_through(self):
        mapper = SymbolMapper()
        assert mapper.to_provider("AAPL", "fmp") == "AAPL"
        assert mapper.from_provider("AAPL", "fmp") == "AAPL"

    def test_normal_ticker_round_trips(self):
        mapper = SymbolMapper()
        provider_sym = mapper.to_provider("MSFT", "fmp")
        canonical = mapper.from_provider(provider_sym, "fmp")
        assert canonical == "MSFT"


class TestSymbolMapperOverrides:
    def test_brk_b_mapped_for_fmp(self):
        overrides = {"fmp": {"BRK-B": "BRK.B", "BRK-A": "BRK.A"}}
        mapper = SymbolMapper(overrides=overrides)
        assert mapper.to_provider("BRK-B", "fmp") == "BRK.B"
        assert mapper.from_provider("BRK.B", "fmp") == "BRK-B"

    def test_override_only_applies_to_specified_provider(self):
        overrides = {"fmp": {"BRK-B": "BRK.B"}}
        mapper = SymbolMapper(overrides=overrides)
        assert mapper.to_provider("BRK-B", "yfinance") == "BRK-B"  # no override

    def test_unknown_provider_passes_through(self):
        overrides = {"fmp": {"BRK-B": "BRK.B"}}
        mapper = SymbolMapper(overrides=overrides)
        assert mapper.to_provider("BRK-B", "unknown_provider") == "BRK-B"
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest engine/tests/ingestion/test_symbol_mapper.py -v`
Expected: FAIL — module not found

**Step 3: Implement symbol mapper**

```python
"""Cross-provider symbol translation.

Uses yfinance format as canonical (matches DB storage).
Override map from engine/symbol_overrides.yaml for known exceptions.
"""

from __future__ import annotations

from pathlib import Path

import yaml


class SymbolMapper:
    """Translate ticker symbols between providers."""

    def __init__(self, overrides: dict[str, dict[str, str]] | None = None) -> None:
        self._overrides = overrides or {}
        # Build reverse maps: {provider: {provider_sym: canonical_sym}}
        self._reverse: dict[str, dict[str, str]] = {}
        for provider, mapping in self._overrides.items():
            self._reverse[provider] = {v: k for k, v in mapping.items()}

    @classmethod
    def from_yaml(cls, path: Path | None = None) -> SymbolMapper:
        if path is None:
            path = Path(__file__).resolve().parents[3] / "symbol_overrides.yaml"
        if not path.exists():
            return cls()
        with open(path) as f:
            data = yaml.safe_load(f) or {}
        return cls(overrides=data.get("overrides", {}))

    def to_provider(self, canonical: str, provider_name: str) -> str:
        mapping = self._overrides.get(provider_name, {})
        return mapping.get(canonical, canonical)

    def from_provider(self, provider_sym: str, provider_name: str) -> str:
        reverse = self._reverse.get(provider_name, {})
        return reverse.get(provider_sym, provider_sym)
```

Create `engine/symbol_overrides.yaml`:

```yaml
# Cross-provider symbol overrides
# canonical (yfinance) -> provider-specific symbol
overrides:
  fmp:
    BRK-B: BRK.B
    BRK-A: BRK.A
```

**Step 4: Run tests**

Run: `uv run pytest engine/tests/ingestion/test_symbol_mapper.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add engine/src/margin_engine/ingestion/symbol_mapper.py engine/symbol_overrides.yaml engine/tests/ingestion/test_symbol_mapper.py
git commit -m "feat(ingestion): add cross-provider symbol mapper with YAML overrides"
```

---

## Task 8: Per-Category Fallback Orchestration

Wire FMP as fallback for failed yfinance categories in `seed_ticker_data`. When a category fails with yfinance, retry it with FMP before storing.

**Files:**
- Modify: `api/src/margin_api/cli.py` (seed_ticker_data)
- Modify: `api/src/margin_api/workers.py` (full_ingest — pass FMP provider)
- Create: `api/tests/test_category_fallback.py`

**Step 1: Write the failing test**

```python
"""Tests for per-category fallback from yfinance to FMP."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from margin_engine.ingestion.types import DataCategory, FetchResult


def _make_fetch_result(category, ticker="AAPL", success=True, raw_data=None, error=None, provider="yfinance"):
    return FetchResult(
        provider_name=provider,
        category=category,
        ticker=ticker,
        raw_data=raw_data or {},
        fetched_at=datetime.now(UTC).isoformat(),
        success=success,
        error=error,
    )


class TestCategoryFallback:
    @pytest.mark.asyncio
    async def test_fmp_called_for_failed_yfinance_earnings(self):
        """When yfinance earnings fail, FMP earnings should be tried."""
        from margin_api.cli import seed_ticker_data

        # Primary provider: yfinance — earnings fail
        yf_provider = MagicMock()
        yf_provider.fetch_all.return_value = {
            "fundamentals": _make_fetch_result(DataCategory.FUNDAMENTALS, raw_data={
                "income_statement": {"Total Revenue": 100000},
                "balance_sheet": {"Total Assets": 500000},
                "cash_flow": {"Operating Cash Flow": 40000},
            }),
            "price": _make_fetch_result(DataCategory.PRICE, raw_data={"bars": [{"Close": 150.0}]}),
            "earnings": _make_fetch_result(DataCategory.EARNINGS, success=False, error="lxml missing"),
            "info": _make_fetch_result(DataCategory.FUNDAMENTALS, raw_data={
                "shortName": "Apple Inc.", "sector": "Technology",
                "country": "United States", "marketCap": 3000000000000,
                "sharesOutstanding": 15000000000,
            }),
        }

        # Fallback provider: FMP — earnings succeed
        fmp_provider = MagicMock()
        fmp_provider.fetch_earnings.return_value = _make_fetch_result(
            DataCategory.EARNINGS,
            success=True,
            raw_data={"earnings": [{"quarter": "2024-01-25", "actual_eps": 2.18}]},
            provider="fmp",
        )

        mock_session = AsyncMock()
        asset_upsert_result = MagicMock()
        asset_upsert_result.scalar_one.return_value = 1
        fd_upsert_result = MagicMock()
        asset_obj = MagicMock()
        asset_obj.consecutive_failures = 0
        asset_obj.ingestion_status = "active"
        asset_obj.last_failure_reason = None
        asset_obj.quarantined_at = None
        asset_obj.last_retry_at = None
        asset_select_result = MagicMock()
        asset_select_result.scalar_one.return_value = asset_obj
        mock_session.execute.side_effect = [asset_upsert_result, fd_upsert_result, asset_select_result]

        result = await seed_ticker_data(
            ticker="AAPL",
            provider=yf_provider,
            session=mock_session,
            fallback_provider=fmp_provider,
        )

        assert result.status == "ok"  # FMP rescued the earnings
        fmp_provider.fetch_earnings.assert_called_once_with("AAPL")

    @pytest.mark.asyncio
    async def test_no_fallback_stays_partial(self):
        """Without fallback provider, failed categories stay failed."""
        from margin_api.cli import seed_ticker_data

        yf_provider = MagicMock()
        yf_provider.fetch_all.return_value = {
            "fundamentals": _make_fetch_result(DataCategory.FUNDAMENTALS, raw_data={
                "income_statement": {}, "balance_sheet": {}, "cash_flow": {},
            }),
            "price": _make_fetch_result(DataCategory.PRICE, raw_data={"bars": []}),
            "earnings": _make_fetch_result(DataCategory.EARNINGS, success=False, error="lxml"),
            "info": _make_fetch_result(DataCategory.FUNDAMENTALS, raw_data={
                "shortName": "Apple", "sector": "Technology",
                "country": "United States", "marketCap": 3000000000000,
            }),
        }

        mock_session = AsyncMock()
        asset_upsert_result = MagicMock()
        asset_upsert_result.scalar_one.return_value = 1
        fd_upsert_result = MagicMock()
        asset_obj = MagicMock()
        asset_obj.consecutive_failures = 0
        asset_obj.ingestion_status = "active"
        asset_obj.last_failure_reason = None
        asset_obj.quarantined_at = None
        asset_obj.last_retry_at = None
        asset_select_result = MagicMock()
        asset_select_result.scalar_one.return_value = asset_obj
        mock_session.execute.side_effect = [asset_upsert_result, fd_upsert_result, asset_select_result]

        result = await seed_ticker_data(
            ticker="AAPL",
            provider=yf_provider,
            session=mock_session,
            # No fallback_provider
        )

        assert result.status == "partial"
        assert "earnings" in result.categories_failed
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/test_category_fallback.py -v`
Expected: FAIL — `seed_ticker_data` doesn't accept `fallback_provider`

**Step 3: Implement fallback in seed_ticker_data**

Add optional `fallback_provider` parameter to `seed_ticker_data`. After the initial fetch_all, retry failed categories via the fallback:

```python
async def seed_ticker_data(
    *,
    ticker: str,
    provider: YFinanceProvider,
    session,
    fallback_provider=None,  # <-- new optional param
) -> SeedResult:
    try:
        results = provider.fetch_all(ticker)

        # Attempt fallback for failed categories
        if fallback_provider is not None:
            _FALLBACK_MAP = {
                "fundamentals": "fetch_fundamentals",
                "price": "fetch_price_history",
                "earnings": "fetch_earnings",
            }
            for cat_name, method_name in _FALLBACK_MAP.items():
                if cat_name in results and not results[cat_name].success:
                    try:
                        method = getattr(fallback_provider, method_name)
                        fb_result = method(ticker)
                        if fb_result.success:
                            results[cat_name] = fb_result
                            logger.info("  %s: %s rescued by %s", ticker, cat_name, fb_result.provider_name)
                    except Exception as fb_exc:
                        logger.warning("  %s: fallback %s failed: %s", ticker, cat_name, fb_exc)

        # ... rest of existing logic unchanged
```

In `run_seed` and `full_ingest`, construct the FMP provider if `FMP_API_KEY` is set:

```python
import os
fmp_provider = None
fmp_key = os.environ.get("FMP_API_KEY")
if fmp_key:
    from margin_engine.ingestion.providers.fmp_provider import FMPProvider
    fmp_provider = FMPProvider(api_key=fmp_key)
    logger.info("FMP fallback provider enabled")

# Then pass to seed_ticker_data:
result = await seed_ticker_data(
    ticker=ticker,
    provider=provider,
    session=session,
    fallback_provider=fmp_provider,
)
```

**Step 4: Run tests**

Run: `uv run pytest api/tests/test_category_fallback.py api/tests/ -v --tb=short -q`
Expected: All pass

**Step 5: Commit**

```bash
git add api/src/margin_api/cli.py api/src/margin_api/workers.py api/tests/test_category_fallback.py
git commit -m "feat(ingestion): per-category FMP fallback for failed yfinance categories"
```

---

## Task 9: IngestionTickerStatus Audit Trail

Write an `IngestionTickerStatus` row for every ticker processed in a run. The model already exists; we need to populate it from `full_ingest`.

**Files:**
- Modify: `api/src/margin_api/workers.py` (full_ingest loop)
- Create: `api/tests/test_ticker_audit_trail.py`

**Step 1: Write the failing test**

```python
"""Tests for IngestionTickerStatus audit trail."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestTickerAuditTrail:
    @pytest.mark.asyncio
    async def test_full_ingest_writes_ticker_status_rows(self):
        """full_ingest should write IngestionTickerStatus for each ticker."""
        from margin_api.workers import full_ingest

        ctx = {"redis": AsyncMock()}

        with (
            patch("margin_api.workers.get_engine") as mock_ge,
            patch("margin_api.workers.get_session_factory") as mock_gsf,
            patch("margin_api.workers.get_active_snapshot") as mock_snap,
            patch("margin_api.workers._load_foreign_skips", return_value=set()),
            patch("margin_api.workers.seed_ticker_data") as mock_seed,
        ):
            # Setup snapshot
            snapshot = MagicMock()
            snapshot.id = 1
            snapshot.version = "1.0"
            snapshot.tickers = ["AAPL", "MSFT"]
            mock_snap.return_value = snapshot

            # Setup session
            mock_session = AsyncMock()
            mock_session_ctx = AsyncMock()
            mock_session_ctx.__aenter__.return_value = mock_session
            mock_session_ctx.__aexit__.return_value = None
            mock_gsf.return_value = MagicMock(return_value=mock_session_ctx)

            # Seed results
            from margin_api.services.seed_result import SeedResult

            mock_seed.side_effect = [
                SeedResult(status="ok", categories_succeeded=["fundamentals", "price", "earnings", "info"]),
                SeedResult(status="partial", categories_succeeded=["fundamentals", "price"], categories_failed=["earnings"]),
            ]

            # Track IngestionTickerStatus adds
            added_objects = []
            original_add = mock_session.add

            def track_add(obj):
                added_objects.append(obj)

            mock_session.add = track_add

            # Run ID setup
            run_mock = MagicMock()
            run_mock.id = 1
            run_mock.started_at = datetime.now(UTC)
            mock_result = MagicMock()
            mock_result.scalar_one.return_value = run_mock
            mock_session.execute.return_value = mock_result

            result = await full_ingest(ctx)

        # Should have added IngestionTickerStatus rows
        from margin_api.db.models import IngestionTickerStatus

        ticker_statuses = [o for o in added_objects if isinstance(o, IngestionTickerStatus)]
        assert len(ticker_statuses) == 2
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/test_ticker_audit_trail.py -v`
Expected: FAIL — no IngestionTickerStatus rows added

**Step 3: Implement audit trail**

In `workers.py:full_ingest`, after each `seed_ticker_data` call, write an `IngestionTickerStatus` row:

```python
from margin_api.db.models import IngestionTickerStatus

# Inside the per-ticker loop, after getting seed result:
tick_started = datetime.now(UTC)
async with session_factory() as session:
    result = await seed_ticker_data(...)
tick_ended = datetime.now(UTC)
duration_ms = int((tick_ended - tick_started).total_seconds() * 1000)

# Record per-ticker audit trail
async with session_factory() as session:
    ticker_status = IngestionTickerStatus(
        run_id=run_id,
        ticker=ticker,
        status="succeeded" if result.status in ("ok", "partial") else result.status,
        error_message=result.error_message,
        data_fetched=result.data_categories_present if result.is_success else None,
        duration_ms=duration_ms,
        started_at=tick_started,
        completed_at=tick_ended,
    )
    session.add(ticker_status)
    await session.commit()
```

**Step 4: Run tests**

Run: `uv run pytest api/tests/test_ticker_audit_trail.py api/tests/ -v --tb=short -q`
Expected: All pass

**Step 5: Commit**

```bash
git add api/src/margin_api/workers.py api/tests/test_ticker_audit_trail.py
git commit -m "feat(ingestion): write IngestionTickerStatus audit trail per ticker per run"
```

---

## Task 10: Integration Tests

End-to-end tests verifying the full resilient pipeline flow.

**Files:**
- Modify: `api/tests/test_resilient_ingestion.py` (add new test classes)

**Step 1: Write new integration tests**

Add to `api/tests/test_resilient_ingestion.py`:

```python
class TestCircuitBreakerIntegration:
    def test_circuit_breaker_trips_after_threshold(self):
        from margin_engine.ingestion.circuit_breaker import CircuitBreaker

        cb = CircuitBreaker(failure_threshold=3, cooldown_seconds=60)
        for _ in range(3):
            cb.record_failure()
        assert cb.state == "open"
        assert cb.trip_count == 1

    def test_circuit_breaker_resets_on_success(self):
        from margin_engine.ingestion.circuit_breaker import CircuitBreaker

        cb = CircuitBreaker(failure_threshold=3, cooldown_seconds=60)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        assert cb.state == "closed"
        assert cb.consecutive_failures == 0


class TestRetryIntegration:
    def test_retry_decorator_retries_transient(self):
        from margin_engine.ingestion.retry import retry_transient

        call_count = 0

        @retry_transient(max_retries=2, base_delay=0.01)
        def flaky():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionError("reset")
            return "ok"

        assert flaky() == "ok"
        assert call_count == 2


class TestSymbolMapperIntegration:
    def test_yaml_loading(self):
        from pathlib import Path

        from margin_engine.ingestion.symbol_mapper import SymbolMapper

        # Load from the actual YAML file
        yaml_path = Path(__file__).resolve().parents[2] / "engine" / "symbol_overrides.yaml"
        if yaml_path.exists():
            mapper = SymbolMapper.from_yaml(yaml_path)
            assert mapper.to_provider("BRK-B", "fmp") == "BRK.B"

    def test_missing_yaml_returns_passthrough(self):
        from pathlib import Path

        from margin_engine.ingestion.symbol_mapper import SymbolMapper

        mapper = SymbolMapper.from_yaml(Path("/nonexistent/path.yaml"))
        assert mapper.to_provider("AAPL", "fmp") == "AAPL"


class TestRunLevelResumeIntegration:
    def test_seed_result_data_categories_present(self):
        from margin_api.services.seed_result import SeedResult

        result = SeedResult(
            status="partial",
            categories_succeeded=["fundamentals", "price", "info"],
            categories_failed=["earnings"],
        )
        cats = result.data_categories_present
        assert cats == {
            "fundamentals": True,
            "price": True,
            "info": True,
            "earnings": False,
        }
```

**Step 2: Run all tests**

Run: `uv run pytest api/tests/test_resilient_ingestion.py -v`
Expected: PASS

**Step 3: Run full test suite**

Run: `uv run pytest engine/tests/ api/tests/ -v --tb=short -q`
Expected: All pass

**Step 4: Lint check**

Run: `uv run ruff check engine/ api/`
Expected: Clean (or only pre-existing alembic issues)

**Step 5: Commit**

```bash
git add api/tests/test_resilient_ingestion.py
git commit -m "test(ingestion): add integration tests for circuit breaker, retry, mapper, resume"
```

---

## Summary

| Task | What | Files |
|------|------|-------|
| 1 | Per-request rate limiting | yfinance_provider.py |
| 2 | Wire should_ingest_ticker | cli.py, workers.py |
| 3 | Circuit breaker | circuit_breaker.py (new) |
| 4 | Retry decorator | retry.py (new) |
| 5 | Run-level resume | cli.py, workers.py |
| 6 | FMP provider | fmp_provider.py (new) |
| 7 | Symbol mapper | symbol_mapper.py (new) |
| 8 | Per-category fallback | cli.py, workers.py |
| 9 | IngestionTickerStatus | workers.py |
| 10 | Integration tests | test_resilient_ingestion.py |

**Dependency order:** Tasks 1-5 are independent. Task 6 needs Task 4 (retry). Task 8 needs Task 6 (FMP). Task 9 is independent. Task 10 is last.
