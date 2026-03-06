# Live Price Refresh Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Keep the price chart in the candidate expanded view fresh (~15 min delay) by injecting today's live OHLCV bar from Redis into the API's `price_history` response.

**Architecture:** Extend existing `live_price_poll` worker to fetch daily OHLCV bars for all scored tickers (not just high conviction), store them in Redis, and inject them into the scores API response at serving time. No frontend changes.

**Tech Stack:** Python, Redis (fakeredis for tests), yfinance, ARQ cron, FastAPI

**Design doc:** `docs/plans/2026-03-06-live-price-refresh-design.md`

---

### Task 1: Add `set_bar`/`get_bar` methods to LivePriceService

**Files:**
- Modify: `api/src/margin_api/services/live_prices.py:11-48`
- Test: `api/tests/test_live_prices.py`

**Step 1: Write the failing tests**

Add to the end of `api/tests/test_live_prices.py`:

```python
    @pytest.mark.asyncio
    async def test_get_bar_returns_none_when_not_cached(self, service):
        result = await service.get_bar("AAPL")
        assert result is None

    @pytest.mark.asyncio
    async def test_set_and_get_bar(self, service):
        bar = {
            "date": "2026-03-06",
            "open": 188.50,
            "high": 192.30,
            "low": 187.20,
            "close": 191.75,
            "volume": 4523000,
        }
        await service.set_bar("AAPL", bar)
        result = await service.get_bar("AAPL")
        assert result is not None
        assert result["date"] == "2026-03-06"
        assert result["close"] == 191.75
        assert result["volume"] == 4523000
        assert "updated_at" in result

    @pytest.mark.asyncio
    async def test_bar_key_prefix(self, service, redis_client):
        bar = {"date": "2026-03-06", "open": 1, "high": 2, "low": 0.5, "close": 1.5, "volume": 100}
        await service.set_bar("AAPL", bar)
        raw = await redis_client.get("live_bar:AAPL")
        assert raw is not None

    @pytest.mark.asyncio
    async def test_bar_ttl_is_set(self, service, redis_client):
        bar = {"date": "2026-03-06", "open": 1, "high": 2, "low": 0.5, "close": 1.5, "volume": 100}
        await service.set_bar("AAPL", bar)
        ttl = await redis_client.ttl("live_bar:AAPL")
        assert ttl > 0
        assert ttl <= 86400
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest api/tests/test_live_prices.py -v -k "bar"`
Expected: FAIL — `AttributeError: 'LivePriceService' object has no attribute 'get_bar'`

**Step 3: Implement `set_bar` and `get_bar`**

Add to `api/src/margin_api/services/live_prices.py` — new constants and methods on `LivePriceService`:

```python
    BAR_KEY_PREFIX = "live_bar:"
    BAR_TTL_SECONDS = 86400  # 24 hours

    async def get_bar(self, ticker: str) -> dict | None:
        """Get today's live OHLCV bar for a ticker. Returns None if not cached."""
        data = await self.redis.get(f"{self.BAR_KEY_PREFIX}{ticker}")
        if data is None:
            return None
        return json.loads(data)

    async def set_bar(self, ticker: str, bar: dict) -> None:
        """Cache today's OHLCV bar with 24h TTL."""
        payload = {**bar, "updated_at": datetime.now(UTC).isoformat()}
        await self.redis.set(
            f"{self.BAR_KEY_PREFIX}{ticker}",
            json.dumps(payload),
            ex=self.BAR_TTL_SECONDS,
        )
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest api/tests/test_live_prices.py -v`
Expected: All tests PASS (existing + new)

**Step 5: Commit**

```bash
git add api/src/margin_api/services/live_prices.py api/tests/test_live_prices.py
git commit -m "feat(api): add set_bar/get_bar to LivePriceService for daily OHLCV caching"
```

---

### Task 2: Expand `live_price_poll` to fetch OHLCV bars for all scored tickers

**Files:**
- Modify: `api/src/margin_api/workers.py:2182-2237` (the `live_price_poll` function)
- Modify: `api/src/margin_api/workers.py:3010-3014` (cron interval)
- Test: `api/tests/test_workers.py` (class `TestLivePricePoll`)

**Step 1: Write the failing test**

Add a new test to `TestLivePricePoll` in `api/tests/test_workers.py`:

