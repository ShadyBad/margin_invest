# Margin Invest v1 — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a deterministic investment analysis platform that surfaces once-in-a-generation, high-conviction equity picks through a multi-stage scoring engine, validated by backtesting, served via a web app.

**Architecture:** Monorepo with three packages — `engine/` (pure Python scoring library), `api/` (FastAPI service), `web/` (Next.js frontend). Engine is the core, with zero web dependencies. API wraps the engine. Frontend consumes the API.

**Tech Stack:** Python 3.13.5+ (uv), FastAPI, PostgreSQL + TimescaleDB, ARQ (Redis), Next.js 15, Tailwind CSS, Framer Motion, NextAuth.js v5, Vitest, Playwright, pytest.

**Design Doc:** `docs/plans/2026-02-12-margin-invest-v1-design.md`

---

## Master Phase Overview

| Phase | Name | What It Delivers | Depends On |
|-------|------|-----------------|------------|
| 1 | Foundation & Data Models | Monorepo, Pydantic models, test infra, golden dataset | — |
| 2 | Elimination Filters | M-Score, Z-Score, distress checks, liquidity filters | 1 |
| 3 | Quality Factor | Gross Profitability, ROIC-WACC, Accrual Ratio, F-Score | 1 |
| 4 | Value Factor | EV/FCF, Shareholder Yield, DCF, Acquirer's Multiple | 1 |
| 5 | Momentum & Catalyst Factor | Price momentum, SUE, insider buying, institutional, sentiment | 1 |
| 6 | Composite Scoring & Classification | Percentile ranking, sector-neutral, growth stage, composite score | 2, 3, 4, 5 |
| 7 | Data Ingestion Layer | Provider abstraction, yfinance, Finnhub, EDGAR, FRED, FMP, Polygon, fallbacks | 1 |
| 8 | API Layer | Database schema, FastAPI, auth, endpoints, background jobs | 6, 7 |
| 9 | Web Frontend — Foundation | Next.js scaffold, design system, auth, layout | 8 |
| 10 | Web Frontend — Pages | Landing, dashboard, asset detail, settings | 9 |
| 11 | Real-Time Events | Event detection, WebSocket, notifications, re-scoring | 8 |
| 12 | Backtesting Engine | Walk-forward simulation, profile backtest, validation gate | 6, 7 |
| 13 | Web Frontend — Backtesting | Performance charts, metrics, heatmap | 10, 12 |
| 14 | Integration & Deployment | Full pipeline test, CI/CD, Vercel + Railway deploy | All |

Phases 2-5 can be parallelized (they share Phase 1 models but are independent of each other).
Phases 3, 4, 5 can be worked on simultaneously.
Phase 7 can be parallelized with Phases 2-5 (ingestion is independent of scoring logic).

---

## Phase 1: Foundation & Data Models

**Goal:** Establish the monorepo structure, core data models, test infrastructure, and golden test dataset. After this phase, every subsequent phase has a stable foundation to build on.

---

### Task 1: Initialize Monorepo with uv Workspaces

**Files:**
- Modify: `pyproject.toml` (workspace root)
- Create: `engine/pyproject.toml`
- Create: `engine/src/margin_engine/__init__.py`
- Create: `api/pyproject.toml`
- Create: `api/src/margin_api/__init__.py`

**Step 1: Configure workspace root pyproject.toml**

Replace the existing `pyproject.toml` with workspace configuration:

```toml
[project]
name = "margin-invest"
version = "0.1.0"
description = "Once-in-a-generation, high-conviction investment analysis"
readme = "README.md"
requires-python = ">=3.13.5"

[tool.uv.workspace]
members = ["engine", "api"]

[tool.pytest.ini_options]
testpaths = ["engine/tests", "api/tests"]
addopts = "-v --tb=short"

[tool.ruff]
target-version = "py313"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP"]
```

**Step 2: Create engine package**

`engine/pyproject.toml`:
```toml
[project]
name = "margin-engine"
version = "0.1.0"
description = "Margin Invest scoring engine — pure Python analysis library"
requires-python = ">=3.13.5"
dependencies = [
    "pydantic>=2.10",
    "numpy>=2.2",
    "scipy>=1.15",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3",
    "pytest-cov>=6.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/margin_engine"]
```

`engine/src/margin_engine/__init__.py`:
```python
"""Margin Engine — deterministic investment scoring library."""

__version__ = "0.1.0"
```

**Step 3: Create api package**

`api/pyproject.toml`:
```toml
[project]
name = "margin-api"
version = "0.1.0"
description = "Margin Invest API service"
requires-python = ">=3.13.5"
dependencies = [
    "margin-engine",
    "fastapi>=0.115",
    "uvicorn>=0.34",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3",
    "pytest-cov>=6.0",
    "httpx>=0.28",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/margin_api"]

[tool.uv.sources]
margin-engine = { workspace = true }
```

`api/src/margin_api/__init__.py`:
```python
"""Margin API — FastAPI service wrapping the scoring engine."""

__version__ = "0.1.0"
```

**Step 4: Install dependencies and verify workspace**

Run: `cd /Users/brandon/repos/margin_invest && uv sync`
Expected: Dependencies install successfully. Both workspace members detected.

Run: `uv run python -c "import margin_engine; print(margin_engine.__version__)"`
Expected: `0.1.0`

**Step 5: Commit**

```bash
git add pyproject.toml engine/ api/
git commit -m "feat: initialize uv workspace with engine and api packages"
```

---

### Task 2: Create Engine Directory Structure

**Files:**
- Create all `__init__.py` files for the engine package tree

**Step 1: Create directory structure**

```bash
mkdir -p engine/src/margin_engine/{ingestion/providers,scoring/{filters,quantitative,qualitative},backtesting,models}
mkdir -p engine/tests/{scoring/{filters,quantitative,qualitative},ingestion,backtesting,fixtures}
```

