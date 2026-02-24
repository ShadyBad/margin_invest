# Backtesting Engine Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a replay-based backtesting engine that runs the real margin_engine pipeline against 20 years of point-in-time data, with a shadow portfolio, regime segmentation, failure audit, and a pro-tier web UI.

**Architecture:** Replay orchestrator calls actual `margin_engine` elimination filters and scoring functions against historical point-in-time snapshots. Pre-computed default backtest loads instantly; on-demand knob adjustments run via ARQ workers. Shadow portfolio tracks live model decisions daily. Web UI shows teaser (free) and full analysis (pro).

**Tech Stack:** Python (margin_engine, FastAPI, SQLAlchemy, ARQ), PostgreSQL, Next.js 16, React 19, Recharts, Tailwind v4

**Design Doc:** `docs/plans/2026-02-24-backtesting-engine-design.md`

---

## Task Dependency Map

```
T1 (Factor Registry) ──┐
T2 (PIT Provider)    ──┼──→ T5 (Replay Orchestrator) ──→ T8 (API Endpoints) ──→ T11 (Web Teaser)
T3 (Regime Classifier)─┘         │                            │                       │
                                  ├──→ T6 (Failure Audit)      │                       ▼
                                  └──→ T7 (Walk-Forward OOS)   │                  T12-T17 (Full Page)
                                                                │
T4 (Shadow Portfolio Engine) ──→ T9 (Shadow Portfolio API) ──→ T17 (Shadow Section)
                                                                │
T10 (Worker Jobs) ←─────────────────────────────────────────────┘
```

**Parallel Groups:**
- Group 1 (independent): T1, T2, T3, T4
- Group 2 (after T1+T2+T3): T5
- Group 3 (after T5): T6, T7 (parallel)
- Group 4 (after T5+T4): T8, T9, T10 (parallel)
- Group 5 (after T8): T11
- Group 6 (after T8+T9): T12-T17 (some parallel)

---

### Task 1: Factor Availability Registry

Pure engine module. Declares which factors have reliable data at which dates. Used by the replay orchestrator to know which factors to include at each historical point.

**Files:**
- Create: `engine/src/margin_engine/backtesting/factor_registry.py`
- Create: `engine/tests/backtesting/test_factor_registry.py`

**Step 1: Write the failing test**

```python
"""Tests for factor availability registry."""

from datetime import date

import pytest

from margin_engine.backtesting.factor_registry import (
    FactorAvailability,
    FactorRegistry,
)


class TestFactorRegistry:
    def test_available_factors_returns_all_when_after_all_dates(self):
        registry = FactorRegistry.default()
        factors = registry.available_factors(date(2026, 1, 1))
        # All factors should be available in 2026
        assert len(factors) > 10

    def test_available_factors_excludes_ml_before_2026(self):
        registry = FactorRegistry.default()
        factors = registry.available_factors(date(2020, 1, 1))
        factor_names = {f.name for f in factors}
        assert "ml_cluster_score" not in factor_names

    def test_available_factors_returns_subset_for_2006(self):
        registry = FactorRegistry.default()
        factors_2006 = registry.available_factors(date(2006, 6, 1))
        factors_2020 = registry.available_factors(date(2020, 6, 1))
        assert len(factors_2006) < len(factors_2020)

    def test_coverage_ratio(self):
        registry = FactorRegistry.default()
        ratio = registry.coverage_ratio(date(2006, 6, 1))
        assert 0.0 < ratio < 1.0
        ratio_2026 = registry.coverage_ratio(date(2026, 1, 1))
        assert ratio_2026 == 1.0

    def test_missing_factors(self):
        registry = FactorRegistry.default()
        missing = registry.missing_factors(date(2006, 6, 1))
        assert len(missing) > 0
        missing_names = {f.name for f in missing}
        assert "ml_cluster_score" in missing_names

    def test_custom_registry(self):
        entries = [
            FactorAvailability(name="test_factor", available_from=date(2010, 1, 1), category="quality"),
            FactorAvailability(name="old_factor", available_from=date(2005, 1, 1), category="value"),
        ]
        registry = FactorRegistry(entries)
        assert len(registry.available_factors(date(2008, 1, 1))) == 1
        assert len(registry.available_factors(date(2012, 1, 1))) == 2
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest engine/tests/backtesting/test_factor_registry.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Write minimal implementation**

```python
"""Factor availability registry for historical backtesting.

Declares which scoring factors have reliable data at which dates.
The replay orchestrator uses this to determine which factors to include
when scoring at each historical rebalance point.
"""

from __future__ import annotations

from datetime import date
from dataclasses import dataclass

from pydantic import BaseModel


class FactorAvailability(BaseModel):
    """A single factor's data availability window."""

    name: str
    available_from: date
    category: str  # "quality", "value", "momentum", "growth", "ml"
    notes: str = ""


class FactorRegistry:
    """Registry of factor data availability dates.

    Provides lookup methods for determining which factors can be
    computed at any given historical date.
    """

    def __init__(self, entries: list[FactorAvailability]) -> None:
        self._entries = sorted(entries, key=lambda e: e.available_from)

    @classmethod
    def default(cls) -> FactorRegistry:
        """Build the default registry with known factor availability dates."""
        return cls(_DEFAULT_ENTRIES[:])

    def available_factors(self, as_of: date) -> list[FactorAvailability]:
        """Return factors with reliable data at the given date."""
        return [e for e in self._entries if e.available_from <= as_of]

    def missing_factors(self, as_of: date) -> list[FactorAvailability]:
        """Return factors NOT yet available at the given date."""
        return [e for e in self._entries if e.available_from > as_of]

    def coverage_ratio(self, as_of: date) -> float:
        """Fraction of total factors available at the given date (0.0 to 1.0)."""
        if not self._entries:
            return 0.0
        available = len(self.available_factors(as_of))
        return available / len(self._entries)

    def all_factors(self) -> list[FactorAvailability]:
        """Return all registered factors regardless of date."""
        return list(self._entries)


# Default entries based on data source availability research.
# Dates represent the earliest reliable data for each factor.
_DEFAULT_ENTRIES = [
    # Quality factors — available from SEC EDGAR XBRL (~2005-2008)
    FactorAvailability(name="gross_profitability", available_from=date(2005, 1, 1), category="quality"),
    FactorAvailability(name="f_score", available_from=date(2005, 1, 1), category="quality"),
    FactorAvailability(name="accrual_ratio", available_from=date(2005, 1, 1), category="quality"),
    FactorAvailability(name="roic_wacc", available_from=date(2006, 1, 1), category="quality"),
    FactorAvailability(name="roic_trend", available_from=date(2006, 1, 1), category="quality"),
    FactorAvailability(name="roic_stability", available_from=date(2008, 1, 1), category="quality", notes="Needs 3yr history"),
    FactorAvailability(name="fcf_conversion", available_from=date(2005, 1, 1), category="quality"),
    FactorAvailability(name="capital_allocation", available_from=date(2006, 1, 1), category="quality"),
    # Value factors
    FactorAvailability(name="ev_fcf", available_from=date(2005, 1, 1), category="value"),
    FactorAvailability(name="ev_gross_profit", available_from=date(2005, 1, 1), category="value"),
    FactorAvailability(name="acquirers_multiple", available_from=date(2005, 1, 1), category="value"),
    FactorAvailability(name="reverse_dcf", available_from=date(2006, 1, 1), category="value"),
    FactorAvailability(name="owner_earnings", available_from=date(2006, 1, 1), category="value"),
    FactorAvailability(name="peg_ratio", available_from=date(2006, 1, 1), category="value"),
    # Momentum factors
    FactorAvailability(name="price_momentum", available_from=date(2005, 1, 1), category="momentum"),
    FactorAvailability(name="multi_horizon_momentum", available_from=date(2005, 1, 1), category="momentum"),
    FactorAvailability(name="earnings_revision", available_from=date(2010, 1, 1), category="momentum", notes="Analyst estimates data spotty before 2010"),
    FactorAvailability(name="sue", available_from=date(2008, 1, 1), category="momentum"),
    # Growth factors
    FactorAvailability(name="revenue_cagr", available_from=date(2008, 1, 1), category="growth", notes="Needs 3yr history"),
    FactorAvailability(name="operating_leverage", available_from=date(2008, 1, 1), category="growth"),
    FactorAvailability(name="rule_of_40", available_from=date(2008, 1, 1), category="growth"),
    # Specialized factors
    FactorAvailability(name="insider_activity", available_from=date(2010, 1, 1), category="quality", notes="SEC Form 4 data spotty before 2010"),
    FactorAvailability(name="institutional_accumulation", available_from=date(2010, 1, 1), category="quality", notes="13F data"),
    FactorAvailability(name="moat_durability", available_from=date(2010, 1, 1), category="quality", notes="Needs 5yr history"),
    # ML factors — only available from when the ML pipeline started
    FactorAvailability(name="ml_cluster_score", available_from=date(2026, 1, 1), category="ml", notes="Requires trained cluster model"),
    FactorAvailability(name="ml_vae_anomaly", available_from=date(2026, 1, 1), category="ml", notes="Requires trained VAE model"),
]
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest engine/tests/backtesting/test_factor_registry.py -v`
Expected: PASS (all 7 tests)

**Step 5: Commit**

```bash
git add engine/src/margin_engine/backtesting/factor_registry.py engine/tests/backtesting/test_factor_registry.py
git commit -m "feat(engine): add factor availability registry for historical backtesting"
```

---

### Task 2: Point-in-Time Data Provider Protocol

Define the protocol for point-in-time historical data access and build an in-memory implementation for testing. The real implementation (Sharadar/EDGAR) will be plugged in later — the protocol is the contract.

**Files:**
- Create: `engine/src/margin_engine/backtesting/pit_provider.py`
- Create: `engine/tests/backtesting/test_pit_provider.py`

**Step 1: Write the failing test**

```python
"""Tests for point-in-time data provider."""

from datetime import date

import pytest

from margin_engine.backtesting.pit_provider import (
    DelistingEvent,
    DelistingType,
    InMemoryPITProvider,
    PITSnapshot,
    PointInTimeProvider,
)
from margin_engine.models.financial import (
    AssetProfile,
    BalanceSheet,
    CashFlowStatement,
    FinancialPeriod,
    GICSSector,
    IncomeStatement,
    PriceBar,
)


def _make_profile(ticker: str, sector: GICSSector = GICSSector.TECHNOLOGY) -> AssetProfile:
    return AssetProfile(
        ticker=ticker,
        name=f"{ticker} Inc",
        sector=sector,
        sub_industry="Software",
        market_cap=50_000_000_000,
        avg_daily_volume=10_000_000,
        shares_outstanding=1_000_000_000,
    )


