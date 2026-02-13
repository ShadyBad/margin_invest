# Backend Data Pipeline Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Wire real scoring data through the backend so API endpoints serve actual computed scores from financial data instead of an in-memory mock store.

**Architecture:** Alembic manages DB schema. A seed CLI fetches financial data from yfinance for ~50 S&P 500 tickers and stores it in a `financial_data` table (JSONB). An ARQ background worker scores each ticker using the engine's full pipeline and persists results to the `scores` table. API routes query the DB instead of an in-memory dict.

**Tech Stack:** SQLAlchemy 2.0 (async), Alembic, ARQ (async Redis queue), yfinance, PostgreSQL/TimescaleDB, existing margin-engine scoring pipeline.

---

### Task 1: Add new dependencies (alembic, arq, asyncpg)

**Files:**
- Modify: `api/pyproject.toml`

**Step 1: Add alembic, arq, and asyncpg to api dependencies**

In `api/pyproject.toml`, add to the `dependencies` list:

```toml
dependencies = [
    "margin-engine",
    "fastapi>=0.115",
    "uvicorn>=0.34",
    "pydantic-settings>=2.12.0",
    "sqlalchemy>=2.0.46",
    "asyncpg>=0.30",
    "alembic>=1.15",
    "arq>=0.26",
    "argon2-cffi>=23.1.0",
    "pyotp>=2.9.0",
    "cryptography>=44.0.0",
    "webauthn>=2.5.0",
]
```

**Step 2: Sync dependencies**

Run: `uv sync`
Expected: All packages install successfully.

**Step 3: Commit**

```bash
git add api/pyproject.toml uv.lock
git commit -m "chore(api): add alembic, arq, asyncpg dependencies"
```

---

### Task 2: Add FinancialData ORM model and score_detail column

**Files:**
- Modify: `api/src/margin_api/db/models.py`
- Test: `api/tests/test_db_models.py`

**Step 1: Write failing test for FinancialData model**

Add to `api/tests/test_db_models.py`:

```python
from margin_api.db.models import FinancialData


class TestFinancialDataModel:
    def test_financial_data_has_required_columns(self):
        """FinancialData model has all expected columns."""
        from sqlalchemy import inspect
        mapper = inspect(FinancialData)
        column_names = {c.key for c in mapper.column_attrs}
        expected = {
            "id", "asset_id", "period_end", "filing_date",
            "income_statement", "balance_sheet", "cash_flow",
            "price_history", "earnings_data", "source", "fetched_at",
        }
        assert expected.issubset(column_names)

    def test_financial_data_tablename(self):
        assert FinancialData.__tablename__ == "financial_data"


class TestScoreDetailColumn:
    def test_score_has_score_detail_column(self):
        """Score model has the score_detail JSONB column."""
        from sqlalchemy import inspect
        from margin_api.db.models import Score
        mapper = inspect(Score)
        column_names = {c.key for c in mapper.column_attrs}
        assert "score_detail" in column_names
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/test_db_models.py::TestFinancialDataModel -v`
Expected: FAIL — `ImportError: cannot import name 'FinancialData'`

**Step 3: Implement FinancialData model and score_detail column**

In `api/src/margin_api/db/models.py`, add import at top:

```python
from sqlalchemy import ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
```

Add the `FinancialData` class after the `Asset` class:

```python
class FinancialData(Base):
    """Raw financial data fetched from data providers."""

    __tablename__ = "financial_data"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), index=True)
    period_end: Mapped[str] = mapped_column(String(10))  # ISO date
    filing_date: Mapped[str] = mapped_column(String(10))
    income_statement: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    balance_sheet: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    cash_flow: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    price_history: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    earnings_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    source: Mapped[str] = mapped_column(String(50), default="yfinance")
    fetched_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))

    asset: Mapped[Asset] = relationship()

    __table_args__ = (
        UniqueConstraint("asset_id", "period_end", name="uq_financial_data_asset_period"),
    )
```

Add `score_detail` column to the `Score` class:

```python
score_detail: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
```

Add the `FinancialData` relationship to `Asset`:

```python
financial_data: Mapped[list[FinancialData]] = relationship(back_populates="asset")
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest api/tests/test_db_models.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add api/src/margin_api/db/models.py api/tests/test_db_models.py
git commit -m "feat(api): add FinancialData model and score_detail JSONB column"
```

---

### Task 3: Initialize Alembic and create initial migration

**Files:**
- Create: `api/alembic.ini`
- Create: `api/alembic/env.py`
- Create: `api/alembic/script.py.mako`
- Create: `api/alembic/versions/` (directory)

**Step 1: Initialize Alembic in the api directory**

Run: `cd /Users/brandon/repos/margin_invest/api && uv run alembic init alembic`
Expected: Creates `alembic.ini` and `alembic/` directory.

**Step 2: Configure alembic.ini**

In `api/alembic.ini`, set the sqlalchemy.url:

```ini
sqlalchemy.url = postgresql+asyncpg://margin:margin_dev@localhost:5432/margin_invest
```

**Step 3: Configure alembic/env.py for async and model discovery**

Replace `api/alembic/env.py` with:

```python
"""Alembic environment configuration for async SQLAlchemy."""

from __future__ import annotations

import asyncio

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

from margin_api.config import get_settings
from margin_api.db.base import Base

# Import all models so they register with Base.metadata
import margin_api.db.models  # noqa: F401

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode — emit SQL without connecting."""
    url = get_settings().database_url
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode with async engine."""
    engine = create_async_engine(get_settings().database_url)
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await engine.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

**Step 4: Generate initial migration**

Run: `cd /Users/brandon/repos/margin_invest/api && uv run alembic revision --autogenerate -m "initial schema"`
Expected: Creates a migration file in `alembic/versions/`.

**Step 5: Verify docker services are running and apply migration**

Run: `docker compose -f /Users/brandon/repos/margin_invest/docker-compose.yml up -d`
Run: `cd /Users/brandon/repos/margin_invest/api && uv run alembic upgrade head`
Expected: All tables created in the database.

**Step 6: Commit**

```bash
git add api/alembic.ini api/alembic/ api/tests/
git commit -m "feat(api): initialize alembic with initial schema migration"
```

---

### Task 4: Build the scoring service (engine-to-DB bridge)

**Files:**
- Create: `api/src/margin_api/services/scoring.py`
- Create: `api/tests/test_scoring_service.py`

This service converts raw JSONB financial data into engine models and runs the full scoring pipeline.

**Step 1: Write failing tests for the scoring service**

Create `api/tests/test_scoring_service.py`:

```python
"""Tests for the scoring service — engine-to-DB bridge."""

from __future__ import annotations

from decimal import Decimal

import pytest

from margin_api.services.scoring import (
    build_financial_period,
    build_asset_profile,
    run_scoring_pipeline,
)