Create `__init__.py` in every package directory:

`engine/src/margin_engine/ingestion/__init__.py`: empty
`engine/src/margin_engine/ingestion/providers/__init__.py`: empty
`engine/src/margin_engine/scoring/__init__.py`: empty
`engine/src/margin_engine/scoring/filters/__init__.py`: empty
`engine/src/margin_engine/scoring/quantitative/__init__.py`: empty
`engine/src/margin_engine/scoring/qualitative/__init__.py`: empty
`engine/src/margin_engine/backtesting/__init__.py`: empty
`engine/src/margin_engine/models/__init__.py`: empty
`engine/tests/__init__.py`: empty
`engine/tests/scoring/__init__.py`: empty
`engine/tests/scoring/filters/__init__.py`: empty
`engine/tests/scoring/quantitative/__init__.py`: empty
`engine/tests/scoring/qualitative/__init__.py`: empty
`engine/tests/ingestion/__init__.py`: empty
`engine/tests/backtesting/__init__.py`: empty

**Step 2: Verify structure**

Run: `find engine/src -name "*.py" | sort`
Expected: All `__init__.py` files listed.

**Step 3: Commit**

```bash
git add engine/
git commit -m "feat: create engine package directory structure"
```

---

### Task 3: Core Financial Data Models

**Files:**
- Create: `engine/src/margin_engine/models/financial.py`
- Test: `engine/tests/test_models.py`

**Step 1: Write the failing test**

`engine/tests/test_models.py`:
```python
"""Tests for core financial data models."""

import pytest
from decimal import Decimal
from margin_engine.models.financial import (
    IncomeStatement,
    BalanceSheet,
    CashFlowStatement,
    FinancialPeriod,
    PriceBar,
    AssetProfile,
    GICSSector,
)


class TestIncomeStatement:
    def test_create_income_statement(self):
        stmt = IncomeStatement(
            revenue=Decimal("394328000000"),
            cost_of_revenue=Decimal("223546000000"),
            gross_profit=Decimal("170782000000"),
            sga_expense=Decimal("24932000000"),
            rd_expense=Decimal("29915000000"),
            depreciation=Decimal("11519000000"),
            ebit=Decimal("114301000000"),
            interest_expense=Decimal("3933000000"),
            tax_provision=Decimal("16741000000"),
            net_income=Decimal("96995000000"),
            shares_outstanding=15460000000,
        )
        assert stmt.revenue == Decimal("394328000000")
        assert stmt.gross_margin == pytest.approx(0.4331, abs=0.001)
        assert stmt.net_margin == pytest.approx(0.2460, abs=0.001)

    def test_gross_margin_calculation(self):
        stmt = IncomeStatement(
            revenue=Decimal("100"),
            cost_of_revenue=Decimal("60"),
            gross_profit=Decimal("40"),
            ebit=Decimal("20"),
            net_income=Decimal("15"),
            shares_outstanding=100,
        )
        assert stmt.gross_margin == pytest.approx(0.40)

    def test_zero_revenue_margin(self):
        stmt = IncomeStatement(
            revenue=Decimal("0"),
            cost_of_revenue=Decimal("0"),
            gross_profit=Decimal("0"),
            ebit=Decimal("0"),
            net_income=Decimal("-100"),
            shares_outstanding=100,
        )
        assert stmt.gross_margin == 0.0
        assert stmt.net_margin == 0.0


class TestBalanceSheet:
    def test_create_balance_sheet(self):
        bs = BalanceSheet(
            total_assets=Decimal("352583000000"),
            current_assets=Decimal("143566000000"),
            cash_and_equivalents=Decimal("29965000000"),
            receivables=Decimal("60932000000"),
            total_liabilities=Decimal("290437000000"),
            current_liabilities=Decimal("145308000000"),
            long_term_debt=Decimal("98959000000"),
            total_equity=Decimal("62146000000"),
            retained_earnings=Decimal("4336000000"),
            pp_and_e=Decimal("43715000000"),
            shares_outstanding=15460000000,
        )
        assert bs.working_capital == Decimal("143566000000") - Decimal("145308000000")
        assert bs.debt_to_equity == pytest.approx(1.5925, abs=0.001)
        assert bs.current_ratio == pytest.approx(0.9880, abs=0.001)

    def test_working_capital(self):
        bs = BalanceSheet(
            total_assets=Decimal("1000"),
            current_assets=Decimal("500"),
            total_liabilities=Decimal("600"),
            current_liabilities=Decimal("300"),
            total_equity=Decimal("400"),
            shares_outstanding=100,
        )
        assert bs.working_capital == Decimal("200")

    def test_zero_equity_debt_ratio(self):
        bs = BalanceSheet(
            total_assets=Decimal("1000"),
            current_assets=Decimal("500"),
            total_liabilities=Decimal("1000"),
            current_liabilities=Decimal("300"),
            total_equity=Decimal("0"),
            shares_outstanding=100,
        )
        assert bs.debt_to_equity == float("inf")


class TestCashFlowStatement:
    def test_create_cash_flow(self):
        cf = CashFlowStatement(
            operating_cash_flow=Decimal("110543000000"),
            capital_expenditures=Decimal("-10959000000"),
            dividends_paid=Decimal("-15025000000"),
            share_repurchases=Decimal("-77550000000"),
            share_issuance=Decimal("0"),
        )
        assert cf.free_cash_flow == Decimal("110543000000") + Decimal("-10959000000")
        assert cf.net_buybacks == Decimal("77550000000") - Decimal("0")

    def test_fcf_calculation(self):
        cf = CashFlowStatement(
            operating_cash_flow=Decimal("100"),
            capital_expenditures=Decimal("-30"),
        )
        assert cf.free_cash_flow == Decimal("70")


class TestFinancialPeriod:
    def test_create_period_with_two_years(self):
        current_income = IncomeStatement(
            revenue=Decimal("200"),
            cost_of_revenue=Decimal("100"),
            gross_profit=Decimal("100"),
            ebit=Decimal("50"),
            net_income=Decimal("30"),
            shares_outstanding=100,
        )
        prior_income = IncomeStatement(
            revenue=Decimal("180"),
            cost_of_revenue=Decimal("100"),
            gross_profit=Decimal("80"),
            ebit=Decimal("40"),
            net_income=Decimal("20"),
            shares_outstanding=100,
        )
        current_balance = BalanceSheet(
            total_assets=Decimal("500"),
            current_assets=Decimal("200"),
            total_liabilities=Decimal("300"),
            current_liabilities=Decimal("150"),
            total_equity=Decimal("200"),
            shares_outstanding=100,
        )
        prior_balance = BalanceSheet(
            total_assets=Decimal("480"),
            current_assets=Decimal("190"),
            total_liabilities=Decimal("290"),
            current_liabilities=Decimal("140"),
            total_equity=Decimal("190"),
            shares_outstanding=100,
        )
        current_cf = CashFlowStatement(
            operating_cash_flow=Decimal("40"),
            capital_expenditures=Decimal("-10"),
        )
        period = FinancialPeriod(
            period_end="2024-09-28",
            filing_date="2024-11-01",
            current_income=current_income,
            prior_income=prior_income,
            current_balance=current_balance,
            prior_balance=prior_balance,
            current_cash_flow=current_cf,
        )
        assert period.period_end == "2024-09-28"
        assert period.revenue_growth == pytest.approx(0.1111, abs=0.001)


class TestAssetProfile:
    def test_create_asset_profile(self):
        profile = AssetProfile(
            ticker="AAPL",
            name="Apple Inc.",
            sector=GICSSector.TECHNOLOGY,
            sub_industry="Technology Hardware, Storage & Peripherals",
            market_cap=Decimal("3500000000000"),
            avg_daily_volume=Decimal("55000000"),
            years_of_history=20,
        )
        assert profile.ticker == "AAPL"
        assert profile.sector == GICSSector.TECHNOLOGY
        assert profile.is_excluded is False

    def test_financials_excluded(self):
        profile = AssetProfile(
            ticker="JPM",
            name="JPMorgan Chase",
            sector=GICSSector.FINANCIALS,
            market_cap=Decimal("500000000000"),
            avg_daily_volume=Decimal("10000000"),
            years_of_history=20,
        )
        assert profile.is_excluded is True

    def test_real_estate_excluded(self):
        profile = AssetProfile(
            ticker="AMT",
            name="American Tower",
            sector=GICSSector.REAL_ESTATE,
            market_cap=Decimal("100000000000"),
            avg_daily_volume=Decimal("5000000"),
            years_of_history=15,
        )
        assert profile.is_excluded is True


class TestPriceBar:
    def test_create_price_bar(self):
        bar = PriceBar(
            date="2024-01-15",
            open=Decimal("185.50"),
            high=Decimal("187.20"),
            low=Decimal("184.80"),
            close=Decimal("186.90"),
            volume=50000000,
            adj_close=Decimal("186.90"),
        )
        assert bar.close == Decimal("186.90")
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/brandon/repos/margin_invest && uv run pytest engine/tests/test_models.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'margin_engine.models.financial'`