def _make_period() -> FinancialPeriod:
    income = IncomeStatement(
        revenue=10_000, cogs=4_000, gross_profit=6_000,
        sga=1_000, depreciation=500, ebit=4_500,
        interest_expense=200, tax_expense=1_000, net_income=3_300,
        shares_outstanding=1_000_000_000,
    )
    balance = BalanceSheet(
        total_assets=50_000, current_assets=20_000, cash=10_000,
        receivables=5_000, total_liabilities=20_000, current_liabilities=8_000,
        long_term_debt=10_000, total_equity=30_000,
        retained_earnings=15_000, shares_outstanding=1_000_000_000,
    )
    cash_flow = CashFlowStatement(
        operating_cash_flow=5_000, capital_expenditures=-1_000,
    )
    return FinancialPeriod(
        period_end=date(2008, 12, 31),
        current=income,
        current_balance=balance,
        current_cash_flow=cash_flow,
        prior=income,
        prior_balance=balance,
        prior_cash_flow=cash_flow,
    )


class TestInMemoryPITProvider:
    def test_get_universe_returns_known_tickers(self):
        provider = InMemoryPITProvider()
        provider.add_snapshot(date(2008, 3, 1), "AAPL", _make_profile("AAPL"), _make_period(), 150.0)
        provider.add_snapshot(date(2008, 3, 1), "MSFT", _make_profile("MSFT"), _make_period(), 28.0)

        universe = provider.get_universe(date(2008, 3, 1))
        assert len(universe) == 2
        tickers = {s.ticker for s in universe}
        assert tickers == {"AAPL", "MSFT"}

    def test_get_universe_excludes_delisted(self):
        provider = InMemoryPITProvider()
        provider.add_snapshot(date(2008, 3, 1), "AAPL", _make_profile("AAPL"), _make_period(), 150.0)
        provider.add_snapshot(date(2008, 3, 1), "LEH", _make_profile("LEH"), _make_period(), 40.0)
        provider.add_delisting("LEH", DelistingEvent(
            ticker="LEH", delist_date=date(2008, 9, 15),
            delist_type=DelistingType.BANKRUPTCY, last_price=0.20,
        ))

        # Before delisting: both present
        universe_before = provider.get_universe(date(2008, 3, 1))
        assert len(universe_before) == 2

        # After delisting: LEH excluded
        universe_after = provider.get_universe(date(2008, 10, 1))
        assert len(universe_after) == 1
        assert universe_after[0].ticker == "AAPL"

    def test_get_snapshot_returns_pit_data(self):
        provider = InMemoryPITProvider()
        profile = _make_profile("AAPL")
        period = _make_period()
        provider.add_snapshot(date(2008, 3, 1), "AAPL", profile, period, 150.0)

        snapshot = provider.get_snapshot("AAPL", date(2008, 3, 1))
        assert snapshot is not None
        assert snapshot.ticker == "AAPL"
        assert snapshot.price == 150.0
        assert snapshot.profile.sector == GICSSector.TECHNOLOGY

    def test_get_snapshot_returns_none_for_unknown(self):
        provider = InMemoryPITProvider()
        assert provider.get_snapshot("FAKE", date(2008, 3, 1)) is None

    def test_delisting_bankruptcy_returns_zero_value(self):
        provider = InMemoryPITProvider()
        provider.add_delisting("LEH", DelistingEvent(
            ticker="LEH", delist_date=date(2008, 9, 15),
            delist_type=DelistingType.BANKRUPTCY, last_price=0.20,
        ))
        event = provider.get_delisting("LEH")
        assert event is not None
        assert event.delist_type == DelistingType.BANKRUPTCY
        assert event.settlement_value == 0.0

    def test_delisting_acquisition_returns_acquisition_price(self):
        provider = InMemoryPITProvider()
        provider.add_delisting("ATVI", DelistingEvent(
            ticker="ATVI", delist_date=date(2023, 10, 13),
            delist_type=DelistingType.ACQUISITION, last_price=95.0,
            acquisition_price=95.0,
        ))
        event = provider.get_delisting("ATVI")
        assert event is not None
        assert event.settlement_value == 95.0

    def test_implements_protocol(self):
        provider = InMemoryPITProvider()
        assert isinstance(provider, PointInTimeProvider)
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest engine/tests/backtesting/test_pit_provider.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Write minimal implementation**

```python
"""Point-in-time data provider for historical backtesting.

Defines the protocol for accessing historical market data as it was known
at any given date, and provides an in-memory implementation for testing.
"""

from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Protocol, runtime_checkable

from pydantic import BaseModel

from margin_engine.models.financial import AssetProfile, FinancialPeriod, PriceBar


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
        """Return all snapshots at the given date, excluding delisted stocks."""
        snapshots = []
        for (snap_date, ticker), snapshot in self._snapshots.items():
            if snap_date != as_of_date:
                continue
            delisting = self._delistings.get(ticker)
            if delisting and delisting.delist_date <= as_of_date:
                continue
            snapshots.append(snapshot)
        return snapshots

    def get_snapshot(self, ticker: str, as_of_date: date) -> PITSnapshot | None:
        """Return snapshot for a specific ticker at the given date."""
        return self._snapshots.get((as_of_date, ticker))

    def get_price(self, ticker: str, as_of_date: date) -> float | None:
        """Return price for a ticker at the given date."""
        snapshot = self.get_snapshot(ticker, as_of_date)
        return snapshot.price if snapshot else None

    def get_delisting(self, ticker: str) -> DelistingEvent | None:
        """Return delisting event for a ticker."""
        return self._delistings.get(ticker)
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest engine/tests/backtesting/test_pit_provider.py -v`
Expected: PASS (all 7 tests)

**Step 5: Commit**

```bash
git add engine/src/margin_engine/backtesting/pit_provider.py engine/tests/backtesting/test_pit_provider.py
git commit -m "feat(engine): add point-in-time data provider protocol and in-memory implementation"
```

---

### Task 3: Historical Regime Classifier

Classifies any historical date into a market regime (Bull, Bear, Sideways, Crisis) using S&P 500 drawdown thresholds and VIX levels. Used for regime-segmented performance in the UI.

**Files:**
- Create: `engine/src/margin_engine/backtesting/regime_classifier.py`
- Create: `engine/tests/backtesting/test_regime_classifier.py`

**Step 1: Write the failing test**

```python
"""Tests for historical regime classifier."""

from datetime import date

import pytest

from margin_engine.backtesting.regime_classifier import (
    MarketRegimeHistorical,
    RegimePeriod,
    classify_regime,
    get_nber_recessions,
    segment_by_regime,
)


class TestClassifyRegime:
    def test_bull_when_above_trough(self):
        regime = classify_regime(drawdown_from_peak=0.05, vix=15.0, in_nber_recession=False)
        assert regime == MarketRegimeHistorical.BULL

    def test_bear_when_deep_drawdown(self):
        regime = classify_regime(drawdown_from_peak=0.25, vix=25.0, in_nber_recession=False)
        assert regime == MarketRegimeHistorical.BEAR

    def test_crisis_when_vix_high_and_drawdown(self):
        regime = classify_regime(drawdown_from_peak=0.30, vix=45.0, in_nber_recession=True)
        assert regime == MarketRegimeHistorical.CRISIS

    def test_sideways_moderate_drawdown(self):
        regime = classify_regime(drawdown_from_peak=0.12, vix=18.0, in_nber_recession=False)
        assert regime == MarketRegimeHistorical.SIDEWAYS

    def test_crisis_takes_priority_over_bear(self):
        regime = classify_regime(drawdown_from_peak=0.35, vix=50.0, in_nber_recession=True)
        assert regime == MarketRegimeHistorical.CRISIS


class TestSegmentByRegime:
    def test_segments_returns_by_regime(self):
        dates = [date(2008, 1, 1), date(2008, 6, 1), date(2009, 3, 1), date(2010, 1, 1)]
        regimes = [
            MarketRegimeHistorical.BULL,
            MarketRegimeHistorical.CRISIS,
            MarketRegimeHistorical.CRISIS,
            MarketRegimeHistorical.BULL,
        ]
        portfolio_returns = [0.02, -0.15, -0.08, 0.05]
        benchmark_returns = [0.01, -0.10, -0.05, 0.03]

        segments = segment_by_regime(dates, regimes, portfolio_returns, benchmark_returns)
        assert MarketRegimeHistorical.CRISIS in segments
        assert MarketRegimeHistorical.BULL in segments
        crisis = segments[MarketRegimeHistorical.CRISIS]
        assert crisis.num_months == 2
        assert len(crisis.portfolio_returns) == 2

    def test_empty_input_returns_empty(self):
        segments = segment_by_regime([], [], [], [])
        assert len(segments) == 0


class TestNBERRecessions:
    def test_gfc_is_recession(self):
        recessions = get_nber_recessions()
        # Dec 2007 - Jun 2009
        gfc = [r for r in recessions if r[0].year == 2007]
        assert len(gfc) == 1
        assert gfc[0][0] == date(2007, 12, 1)
        assert gfc[0][1] == date(2009, 6, 30)

    def test_date_in_recession(self):
        recessions = get_nber_recessions()
        # March 2009 should be in GFC recession
        in_recession = any(start <= date(2009, 3, 1) <= end for start, end in recessions)
        assert in_recession
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest engine/tests/backtesting/test_regime_classifier.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Write minimal implementation**

```python
"""Historical market regime classifier.

Classifies dates into Bull, Bear, Sideways, or Crisis using S&P 500
drawdown thresholds, VIX levels, and NBER recession dates.
"""

from __future__ import annotations

from datetime import date
from enum import StrEnum

from pydantic import BaseModel


class MarketRegimeHistorical(StrEnum):
    """Market regime classification for backtesting."""

    BULL = "bull"
    BEAR = "bear"
    SIDEWAYS = "sideways"
    CRISIS = "crisis"


class RegimeSegment(BaseModel):
    """Aggregated performance within a single regime."""

    regime: MarketRegimeHistorical
    num_months: int
    portfolio_returns: list[float]
    benchmark_returns: list[float]

    @property
    def total_portfolio_return(self) -> float:
        import math
        return math.prod(1.0 + r for r in self.portfolio_returns) - 1.0

    @property
    def total_benchmark_return(self) -> float:
        import math
        return math.prod(1.0 + r for r in self.benchmark_returns) - 1.0

    @property
    def max_drawdown(self) -> float:
        if not self.portfolio_returns:
            return 0.0
        peak = 1.0
        value = 1.0
        max_dd = 0.0
        for r in self.portfolio_returns:
            value *= (1.0 + r)
            if value > peak:
                peak = value
            dd = (peak - value) / peak if peak > 0 else 0.0
            if dd > max_dd:
                max_dd = dd
        return max_dd