def _sample_income_json() -> dict:
    """Minimal income statement JSON matching yfinance normalizer format."""
    return {
        "revenue": 100_000_000,
        "costOfRevenue": 40_000_000,
        "grossProfit": 60_000_000,
        "ebit": 20_000_000,
        "netIncome": 15_000_000,
        "interestExpense": 1_000_000,
        "shares_outstanding": 1_000_000,
    }


def _sample_balance_json() -> dict:
    return {
        "totalAssets": 200_000_000,
        "currentAssets": 80_000_000,
        "cashAndEquivalents": 30_000_000,
        "totalLiabilities": 100_000_000,
        "currentLiabilities": 40_000_000,
        "longTermDebt": 30_000_000,
        "totalEquity": 100_000_000,
        "shares_outstanding": 1_000_000,
    }


def _sample_cashflow_json() -> dict:
    return {
        "operatingCashFlow": 25_000_000,
        "capitalExpenditures": -5_000_000,
    }


class TestBuildFinancialPeriod:
    def test_returns_financial_period(self):
        result = build_financial_period(
            income_json=_sample_income_json(),
            balance_json=_sample_balance_json(),
            cashflow_json=_sample_cashflow_json(),
            period_end="2024-09-28",
            filing_date="2024-11-01",
        )
        from margin_engine.models.financial import FinancialPeriod
        assert isinstance(result, FinancialPeriod)
        assert result.period_end == "2024-09-28"
        assert result.current_income.revenue == Decimal("100000000")

    def test_handles_none_prior_data(self):
        result = build_financial_period(
            income_json=_sample_income_json(),
            balance_json=_sample_balance_json(),
            cashflow_json=_sample_cashflow_json(),
            period_end="2024-09-28",
            filing_date="2024-11-01",
        )
        assert result.prior_income is None


class TestBuildAssetProfile:
    def test_returns_asset_profile(self):
        result = build_asset_profile(
            ticker="AAPL",
            name="Apple Inc.",
            sector="Information Technology",
            market_cap=Decimal("3500000000000"),
            sub_industry="Technology Hardware",
        )
        from margin_engine.models.financial import AssetProfile
        assert isinstance(result, AssetProfile)
        assert result.ticker == "AAPL"
        assert result.sector.value == "Information Technology"


class TestRunScoringPipeline:
    def test_returns_composite_score(self):
        income = _sample_income_json()
        balance = _sample_balance_json()
        cashflow = _sample_cashflow_json()
        period = build_financial_period(
            income_json=income,
            balance_json=balance,
            cashflow_json=cashflow,
            period_end="2024-09-28",
            filing_date="2024-11-01",
        )
        profile = build_asset_profile(
            ticker="TEST",
            name="Test Corp",
            sector="Information Technology",
            market_cap=Decimal("5000000000"),
        )
        result = run_scoring_pipeline(
            ticker="TEST",
            period=period,
            profile=profile,
            price_bars=[],
            earnings=[],
        )
        from margin_engine.models.scoring import CompositeScore
        assert isinstance(result, CompositeScore)
        assert result.ticker == "TEST"
        assert 0.0 <= result.composite_percentile <= 100.0
        assert 0.0 <= result.data_coverage <= 1.0
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest api/tests/test_scoring_service.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'margin_api.services.scoring'`

**Step 3: Implement the scoring service**

Create `api/src/margin_api/services/__init__.py` (if not exists).

Create `api/src/margin_api/services/scoring.py`:

```python
"""Scoring service — bridges raw financial data to engine scoring pipeline."""

from __future__ import annotations

from decimal import Decimal

from margin_engine.ingestion.normalizer import (
    normalize_balance_sheet,
    normalize_cash_flow,
    normalize_income_statement,
    normalize_price_bar,
)
from margin_engine.models.financial import (
    AssetProfile,
    EarningsSurprise,
    FinancialPeriod,
    GICSSector,
    PriceBar,
)
from margin_engine.models.scoring import CompositeScore, FactorScore
from margin_engine.scoring.classifier import classify_growth_stage
from margin_engine.scoring.composite import compute_composite_score
from margin_engine.scoring.filters.pipeline import run_elimination_filters
from margin_engine.scoring.quantitative.ev_fcf import ev_fcf
from margin_engine.scoring.quantitative.gross_profitability import gross_profitability
from margin_engine.scoring.quantitative.piotroski import piotroski_f_score
from margin_engine.scoring.quantitative.price_momentum import price_momentum
from margin_engine.scoring.quantitative.roic_wacc import roic_wacc_spread
from margin_engine.scoring.quantitative.sloan_accrual import sloan_accrual_ratio
from margin_engine.scoring.quantitative.acquirers_multiple import acquirers_multiple
from margin_engine.scoring.quantitative.dcf_margin import dcf_margin_of_safety
from margin_engine.scoring.quantitative.shareholder_yield import shareholder_yield
from margin_engine.scoring.quantitative.sue import sue_score
from margin_engine.scoring.quantitative.sentiment import sentiment_score
from margin_engine.scoring.quantitative.insider_cluster import insider_cluster_score
from margin_engine.scoring.quantitative.institutional import institutional_accumulation


def build_financial_period(
    *,
    income_json: dict,
    balance_json: dict,
    cashflow_json: dict,
    period_end: str,
    filing_date: str,
    prior_income_json: dict | None = None,
    prior_balance_json: dict | None = None,
    prior_cashflow_json: dict | None = None,
) -> FinancialPeriod:
    """Convert raw JSON financial data into an engine FinancialPeriod."""
    current_income = normalize_income_statement(income_json)
    current_balance = normalize_balance_sheet(balance_json)
    current_cash_flow = normalize_cash_flow(cashflow_json)

    prior_income = normalize_income_statement(prior_income_json) if prior_income_json else None
    prior_balance = normalize_balance_sheet(prior_balance_json) if prior_balance_json else None
    prior_cash_flow = normalize_cash_flow(prior_cashflow_json) if prior_cashflow_json else None

    return FinancialPeriod(
        period_end=period_end,
        filing_date=filing_date,
        current_income=current_income,
        prior_income=prior_income,
        current_balance=current_balance,
        prior_balance=prior_balance,
        current_cash_flow=current_cash_flow,
        prior_cash_flow=prior_cash_flow,
    )


def build_asset_profile(
    *,
    ticker: str,
    name: str,
    sector: str,
    market_cap: Decimal,
    sub_industry: str | None = None,
) -> AssetProfile:
    """Build an engine AssetProfile from DB asset fields."""
    return AssetProfile(
        ticker=ticker,
        name=name,
        sector=GICSSector(sector),
        sub_industry=sub_industry,
        market_cap=market_cap,
    )


def _parse_price_bars(raw_bars: list[dict]) -> list[PriceBar]:
    """Convert raw price bar dicts to engine PriceBar models."""
    return [normalize_price_bar(bar) for bar in raw_bars]