**Step 3: Write the implementation**

`engine/src/margin_engine/models/financial.py`:
```python
"""Core financial data models for the Margin scoring engine.

All monetary values use Decimal for precision. Computed properties
derive ratios and metrics from raw financial data.
"""

from __future__ import annotations

from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class GICSSector(str, Enum):
    """GICS sector classification. 11 sectors."""

    TECHNOLOGY = "Information Technology"
    HEALTHCARE = "Health Care"
    FINANCIALS = "Financials"
    CONSUMER_DISCRETIONARY = "Consumer Discretionary"
    CONSUMER_STAPLES = "Consumer Staples"
    ENERGY = "Energy"
    INDUSTRIALS = "Industrials"
    MATERIALS = "Materials"
    REAL_ESTATE = "Real Estate"
    UTILITIES = "Utilities"
    COMMUNICATION_SERVICES = "Communication Services"

    @property
    def is_excluded_v1(self) -> bool:
        return self in (GICSSector.FINANCIALS, GICSSector.REAL_ESTATE)

    @property
    def is_cyclical(self) -> bool:
        return self in (
            GICSSector.ENERGY,
            GICSSector.MATERIALS,
            GICSSector.INDUSTRIALS,
            GICSSector.CONSUMER_DISCRETIONARY,
        )


class IncomeStatement(BaseModel):
    """Annual or quarterly income statement data."""

    revenue: Decimal
    cost_of_revenue: Decimal = Decimal("0")
    gross_profit: Decimal = Decimal("0")
    sga_expense: Optional[Decimal] = None
    rd_expense: Optional[Decimal] = None
    depreciation: Optional[Decimal] = None
    ebit: Decimal = Decimal("0")
    interest_expense: Optional[Decimal] = None
    tax_provision: Optional[Decimal] = None
    net_income: Decimal = Decimal("0")
    shares_outstanding: int = 0

    @property
    def gross_margin(self) -> float:
        if self.revenue == 0:
            return 0.0
        return float(self.gross_profit / self.revenue)

    @property
    def net_margin(self) -> float:
        if self.revenue == 0:
            return 0.0
        return float(self.net_income / self.revenue)

    @property
    def effective_tax_rate(self) -> float:
        if self.tax_provision is None or self.ebit == 0:
            return 0.21  # Default US corporate rate
        pretax = self.ebit - (self.interest_expense or Decimal("0"))
        if pretax <= 0:
            return 0.21
        return float(self.tax_provision / pretax)


class BalanceSheet(BaseModel):
    """Annual or quarterly balance sheet data."""

    total_assets: Decimal
    current_assets: Decimal = Decimal("0")
    cash_and_equivalents: Optional[Decimal] = None
    receivables: Optional[Decimal] = None
    total_liabilities: Decimal = Decimal("0")
    current_liabilities: Decimal = Decimal("0")
    long_term_debt: Optional[Decimal] = None
    total_equity: Decimal = Decimal("0")
    retained_earnings: Optional[Decimal] = None
    pp_and_e: Optional[Decimal] = None
    shares_outstanding: int = 0

    @property
    def working_capital(self) -> Decimal:
        return self.current_assets - self.current_liabilities

    @property
    def debt_to_equity(self) -> float:
        if self.total_equity == 0:
            return float("inf")
        total_debt = (self.long_term_debt or Decimal("0")) + self.current_liabilities
        return float(total_debt / self.total_equity)

    @property
    def current_ratio(self) -> float:
        if self.current_liabilities == 0:
            return float("inf")
        return float(self.current_assets / self.current_liabilities)

    @property
    def total_debt(self) -> Decimal:
        return (self.long_term_debt or Decimal("0")) + self.current_liabilities


class CashFlowStatement(BaseModel):
    """Annual or quarterly cash flow statement data."""

    operating_cash_flow: Decimal = Decimal("0")
    capital_expenditures: Decimal = Decimal("0")  # Usually negative
    dividends_paid: Optional[Decimal] = None  # Usually negative
    share_repurchases: Optional[Decimal] = None  # Usually negative
    share_issuance: Optional[Decimal] = None

    @property
    def free_cash_flow(self) -> Decimal:
        return self.operating_cash_flow + self.capital_expenditures

    @property
    def net_buybacks(self) -> Decimal:
        repurchases = abs(self.share_repurchases or Decimal("0"))
        issuance = abs(self.share_issuance or Decimal("0"))
        return repurchases - issuance


class FinancialPeriod(BaseModel):
    """A complete financial snapshot: current and prior period for YoY comparisons."""

    period_end: str  # ISO date: "2024-09-28"
    filing_date: str  # ISO date: "2024-11-01"

    current_income: IncomeStatement
    prior_income: Optional[IncomeStatement] = None
    current_balance: BalanceSheet
    prior_balance: Optional[BalanceSheet] = None
    current_cash_flow: CashFlowStatement
    prior_cash_flow: Optional[CashFlowStatement] = None

    @property
    def revenue_growth(self) -> Optional[float]:
        if self.prior_income is None or self.prior_income.revenue == 0:
            return None
        return float(
            (self.current_income.revenue - self.prior_income.revenue)
            / self.prior_income.revenue
        )


class PriceBar(BaseModel):
    """Single OHLCV price bar."""

    date: str  # ISO date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    adj_close: Optional[Decimal] = None


class AssetProfile(BaseModel):
    """Static asset metadata and classification."""

    ticker: str
    name: str
    sector: GICSSector
    sub_industry: Optional[str] = None
    market_cap: Decimal = Decimal("0")
    avg_daily_volume: Decimal = Decimal("0")
    years_of_history: int = 0

    @property
    def is_excluded(self) -> bool:
        return self.sector.is_excluded_v1
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/brandon/repos/margin_invest && uv sync && uv run pytest engine/tests/test_models.py -v`
Expected: All tests PASS.