class RegimePeriod(BaseModel):
    """A time-stamped regime classification."""

    as_of_date: date
    regime: MarketRegimeHistorical
    drawdown_from_peak: float
    vix: float | None = None


def classify_regime(
    drawdown_from_peak: float,
    vix: float | None = None,
    in_nber_recession: bool = False,
) -> MarketRegimeHistorical:
    """Classify a market regime from drawdown and VIX.

    Thresholds:
    - Crisis: drawdown > 20% AND (VIX > 30 OR NBER recession)
    - Bear: drawdown > 20%
    - Sideways: drawdown 10-20%
    - Bull: drawdown < 10%
    """
    vix_val = vix or 0.0

    if drawdown_from_peak > 0.20 and (vix_val > 30.0 or in_nber_recession):
        return MarketRegimeHistorical.CRISIS
    if drawdown_from_peak > 0.20:
        return MarketRegimeHistorical.BEAR
    if drawdown_from_peak > 0.10:
        return MarketRegimeHistorical.SIDEWAYS
    return MarketRegimeHistorical.BULL


def get_nber_recessions() -> list[tuple[date, date]]:
    """Return NBER recession date ranges (start, end).

    Source: National Bureau of Economic Research.
    Covers recessions relevant to 2005-2025 backtesting window.
    """
    return [
        (date(2007, 12, 1), date(2009, 6, 30)),   # Great Financial Crisis
        (date(2020, 2, 1), date(2020, 4, 30)),     # COVID-19
    ]


def is_in_recession(as_of: date) -> bool:
    """Check if a date falls within an NBER recession."""
    return any(start <= as_of <= end for start, end in get_nber_recessions())


def segment_by_regime(
    dates: list[date],
    regimes: list[MarketRegimeHistorical],
    portfolio_returns: list[float],
    benchmark_returns: list[float],
) -> dict[MarketRegimeHistorical, RegimeSegment]:
    """Group returns by regime for segmented analysis."""
    buckets: dict[MarketRegimeHistorical, dict] = {}

    for d, regime, pr, br in zip(dates, regimes, portfolio_returns, benchmark_returns):
        if regime not in buckets:
            buckets[regime] = {"portfolio_returns": [], "benchmark_returns": []}
        buckets[regime]["portfolio_returns"].append(pr)
        buckets[regime]["benchmark_returns"].append(br)

    return {
        regime: RegimeSegment(
            regime=regime,
            num_months=len(data["portfolio_returns"]),
            portfolio_returns=data["portfolio_returns"],
            benchmark_returns=data["benchmark_returns"],
        )
        for regime, data in buckets.items()
    }
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest engine/tests/backtesting/test_regime_classifier.py -v`
Expected: PASS (all 7 tests)

**Step 5: Commit**

```bash
git add engine/src/margin_engine/backtesting/regime_classifier.py engine/tests/backtesting/test_regime_classifier.py
git commit -m "feat(engine): add historical market regime classifier with NBER recession dates"
```

---

### Task 4: Shadow Portfolio Engine Models

Pure engine module for tracking a live paper portfolio. Records positions daily with immutable timestamps. Independent of the replay engine.

**Files:**
- Create: `engine/src/margin_engine/backtesting/shadow_portfolio.py`
- Create: `engine/tests/backtesting/test_shadow_portfolio.py`

**Step 1: Write the failing test**

```python
"""Tests for shadow portfolio tracker."""

from datetime import UTC, date, datetime

import pytest

from margin_engine.backtesting.shadow_portfolio import (
    ShadowPortfolio,
    ShadowPosition,
    ShadowSnapshot,
)


class TestShadowPortfolio:
    def test_record_snapshot(self):
        portfolio = ShadowPortfolio(start_date=date(2026, 2, 24))
        positions = [
            ShadowPosition(ticker="AAPL", weight=0.5, price=175.0, composite_score=82.0),
            ShadowPosition(ticker="MSFT", weight=0.5, price=410.0, composite_score=78.0),
        ]
        portfolio.record_snapshot(date(2026, 2, 24), positions, portfolio_value=1_000_000.0)
        assert len(portfolio.snapshots) == 1
        assert portfolio.snapshots[0].num_positions == 2

    def test_cannot_backfill(self):
        portfolio = ShadowPortfolio(start_date=date(2026, 2, 24))
        positions = [ShadowPosition(ticker="AAPL", weight=1.0, price=175.0, composite_score=82.0)]
        portfolio.record_snapshot(date(2026, 2, 25), positions, portfolio_value=1_000_000.0)

        with pytest.raises(ValueError, match="Cannot backfill"):
            portfolio.record_snapshot(date(2026, 2, 24), positions, portfolio_value=999_000.0)

    def test_performance_calculation(self):
        portfolio = ShadowPortfolio(start_date=date(2026, 2, 24))
        positions = [ShadowPosition(ticker="AAPL", weight=1.0, price=175.0, composite_score=82.0)]
        portfolio.record_snapshot(date(2026, 2, 24), positions, portfolio_value=1_000_000.0)
        portfolio.record_snapshot(date(2026, 2, 25), positions, portfolio_value=1_010_000.0)
        portfolio.record_snapshot(date(2026, 2, 26), positions, portfolio_value=1_005_000.0)

        assert portfolio.total_return == pytest.approx(0.005, abs=1e-6)
        assert portfolio.max_drawdown == pytest.approx(0.00495, abs=1e-4)
        assert portfolio.num_days == 3

    def test_empty_portfolio_zero_return(self):
        portfolio = ShadowPortfolio(start_date=date(2026, 2, 24))
        assert portfolio.total_return == 0.0
        assert portfolio.max_drawdown == 0.0
        assert portfolio.num_days == 0
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest engine/tests/backtesting/test_shadow_portfolio.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Write minimal implementation**

```python
"""Shadow portfolio tracker for live out-of-sample tracking.

Records paper positions daily with immutable timestamps.
Cannot be edited or backfilled — provably forward-looking.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

from pydantic import BaseModel, Field


class ShadowPosition(BaseModel):
    """A single position in the shadow portfolio."""

    ticker: str
    weight: float
    price: float
    composite_score: float


class ShadowSnapshot(BaseModel):
    """Daily shadow portfolio state."""

    as_of_date: date
    positions: list[ShadowPosition]
    portfolio_value: float
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @property
    def num_positions(self) -> int:
        return len(self.positions)


class ShadowPortfolio:
    """Tracks a live paper portfolio with immutable history.

    Key invariant: snapshots can only be appended in chronological order.
    No backdating, no editing, no deletion.
    """

    def __init__(self, start_date: date) -> None:
        self.start_date = start_date
        self.snapshots: list[ShadowSnapshot] = []

    def record_snapshot(
        self,
        as_of_date: date,
        positions: list[ShadowPosition],
        portfolio_value: float,
    ) -> ShadowSnapshot:
        """Record today's portfolio state. Cannot backfill."""
        if self.snapshots and as_of_date <= self.snapshots[-1].as_of_date:
            raise ValueError(
                f"Cannot backfill: {as_of_date} <= last snapshot "
                f"{self.snapshots[-1].as_of_date}"
            )
        snapshot = ShadowSnapshot(
            as_of_date=as_of_date,
            positions=positions,
            portfolio_value=portfolio_value,
        )
        self.snapshots.append(snapshot)
        return snapshot

    @property
    def total_return(self) -> float:
        """Cumulative return since inception."""
        if len(self.snapshots) < 2:
            return 0.0
        initial = self.snapshots[0].portfolio_value
        final = self.snapshots[-1].portfolio_value
        if initial <= 0:
            return 0.0
        return (final - initial) / initial

    @property
    def max_drawdown(self) -> float:
        """Maximum drawdown from peak."""
        if len(self.snapshots) < 2:
            return 0.0
        values = [s.portfolio_value for s in self.snapshots]
        peak = values[0]
        max_dd = 0.0
        for v in values:
            if v > peak:
                peak = v
            dd = (peak - v) / peak if peak > 0 else 0.0
            if dd > max_dd:
                max_dd = dd
        return max_dd

    @property
    def num_days(self) -> int:
        """Number of recorded trading days."""
        return len(self.snapshots)
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest engine/tests/backtesting/test_shadow_portfolio.py -v`
Expected: PASS (all 4 tests)

**Step 5: Commit**

```bash
git add engine/src/margin_engine/backtesting/shadow_portfolio.py engine/tests/backtesting/test_shadow_portfolio.py
git commit -m "feat(engine): add shadow portfolio tracker with immutable append-only history"
```

---

### Task 5: Replay Orchestrator

The core engine. Wraps `WalkForwardSimulator` with point-in-time data, factor availability, and regime classification. Produces a `ReplayResult` with regime-segmented metrics, factor coverage timeline, and per-rebalance audit records.

**Files:**
- Create: `engine/src/margin_engine/backtesting/replay_orchestrator.py`
- Create: `engine/tests/backtesting/test_replay_orchestrator.py`
- Modify: `engine/src/margin_engine/backtesting/__init__.py` (add exports)

**Step 1: Write the failing test**

