"""Tests for the ARQ background worker (score_ticker function).

Uses mocked DB sessions and scoring pipeline to verify the worker
correctly loads data, runs scoring, and persists Score rows.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from margin_api.db.models import Asset, FinancialData, Score
from margin_api.worker import score_ticker
from margin_engine.models.scoring import (
    CompositeScore,
    ConvictionLevel,
    FactorBreakdown,
    FactorScore,
    GrowthStage,
    Signal,
)

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _make_asset(
    id: int = 1,
    ticker: str = "AAPL",
    name: str = "Apple Inc.",
    sector: str = "Information Technology",
    market_cap: Decimal = Decimal("3000000000000"),
) -> Asset:
    """Create a mock Asset object."""
    asset = MagicMock(spec=Asset)
    asset.id = id
    asset.ticker = ticker
    asset.name = name
    asset.sector = sector
    asset.market_cap = market_cap
    return asset


def _make_financial_data(
    asset_id: int = 1,
    period_end: str = "2024-09-28",
    filing_date: str = "2024-11-01",
) -> FinancialData:
    """Create a mock FinancialData object with realistic JSONB data."""
    fd = MagicMock(spec=FinancialData)
    fd.asset_id = asset_id
    fd.period_end = period_end
    fd.filing_date = filing_date
    fd.income_statement = {"revenue": "391035000000", "grossProfit": "176898000000"}
    fd.balance_sheet = {"totalAssets": "352583000000", "totalStockholdersEquity": "62146000000"}
    fd.cash_flow = {"operatingCashFlow": "118254000000", "capitalExpenditure": "-9959000000"}
    fd.price_history = [
        {
            "date": "2024-09-27",
            "open": "195.0",
            "high": "196.0",
            "low": "194.0",
            "close": "195.5",
            "volume": 50000000,
        },
    ]
    fd.earnings_data = [
        {"quarter": "2024-Q4", "actual_eps": "2.40", "expected_eps": "2.35"},
    ]
    fd.fetched_at = datetime(2024, 11, 15, tzinfo=UTC)
    return fd


def _make_composite_score(ticker: str = "AAPL") -> CompositeScore:
    """Build a minimal CompositeScore for mocking the pipeline return."""
    quality = FactorBreakdown(
        factor_name="quality",
        weight=0.35,
        sub_scores=[
            FactorScore(name="gross_profitability", raw_value=0.45, percentile_rank=72.0),
        ],
    )
    value = FactorBreakdown(
        factor_name="value",
        weight=0.30,
        sub_scores=[
            FactorScore(name="ev_fcf", raw_value=15.0, percentile_rank=55.0),
        ],
    )
    momentum = FactorBreakdown(
        factor_name="momentum",
        weight=0.35,
        sub_scores=[
            FactorScore(name="price_momentum", raw_value=0.12, percentile_rank=65.0),
        ],
    )
    return CompositeScore(
        ticker=ticker,
        composite_percentile=64.0,
        quality=quality,
        value=value,
        momentum=momentum,
        filters_passed=[],
        data_coverage=0.85,
        growth_stage=GrowthStage.STEADY_GROWTH,
    )


def _mock_session_execute(asset, fin_data):
    """Create an async side_effect for session.execute that returns asset then fin_data.

    The first call returns asset (for the Asset query), the second returns
    fin_data (for the FinancialData query).
    """
    call_count = 0

    async def _execute(stmt):
        nonlocal call_count
        call_count += 1
        mock_result = MagicMock()
        if call_count == 1:
            mock_result.scalar_one_or_none.return_value = asset
        else:
            mock_result.scalar_one_or_none.return_value = fin_data
        return mock_result

    return _execute


def _make_session(asset=None, fin_data=None) -> AsyncMock:
    """Build a mock AsyncSession with execute side-effect and sync add.

    SQLAlchemy's session.add() is synchronous, so we override it with a
    plain MagicMock to avoid RuntimeWarnings from unawaited coroutines.
    """
    session = AsyncMock()
    session.add = MagicMock()
    session.execute = AsyncMock(side_effect=_mock_session_execute(asset, fin_data))
    return session


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestScoreTickerSuccess:
    """Test that score_ticker succeeds with valid asset + financial data."""

    @pytest.mark.asyncio
    async def test_returns_true(self):
        asset = _make_asset()
        fin_data = _make_financial_data()
        composite = _make_composite_score()
        session = _make_session(asset, fin_data)

        with (
            patch("margin_api.worker.run_scoring_pipeline", return_value=composite),
            patch("margin_api.worker.build_financial_period") as mock_period,
            patch("margin_api.worker.build_asset_profile") as mock_profile,
        ):
            mock_period.return_value = MagicMock()
            mock_profile.return_value = MagicMock()

            result = await score_ticker(ticker="AAPL", session=session)

        assert result is True

    @pytest.mark.asyncio
    async def test_calls_session_add_with_score(self):
        asset = _make_asset()
        fin_data = _make_financial_data()
        composite = _make_composite_score()
        session = _make_session(asset, fin_data)

        with (
            patch("margin_api.worker.run_scoring_pipeline", return_value=composite),
            patch("margin_api.worker.build_financial_period") as mock_period,
            patch("margin_api.worker.build_asset_profile") as mock_profile,
        ):
            mock_period.return_value = MagicMock()
            mock_profile.return_value = MagicMock()

            await score_ticker(ticker="AAPL", session=session)

        session.add.assert_called_once()
        added_obj = session.add.call_args[0][0]
        assert isinstance(added_obj, Score)

    @pytest.mark.asyncio
    async def test_score_fields_match_composite(self):
        asset = _make_asset()
        fin_data = _make_financial_data()
        composite = _make_composite_score()
        session = _make_session(asset, fin_data)

        with (
            patch("margin_api.worker.run_scoring_pipeline", return_value=composite),
            patch("margin_api.worker.build_financial_period") as mock_period,
            patch("margin_api.worker.build_asset_profile") as mock_profile,
        ):
            mock_period.return_value = MagicMock()
            mock_profile.return_value = MagicMock()

            await score_ticker(ticker="AAPL", session=session)

        added_score: Score = session.add.call_args[0][0]
        assert added_score.asset_id == 1
        assert added_score.composite_percentile == 64.0
        assert added_score.conviction_level == ConvictionLevel.NONE.value
        assert added_score.signal == Signal.NO_ACTION.value
        assert added_score.quality_percentile == composite.quality.average_percentile
        assert added_score.value_percentile == composite.value.average_percentile
        assert added_score.momentum_percentile == composite.momentum.average_percentile
        assert added_score.data_coverage == 0.85
        assert added_score.growth_stage == GrowthStage.STEADY_GROWTH.value

    @pytest.mark.asyncio
    async def test_commits_session(self):
        asset = _make_asset()
        fin_data = _make_financial_data()
        composite = _make_composite_score()
        session = _make_session(asset, fin_data)

        with (
            patch("margin_api.worker.run_scoring_pipeline", return_value=composite),
            patch("margin_api.worker.build_financial_period") as mock_period,
            patch("margin_api.worker.build_asset_profile") as mock_profile,
        ):
            mock_period.return_value = MagicMock()
            mock_profile.return_value = MagicMock()

            await score_ticker(ticker="AAPL", session=session)

        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_builds_period_with_financial_data(self):
        asset = _make_asset()
        fin_data = _make_financial_data()
        composite = _make_composite_score()
        session = _make_session(asset, fin_data)

        with (
            patch("margin_api.worker.run_scoring_pipeline", return_value=composite),
            patch("margin_api.worker.build_financial_period") as mock_period,
            patch("margin_api.worker.build_asset_profile") as mock_profile,
        ):
            mock_period.return_value = MagicMock()
            mock_profile.return_value = MagicMock()

            await score_ticker(ticker="AAPL", session=session)

        mock_period.assert_called_once_with(
            income_raw=fin_data.income_statement,
            balance_raw=fin_data.balance_sheet,
            cashflow_raw=fin_data.cash_flow,
            period_end=fin_data.period_end,
            filing_date=fin_data.filing_date,
        )

    @pytest.mark.asyncio
    async def test_builds_profile_with_asset_data(self):
        asset = _make_asset()
        fin_data = _make_financial_data()
        composite = _make_composite_score()
        session = _make_session(asset, fin_data)

        with (
            patch("margin_api.worker.run_scoring_pipeline", return_value=composite),
            patch("margin_api.worker.build_financial_period") as mock_period,
            patch("margin_api.worker.build_asset_profile") as mock_profile,
        ):
            mock_period.return_value = MagicMock()
            mock_profile.return_value = MagicMock()

            await score_ticker(ticker="AAPL", session=session)

        mock_profile.assert_called_once_with(
            ticker="AAPL",
            name="Apple Inc.",
            sector="Information Technology",
            market_cap=Decimal("3000000000000"),
        )


class TestScoreTickerNoAsset:
    """Test that score_ticker returns False when the asset is not found."""

    @pytest.mark.asyncio
    async def test_returns_false(self):
        session = _make_session(asset=None, fin_data=None)

        result = await score_ticker(ticker="UNKNOWN", session=session)

        assert result is False

    @pytest.mark.asyncio
    async def test_does_not_add_score(self):
        session = _make_session(asset=None, fin_data=None)

        await score_ticker(ticker="UNKNOWN", session=session)

        session.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_does_not_commit(self):
        session = _make_session(asset=None, fin_data=None)

        await score_ticker(ticker="UNKNOWN", session=session)

        session.commit.assert_not_awaited()


class TestScoreTickerNoFinancialData:
    """Test that score_ticker returns False when financial data is missing."""

    @pytest.mark.asyncio
    async def test_returns_false(self):
        asset = _make_asset()
        session = _make_session(asset=asset, fin_data=None)

        result = await score_ticker(ticker="AAPL", session=session)

        assert result is False

    @pytest.mark.asyncio
    async def test_does_not_add_score(self):
        asset = _make_asset()
        session = _make_session(asset=asset, fin_data=None)

        await score_ticker(ticker="AAPL", session=session)

        session.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_does_not_commit(self):
        asset = _make_asset()
        session = _make_session(asset=asset, fin_data=None)

        await score_ticker(ticker="AAPL", session=session)

        session.commit.assert_not_awaited()


class TestScoreTickerException:
    """Test that score_ticker handles exceptions gracefully."""

    @pytest.mark.asyncio
    async def test_returns_false_on_exception(self):
        asset = _make_asset()
        fin_data = _make_financial_data()
        session = _make_session(asset, fin_data)

        with patch("margin_api.worker.build_financial_period", side_effect=ValueError("boom")):
            result = await score_ticker(ticker="AAPL", session=session)

        assert result is False

    @pytest.mark.asyncio
    async def test_rolls_back_on_exception(self):
        asset = _make_asset()
        fin_data = _make_financial_data()
        session = _make_session(asset, fin_data)

        with patch("margin_api.worker.build_financial_period", side_effect=ValueError("boom")):
            await score_ticker(ticker="AAPL", session=session)

        session.rollback.assert_awaited_once()
