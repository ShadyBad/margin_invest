"""Tests for V4Score.detail JSONB population.

Verifies that:
1. CompositeScore.model_dump(mode="json") produces the expected structure
   with quality, value, momentum factor breakdowns and filters_passed.
2. V4Score.detail can be persisted and read back from the DB.
3. The detail blob matches the structure used by V2 scoring.
"""

from __future__ import annotations

import datetime
from decimal import Decimal

import pytest
import pytest_asyncio
from margin_api.db.base import Base
from margin_api.db.models import Asset, V4Score
from margin_api.services.scoring import (
    build_asset_profile,
    build_financial_history_from_rows,
    build_financial_period,
    compute_raw_factor_scores,
    rank_and_compute_composites,
)
from margin_engine.models.financial import AssetProfile, FinancialHistory, FinancialPeriod
from margin_engine.models.scoring import CompositeScore
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# ---------------------------------------------------------------------------
# Test data helpers — same Apple-like numbers as test_scoring_service.py
# ---------------------------------------------------------------------------


def _income_raw() -> dict:
    return {
        "revenue": "391035000000",
        "costOfRevenue": "214137000000",
        "grossProfit": "176898000000",
        "ebit": "123216000000",
        "netIncome": "100913000000",
        "interestExpense": "3933000000",
        "incomeTaxExpense": "18679000000",
        "sharesOutstanding": 15408095000,
    }


def _balance_raw() -> dict:
    return {
        "totalAssets": "352583000000",
        "totalCurrentAssets": "152987000000",
        "cashAndCashEquivalents": "29965000000",
        "netReceivables": "66243000000",
        "totalLiabilities": "290437000000",
        "totalCurrentLiabilities": "176392000000",
        "longTermDebt": "96807000000",
        "totalStockholdersEquity": "62146000000",
        "retainedEarnings": "-214000000",
        "propertyPlantEquipmentNet": "44856000000",
        "sharesOutstanding": 15408095000,
    }


def _cashflow_raw() -> dict:
    return {
        "operatingCashFlow": "118254000000",
        "capitalExpenditure": "-9959000000",
        "dividendsPaid": "-15025000000",
        "commonStockRepurchased": "-94949000000",
        "commonStockIssued": "0",
    }


def _prior_income_raw() -> dict:
    return _income_raw() | {
        "revenue": "383285000000",
        "costOfRevenue": "209717000000",
        "grossProfit": "173568000000",
        "ebit": "118658000000",
        "netIncome": "96995000000",
        "interestExpense": "3468000000",
        "incomeTaxExpense": "16741000000",
    }


def _prior_balance_raw() -> dict:
    return _balance_raw() | {
        "totalAssets": "352755000000",
        "totalCurrentAssets": "143566000000",
        "cashAndCashEquivalents": "29965000000",
        "netReceivables": "60985000000",
        "totalLiabilities": "290020000000",
        "totalCurrentLiabilities": "145308000000",
        "longTermDebt": "95281000000",
        "totalStockholdersEquity": "62235000000",
    }


def _prior_cashflow_raw() -> dict:
    return _cashflow_raw() | {
        "operatingCashFlow": "110543000000",
        "capitalExpenditure": "-11062000000",
        "dividendsPaid": "-14996000000",
        "commonStockRepurchased": "-77550000000",
    }


def _price_bars_raw(n_bars: int = 260) -> list[dict]:
    """Generate ~1 year of daily price bars with a slight uptrend."""
    bars = []
    base_date = datetime.date(2024, 9, 28)
    base_price = 170.0
    for i in range(n_bars):
        d = base_date - datetime.timedelta(days=n_bars - 1 - i)
        price = base_price + i * 0.1
        bars.append(
            {
                "date": d.isoformat(),
                "open": str(round(price - 0.5, 2)),
                "high": str(round(price + 1.0, 2)),
                "low": str(round(price - 1.0, 2)),
                "close": str(round(price, 2)),
                "volume": 50000000,
            }
        )
    return bars


