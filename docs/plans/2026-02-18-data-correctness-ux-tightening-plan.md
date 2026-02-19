# Data Correctness & UX Tightening Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix valuation math (dual threshold MoS), externalize filter config, fix broken metrics, expose score history, and consolidate the valuation UX into a single cohesive module.

**Architecture:** Data-up approach — engine calculations first (Python, pure logic), then API layer (FastAPI + SQLAlchemy), then frontend (Next.js + Recharts). Each phase builds on the previous.

**Tech Stack:** Python 3.13 / Pydantic / pytest / SQLAlchemy 2.0 / asyncpg / aiosqlite (tests) / Alembic / FastAPI / Next.js 15 / TypeScript / Recharts

**Design Doc:** `docs/plans/2026-02-18-data-correctness-ux-tightening-design.md`

---

## Phase 1: Engine — Valuation Model (Tasks 1-3)

### Task 1: Dual Threshold MoS — Failing Tests

**Files:**
- Modify: `engine/tests/scoring/quantitative/test_price_targets.py`

**Step 1: Update existing test to expect dual threshold**

The test `test_buy_price_equals_intrinsic` (line 149) asserts `buy_price == intrinsic_value`. Change it to assert the dual threshold relationship:

```python
def test_dual_threshold_mos(
    self, healthy_period, healthy_profile, price_bars
):
    """buy_price = MIV * (1 - MoS), sell_price = MIV * (1 + MoS)."""
    result = compute_price_targets(
        period=healthy_period,
        profile=healthy_profile,
        price_bars=price_bars,
        conviction_level=ConvictionLevel.HIGH,
    )
    assert result.buy_price is not None
    assert result.sell_price is not None
    assert result.intrinsic_value is not None
    assert result.margin_of_safety is not None
    mos = result.margin_of_safety
    # Dual threshold: buy below fair value, sell above
    assert result.buy_price == pytest.approx(
        result.intrinsic_value * (1 - mos), rel=1e-2
    )
    assert result.sell_price == pytest.approx(
        result.intrinsic_value * (1 + mos), rel=1e-2
    )
    # Ordering invariant
    assert result.buy_price < result.intrinsic_value < result.sell_price
```

**Step 2: Add test for MoS symmetry across growth stages**

```python
def test_mos_symmetry_across_growth_stages(
    self, healthy_period, healthy_profile, price_bars
):
    """Both buy and sell prices should widen symmetrically with higher MoS."""
    from margin_engine.models.scoring import GrowthStage

    steady = compute_price_targets(
        period=healthy_period,
        profile=healthy_profile,
        price_bars=price_bars,
        conviction_level=ConvictionLevel.HIGH,
        growth_stage=GrowthStage.STEADY_GROWTH,
    )
    turnaround = compute_price_targets(
        period=healthy_period,
        profile=healthy_profile,
        price_bars=price_bars,
        conviction_level=ConvictionLevel.HIGH,
        growth_stage=GrowthStage.TURNAROUND,
    )
    # Turnaround has wider MoS -> lower buy price, higher sell price
    assert turnaround.buy_price < steady.buy_price
    assert turnaround.sell_price > steady.sell_price
    # Same intrinsic value (same inputs)
    assert steady.intrinsic_value == pytest.approx(
        turnaround.intrinsic_value, rel=1e-4
    )
```

**Step 3: Run tests to verify they fail**

Run: `uv run pytest engine/tests/scoring/quantitative/test_price_targets.py::TestPriceTargets::test_dual_threshold_mos engine/tests/scoring/quantitative/test_price_targets.py::TestPriceTargets::test_mos_symmetry_across_growth_stages -v`
Expected: FAIL — `buy_price == intrinsic_value` still holds in current code.

---

### Task 2: Dual Threshold MoS — Implementation

**Files:**
- Modify: `engine/src/margin_engine/scoring/quantitative/price_targets.py:256-275`

**Step 1: Change buy_price and sell_price computation**

In `compute_price_targets()`, replace lines 256-261:

Old:
```python
    # Dynamic margin of safety — intrinsic value IS the buy price (floor).
    # MoS only applies upward for the sell price, protecting against
    # calculation error and capping expected upside.
    mos = _compute_margin_of_safety(valid_methods, intrinsic_value, growth_stage)
    buy_price = intrinsic_value
    sell_price = intrinsic_value * (1 + mos)
```

New:
```python
    # Dual threshold margin of safety — MoS applied symmetrically.
    # Buy price is discounted below fair value (entry with safety margin).
    # Sell price is above fair value (exit when overvalued).
    mos = _compute_margin_of_safety(valid_methods, intrinsic_value, growth_stage)
    buy_price = intrinsic_value * (1 - mos)
    sell_price = intrinsic_value * (1 + mos)
```

**Step 2: Run all price target tests**

Run: `uv run pytest engine/tests/scoring/quantitative/test_price_targets.py -v`
Expected: New tests PASS. The old `test_buy_price_equals_intrinsic` should have been replaced in Task 1. Check for any other tests asserting `buy_price == intrinsic_value` and update them.

**Step 3: Run full engine test suite to check for cascading failures**

