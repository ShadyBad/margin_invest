"""Point-in-time data provider for historical backtesting.

Defines the protocol for accessing historical market data as it was known
at any given date, and provides an in-memory implementation for testing.
"""

from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Protocol, runtime_checkable

from pydantic import BaseModel

from margin_engine.models.financial import AssetProfile, FinancialPeriod


class DelistingType(StrEnum):
    """How a stock left the market."""

    BANKRUPTCY = "bankruptcy"
    ACQUISITION = "acquisition"
    VOLUNTARY = "voluntary"


class DelistingEvent(BaseModel):
    """Record of a stock delisting."""

    ticker: str
    delist_date: date
    delist_type: DelistingType
    last_price: float
    acquisition_price: float | None = None

    @property
    def settlement_value(self) -> float:
        """Value returned to shareholders at delisting."""
        if self.delist_type == DelistingType.BANKRUPTCY:
            return 0.0
        if self.delist_type == DelistingType.ACQUISITION and self.acquisition_price is not None:
            return self.acquisition_price
        return self.last_price


class PITSnapshot(BaseModel):
    """Point-in-time data for a single ticker at a single date."""

    ticker: str
    as_of_date: date
    profile: AssetProfile
    period: FinancialPeriod
    price: float
    filing_date: date | None = None


@runtime_checkable
class PointInTimeProvider(Protocol):
    """Protocol for point-in-time historical data access.

    All data returned must reflect what was publicly known at the
    as_of_date — no future data leakage.
    """

    def get_universe(self, as_of_date: date) -> list[PITSnapshot]:
        """Return all tradeable stocks at the given date."""
        ...

    def get_snapshot(self, ticker: str, as_of_date: date) -> PITSnapshot | None:
        """Return point-in-time data for a specific ticker."""
        ...

    def get_price(self, ticker: str, as_of_date: date) -> float | None:
        """Return closing price for a ticker at the given date."""
        ...

    def get_delisting(self, ticker: str) -> DelistingEvent | None:
        """Return delisting event for a ticker, or None if still listed."""
        ...


class InMemoryPITProvider:
    """In-memory implementation of PointInTimeProvider for testing."""

    def __init__(self) -> None:
        self._snapshots: dict[tuple[date, str], PITSnapshot] = {}
        self._delistings: dict[str, DelistingEvent] = {}

    def add_snapshot(
        self,
        as_of_date: date,
        ticker: str,
        profile: AssetProfile,
        period: FinancialPeriod,
        price: float,
        filing_date: date | None = None,
    ) -> None:
        """Add a point-in-time snapshot for a ticker at a date."""
        self._snapshots[(as_of_date, ticker)] = PITSnapshot(
            ticker=ticker,
            as_of_date=as_of_date,
            profile=profile,
            period=period,
            price=price,
            filing_date=filing_date,
        )

    def add_delisting(self, ticker: str, event: DelistingEvent) -> None:
        """Register a delisting event for a ticker."""
        self._delistings[ticker] = event

    def get_universe(self, as_of_date: date) -> list[PITSnapshot]:
        """Return most recent snapshot per ticker at or before date, excluding delisted."""
        # Collect the most recent snapshot for each ticker at or before as_of_date
        latest: dict[str, PITSnapshot] = {}
        for (snap_date, ticker), snapshot in self._snapshots.items():
            if snap_date > as_of_date:
                continue
            existing = latest.get(ticker)
            if existing is None or snap_date > existing.as_of_date:
                latest[ticker] = snapshot

        # Filter out delisted tickers
        result = []
        for ticker, snapshot in latest.items():
            delisting = self._delistings.get(ticker)
            if delisting and delisting.delist_date <= as_of_date:
                continue
            result.append(snapshot)
        return result

    def get_snapshot(self, ticker: str, as_of_date: date) -> PITSnapshot | None:
        """Return the most recent snapshot for a ticker at or before the given date."""
        best: PITSnapshot | None = None
        for (snap_date, snap_ticker), snapshot in self._snapshots.items():
            if snap_ticker != ticker or snap_date > as_of_date:
                continue
            if best is None or snap_date > best.as_of_date:
                best = snapshot
        return best

    def get_price(self, ticker: str, as_of_date: date) -> float | None:
        """Return price for a ticker at the given date."""
        snapshot = self.get_snapshot(ticker, as_of_date)
        return snapshot.price if snapshot else None

    def get_delisting(self, ticker: str) -> DelistingEvent | None:
        """Return delisting event for a ticker."""
        return self._delistings.get(ticker)
