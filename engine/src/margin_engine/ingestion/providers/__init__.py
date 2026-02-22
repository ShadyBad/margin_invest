"""Concrete data provider implementations."""

from margin_engine.ingestion.providers.edgar_provider import EDGARProvider
from margin_engine.ingestion.providers.finnhub_provider import FinnhubProvider
from margin_engine.ingestion.providers.fmp_provider import FMPProvider
from margin_engine.ingestion.providers.polygon_provider import PolygonProvider
from margin_engine.ingestion.providers.yfinance_provider import YFinanceProvider

__all__ = ["EDGARProvider", "FinnhubProvider", "FMPProvider", "PolygonProvider", "YFinanceProvider"]
