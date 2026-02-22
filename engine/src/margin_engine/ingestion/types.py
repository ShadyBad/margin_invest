"""Abstract contracts and types for all data providers.

Defines the DataCategory enum, provider metadata models, fetch result
types, and the DataProvider abstract base class that all concrete
providers must implement.

Data category fallback chains:
    Fundamentals:  FMP -> yfinance -> SEC EDGAR XBRL
    Price:         Polygon -> yfinance
    Insider:       SEC EDGAR Form 4 -> Finnhub
    Institutional: SEC EDGAR 13F -> Finnhub
    Macro:         FRED (no fallback)
    News:          Finnhub -> FMP
    Earnings:      Finnhub
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import StrEnum

from pydantic import BaseModel


class DataCategory(StrEnum):
    """Categories of financial data the system can ingest."""

    FUNDAMENTALS = "fundamentals"
    PRICE = "price"
    INSIDER = "insider"
    INSTITUTIONAL = "institutional"
    MACRO = "macro"
    NEWS = "news"
    EARNINGS = "earnings"


class ProviderInfo(BaseModel):
    """Metadata describing a data provider's capabilities and constraints."""

    name: str
    """Unique provider name (e.g., 'yfinance', 'finnhub')."""

    supported_categories: list[DataCategory]
    """What data categories this provider can fetch."""

    requests_per_minute: int
    """Rate limit for this provider."""

    requires_api_key: bool
    """Whether an API key is needed to use this provider."""

    priority: int = 0
    """Higher values = preferred provider (used for fallback ordering)."""


class FetchResult(BaseModel):
    """Result of a single data fetch operation from a provider."""

    provider_name: str
    """Which provider returned this data."""

    category: DataCategory
    """What type of data was fetched."""

    ticker: str
    """Stock symbol."""

    raw_data: dict
    """The raw response data (will be normalized later)."""

    fetched_at: str
    """ISO datetime of when data was fetched."""

    success: bool = True
    """Whether the fetch succeeded."""

    error: str | None = None
    """Error message if the fetch failed."""


class DataProvider(ABC):
    """Abstract base class for all data providers.

    Concrete providers must implement the ``info`` property. All fetch
    methods have default implementations that raise ``NotImplementedError``,
    so subclasses only need to override the methods they support.
    """

    @property
    @abstractmethod
    def info(self) -> ProviderInfo:
        """Return metadata about this provider."""
        ...

    def fetch_fundamentals(self, ticker: str) -> FetchResult:
        """Fetch fundamental financial data for a ticker."""
        raise NotImplementedError(f"{self.info.name} does not support fetch_fundamentals")

    def fetch_price_history(self, ticker: str, days: int = 365) -> FetchResult:
        """Fetch historical price data for a ticker."""
        raise NotImplementedError(f"{self.info.name} does not support fetch_price_history")

    def fetch_insider_transactions(self, ticker: str) -> FetchResult:
        """Fetch insider transaction data for a ticker."""
        raise NotImplementedError(f"{self.info.name} does not support fetch_insider_transactions")

    def fetch_institutional_holdings(self, ticker: str) -> FetchResult:
        """Fetch institutional holdings data for a ticker."""
        raise NotImplementedError(f"{self.info.name} does not support fetch_institutional_holdings")

    def fetch_earnings(self, ticker: str) -> FetchResult:
        """Fetch earnings data for a ticker."""
        raise NotImplementedError(f"{self.info.name} does not support fetch_earnings")