```python
"""Tests for replay orchestrator."""

from datetime import date

import pytest

from margin_engine.backtesting.factor_registry import FactorRegistry
from margin_engine.backtesting.pit_provider import (
    InMemoryPITProvider,
    PITSnapshot,
)
from margin_engine.backtesting.regime_classifier import MarketRegimeHistorical
from margin_engine.backtesting.replay_orchestrator import (
    RebalanceAuditRecord,
    ReplayConfig,
    ReplayOrchestrator,
    ReplayResult,
)
from margin_engine.models.financial import (
    AssetProfile,
    BalanceSheet,
    CashFlowStatement,
    FinancialPeriod,
    GICSSector,
    IncomeStatement,
)


def _make_profile(ticker: str, sector: GICSSector = GICSSector.TECHNOLOGY) -> AssetProfile:
    return AssetProfile(
        ticker=ticker, name=f"{ticker} Inc", sector=sector,
        sub_industry="Software", market_cap=50_000_000_000,
        avg_daily_volume=10_000_000, shares_outstanding=1_000_000_000,
    )


def _make_period(period_end: date = date(2008, 12, 31)) -> FinancialPeriod:
    income = IncomeStatement(
        revenue=10_000, cogs=4_000, gross_profit=6_000,
        sga=1_000, depreciation=500, ebit=4_500,
        interest_expense=200, tax_expense=1_000, net_income=3_300,
        shares_outstanding=1_000_000_000,
    )
    balance = BalanceSheet(
        total_assets=50_000, current_assets=20_000, cash=10_000,
        receivables=5_000, total_liabilities=20_000, current_liabilities=8_000,
        long_term_debt=10_000, total_equity=30_000,
        retained_earnings=15_000, shares_outstanding=1_000_000_000,
    )
    cash_flow = CashFlowStatement(
        operating_cash_flow=5_000, capital_expenditures=-1_000,
    )
    return FinancialPeriod(
        period_end=period_end,
        current=income, current_balance=balance, current_cash_flow=cash_flow,
        prior=income, prior_balance=balance, prior_cash_flow=cash_flow,
    )


def _build_provider_with_data(months: int = 6) -> InMemoryPITProvider:
    """Build a provider with AAPL and MSFT data for N months starting 2020-01."""
    provider = InMemoryPITProvider()
    base_prices = {"AAPL": 300.0, "MSFT": 170.0}

    for i in range(months):
        month = 1 + i
        year = 2020 + (month - 1) // 12
        m = ((month - 1) % 12) + 1
        rebal_date = date(year, m, 1)
        # Simulate gentle uptrend
        for ticker, base in base_prices.items():
            price = base * (1 + 0.01 * i)
            provider.add_snapshot(
                rebal_date, ticker,
                _make_profile(ticker),
                _make_period(period_end=rebal_date),
                price,
            )
    return provider


class TestReplayOrchestrator:
    def test_run_produces_result(self):
        provider = _build_provider_with_data(months=6)
        config = ReplayConfig(
            start_date=date(2020, 1, 1),
            end_date=date(2020, 6, 1),
            rebalance_frequency="monthly",
        )
        orchestrator = ReplayOrchestrator(
            config=config,
            pit_provider=provider,
            factor_registry=FactorRegistry.default(),
        )
        result = orchestrator.run()
        assert isinstance(result, ReplayResult)
        assert result.metrics is not None
        assert len(result.audit_log) > 0

    def test_audit_log_has_correct_fields(self):
        provider = _build_provider_with_data(months=3)
        config = ReplayConfig(
            start_date=date(2020, 1, 1),
            end_date=date(2020, 3, 1),
            rebalance_frequency="monthly",
        )
        orchestrator = ReplayOrchestrator(
            config=config,
            pit_provider=provider,
            factor_registry=FactorRegistry.default(),
        )
        result = orchestrator.run()
        record = result.audit_log[0]
        assert isinstance(record, RebalanceAuditRecord)
        assert record.universe_size >= 2
        assert record.factor_coverage > 0.0

    def test_regime_segments_populated(self):
        provider = _build_provider_with_data(months=6)
        config = ReplayConfig(
            start_date=date(2020, 1, 1),
            end_date=date(2020, 6, 1),
            rebalance_frequency="monthly",
        )
        orchestrator = ReplayOrchestrator(
            config=config,
            pit_provider=provider,
            factor_registry=FactorRegistry.default(),
        )
        result = orchestrator.run()
        # Should have at least one regime segment
        assert len(result.regime_segments) > 0

    def test_factor_timeline_populated(self):
        provider = _build_provider_with_data(months=3)
        config = ReplayConfig(
            start_date=date(2020, 1, 1),
            end_date=date(2020, 3, 1),
            rebalance_frequency="monthly",
        )
        orchestrator = ReplayOrchestrator(
            config=config,
            pit_provider=provider,
            factor_registry=FactorRegistry.default(),
        )
        result = orchestrator.run()
        assert len(result.factor_timeline) > 0
        entry = result.factor_timeline[0]
        assert "available" in entry
        assert "missing" in entry
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest engine/tests/backtesting/test_replay_orchestrator.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Write minimal implementation**

The replay orchestrator is the largest single component. It:
1. Generates rebalance dates
2. At each date, loads PIT universe from the provider
3. Runs elimination filters (from `margin_engine.scoring.filters.pipeline`)
4. Scores survivors using available factors
5. Selects holdings (top percentile or conviction-based)
6. Tracks portfolio value with transaction costs
7. Classifies each period's regime
8. Records audit metadata per rebalance

```python
"""Replay orchestrator for historical backtesting.

Replays the actual margin_engine elimination and scoring pipeline against
point-in-time historical data. Produces regime-segmented metrics, a factor
coverage timeline, and per-rebalance audit records.
"""

from __future__ import annotations

import logging
import math
import time
from datetime import date

from pydantic import BaseModel, Field

from margin_engine.backtesting.factor_registry import FactorRegistry
from margin_engine.backtesting.metrics import PerformanceCalculator
from margin_engine.backtesting.models import (
    HoldingRecord,
    MonthlySnapshot,
    PerformanceMetrics,
)
from margin_engine.backtesting.pit_provider import PointInTimeProvider
from margin_engine.backtesting.regime_classifier import (
    MarketRegimeHistorical,
    RegimeSegment,
    classify_regime,
    is_in_recession,
    segment_by_regime,
)
from margin_engine.scoring.filters.pipeline import run_elimination_filters

logger = logging.getLogger(__name__)

STARTING_CAPITAL = 1_000_000.0


class ReplayConfig(BaseModel):
    """Configuration for a replay backtest."""

    start_date: date = Field(default=date(2006, 1, 1))
    end_date: date = Field(default_factory=date.today)
    rebalance_frequency: str = "monthly"  # monthly, quarterly, semi_annual
    conviction_threshold: float = 0.10  # top N% by score
    weighting: str = "equal"  # equal or conviction
    sector_exclusions: list[str] = Field(default_factory=list)  # max 2
    transaction_cost_bps: float = 20.0
    benchmark_ticker: str = "SPY"


class RebalanceAuditRecord(BaseModel):
    """Audit trail for a single rebalance event."""

    rebalance_date: date
    universe_size: int
    eliminated_count: int
    survivor_count: int
    selected_count: int
    top_holdings: list[dict]  # [{ticker, score, price}]
    notable_events: list[str]  # e.g. "LEH eliminated — insufficient earnings quality"
    factor_coverage: float  # 0.0-1.0
    available_factors: list[str]
    missing_factors: list[str]
    regime: MarketRegimeHistorical


class FactorTimelineEntry(BaseModel):
    """Factor availability at a point in time."""

    as_of_date: date
    available: list[str]
    missing: list[str]
    coverage_ratio: float


class ReplayResult(BaseModel):
    """Complete output of a replay backtest."""

    config: ReplayConfig
    metrics: PerformanceMetrics
    snapshots: list[MonthlySnapshot]
    audit_log: list[RebalanceAuditRecord]
    regime_segments: dict[str, RegimeSegment]
    factor_timeline: list[FactorTimelineEntry]
    duration_seconds: float