def _earnings_raw() -> list[dict]:
    return [
        {"quarter": "2024-Q1", "actual_eps": "2.18", "expected_eps": "2.10"},
        {"quarter": "2024-Q2", "actual_eps": "1.40", "expected_eps": "1.35"},
        {"quarter": "2024-Q3", "actual_eps": "1.46", "expected_eps": "1.39"},
        {"quarter": "2024-Q4", "actual_eps": "2.40", "expected_eps": "2.35"},
    ]


def _build_period_with_priors() -> FinancialPeriod:
    return build_financial_period(
        income_raw=_income_raw(),
        balance_raw=_balance_raw(),
        cashflow_raw=_cashflow_raw(),
        period_end="2024-09-28",
        filing_date="2024-11-01",
        prior_income_raw=_prior_income_raw(),
        prior_balance_raw=_prior_balance_raw(),
        prior_cashflow_raw=_prior_cashflow_raw(),
    )


def _build_profile() -> AssetProfile:
    return build_asset_profile(
        ticker="AAPL",
        name="Apple Inc.",
        sector="Information Technology",
        market_cap=Decimal("3000000000000"),
        avg_daily_volume=Decimal("10000000000"),
        years_of_history=44,
    )


def _build_history() -> FinancialHistory:
    rows = []
    for year in (2022, 2023, 2024):
        rows.append(
            {
                "period_end": f"{year}-09-28",
                "filing_date": f"{year}-11-01",
                "income_statement": _income_raw(),
                "balance_sheet": _balance_raw(),
                "cash_flow": _cashflow_raw(),
            }
        )
    return build_financial_history_from_rows("AAPL", rows)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def async_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def async_session(async_engine):
    factory = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestCompositeDetailBlobStructure:
    """Tests that composite.model_dump(mode='json') produces the expected detail structure."""

    def _compute_composite(self) -> CompositeScore:
        """Compute a single-ticker composite through the full pipeline."""
        period = _build_period_with_priors()
        profile = _build_profile()
        history = _build_history()

        raw = compute_raw_factor_scores(
            ticker="AAPL",
            period=period,
            profile=profile,
            price_bars_raw=_price_bars_raw(),
            earnings_raw=_earnings_raw(),
            history=history,
        )
        composites = rank_and_compute_composites([raw])
        assert len(composites) == 1
        return composites[0]

    def test_detail_has_ticker(self):
        composite = self._compute_composite()
        detail = composite.model_dump(mode="json")
        assert detail["ticker"] == "AAPL"

    def test_detail_has_quality_breakdown(self):
        composite = self._compute_composite()
        detail = composite.model_dump(mode="json")
        quality = detail["quality"]
        assert quality["factor_name"] == "quality"
        assert "weight" in quality
        assert "sub_scores" in quality
        assert isinstance(quality["sub_scores"], list)
        assert len(quality["sub_scores"]) >= 5
        # Check sub-score structure
        for sub in quality["sub_scores"]:
            assert "name" in sub
            assert "raw_value" in sub
            assert "percentile_rank" in sub

    def test_detail_has_value_breakdown(self):
        composite = self._compute_composite()
        detail = composite.model_dump(mode="json")
        value = detail["value"]
        assert value["factor_name"] == "value"
        assert "weight" in value
        assert "sub_scores" in value
        assert isinstance(value["sub_scores"], list)
        assert len(value["sub_scores"]) >= 4

    def test_detail_has_momentum_breakdown(self):
        composite = self._compute_composite()
        detail = composite.model_dump(mode="json")
        momentum = detail["momentum"]
        assert momentum["factor_name"] == "momentum"
        assert "weight" in momentum
        assert "sub_scores" in momentum
        assert isinstance(momentum["sub_scores"], list)
        assert len(momentum["sub_scores"]) >= 1

    def test_detail_has_filters_passed(self):
        composite = self._compute_composite()
        detail = composite.model_dump(mode="json")
        assert "filters_passed" in detail
        assert isinstance(detail["filters_passed"], list)
        assert len(detail["filters_passed"]) > 0
        # Check filter structure
        for f in detail["filters_passed"]:
            assert "name" in f
            assert "passed" in f

    def test_detail_has_composite_percentile(self):
        composite = self._compute_composite()
        detail = composite.model_dump(mode="json")
        assert "composite_percentile" in detail
        assert isinstance(detail["composite_percentile"], (int, float))
        assert 0.0 <= detail["composite_percentile"] <= 100.0

    def test_detail_has_data_coverage(self):
        composite = self._compute_composite()
        detail = composite.model_dump(mode="json")
        assert "data_coverage" in detail
        assert isinstance(detail["data_coverage"], (int, float))
        assert 0.0 <= detail["data_coverage"] <= 1.0

    def test_detail_has_growth_stage(self):
        composite = self._compute_composite()
        detail = composite.model_dump(mode="json")
        assert "growth_stage" in detail

    def test_detail_conviction_level_is_property(self):
        """conviction_level is a @property on CompositeScore, not in model_dump()."""
        composite = self._compute_composite()
        detail = composite.model_dump(mode="json")
        # conviction_level is a computed @property and is NOT in model_dump
        assert "conviction_level" not in detail
        # But the composite object itself has the property
        assert composite.conviction_level is not None

    def test_detail_signal_is_property(self):
        """signal is a @property on CompositeScore, not in model_dump()."""
        composite = self._compute_composite()
        detail = composite.model_dump(mode="json")
        # signal is a computed @property and is NOT in model_dump
        assert "signal" not in detail
        # But the composite object itself has the property
        assert composite.signal is not None