```python
    @pytest.mark.asyncio
    async def test_live_price_poll_stores_bar_data(self):
        """Stores OHLCV bar in Redis alongside price."""
        import fakeredis.aioredis
        from margin_api.workers import live_price_poll

        fake_redis = fakeredis.aioredis.FakeRedis()

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = [("AAPL",)]
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        # Mock yfinance Ticker with history returning a DataFrame-like object
        import pandas as pd
        mock_ticker = MagicMock()
        mock_ticker.fast_info = MagicMock()
        mock_ticker.fast_info.last_price = 191.75
        mock_hist = pd.DataFrame(
            {
                "Open": [188.50],
                "High": [192.30],
                "Low": [187.20],
                "Close": [191.75],
                "Volume": [4523000],
            },
            index=pd.DatetimeIndex(["2026-03-06"], name="Date"),
        )
        mock_ticker.history.return_value = mock_hist

        with (
            patch("margin_api.workers.get_engine"),
            patch("margin_api.workers.get_session_factory", return_value=mock_session_factory),
            patch("margin_api.workers.get_settings") as mock_settings,
            patch("margin_api.workers.aioredis.from_url", return_value=fake_redis),
            patch("margin_api.workers.yf.Ticker", return_value=mock_ticker),
        ):
            mock_settings.return_value.redis_url = "redis://localhost:6379"
            result = await live_price_poll({})

        assert result["status"] == "completed"

        from margin_api.services.live_prices import LivePriceService
        service = LivePriceService(fake_redis)

        # Verify bar was stored
        bar = await service.get_bar("AAPL")
        assert bar is not None
        assert bar["date"] == "2026-03-06"
        assert bar["close"] == 191.75
        assert bar["volume"] == 4523000

        # Verify price was also stored (backward compat)
        price = await service.get_price("AAPL")
        assert price is not None
        assert price["price"] == 191.75

        await fake_redis.aclose()

    @pytest.mark.asyncio
    async def test_live_price_poll_all_scored_tickers(self):
        """Polls all scored tickers, not just high conviction."""
        import fakeredis.aioredis
        from margin_api.workers import live_price_poll

        fake_redis = fakeredis.aioredis.FakeRedis()

        mock_session = AsyncMock()
        # Return tickers without conviction filter
        mock_result = MagicMock()
        mock_result.all.return_value = [("AAPL",), ("MSFT",)]
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        import pandas as pd
        def mock_ticker_factory(ticker):
            mock_t = MagicMock()
            mock_t.fast_info = MagicMock()
            mock_t.fast_info.last_price = 100.0
            mock_t.history.return_value = pd.DataFrame(
                {"Open": [99.0], "High": [101.0], "Low": [98.0], "Close": [100.0], "Volume": [1000]},
                index=pd.DatetimeIndex(["2026-03-06"], name="Date"),
            )
            return mock_t

        with (
            patch("margin_api.workers.get_engine"),
            patch("margin_api.workers.get_session_factory", return_value=mock_session_factory),
            patch("margin_api.workers.get_settings") as mock_settings,
            patch("margin_api.workers.aioredis.from_url", return_value=fake_redis),
            patch("margin_api.workers.yf.Ticker", side_effect=mock_ticker_factory),
        ):
            mock_settings.return_value.redis_url = "redis://localhost:6379"
            result = await live_price_poll({})

        assert result["updated"] == 2

        from margin_api.services.live_prices import LivePriceService
        service = LivePriceService(fake_redis)
        assert await service.get_bar("AAPL") is not None
        assert await service.get_bar("MSFT") is not None

        await fake_redis.aclose()
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest api/tests/test_workers.py::TestLivePricePoll::test_live_price_poll_stores_bar_data -v`
Expected: FAIL — no `get_bar` call in current `live_price_poll`, or bar not stored

**Step 3: Rewrite `live_price_poll` function**

Replace the function at `api/src/margin_api/workers.py:2182-2237` with:

```python
async def live_price_poll(ctx: dict) -> dict:
    """Poll live prices for all scored tickers and cache bars + prices in Redis."""
    settings = get_settings()

    engine = get_engine()
    session_factory = get_session_factory(engine)

    # Query DB for ALL tickers with a latest score (no conviction filter)
    async with session_factory() as session:
        latest_subq = (
            select(
                Score.asset_id,
                func.max(Score.scored_at).label("max_scored_at"),
            )
            .group_by(Score.asset_id)
            .subquery()
        )
        result = await session.execute(
            select(Asset.ticker)
            .join(Score, Score.asset_id == Asset.id)
            .join(
                latest_subq,
                (Score.asset_id == latest_subq.c.asset_id)
                & (Score.scored_at == latest_subq.c.max_scored_at),
            )
        )
        scored_tickers = [row[0] for row in result.all()]

    if not scored_tickers:
        return {"status": "no_scored_tickers", "updated": 0}

    logger.info("[prices] Polling prices for %d scored tickers", len(scored_tickers))

    redis_client = aioredis.from_url(settings.redis_url)
    service = LivePriceService(redis_client)

    try:
        updated = 0
        for ticker in scored_tickers:
            try:
                t = yf.Ticker(ticker)

                # Fetch last_price for backward-compat actual_price override
                info = t.fast_info
                current = getattr(info, "last_price", None)
                if current and current > 0:
                    await service.set_price(ticker, float(current))

                # Fetch today's daily bar for chart injection
                hist = t.history(period="1d")
                if hist is not None and not hist.empty:
                    row = hist.iloc[-1]
                    bar_date = hist.index[-1].strftime("%Y-%m-%d")
                    bar = {
                        "date": bar_date,
                        "open": float(row["Open"]),
                        "high": float(row["High"]),
                        "low": float(row["Low"]),
                        "close": float(row["Close"]),
                        "volume": int(row["Volume"]),
                    }
                    await service.set_bar(ticker, bar)

                updated += 1
            except Exception:
                logger.debug("[prices] Failed to fetch %s", ticker, exc_info=True)
                continue

        logger.info("[prices] Updated %d/%d tickers", updated, len(scored_tickers))
        return {"status": "completed", "updated": updated}
    finally:
        await redis_client.aclose()
```

Also change the cron interval at line 3010-3014 from every 5 min to every 15 min:

```python
        cron(
            live_price_poll,
            minute={0, 15, 30, 45},
            run_at_startup=False,
        ),
```

**Step 4: Update existing tests**

The existing `test_live_price_poll_with_tickers` and `test_live_price_poll_no_recommendations` tests need minor updates:
- `test_live_price_poll_no_recommendations`: Change expected status from `"no_recommendations"` to `"no_scored_tickers"`
- `test_live_price_poll_with_tickers`: Add `mock_ticker.history.return_value` as an empty DataFrame (so bar storage is skipped gracefully)
- `test_live_price_poll_skips_failed_tickers`: Same — add history mock to the good ticker factory

For `test_live_price_poll_with_tickers`, add after line 409:
```python
        import pandas as pd
        mock_ticker.history.return_value = pd.DataFrame()  # empty — bar not stored
```

For `test_live_price_poll_skips_failed_tickers`, inside `mock_ticker_factory` for the good path, add:
```python
            import pandas as pd
            mock_t.history.return_value = pd.DataFrame()
```

For `test_live_price_poll_no_recommendations`, change the assertion:
```python
        assert result["status"] == "no_scored_tickers"
```

**Step 5: Run all tests to verify they pass**

Run: `uv run pytest api/tests/test_workers.py::TestLivePricePoll -v`
Expected: All 5 tests PASS

**Step 6: Commit**

```bash
git add api/src/margin_api/workers.py api/tests/test_workers.py
git commit -m "feat(api): expand live_price_poll to store OHLCV bars for all scored tickers"
```

---

### Task 3: Inject live bar into `price_history` API response

**Files:**
- Modify: `api/src/margin_api/routes/scores.py:472-486` (add `_try_get_live_bar`)
- Modify: `api/src/margin_api/routes/scores.py:723-761` (inject bar into response)
- Test: `api/tests/routes/test_live_bar_injection.py` (new file)

**Step 1: Write the failing tests**

Create `api/tests/routes/test_live_bar_injection.py`:

```python
"""Tests for live bar injection into price_history response."""

from __future__ import annotations

import pytest


class TestInjectLiveBar:
    """Unit tests for the _inject_live_bar helper."""

    def test_append_bar_new_day(self):
        """Live bar on a new date is appended to the list."""
        from margin_api.routes.scores import _inject_live_bar

        existing = [
            {"date": "2026-03-04", "open": 1, "high": 2, "low": 0.5, "close": 1.5, "volume": 100},
            {"date": "2026-03-05", "open": 1.5, "high": 2.5, "low": 1, "close": 2, "volume": 200},
        ]
        live_bar = {
            "date": "2026-03-06",
            "open": 2,
            "high": 3,
            "low": 1.5,
            "close": 2.5,
            "volume": 300,
            "updated_at": "2026-03-06T15:00:00Z",
        }
        result = _inject_live_bar(existing, live_bar)
        assert len(result) == 3
        assert result[-1]["date"] == "2026-03-06"
        assert result[-1]["close"] == 2.5

    def test_replace_bar_same_day(self):
        """Live bar on the same date as last bar replaces it."""
        from margin_api.routes.scores import _inject_live_bar

        existing = [
            {"date": "2026-03-05", "open": 1, "high": 2, "low": 0.5, "close": 1.5, "volume": 100},
            {"date": "2026-03-06", "open": 2, "high": 2.8, "low": 1.9, "close": 2.3, "volume": 250},
        ]
        live_bar = {
            "date": "2026-03-06",
            "open": 2,
            "high": 3.1,
            "low": 1.8,
            "close": 2.7,
            "volume": 400,
            "updated_at": "2026-03-06T15:30:00Z",
        }
        result = _inject_live_bar(existing, live_bar)
        assert len(result) == 2  # replaced, not appended
        assert result[-1]["close"] == 2.7
        assert result[-1]["volume"] == 400

    def test_no_injection_when_live_bar_is_none(self):
        """Returns existing bars unchanged when live bar is None."""
        from margin_api.routes.scores import _inject_live_bar

        existing = [
            {"date": "2026-03-05", "open": 1, "high": 2, "low": 0.5, "close": 1.5, "volume": 100},
        ]
        result = _inject_live_bar(existing, None)
        assert len(result) == 1
        assert result is existing

    def test_injection_into_empty_list(self):
        """Live bar is appended even when existing list is empty."""
        from margin_api.routes.scores import _inject_live_bar

        live_bar = {
            "date": "2026-03-06",
            "open": 2,
            "high": 3,
            "low": 1.5,
            "close": 2.5,
            "volume": 300,
            "updated_at": "2026-03-06T15:00:00Z",
        }
        result = _inject_live_bar([], live_bar)
        assert len(result) == 1
        assert result[0]["date"] == "2026-03-06"

    def test_updated_at_stripped_from_result(self):
        """The updated_at metadata key is not passed to chart bars."""
        from margin_api.routes.scores import _inject_live_bar

        live_bar = {
            "date": "2026-03-06",
            "open": 2,
            "high": 3,
            "low": 1.5,
            "close": 2.5,
            "volume": 300,
            "updated_at": "2026-03-06T15:00:00Z",
        }
        result = _inject_live_bar([], live_bar)
        assert "updated_at" not in result[0]
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest api/tests/routes/test_live_bar_injection.py -v`
Expected: FAIL — `ImportError: cannot import name '_inject_live_bar'`

**Step 3: Implement `_inject_live_bar` and `_try_get_live_bar`**

Add the helper function to `api/src/margin_api/routes/scores.py`, right after `_try_get_live_price` (after line 486):

```python
async def _try_get_live_bar(ticker: str) -> dict | None:
    """Try to fetch today's live OHLCV bar from Redis. Returns None if unavailable."""
    try:
        import redis.asyncio as aioredis

        from margin_api.services.live_prices import LivePriceService

        client = aioredis.Redis(host="localhost", port=6379, socket_connect_timeout=1)
        service = LivePriceService(client)
        try:
            return await service.get_bar(ticker)
        finally:
            await client.aclose()
    except Exception:
        return None


def _inject_live_bar(
    existing_bars: list[dict],
    live_bar: dict | None,
) -> list[dict]:
    """Merge today's live bar into the historical bars list.

    - If live_bar is None, return existing bars unchanged.
    - If the last existing bar has the same date as the live bar, replace it.
    - Otherwise, append the live bar.
    """
    if live_bar is None:
        return existing_bars

    # Strip metadata keys — only keep OHLCV fields
    bar = {
        "date": live_bar["date"],
        "open": live_bar["open"],
        "high": live_bar["high"],
        "low": live_bar["low"],
        "close": live_bar["close"],
        "volume": live_bar["volume"],
    }

    if not existing_bars:
        return [bar]

    last_date = existing_bars[-1].get("date", "")
    # Normalize: strip time portion if present (e.g. "2026-03-06T00:00:00")
    last_date_str = last_date[:10] if last_date else ""
    live_date_str = bar["date"][:10]

    if last_date_str == live_date_str:
        # Replace last bar with updated live data
        return existing_bars[:-1] + [bar]
    else:
        # Append new day's bar
        return existing_bars + [bar]
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest api/tests/routes/test_live_bar_injection.py -v`
Expected: All 5 tests PASS

