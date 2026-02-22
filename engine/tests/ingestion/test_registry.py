"""Tests for provider registry with fallback chains."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from margin_engine.ingestion.rate_limiter import RateLimiterRegistry
from margin_engine.ingestion.registry import ProviderRegistry
from margin_engine.ingestion.types import (
    DataCategory,
    DataProvider,
    FetchResult,
    ProviderInfo,
)

# ---------------------------------------------------------------------------
# Fake / mock providers for testing
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


class FakeProvider(DataProvider):
    """Configurable fake provider for unit tests."""

    def __init__(
        self,
        name: str,
        categories: list[DataCategory],
        *,
        priority: int = 0,
        requires_api_key: bool = False,
        requests_per_minute: int = 60,
        should_fail: bool = False,
        fail_exception: Exception | None = None,
    ) -> None:
        self._info = ProviderInfo(
            name=name,
            supported_categories=categories,
            requests_per_minute=requests_per_minute,
            requires_api_key=requires_api_key,
            priority=priority,
        )
        self._should_fail = should_fail
        self._fail_exception = fail_exception
        self.calls: list[tuple[str, str, dict]] = []  # (method, ticker, kwargs)

    @property
    def info(self) -> ProviderInfo:
        return self._info

    def _make_result(
        self, category: DataCategory, ticker: str, extra_data: dict | None = None
    ) -> FetchResult:
        if self._should_fail:
            raise self._fail_exception or RuntimeError(f"{self.info.name} failed")
        return FetchResult(
            provider_name=self.info.name,
            category=category,
            ticker=ticker,
            raw_data=extra_data or {"source": self.info.name},
            fetched_at=_now_iso(),
        )

    def fetch_fundamentals(self, ticker: str) -> FetchResult:
        self.calls.append(("fetch_fundamentals", ticker, {}))
        return self._make_result(DataCategory.FUNDAMENTALS, ticker)

    def fetch_price_history(self, ticker: str, days: int = 365) -> FetchResult:
        self.calls.append(("fetch_price_history", ticker, {"days": days}))
        return self._make_result(DataCategory.PRICE, ticker, extra_data={"days": days})

    def fetch_insider_transactions(self, ticker: str) -> FetchResult:
        self.calls.append(("fetch_insider_transactions", ticker, {}))
        return self._make_result(DataCategory.INSIDER, ticker)

    def fetch_institutional_holdings(self, ticker: str) -> FetchResult:
        self.calls.append(("fetch_institutional_holdings", ticker, {}))
        return self._make_result(DataCategory.INSTITUTIONAL, ticker)

    def fetch_earnings(self, ticker: str) -> FetchResult:
        self.calls.append(("fetch_earnings", ticker, {}))
        return self._make_result(DataCategory.EARNINGS, ticker)


# ---------------------------------------------------------------------------
# Tests: register and list providers
# ---------------------------------------------------------------------------


class TestRegisterAndList:
    def test_register_single_provider(self):
        registry = ProviderRegistry()
        provider = FakeProvider("alpha", [DataCategory.FUNDAMENTALS])
        registry.register(provider)

        infos = registry.registered_providers
        assert len(infos) == 1
        assert infos[0].name == "alpha"

    def test_register_multiple_providers(self):
        registry = ProviderRegistry()
        registry.register(FakeProvider("alpha", [DataCategory.FUNDAMENTALS]))
        registry.register(FakeProvider("beta", [DataCategory.PRICE]))
        registry.register(FakeProvider("gamma", [DataCategory.INSIDER]))

        names = {p.name for p in registry.registered_providers}
        assert names == {"alpha", "beta", "gamma"}

    def test_registered_providers_returns_provider_infos(self):
        registry = ProviderRegistry()
        provider = FakeProvider("alpha", [DataCategory.PRICE], priority=5)
        registry.register(provider)

        infos = registry.registered_providers
        assert isinstance(infos[0], ProviderInfo)
        assert infos[0].priority == 5

    def test_empty_registry(self):
        registry = ProviderRegistry()
        assert registry.registered_providers == []


# ---------------------------------------------------------------------------
# Tests: fallback chain ordering by priority
# ---------------------------------------------------------------------------


class TestFallbackChainOrdering:
    def test_single_provider_in_chain(self):
        registry = ProviderRegistry()
        p = FakeProvider("solo", [DataCategory.FUNDAMENTALS], priority=1)
        registry.register(p)

        chain = registry.get_fallback_chain(DataCategory.FUNDAMENTALS)
        assert len(chain) == 1
        assert chain[0].info.name == "solo"

    def test_ordered_by_priority_highest_first(self):
        registry = ProviderRegistry()
        low = FakeProvider("low", [DataCategory.PRICE], priority=1)
        high = FakeProvider("high", [DataCategory.PRICE], priority=10)
        mid = FakeProvider("mid", [DataCategory.PRICE], priority=5)

        # Register in non-priority order
        registry.register(low)
        registry.register(high)
        registry.register(mid)

        chain = registry.get_fallback_chain(DataCategory.PRICE)
        names = [p.info.name for p in chain]
        assert names == ["high", "mid", "low"]

    def test_chain_only_includes_providers_for_category(self):
        registry = ProviderRegistry()
        price_provider = FakeProvider("price_only", [DataCategory.PRICE], priority=10)
        fund_provider = FakeProvider("fund_only", [DataCategory.FUNDAMENTALS], priority=5)
        registry.register(price_provider)
        registry.register(fund_provider)

        chain = registry.get_fallback_chain(DataCategory.PRICE)
        assert len(chain) == 1
        assert chain[0].info.name == "price_only"

    def test_empty_chain_for_unsupported_category(self):
        registry = ProviderRegistry()
        registry.register(FakeProvider("fund", [DataCategory.FUNDAMENTALS]))

        chain = registry.get_fallback_chain(DataCategory.INSIDER)
        assert chain == []


# ---------------------------------------------------------------------------
# Tests: key-aware exclusion
# ---------------------------------------------------------------------------


class TestKeyAwareExclusion:
    def test_provider_requiring_key_excluded_without_key(self):
        registry = ProviderRegistry(api_keys={})
        needs_key = FakeProvider(
            "premium",
            [DataCategory.PRICE],
            requires_api_key=True,
            priority=10,
        )
        registry.register(needs_key)

        chain = registry.get_fallback_chain(DataCategory.PRICE)
        assert chain == []

    def test_provider_requiring_key_included_with_key(self):
        registry = ProviderRegistry(api_keys={"premium": "secret123"})
        needs_key = FakeProvider(
            "premium",
            [DataCategory.PRICE],
            requires_api_key=True,
            priority=10,
        )
        registry.register(needs_key)

        chain = registry.get_fallback_chain(DataCategory.PRICE)
        assert len(chain) == 1
        assert chain[0].info.name == "premium"

    def test_mixed_key_and_no_key_providers(self):
        registry = ProviderRegistry(api_keys={"polygon": "pk_123"})

        polygon = FakeProvider(
            "polygon",
            [DataCategory.PRICE],
            requires_api_key=True,
            priority=10,
        )
        yfinance = FakeProvider(
            "yfinance",
            [DataCategory.PRICE],
            requires_api_key=False,
            priority=5,
        )
        registry.register(polygon)
        registry.register(yfinance)

        chain = registry.get_fallback_chain(DataCategory.PRICE)
        names = [p.info.name for p in chain]
        assert names == ["polygon", "yfinance"]

    def test_provider_requiring_key_excluded_when_no_keys_dict(self):
        """api_keys=None means no keys are available."""
        registry = ProviderRegistry(api_keys=None)
        needs_key = FakeProvider(
            "premium",
            [DataCategory.PRICE],
            requires_api_key=True,
            priority=10,
        )
        free = FakeProvider(
            "free",
            [DataCategory.PRICE],
            requires_api_key=False,
            priority=1,
        )
        registry.register(needs_key)
        registry.register(free)

        chain = registry.get_fallback_chain(DataCategory.PRICE)
        assert len(chain) == 1
        assert chain[0].info.name == "free"

    def test_empty_string_key_excludes_provider(self):
        registry = ProviderRegistry(api_keys={"premium": ""})
        needs_key = FakeProvider(
            "premium",
            [DataCategory.PRICE],
            requires_api_key=True,
            priority=10,
        )
        registry.register(needs_key)

        chain = registry.get_fallback_chain(DataCategory.PRICE)
        assert chain == []


# ---------------------------------------------------------------------------
# Tests: fetch success on first provider
# ---------------------------------------------------------------------------


class TestFetchSuccess:
    def test_fetch_returns_result_from_first_provider(self):
        registry = ProviderRegistry()
        primary = FakeProvider("primary", [DataCategory.FUNDAMENTALS], priority=10)
        fallback = FakeProvider("fallback", [DataCategory.FUNDAMENTALS], priority=1)
        registry.register(primary)
        registry.register(fallback)

        result = registry.fetch(DataCategory.FUNDAMENTALS, "AAPL")

        assert result.success is True
        assert result.provider_name == "primary"
        assert result.ticker == "AAPL"
        assert result.category == DataCategory.FUNDAMENTALS

    def test_fetch_does_not_call_fallback_on_success(self):
        registry = ProviderRegistry()
        primary = FakeProvider("primary", [DataCategory.FUNDAMENTALS], priority=10)
        fallback = FakeProvider("fallback", [DataCategory.FUNDAMENTALS], priority=1)
        registry.register(primary)
        registry.register(fallback)

        registry.fetch(DataCategory.FUNDAMENTALS, "AAPL")

        assert len(primary.calls) == 1
        assert len(fallback.calls) == 0


# ---------------------------------------------------------------------------
# Tests: fetch falls back on first provider failure
# ---------------------------------------------------------------------------


class TestFetchFallback:
    def test_falls_back_to_second_provider_on_failure(self):
        registry = ProviderRegistry()
        failing = FakeProvider(
            "failing",
            [DataCategory.PRICE],
            priority=10,
            should_fail=True,
        )
        working = FakeProvider("working", [DataCategory.PRICE], priority=5)
        registry.register(failing)
        registry.register(working)

        result = registry.fetch(DataCategory.PRICE, "MSFT")

        assert result.success is True
        assert result.provider_name == "working"

    def test_falls_back_through_multiple_failures(self):
        registry = ProviderRegistry()
        fail1 = FakeProvider("fail1", [DataCategory.INSIDER], priority=10, should_fail=True)
        fail2 = FakeProvider("fail2", [DataCategory.INSIDER], priority=5, should_fail=True)
        success = FakeProvider("success", [DataCategory.INSIDER], priority=1)
        registry.register(fail1)
        registry.register(fail2)
        registry.register(success)

        result = registry.fetch(DataCategory.INSIDER, "GOOG")

        assert result.success is True
        assert result.provider_name == "success"

    def test_fallback_with_custom_exception(self):
        registry = ProviderRegistry()
        failing = FakeProvider(
            "failing",
            [DataCategory.EARNINGS],
            priority=10,
            should_fail=True,
            fail_exception=ConnectionError("timeout"),
        )
        working = FakeProvider("working", [DataCategory.EARNINGS], priority=5)
        registry.register(failing)
        registry.register(working)

        result = registry.fetch(DataCategory.EARNINGS, "NFLX")

        assert result.success is True
        assert result.provider_name == "working"


# ---------------------------------------------------------------------------
# Tests: fetch all fail returns error
# ---------------------------------------------------------------------------


class TestFetchAllFail:
    def test_all_providers_fail_returns_error(self):
        registry = ProviderRegistry()
        fail1 = FakeProvider(
            "fail1",
            [DataCategory.FUNDAMENTALS],
            priority=10,
            should_fail=True,
            fail_exception=RuntimeError("fail1 error"),
        )
        fail2 = FakeProvider(
            "fail2",
            [DataCategory.FUNDAMENTALS],
            priority=5,
            should_fail=True,
            fail_exception=RuntimeError("fail2 error"),
        )
        registry.register(fail1)
        registry.register(fail2)

        result = registry.fetch(DataCategory.FUNDAMENTALS, "AAPL")

        assert result.success is False
        assert result.error is not None
        assert "fail1" in result.error
        assert "fail2" in result.error

    def test_all_fail_result_has_correct_metadata(self):
        registry = ProviderRegistry()
        fail1 = FakeProvider("fail1", [DataCategory.PRICE], priority=10, should_fail=True)
        registry.register(fail1)

        result = registry.fetch(DataCategory.PRICE, "TSLA")

        assert result.success is False
        assert result.ticker == "TSLA"
        assert result.category == DataCategory.PRICE
        assert result.raw_data == {}


# ---------------------------------------------------------------------------
# Tests: empty chain (no providers for category)
# ---------------------------------------------------------------------------


class TestFetchEmptyChain:
    def test_fetch_no_providers_returns_error(self):
        registry = ProviderRegistry()

        result = registry.fetch(DataCategory.FUNDAMENTALS, "AAPL")

        assert result.success is False
        assert result.error is not None
        assert "No providers available" in result.error

    def test_fetch_no_providers_for_category(self):
        registry = ProviderRegistry()
        registry.register(FakeProvider("price_only", [DataCategory.PRICE]))

        result = registry.fetch(DataCategory.INSIDER, "AAPL")

        assert result.success is False
        assert "No providers available" in result.error


# ---------------------------------------------------------------------------
# Tests: rate limiter integration
# ---------------------------------------------------------------------------


class TestRateLimiterIntegration:
    def test_rate_limited_provider_skipped_falls_back(self):
        rate_registry = RateLimiterRegistry()
        rate_registry.register("rate_limited", 1)

        registry = ProviderRegistry(rate_limiter_registry=rate_registry)
        limited = FakeProvider("rate_limited", [DataCategory.FUNDAMENTALS], priority=10)
        backup = FakeProvider("backup", [DataCategory.FUNDAMENTALS], priority=5)
        registry.register(limited)
        registry.register(backup)

        # Exhaust the rate limit for the first provider
        rate_registry.get("rate_limited").acquire()

        result = registry.fetch(DataCategory.FUNDAMENTALS, "AAPL")

        assert result.success is True
        assert result.provider_name == "backup"
        # The rate-limited provider should not have been called
        assert len(limited.calls) == 0

    def test_rate_limiter_allows_when_tokens_available(self):
        rate_registry = RateLimiterRegistry()
        rate_registry.register("primary", 60)

        registry = ProviderRegistry(rate_limiter_registry=rate_registry)
        primary = FakeProvider("primary", [DataCategory.PRICE], priority=10)
        registry.register(primary)

        result = registry.fetch(DataCategory.PRICE, "AAPL")

        assert result.success is True
        assert result.provider_name == "primary"

    def test_no_rate_limiter_still_works(self):
        """If no rate limiter registry, all providers are tried normally."""
        registry = ProviderRegistry()
        provider = FakeProvider("normal", [DataCategory.EARNINGS], priority=5)
        registry.register(provider)

        result = registry.fetch(DataCategory.EARNINGS, "GOOG")

        assert result.success is True
        assert result.provider_name == "normal"

    def test_provider_without_limiter_entry_still_works(self):
        """Provider not registered in rate limiter should still be tried."""
        rate_registry = RateLimiterRegistry()
        # Note: do NOT register "unregistered" in the rate limiter
        registry = ProviderRegistry(rate_limiter_registry=rate_registry)
        provider = FakeProvider("unregistered", [DataCategory.PRICE], priority=5)
        registry.register(provider)

        result = registry.fetch(DataCategory.PRICE, "AAPL")

        assert result.success is True
        assert result.provider_name == "unregistered"


# ---------------------------------------------------------------------------
# Tests: fetch with kwargs passed through
# ---------------------------------------------------------------------------


class TestFetchWithKwargs:
    def test_price_fetch_passes_days_kwarg(self):
        registry = ProviderRegistry()
        provider = FakeProvider("price_src", [DataCategory.PRICE], priority=10)
        registry.register(provider)

        result = registry.fetch(DataCategory.PRICE, "AAPL", days=30)

        assert result.success is True
        assert result.raw_data["days"] == 30
        # Verify the kwarg was actually passed
        assert provider.calls[0] == ("fetch_price_history", "AAPL", {"days": 30})

    def test_fundamentals_fetch_ignores_extra_kwargs(self):
        """Fundamentals doesn't take extra kwargs; they should not cause errors."""
        registry = ProviderRegistry()
        provider = FakeProvider("fund_src", [DataCategory.FUNDAMENTALS], priority=10)
        registry.register(provider)

        result = registry.fetch(DataCategory.FUNDAMENTALS, "AAPL")

        assert result.success is True
        assert provider.calls[0] == ("fetch_fundamentals", "AAPL", {})