class ReplayOrchestrator:
    """Replays the margin_engine pipeline against historical data.

    At each rebalance date:
    1. Load PIT universe from provider
    2. Run elimination filters (same code as live)
    3. Score survivors by composite score (simplified — uses available factors)
    4. Select top holdings by conviction threshold
    5. Track portfolio value with transaction costs
    6. Classify regime and record audit trail
    """

    def __init__(
        self,
        config: ReplayConfig,
        pit_provider: PointInTimeProvider,
        factor_registry: FactorRegistry,
        benchmark_prices: dict[date, float] | None = None,
    ) -> None:
        self._config = config
        self._provider = pit_provider
        self._registry = factor_registry
        self._benchmark_prices = benchmark_prices or {}
        self._calculator = PerformanceCalculator()

    def run(self) -> ReplayResult:
        """Execute the replay and return results."""
        start_time = time.monotonic()

        rebalance_dates = self._generate_rebalance_dates()
        if not rebalance_dates:
            return self._empty_result(time.monotonic() - start_time)

        snapshots: list[MonthlySnapshot] = []
        audit_log: list[RebalanceAuditRecord] = []
        factor_timeline: list[FactorTimelineEntry] = []
        regime_dates: list[date] = []
        regime_labels: list[MarketRegimeHistorical] = []
        portfolio_returns_list: list[float] = []
        benchmark_returns_list: list[float] = []

        portfolio_value = STARTING_CAPITAL
        benchmark_value = STARTING_CAPITAL
        prev_holdings: list[HoldingRecord] = []
        initial_benchmark_price: float | None = None
        prev_drawdown = 0.0

        for i, rebal_date in enumerate(rebalance_dates):
            # 1. Load PIT universe
            universe = self._provider.get_universe(rebal_date)
            if not universe:
                continue

            # 2. Factor availability at this date
            available = self._registry.available_factors(rebal_date)
            missing = self._registry.missing_factors(rebal_date)
            coverage = self._registry.coverage_ratio(rebal_date)

            factor_timeline.append(FactorTimelineEntry(
                as_of_date=rebal_date,
                available=[f.name for f in available],
                missing=[f.name for f in missing],
                coverage_ratio=coverage,
            ))

            # 3. Run elimination filters on each ticker
            survivors = []
            eliminated_count = 0
            notable_events: list[str] = []

            for snapshot in universe:
                try:
                    filter_result = run_elimination_filters(
                        period=snapshot.period,
                        profile=snapshot.profile,
                    )
                    if filter_result.passed:
                        survivors.append(snapshot)
                    else:
                        eliminated_count += 1
                        failed = [f.name for f in filter_result.failed_filters]
                        notable_events.append(
                            f"{snapshot.ticker} eliminated — {', '.join(failed)}"
                        )
                except Exception:
                    logger.warning("Filter error for %s on %s", snapshot.ticker, rebal_date)
                    eliminated_count += 1

            # 4. Score survivors (use price as proxy score for now — real scoring
            #    requires full factor computation which needs the data provider
            #    to supply enough history). In production, this will call the
            #    actual scoring pipeline with available factors.
            scored = []
            for s in survivors:
                # Simple composite: use a deterministic score based on available financials
                score = self._compute_simple_score(s)
                scored.append((s, score))

            scored.sort(key=lambda x: -x[1])

            # 5. Select top holdings
            n_select = max(1, math.ceil(len(scored) * self._config.conviction_threshold))
            selected = scored[:n_select]

            if self._config.weighting == "equal" and selected:
                weight = 1.0 / len(selected)
            else:
                weight = 1.0

            new_holdings = [
                HoldingRecord(
                    ticker=s.ticker,
                    weight=weight if self._config.weighting == "equal" else weight,
                    entry_price=s.price,
                    composite_score=score,
                )
                for s, score in selected
            ]

            # 6. Calculate portfolio value change
            if i > 0 and prev_holdings:
                total_return = 0.0
                for h in prev_holdings:
                    current_price = self._provider.get_price(h.ticker, rebal_date)
                    if current_price and h.entry_price > 0:
                        stock_return = (current_price / h.entry_price) - 1.0
                        total_return += h.weight * stock_return
                portfolio_value *= (1.0 + total_return)

            # 7. Transaction costs
            turnover = self._calculate_turnover(prev_holdings, new_holdings)
            cost = portfolio_value * (turnover * self._config.transaction_cost_bps / 10_000)
            portfolio_value -= cost

            # 8. Benchmark tracking
            benchmark_price = self._benchmark_prices.get(rebal_date, 100.0 * (1.0 + 0.005 * i))
            if initial_benchmark_price is None:
                initial_benchmark_price = benchmark_price
            if initial_benchmark_price > 0:
                benchmark_value = STARTING_CAPITAL * benchmark_price / initial_benchmark_price

            # 9. Returns
            if i == 0:
                port_return = 0.0
                bench_return = 0.0
            else:
                prev_pv = snapshots[-1].portfolio_value
                prev_bv = snapshots[-1].benchmark_value
                port_return = (portfolio_value - prev_pv) / prev_pv if prev_pv > 0 else 0.0
                bench_return = (benchmark_value - prev_bv) / prev_bv if prev_bv > 0 else 0.0

            # 10. Regime classification
            if portfolio_value < STARTING_CAPITAL:
                drawdown = (STARTING_CAPITAL - portfolio_value) / STARTING_CAPITAL
            else:
                drawdown = 0.0
            # Use benchmark drawdown for regime (market-level, not portfolio-level)
            bench_drawdown = max(0, (STARTING_CAPITAL - benchmark_value) / STARTING_CAPITAL)
            regime = classify_regime(
                drawdown_from_peak=bench_drawdown,
                in_nber_recession=is_in_recession(rebal_date),
            )

            snapshot = MonthlySnapshot(
                date=rebal_date,
                holdings=new_holdings,
                portfolio_value=portfolio_value,
                benchmark_value=benchmark_value,
                portfolio_return=port_return,
                benchmark_return=bench_return,
                turnover=turnover,
                transaction_costs=cost,
            )
            snapshots.append(snapshot)

            regime_dates.append(rebal_date)
            regime_labels.append(regime)
            portfolio_returns_list.append(port_return)
            benchmark_returns_list.append(bench_return)

            # Audit record
            top_holdings = [
                {"ticker": s.ticker, "score": round(score, 2), "price": s.price}
                for s, score in selected[:10]
            ]
            audit_log.append(RebalanceAuditRecord(
                rebalance_date=rebal_date,
                universe_size=len(universe),
                eliminated_count=eliminated_count,
                survivor_count=len(survivors),
                selected_count=len(selected),
                top_holdings=top_holdings,
                notable_events=notable_events[:5],
                factor_coverage=coverage,
                available_factors=[f.name for f in available],
                missing_factors=[f.name for f in missing],
                regime=regime,
            ))

            prev_holdings = new_holdings

        # Compute aggregate metrics
        metrics = self._calculator.calculate(snapshots)

        # Segment by regime
        regime_segments = segment_by_regime(
            regime_dates, regime_labels,
            portfolio_returns_list, benchmark_returns_list,
        )

        duration = time.monotonic() - start_time
        return ReplayResult(
            config=self._config,
            metrics=metrics,
            snapshots=snapshots,
            audit_log=audit_log,
            regime_segments={k.value: v for k, v in regime_segments.items()},
            factor_timeline=factor_timeline,
            duration_seconds=duration,
        )

    def _compute_simple_score(self, snapshot) -> float:
        """Compute a simplified composite score from available financials.

        In the full implementation, this calls the actual scoring pipeline
        with the factor registry determining which factors to use.
        """
        period = snapshot.period
        score = 50.0  # baseline

        # Quality signal: gross margin
        if period.current and period.current.gross_profit and period.current.revenue:
            gm = period.current.gross_profit / period.current.revenue
            score += gm * 20  # higher margin = better

        # Value signal: earnings yield
        if (period.current and period.current.net_income
                and snapshot.profile.market_cap and snapshot.profile.market_cap > 0):
            ey = period.current.net_income / (snapshot.profile.market_cap / 1e6)
            score += min(ey * 100, 20)  # cap contribution

        return min(max(score, 0), 100)

    def _generate_rebalance_dates(self) -> list[date]:
        """Generate rebalance dates from start to end."""
        dates: list[date] = []
        step = {"monthly": 1, "quarterly": 3, "semi_annual": 6}.get(
            self._config.rebalance_frequency, 1
        )
        current = date(self._config.start_date.year, self._config.start_date.month, 1)

        while current <= self._config.end_date:
            # First business day
            d = current
            while d.weekday() >= 5:
                d = d.replace(day=d.day + 1)
            if self._config.start_date <= d <= self._config.end_date:
                dates.append(d)

            month = current.month + step
            year = current.year
            while month > 12:
                month -= 12
                year += 1
            current = date(year, month, 1)

        return dates

    @staticmethod
    def _calculate_turnover(
        old_holdings: list[HoldingRecord],
        new_holdings: list[HoldingRecord],
    ) -> float:
        """Calculate fraction of portfolio that changed."""
        old_tickers = {h.ticker for h in old_holdings}
        new_tickers = {h.ticker for h in new_holdings}
        if not old_tickers and not new_tickers:
            return 0.0
        changed = old_tickers.symmetric_difference(new_tickers)
        denominator = max(len(old_tickers), len(new_tickers), 1)
        return min(len(changed) / denominator, 1.0)

    def _empty_result(self, duration: float) -> ReplayResult:
        """Return empty result when no rebalance dates exist."""
        return ReplayResult(
            config=self._config,
            metrics=PerformanceMetrics(
                cagr=0, excess_cagr=0, sharpe_ratio=0, sortino_ratio=0,
                max_drawdown=0, win_rate=0, information_ratio=0,
                total_return=0, benchmark_total_return=0, num_months=0, avg_turnover=0,
            ),
            snapshots=[],
            audit_log=[],
            regime_segments={},
            factor_timeline=[],
            duration_seconds=duration,
        )
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest engine/tests/backtesting/test_replay_orchestrator.py -v`
Expected: PASS (all 4 tests)

**Step 5: Commit**

```bash
git add engine/src/margin_engine/backtesting/replay_orchestrator.py engine/tests/backtesting/test_replay_orchestrator.py
git commit -m "feat(engine): add replay orchestrator for point-in-time backtesting with regime segmentation"
```

---

### Task 6: Failure Audit Computation

Identifies the 10 worst rebalance periods by relative underperformance. Explains what the model held, what it missed, and which factors drove the bad selections.

**Files:**
- Create: `engine/src/margin_engine/backtesting/failure_audit.py`
- Create: `engine/tests/backtesting/test_failure_audit.py`

**Step 1: Write the failing test**

```python
"""Tests for failure audit computation."""

from datetime import date

import pytest

from margin_engine.backtesting.failure_audit import (
    FailurePeriod,
    compute_failure_audit,
)
from margin_engine.backtesting.models import HoldingRecord, MonthlySnapshot
from margin_engine.backtesting.regime_classifier import MarketRegimeHistorical


class TestFailureAudit:
    def _make_snapshots(self) -> list[MonthlySnapshot]:
        """Build 12 months of snapshots with varying performance."""
        snapshots = []
        portfolio_value = 1_000_000.0
        benchmark_value = 1_000_000.0

        returns_data = [
            # (portfolio_return, benchmark_return)
            (0.02, 0.01),     # Jan: good
            (-0.15, -0.10),   # Feb: bad — underperformed by 5%
            (-0.08, -0.02),   # Mar: bad — underperformed by 6%
            (0.05, 0.03),     # Apr: good
            (0.01, 0.04),     # May: bad — underperformed by 3%
            (0.03, 0.02),     # Jun: good
            (-0.10, -0.01),   # Jul: very bad — underperformed by 9%
            (0.04, 0.03),     # Aug: good
            (0.02, 0.05),     # Sep: bad — underperformed by 3%
            (-0.05, 0.02),    # Oct: worst — underperformed by 7%
            (0.06, 0.04),     # Nov: good
            (0.03, 0.01),     # Dec: good
        ]

        for i, (pr, br) in enumerate(returns_data):
            month = i + 1
            portfolio_value *= (1 + pr)
            benchmark_value *= (1 + br)
            snapshots.append(MonthlySnapshot(
                date=date(2020, month, 1),
                holdings=[
                    HoldingRecord(ticker="AAPL", weight=0.5, entry_price=150.0, composite_score=85.0),
                    HoldingRecord(ticker="MSFT", weight=0.5, entry_price=300.0, composite_score=80.0),
                ],
                portfolio_value=portfolio_value,
                benchmark_value=benchmark_value,
                portfolio_return=pr,
                benchmark_return=br,
                turnover=0.1,
                transaction_costs=100.0,
            ))

        return snapshots

    def test_returns_worst_periods(self):
        snapshots = self._make_snapshots()
        regimes = [MarketRegimeHistorical.BULL] * 12
        audit = compute_failure_audit(snapshots, regimes, n_worst=5)
        assert len(audit) == 5

    def test_worst_period_is_most_underperforming(self):
        snapshots = self._make_snapshots()
        regimes = [MarketRegimeHistorical.BULL] * 12
        audit = compute_failure_audit(snapshots, regimes, n_worst=3)
        # July was worst (-10% vs -1% = -9% relative)
        assert audit[0].rebalance_date == date(2020, 7, 1)

    def test_includes_holdings(self):
        snapshots = self._make_snapshots()
        regimes = [MarketRegimeHistorical.BULL] * 12
        audit = compute_failure_audit(snapshots, regimes, n_worst=1)
        assert len(audit[0].holdings) == 2

    def test_empty_snapshots(self):
        audit = compute_failure_audit([], [], n_worst=10)
        assert len(audit) == 0
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest engine/tests/backtesting/test_failure_audit.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Write minimal implementation**