class TestV4ScoreDetailPersistence:
    """Tests that V4Score.detail can be persisted and read back from SQLite."""

    @pytest.mark.asyncio
    async def test_v4score_detail_roundtrip(self, async_session):
        """Persist a V4Score with detail and verify it round-trips."""
        # Build the composite detail blob
        period = _build_period_with_priors()
        profile = _build_profile()
        raw = compute_raw_factor_scores(
            ticker="AAPL",
            period=period,
            profile=profile,
            price_bars_raw=_price_bars_raw(),
            earnings_raw=_earnings_raw(),
        )
        composites = rank_and_compute_composites([raw])
        detail = composites[0].model_dump(mode="json")

        # Create asset
        asset = Asset(
            ticker="AAPL",
            name="Apple Inc.",
            sector="Information Technology",
            market_cap=Decimal("3000000000000"),
        )
        async_session.add(asset)
        await async_session.flush()

        # Create V4Score with detail
        score = V4Score(
            asset_id=asset.id,
            opportunity_type="quality_compounder",
            conviction="high",
            rules_conviction="high",
            track_a={"score": 0.8},
            track_b={"score": 0.7},
            track_c={"score": 0.6},
            style="blend",
            timing_signal="neutral",
            max_position_pct=2.0,
            regime="normal",
            composite_score=75.0,
            ml_override="none",
            detail=detail,
        )
        async_session.add(score)
        await async_session.commit()

        # Read back
        result = await async_session.execute(select(V4Score).where(V4Score.asset_id == asset.id))
        stored = result.scalar_one()

        assert stored.detail is not None
        assert stored.detail["ticker"] == "AAPL"
        assert "quality" in stored.detail
        assert "value" in stored.detail
        assert "momentum" in stored.detail
        assert "filters_passed" in stored.detail
        assert stored.detail["quality"]["factor_name"] == "quality"
        assert stored.detail["value"]["factor_name"] == "value"
        assert stored.detail["momentum"]["factor_name"] == "momentum"

    @pytest.mark.asyncio
    async def test_v4score_detail_null_when_not_set(self, async_session):
        """V4Score.detail should be None when not set (backward compatibility)."""
        asset = Asset(
            ticker="MSFT",
            name="Microsoft Corp",
            sector="Information Technology",
            market_cap=Decimal("2500000000000"),
        )
        async_session.add(asset)
        await async_session.flush()

        score = V4Score(
            asset_id=asset.id,
            opportunity_type="quality_compounder",
            conviction="medium",
            rules_conviction="medium",
            style="growth",
            timing_signal="neutral",
            max_position_pct=2.0,
            regime="normal",
            composite_score=65.0,
            ml_override="none",
        )
        async_session.add(score)
        await async_session.commit()

        result = await async_session.execute(select(V4Score).where(V4Score.asset_id == asset.id))
        stored = result.scalar_one()
        assert stored.detail is None

    @pytest.mark.asyncio
    async def test_v4score_detail_sub_score_structure(self, async_session):
        """Verify sub-scores in the persisted detail have the right keys."""
        period = _build_period_with_priors()
        profile = _build_profile()
        raw = compute_raw_factor_scores(
            ticker="AAPL",
            period=period,
            profile=profile,
            price_bars_raw=_price_bars_raw(),
            earnings_raw=_earnings_raw(),
        )
        composites = rank_and_compute_composites([raw])
        detail = composites[0].model_dump(mode="json")

        asset = Asset(
            ticker="AAPL",
            name="Apple Inc.",
            sector="Information Technology",
            market_cap=Decimal("3000000000000"),
        )
        async_session.add(asset)
        await async_session.flush()

        score = V4Score(
            asset_id=asset.id,
            opportunity_type="quality_compounder",
            conviction="high",
            rules_conviction="high",
            style="blend",
            timing_signal="neutral",
            max_position_pct=2.0,
            regime="normal",
            composite_score=75.0,
            ml_override="none",
            detail=detail,
        )
        async_session.add(score)
        await async_session.commit()

        result = await async_session.execute(select(V4Score).where(V4Score.asset_id == asset.id))
        stored = result.scalar_one()

        # Verify quality sub-scores
        quality_names = {s["name"] for s in stored.detail["quality"]["sub_scores"]}
        assert "gross_profitability" in quality_names
        assert "roic_wacc_spread" in quality_names
        assert "accrual_ratio" in quality_names
        assert "piotroski_f_score" in quality_names
        assert "fcf_conversion" in quality_names

        # Verify value sub-scores
        value_names = {s["name"] for s in stored.detail["value"]["sub_scores"]}
        assert "ev_fcf" in value_names
        assert "shareholder_yield" in value_names
        assert "dcf_margin_of_safety" in value_names
        assert "acquirers_multiple" in value_names

        # Verify momentum sub-scores
        momentum_names = {s["name"] for s in stored.detail["momentum"]["sub_scores"]}
        assert "multi_horizon_momentum" in momentum_names