def run_scoring_pipeline(
    *,
    ticker: str,
    period: FinancialPeriod,
    profile: AssetProfile,
    price_bars: list[dict],
    earnings: list[dict],
) -> CompositeScore:
    """Run the full scoring pipeline for a single ticker.

    1. Elimination filters
    2. Quality, value, momentum factor scores
    3. Growth stage classification
    4. Composite scoring
    """
    # 1. Elimination filters
    pipeline_result = run_elimination_filters(period, profile)

    # 2. Parse supplementary data
    bars = _parse_price_bars(price_bars) if price_bars else []

    # 3. Quality factors
    quality_scores: list[FactorScore] = [
        gross_profitability(period),
        roic_wacc_spread(period),
        sloan_accrual_ratio(period),
        piotroski_f_score(period),
    ]

    # 4. Value factors
    value_scores: list[FactorScore] = [
        ev_fcf(period, profile.market_cap),
        shareholder_yield(period, profile.market_cap),
        dcf_margin_of_safety(period, profile.market_cap),
        acquirers_multiple(period, profile.market_cap),
    ]

    # 5. Momentum factors
    momentum_scores: list[FactorScore] = [
        price_momentum(bars),
    ]
    # Sentiment, insider, institutional, SUE require external data;
    # use zero-value placeholders when data is unavailable
    momentum_scores.append(
        sue_score(earnings) if earnings else FactorScore(
            name="sue_score", raw_value=0.0, percentile_rank=0.0, detail="No earnings data",
        )
    )
    momentum_scores.append(
        FactorScore(
            name="sentiment_score", raw_value=0.0, percentile_rank=0.0,
            detail="No sentiment data",
        )
    )
    momentum_scores.append(
        FactorScore(
            name="insider_cluster_score", raw_value=0.0, percentile_rank=0.0,
            detail="No insider data",
        )
    )
    momentum_scores.append(
        FactorScore(
            name="institutional_accumulation", raw_value=0.0, percentile_rank=0.0,
            detail="No institutional data",
        )
    )

    # 6. Classify growth stage
    growth_stage = classify_growth_stage(period, profile)

    # 7. Composite score
    return compute_composite_score(
        ticker=ticker,
        quality_scores=quality_scores,
        value_scores=value_scores,
        momentum_scores=momentum_scores,
        filters_passed=pipeline_result.results,
        growth_stage=growth_stage,
    )
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest api/tests/test_scoring_service.py -v`
Expected: PASS

Note: Some imports may need path adjustments depending on actual module names in `engine/src/margin_engine/scoring/quantitative/`. If an import fails, check the actual filenames with `ls engine/src/margin_engine/scoring/quantitative/` and adjust.

**Step 5: Commit**

```bash
git add api/src/margin_api/services/ api/tests/test_scoring_service.py
git commit -m "feat(api): add scoring service bridging engine to DB"
```

---

### Task 5: Build the data seed CLI

**Files:**
- Create: `api/src/margin_api/cli.py`
- Create: `api/tests/test_cli.py`

**Step 1: Write failing test for the seed command**

Create `api/tests/test_cli.py`:

```python
"""Tests for the CLI seed command."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from margin_api.cli import SP500_TICKERS, seed_ticker_data


class TestSp500Tickers:
    def test_tickers_is_nonempty_list(self):
        assert len(SP500_TICKERS) >= 40
        assert all(isinstance(t, str) for t in SP500_TICKERS)

    def test_tickers_are_uppercase(self):
        assert all(t == t.upper() for t in SP500_TICKERS)

    def test_includes_known_tickers(self):
        for ticker in ["AAPL", "MSFT", "GOOGL", "JPM", "XOM"]:
            assert ticker in SP500_TICKERS


class TestSeedTickerData:
    @pytest.mark.asyncio
    async def test_seed_ticker_data_calls_provider(self):
        mock_provider = MagicMock()
        mock_provider.fetch_fundamentals.return_value = MagicMock(
            success=True,
            raw_data={
                "income_statement": {"revenue": 100},
                "balance_sheet": {"totalAssets": 200},
                "cash_flow": {"operatingCashFlow": 50},
            },
        )
        mock_provider.fetch_price_history.return_value = MagicMock(
            success=True, raw_data={"bars": []},
        )
        mock_provider.fetch_earnings.return_value = MagicMock(
            success=True, raw_data={"earnings": []},
        )

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))

        mock_info = MagicMock()
        mock_info.get.return_value = {}

        with patch("margin_api.cli.yfinance") as mock_yf:
            mock_ticker_obj = MagicMock()
            mock_ticker_obj.info = {
                "shortName": "Apple Inc.",
                "sector": "Technology",
                "industry": "Consumer Electronics",
                "marketCap": 3_000_000_000_000,
            }
            mock_yf.Ticker.return_value = mock_ticker_obj

            result = await seed_ticker_data(
                ticker="AAPL",
                provider=mock_provider,
                session=mock_session,
            )

        assert result is True
        mock_provider.fetch_fundamentals.assert_called_once_with("AAPL")
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest api/tests/test_cli.py::TestSp500Tickers -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Implement the CLI module**

Create `api/src/margin_api/cli.py`:

```python
"""CLI commands for seeding data and managing the scoring pipeline."""

from __future__ import annotations

import asyncio
import logging
import sys
from decimal import Decimal

import yfinance
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from margin_engine.ingestion.providers.yfinance_provider import YFinanceProvider
from margin_engine.ingestion.rate_limiter import RateLimiterRegistry
from margin_api.db.models import Asset, FinancialData
from margin_api.db.session import get_engine, get_session_factory

logger = logging.getLogger(__name__)

SP500_TICKERS = [
    # Technology
    "AAPL", "MSFT", "NVDA", "GOOGL", "META", "AMZN", "AVGO", "ORCL", "CRM", "AMD",
    # Healthcare
    "UNH", "JNJ", "LLY", "ABBV", "MRK",
    # Financials
    "JPM", "V", "MA", "BAC", "GS",
    # Consumer Staples
    "PG", "KO", "PEP", "COST", "WMT",
    # Consumer Discretionary
    "TSLA", "HD", "NKE", "SBUX", "MCD", "TJX",
    # Energy
    "XOM", "CVX",
    # Industrials
    "CAT", "GE", "HON", "UNP", "RTX",
    # Communication
    "NFLX", "DIS", "CMCSA",
    # Utilities
    "NEE", "SO", "DUK",
    # Materials
    "LIN", "APD", "SHW",
    # Real Estate
    "PLD", "AMT",
]

# yfinance sector names -> GICSSector values
SECTOR_MAP = {
    "Technology": "Information Technology",
    "Healthcare": "Health Care",
    "Financial Services": "Financials",
    "Consumer Cyclical": "Consumer Discretionary",
    "Consumer Defensive": "Consumer Staples",
    "Energy": "Energy",
    "Industrials": "Industrials",
    "Basic Materials": "Materials",
    "Real Estate": "Real Estate",
    "Utilities": "Utilities",
    "Communication Services": "Communication Services",
}


async def seed_ticker_data(
    *,
    ticker: str,
    provider: YFinanceProvider,
    session: AsyncSession,
) -> bool:
    """Fetch financial data for a ticker and store in DB.

    Returns True on success, False on failure.
    """
    try:
        # Fetch data from provider
        fundamentals = provider.fetch_fundamentals(ticker)
        prices = provider.fetch_price_history(ticker, days=365)
        earnings = provider.fetch_earnings(ticker)

        if not fundamentals.success:
            logger.warning("Failed to fetch fundamentals for %s: %s", ticker, fundamentals.error)
            return False

        # Get asset info from yfinance
        yf_ticker = yfinance.Ticker(ticker)
        info = yf_ticker.info or {}

        name = info.get("shortName", info.get("longName", ticker))
        yf_sector = info.get("sector", "Information Technology")
        sector = SECTOR_MAP.get(yf_sector, yf_sector)
        sub_industry = info.get("industry")
        market_cap = Decimal(str(info.get("marketCap", 0)))

        # Upsert asset
        result = await session.execute(
            select(Asset).where(Asset.ticker == ticker)
        )
        asset = result.scalar_one_or_none()
        if asset is None:
            asset = Asset(
                ticker=ticker,
                name=name,
                sector=sector,
                sub_industry=sub_industry,
                market_cap=market_cap,
            )
            session.add(asset)
            await session.flush()
        else:
            asset.name = name
            asset.sector = sector
            asset.sub_industry = sub_industry
            asset.market_cap = market_cap

        # Extract raw data
        raw = fundamentals.raw_data
        income_json = raw.get("income_statement", {})
        balance_json = raw.get("balance_sheet", {})
        cashflow_json = raw.get("cash_flow", {})
        price_json = prices.raw_data if prices.success else {}
        earnings_json = earnings.raw_data if earnings.success else {}

        # Determine period_end from data or use today
        period_end = info.get("lastFiscalYearEnd", "")
        if not period_end:
            from datetime import UTC, datetime
            period_end = datetime.now(UTC).strftime("%Y-%m-%d")

        # Upsert financial data
        result = await session.execute(
            select(FinancialData).where(
                FinancialData.asset_id == asset.id,
                FinancialData.period_end == period_end,
            )
        )
        fin_data = result.scalar_one_or_none()
        if fin_data is None:
            fin_data = FinancialData(
                asset_id=asset.id,
                period_end=period_end,
                filing_date=period_end,
                income_statement=income_json,
                balance_sheet=balance_json,
                cash_flow=cashflow_json,
                price_history=price_json,
                earnings_data=earnings_json,
                source="yfinance",
            )
            session.add(fin_data)
        else:
            fin_data.income_statement = income_json
            fin_data.balance_sheet = balance_json
            fin_data.cash_flow = cashflow_json
            fin_data.price_history = price_json
            fin_data.earnings_data = earnings_json

        await session.commit()
        return True

    except Exception:
        logger.exception("Error seeding %s", ticker)
        await session.rollback()
        return False


async def run_seed(tickers: list[str] | None = None) -> None:
    """Seed financial data for all tickers."""
    tickers = tickers or SP500_TICKERS
    provider = YFinanceProvider()

    # Set up rate limiting
    rate_registry = RateLimiterRegistry()
    rate_registry.register("yfinance", 60)

    engine = get_engine()
    session_factory = get_session_factory(engine)

    success_count = 0
    fail_count = 0

    for i, ticker in enumerate(tickers, 1):
        # Respect rate limits
        rate_registry.get("yfinance").wait_and_acquire()

        async with session_factory() as session:
            ok = await seed_ticker_data(
                ticker=ticker, provider=provider, session=session,
            )
            if ok:
                success_count += 1
                print(f"[{i}/{len(tickers)}] Seeded {ticker}")
            else:
                fail_count += 1
                print(f"[{i}/{len(tickers)}] FAILED {ticker}")

    print(f"\nDone: {success_count} seeded, {fail_count} failed")
    await engine.dispose()


def main() -> None:
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Margin Invest CLI")
    subparsers = parser.add_subparsers(dest="command")

    seed_parser = subparsers.add_parser("seed", help="Seed financial data from yfinance")
    seed_parser.add_argument(
        "--tickers", nargs="*", help="Specific tickers to seed (default: SP500 top 50)",
    )

    args = parser.parse_args()

    if args.command == "seed":
        asyncio.run(run_seed(args.tickers))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest api/tests/test_cli.py::TestSp500Tickers -v`
Expected: PASS

**Step 5: Commit**

```bash
git add api/src/margin_api/cli.py api/tests/test_cli.py
git commit -m "feat(api): add data seed CLI with S&P 500 ticker list"
```

---

### Task 6: Build the ARQ background worker

**Files:**
- Create: `api/src/margin_api/worker.py`
- Create: `api/tests/test_worker.py`

**Step 1: Write failing test for the worker task**

Create `api/tests/test_worker.py`:

```python
"""Tests for the ARQ background worker."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from margin_api.worker import score_ticker