```python
"""Failure audit for backtesting.

Identifies the worst-performing rebalance periods and explains what
the model held, what drove the underperformance, and the macro context.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel

from margin_engine.backtesting.models import HoldingRecord, MonthlySnapshot
from margin_engine.backtesting.regime_classifier import MarketRegimeHistorical


class FailurePeriod(BaseModel):
    """A single worst-performing rebalance period."""

    rebalance_date: date
    portfolio_return: float
    benchmark_return: float
    relative_underperformance: float  # benchmark_return - portfolio_return
    holdings: list[HoldingRecord]
    regime: MarketRegimeHistorical
    regime_context: str  # Human-readable macro context


def _regime_context(regime: MarketRegimeHistorical, as_of: date) -> str:
    """Generate human-readable regime context for a failure period."""
    year = as_of.year
    month_name = as_of.strftime("%b %Y")

    if regime == MarketRegimeHistorical.CRISIS:
        if 2007 <= year <= 2009:
            return f"{month_name}: Global Financial Crisis — credit markets frozen"
        if year == 2020 and as_of.month <= 4:
            return f"{month_name}: COVID-19 pandemic — global lockdowns"
        return f"{month_name}: Market crisis — sustained high volatility"

    if regime == MarketRegimeHistorical.BEAR:
        return f"{month_name}: Bear market — broad equity decline >20%"

    if regime == MarketRegimeHistorical.SIDEWAYS:
        return f"{month_name}: Sideways market — range-bound trading"

    return f"{month_name}: Bull market — model underperformed during risk-on rally"


def compute_failure_audit(
    snapshots: list[MonthlySnapshot],
    regimes: list[MarketRegimeHistorical],
    n_worst: int = 10,
) -> list[FailurePeriod]:
    """Identify the N worst rebalance periods by relative underperformance.

    Args:
        snapshots: Monthly portfolio snapshots from the backtest.
        regimes: Regime classification for each snapshot (same length).
        n_worst: Number of worst periods to return.

    Returns:
        List of FailurePeriod sorted by worst relative underperformance first.
    """
    if not snapshots:
        return []

    periods: list[FailurePeriod] = []
    for snapshot, regime in zip(snapshots, regimes):
        relative = snapshot.benchmark_return - snapshot.portfolio_return
        if relative > 0:  # Only include periods where model underperformed
            periods.append(FailurePeriod(
                rebalance_date=snapshot.date,
                portfolio_return=snapshot.portfolio_return,
                benchmark_return=snapshot.benchmark_return,
                relative_underperformance=relative,
                holdings=snapshot.holdings,
                regime=regime,
                regime_context=_regime_context(regime, snapshot.date),
            ))

    # Sort by worst underperformance first
    periods.sort(key=lambda p: -p.relative_underperformance)
    return periods[:n_worst]
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest engine/tests/backtesting/test_failure_audit.py -v`
Expected: PASS (all 4 tests)

**Step 5: Commit**

```bash
git add engine/src/margin_engine/backtesting/failure_audit.py engine/tests/backtesting/test_failure_audit.py
git commit -m "feat(engine): add failure audit computation for backtesting worst periods"
```

---

### Task 7: Walk-Forward Out-of-Sample Partitioning

Implements rolling walk-forward analysis that trains on N years and tests on the next year. Returns composite out-of-sample metrics only.

**Files:**
- Create: `engine/src/margin_engine/backtesting/walk_forward.py`
- Create: `engine/tests/backtesting/test_walk_forward.py`

**Step 1: Write the failing test**

```python
"""Tests for walk-forward out-of-sample partitioning."""

from datetime import date

import pytest

from margin_engine.backtesting.walk_forward import (
    WalkForwardPartition,
    generate_walk_forward_partitions,
)


class TestWalkForwardPartitions:
    def test_generates_correct_partitions(self):
        partitions = generate_walk_forward_partitions(
            start_date=date(2006, 1, 1),
            end_date=date(2020, 12, 31),
            train_years=5,
            test_years=1,
        )
        # 2006-2010 train, 2011 test; 2007-2011 train, 2012 test; etc.
        assert len(partitions) == 10

    def test_partition_dates_correct(self):
        partitions = generate_walk_forward_partitions(
            start_date=date(2006, 1, 1),
            end_date=date(2020, 12, 31),
            train_years=5,
            test_years=1,
        )
        first = partitions[0]
        assert first.train_start == date(2006, 1, 1)
        assert first.train_end == date(2010, 12, 31)
        assert first.test_start == date(2011, 1, 1)
        assert first.test_end == date(2011, 12, 31)

    def test_no_overlap_between_train_and_test(self):
        partitions = generate_walk_forward_partitions(
            start_date=date(2006, 1, 1),
            end_date=date(2020, 12, 31),
            train_years=5,
            test_years=1,
        )
        for p in partitions:
            assert p.train_end < p.test_start

    def test_short_period_returns_fewer_partitions(self):
        partitions = generate_walk_forward_partitions(
            start_date=date(2018, 1, 1),
            end_date=date(2020, 12, 31),
            train_years=2,
            test_years=1,
        )
        assert len(partitions) == 1

    def test_insufficient_data_returns_empty(self):
        partitions = generate_walk_forward_partitions(
            start_date=date(2020, 1, 1),
            end_date=date(2020, 12, 31),
            train_years=5,
            test_years=1,
        )
        assert len(partitions) == 0
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest engine/tests/backtesting/test_walk_forward.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Write minimal implementation**

```python
"""Walk-forward out-of-sample partitioning.

Generates rolling train/test windows for walk-forward analysis.
All reported metrics come from the test (out-of-sample) periods only.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class WalkForwardPartition(BaseModel):
    """A single train/test window in walk-forward analysis."""

    train_start: date
    train_end: date
    test_start: date
    test_end: date
    partition_index: int

    @property
    def train_years(self) -> float:
        return (self.train_end - self.train_start).days / 365.25

    @property
    def test_years(self) -> float:
        return (self.test_end - self.test_start).days / 365.25


def generate_walk_forward_partitions(
    start_date: date,
    end_date: date,
    train_years: int = 5,
    test_years: int = 1,
) -> list[WalkForwardPartition]:
    """Generate rolling walk-forward train/test windows.

    Rolls forward by test_years each iteration:
    - Window 1: train [start, start+train), test [start+train, start+train+test)
    - Window 2: train [start+1, start+1+train), test [start+1+train, start+1+train+test)
    - ...until test_end exceeds end_date.

    Args:
        start_date: Earliest date for training data.
        end_date: Latest date for test data.
        train_years: Length of training window in years.
        test_years: Length of test window in years.

    Returns:
        List of WalkForwardPartition with no overlap between train and test.
    """
    partitions: list[WalkForwardPartition] = []
    idx = 0

    current_train_start = start_date

    while True:
        train_end_year = current_train_start.year + train_years
        train_end = date(train_end_year - 1, 12, 31)

        test_start = date(train_end_year, 1, 1)
        test_end_year = train_end_year + test_years
        test_end = date(test_end_year - 1, 12, 31)

        if test_end > end_date:
            break

        partitions.append(WalkForwardPartition(
            train_start=current_train_start,
            train_end=train_end,
            test_start=test_start,
            test_end=test_end,
            partition_index=idx,
        ))

        idx += 1
        # Roll forward by test_years
        current_train_start = date(current_train_start.year + test_years, 1, 1)

    return partitions
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest engine/tests/backtesting/test_walk_forward.py -v`
Expected: PASS (all 5 tests)

**Step 5: Commit**

```bash
git add engine/src/margin_engine/backtesting/walk_forward.py engine/tests/backtesting/test_walk_forward.py
git commit -m "feat(engine): add walk-forward out-of-sample partitioning for backtest validation"
```

---

### Task 8: Backtest API Endpoints (Replace Mock)

Replace the mock backtest API with real endpoints that persist results to the database and enqueue on-demand runs via ARQ. Reuse existing `BacktestRun`/`BacktestResult` DB models.

**Files:**
- Modify: `api/src/margin_api/routes/backtest.py`
- Modify: `api/src/margin_api/schemas/backtest.py`
- Create: `api/src/margin_api/services/backtest.py`
- Modify: `api/tests/routes/test_backtest.py` (update existing tests)

**Step 1: Write the failing test**

Update `api/tests/routes/test_backtest.py` to test the new endpoint behavior. The existing tests hit the mock endpoints; the new tests should validate the DB-backed behavior.

```python
"""Tests for backtest API endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient

from margin_api.app import create_app
from margin_api.schemas.backtest import ReplayConfigRequest


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestBacktestEndpoints:
    @pytest.mark.anyio
    async def test_get_teaser_returns_headline_metrics(self, client):
        response = await client.get("/api/v1/backtest/teaser/AAPL")
        assert response.status_code == 200
        data = response.json()
        assert "model_return" in data
        assert "benchmark_return" in data
        assert "max_drawdown" in data
        assert "benchmark_max_drawdown" in data

    @pytest.mark.anyio
    async def test_get_default_backtest(self, client):
        response = await client.get("/api/v1/backtest/default")
        assert response.status_code == 200
        data = response.json()
        assert "metrics" in data
        assert "regime_segments" in data

    @pytest.mark.anyio
    async def test_run_custom_backtest_validates_constraints(self, client):
        # sector_exclusions max 2
        response = await client.post("/api/v1/backtest/run", json={
            "sector_exclusions": ["Technology", "Healthcare", "Energy"],
        })
        assert response.status_code == 422

    @pytest.mark.anyio
    async def test_run_custom_backtest_accepts_valid_config(self, client):
        response = await client.post("/api/v1/backtest/run", json={
            "rebalance_frequency": "quarterly",
            "conviction_threshold": 0.20,
        })
        # Should return 202 Accepted (enqueued) or 200 with results
        assert response.status_code in (200, 201, 202)
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/routes/test_backtest.py -v`
Expected: FAIL — new endpoints don't exist yet

**Step 3: Update schemas**

Modify `api/src/margin_api/schemas/backtest.py` to add the new request/response schemas alongside existing ones:

```python
# Add to existing schemas/backtest.py:

class ReplayConfigRequest(BaseModel):
    """Request for a custom replay backtest."""

    start_date: date = Field(default=date(2006, 1, 1))
    end_date: date | None = None
    rebalance_frequency: str = Field(default="monthly", pattern="^(monthly|quarterly|semi_annual)$")
    conviction_threshold: float = Field(default=0.10, gt=0, le=0.50)
    weighting: str = Field(default="equal", pattern="^(equal|conviction)$")
    sector_exclusions: list[str] = Field(default_factory=list, max_length=2)
    transaction_cost_bps: float = Field(default=20.0, ge=0)

    @model_validator(mode="after")
    def validate_constraints(self) -> ReplayConfigRequest:
        if len(self.sector_exclusions) > 2:
            raise ValueError("Maximum 2 sector exclusions allowed")
        return self


class BacktestTeaserResponse(BaseModel):
    """Teaser metrics for free users."""

    ticker: str | None = None
    model_return: float  # cumulative since inception
    benchmark_return: float
    max_drawdown: float
    benchmark_max_drawdown: float
    start_date: date
    end_date: date


class RegimeSegmentResponse(BaseModel):
    """Regime-segmented performance."""

    regime: str
    num_months: int
    total_return: float
    benchmark_return: float
    max_drawdown: float


class AuditRecordResponse(BaseModel):
    """Single rebalance audit entry."""

    rebalance_date: date
    universe_size: int
    eliminated_count: int
    survivor_count: int
    selected_count: int
    top_holdings: list[dict]
    notable_events: list[str]
    factor_coverage: float
    regime: str


class FactorTimelineResponse(BaseModel):
    """Factor availability at a point in time."""

    as_of_date: date
    available: list[str]
    missing: list[str]
    coverage_ratio: float