# ---------------------------------------------------------------------------
# Tests: MACRO/NEWS raise NotImplementedError
# ---------------------------------------------------------------------------


class TestUnsupportedCategoryFetch:
    def test_macro_fetch_raises_not_implemented(self):
        registry = ProviderRegistry()
        provider = FakeProvider("fred", [DataCategory.MACRO], priority=10)
        registry.register(provider)

        with pytest.raises(NotImplementedError, match="MACRO"):
            registry.fetch(DataCategory.MACRO, "N/A")

    def test_news_fetch_raises_not_implemented(self):
        registry = ProviderRegistry()
        provider = FakeProvider("finnhub", [DataCategory.NEWS], priority=10)
        registry.register(provider)

        with pytest.raises(NotImplementedError, match="NEWS"):
            registry.fetch(DataCategory.NEWS, "N/A")


# ---------------------------------------------------------------------------
# Tests: real PolygonProvider in fallback chain
# ---------------------------------------------------------------------------


class TestPolygonInFallbackChain:
    """Verify real PolygonProvider integrates with registry correctly."""

    def test_polygon_is_primary_price_provider(self):
        from margin_engine.ingestion.providers.polygon_provider import PolygonProvider
        from margin_engine.ingestion.providers.yfinance_provider import YFinanceProvider

        registry = ProviderRegistry(api_keys={"polygon": "test_key"})
        registry.register(PolygonProvider(api_key="test_key"))
        registry.register(YFinanceProvider())

        chain = registry.get_fallback_chain(DataCategory.PRICE)
        names = [p.info.name for p in chain]
        assert names == ["polygon", "yfinance"]

    def test_polygon_excluded_without_api_key(self):
        from margin_engine.ingestion.providers.polygon_provider import PolygonProvider
        from margin_engine.ingestion.providers.yfinance_provider import YFinanceProvider

        registry = ProviderRegistry(api_keys={})
        registry.register(PolygonProvider(api_key="test_key"))
        registry.register(YFinanceProvider())

        chain = registry.get_fallback_chain(DataCategory.PRICE)
        names = [p.info.name for p in chain]
        assert names == ["yfinance"]

    def test_polygon_not_in_fundamentals_chain(self):
        from margin_engine.ingestion.providers.polygon_provider import PolygonProvider

        registry = ProviderRegistry(api_keys={"polygon": "test_key"})
        registry.register(PolygonProvider(api_key="test_key"))

        chain = registry.get_fallback_chain(DataCategory.FUNDAMENTALS)
        assert len(chain) == 0