class TestScoreTicker:
    @pytest.mark.asyncio
    async def test_score_ticker_produces_result(self):
        """score_ticker should fetch data from DB and produce a CompositeScore."""
        # Mock the DB session and its queries
        mock_asset = MagicMock()
        mock_asset.id = 1
        mock_asset.ticker = "TEST"
        mock_asset.name = "Test Corp"
        mock_asset.sector = "Information Technology"
        mock_asset.market_cap = Decimal("5000000000")
        mock_asset.sub_industry = None

        mock_fin = MagicMock()
        mock_fin.income_statement = {
            "revenue": 100_000_000,
            "costOfRevenue": 40_000_000,
            "grossProfit": 60_000_000,
            "ebit": 20_000_000,
            "netIncome": 15_000_000,
            "interestExpense": 1_000_000,
            "shares_outstanding": 1_000_000,
        }
        mock_fin.balance_sheet = {
            "totalAssets": 200_000_000,
            "currentAssets": 80_000_000,
            "cashAndEquivalents": 30_000_000,
            "totalLiabilities": 100_000_000,
            "currentLiabilities": 40_000_000,
            "longTermDebt": 30_000_000,
            "totalEquity": 100_000_000,
            "shares_outstanding": 1_000_000,
        }
        mock_fin.cash_flow = {
            "operatingCashFlow": 25_000_000,
            "capitalExpenditures": -5_000_000,
        }
        mock_fin.price_history = {"bars": []}
        mock_fin.earnings_data = {"earnings": []}
        mock_fin.period_end = "2024-09-28"
        mock_fin.filing_date = "2024-11-01"

        # Mock session.execute to return asset and financial data
        mock_session = AsyncMock()
        asset_result = MagicMock()
        asset_result.scalar_one_or_none.return_value = mock_asset
        fin_result = MagicMock()
        fin_result.scalar_one_or_none.return_value = mock_fin

        mock_session.execute = AsyncMock(side_effect=[asset_result, fin_result])
        mock_session.commit = AsyncMock()

        result = await score_ticker(
            ticker="TEST",
            session=mock_session,
        )

        assert result is True
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/test_worker.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Implement the worker**

