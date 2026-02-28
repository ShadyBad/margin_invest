"""Tests for async PIT provider protocol and async replay."""

from datetime import date

import pytest
from margin_engine.backtesting import FactorRegistry, ReplayConfig, ReplayOrchestrator
from margin_engine.backtesting.pit_provider import (
    AsyncPointInTimeProvider,
)


class FakeAsyncProvider:
    """Test implementation of AsyncPointInTimeProvider."""

    async def get_universe(self, as_of_date):
        return []

    async def get_snapshot(self, ticker, as_of_date):
        return None

    async def get_price(self, ticker, as_of_date):
        return 100.0

    async def get_delisting(self, ticker):
        return None


def test_fake_async_provider_satisfies_protocol():
    provider = FakeAsyncProvider()
    assert isinstance(provider, AsyncPointInTimeProvider)


@pytest.mark.asyncio
async def test_async_provider_methods():
    provider = FakeAsyncProvider()
    price = await provider.get_price("AAPL", date(2024, 1, 1))
    assert price == 100.0
    universe = await provider.get_universe(date(2024, 1, 1))
    assert universe == []
    snap = await provider.get_snapshot("AAPL", date(2024, 1, 1))
    assert snap is None
    delist = await provider.get_delisting("AAPL")
    assert delist is None


@pytest.mark.asyncio
async def test_replay_orchestrator_run_async_empty():
    """run_async with empty provider should produce empty result."""
    provider = FakeAsyncProvider()
    config = ReplayConfig(start_date=date(2024, 1, 1), end_date=date(2024, 6, 1))
    orchestrator = ReplayOrchestrator(
        config=config,
        pit_provider=provider,
        factor_registry=FactorRegistry.default(),
    )
    result = await orchestrator.run_async()
    assert result.metrics.num_months == 0