**Step 5: Commit**

```bash
git add engine/src/margin_engine/models/financial.py engine/tests/test_models.py
git commit -m "feat(engine): add core financial data models with computed properties"
```

---

### Task 4: Scoring Result Models

**Files:**
- Create: `engine/src/margin_engine/models/scoring.py`
- Test: `engine/tests/test_scoring_models.py`

**Step 1: Write the failing test**

`engine/tests/test_scoring_models.py`:
```python
"""Tests for scoring result models."""

import pytest
from margin_engine.models.scoring import (
    FilterResult,
    FilterVerdict,
    FactorScore,
    FactorBreakdown,
    CompositeScore,
    ConvictionLevel,
    Signal,
    GrowthStage,
    ScoringConfig,
)


class TestFilterResult:
    def test_pass(self):
        result = FilterResult(
            name="beneish_m_score",
            passed=True,
            value=-2.94,
            threshold=-1.78,
            detail="M-Score well below threshold",
        )
        assert result.passed is True
        assert result.verdict == FilterVerdict.PASS

    def test_fail(self):
        result = FilterResult(
            name="beneish_m_score",
            passed=False,
            value=-1.50,
            threshold=-1.78,
            detail="M-Score above threshold — possible manipulation",
        )
        assert result.passed is False
        assert result.verdict == FilterVerdict.FAIL


class TestFactorScore:
    def test_create_factor_score(self):
        score = FactorScore(
            name="gross_profitability",
            raw_value=0.732,
            percentile_rank=98.0,
            detail="Revenue $394B, COGS $224B, Total Assets $353B",
        )
        assert score.percentile_rank == 98.0

    def test_percentile_bounds(self):
        with pytest.raises(ValueError):
            FactorScore(name="test", raw_value=0.5, percentile_rank=101.0)
        with pytest.raises(ValueError):
            FactorScore(name="test", raw_value=0.5, percentile_rank=-1.0)


class TestFactorBreakdown:
    def test_quality_factor(self):
        breakdown = FactorBreakdown(
            factor_name="quality",
            weight=0.35,
            sub_scores=[
                FactorScore(name="gross_profitability", raw_value=0.73, percentile_rank=98.0),
                FactorScore(name="roic_wacc_spread", raw_value=0.58, percentile_rank=99.0),
                FactorScore(name="accrual_ratio", raw_value=-0.02, percentile_rank=96.0),
                FactorScore(name="f_score", raw_value=8.0, percentile_rank=95.0),
            ],
        )
        assert breakdown.average_percentile == pytest.approx(97.0)


class TestCompositeScore:
    def test_conviction_level_exceptional(self):
        score = CompositeScore(
            ticker="NVDA",
            composite_percentile=96.0,
            quality=FactorBreakdown(
                factor_name="quality", weight=0.35, sub_scores=[]
            ),
            value=FactorBreakdown(
                factor_name="value", weight=0.30, sub_scores=[]
            ),
            momentum=FactorBreakdown(
                factor_name="momentum", weight=0.35, sub_scores=[]
            ),
            filters_passed=[],
            data_coverage=1.0,
        )
        assert score.conviction_level == ConvictionLevel.EXCEPTIONAL
        assert score.signal == Signal.BUY

    def test_conviction_level_high(self):
        score = CompositeScore(
            ticker="COST",
            composite_percentile=95.5,
            quality=FactorBreakdown(factor_name="quality", weight=0.35, sub_scores=[]),
            value=FactorBreakdown(factor_name="value", weight=0.30, sub_scores=[]),
            momentum=FactorBreakdown(factor_name="momentum", weight=0.35, sub_scores=[]),
            filters_passed=[],
            data_coverage=1.0,
        )
        assert score.conviction_level == ConvictionLevel.HIGH
        assert score.signal == Signal.BUY

    def test_conviction_level_watchlist(self):
        score = CompositeScore(
            ticker="XYZ",
            composite_percentile=92.0,
            quality=FactorBreakdown(factor_name="quality", weight=0.35, sub_scores=[]),
            value=FactorBreakdown(factor_name="value", weight=0.30, sub_scores=[]),
            momentum=FactorBreakdown(factor_name="momentum", weight=0.35, sub_scores=[]),
            filters_passed=[],
            data_coverage=1.0,
        )
        assert score.conviction_level == ConvictionLevel.WATCHLIST
        assert score.signal == Signal.WATCH

    def test_not_recommended(self):
        score = CompositeScore(
            ticker="BAD",
            composite_percentile=50.0,
            quality=FactorBreakdown(factor_name="quality", weight=0.35, sub_scores=[]),
            value=FactorBreakdown(factor_name="value", weight=0.30, sub_scores=[]),
            momentum=FactorBreakdown(factor_name="momentum", weight=0.35, sub_scores=[]),
            filters_passed=[],
            data_coverage=1.0,
        )
        assert score.conviction_level == ConvictionLevel.NONE
        assert score.signal == Signal.NO_ACTION


class TestGrowthStage:
    def test_all_stages_exist(self):
        stages = [
            GrowthStage.HIGH_GROWTH,
            GrowthStage.STEADY_GROWTH,
            GrowthStage.MATURE,
            GrowthStage.CYCLICAL,
            GrowthStage.TURNAROUND,
        ]
        assert len(stages) == 5


class TestScoringConfig:
    def test_default_weights(self):
        config = ScoringConfig()
        assert config.quality_weight == 0.35
        assert config.value_weight == 0.30
        assert config.momentum_weight == 0.35
        assert config.quality_weight + config.value_weight + config.momentum_weight == pytest.approx(1.0)

    def test_growth_stage_weights(self):
        config = ScoringConfig()
        weights = config.weights_for_stage(GrowthStage.HIGH_GROWTH)
        assert weights == (0.40, 0.25, 0.35)

        weights = config.weights_for_stage(GrowthStage.MATURE)
        assert weights == (0.30, 0.40, 0.30)

    def test_all_stage_weights_sum_to_one(self):
        config = ScoringConfig()
        for stage in GrowthStage:
            q, v, m = config.weights_for_stage(stage)
            assert q + v + m == pytest.approx(1.0), f"Weights for {stage} don't sum to 1.0"
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest engine/tests/test_scoring_models.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Write the implementation**

`engine/src/margin_engine/models/scoring.py`:
```python
"""Scoring result models — outputs of the conviction engine."""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class FilterVerdict(str, Enum):
    PASS = "pass"
    FAIL = "fail"


