"""Provider registry with automatic fallback chains.

Manages data providers keyed by :class:`DataCategory`, building
priority-ordered fallback chains at runtime. Providers that require an
API key are excluded from chains when no key is supplied.

Fallback chain design:
    Fundamentals:  FMP -> yfinance -> SEC EDGAR XBRL
    Price:         Polygon -> yfinance
    Insider:       SEC EDGAR Form 4 -> Finnhub
    Institutional: SEC EDGAR 13F -> Finnhub
    Macro:         FRED (no fallback)
    News:          Finnhub -> FMP
    Earnings:      Finnhub
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from margin_engine.ingestion.rate_limiter import RateLimiterRegistry
from margin_engine.ingestion.types import (
    DataCategory,
    DataProvider,
    FetchResult,
    ProviderInfo,
)

logger = logging.getLogger(__name__)

# Categories whose fetch methods do not take a single ticker argument.
# These are not yet supported by the registry's ``fetch()`` method.
_NON_TICKER_CATEGORIES: frozenset[DataCategory] = frozenset(
    {DataCategory.MACRO, DataCategory.NEWS}
)

# Maps a DataCategory to the DataProvider method name used for fetching.
_CATEGORY_METHOD_MAP: dict[DataCategory, str] = {
    DataCategory.FUNDAMENTALS: "fetch_fundamentals",
    DataCategory.PRICE: "fetch_price_history",
    DataCategory.INSIDER: "fetch_insider_transactions",
    DataCategory.INSTITUTIONAL: "fetch_institutional_holdings",
    DataCategory.EARNINGS: "fetch_earnings",
}


class ProviderRegistry:
    """Registry that manages data providers with automatic fallback.

    Providers are registered and then grouped by their supported
    categories.  When :meth:`fetch` is called for a category, the
    registry tries each provider in priority order (highest first)
    until one succeeds, skipping providers that are rate-limited or
    missing a required API key.
    """

    def __init__(
        self,
        api_keys: dict[str, str] | None = None,
        rate_limiter_registry: RateLimiterRegistry | None = None,
    ) -> None:
        """Create a registry, optionally with available API keys.

        Args:
            api_keys: Maps ``provider_name -> api_key`` string.
                Providers that ``require_api_key`` but have no key (or
                an empty-string key) are excluded from fallback chains.
            rate_limiter_registry: Optional rate-limiter registry.  When
                present, the registry checks whether a provider is
                rate-limited before calling it, falling back to the next
                provider if the limiter returns ``False``.
        """
        self._api_keys: dict[str, str] = api_keys if api_keys is not None else {}
        self._rate_limiter_registry = rate_limiter_registry
        self._providers: list[DataProvider] = []

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, provider: DataProvider) -> None:
        """Register a data provider."""
        self._providers.append(provider)

    # ------------------------------------------------------------------
    # Fallback chain
    # ------------------------------------------------------------------

    def get_fallback_chain(self, category: DataCategory) -> list[DataProvider]:
        """Get the ordered fallback chain for a data category.

        Returns providers sorted by priority (highest first).
        Excludes providers that require an API key but don't have one
        (or have an empty string key).
        """
        eligible: list[DataProvider] = []
        for provider in self._providers:
            info = provider.info
            if category not in info.supported_categories:
                continue
            if info.requires_api_key and not self._api_keys.get(info.name):
                continue
            eligible.append(provider)

        # Sort by priority descending (highest first)
        eligible.sort(key=lambda p: p.info.priority, reverse=True)
        return eligible

    # ------------------------------------------------------------------
    # Fetch with fallback
    # ------------------------------------------------------------------

    def fetch(
        self, category: DataCategory, ticker: str, **kwargs: object
    ) -> FetchResult:
        """Fetch data using the fallback chain for the given category.

        Tries each provider in order.  Returns the first successful
        result.  If all providers fail, returns a :class:`FetchResult`
        with ``success=False`` and an error describing all failures.

        Args:
            category: The data category to fetch.
            ticker: Stock ticker symbol.
            **kwargs: Extra keyword arguments forwarded to the
                underlying fetch method (e.g. ``days`` for price).

        Raises:
            NotImplementedError: If *category* is MACRO or NEWS (these
                do not use a ticker-based fetch and are not yet
                supported).
        """
        if category in _NON_TICKER_CATEGORIES:
            raise NotImplementedError(
                f"Fetching {category.name} data is not yet supported by the registry"
            )

        chain = self.get_fallback_chain(category)

        if not chain:
            return FetchResult(
                provider_name="",
                category=category,
                ticker=ticker,
                raw_data={},
                fetched_at=datetime.now(UTC).isoformat(),
                success=False,
                error=f"No providers available for {category.value}",
            )

        method_name = _CATEGORY_METHOD_MAP[category]
        errors: list[str] = []

        for provider in chain:
            name = provider.info.name

            # Check rate limiter if one is registered for this provider
            if self._rate_limiter_registry is not None:
                try:
                    if not self._rate_limiter_registry.acquire(name):
                        logger.info(
                            "Provider %s rate-limited, trying next", name
                        )
                        errors.append(f"{name}: rate limited")
                        continue
                except KeyError:
                    # Provider not registered in the rate limiter; proceed
                    pass

            try:
                method = getattr(provider, method_name)
                if category == DataCategory.PRICE:
                    result: FetchResult = method(ticker, **kwargs)
                else:
                    result = method(ticker)
                if result.success:
                    return result
                # Provider returned a non-success result
                msg = result.error or "returned success=False"
                errors.append(f"{name}: {msg}")
                logger.warning("Provider %s failed: %s", name, msg)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{name}: {exc}")
                logger.warning("Provider %s raised %s: %s", name, type(exc).__name__, exc)

        return FetchResult(
            provider_name="",
            category=category,
            ticker=ticker,
            raw_data={},
            fetched_at=datetime.now(UTC).isoformat(),
            success=False,
            error="All providers failed: " + "; ".join(errors),
        )

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    @property
    def registered_providers(self) -> list[ProviderInfo]:
        """List all registered provider infos."""
        return [p.info for p in self._providers]