class TestMultiTickerCompositeDetail:
    """Tests with multiple tickers to verify cross-sector ranking in composites."""

    def _build_second_ticker_data(self):
        """Build a second ticker (MSFT-like) for sector peer ranking."""
        period = build_financial_period(
            income_raw=_income_raw() | {"revenue": "250000000000", "netIncome": "80000000000"},
            balance_raw=_balance_raw() | {"totalStockholdersEquity": "100000000000"},
            cashflow_raw=_cashflow_raw() | {"operatingCashFlow": "90000000000"},
            period_end="2024-06-30",
            filing_date="2024-08-01",
        )
        profile = build_asset_profile(
            ticker="MSFT",
            name="Microsoft Corp",
            sector="Information Technology",
            market_cap=Decimal("2500000000000"),
            avg_daily_volume=Decimal("8000000000"),
            years_of_history=40,
        )
        return period, profile

    def test_two_tickers_same_sector_produce_ranked_composites(self):
        """Two tickers in the same sector should produce composites with sector-neutral ranking."""
        period1 = _build_period_with_priors()
        profile1 = _build_profile()

        period2, profile2 = self._build_second_ticker_data()

        raw1 = compute_raw_factor_scores(
            ticker="AAPL",
            period=period1,
            profile=profile1,
            price_bars_raw=_price_bars_raw(),
            earnings_raw=_earnings_raw(),
        )
        raw2 = compute_raw_factor_scores(
            ticker="MSFT",
            period=period2,
            profile=profile2,
            price_bars_raw=_price_bars_raw(200),
            earnings_raw=_earnings_raw(),
        )

        composites = rank_and_compute_composites([raw1, raw2])
        assert len(composites) == 2

        composites_by_ticker = {c.ticker: c for c in composites}
        for ticker in ("AAPL", "MSFT"):
            detail = composites_by_ticker[ticker].model_dump(mode="json")
            assert detail["ticker"] == ticker
            assert "quality" in detail
            assert "value" in detail
            assert "momentum" in detail
            assert "filters_passed" in detail
            # Percentile ranks should be valid
            assert 0.0 <= detail["composite_percentile"] <= 100.0