class ConvictionLevel(str, Enum):
    EXCEPTIONAL = "exceptional"  # Top 1% (99-100)
    HIGH = "high"  # Top 5% (95-98)
    WATCHLIST = "watchlist"  # Top 10% (90-94)
    NONE = "none"  # Below 90


class Signal(str, Enum):
    BUY = "buy"
    HOLD = "hold"
    WATCH = "watch"
    SELL = "sell"
    URGENT_SELL = "urgent_sell"
    NO_ACTION = "no_action"


class GrowthStage(str, Enum):
    HIGH_GROWTH = "high_growth"
    STEADY_GROWTH = "steady_growth"
    MATURE = "mature"
    CYCLICAL = "cyclical"
    TURNAROUND = "turnaround"


class FilterResult(BaseModel):
    """Result of a single elimination filter."""

    name: str
    passed: bool
    value: Optional[float] = None
    threshold: Optional[float] = None
    detail: str = ""

    @property
    def verdict(self) -> FilterVerdict:
        return FilterVerdict.PASS if self.passed else FilterVerdict.FAIL


class FactorScore(BaseModel):
    """Score for a single sub-factor (e.g., gross profitability)."""

    name: str
    raw_value: float
    percentile_rank: float = Field(ge=0.0, le=100.0)
    detail: str = ""

    @field_validator("percentile_rank")
    @classmethod
    def validate_percentile(cls, v: float) -> float:
        if v < 0.0 or v > 100.0:
            raise ValueError(f"Percentile rank must be 0-100, got {v}")
        return v