Run: `uv run pytest engine/tests/ -v --tb=short 2>&1 | tail -30`
Expected: Some signal-related tests may fail if they assumed the old relationship. Fix any that do — the signal property tests in `test_composite.py` or similar will need the new thresholds.

**Step 4: Commit**

```bash
git add engine/src/margin_engine/scoring/quantitative/price_targets.py engine/tests/scoring/quantitative/test_price_targets.py
git commit -m "feat(engine): implement dual threshold MoS — buy below fair value, sell above"
```

---

### Task 3: Signal Logic Update

**Files:**
- Modify: `engine/src/margin_engine/models/scoring.py:146-167`
- Modify: `engine/tests/` (any tests asserting signal behavior)

**Step 1: Write failing test for new signal zones**

Create or update signal tests. Find the existing signal tests:

Run: `uv run pytest engine/tests/ -k "signal" --collect-only 2>&1 | head -30`

Add a test (in the appropriate test file for `CompositeScore`):

```python
def test_signal_hold_between_buy_and_sell():
    """Price between buy and sell should be HOLD, not BUY."""
    score = CompositeScore(
        ticker="TEST",
        composite_percentile=99.5,
        composite_raw_score=99.5,
        quality=_make_factor("quality"),
        value=_make_factor("value"),
        momentum=_make_factor("momentum"),
        filters_passed=[],
        data_coverage=1.0,
        buy_price=70.0,
        sell_price=130.0,
        actual_price=85.0,  # between buy and sell
        intrinsic_value=100.0,
    )
    assert score.signal == Signal.HOLD


def test_signal_buy_at_or_below_buy_price():
    """Price at or below buy_price should be BUY."""
    score = CompositeScore(
        ticker="TEST",
        composite_percentile=99.5,
        composite_raw_score=99.5,
        quality=_make_factor("quality"),
        value=_make_factor("value"),
        momentum=_make_factor("momentum"),
        filters_passed=[],
        data_coverage=1.0,
        buy_price=70.0,
        sell_price=130.0,
        actual_price=70.0,  # exactly at buy price
        intrinsic_value=100.0,
    )
    assert score.signal == Signal.BUY
```

**Step 2: Verify tests fail** (the old signal logic triggers BUY for any price <= buy_price, but with dual threshold the intermediate zone should be HOLD)

Run: `uv run pytest engine/tests/ -k "signal_hold_between" -v`

**Step 3: The signal logic doesn't actually need to change**

Looking at the existing code (lines 158-165):
```python
if self.actual_price > self.sell_price * 1.15:
    return Signal.URGENT_SELL
if self.actual_price > self.sell_price:
    return Signal.SELL
if self.actual_price <= self.buy_price:
    return Signal.BUY
return Signal.HOLD
```

This logic is already correct for dual threshold! When `buy_price < intrinsic_value`:
- Price $70 (at buy_price) → `<= buy_price` → BUY ✓
- Price $85 (between buy and sell) → not `<= buy_price`, not `> sell_price` → HOLD ✓
- Price $130 (at sell) → `> sell_price` → SELL ✓