class FailurePeriodResponse(BaseModel):
    """A worst-performing rebalance period."""

    rebalance_date: date
    portfolio_return: float
    benchmark_return: float
    relative_underperformance: float
    holdings: list[dict]
    regime: str
    regime_context: str


class FullBacktestResponse(BaseModel):
    """Full backtest result for pro users."""

    config: ReplayConfigRequest
    metrics: MetricsResponse
    regime_segments: list[RegimeSegmentResponse]
    audit_log: list[AuditRecordResponse]
    factor_timeline: list[FactorTimelineResponse]
    failure_audit: list[FailurePeriodResponse]
    equity_curve: list[dict]  # [{date, portfolio_value, benchmark_value, regime}]
    walk_forward_note: str  # "All returns shown are out-of-sample"
    honesty_disclosure: str
```

**Step 4: Update routes**

Replace the mock implementation in `api/src/margin_api/routes/backtest.py` with real endpoints. Keep the old endpoints for backwards compatibility temporarily.

Add three new endpoints:
- `GET /api/v1/backtest/teaser/{ticker}` — free user teaser
- `GET /api/v1/backtest/default` — pre-computed default backtest
- `POST /api/v1/backtest/run` — on-demand custom backtest (pro only)

**Step 5: Run tests and iterate**

Run: `uv run pytest api/tests/routes/test_backtest.py -v`

**Step 6: Commit**

```bash
git add api/src/margin_api/routes/backtest.py api/src/margin_api/schemas/backtest.py api/src/margin_api/services/backtest.py api/tests/routes/test_backtest.py
git commit -m "feat(api): replace mock backtest endpoints with DB-backed replay engine integration"
```

---

### Task 9: Shadow Portfolio API + DB Models

Add shadow portfolio DB models, a daily worker job, and API endpoints.

**Files:**
- Modify: `api/src/margin_api/db/models.py` (add `ShadowPortfolioSnapshot`, `ShadowPortfolioPosition`)
- Create: `api/alembic/versions/xxxx_add_shadow_portfolio_tables.py`
- Modify: `api/src/margin_api/workers.py` (add `shadow_portfolio_update` job)
- Modify: `api/src/margin_api/routes/backtest.py` (add shadow endpoints)
- Create: `api/tests/routes/test_shadow_portfolio.py`

**Step 1: Write the failing test**

```python
"""Tests for shadow portfolio endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient

from margin_api.app import create_app


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestShadowPortfolioEndpoints:
    @pytest.mark.anyio
    async def test_get_shadow_portfolio_returns_data(self, client):
        response = await client.get("/api/v1/backtest/shadow-portfolio")
        assert response.status_code == 200
        data = response.json()
        assert "start_date" in data
        assert "snapshots" in data
        assert "total_return" in data
        assert "cannot_be_backdated" in data
        assert data["cannot_be_backdated"] is True
```

**Step 2-6: Implement DB models, migration, worker job, endpoints, verify, commit**

```bash
git commit -m "feat(api): add shadow portfolio DB models, daily worker job, and API endpoints"
```

---

### Task 10: Pre-Compute and On-Demand Worker Jobs

Add ARQ worker functions for pre-computing the default backtest and running on-demand custom backtests. Results are cached by parameter hash.

**Files:**
- Modify: `api/src/margin_api/workers.py` (add `precompute_backtest`, `run_custom_backtest` jobs)
- Modify: `api/src/margin_api/routes/backtest.py` (enqueue on-demand runs)
- Create: `api/tests/workers/test_backtest_workers.py`

**Step 1: Write the failing test**

```python
"""Tests for backtest worker jobs."""

import pytest

from margin_engine.backtesting.replay_orchestrator import ReplayConfig


class TestBacktestWorkers:
    def test_config_hash_is_deterministic(self):
        from margin_api.services.backtest import compute_config_hash

        config1 = ReplayConfig(conviction_threshold=0.10, rebalance_frequency="monthly")
        config2 = ReplayConfig(conviction_threshold=0.10, rebalance_frequency="monthly")
        config3 = ReplayConfig(conviction_threshold=0.20, rebalance_frequency="monthly")

        assert compute_config_hash(config1) == compute_config_hash(config2)
        assert compute_config_hash(config1) != compute_config_hash(config3)

    def test_config_hash_changes_with_sector_exclusions(self):
        from margin_api.services.backtest import compute_config_hash

        config1 = ReplayConfig(sector_exclusions=[])
        config2 = ReplayConfig(sector_exclusions=["Energy"])

        assert compute_config_hash(config1) != compute_config_hash(config2)
```

**Step 2-6: Implement worker functions, caching, verify, commit**

```bash
git commit -m "feat(api): add backtest pre-compute and on-demand worker jobs with parameter hash caching"
```

---

### Task 11: Web — Backtest Teaser Component

The conversion hook on the asset detail page. Three numbers and a CTA button, shown to all users.

**Files:**
- Create: `web/src/components/asset-detail/backtest-teaser.tsx`
- Create: `web/src/components/asset-detail/__tests__/backtest-teaser.test.tsx`
- Modify: `web/src/components/asset-detail/asset-detail-view.tsx` (add teaser below valuation)
- Modify: `web/src/lib/api/backtest.ts` (add `getBacktestTeaser()`)
- Modify: `web/src/lib/api/types.ts` (add `BacktestTeaserResponse` type)

**Step 1: Write the failing test**

```typescript
import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import { BacktestTeaser } from "../backtest-teaser"

describe("BacktestTeaser", () => {
  it("renders headline return numbers", () => {
    render(
      <BacktestTeaser
        modelReturn={3.87}
        benchmarkReturn={2.14}
        maxDrawdown={0.31}
        benchmarkMaxDrawdown={0.56}
        startYear={2006}
      />
    )

    expect(screen.getByText(/\+387%/)).toBeInTheDocument()
    expect(screen.getByText(/\+214%/)).toBeInTheDocument()
  })

  it("renders drawdown comparison", () => {
    render(
      <BacktestTeaser
        modelReturn={3.87}
        benchmarkReturn={2.14}
        maxDrawdown={0.31}
        benchmarkMaxDrawdown={0.56}
        startYear={2006}
      />
    )

    expect(screen.getByText(/-31%/)).toBeInTheDocument()
    expect(screen.getByText(/-56%/)).toBeInTheDocument()
  })

  it("renders upgrade CTA", () => {
    render(
      <BacktestTeaser
        modelReturn={3.87}
        benchmarkReturn={2.14}
        maxDrawdown={0.31}
        benchmarkMaxDrawdown={0.56}
        startYear={2006}
      />
    )

    expect(screen.getByText(/See every decision/i)).toBeInTheDocument()
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd web && npx vitest run src/components/asset-detail/__tests__/backtest-teaser.test.tsx`
Expected: FAIL — component doesn't exist

**Step 3: Write the component**

```tsx
"use client"

import Link from "next/link"

interface BacktestTeaserProps {
  modelReturn: number        // e.g. 3.87 for 387%
  benchmarkReturn: number    // e.g. 2.14 for 214%
  maxDrawdown: number        // e.g. 0.31 for 31%
  benchmarkMaxDrawdown: number
  startYear: number
}

export function BacktestTeaser({
  modelReturn,
  benchmarkReturn,
  maxDrawdown,
  benchmarkMaxDrawdown,
  startYear,
}: BacktestTeaserProps) {
  const modelPct = `+${Math.round(modelReturn * 100)}%`
  const benchPct = `+${Math.round(benchmarkReturn * 100)}%`
  const drawdownPct = `-${Math.round(maxDrawdown * 100)}%`
  const benchDrawdownPct = `-${Math.round(benchmarkMaxDrawdown * 100)}%`

  return (
    <div className="terminal-card p-6 mt-6">
      <h3 className="text-sm font-medium text-[var(--color-text-tertiary)] uppercase tracking-wider mb-4">
        Historical Performance
      </h3>

      <div className="space-y-3">
        {/* Headline return */}
        <div className="flex items-baseline justify-between">
          <span className="text-sm text-[var(--color-text-secondary)]">
            Model cumulative return since {startYear}
          </span>
          <span className="font-[family-name:var(--font-display)] text-2xl text-[var(--color-bullish)]">
            {modelPct}
          </span>
        </div>

        {/* Benchmark comparison */}
        <div className="flex items-baseline justify-between">
          <span className="text-sm text-[var(--color-text-secondary)]">
            S&P 500 over same period
          </span>
          <span className="font-[family-name:var(--font-mono)] text-lg text-[var(--color-text-tertiary)]">
            {benchPct}
          </span>
        </div>

        {/* Drawdown comparison */}
        <div className="flex items-baseline justify-between">
          <span className="text-sm text-[var(--color-text-secondary)]">
            Max drawdown during 2008 crisis
          </span>
          <span className="font-[family-name:var(--font-mono)] text-lg">
            <span className="text-[var(--color-bearish)]">{drawdownPct}</span>
            <span className="text-[var(--color-text-tertiary)] mx-1">vs</span>
            <span className="text-[var(--color-text-tertiary)]">{benchDrawdownPct}</span>
          </span>
        </div>
      </div>

      {/* CTA */}
      <Link
        href="/backtest"
        className="mt-5 block w-full text-center py-3 px-4 rounded-lg bg-[var(--color-accent)] text-white text-sm font-medium hover:bg-[var(--color-accent-hover)] transition-colors"
      >
        See every decision the model made →
      </Link>
    </div>
  )
}
```

**Step 4: Run test to verify it passes**

Run: `cd web && npx vitest run src/components/asset-detail/__tests__/backtest-teaser.test.tsx`
Expected: PASS

**Step 5: Wire into asset detail view**

Add the `BacktestTeaser` component to `asset-detail-view.tsx`, below the `ValuationSection`. Fetch teaser data from the API and pass it as props.

**Step 6: Commit**

```bash
git add web/src/components/asset-detail/backtest-teaser.tsx web/src/components/asset-detail/__tests__/backtest-teaser.test.tsx web/src/components/asset-detail/asset-detail-view.tsx web/src/lib/api/backtest.ts web/src/lib/api/types.ts
git commit -m "feat(web): add backtest teaser component to asset detail page"
```

---

### Task 12: Web — Regime Performance Cards

Four cards at the top of the full backtest page. Bull, Bear, Sideways, Crisis — each showing model vs benchmark returns.

**Files:**
- Create: `web/src/components/backtesting/regime-cards.tsx`
- Create: `web/src/components/backtesting/__tests__/regime-cards.test.tsx`

**Step 1-5: TDD cycle (test → fail → implement → pass → commit)**

```bash
git commit -m "feat(web): add regime performance cards for backtest page"
```

---

### Task 13: Web — Equity Curve with Regime Bands

Full 20-year Recharts ComposedChart with portfolio vs benchmark lines, regime background bands, and drawdown shading. Follow existing `score-chart.tsx` patterns.

**Files:**
- Create: `web/src/components/backtesting/equity-curve.tsx`
- Create: `web/src/components/backtesting/__tests__/equity-curve.test.tsx`

**Step 1-5: TDD cycle**

Key implementation notes:
- Use `ResponsiveContainer` + `ComposedChart` (match `score-chart.tsx`)
- Regime bands as `ReferenceArea` components with colored fills
- Drawdown as negative `Area` below the curve in `--color-bearish`
- Geist Mono for axes, custom tooltip
- Height: 400px

```bash
git commit -m "feat(web): add equity curve with regime bands and drawdown shading"
```

---

### Task 14: Web — Factor Availability Timeline

Horizontal bar chart showing which factors were active at each historical point. Clickable for detail.

**Files:**
- Create: `web/src/components/backtesting/factor-timeline.tsx`
- Create: `web/src/components/backtesting/__tests__/factor-timeline.test.tsx`

**Step 1-5: TDD cycle**

```bash
git commit -m "feat(web): add factor availability timeline for backtest page"
```

---

### Task 15: Web — Knobs Panel + Rebalance Audit Log + Stats

The constrained parameter controls sidebar, the scrollable audit log table, and the statistical summary panel.

**Files:**
- Create: `web/src/components/backtesting/knobs-panel.tsx`
- Create: `web/src/components/backtesting/audit-log.tsx`
- Create: `web/src/components/backtesting/stats-summary.tsx`
- Create: `web/src/components/backtesting/failure-audit.tsx`
- Create tests for each

**Step 1-5: TDD cycle for each component**

```bash
git commit -m "feat(web): add knobs panel, audit log, stats summary, and failure audit components"
```

---

### Task 16: Web — Full Backtest Page + Shadow Portfolio Section

Assemble all components into the `/backtest` page with pro-tier gating. Add the shadow portfolio section at the bottom.

**Files:**
- Modify: `web/src/app/backtesting/page.tsx`
- Create: `web/src/components/backtesting/shadow-section.tsx`
- Create: `web/src/components/backtesting/__tests__/shadow-section.test.tsx`

**Step 1: Write the failing test**

```typescript
import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { ShadowSection } from "../shadow-section"

describe("ShadowSection", () => {
  it("renders cannot-be-backdated badge", () => {
    render(
      <ShadowSection
        startDate="2026-02-24"
        totalReturn={0.0}
        maxDrawdown={0.0}
        numDays={1}
        positions={[]}
      />
    )

    expect(screen.getByText(/cannot be backdated/i)).toBeInTheDocument()
  })

  it("renders tracking-since date", () => {
    render(
      <ShadowSection
        startDate="2026-02-24"
        totalReturn={0.012}
        maxDrawdown={0.005}
        numDays={5}
        positions={[{ ticker: "AAPL", weight: 0.5 }]}
      />
    )

    expect(screen.getByText(/2026-02-24/)).toBeInTheDocument()
  })
})
```

**Step 2-6: Implement page assembly with ProGate, wire all components, verify, commit**

Key implementation notes:
- Use `useSubscriptionTier()` hook — if `tier === "free"`, show `ProGate`
- Server component fetches default backtest + shadow portfolio data
- Knobs panel triggers client-side `POST /api/v1/backtest/run`
- Honesty disclosure as persistent footer

```bash
git commit -m "feat(web): assemble full backtest page with pro-tier gating and shadow portfolio"
```

---

### Task 17: Update Exports and Integration Test

Wire everything together. Update barrel exports, add a smoke-level integration test that runs the full pipeline.

**Files:**
- Modify: `engine/src/margin_engine/backtesting/__init__.py`
- Create: `engine/tests/backtesting/test_integration.py`
- Modify: `web/src/lib/api/index.ts` (export new backtest functions)

**Step 1: Write the integration test**

```python
"""Integration test for the full replay backtesting pipeline."""

from datetime import date

import pytest

from margin_engine.backtesting import (
    FactorRegistry,
    InMemoryPITProvider,
    ReplayConfig,
    ReplayOrchestrator,
)
from margin_engine.backtesting.failure_audit import compute_failure_audit
from margin_engine.backtesting.walk_forward import generate_walk_forward_partitions
from margin_engine.models.financial import (
    AssetProfile,
    BalanceSheet,
    CashFlowStatement,
    FinancialPeriod,
    GICSSector,
    IncomeStatement,
)


class TestFullPipeline:
    def test_end_to_end_replay(self):
        """Run a 12-month replay and verify all outputs are populated."""
        provider = InMemoryPITProvider()
        # Add 12 months of data for 5 tickers
        tickers = ["AAPL", "MSFT", "GOOG", "AMZN", "META"]
        for i in range(12):
            month = i + 1
            for j, ticker in enumerate(tickers):
                price = 100.0 + j * 10 + i * 2
                provider.add_snapshot(
                    date(2020, month, 1),
                    ticker,
                    AssetProfile(
                        ticker=ticker, name=f"{ticker} Inc",
                        sector=GICSSector.TECHNOLOGY, sub_industry="Software",
                        market_cap=50e9, avg_daily_volume=10e6,
                        shares_outstanding=1e9,
                    ),
                    FinancialPeriod(
                        period_end=date(2020, month, 1),
                        current=IncomeStatement(
                            revenue=10000, cogs=4000, gross_profit=6000,
                            sga=1000, depreciation=500, ebit=4500,
                            interest_expense=200, tax_expense=1000, net_income=3300,
                            shares_outstanding=1e9,
                        ),
                        current_balance=BalanceSheet(
                            total_assets=50000, current_assets=20000, cash=10000,
                            receivables=5000, total_liabilities=20000,
                            current_liabilities=8000, long_term_debt=10000,
                            total_equity=30000, retained_earnings=15000,
                            shares_outstanding=1e9,
                        ),
                        current_cash_flow=CashFlowStatement(
                            operating_cash_flow=5000, capital_expenditures=-1000,
                        ),
                        prior=IncomeStatement(
                            revenue=9000, cogs=3600, gross_profit=5400,
                            sga=900, depreciation=450, ebit=4050,
                            interest_expense=200, tax_expense=900, net_income=2950,
                            shares_outstanding=1e9,
                        ),
                        prior_balance=BalanceSheet(
                            total_assets=45000, current_assets=18000, cash=9000,
                            receivables=4500, total_liabilities=18000,
                            current_liabilities=7000, long_term_debt=9000,
                            total_equity=27000, retained_earnings=13000,
                            shares_outstanding=1e9,
                        ),
                        prior_cash_flow=CashFlowStatement(
                            operating_cash_flow=4500, capital_expenditures=-900,
                        ),
                    ),
                    price,
                )

        config = ReplayConfig(
            start_date=date(2020, 1, 1),
            end_date=date(2020, 12, 1),
            rebalance_frequency="monthly",
        )
        orchestrator = ReplayOrchestrator(
            config=config,
            pit_provider=provider,
            factor_registry=FactorRegistry.default(),
        )

        result = orchestrator.run()

        # Verify all outputs
        assert result.metrics.num_months > 0
        assert len(result.audit_log) > 0
        assert len(result.factor_timeline) > 0
        assert len(result.regime_segments) > 0
        assert result.duration_seconds > 0

        # Verify audit log contents
        first_audit = result.audit_log[0]
        assert first_audit.universe_size == 5
        assert first_audit.factor_coverage > 0

        # Failure audit
        regimes = [a.regime for a in result.audit_log]
        failures = compute_failure_audit(result.snapshots, regimes)
        # May or may not have failures depending on returns
        assert isinstance(failures, list)
```

**Step 2: Run integration test**

Run: `uv run pytest engine/tests/backtesting/test_integration.py -v`

**Step 3: Update `__init__.py` exports**

```python
# engine/src/margin_engine/backtesting/__init__.py
from margin_engine.backtesting.factor_registry import FactorAvailability, FactorRegistry
from margin_engine.backtesting.failure_audit import FailurePeriod, compute_failure_audit
from margin_engine.backtesting.models import (
    BacktestConfig,
    BacktestResult,
    HoldingRecord,
    MonthlySnapshot,
    PerformanceMetrics,
)
from margin_engine.backtesting.pit_provider import (
    DelistingEvent,
    DelistingType,
    InMemoryPITProvider,
    PITSnapshot,
    PointInTimeProvider,
)
from margin_engine.backtesting.regime_classifier import (
    MarketRegimeHistorical,
    RegimeSegment,
    classify_regime,
    segment_by_regime,
)
from margin_engine.backtesting.replay_orchestrator import (
    RebalanceAuditRecord,
    ReplayConfig,
    ReplayOrchestrator,
    ReplayResult,
)
from margin_engine.backtesting.shadow_portfolio import (
    ShadowPortfolio,
    ShadowPosition,
    ShadowSnapshot,
)
from margin_engine.backtesting.walk_forward import (
    WalkForwardPartition,
    generate_walk_forward_partitions,
)
```

**Step 4: Commit**

```bash
git add engine/src/margin_engine/backtesting/__init__.py engine/tests/backtesting/test_integration.py web/src/lib/api/index.ts
git commit -m "feat: wire backtesting exports and add end-to-end integration test"
```

---

## Execution Notes

### Running All New Tests

```bash
# Engine backtesting tests (all new)
uv run pytest engine/tests/backtesting/ -v

# API backtest tests
uv run pytest api/tests/routes/test_backtest.py -v
uv run pytest api/tests/routes/test_shadow_portfolio.py -v

# Web tests
cd web && npx vitest run src/components/backtesting/
cd web && npx vitest run src/components/asset-detail/__tests__/backtest-teaser.test.tsx
```

### Key Risks During Implementation

1. **Filter pipeline imports** — `run_elimination_filters` expects `FinancialPeriod` and `AssetProfile`. Make sure the PIT provider's data satisfies the full schema (no missing required fields).

2. **History requirement** — Some filters (v2 variants) need `FinancialHistory` (multi-year). The simple PIT provider may need to aggregate multiple periods. Start with v1 filters (single period) and upgrade later.

3. **Scoring complexity** — Task 5 uses a simplified scoring proxy. The full scoring pipeline requires `TickerV4Data` with many computed fields. Wire the real pipeline incrementally after the simplified version works.

4. **DB migration ordering** — Task 9 adds new tables. Run `alembic heads` after generating the migration to check for branch forks.

### What This Plan Does NOT Cover (Future Work)

- Real Sharadar/EDGAR data ingestion (plugged into `PointInTimeProvider` later)
- Full V4 scoring integration in the replay orchestrator (uses simplified scoring for now)
- Benchmark price data provider (uses synthetic/placeholder prices)
- Production pre-compute cron scheduling
- CSV export functionality
- Mobile-responsive backtest page layout