class FactorBreakdown(BaseModel):
    """Breakdown of a top-level factor (quality, value, momentum)."""

    factor_name: str
    weight: float
    sub_scores: list[FactorScore]

    @property
    def average_percentile(self) -> float:
        if not self.sub_scores:
            return 0.0
        return sum(s.percentile_rank for s in self.sub_scores) / len(self.sub_scores)


class CompositeScore(BaseModel):
    """Complete scoring result for a single asset."""

    ticker: str
    composite_percentile: float = Field(ge=0.0, le=100.0)
    quality: FactorBreakdown
    value: FactorBreakdown
    momentum: FactorBreakdown
    filters_passed: list[FilterResult]
    data_coverage: float = Field(ge=0.0, le=1.0)
    growth_stage: Optional[GrowthStage] = None

    @property
    def conviction_level(self) -> ConvictionLevel:
        if self.composite_percentile >= 99.0:
            return ConvictionLevel.EXCEPTIONAL
        elif self.composite_percentile >= 95.0:
            return ConvictionLevel.HIGH
        elif self.composite_percentile >= 90.0:
            return ConvictionLevel.WATCHLIST
        return ConvictionLevel.NONE

    @property
    def signal(self) -> Signal:
        level = self.conviction_level
        if level in (ConvictionLevel.EXCEPTIONAL, ConvictionLevel.HIGH):
            return Signal.BUY
        elif level == ConvictionLevel.WATCHLIST:
            return Signal.WATCH
        return Signal.NO_ACTION


class ScoringConfig(BaseModel):
    """Configuration for the scoring engine — factor weights and thresholds."""

    # Default weights (Steady Growth)
    quality_weight: float = 0.35
    value_weight: float = 0.30
    momentum_weight: float = 0.35

    # Conviction thresholds (percentile)
    exceptional_threshold: float = 99.0
    high_threshold: float = 95.0
    watchlist_threshold: float = 90.0
    sell_threshold: float = 85.0

    # Turnaround stocks need higher bar
    turnaround_threshold: float = 97.0  # Top 3% instead of top 5%

    def weights_for_stage(self, stage: GrowthStage) -> tuple[float, float, float]:
        """Return (quality, value, momentum) weights for a growth stage."""
        stage_weights = {
            GrowthStage.HIGH_GROWTH: (0.40, 0.25, 0.35),
            GrowthStage.STEADY_GROWTH: (0.35, 0.30, 0.35),
            GrowthStage.MATURE: (0.30, 0.40, 0.30),
            GrowthStage.CYCLICAL: (0.35, 0.30, 0.35),
            GrowthStage.TURNAROUND: (0.35, 0.30, 0.35),
        }
        return stage_weights[stage]
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest engine/tests/test_scoring_models.py -v`
Expected: All tests PASS.

**Step 5: Commit**

```bash
git add engine/src/margin_engine/models/scoring.py engine/tests/test_scoring_models.py
git commit -m "feat(engine): add scoring result models with conviction levels and growth stage weights"
```

---

### Task 5: Model Exports and Golden Test Fixture

**Files:**
- Modify: `engine/src/margin_engine/models/__init__.py`
- Create: `engine/tests/fixtures/golden_apple_2024.py`
- Test: `engine/tests/test_golden_fixture.py`

**Step 1: Update models __init__.py to export all models**

`engine/src/margin_engine/models/__init__.py`:
```python
"""Data models for the Margin scoring engine."""

from margin_engine.models.financial import (
    AssetProfile,
    BalanceSheet,
    CashFlowStatement,
    FinancialPeriod,
    GICSSector,
    IncomeStatement,
    PriceBar,
)
from margin_engine.models.scoring import (
    CompositeScore,
    ConvictionLevel,
    FactorBreakdown,
    FactorScore,
    FilterResult,
    FilterVerdict,
    GrowthStage,
    ScoringConfig,
    Signal,
)

__all__ = [
    "AssetProfile",
    "BalanceSheet",
    "CashFlowStatement",
    "CompositeScore",
    "ConvictionLevel",
    "FactorBreakdown",
    "FactorScore",
    "FilterResult",
    "FilterVerdict",
    "FinancialPeriod",
    "GICSSector",
    "GrowthStage",
    "IncomeStatement",
    "PriceBar",
    "ScoringConfig",
    "Signal",
]
```

**Step 2: Create golden fixture (Apple FY2024 10-K data)**

This is hand-verified data from Apple's actual SEC filings. It serves as the source of truth for all scoring formula tests.

`engine/tests/fixtures/golden_apple_2024.py`:
```python
"""Golden test fixture: Apple Inc. FY2024 (10-K filed Nov 1, 2024).

All values sourced from Apple's actual SEC filing.
Used to verify scoring formulas produce correct results against
known real-world data.
"""

from decimal import Decimal

from margin_engine.models import (
    AssetProfile,
    BalanceSheet,
    CashFlowStatement,
    FinancialPeriod,
    GICSSector,
    IncomeStatement,
)

APPLE_PROFILE = AssetProfile(
    ticker="AAPL",
    name="Apple Inc.",
    sector=GICSSector.TECHNOLOGY,
    sub_industry="Technology Hardware, Storage & Peripherals",
    market_cap=Decimal("3500000000000"),  # ~$3.5T
    avg_daily_volume=Decimal("55000000"),
    years_of_history=20,
)