Create `api/src/margin_api/worker.py`:

```python
"""ARQ background worker for scoring tickers."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.config import get_settings
from margin_api.db.models import Asset, FinancialData, Score
from margin_api.db.session import get_engine, get_session_factory
from margin_api.services.scoring import (
    build_asset_profile,
    build_financial_period,
    run_scoring_pipeline,
)

logger = logging.getLogger(__name__)


async def score_ticker(
    *,
    ticker: str,
    session: AsyncSession,
) -> bool:
    """Score a single ticker using data from the DB.

    Loads financial data, runs the engine scoring pipeline,
    and persists the result to the scores table.

    Returns True on success, False on failure.
    """
    try:
        # Load asset
        result = await session.execute(
            select(Asset).where(Asset.ticker == ticker)
        )
        asset = result.scalar_one_or_none()
        if asset is None:
            logger.warning("No asset found for %s", ticker)
            return False

        # Load most recent financial data
        result = await session.execute(
            select(FinancialData)
            .where(FinancialData.asset_id == asset.id)
            .order_by(FinancialData.fetched_at.desc())
            .limit(1)
        )
        fin_data = result.scalar_one_or_none()
        if fin_data is None:
            logger.warning("No financial data found for %s", ticker)
            return False

        # Build engine models
        period = build_financial_period(
            income_json=fin_data.income_statement or {},
            balance_json=fin_data.balance_sheet or {},
            cashflow_json=fin_data.cash_flow or {},
            period_end=fin_data.period_end,
            filing_date=fin_data.filing_date,
        )
        profile = build_asset_profile(
            ticker=asset.ticker,
            name=asset.name,
            sector=asset.sector,
            market_cap=asset.market_cap,
            sub_industry=asset.sub_industry,
        )

        # Extract price bars and earnings
        price_data = fin_data.price_history or {}
        bars = price_data.get("bars", [])
        earnings_data = fin_data.earnings_data or {}
        earnings = earnings_data.get("earnings", [])

        # Run scoring pipeline
        composite = run_scoring_pipeline(
            ticker=ticker,
            period=period,
            profile=profile,
            price_bars=bars,
            earnings=earnings,
        )

        # Persist score to DB
        score_row = Score(
            asset_id=asset.id,
            composite_percentile=composite.composite_percentile,
            conviction_level=composite.conviction_level.value,
            signal=composite.signal.value,
            quality_percentile=composite.quality.average_percentile,
            value_percentile=composite.value.average_percentile,
            momentum_percentile=composite.momentum.average_percentile,
            data_coverage=composite.data_coverage,
            growth_stage=composite.growth_stage.value if composite.growth_stage else None,
            score_detail=composite.model_dump(mode="json"),
            scored_at=datetime.now(UTC),
        )
        session.add(score_row)
        await session.commit()

        logger.info(
            "Scored %s: percentile=%.1f conviction=%s",
            ticker, composite.composite_percentile, composite.conviction_level.value,
        )
        return True

    except Exception:
        logger.exception("Error scoring %s", ticker)
        await session.rollback()
        return False


async def score_all_tickers(ctx: dict) -> None:
    """ARQ task: score all tickers that have financial data."""
    engine = get_engine()
    session_factory = get_session_factory(engine)

    async with session_factory() as session:
        result = await session.execute(select(Asset.ticker))
        tickers = [row[0] for row in result.all()]

    success = 0
    failed = 0
    for ticker in tickers:
        async with session_factory() as session:
            ok = await score_ticker(ticker=ticker, session=session)
            if ok:
                success += 1
            else:
                failed += 1

    logger.info("Scoring complete: %d success, %d failed", success, failed)
    await engine.dispose()


async def score_single_ticker(ctx: dict, ticker: str) -> bool:
    """ARQ task: score a single ticker."""
    engine = get_engine()
    session_factory = get_session_factory(engine)

    async with session_factory() as session:
        result = await score_ticker(ticker=ticker, session=session)

    await engine.dispose()
    return result


class WorkerSettings:
    """ARQ worker settings."""

    functions = [score_all_tickers, score_single_ticker]
    redis_settings = None  # Set at startup from config

    @staticmethod
    def on_startup(ctx: dict) -> None:
        """Initialize worker context."""
        logger.info("Scoring worker started")

    @staticmethod
    def on_shutdown(ctx: dict) -> None:
        """Clean up worker context."""
        logger.info("Scoring worker stopped")


def get_worker_settings() -> type:
    """Return WorkerSettings with redis configured from app settings."""
    from arq.connections import RedisSettings

    settings = get_settings()
    # Parse redis URL into host/port
    url = settings.redis_url.replace("redis://", "")
    host, port = url.split(":") if ":" in url else (url, "6379")
    WorkerSettings.redis_settings = RedisSettings(host=host, port=int(port))
    return WorkerSettings
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest api/tests/test_worker.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add api/src/margin_api/worker.py api/tests/test_worker.py
git commit -m "feat(api): add ARQ background worker for scoring tickers"
```

---

### Task 7: Refactor scores route to use database

**Files:**
- Modify: `api/src/margin_api/routes/scores.py`
- Modify: `api/tests/test_scores.py`

**Step 1: Rewrite the scores test to use DB fixtures**

Replace `api/tests/test_scores.py`:

```python
"""Tests for score endpoints — DB-backed."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from margin_api.app import create_app


def _mock_score_row(
    ticker: str = "AAPL",
    name: str = "Apple Inc.",
    percentile: float = 99.5,
    conviction: str = "exceptional",
    signal: str = "buy",
    quality_pct: float = 98.0,
    value_pct: float = 95.0,
    momentum_pct: float = 97.0,
    growth_stage: str | None = None,
) -> MagicMock:
    """Create a mock Score + Asset join result."""
    mock = MagicMock()
    # Score fields
    mock.composite_percentile = percentile
    mock.conviction_level = conviction
    mock.signal = signal
    mock.quality_percentile = quality_pct
    mock.value_percentile = value_pct
    mock.momentum_percentile = momentum_pct
    mock.data_coverage = 1.0
    mock.growth_stage = growth_stage
    mock.scored_at = datetime.now(UTC)
    mock.score_detail = {
        "ticker": ticker,
        "composite_percentile": percentile,
        "conviction_level": conviction,
        "signal": signal,
        "quality": {
            "factor_name": "quality", "weight": 0.35,
            "sub_scores": [], "average_percentile": quality_pct,
        },
        "value": {
            "factor_name": "value", "weight": 0.30,
            "sub_scores": [], "average_percentile": value_pct,
        },
        "momentum": {
            "factor_name": "momentum", "weight": 0.35,
            "sub_scores": [], "average_percentile": momentum_pct,
        },
        "filters_passed": [],
        "data_coverage": 1.0,
        "growth_stage": growth_stage,
    }
    # Asset fields (from join)
    mock.ticker = ticker
    mock.asset_name = name
    return mock


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


class TestGetScore:
    def test_get_score_success(self, client):
        mock_row = _mock_score_row("AAPL")
        with patch("margin_api.routes.scores.get_db") as mock_get_db:
            mock_session = AsyncMock()
            mock_result = MagicMock()
            mock_result.first.return_value = mock_row
            mock_session.execute = AsyncMock(return_value=mock_result)
            mock_get_db.return_value = mock_session

            # For sync TestClient with async deps, we need to override the dep
            from margin_api.db.session import get_db
            app = create_app()
            app.dependency_overrides[get_db] = lambda: mock_session
            client = TestClient(app)

            response = client.get("/api/v1/scores/AAPL")

        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == "AAPL"
        assert data["composite_percentile"] == 99.5

    def test_get_score_not_found(self, client):
        with patch("margin_api.routes.scores.get_db") as mock_get_db:
            mock_session = AsyncMock()
            mock_result = MagicMock()
            mock_result.first.return_value = None
            mock_session.execute = AsyncMock(return_value=mock_result)

            from margin_api.db.session import get_db
            app = create_app()
            app.dependency_overrides[get_db] = lambda: mock_session
            client = TestClient(app)

            response = client.get("/api/v1/scores/UNKNOWN")

        assert response.status_code == 404
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/test_scores.py::TestGetScore::test_get_score_not_found -v`
Expected: FAIL (route still uses `_score_store`)

**Step 3: Rewrite the scores route to use DB**

Replace `api/src/margin_api/routes/scores.py`:

```python
"""Score endpoints for the Margin Invest API — DB-backed."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.db.models import Asset, Score
from margin_api.db.session import get_db
from margin_api.schemas.scores import ScoreListResponse, ScoreResponse

router = APIRouter(prefix="/api/v1/scores", tags=["scores"])


def _score_response_from_row(row) -> ScoreResponse:
    """Build a ScoreResponse from a DB query row.

    If score_detail JSONB is present, use it for full factor breakdowns.
    Otherwise, build a minimal response from summary columns.
    """
    detail = row.score_detail
    if detail:
        return ScoreResponse(**detail)

    # Fallback: build from summary columns (no sub-score detail)
    from margin_api.schemas.scores import FactorBreakdownResponse
    return ScoreResponse(
        ticker=row.ticker,
        composite_percentile=row.composite_percentile,
        conviction_level=row.conviction_level,
        signal=row.signal,
        quality=FactorBreakdownResponse(
            factor_name="quality", weight=0.35,
            sub_scores=[], average_percentile=row.quality_percentile,
        ),
        value=FactorBreakdownResponse(
            factor_name="value", weight=0.30,
            sub_scores=[], average_percentile=row.value_percentile,
        ),
        momentum=FactorBreakdownResponse(
            factor_name="momentum", weight=0.35,
            sub_scores=[], average_percentile=row.momentum_percentile,
        ),
        filters_passed=[],
        data_coverage=row.data_coverage,
        growth_stage=row.growth_stage,
    )


@router.get("", response_model=ScoreListResponse)
async def list_scores(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    min_percentile: float = Query(0.0, ge=0.0, le=100.0),
    conviction: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
) -> ScoreListResponse:
    """List all scored assets with optional filtering and pagination."""
    # Build base query: latest score per asset
    latest_score = (
        select(
            Score.asset_id,
            func.max(Score.scored_at).label("max_scored_at"),
        )
        .group_by(Score.asset_id)
        .subquery()
    )

    query = (
        select(Score, Asset.ticker, Asset.name.label("asset_name"))
        .join(Asset, Score.asset_id == Asset.id)
        .join(
            latest_score,
            (Score.asset_id == latest_score.c.asset_id)
            & (Score.scored_at == latest_score.c.max_scored_at),
        )
    )

    if min_percentile > 0:
        query = query.where(Score.composite_percentile >= min_percentile)
    if conviction:
        query = query.where(Score.conviction_level == conviction.lower())

    # Get total count
    count_result = await db.execute(
        select(func.count()).select_from(query.subquery())
    )
    total = count_result.scalar() or 0

    # Sort and paginate
    query = query.order_by(Score.composite_percentile.desc())
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    rows = result.all()

    scores = [_score_response_from_row(row) for row in rows]

    return ScoreListResponse(
        scores=scores,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{ticker}", response_model=ScoreResponse)
async def get_score(
    ticker: str,
    db: AsyncSession = Depends(get_db),
) -> ScoreResponse:
    """Get the latest scoring result for a specific ticker."""
    ticker = ticker.upper()
    query = (
        select(Score, Asset.ticker, Asset.name.label("asset_name"))
        .join(Asset, Score.asset_id == Asset.id)
        .where(Asset.ticker == ticker)
        .order_by(Score.scored_at.desc())
        .limit(1)
    )
    result = await db.execute(query)
    row = result.first()

    if row is None:
        raise HTTPException(status_code=404, detail=f"No score found for {ticker}")

    return _score_response_from_row(row)
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest api/tests/test_scores.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add api/src/margin_api/routes/scores.py api/tests/test_scores.py
git commit -m "feat(api): refactor scores route from in-memory store to DB queries"
```

---

### Task 8: Refactor dashboard route to use database

**Files:**
- Modify: `api/src/margin_api/routes/dashboard.py`
- Modify: `api/tests/test_dashboard.py`

**Step 1: Rewrite dashboard test to use DB mocks**

Replace `api/tests/test_dashboard.py`:

```python
"""Tests for dashboard endpoint — DB-backed."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from margin_api.app import create_app
from margin_api.db.session import get_db


def _mock_score_row(
    ticker: str,
    name: str,
    percentile: float,
    conviction: str,
    signal: str = "buy",
) -> MagicMock:
    mock = MagicMock()
    mock.ticker = ticker
    mock.asset_name = name
    mock.composite_percentile = percentile
    mock.conviction_level = conviction
    mock.signal = signal
    mock.quality_percentile = percentile
    mock.value_percentile = percentile
    mock.momentum_percentile = percentile
    return mock


def _make_client_with_mock_db(mock_session):
    app = create_app()
    app.dependency_overrides[get_db] = lambda: mock_session
    return TestClient(app)


class TestDashboardEndpoint:
    def test_dashboard_empty(self):
        mock_session = AsyncMock()
        # Picks query
        mock_picks = MagicMock()
        mock_picks.all.return_value = []
        # Watchlist query
        mock_watchlist = MagicMock()
        mock_watchlist.all.return_value = []
        # Total count query
        mock_total = MagicMock()
        mock_total.scalar.return_value = 0
        # Last updated query
        mock_updated = MagicMock()
        mock_updated.scalar.return_value = None

        mock_session.execute = AsyncMock(
            side_effect=[mock_picks, mock_watchlist, mock_total, mock_updated]
        )
        client = _make_client_with_mock_db(mock_session)
        response = client.get("/api/v1/dashboard")
        assert response.status_code == 200
        data = response.json()
        assert data["picks"] == []
        assert data["watchlist"] == []
        assert data["total_scored"] == 0

    def test_dashboard_with_picks(self):
        mock_session = AsyncMock()
        picks = [
            _mock_score_row("AAPL", "Apple Inc.", 99.5, "exceptional"),
            _mock_score_row("NVDA", "NVIDIA Corp", 96.0, "high"),
        ]
        mock_picks = MagicMock()
        mock_picks.all.return_value = picks
        mock_watchlist = MagicMock()
        mock_watchlist.all.return_value = []
        mock_total = MagicMock()
        mock_total.scalar.return_value = 2
        mock_updated = MagicMock()
        mock_updated.scalar.return_value = datetime.now(UTC)

        mock_session.execute = AsyncMock(
            side_effect=[mock_picks, mock_watchlist, mock_total, mock_updated]
        )
        client = _make_client_with_mock_db(mock_session)
        response = client.get("/api/v1/dashboard")
        data = response.json()
        assert len(data["picks"]) == 2
        assert data["picks"][0]["ticker"] == "AAPL"
        assert data["picks"][1]["ticker"] == "NVDA"
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/test_dashboard.py::TestDashboardEndpoint::test_dashboard_empty -v`
Expected: FAIL

**Step 3: Rewrite dashboard route to use DB**

Replace `api/src/margin_api/routes/dashboard.py`:

```python
"""Dashboard endpoint — high-conviction picks and watchlist from DB."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from margin_api.db.models import Asset, Score
from margin_api.db.session import get_db
from margin_api.schemas.dashboard import (
    DashboardResponse,
    PickSummary,
    WatchlistItem,
)

router = APIRouter(prefix="/api/v1", tags=["dashboard"])


def _latest_scores_subquery():
    """Subquery for the most recent score per asset."""
    return (
        select(
            Score.asset_id,
            func.max(Score.scored_at).label("max_scored_at"),
        )
        .group_by(Score.asset_id)
        .subquery()
    )


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    db: AsyncSession = Depends(get_db),
) -> DashboardResponse:
    """Get dashboard with high-conviction picks and watchlist.

    Picks = latest scores with conviction_level in ('exceptional', 'high')
    Watchlist = latest scores with conviction_level == 'watchlist'
    """
    latest = _latest_scores_subquery()

    base_join = (
        select(Score, Asset.ticker, Asset.name.label("asset_name"))
        .join(Asset, Score.asset_id == Asset.id)
        .join(
            latest,
            (Score.asset_id == latest.c.asset_id)
            & (Score.scored_at == latest.c.max_scored_at),
        )
    )

    # Picks: exceptional + high
    picks_query = (
        base_join
        .where(Score.conviction_level.in_(["exceptional", "high"]))
        .order_by(Score.composite_percentile.desc())
    )
    picks_result = await db.execute(picks_query)
    pick_rows = picks_result.all()

    picks = [
        PickSummary(
            ticker=row.ticker,
            name=row.asset_name,
            composite_percentile=row.Score.composite_percentile,
            conviction_level=row.Score.conviction_level,
            signal=row.Score.signal,
            quality_percentile=row.Score.quality_percentile,
            value_percentile=row.Score.value_percentile,
            momentum_percentile=row.Score.momentum_percentile,
        )
        for row in pick_rows
    ]

    # Watchlist
    watchlist_query = (
        base_join
        .where(Score.conviction_level == "watchlist")
        .order_by(Score.composite_percentile.desc())
    )
    watchlist_result = await db.execute(watchlist_query)
    watchlist_rows = watchlist_result.all()

    watchlist = [
        WatchlistItem(
            ticker=row.ticker,
            name=row.asset_name,
            composite_percentile=row.Score.composite_percentile,
            conviction_level=row.Score.conviction_level,
        )
        for row in watchlist_rows
    ]

    # Total scored
    total_result = await db.execute(
        select(func.count(func.distinct(Score.asset_id)))
    )
    total_scored = total_result.scalar() or 0

    # Last updated
    updated_result = await db.execute(select(func.max(Score.scored_at)))
    last_updated_dt = updated_result.scalar()
    last_updated = (
        last_updated_dt.isoformat() if last_updated_dt
        else datetime.now(UTC).isoformat()
    )

    return DashboardResponse(
        picks=picks,
        watchlist=watchlist,
        last_updated=last_updated,
        total_scored=total_scored,
    )
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest api/tests/test_dashboard.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add api/src/margin_api/routes/dashboard.py api/tests/test_dashboard.py
git commit -m "feat(api): refactor dashboard route from in-memory store to DB queries"
```

---

### Task 9: Update conftest and remove stale mock fixtures

**Files:**
- Modify: `api/tests/conftest.py`

**Step 1: Remove _clear_score_store fixture**

The `_clear_score_store` fixture in `api/tests/conftest.py` clears the old `_score_store` dict which no longer exists. Remove it:

```python
# DELETE the _clear_score_store fixture entirely
```

Keep `_clear_settings_cache` and `_clear_backtest_store`. The conftest should now be:

```python
"""Shared test fixtures for the API test suite."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from margin_api.app import create_app
from margin_api.config import get_settings


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    """Clear the settings cache before each test for isolation."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _clear_backtest_store():
    """Clear the in-memory backtest store before and after each test."""
    from margin_api.routes.backtest import _backtest_store
    _backtest_store.clear()
    yield
    _backtest_store.clear()


@pytest.fixture
def app():
    """Create a fresh app instance for testing."""
    return create_app()


@pytest.fixture
def client(app):
    """Create a test client."""
    return TestClient(app)
```

**Step 2: Run all API tests**

Run: `uv run pytest api/tests/ -v`
Expected: All tests pass. Fix any remaining references to `_score_store` in other test files.

**Step 3: Commit**

```bash
git add api/tests/conftest.py
git commit -m "chore(api): remove stale in-memory score store fixtures from conftest"
```

---

### Task 10: Add seed-then-score integration command to CLI

**Files:**
- Modify: `api/src/margin_api/cli.py`

**Step 1: Add a `score` subcommand to the CLI**

Add to the `main()` function in `cli.py`:

```python
score_parser = subparsers.add_parser("score", help="Score all seeded tickers")
score_parser.add_argument(
    "--tickers", nargs="*", help="Specific tickers to score (default: all seeded)",
)
```

And handle it:

```python
elif args.command == "score":
    from margin_api.worker import score_ticker as _score_ticker
    asyncio.run(_run_scoring(args.tickers))
```

Add the scoring function:

```python
async def _run_scoring(tickers: list[str] | None = None) -> None:
    """Score tickers from DB data."""
    from margin_api.worker import score_ticker as _score_ticker

    engine = get_engine()
    session_factory = get_session_factory(engine)

    if tickers is None:
        async with session_factory() as session:
            result = await session.execute(select(Asset.ticker))
            tickers = [row[0] for row in result.all()]

    success = 0
    failed = 0
    for i, ticker in enumerate(tickers, 1):
        async with session_factory() as session:
            ok = await _score_ticker(ticker=ticker, session=session)
            if ok:
                success += 1
                print(f"[{i}/{len(tickers)}] Scored {ticker}")
            else:
                failed += 1
                print(f"[{i}/{len(tickers)}] FAILED {ticker}")

    print(f"\nScoring done: {success} scored, {failed} failed")
    await engine.dispose()
```

**Step 2: Test the CLI manually (after seeding)**

Run: `uv run python -m margin_api.cli score --tickers AAPL`
Expected: Scores AAPL from DB data if it was previously seeded.

**Step 3: Commit**

```bash
git add api/src/margin_api/cli.py
git commit -m "feat(api): add score subcommand to CLI for manual scoring runs"
```

---

### Task 11: End-to-end integration test

**Files:**
- Create: `api/tests/test_pipeline_integration.py`

**Step 1: Write an integration test for the full pipeline**

Create `api/tests/test_pipeline_integration.py`:

```python
"""Integration test for the full scoring pipeline (no external services)."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from margin_api.services.scoring import (
    build_asset_profile,
    build_financial_period,
    run_scoring_pipeline,
)
from margin_engine.models.scoring import CompositeScore


# Use real Apple-like data for a realistic integration test
INCOME = {
    "revenue": 391_035_000_000,
    "costOfRevenue": 210_352_000_000,
    "grossProfit": 180_683_000_000,
    "ebit": 123_216_000_000,
    "netIncome": 93_736_000_000,
    "interestExpense": 3_423_000_000,
    "shares_outstanding": 15_408_095_000,
}

BALANCE = {
    "totalAssets": 364_980_000_000,
    "currentAssets": 152_987_000_000,
    "cashAndEquivalents": 29_943_000_000,
    "totalLiabilities": 308_030_000_000,
    "currentLiabilities": 176_392_000_000,
    "longTermDebt": 96_802_000_000,
    "totalEquity": 56_950_000_000,
    "shares_outstanding": 15_408_095_000,
}

CASHFLOW = {
    "operatingCashFlow": 118_254_000_000,
    "capitalExpenditures": -9_959_000_000,
    "dividendsPaid": -15_234_000_000,
    "shareRepurchases": -94_949_000_000,
}


class TestFullPipeline:
    def test_pipeline_produces_valid_composite_score(self):
        period = build_financial_period(
            income_json=INCOME,
            balance_json=BALANCE,
            cashflow_json=CASHFLOW,
            period_end="2024-09-28",
            filing_date="2024-11-01",
        )
        profile = build_asset_profile(
            ticker="AAPL",
            name="Apple Inc.",
            sector="Information Technology",
            market_cap=Decimal("3500000000000"),
        )

        result = run_scoring_pipeline(
            ticker="AAPL",
            period=period,
            profile=profile,
            price_bars=[],
            earnings=[],
        )

        assert isinstance(result, CompositeScore)
        assert result.ticker == "AAPL"
        assert 0.0 <= result.composite_percentile <= 100.0
        assert result.conviction_level.value in ("exceptional", "high", "watchlist", "none")
        assert result.signal.value in ("buy", "watch", "no_action", "hold", "sell", "urgent_sell")
        assert 0.0 <= result.data_coverage <= 1.0

        # Quality factors should be computed
        assert len(result.quality.sub_scores) == 4
        assert result.quality.factor_name == "quality"

        # Value factors should be computed
        assert len(result.value.sub_scores) == 4
        assert result.value.factor_name == "value"

        # Momentum factors (price momentum + placeholders)
        assert len(result.momentum.sub_scores) >= 1

        # Filters should all run
        assert len(result.filters_passed) == 6

    def test_pipeline_handles_excluded_sector(self):
        period = build_financial_period(
            income_json=INCOME,
            balance_json=BALANCE,
            cashflow_json=CASHFLOW,
            period_end="2024-09-28",
            filing_date="2024-11-01",
        )
        profile = build_asset_profile(
            ticker="JPM",
            name="JPMorgan Chase",
            sector="Financials",
            market_cap=Decimal("500000000000"),
        )

        # Should still produce a score even for excluded sectors
        result = run_scoring_pipeline(
            ticker="JPM",
            period=period,
            profile=profile,
            price_bars=[],
            earnings=[],
        )

        assert isinstance(result, CompositeScore)
        assert result.ticker == "JPM"
```

**Step 2: Run the integration test**

Run: `uv run pytest api/tests/test_pipeline_integration.py -v`
Expected: PASS

**Step 3: Commit**

```bash
git add api/tests/test_pipeline_integration.py
git commit -m "test(api): add end-to-end integration test for scoring pipeline"
```

---

### Task 12: Verify and fix all existing tests

**Step 1: Run all API tests**

Run: `uv run pytest api/tests/ -v`
Expected: All pass. If any fail due to removed `_score_store`, fix them.

**Step 2: Run all engine tests**

Run: `uv run pytest engine/tests/ -v`
Expected: All pass (engine is unchanged).

**Step 3: Run linting**

Run: `uv run ruff check api/src/ api/tests/ --fix`
Expected: Clean or auto-fixed.

**Step 4: Commit any fixes**

```bash
git add -u
git commit -m "fix(api): resolve test and lint issues after DB migration"
```

---

## Summary

| Task | What | Key Files |
|------|------|-----------|
| 1 | Add dependencies | `api/pyproject.toml` |
| 2 | FinancialData model + score_detail | `api/src/margin_api/db/models.py` |
| 3 | Alembic setup + initial migration | `api/alembic/` |
| 4 | Scoring service (engine bridge) | `api/src/margin_api/services/scoring.py` |
| 5 | Data seed CLI | `api/src/margin_api/cli.py` |
| 6 | ARQ background worker | `api/src/margin_api/worker.py` |
| 7 | Refactor scores route to DB | `api/src/margin_api/routes/scores.py` |
| 8 | Refactor dashboard route to DB | `api/src/margin_api/routes/dashboard.py` |
| 9 | Clean up conftest | `api/tests/conftest.py` |
| 10 | CLI score subcommand | `api/src/margin_api/cli.py` |
| 11 | E2E integration test | `api/tests/test_pipeline_integration.py` |
| 12 | Verify all tests pass | All test files |

**After completing all tasks**, the pipeline is:
1. `docker compose up -d` — Start PostgreSQL + Redis
2. `cd api && uv run alembic upgrade head` — Create tables
3. `uv run python -m margin_api.cli seed` — Fetch financial data for 50 tickers
4. `uv run python -m margin_api.cli score` — Score all tickers
5. `uv run uvicorn margin_api.app:create_app --factory --reload` — API serves real data