**Step 5: Wire injection into the `get_score` endpoint**

In `api/src/margin_api/routes/scores.py`, modify the `"price_history"` handling block (around line 723).

After `response.price_history` is set (around line 761), add the injection call. Replace the section from line 723 to 761 with:

```python
    if "price_history" in includes:
        from margin_api.schemas.scores import PriceBarResponse

        fd_query = (
            select(FinancialData.price_history)
            .where(FinancialData.asset_id == row[0].asset_id)
            .order_by(FinancialData.period_end.desc())
            .limit(1)
        )
        fd_result = await db.execute(fd_query)
        fd_row = fd_result.scalar()

        def _normalize_bar(bar: dict) -> dict:
            """Map yfinance capitalized keys to PriceBarResponse fields."""
            return {
                "date": bar.get("date") or bar.get("Date", ""),
                "open": bar.get("open") or bar.get("Open", 0),
                "high": bar.get("high") or bar.get("High", 0),
                "low": bar.get("low") or bar.get("Low", 0),
                "close": bar.get("close") or bar.get("Close", 0),
                "volume": int(bar.get("volume") or bar.get("Volume", 0)),
            }

        try:
            if fd_row and isinstance(fd_row, dict) and "bars" in fd_row:
                bars = [_normalize_bar(bar) for bar in fd_row["bars"]]
            elif fd_row and isinstance(fd_row, list):
                bars = [_normalize_bar(bar) for bar in fd_row]
            else:
                bars = []

            # Inject today's live bar from Redis
            live_bar = await _try_get_live_bar(ticker)
            bars = _inject_live_bar(bars, live_bar)

            response.price_history = [PriceBarResponse(**bar) for bar in bars]
        except Exception:
            import logging

            logging.getLogger(__name__).warning(
                "Failed to parse price_history for %s", ticker, exc_info=True
            )
            response.price_history = []
```

**Step 6: Run full test suite to verify nothing broke**

Run: `uv run pytest api/tests/routes/test_live_bar_injection.py api/tests/test_live_prices.py api/tests/test_workers.py::TestLivePricePoll -v`
Expected: All tests PASS

**Step 7: Commit**

```bash
git add api/src/margin_api/routes/scores.py api/tests/routes/test_live_bar_injection.py
git commit -m "feat(api): inject today's live OHLCV bar into price_history response"
```

---

### Task 4: Run full API test suite to verify no regressions

**Files:** None (verification only)

**Step 1: Run full API tests**

Run: `uv run pytest api/tests/ -v --ignore=api/tests/services/test_xbrl_parser.py`
Expected: All ~1587 tests PASS

**Step 2: Run web tests to verify frontend still works**

Run: `cd web && npx vitest run`
Expected: All ~1285 tests PASS

**Step 3: Run linters**

Run: `uv run ruff check --fix api/ && uv run ruff format api/`
Run: `cd web && npx eslint --fix .`
Expected: No errors

**Step 4: Commit any lint fixes**

```bash
git add -A
git commit -m "chore: lint fixes for live price refresh"
```

---

### Task 5: Final commit and summary

**Step 1: Verify all changes**

Run: `git log --oneline -5`
Expected: See the 3-4 commits from this implementation

**Step 2: Summary of changes**

Files modified:
- `api/src/margin_api/services/live_prices.py` — added `set_bar`/`get_bar` with 24h TTL
- `api/src/margin_api/workers.py` — expanded `live_price_poll` to all scored tickers, fetch OHLCV bars, 15-min interval
- `api/src/margin_api/routes/scores.py` — added `_try_get_live_bar`, `_inject_live_bar`, wired injection into `get_score`

Files created:
- `api/tests/routes/test_live_bar_injection.py` — 5 unit tests for bar injection logic

Files updated:
- `api/tests/test_live_prices.py` — 4 new tests for `set_bar`/`get_bar`
- `api/tests/test_workers.py` — 2 new tests + 3 updated tests for expanded worker