# FY2024 (ended Sept 28, 2024)
APPLE_INCOME_2024 = IncomeStatement(
    revenue=Decimal("391035000000"),
    cost_of_revenue=Decimal("210352000000"),
    gross_profit=Decimal("180683000000"),
    sga_expense=Decimal("26742000000"),
    rd_expense=Decimal("31370000000"),
    depreciation=Decimal("11445000000"),
    ebit=Decimal("122571000000"),
    interest_expense=Decimal("3583000000"),
    tax_provision=Decimal("29749000000"),
    net_income=Decimal("93736000000"),
    shares_outstanding=15408095000,
)

# FY2023 (ended Sept 30, 2023)
APPLE_INCOME_2023 = IncomeStatement(
    revenue=Decimal("383285000000"),
    cost_of_revenue=Decimal("214137000000"),
    gross_profit=Decimal("169148000000"),
    sga_expense=Decimal("24932000000"),
    rd_expense=Decimal("29915000000"),
    depreciation=Decimal("11519000000"),
    ebit=Decimal("114301000000"),
    interest_expense=Decimal("3933000000"),
    tax_provision=Decimal("16741000000"),
    net_income=Decimal("96995000000"),
    shares_outstanding=15460000000,
)

# Balance Sheet FY2024
APPLE_BALANCE_2024 = BalanceSheet(
    total_assets=Decimal("364980000000"),
    current_assets=Decimal("152987000000"),
    cash_and_equivalents=Decimal("29943000000"),
    receivables=Decimal("66243000000"),
    total_liabilities=Decimal("308030000000"),
    current_liabilities=Decimal("176392000000"),
    long_term_debt=Decimal("96811000000"),
    total_equity=Decimal("56950000000"),
    retained_earnings=Decimal("-19154000000"),
    pp_and_e=Decimal("44856000000"),
    shares_outstanding=15408095000,
)

# Balance Sheet FY2023
APPLE_BALANCE_2023 = BalanceSheet(
    total_assets=Decimal("352583000000"),
    current_assets=Decimal("143566000000"),
    cash_and_equivalents=Decimal("29965000000"),
    receivables=Decimal("60932000000"),
    total_liabilities=Decimal("290437000000"),
    current_liabilities=Decimal("145308000000"),
    long_term_debt=Decimal("95281000000"),
    total_equity=Decimal("62146000000"),
    retained_earnings=Decimal("4336000000"),
    pp_and_e=Decimal("43715000000"),
    shares_outstanding=15460000000,
)

# Cash Flow FY2024
APPLE_CASHFLOW_2024 = CashFlowStatement(
    operating_cash_flow=Decimal("118254000000"),
    capital_expenditures=Decimal("-9959000000"),
    dividends_paid=Decimal("-15234000000"),
    share_repurchases=Decimal("-94949000000"),
    share_issuance=Decimal("0"),
)

# Cash Flow FY2023
APPLE_CASHFLOW_2023 = CashFlowStatement(
    operating_cash_flow=Decimal("110543000000"),
    capital_expenditures=Decimal("-10959000000"),
    dividends_paid=Decimal("-15025000000"),
    share_repurchases=Decimal("-77550000000"),
    share_issuance=Decimal("0"),
)

APPLE_PERIOD_2024 = FinancialPeriod(
    period_end="2024-09-28",
    filing_date="2024-11-01",
    current_income=APPLE_INCOME_2024,
    prior_income=APPLE_INCOME_2023,
    current_balance=APPLE_BALANCE_2024,
    prior_balance=APPLE_BALANCE_2023,
    current_cash_flow=APPLE_CASHFLOW_2024,
    prior_cash_flow=APPLE_CASHFLOW_2023,
)

# Pre-computed expected values for verification
EXPECTED = {
    "gross_margin_2024": 0.4621,  # 180683 / 391035
    "gross_margin_2023": 0.4413,  # 169148 / 383285
    "revenue_growth": 0.0202,  # (391035 - 383285) / 383285
    "fcf_2024": 108295000000,  # 118254 - 9959 (millions)
    "net_buyback_2024": 94949000000,
    "working_capital_2024": -23405000000,  # 152987 - 176392 (millions)
    "current_ratio_2024": 0.8673,  # 152987 / 176392
    "roa_2024": 0.2568,  # 93736 / 364980
    "roa_2023": 0.2751,  # 96995 / 352583
}
```

**Step 3: Write test to verify the golden fixture**

`engine/tests/test_golden_fixture.py`:
```python
"""Verify golden fixture data produces expected computed values."""

import pytest
from engine.tests.fixtures.golden_apple_2024 import (
    APPLE_INCOME_2024,
    APPLE_INCOME_2023,
    APPLE_BALANCE_2024,
    APPLE_CASHFLOW_2024,
    APPLE_PERIOD_2024,
    APPLE_PROFILE,
    EXPECTED,
)


class TestGoldenAppleFixture:
    def test_gross_margin_2024(self):
        assert APPLE_INCOME_2024.gross_margin == pytest.approx(
            EXPECTED["gross_margin_2024"], abs=0.001
        )

    def test_gross_margin_2023(self):
        assert APPLE_INCOME_2023.gross_margin == pytest.approx(
            EXPECTED["gross_margin_2023"], abs=0.001
        )

    def test_revenue_growth(self):
        assert APPLE_PERIOD_2024.revenue_growth == pytest.approx(
            EXPECTED["revenue_growth"], abs=0.001
        )

    def test_fcf_2024(self):
        assert APPLE_CASHFLOW_2024.free_cash_flow == EXPECTED["fcf_2024"]

    def test_net_buybacks(self):
        assert APPLE_CASHFLOW_2024.net_buybacks == EXPECTED["net_buyback_2024"]

    def test_working_capital(self):
        assert APPLE_BALANCE_2024.working_capital == EXPECTED["working_capital_2024"]

    def test_current_ratio(self):
        assert APPLE_BALANCE_2024.current_ratio == pytest.approx(
            EXPECTED["current_ratio_2024"], abs=0.001
        )

    def test_roa_2024(self):
        roa = float(APPLE_INCOME_2024.net_income / APPLE_BALANCE_2024.total_assets)
        assert roa == pytest.approx(EXPECTED["roa_2024"], abs=0.001)

    def test_profile_not_excluded(self):
        assert APPLE_PROFILE.is_excluded is False

    def test_profile_sector(self):
        assert APPLE_PROFILE.sector.is_cyclical is False