The signal logic works unchanged. The only thing that changed is what `buy_price` equals (now it's lower than `intrinsic_value`).

**Step 4: Run tests and confirm**

Run: `uv run pytest engine/tests/ -v --tb=short 2>&1 | tail -30`
Expected: All signal tests pass.

**Step 5: Commit**

```bash
git add engine/tests/ engine/src/margin_engine/models/scoring.py
git commit -m "test(engine): verify signal logic works with dual threshold MoS"
```

---

## Phase 2: Engine — Filter Configuration (Tasks 4-6)

### Task 4: FilterConfig Pydantic Model + YAML

**Files:**
- Create: `engine/config/filters.yaml`
- Create: `engine/src/margin_engine/config/filter_config.py`
- Create: `engine/tests/config/test_filter_config.py`

**Step 1: Write failing test for config loading**

```python
"""Tests for filter configuration loading."""

import pytest
from margin_engine.config.filter_config import FilterConfig, load_filter_config


class TestFilterConfig:
    def test_default_config_loads(self):
        """Default config should load without a YAML file."""
        config = FilterConfig()
        assert config.liquidity.min_years_of_history == 5
        assert config.beneish.threshold == -1.78
        assert config.altman.threshold == 1.1

    def test_load_from_yaml(self, tmp_path):
        """Config should load from a YAML file."""
        yaml_content = """
liquidity:
  min_years_of_history: 3
  dollar_volume:
    mega: 100_000_000
beneish:
  threshold: -2.0
"""
        yaml_file = tmp_path / "filters.yaml"
        yaml_file.write_text(yaml_content)
        config = load_filter_config(yaml_file)
        assert config.liquidity.min_years_of_history == 3
        assert config.liquidity.dollar_volume.mega == 100_000_000
        assert config.beneish.threshold == -2.0
        # Defaults preserved for unspecified fields
        assert config.altman.threshold == 1.1

    def test_liquidity_dollar_volume_tiers(self):
        """Dollar volume has per-tier defaults."""
        config = FilterConfig()
        assert config.liquidity.dollar_volume.mega == 50_000_000
        assert config.liquidity.dollar_volume.large == 20_000_000
        assert config.liquidity.dollar_volume.mid == 5_000_000
        assert config.liquidity.dollar_volume.small == 2_000_000

    def test_sector_overrides(self):
        """Sector overrides have defaults matching current hardcoded values."""
        config = FilterConfig()
        assert config.interest_coverage.sector_overrides["technology"] == 3.0
        assert config.interest_coverage.sector_overrides["utilities"] == 1.2
        assert config.current_ratio.sector_overrides["utilities"] == 0.6
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest engine/tests/config/test_filter_config.py -v`
Expected: FAIL — module `margin_engine.config.filter_config` does not exist.

**Step 3: Implement FilterConfig**

Create `engine/src/margin_engine/config/__init__.py` (empty) if it doesn't exist.

Create `engine/src/margin_engine/config/filter_config.py`:

```python
"""Filter configuration — loaded from YAML, with Pydantic defaults matching current hardcoded values."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class DollarVolumeTiers(BaseModel):
    mega: int = 50_000_000
    large: int = 20_000_000
    mid: int = 5_000_000
    small: int = 2_000_000


class MarketCapMinimum(BaseModel):
    default: int = 300_000_000
    utilities: int = 1_000_000_000
    energy: int = 500_000_000


class PositionImpact(BaseModel):
    enabled: bool = False
    max_days: int = 5
    participation_rate: float = 0.10


class LiquidityConfig(BaseModel):
    excluded_sectors: list[str] = Field(default_factory=lambda: ["Financials", "Real Estate"])
    min_years_of_history: int = 5
    market_cap_minimum: MarketCapMinimum = Field(default_factory=MarketCapMinimum)
    dollar_volume: DollarVolumeTiers = Field(default_factory=DollarVolumeTiers)
    dollar_volume_window_days: int = 60
    position_impact: PositionImpact = Field(default_factory=PositionImpact)


class BeneishConfig(BaseModel):
    threshold: float = -1.78


class AltmanConfig(BaseModel):
    threshold: float = 1.1
    equity_tl_cap: float = 10.0
    exempt_sectors: list[str] = Field(default_factory=lambda: ["Utilities"])


class FcfDistressConfig(BaseModel):
    positive_years_required: int = 3
    lookback_years: int = 5
    min_fcf_margin: float = -0.05
    allow_positive_trend_rescue: bool = True


class InterestCoverageConfig(BaseModel):
    default: float = 1.5
    sector_overrides: dict[str, float] = Field(
        default_factory=lambda: {"technology": 3.0, "utilities": 1.2}
    )
    median_lookback_years: int = 3
    median_minimum: float = 1.0


class CurrentRatioConfig(BaseModel):
    default: float = 0.8
    sector_overrides: dict[str, float] = Field(
        default_factory=lambda: {"technology": 0.8, "utilities": 0.6}
    )
    quick_ratio_rescue: float = 0.5
    max_3yr_decline_pct: float = 30.0


class MediocGateConfig(BaseModel):
    min_roic_5yr_median: float = 0.08
    gross_margin_default: float = 0.20
    gross_margin_energy: float = 0.15
    gross_margin_utilities: float = 0.10
    fcf_positive_years: int = 4
    fcf_lookback_years: int = 5
    max_consecutive_revenue_decline: int = 3


class FilterConfig(BaseModel):
    liquidity: LiquidityConfig = Field(default_factory=LiquidityConfig)
    beneish: BeneishConfig = Field(default_factory=BeneishConfig)
    altman: AltmanConfig = Field(default_factory=AltmanConfig)
    fcf_distress: FcfDistressConfig = Field(default_factory=FcfDistressConfig)
    interest_coverage: InterestCoverageConfig = Field(default_factory=InterestCoverageConfig)
    current_ratio: CurrentRatioConfig = Field(default_factory=CurrentRatioConfig)
    mediocrity_gate: MediocGateConfig = Field(default_factory=MediocGateConfig)


def load_filter_config(path: Path | None = None) -> FilterConfig:
    """Load filter config from YAML file. Falls back to defaults if file missing."""
    if path is None:
        path = Path(__file__).parent.parent.parent.parent / "config" / "filters.yaml"
    if not path.exists():
        return FilterConfig()
    with open(path) as f:
        data = yaml.safe_load(f) or {}
    return FilterConfig.model_validate(data)
```

**Step 4: Create the YAML file**

Create `engine/config/filters.yaml` with the full configuration from the design doc (see design doc Section 2 for contents).

**Step 5: Run tests**

Run: `uv run pytest engine/tests/config/test_filter_config.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add engine/src/margin_engine/config/ engine/config/filters.yaml engine/tests/config/
git commit -m "feat(engine): add FilterConfig Pydantic model with YAML loading"
```

---

### Task 5: Wire FilterConfig Into Liquidity Filter

**Files:**
- Modify: `engine/src/margin_engine/scoring/filters/liquidity.py`
- Modify: `engine/tests/scoring/filters/test_liquidity.py`

**Step 1: Write failing test for tiered dollar volume**

```python
def test_dollar_volume_tiered_by_market_cap(self):
    """Mega-cap needs $50M daily volume, small-cap needs $2M."""
    from margin_engine.config.filter_config import FilterConfig

    config = FilterConfig()

    # Mega-cap with $30M volume: fails $50M threshold
    mega_profile = AssetProfile(
        ticker="MEGA",
        name="Mega Corp",
        sector=GICSSector.TECHNOLOGY,
        market_cap=Decimal("500_000_000_000"),  # $500B
        avg_daily_dollar_volume=Decimal("30_000_000"),  # $30M < $50M
        years_of_history=10,
    )
    result = liquidity_check(mega_profile, config=config.liquidity)
    assert not result.passed
    assert "dollar_vol" in result.detail.lower() or "FAIL" in result.detail

    # Small-cap with $3M volume: passes $2M threshold
    small_profile = AssetProfile(
        ticker="SMLL",
        name="Small Corp",
        sector=GICSSector.TECHNOLOGY,
        market_cap=Decimal("1_000_000_000"),  # $1B
        avg_daily_dollar_volume=Decimal("3_000_000"),  # $3M > $2M
        years_of_history=10,
    )
    result = liquidity_check(small_profile, config=config.liquidity)
    assert result.passed
```

**Step 2: Run test to verify failure**

Run: `uv run pytest engine/tests/scoring/filters/test_liquidity.py::TestLiquidity::test_dollar_volume_tiered_by_market_cap -v`
Expected: FAIL — `liquidity_check()` doesn't accept `config` parameter yet.

**Step 3: Update liquidity_check() to accept config**

Modify `liquidity.py` to:
1. Accept an optional `LiquidityConfig` parameter (default: `None`, falls back to current constants for backward compat)
2. Determine market cap bucket and look up the appropriate dollar volume threshold
3. Remove hardcoded `_MIN_AVG_DAILY_VOLUME` usage when config is provided

Key implementation:

```python
from margin_engine.config.filter_config import LiquidityConfig

def _market_cap_bucket(market_cap: Decimal) -> str:
    if market_cap >= Decimal("200_000_000_000"):
        return "mega"
    if market_cap >= Decimal("10_000_000_000"):
        return "large"
    if market_cap >= Decimal("2_000_000_000"):
        return "mid"
    return "small"

def liquidity_check(
    profile: AssetProfile,
    config: LiquidityConfig | None = None,
) -> FilterResult:
    # ... existing logic, but use config thresholds when provided
    if config is not None:
        bucket = _market_cap_bucket(profile.market_cap)
        vol_threshold = getattr(config.dollar_volume, bucket)
    else:
        vol_threshold = _MIN_AVG_DAILY_VOLUME  # legacy fallback
```

**Step 4: Run tests**

Run: `uv run pytest engine/tests/scoring/filters/test_liquidity.py -v`
Expected: All tests pass (old tests use default, new test uses config).

**Step 5: Commit**

```bash
git add engine/src/margin_engine/scoring/filters/liquidity.py engine/tests/scoring/filters/test_liquidity.py
git commit -m "feat(engine): tiered liquidity thresholds by market cap bucket"
```

---

### Task 6: Wire FilterConfig Into Remaining Filters + Pipeline

**Files:**
- Modify: `engine/src/margin_engine/scoring/filters/beneish.py`
- Modify: `engine/src/margin_engine/scoring/filters/altman.py`
- Modify: `engine/src/margin_engine/scoring/filters/fcf_distress.py`
- Modify: `engine/src/margin_engine/scoring/filters/interest_coverage.py`
- Modify: `engine/src/margin_engine/scoring/filters/current_ratio.py`
- Modify: `engine/src/margin_engine/scoring/filters/pipeline.py`
- Modify: `engine/src/margin_engine/models/scoring.py` (FilterResult: add `insufficient_data`, `missing_fields`)
- Modify: corresponding test files

**Step 1: Add `insufficient_data` and `missing_fields` to FilterResult**

In `engine/src/margin_engine/models/scoring.py`, update `FilterResult`:

```python
class FilterResult(BaseModel):
    name: str
    passed: bool
    value: float | None = None
    threshold: float | None = None
    detail: str = ""
    insufficient_data: bool = False
    missing_fields: list[str] | None = None
```

Write a test:
```python
def test_filter_result_insufficient_data():
    r = FilterResult(name="beneish", passed=True, insufficient_data=True, missing_fields=["prior_balance"])
    assert r.insufficient_data is True
    assert r.missing_fields == ["prior_balance"]
```

**Step 2: Update each filter function signature to accept its config section**

Pattern for each filter (showing beneish as example):

```python
# beneish.py
from margin_engine.config.filter_config import BeneishConfig

def beneish_m_score(
    period: FinancialPeriod,
    config: BeneishConfig | None = None,
) -> FilterResult:
    threshold = config.threshold if config else _THRESHOLD
    # ... rest of logic unchanged, but use `threshold` variable
    # When insufficient data, return:
    # FilterResult(name="beneish", passed=True, insufficient_data=True,
    #              missing_fields=["prior_income", "prior_balance"], detail="...")
```

Apply same pattern to: `altman.py` (AltmanConfig), `fcf_distress.py` (FcfDistressConfig), `interest_coverage.py` (InterestCoverageConfig), `current_ratio.py` (CurrentRatioConfig).

**Step 3: Update pipeline to load and pass config**

```python
# pipeline.py
from margin_engine.config.filter_config import FilterConfig, load_filter_config

def run_elimination_filters(
    period: FinancialPeriod,
    profile: AssetProfile,
    config: FilterConfig | None = None,
) -> PipelineResult:
    if config is None:
        config = load_filter_config()
    sector = profile.sector
    results = [
        liquidity_check(profile, config=config.liquidity),
        beneish_m_score(period, config=config.beneish),
        altman_z_score(period, sector=sector, config=config.altman),
        fcf_distress_check(period, config=config.fcf_distress),
        interest_coverage_check(period, sector=sector, config=config.interest_coverage),
        current_ratio_check(period, sector=sector, config=config.current_ratio),
    ]
    return PipelineResult(results=results)
```

**Step 4: Run full engine test suite**

Run: `uv run pytest engine/tests/ -v --tb=short 2>&1 | tail -40`
Expected: All 784+ tests pass. Existing tests use default config values which match the old hardcoded constants.

**Step 5: Commit**

```bash
git add engine/src/margin_engine/scoring/filters/ engine/src/margin_engine/models/scoring.py engine/tests/
git commit -m "feat(engine): wire FilterConfig into all filters and pipeline"
```

---

## Phase 3: API Layer (Tasks 7-10)

### Task 7: Score History Endpoint

**Files:**
- Create: `api/src/margin_api/schemas/score_history.py`
- Modify: `api/src/margin_api/routes/scores.py`
- Create: `api/tests/test_score_history.py`

**Step 1: Write failing test**

```python
"""Tests for score history endpoint."""

from __future__ import annotations
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from margin_api.app import create_app
from margin_api.db.base import Base
from margin_api.db.models import Asset, Score
from margin_api.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest_asyncio.fixture
async def history_session():
    """Seed DB with multiple score rows per ticker for history testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        aapl = Asset(
            ticker="AAPL", name="Apple Inc.",
            sector="Information Technology",
            market_cap=Decimal("3500000000000"),
        )
        session.add(aapl)
        await session.flush()

        base_time = datetime(2026, 1, 1, tzinfo=UTC)
        for i in range(5):
            score = Score(
                asset_id=aapl.id,
                composite_percentile=80.0 + i * 2,
                conviction_level="high",
                signal="buy",
                quality_percentile=85.0 + i,
                value_percentile=80.0 + i,
                momentum_percentile=82.0 + i,
                data_coverage=1.0,
                scored_at=base_time + timedelta(days=i * 7),
                intrinsic_value=Decimal("200"),
                buy_price=Decimal("150"),
                sell_price=Decimal("250"),
                actual_price=Decimal("185"),
                score_detail={},
            )
            session.add(score)
        await session.commit()

    app = create_app()
    app.dependency_overrides[get_db] = lambda: factory()
    yield app, factory
    await engine.dispose()


@pytest.mark.asyncio
async def test_score_history_returns_multiple_points(history_session):
    app, _ = history_session
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/api/v1/scores/AAPL/history")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ticker"] == "AAPL"
    assert len(data["points"]) == 5
    assert data["total_runs"] == 5


@pytest.mark.asyncio
async def test_score_history_ordered_ascending(history_session):
    app, _ = history_session
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/api/v1/scores/AAPL/history")
    points = resp.json()["points"]
    dates = [p["scored_at"] for p in points]
    assert dates == sorted(dates)


@pytest.mark.asyncio
async def test_score_history_delta_computed(history_session):
    app, _ = history_session
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/api/v1/scores/AAPL/history")
    points = resp.json()["points"]
    assert points[0]["delta"] is None  # first point has no prior
    assert points[1]["delta"] == pytest.approx(2.0)  # 82 - 80


@pytest.mark.asyncio
async def test_score_history_404_unknown_ticker(history_session):
    app, _ = history_session
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/api/v1/scores/ZZZZ/history")
    assert resp.status_code == 404
```

**Step 2: Run tests to verify failure**

Run: `uv run pytest api/tests/test_score_history.py -v`
Expected: FAIL — route does not exist.

**Step 3: Create schema**

Create `api/src/margin_api/schemas/score_history.py`:

```python
"""Score history response schemas."""

from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel


class ScoreHistoryPoint(BaseModel):
    scored_at: datetime
    composite_percentile: float
    composite_raw_score: float | None = None
    quality_percentile: float | None = None
    value_percentile: float | None = None
    momentum_percentile: float | None = None
    conviction_level: str
    signal: str
    margin_invest_value: float | None = None
    buy_price: float | None = None
    sell_price: float | None = None
    actual_price: float | None = None
    delta: float | None = None


class ScoreHistoryResponse(BaseModel):
    ticker: str
    points: list[ScoreHistoryPoint]
    total_runs: int
```

**Step 4: Add route handler**

In `api/src/margin_api/routes/scores.py`, add:

```python
from margin_api.schemas.score_history import ScoreHistoryPoint, ScoreHistoryResponse

@router.get("/{ticker}/history", response_model=ScoreHistoryResponse)
async def get_score_history(
    ticker: str,
    limit: int = Query(default=100, le=500),
    session: AsyncSession = Depends(get_db),
) -> ScoreHistoryResponse:
    asset = await session.execute(select(Asset).where(Asset.ticker == ticker))
    asset_row = asset.scalar_one_or_none()
    if asset_row is None:
        raise HTTPException(status_code=404, detail=f"Ticker {ticker} not found")

    query = (
        select(Score)
        .where(Score.asset_id == asset_row.id)
        .order_by(Score.scored_at.asc())
        .limit(limit)
    )
    result = await session.execute(query)
    rows = result.scalars().all()

    points: list[ScoreHistoryPoint] = []
    for i, row in enumerate(rows):
        delta = None
        if i > 0:
            delta = round(row.composite_percentile - rows[i - 1].composite_percentile, 2)
        points.append(ScoreHistoryPoint(
            scored_at=row.scored_at,
            composite_percentile=row.composite_percentile,
            composite_raw_score=getattr(row, "composite_raw_score", None),
            quality_percentile=row.quality_percentile,
            value_percentile=row.value_percentile,
            momentum_percentile=row.momentum_percentile,
            conviction_level=row.conviction_level,
            signal=row.signal,
            margin_invest_value=float(row.intrinsic_value) if row.intrinsic_value else None,
            buy_price=float(row.buy_price) if row.buy_price else None,
            sell_price=float(row.sell_price) if row.sell_price else None,
            actual_price=float(row.actual_price) if row.actual_price else None,
            delta=delta,
        ))

    return ScoreHistoryResponse(ticker=ticker, points=points, total_runs=len(points))
```

Note: `margin_invest_value` maps from DB column `intrinsic_value` until the rename migration (Task 10).

**Step 5: Run tests**

Run: `uv run pytest api/tests/test_score_history.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add api/src/margin_api/schemas/score_history.py api/src/margin_api/routes/scores.py api/tests/test_score_history.py
git commit -m "feat(api): add GET /scores/{ticker}/history endpoint"
```

---

### Task 8: Fix Avg Profit Margin Key-Name Bug

**Files:**
- Modify: `api/src/margin_api/services/metrics.py:90-107`
- Modify or create: `api/tests/test_metrics_service.py`

**Step 1: Write failing test**

```python
"""Tests for metrics service computation."""

from margin_api.services.metrics import compute_avg_profit_margin


def test_avg_profit_margin_with_yfinance_keys():
    """Should handle capitalized yfinance keys like 'Net Income'."""
    periods = [
        {"Net Income": 25000000000, "Total Revenue": 100000000000},
        {"Net Income": 23000000000, "Total Revenue": 95000000000},
    ]
    result = compute_avg_profit_margin(periods)
    assert result is not None
    assert result == pytest.approx(24.6, abs=1.0)  # avg of 25% and 24.2%


def test_avg_profit_margin_with_snake_case_keys():
    """Should also handle snake_case keys."""
    periods = [
        {"net_income": 25000000000, "total_revenue": 100000000000},
    ]
    result = compute_avg_profit_margin(periods)
    assert result is not None
    assert result == pytest.approx(25.0, abs=0.1)
```

**Step 2: Run test to verify failure**

Run: `uv run pytest api/tests/test_metrics_service.py::test_avg_profit_margin_with_yfinance_keys -v`
Expected: FAIL — returns `None` because keys don't match.

**Step 3: Fix the key lookup**

In `api/src/margin_api/services/metrics.py`, add a helper and update `compute_avg_profit_margin()`:

```python
def _get_field(period: dict, *candidates: str) -> float | None:
    """Try multiple key variants for yfinance compatibility."""
    for key in candidates:
        if key in period:
            val = period[key]
            return float(val) if val is not None else None
    return None


def compute_avg_profit_margin(income_periods: list[dict]) -> float | None:
    margins = []
    for period in income_periods:
        net_income = _get_field(period, "net_income", "Net Income", "netIncome")
        total_revenue = _get_field(period, "total_revenue", "Total Revenue", "totalRevenue")
        if net_income is not None and total_revenue is not None and total_revenue != 0:
            margins.append(net_income / total_revenue * 100)
    return round(sum(margins) / len(margins), 2) if margins else None
```

**Step 4: Run tests**

Run: `uv run pytest api/tests/test_metrics_service.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add api/src/margin_api/services/metrics.py api/tests/test_metrics_service.py
git commit -m "fix(api): resolve key-name mismatch in avg profit margin computation"
```

---

### Task 9: Allocation Formula + MetricStatus Schema

**Files:**
- Modify: `api/src/margin_api/services/metrics.py`
- Modify: `api/src/margin_api/schemas/metrics.py`
- Modify: `api/src/margin_api/routes/metrics.py`
- Modify: `api/tests/`

**Step 1: Write tests for allocation computation**

```python
def test_allocation_exceptional_low_vol():
    result = compute_allocation_weight("exceptional", 15.0)
    assert result == 8.0

def test_allocation_high_aggressive_vol():
    result = compute_allocation_weight("high", 45.0)
    assert result == 2.5  # 5.0 * 0.5

def test_allocation_none_volatility():
    result = compute_allocation_weight("moderate", None)
    assert result == 3.0  # base, no vol adjustment
```

**Step 2: Implement allocation formula**

In `api/src/margin_api/services/metrics.py`:

```python
def compute_allocation_weight(conviction: str, volatility: float | None) -> float:
    base = {"exceptional": 8.0, "high": 5.0, "moderate": 3.0, "watchlist": 2.0}.get(conviction, 2.0)
    if volatility is not None:
        if volatility > 40:
            base *= 0.5
        elif volatility > 25:
            base *= 0.75
    return round(base, 1)
```

**Step 3: Update MetricStatus schema**

In `api/src/margin_api/schemas/metrics.py`:

```python
class MetricStatus(BaseModel):
    value: float | None = None
    unavailable_reason: str | None = None

class InstitutionalMetricsResponse(BaseModel):
    sharpe_ratio: MetricStatus
    max_drawdown: MetricStatus
    volatility: MetricStatus
    avg_profit_margin: MetricStatus
    allocation_weight: MetricStatus
    margin_of_safety: MetricStatus
    risk_classification: str
```

**Step 4: Update metrics route to use MetricStatus and allocation formula**

In `api/src/margin_api/routes/metrics.py`, wrap each metric computation with unavailability reasons and use the new allocation formula as fallback when `max_position_pct` is NULL.

**Step 5: Run all API tests**

Run: `uv run pytest api/tests/ -v --tb=short 2>&1 | tail -30`
Expected: Some existing tests may need schema updates (they expect flat `float | None` fields, now they're `MetricStatus`). Update those tests.

**Step 6: Commit**

```bash
git add api/src/margin_api/services/metrics.py api/src/margin_api/schemas/metrics.py api/src/margin_api/routes/metrics.py api/tests/
git commit -m "feat(api): add allocation formula, MetricStatus schema with unavailability reasons"
```

---

### Task 10: Alembic Migration — Rename intrinsic_value to margin_invest_value

**Files:**
- Create: Alembic migration
- Modify: `api/src/margin_api/db/models.py`
- Modify: `api/src/margin_api/routes/scores.py` (response mapping)
- Modify: `api/src/margin_api/routes/dashboard.py` (response mapping)

**Step 1: Create migration**

Run: `cd api && uv run alembic revision --autogenerate -m "rename intrinsic_value to margin_invest_value"`

Edit the generated migration to use `op.alter_column` with `new_column_name`:

```python
def upgrade():
    op.alter_column("scores", "intrinsic_value", new_column_name="margin_invest_value")

def downgrade():
    op.alter_column("scores", "margin_invest_value", new_column_name="intrinsic_value")
```

**Step 2: Update DB model**

In `api/src/margin_api/db/models.py`, rename the column:

```python
margin_invest_value = Column(Numeric(precision=20, scale=4), nullable=True)  # was intrinsic_value
```

**Step 3: Update all route handlers** that reference `row.intrinsic_value` → `row.margin_invest_value`

Check: `scores.py`, `dashboard.py`, `metrics.py`, `v3_scores.py`

**Step 4: Update API response schemas** — rename `intrinsic_value` → `margin_invest_value` in `ScoreResponse`, `PickSummary`, etc.

**Step 5: Run tests**

Run: `uv run pytest api/tests/ -v --tb=short 2>&1 | tail -30`
Expected: PASS (tests use in-memory SQLite which gets recreated from models)

**Step 6: Commit**

```bash
git add api/
git commit -m "refactor(api): rename intrinsic_value to margin_invest_value across DB, routes, schemas"
```

---

## Phase 4: Frontend (Tasks 11-14)

### Task 11: Score History Data Fetching + Types

**Files:**
- Modify: `web/src/lib/api/types.ts`
- Modify: `web/src/lib/api/client.ts` (or wherever `apiFetch` wrappers live)
- Modify: `web/src/components/dashboard/panel/asset-panel.tsx`

**Step 1: Add types**

In `web/src/lib/api/types.ts`:

```typescript
export interface ScoreHistoryPoint {
  scored_at: string
  composite_percentile: number
  composite_raw_score: number | null
  quality_percentile: number | null
  value_percentile: number | null
  momentum_percentile: number | null
  conviction_level: string
  signal: string
  margin_invest_value: number | null
  buy_price: number | null
  sell_price: number | null
  actual_price: number | null
  delta: number | null
}

export interface ScoreHistoryResponse {
  ticker: string
  points: ScoreHistoryPoint[]
  total_runs: number
}

export interface MetricStatus {
  value: number | null
  unavailable_reason: string | null
}
```

Update `InstitutionalMetricsResponse` to use `MetricStatus` fields.

Rename `intrinsic_value` → `margin_invest_value` in `ScoreResponse` and `PickSummary`.

**Step 2: Add API client function**

```typescript
export async function getScoreHistory(ticker: string): Promise<ScoreHistoryResponse> {
  return apiFetch(`/api/v1/scores/${ticker}/history`)
}
```

**Step 3: Update AssetPanel to fetch and use real history**

Replace the synthetic single-element arrays (lines 79-92) with a fetch to the history endpoint. Wire the response into `ScoreChart` and `ScoreHistoryTable`.

**Step 4: Commit**

```bash
git add web/src/
git commit -m "feat(web): add score history types, API client, and wire into AssetPanel"
```

---

### Task 12: Price Target Chart Component

**Files:**
- Create: `web/src/components/dashboard/panel/price-target-chart.tsx`
- Modify: `web/src/components/dashboard/panel/asset-panel.tsx`

**Step 1: Create PriceTargetChart**

A Recharts `ComposedChart` that overlays:
- Daily price (Line, solid blue)
- Buy price (Line, dashed green, step interpolation)
- Margin Invest Value (Line, dotted gray, step interpolation)
- Sell price (Line, dashed red, step interpolation)
- Green `ReferenceArea` when price < buy, red when price > sell

Data alignment: use last-observation-carried-forward to align per-run target prices with daily price bars.

**Step 2: Wire into AssetPanel**

Add `<PriceTargetChart>` below `<ScoreChart>`, passing `priceHistory` and `scoreHistory` data.

**Step 3: Commit**

```bash
git add web/src/components/dashboard/panel/price-target-chart.tsx web/src/components/dashboard/panel/asset-panel.tsx
git commit -m "feat(web): add PriceTargetChart with price vs buy/sell overlay"
```

---

### Task 13: Unified Valuation Module

**Files:**
- Rewrite: `web/src/components/dashboard/panel/panel-valuation.tsx`
- Create: `web/src/components/dashboard/panel/price-ladder.tsx`

**Step 1: Create PriceLadder component**

A horizontal scale showing buy/current/fair/sell positions with color-coded zones. Takes `buyPrice`, `currentPrice`, `fairValue`, `sellPrice` as props.

**Step 2: Rewrite PanelValuation**

Replace the current layout with the unified design:
- Header trio: Margin Invest Value, Current Price, MoS
- Price ladder component
- Method breakdown bar chart (keep existing logic)
- Dispersion footnote line

Remove: separate "Buy Below" row.

**Step 3: Rename all "Intrinsic Value" labels to "Margin Invest Value"**

Search and replace across all frontend files:
- `"Intrinsic Value"` → `"Margin Invest Value"`
- `intrinsic_value` → `margin_invest_value` (in data access, already done in types)

**Step 4: Commit**

```bash
git add web/src/components/dashboard/panel/
git commit -m "feat(web): unified valuation module with price ladder, rename to Margin Invest Value"
```

---

### Task 14: KPI Grid + ActionPill + Cleanup

**Files:**
- Modify: `web/src/components/dashboard/panel/kpi-grid.tsx`
- Modify: `web/src/components/dashboard/panel/kpi-cell.tsx`
- Modify: `web/src/components/ui/action-pill.tsx`
- Modify: `web/src/components/dashboard/stock-card.tsx`
- Modify: `web/src/components/dashboard/panel/executive-header.tsx`

**Step 1: Update KpiGrid cell 6**

Swap "MARGIN OF SAFETY" → "SCORE DELTA":

```typescript
<KpiCell
  label="SCORE DELTA"
  value={scoreDelta != null ? `${scoreDelta > 0 ? "+" : ""}${scoreDelta.toFixed(1)}` : "\u2014"}
  color={scoreDelta != null ? (scoreDelta >= 0 ? "text-emerald-400" : "text-red-400") : undefined}
  unavailableReason={scoreDelta == null ? "First scoring run" : undefined}
/>
```

**Step 2: Update KpiCell to show unavailability reasons**

Add an `unavailableReason` prop. When value is "—" and reason exists, render it below in muted text:

```typescript
{unavailableReason && (
  <span className="text-[10px] text-zinc-500 mt-0.5">{unavailableReason}</span>
)}
```

**Step 3: Update MetricStatus consumption in KpiGrid**

Each cell now receives `MetricStatus` and extracts `.value` and `.unavailable_reason`.

**Step 4: Update ActionPill subtext**

In `action-pill.tsx`, update `getSubtext()` for dual threshold:

```typescript
case "buy":
  return `Below ${formatPrice(buyPrice)} buy target`
case "hold":
  return `${formatPrice(actualPrice)} — between buy (${formatPrice(buyPrice)}) and sell (${formatPrice(sellPrice)})`
case "sell":
  return `Above ${formatPrice(sellPrice)} sell target`
```

**Step 5: Remove Buy Below line from StockCard**

Delete the Buy Below rendering block (lines 260-277 of `stock-card.tsx`).

**Step 6: Wire real scoreDelta into ExecutiveHeader**

Pass the delta from the first two points of score history instead of hardcoded `0`.

**Step 7: Run frontend build to verify no type errors**

Run: `cd web && npm run build`
Expected: Build succeeds with no type errors.

**Step 8: Commit**

```bash
git add web/src/
git commit -m "feat(web): update KPI grid, ActionPill subtext, remove Buy Below section"
```

---

## Verification Checklist

After all tasks are complete, verify:

- [ ] `uv run pytest engine/tests/ -v` — all pass
- [ ] `uv run pytest api/tests/ -v` — all pass
- [ ] `cd web && npm run build` — no type errors
- [ ] No references to "Intrinsic Value" in codebase: `rg "Intrinsic Value" --type-add 'code:*.{py,ts,tsx}' -t code`
- [ ] No references to `intrinsic_value` in frontend: `rg "intrinsic_value" web/src/`
- [ ] `buy_price < margin_invest_value < sell_price` invariant holds in golden tests
- [ ] Score history endpoint returns multiple points after 2+ CLI scoring runs
- [ ] KPI grid shows no "—" for Sharpe/Vol/Drawdown/Allocation on assets with price data
- [ ] Avg Profit Margin populates for assets with income statement data
