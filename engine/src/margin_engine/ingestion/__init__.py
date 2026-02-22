"""Data ingestion layer — provider abstraction, rate limiting, registry, and normalization."""

from margin_engine.ingestion.circuit_breaker import CircuitBreaker, CircuitState
from margin_engine.ingestion.normalizer import (
    normalize_balance_sheet,
    normalize_cash_flow,
    normalize_earnings_list,
    normalize_earnings_surprise,
    normalize_fundamentals,
    normalize_income_statement,
    normalize_price_bar,
)
from margin_engine.ingestion.providers.polygon_provider import PolygonProvider
from margin_engine.ingestion.providers.yfinance_provider import YFinanceProvider
from margin_engine.ingestion.rate_limiter import RateLimiter, RateLimiterRegistry
from margin_engine.ingestion.registry import ProviderRegistry
from margin_engine.ingestion.retry import retry_transient
from margin_engine.ingestion.symbol_mapper import SymbolMapper
from margin_engine.ingestion.types import (
    DataCategory,
    DataProvider,
    FetchResult,
    ProviderInfo,
)

__all__ = [
    "CircuitBreaker",
    "CircuitState",
    "DataCategory",
    "DataProvider",
    "FetchResult",
    "normalize_balance_sheet",
    "normalize_cash_flow",
    "normalize_earnings_list",
    "normalize_earnings_surprise",
    "normalize_fundamentals",
    "normalize_income_statement",
    "normalize_price_bar",
    "PolygonProvider",
    "ProviderInfo",
    "ProviderRegistry",
    "RateLimiter",
    "RateLimiterRegistry",
    "retry_transient",
    "SymbolMapper",
    "YFinanceProvider",
]
