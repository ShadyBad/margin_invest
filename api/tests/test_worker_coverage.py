"""Tests covering the uncovered branches in worker.py."""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from margin_api.worker import (
    _parse_redis_settings,
    get_worker_settings,
    score_all_tickers,
    score_single_ticker,
)


class TestScoreAllTickers:
    @pytest.mark.asyncio
    async def test_empty_db(self):
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)
        factory_cm = AsyncMock()
        factory_cm.__aenter__ = AsyncMock(return_value=mock_session)
        factory_cm.__aexit__ = AsyncMock(return_value=False)
        factory = MagicMock(return_value=factory_cm)
        with (
            patch("margin_api.worker.get_engine", return_value=MagicMock()),
            patch("margin_api.worker.get_session_factory", return_value=factory),
        ):
            await score_all_tickers({})

    @pytest.mark.asyncio
    async def test_calls_score_ticker_for_each(self):
        calls: list[str] = []

        async def fake_ticker(*, ticker: str, session: AsyncMock) -> bool:
            calls.append(ticker)
            return True

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = ["AAPL", "MSFT"]
        mock_session.execute = AsyncMock(return_value=mock_result)
        factory_cm = AsyncMock()
        factory_cm.__aenter__ = AsyncMock(return_value=mock_session)
        factory_cm.__aexit__ = AsyncMock(return_value=False)
        factory = MagicMock(return_value=factory_cm)
        with (
            patch("margin_api.worker.get_engine", return_value=MagicMock()),
            patch("margin_api.worker.get_session_factory", return_value=factory),
            patch("margin_api.worker.score_ticker", side_effect=fake_ticker),
        ):
            await score_all_tickers({})

        assert calls == ["AAPL", "MSFT"]


class TestScoreSingleTicker:
    @pytest.mark.asyncio
    async def test_returns_true(self):
        factory_cm = AsyncMock()
        factory_cm.__aenter__ = AsyncMock(return_value=AsyncMock())
        factory_cm.__aexit__ = AsyncMock(return_value=False)
        factory = MagicMock(return_value=factory_cm)
        with (
            patch("margin_api.worker.get_engine", return_value=MagicMock()),
            patch("margin_api.worker.get_session_factory", return_value=factory),
            patch("margin_api.worker.score_ticker", new=AsyncMock(return_value=True)),
        ):
            result = await score_single_ticker({}, "AAPL")
        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false(self):
        factory_cm = AsyncMock()
        factory_cm.__aenter__ = AsyncMock(return_value=AsyncMock())
        factory_cm.__aexit__ = AsyncMock(return_value=False)
        factory = MagicMock(return_value=factory_cm)
        with (
            patch("margin_api.worker.get_engine", return_value=MagicMock()),
            patch("margin_api.worker.get_session_factory", return_value=factory),
            patch("margin_api.worker.score_ticker", new=AsyncMock(return_value=False)),
        ):
            result = await score_single_ticker({}, "ZZZZ")
        assert result is False


class TestParseRedisSettings:
    def test_returns_arq_settings(self):
        with patch.dict(os.environ, {"MARGIN_REDIS_URL": "redis://localhost:6379"}):
            from margin_api.config import get_settings

            get_settings.cache_clear()
            try:
                obj = _parse_redis_settings()
                assert obj is not None
                assert hasattr(obj, "host")
            finally:
                get_settings.cache_clear()


class TestGetWorkerSettings:
    def test_returns_class(self):
        with patch.dict(os.environ, {"MARGIN_REDIS_URL": "redis://localhost:6379"}):
            from margin_api.config import get_settings

            get_settings.cache_clear()
            try:
                cls = get_worker_settings()
                assert hasattr(cls, "functions")
                assert hasattr(cls, "redis_settings")
            finally:
                get_settings.cache_clear()

    def test_has_score_functions(self):
        from margin_api.worker import WorkerSettings

        names = [f.__name__ for f in WorkerSettings.functions]
        assert "score_all_tickers" in names
        assert "score_single_ticker" in names