```

**Step 4: Run all tests**

Run: `uv run pytest engine/tests/ -v`
Expected: All tests PASS.

**Step 5: Commit**

```bash
git add engine/src/margin_engine/models/__init__.py engine/tests/fixtures/ engine/tests/test_golden_fixture.py
git commit -m "feat(engine): add model exports and Apple FY2024 golden test fixture"
```

---

### Task 6: Docker Compose for Local Development

**Files:**
- Create: `docker-compose.yml`
- Modify: `.gitignore`

**Step 1: Create Docker Compose**

`docker-compose.yml`:
```yaml
services:
  db:
    image: timescale/timescaledb:latest-pg16
    ports:
      - "5432:5432"
    environment:
      POSTGRES_USER: margin
      POSTGRES_PASSWORD: margin_dev
      POSTGRES_DB: margin_invest
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U margin -d margin_invest"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  pgdata:
```

**Step 2: Update .gitignore**

Add to `.gitignore`:
```
# Python
__pycache__/
*.py[cod]
*.egg-info/
dist/
build/
.eggs/

# Virtual environments
.venv/

# Environment
.env
.env.local

# IDE
.idea/
.vscode/
*.swp

# OS
.DS_Store
Thumbs.db

# Coverage
htmlcov/
.coverage
coverage.xml

# Node
node_modules/
.next/
```

**Step 3: Verify Docker Compose**

Run: `cd /Users/brandon/repos/margin_invest && docker compose config`
Expected: Valid configuration output, no errors.

**Step 4: Commit**

```bash
git add docker-compose.yml .gitignore
git commit -m "infra: add Docker Compose for PostgreSQL/TimescaleDB and Redis"
```

---

### Task 7: Update CLAUDE.md with Project Conventions

**Files:**
- Modify: `CLAUDE.md`

**Step 1: Update CLAUDE.md**

Replace contents of `CLAUDE.md` with:

```markdown
# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Project Overview

Margin Invest is a deterministic investment analysis platform. See `docs/plans/2026-02-12-margin-invest-v1-design.md` for the complete design document.

## Architecture

Monorepo with three packages:
- `engine/` — Pure Python scoring library (zero web dependencies)
- `api/` — FastAPI service wrapping the engine
- `web/` — Next.js 15 frontend

## Package Management

Use **uv** for all Python project and package management:

```bash
uv add <package> --package margin-engine    # Add to engine
uv add <package> --package margin-api       # Add to api
uv sync                                      # Sync all workspace members
uv run <command>                             # Run in virtual environment
```

Use **context7 MCP** to look up documentation for libraries and frameworks before implementing solutions.

## Running Tests

```bash
uv run pytest engine/tests/ -v              # Engine tests
uv run pytest api/tests/ -v                 # API tests
uv run pytest -v                            # All tests
uv run pytest --cov=margin_engine engine/   # With coverage
```

## Development Services

```bash
docker compose up -d                         # Start PostgreSQL/TimescaleDB + Redis
docker compose down                          # Stop services
```

## Python Version

Python 3.13.5+ (specified in `.python-version`).

## Code Standards

- **TDD**: Write failing test first, then implement. No scoring formula ships without a golden-value test.
- **Coverage**: engine/ ≥ 95%, api/ ≥ 90%, web/ ≥ 80%
- **Formatting**: Ruff (line length 100)
- **Types**: All public functions must have type annotations
- **Models**: Use Pydantic for all data models
- **Determinism**: Same inputs must produce same outputs. AI calls use temperature=0.

## Key Design Principles

- Elimination filters run BEFORE scoring (fail-fast)
- All scoring uses percentile ranks (0-100) for cross-factor comparison
- Sector-neutral scoring: rank within GICS sector first, then combine
- Growth stage determines factor weight adjustments
- Cyclical assets use 7-year median normalization
- No human judgment anywhere in the pipeline
```

**Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md with project conventions and development guide"
```

---

### Phase 1 Complete

After these 7 tasks, you have:
- Monorepo with uv workspaces (engine + api)
- Complete Pydantic data models (financial statements, scoring results, classifications)
- Golden test fixture (Apple FY2024 real data)
- Test infrastructure with passing tests
- Docker Compose for local services
- Updated CLAUDE.md with project conventions

**Next:** Phase 2 (Elimination Filters) builds directly on these models. Each filter takes a `FinancialPeriod` and returns a `FilterResult`.

---

## Phase 2: Elimination Filters (Preview)

Detailed tasks for Phase 2 will follow the same TDD pattern. High-level:

- Task 1: Beneish M-Score (8 variables, formula, threshold test against Apple golden data)
- Task 2: Altman Z'' Score (4 variables, sector-aware thresholds)
- Task 3: FCF Distress Check (3 consecutive negative quarters)
- Task 4: Interest Coverage Ratio (sector-adjusted thresholds)
- Task 5: Current Ratio (sector-adjusted thresholds)
- Task 6: Liquidity Filter (market cap, volume, history, sector exclusion)
- Task 7: Filter Pipeline (chain all filters, return list of FilterResults)
- Task 8: Integration test with golden fixture (Apple should pass all filters)

## Phases 3-14 (Preview)

Each subsequent phase follows identical TDD structure. Detailed task breakdowns will be written at the start of each phase. The design doc contains all formulas and specifications needed.
