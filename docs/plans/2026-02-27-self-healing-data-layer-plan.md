# Self-Healing Data Layer Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a three-tier anomaly detection and correction layer between raw financial data and the scoring pipeline, with full audit logging and circuit breakers.

**Architecture:** New `engine/src/margin_engine/healing/` module with detection (Tier 1-3), correction (L1-L3), and audit models. A `HealingPipeline` class intercepts normalized `IncomeStatement`/`BalanceSheet`/`CashFlowStatement` objects, detects anomalies against per-sector rolling distributions, applies corrections deterministically, and returns corrected objects plus `CorrectionEvent` records. The API scoring service calls `HealingPipeline.heal()` after normalization and before `FinancialPeriod` assembly. A new `correction_events` DB table stores all corrections. A new `sector_distributions` DB table stores rolling MAD stats per scoring run.

**Tech Stack:** Python 3.13, Pydantic v2, SQLAlchemy 2.0 (asyncpg + aiosqlite), pytest, Alembic

**Design Doc:** `docs/plans/2026-02-27-self-healing-data-layer-design.md`

---

### Task 1: Healing Data Models (Pydantic)

**Files:**
- Create: `engine/src/margin_engine/healing/__init__.py`
- Create: `engine/src/margin_engine/healing/models.py`
- Test: `engine/tests/healing/test_models.py`

**Step 1: Write the failing test**

Create `engine/tests/healing/__init__.py` (empty) and `engine/tests/healing/test_models.py`:

```python
"""Tests for healing layer Pydantic models."""

from margin_engine.healing.models import (
    CorrectionEvent,
    CorrectionMethod,
    DetectionResult,
    DetectionSeverity,
    FieldClass,
    HealingConfig,
    SectorDistribution,
)


class TestDetectionResult:
    def test_create_impossible(self):
        r = DetectionResult(
            field_path="income_statement.revenue",
            severity=DetectionSeverity.IMPOSSIBLE,
            detail="Revenue is negative for non-financial company",
            original_value=-1000.0,
            mad_deviation=None,
        )
        assert r.severity == DetectionSeverity.IMPOSSIBLE
        assert r.field_path == "income_statement.revenue"

    def test_create_outlier_with_mad(self):
        r = DetectionResult(
            field_path="income_statement.gross_margin",
            severity=DetectionSeverity.OUTLIER,
            detail="MAD deviation: 7.2 on gross_margin, sector median: 0.42",
            original_value=0.95,
            mad_deviation=7.2,
        )
        assert r.mad_deviation == 7.2


class TestCorrectionEvent:
    def test_create_l1_substitute(self):
        e = CorrectionEvent(
            field_path="income_statement.revenue",
            detection_severity=DetectionSeverity.IMPOSSIBLE,
            detection_detail="Revenue is negative",
            original_value=-1000.0,
            corrected_value=50000.0,
            correction_method=CorrectionMethod.L1_SUBSTITUTE,
            correction_source="fmp",
            correction_confidence=0.95,
        )
        assert e.correction_method == CorrectionMethod.L1_SUBSTITUTE
        assert e.correction_confidence == 0.95

    def test_create_l2_carry_forward(self):
        e = CorrectionEvent(
            field_path="balance_sheet.total_assets",
            detection_severity=DetectionSeverity.OUTLIER,
            detection_detail="MAD deviation: 8.1",
            original_value=0.0,
            corrected_value=500000.0,
            correction_method=CorrectionMethod.L2_CARRY_FORWARD,
            correction_source="self_Q-1",
            correction_confidence=0.85,
        )
        assert e.correction_source == "self_Q-1"

    def test_create_l3_sector_median(self):
        e = CorrectionEvent(
            field_path="income_statement.sga_expense",
            detection_severity=DetectionSeverity.SUSPICIOUS,
            detection_detail="Cross-sectional deviation",
            original_value=999999.0,
            corrected_value=10000.0,
            correction_method=CorrectionMethod.L3_SECTOR_MEDIAN,
            correction_source="sector_median",
            correction_confidence=0.5,
        )
        assert e.correction_method == CorrectionMethod.L3_SECTOR_MEDIAN


class TestSectorDistribution:
    def test_create(self):
        d = SectorDistribution(
            sector="TECHNOLOGY",
            field_path="income_statement.gross_margin",
            median=0.55,
            mad=0.08,
            n_observations=45,
            period="2026-Q1",
        )
        assert d.median == 0.55
        assert d.mad == 0.08


class TestHealingConfig:
    def test_defaults(self):
        c = HealingConfig()
        assert c.tier2_mad_thresholds["margins"] == 6.0
        assert c.tier2_mad_thresholds["growth_rates"] == 8.0
        assert c.tier2_mad_thresholds["leverage_ratios"] == 7.0
        assert c.tier2_mad_thresholds["price_returns"] == 10.0
        assert c.carry_forward_max_quarters == 4
        assert c.carry_forward_decay_rate == 0.15
        assert c.substitution_tolerance == 0.20
        assert c.sector_breadth_threshold == 0.15
        assert c.variance_compression_floor == 0.85
        assert "revenue" in c.excluded_fields
        assert "total_assets" in c.excluded_fields

    def test_custom_thresholds(self):
        c = HealingConfig(
            tier2_mad_thresholds={"margins": 5.0, "growth_rates": 7.0,
                                  "leverage_ratios": 6.0, "price_returns": 9.0},
        )
        assert c.tier2_mad_thresholds["margins"] == 5.0

    def test_version_present(self):
        c = HealingConfig()
        assert c.version == "1.0.0"


class TestFieldClass:
    def test_enum_values(self):
        assert FieldClass.MARGINS.value == "margins"
        assert FieldClass.GROWTH_RATES.value == "growth_rates"
        assert FieldClass.LEVERAGE_RATIOS.value == "leverage_ratios"
        assert FieldClass.PRICE_RETURNS.value == "price_returns"
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest engine/tests/healing/test_models.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'margin_engine.healing'`

**Step 3: Write minimal implementation**

Create `engine/src/margin_engine/healing/__init__.py`:

```python
"""Self-healing data layer for anomaly detection and correction."""
```

Create `engine/src/margin_engine/healing/models.py`:

```python
"""Pydantic models for the self-healing data layer.

Defines detection results, correction events, sector distributions,
and configuration for the healing pipeline.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class DetectionSeverity(str, Enum):
    IMPOSSIBLE = "impossible"
    OUTLIER = "outlier"
    SUSPICIOUS = "suspicious"


class CorrectionMethod(str, Enum):
    L1_SUBSTITUTE = "l1_substitute"
    L2_CARRY_FORWARD = "l2_carry_forward"
    L3_SECTOR_MEDIAN = "l3_sector_median"


class FieldClass(str, Enum):
    MARGINS = "margins"
    GROWTH_RATES = "growth_rates"
    LEVERAGE_RATIOS = "leverage_ratios"
    PRICE_RETURNS = "price_returns"


# Maps each financial model field to its FieldClass for threshold lookup.
FIELD_CLASS_MAP: dict[str, FieldClass] = {
    # Margins (bounded 0-1ish, true outliers rare)
    "income_statement.gross_margin": FieldClass.MARGINS,
    "income_statement.net_margin": FieldClass.MARGINS,
    "cash_flow.fcf_margin": FieldClass.MARGINS,
    # Growth rates (heavy-tailed)
    "derived.revenue_growth": FieldClass.GROWTH_RATES,
    "derived.earnings_growth": FieldClass.GROWTH_RATES,
    # Leverage ratios (sector-dependent)
    "balance_sheet.debt_to_equity": FieldClass.LEVERAGE_RATIOS,
    "derived.interest_coverage": FieldClass.LEVERAGE_RATIOS,
    "balance_sheet.current_ratio": FieldClass.LEVERAGE_RATIOS,
    # Raw numeric fields default to growth_rates (most conservative)
}

# Fields that must never be L3-imputed (ticker excluded from scoring instead).
EXCLUDED_FIELDS: frozenset[str] = frozenset({
    "revenue", "net_income", "operating_cash_flow", "free_cash_flow",
    "total_assets", "total_liabilities", "total_equity", "total_debt",
    "shares_outstanding", "market_cap", "price_history",
})


class DetectionResult(BaseModel):
    """Result of anomaly detection for a single field."""

    field_path: str
    severity: DetectionSeverity
    detail: str
    original_value: float | None
    mad_deviation: float | None = None


class CorrectionEvent(BaseModel):
    """Record of a single correction applied to a financial field."""

    field_path: str
    detection_severity: DetectionSeverity
    detection_detail: str
    original_value: float | None
    corrected_value: float
    correction_method: CorrectionMethod
    correction_source: str
    correction_confidence: float


class SectorDistribution(BaseModel):
    """Rolling distribution stats for a single field within a sector."""

    sector: str
    field_path: str
    median: float
    mad: float
    n_observations: int
    period: str


class HealingConfig(BaseModel):
    """Versioned configuration for the self-healing data layer."""

    version: str = "1.0.0"

    # Tier 2: MAD thresholds per field class
    tier2_mad_thresholds: dict[str, float] = {
        "margins": 6.0,
        "growth_rates": 8.0,
        "leverage_ratios": 7.0,
        "price_returns": 10.0,
    }

    # Tier 3: Cross-sectional checks
    tier3_self_history_multiplier: float = 3.0
    tier3_sector_corroboration_required: bool = True

    # Correction parameters
    carry_forward_max_quarters: int = 4
    carry_forward_decay_rate: float = 0.15
    cross_sectional_min_confidence: float = 0.3
    substitution_tolerance: float = 0.20

    # Circuit breakers
    sector_breadth_threshold: float = 0.15
    consecutive_flag_regime_shift: int = 2
    variance_compression_floor: float = 0.85

    # Trend-awareness
    trend_threshold_multiplier: float = 1.5

    # Fields never L3-imputed
    excluded_fields: frozenset[str] = EXCLUDED_FIELDS
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest engine/tests/healing/test_models.py -v`
Expected: All 10 tests PASS

**Step 5: Commit**

```bash
git add engine/src/margin_engine/healing/ engine/tests/healing/
git commit -m "feat(engine): add healing layer Pydantic models"
```

---

### Task 2: Tier 1 Detection — Deterministic Impossibility Checks

**Files:**
- Create: `engine/src/margin_engine/healing/detection.py`
- Test: `engine/tests/healing/test_tier1_detection.py`

**Step 1: Write the failing test**

```python
"""Tests for Tier 1 deterministic impossibility detection."""

from decimal import Decimal

import pytest

from margin_engine.healing.detection import detect_tier1
from margin_engine.healing.models import DetectionSeverity
from margin_engine.models.financial import (
    BalanceSheet,
    CashFlowStatement,
    FinancialPeriod,
    IncomeStatement,
)


def _make_period(
    revenue: int = 100_000,
    total_assets: int = 500_000,
    total_liabilities: int = 200_000,
    total_equity: int = 300_000,
    shares_outstanding: int = 1_000_000,
    operating_cash_flow: int = 25_000,
    capital_expenditures: int = -5_000,
    period_end: str = "2024-12-31",
) -> FinancialPeriod:
    return FinancialPeriod(
        period_end=period_end,
        filing_date=period_end,
        current_income=IncomeStatement(
            revenue=Decimal(str(revenue)),
            ebit=Decimal("20000"),
            net_income=Decimal("15000"),
            shares_outstanding=shares_outstanding,
        ),
        current_balance=BalanceSheet(
            total_assets=Decimal(str(total_assets)),
            total_liabilities=Decimal(str(total_liabilities)),
            total_equity=Decimal(str(total_equity)),
            shares_outstanding=shares_outstanding,
        ),
        current_cash_flow=CashFlowStatement(
            operating_cash_flow=Decimal(str(operating_cash_flow)),
            capital_expenditures=Decimal(str(capital_expenditures)),
        ),
    )


class TestTier1NegativeRevenue:
    def test_negative_revenue_flagged(self):
        period = _make_period(revenue=-50_000)
        flags = detect_tier1(period)
        assert any(
            f.field_path == "income_statement.revenue"
            and f.severity == DetectionSeverity.IMPOSSIBLE
            for f in flags
        )

    def test_zero_revenue_not_flagged(self):
        """Zero revenue is unusual but not impossible (pre-revenue companies)."""
        period = _make_period(revenue=0)
        flags = detect_tier1(period)
        revenue_flags = [f for f in flags if f.field_path == "income_statement.revenue"]
        assert len(revenue_flags) == 0


class TestTier1ZeroShares:
    def test_zero_shares_flagged(self):
        period = _make_period(shares_outstanding=0)
        flags = detect_tier1(period)
        assert any(
            f.field_path == "income_statement.shares_outstanding"
            and f.severity == DetectionSeverity.IMPOSSIBLE
            for f in flags
        )


class TestTier1AccountingIdentity:
    def test_identity_violation_flagged(self):
        """total_assets < total_liabilities + total_equity is impossible."""
        period = _make_period(
            total_assets=100_000,
            total_liabilities=200_000,
            total_equity=200_000,
        )
        flags = detect_tier1(period)
        assert any(
            "accounting identity" in f.detail.lower()
            and f.severity == DetectionSeverity.IMPOSSIBLE
            for f in flags
        )

    def test_small_rounding_difference_not_flagged(self):
        """Small rounding differences (< 1% of total_assets) are OK."""
        period = _make_period(
            total_assets=500_000,
            total_liabilities=200_000,
            total_equity=298_000,  # off by 2000, which is 0.4% of total_assets
        )
        flags = detect_tier1(period)
        identity_flags = [f for f in flags if "accounting identity" in f.detail.lower()]
        assert len(identity_flags) == 0


class TestTier1StaleDuplicate:
    def test_identical_current_and_prior_flagged(self):
        """If current period is byte-for-byte identical to prior, it's stale."""
        income = IncomeStatement(
            revenue=Decimal("100000"),
            ebit=Decimal("20000"),
            net_income=Decimal("15000"),
            shares_outstanding=1_000_000,
        )
        balance = BalanceSheet(
            total_assets=Decimal("500000"),
            shares_outstanding=1_000_000,
        )
        cash_flow = CashFlowStatement(
            operating_cash_flow=Decimal("25000"),
            capital_expenditures=Decimal("-5000"),
        )
        period = FinancialPeriod(
            period_end="2024-12-31",
            filing_date="2024-12-31",
            current_income=income,
            prior_income=income,
            current_balance=balance,
            prior_balance=balance,
            current_cash_flow=cash_flow,
            prior_cash_flow=cash_flow,
        )
        flags = detect_tier1(period)
        assert any(
            "stale" in f.detail.lower()
            and f.severity == DetectionSeverity.IMPOSSIBLE
            for f in flags
        )

    def test_no_prior_period_not_flagged(self):
        """Without prior period data, stale check is skipped."""
        period = _make_period()  # no prior_* fields
        flags = detect_tier1(period)
        stale_flags = [f for f in flags if "stale" in f.detail.lower()]
        assert len(stale_flags) == 0


class TestTier1CleanData:
    def test_healthy_period_no_flags(self):
        period = _make_period()
        flags = detect_tier1(period)
        assert len(flags) == 0
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest engine/tests/healing/test_tier1_detection.py -v`
Expected: FAIL with `ImportError: cannot import name 'detect_tier1'`

**Step 3: Write minimal implementation**

Create `engine/src/margin_engine/healing/detection.py`:

```python
"""Anomaly detection for the self-healing data layer.

Three tiers of detection, ordered by certainty:
- Tier 1: Deterministic impossibility checks (zero false positives)
- Tier 2: Univariate MAD-based outlier detection (low false positive rate)
- Tier 3: Cross-sectional + historical consistency checks (moderate FP rate)
"""

from __future__ import annotations

from margin_engine.healing.models import DetectionResult, DetectionSeverity
from margin_engine.models.financial import FinancialPeriod


_IDENTITY_TOLERANCE = 0.01  # 1% of total_assets


def detect_tier1(period: FinancialPeriod) -> list[DetectionResult]:
    """Run Tier 1 deterministic impossibility checks.

    These checks have zero false positives — any flag represents a logical
    constraint violation that no valid financial statement can exhibit.
    """
    flags: list[DetectionResult] = []

    income = period.current_income
    balance = period.current_balance

    # Negative revenue (non-financial companies)
    if income.revenue < 0:
        flags.append(DetectionResult(
            field_path="income_statement.revenue",
            severity=DetectionSeverity.IMPOSSIBLE,
            detail=f"Negative revenue: {income.revenue}",
            original_value=float(income.revenue),
        ))

    # Zero or missing shares outstanding
    if income.shares_outstanding <= 0:
        flags.append(DetectionResult(
            field_path="income_statement.shares_outstanding",
            severity=DetectionSeverity.IMPOSSIBLE,
            detail=f"Invalid shares_outstanding: {income.shares_outstanding}",
            original_value=float(income.shares_outstanding),
        ))

    # Accounting identity violation: A < L + E beyond rounding tolerance
    total_a = float(balance.total_assets)
    total_l = float(balance.total_liabilities)
    total_e = float(balance.total_equity)
    if total_a > 0:
        imbalance = (total_l + total_e) - total_a
        if imbalance > total_a * _IDENTITY_TOLERANCE:
            flags.append(DetectionResult(
                field_path="balance_sheet.identity",
                severity=DetectionSeverity.IMPOSSIBLE,
                detail=(
                    f"Accounting identity violation: "
                    f"L({total_l}) + E({total_e}) exceeds A({total_a}) "
                    f"by {imbalance:.0f} ({imbalance / total_a:.1%})"
                ),
                original_value=total_a,
            ))

    # Stale duplicate: current period identical to prior period
    if period.prior_income is not None and period.prior_balance is not None:
        current_dump = (
            period.current_income.model_dump(),
            period.current_balance.model_dump(),
        )
        prior_dump = (
            period.prior_income.model_dump(),
            period.prior_balance.model_dump(),
        )
        if current_dump == prior_dump:
            # Also check cash flow if available
            cf_match = True
            if period.current_cash_flow and period.prior_cash_flow:
                cf_match = (
                    period.current_cash_flow.model_dump()
                    == period.prior_cash_flow.model_dump()
                )
            if cf_match:
                flags.append(DetectionResult(
                    field_path="period",
                    severity=DetectionSeverity.IMPOSSIBLE,
                    detail="Stale data: current period identical to prior period",
                    original_value=None,
                ))

    return flags
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest engine/tests/healing/test_tier1_detection.py -v`
Expected: All 8 tests PASS

**Step 5: Commit**

```bash
git add engine/src/margin_engine/healing/detection.py engine/tests/healing/test_tier1_detection.py
git commit -m "feat(engine): add Tier 1 deterministic impossibility detection"
```

---

### Task 3: Tier 2 Detection — MAD-Based Outlier Detection

**Files:**
- Modify: `engine/src/margin_engine/healing/detection.py`
- Test: `engine/tests/healing/test_tier2_detection.py`

**Step 1: Write the failing test**

```python
"""Tests for Tier 2 MAD-based univariate outlier detection."""

import pytest

from margin_engine.healing.detection import detect_tier2
from margin_engine.healing.models import (
    DetectionSeverity,
    FieldClass,
    HealingConfig,
    SectorDistribution,
)


def _dist(field_path: str, median: float, mad: float, n: int = 50) -> SectorDistribution:
    return SectorDistribution(
        sector="TECHNOLOGY",
        field_path=field_path,
        median=median,
        mad=mad,
        n_observations=n,
        period="2026-Q1",
    )


class TestTier2BasicDetection:
    def test_value_within_threshold_not_flagged(self):
        """A value 3 MADs from median should NOT be flagged (threshold is 6)."""
        config = HealingConfig()
        distributions = [_dist("income_statement.gross_margin", median=0.45, mad=0.05)]
        # 0.45 + 3 * 0.05 = 0.60 → within 6 MADs
        flags = detect_tier2(
            field_values={"income_statement.gross_margin": 0.60},
            sector_distributions=distributions,
            config=config,
        )
        assert len(flags) == 0

    def test_value_beyond_threshold_flagged(self):
        """A value 7 MADs from median should be flagged (threshold for margins is 6)."""
        config = HealingConfig()
        distributions = [_dist("income_statement.gross_margin", median=0.45, mad=0.05)]
        # 0.45 + 7 * 0.05 = 0.80 → 7 MADs, beyond threshold of 6
        flags = detect_tier2(
            field_values={"income_statement.gross_margin": 0.80},
            sector_distributions=distributions,
            config=config,
        )
        assert len(flags) == 1
        assert flags[0].severity == DetectionSeverity.OUTLIER
        assert flags[0].mad_deviation == pytest.approx(7.0, abs=0.1)

    def test_negative_deviation_also_flagged(self):
        """Deviation below median is also detected."""
        config = HealingConfig()
        distributions = [_dist("income_statement.gross_margin", median=0.45, mad=0.05)]
        # 0.45 - 7 * 0.05 = 0.10 → 7 MADs below
        flags = detect_tier2(
            field_values={"income_statement.gross_margin": 0.10},
            sector_distributions=distributions,
            config=config,
        )
        assert len(flags) == 1
        assert flags[0].mad_deviation == pytest.approx(7.0, abs=0.1)


class TestTier2FieldClassThresholds:
    def test_growth_rate_uses_higher_threshold(self):
        """Growth rates have threshold 8.0, so 7 MADs should NOT be flagged."""
        config = HealingConfig()
        distributions = [_dist("derived.revenue_growth", median=0.10, mad=0.05)]
        # 0.10 + 7 * 0.05 = 0.45 → 7 MADs, below threshold of 8
        flags = detect_tier2(
            field_values={"derived.revenue_growth": 0.45},
            sector_distributions=distributions,
            config=config,
        )
        assert len(flags) == 0

    def test_growth_rate_beyond_threshold_flagged(self):
        """Growth rates at 9 MADs should be flagged (threshold is 8)."""
        config = HealingConfig()
        distributions = [_dist("derived.revenue_growth", median=0.10, mad=0.05)]
        # 0.10 + 9 * 0.05 = 0.55 → 9 MADs
        flags = detect_tier2(
            field_values={"derived.revenue_growth": 0.55},
            sector_distributions=distributions,
            config=config,
        )
        assert len(flags) == 1

    def test_unknown_field_uses_growth_rate_threshold(self):
        """Fields not in FIELD_CLASS_MAP default to growth_rates (most conservative)."""
        config = HealingConfig()
        distributions = [_dist("some.unknown_field", median=100.0, mad=10.0)]
        # 100 + 7 * 10 = 170 → 7 MADs, below default threshold of 8
        flags = detect_tier2(
            field_values={"some.unknown_field": 170.0},
            sector_distributions=distributions,
            config=config,
        )
        assert len(flags) == 0


class TestTier2ZeroMAD:
    def test_zero_mad_skips_field(self):
        """If MAD is zero (all values identical), skip detection for that field."""
        config = HealingConfig()
        distributions = [_dist("income_statement.gross_margin", median=0.45, mad=0.0)]
        flags = detect_tier2(
            field_values={"income_statement.gross_margin": 0.90},
            sector_distributions=distributions,
            config=config,
        )
        assert len(flags) == 0

    def test_missing_distribution_skips_field(self):
        """If no distribution exists for a field, skip it."""
        config = HealingConfig()
        flags = detect_tier2(
            field_values={"income_statement.gross_margin": 0.90},
            sector_distributions=[],  # no distributions
            config=config,
        )
        assert len(flags) == 0


class TestTier2TrendAwareness:
    def test_monotonic_trend_widens_threshold(self):
        """When trailing 3 values show monotonic movement, threshold is multiplied by 1.5."""
        config = HealingConfig()
        distributions = [_dist("income_statement.gross_margin", median=0.45, mad=0.05)]
        # Normal threshold: 6. With trend: 6 * 1.5 = 9.
        # 7 MADs should NOT be flagged with trend awareness
        flags = detect_tier2(
            field_values={"income_statement.gross_margin": 0.80},
            sector_distributions=distributions,
            config=config,
            trailing_values={"income_statement.gross_margin": [0.50, 0.60, 0.70]},
        )
        assert len(flags) == 0

    def test_non_monotonic_trend_uses_normal_threshold(self):
        """Non-monotonic trailing values use the standard threshold."""
        config = HealingConfig()
        distributions = [_dist("income_statement.gross_margin", median=0.45, mad=0.05)]
        # 7 MADs, threshold 6 (no trend widening)
        flags = detect_tier2(
            field_values={"income_statement.gross_margin": 0.80},
            sector_distributions=distributions,
            config=config,
            trailing_values={"income_statement.gross_margin": [0.60, 0.50, 0.70]},
        )
        assert len(flags) == 1
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest engine/tests/healing/test_tier2_detection.py -v`
Expected: FAIL with `ImportError: cannot import name 'detect_tier2'`

**Step 3: Write minimal implementation**

Add to `engine/src/margin_engine/healing/detection.py`:

```python
from margin_engine.healing.models import (
    DetectionResult,
    DetectionSeverity,
    FieldClass,
    FIELD_CLASS_MAP,
    HealingConfig,
    SectorDistribution,
)


def _is_monotonic(values: list[float]) -> bool:
    """Check if a sequence of 3+ values is monotonically increasing or decreasing."""
    if len(values) < 3:
        return False
    diffs = [values[i + 1] - values[i] for i in range(len(values) - 1)]
    return all(d > 0 for d in diffs) or all(d < 0 for d in diffs)


def _get_threshold(field_path: str, config: HealingConfig) -> float:
    """Look up the MAD threshold for a field, defaulting to growth_rates."""
    field_class = FIELD_CLASS_MAP.get(field_path, FieldClass.GROWTH_RATES)
    return config.tier2_mad_thresholds.get(field_class.value, 8.0)


def detect_tier2(
    field_values: dict[str, float],
    sector_distributions: list[SectorDistribution],
    config: HealingConfig,
    trailing_values: dict[str, list[float]] | None = None,
) -> list[DetectionResult]:
    """Run Tier 2 univariate MAD-based outlier detection.

    For each field with a known sector distribution, compute the MAD deviation
    and flag if it exceeds the threshold for that field class.

    Args:
        field_values: Current-period field values keyed by field_path.
        sector_distributions: Rolling sector distributions for this ticker's sector.
        config: Healing configuration with thresholds.
        trailing_values: Optional trailing 3+ values per field for trend awareness.
    """
    flags: list[DetectionResult] = []
    dist_map = {d.field_path: d for d in sector_distributions}

    for field_path, value in field_values.items():
        dist = dist_map.get(field_path)
        if dist is None or dist.mad == 0.0:
            continue

        deviation = abs(value - dist.median) / dist.mad
        threshold = _get_threshold(field_path, config)

        # Trend-awareness: widen threshold if trailing values are monotonic
        if trailing_values and field_path in trailing_values:
            trail = trailing_values[field_path]
            if _is_monotonic(trail):
                threshold *= config.trend_threshold_multiplier

        if deviation > threshold:
            flags.append(DetectionResult(
                field_path=field_path,
                severity=DetectionSeverity.OUTLIER,
                detail=(
                    f"MAD deviation: {deviation:.1f} on {field_path}, "
                    f"sector median: {dist.median}, MAD: {dist.mad}, "
                    f"threshold: {threshold}"
                ),
                original_value=value,
                mad_deviation=round(deviation, 1),
            ))

    return flags
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest engine/tests/healing/test_tier2_detection.py -v`
Expected: All 10 tests PASS

**Step 5: Commit**

```bash
git add engine/src/margin_engine/healing/detection.py engine/tests/healing/test_tier2_detection.py
git commit -m "feat(engine): add Tier 2 MAD-based outlier detection"
```

---

### Task 4: Tier 3 Detection — Cross-Sectional Consistency Checks

**Files:**
- Modify: `engine/src/margin_engine/healing/detection.py`
- Test: `engine/tests/healing/test_tier3_detection.py`

**Step 1: Write the failing test**

```python
"""Tests for Tier 3 cross-sectional + historical consistency checks."""

import pytest

from margin_engine.healing.detection import detect_tier3
from margin_engine.healing.models import DetectionSeverity, HealingConfig, SectorDistribution


def _dist(field_path: str, median: float, mad: float, n: int = 50) -> SectorDistribution:
    return SectorDistribution(
        sector="TECHNOLOGY",
        field_path=field_path,
        median=median,
        mad=mad,
        n_observations=n,
        period="2026-Q1",
    )


class TestTier3SelfHistoryDeviation:
    def test_deviation_from_own_history_and_sector_stable_flagged(self):
        """Flag when value deviates >3x own MAD AND sector hasn't moved."""
        config = HealingConfig()
        # Ticker's own history: median=100k, MAD=5k
        # Current value: 130k → (130k - 100k) / 5k = 6x own MAD (> 3x threshold)
        # Sector median hasn't changed: still 100k
        flags = detect_tier3(
            field_values={"revenue": 130_000.0},
            ticker_history={"revenue": [95_000.0, 100_000.0, 105_000.0, 98_000.0,
                                        102_000.0, 97_000.0, 103_000.0, 101_000.0]},
            sector_distributions=[_dist("revenue", median=100_000.0, mad=5_000.0)],
            prior_sector_distributions=[_dist("revenue", median=99_000.0, mad=5_000.0)],
            config=config,
        )
        assert len(flags) == 1
        assert flags[0].severity == DetectionSeverity.SUSPICIOUS

    def test_deviation_with_sector_also_moving_not_flagged(self):
        """If sector median has also moved significantly, don't flag (regime shift)."""
        config = HealingConfig()
        flags = detect_tier3(
            field_values={"revenue": 130_000.0},
            ticker_history={"revenue": [95_000.0, 100_000.0, 105_000.0, 98_000.0,
                                        102_000.0, 97_000.0, 103_000.0, 101_000.0]},
            sector_distributions=[_dist("revenue", median=125_000.0, mad=8_000.0)],
            prior_sector_distributions=[_dist("revenue", median=100_000.0, mad=5_000.0)],
            config=config,
        )
        assert len(flags) == 0

    def test_small_deviation_from_history_not_flagged(self):
        """Value within 3x own MAD is not flagged."""
        config = HealingConfig()
        flags = detect_tier3(
            field_values={"revenue": 112_000.0},
            ticker_history={"revenue": [95_000.0, 100_000.0, 105_000.0, 98_000.0,
                                        102_000.0, 97_000.0, 103_000.0, 101_000.0]},
            sector_distributions=[_dist("revenue", median=100_000.0, mad=5_000.0)],
            prior_sector_distributions=[_dist("revenue", median=100_000.0, mad=5_000.0)],
            config=config,
        )
        assert len(flags) == 0


class TestTier3InsufficientHistory:
    def test_fewer_than_4_history_points_skips(self):
        """Need at least 4 historical values to compute meaningful MAD."""
        config = HealingConfig()
        flags = detect_tier3(
            field_values={"revenue": 500_000.0},
            ticker_history={"revenue": [100_000.0, 105_000.0]},
            sector_distributions=[_dist("revenue", median=100_000.0, mad=5_000.0)],
            prior_sector_distributions=[_dist("revenue", median=100_000.0, mad=5_000.0)],
            config=config,
        )
        assert len(flags) == 0

    def test_no_prior_sector_distributions_skips(self):
        """Without prior distributions, can't assess sector movement."""
        config = HealingConfig()
        flags = detect_tier3(
            field_values={"revenue": 130_000.0},
            ticker_history={"revenue": [95_000.0, 100_000.0, 105_000.0, 98_000.0,
                                        102_000.0, 97_000.0, 103_000.0, 101_000.0]},
            sector_distributions=[_dist("revenue", median=100_000.0, mad=5_000.0)],
            prior_sector_distributions=[],
            config=config,
        )
        assert len(flags) == 0
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest engine/tests/healing/test_tier3_detection.py -v`
Expected: FAIL with `ImportError: cannot import name 'detect_tier3'`

**Step 3: Write minimal implementation**

Add to `engine/src/margin_engine/healing/detection.py`:

```python
import statistics


_MIN_HISTORY_POINTS = 4
_SECTOR_MOVEMENT_THRESHOLD = 0.10  # 10% sector median shift = "sector is moving"


def _compute_mad(values: list[float]) -> float:
    """Compute Median Absolute Deviation of a list of values."""
    if len(values) < 2:
        return 0.0
    med = statistics.median(values)
    return statistics.median(abs(v - med) for v in values)


def detect_tier3(
    field_values: dict[str, float],
    ticker_history: dict[str, list[float]],
    sector_distributions: list[SectorDistribution],
    prior_sector_distributions: list[SectorDistribution],
    config: HealingConfig,
) -> list[DetectionResult]:
    """Run Tier 3 cross-sectional + historical consistency checks.

    Flags when a value deviates materially from the ticker's own history
    AND the sector hasn't moved comparably (ruling out regime shifts).

    Args:
        field_values: Current-period values keyed by field name.
        ticker_history: Trailing 8-quarter values per field (oldest first).
        sector_distributions: Current-period sector distributions.
        prior_sector_distributions: Previous-period sector distributions.
        config: Healing configuration.
    """
    flags: list[DetectionResult] = []
    current_dist_map = {d.field_path: d for d in sector_distributions}
    prior_dist_map = {d.field_path: d for d in prior_sector_distributions}

    for field_path, value in field_values.items():
        history = ticker_history.get(field_path, [])
        if len(history) < _MIN_HISTORY_POINTS:
            continue

        current_dist = current_dist_map.get(field_path)
        prior_dist = prior_dist_map.get(field_path)
        if current_dist is None or prior_dist is None:
            continue

        # Check if value deviates from ticker's own history
        ticker_median = statistics.median(history)
        ticker_mad = _compute_mad(history)
        if ticker_mad == 0.0:
            continue

        self_deviation = abs(value - ticker_median) / ticker_mad
        if self_deviation <= config.tier3_self_history_multiplier:
            continue

        # Check if sector has moved comparably (corroboration)
        if config.tier3_sector_corroboration_required and prior_dist.median != 0:
            sector_shift = abs(current_dist.median - prior_dist.median) / abs(prior_dist.median)
            if sector_shift >= _SECTOR_MOVEMENT_THRESHOLD:
                continue  # Sector also moved — likely regime shift, not anomaly

        flags.append(DetectionResult(
            field_path=field_path,
            severity=DetectionSeverity.SUSPICIOUS,
            detail=(
                f"Cross-sectional anomaly on {field_path}: "
                f"self deviation {self_deviation:.1f}x own MAD "
                f"(ticker median: {ticker_median:.0f}, MAD: {ticker_mad:.0f}), "
                f"sector stable"
            ),
            original_value=value,
            mad_deviation=round(self_deviation, 1),
        ))

    return flags
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest engine/tests/healing/test_tier3_detection.py -v`
Expected: All 5 tests PASS

**Step 5: Commit**

```bash
git add engine/src/margin_engine/healing/detection.py engine/tests/healing/test_tier3_detection.py
git commit -m "feat(engine): add Tier 3 cross-sectional consistency detection"
```

---

### Task 5: Correction Engine — L1/L2/L3 Hierarchy

**Files:**
- Create: `engine/src/margin_engine/healing/correction.py`
- Test: `engine/tests/healing/test_correction.py`

**Step 1: Write the failing test**

```python
"""Tests for the three-level correction hierarchy."""

import pytest

from margin_engine.healing.correction import apply_corrections
from margin_engine.healing.models import (
    CorrectionMethod,
    DetectionResult,
    DetectionSeverity,
    HealingConfig,
    SectorDistribution,
)


def _flag(field_path: str, severity: DetectionSeverity, value: float) -> DetectionResult:
    return DetectionResult(
        field_path=field_path,
        severity=severity,
        detail=f"Test flag on {field_path}",
        original_value=value,
    )


def _dist(field_path: str, median: float) -> SectorDistribution:
    return SectorDistribution(
        sector="TECHNOLOGY", field_path=field_path,
        median=median, mad=0.05, n_observations=50, period="2026-Q1",
    )


class TestL1Substitution:
    def test_substitute_from_secondary_source(self):
        config = HealingConfig()
        flags = [_flag("income_statement.sga_expense", DetectionSeverity.IMPOSSIBLE, -5000.0)]
        secondary_values = {"income_statement.sga_expense": 12000.0}
        events = apply_corrections(
            flags=flags,
            config=config,
            secondary_values=secondary_values,
            prior_valid_values={},
            sector_distributions=[],
        )
        assert len(events) == 1
        assert events[0].correction_method == CorrectionMethod.L1_SUBSTITUTE
        assert events[0].corrected_value == 12000.0
        assert events[0].correction_confidence == pytest.approx(0.95, abs=0.05)

    def test_substitute_rejected_when_beyond_tolerance(self):
        """Secondary value >20% different from original AND original is not IMPOSSIBLE → skip L1."""
        config = HealingConfig()
        flags = [_flag("income_statement.sga_expense", DetectionSeverity.OUTLIER, 10000.0)]
        secondary_values = {"income_statement.sga_expense": 15000.0}  # 50% different
        events = apply_corrections(
            flags=flags,
            config=config,
            secondary_values=secondary_values,
            prior_valid_values={"income_statement.sga_expense": (9800.0, 1)},
            sector_distributions=[],
        )
        # Should fall through to L2 since L1 tolerance exceeded
        assert len(events) == 1
        assert events[0].correction_method == CorrectionMethod.L2_CARRY_FORWARD

    def test_substitute_accepted_for_impossible_regardless_of_tolerance(self):
        """IMPOSSIBLE severity accepts any valid secondary value."""
        config = HealingConfig()
        flags = [_flag("income_statement.sga_expense", DetectionSeverity.IMPOSSIBLE, -5000.0)]
        secondary_values = {"income_statement.sga_expense": 50000.0}  # very different
        events = apply_corrections(
            flags=flags,
            config=config,
            secondary_values=secondary_values,
            prior_valid_values={},
            sector_distributions=[],
        )
        assert events[0].correction_method == CorrectionMethod.L1_SUBSTITUTE
        assert events[0].corrected_value == 50000.0


class TestL2CarryForward:
    def test_carry_forward_one_quarter(self):
        config = HealingConfig()
        flags = [_flag("income_statement.sga_expense", DetectionSeverity.OUTLIER, 999999.0)]
        events = apply_corrections(
            flags=flags,
            config=config,
            secondary_values={},
            prior_valid_values={"income_statement.sga_expense": (12000.0, 1)},
            sector_distributions=[],
        )
        assert len(events) == 1
        assert events[0].correction_method == CorrectionMethod.L2_CARRY_FORWARD
        assert events[0].corrected_value == 12000.0
        assert events[0].correction_confidence == pytest.approx(0.85, abs=0.01)

    def test_carry_forward_four_quarters_decayed(self):
        config = HealingConfig()
        flags = [_flag("income_statement.sga_expense", DetectionSeverity.OUTLIER, 999999.0)]
        events = apply_corrections(
            flags=flags,
            config=config,
            secondary_values={},
            prior_valid_values={"income_statement.sga_expense": (12000.0, 4)},
            sector_distributions=[],
        )
        assert events[0].correction_confidence == pytest.approx(0.40, abs=0.01)

    def test_carry_forward_too_stale_falls_through(self):
        """Beyond max_quarters (4), L2 is skipped → falls to L3."""
        config = HealingConfig()
        flags = [_flag("income_statement.sga_expense", DetectionSeverity.OUTLIER, 999999.0)]
        events = apply_corrections(
            flags=flags,
            config=config,
            secondary_values={},
            prior_valid_values={"income_statement.sga_expense": (12000.0, 5)},
            sector_distributions=[_dist("income_statement.sga_expense", 11000.0)],
        )
        assert events[0].correction_method == CorrectionMethod.L3_SECTOR_MEDIAN


class TestL3SectorMedian:
    def test_sector_median_applied(self):
        config = HealingConfig()
        flags = [_flag("income_statement.sga_expense", DetectionSeverity.OUTLIER, 999999.0)]
        events = apply_corrections(
            flags=flags,
            config=config,
            secondary_values={},
            prior_valid_values={},
            sector_distributions=[_dist("income_statement.sga_expense", 11000.0)],
        )
        assert len(events) == 1
        assert events[0].correction_method == CorrectionMethod.L3_SECTOR_MEDIAN
        assert events[0].corrected_value == 11000.0
        assert events[0].correction_confidence <= 0.5

    def test_excluded_field_not_imputed(self):
        """Revenue is in excluded_fields — L3 should NOT be applied. No correction returned."""
        config = HealingConfig()
        flags = [_flag("revenue", DetectionSeverity.OUTLIER, 999999.0)]
        events = apply_corrections(
            flags=flags,
            config=config,
            secondary_values={},
            prior_valid_values={},
            sector_distributions=[_dist("revenue", 50000.0)],
        )
        # No correction possible — excluded from L3 and no L1/L2 available
        assert len(events) == 0


class TestNoCorrectionPossible:
    def test_no_sources_available(self):
        """When no secondary, no prior, and no sector distribution → no correction."""
        config = HealingConfig()
        flags = [_flag("income_statement.sga_expense", DetectionSeverity.OUTLIER, 999999.0)]
        events = apply_corrections(
            flags=flags,
            config=config,
            secondary_values={},
            prior_valid_values={},
            sector_distributions=[],
        )
        assert len(events) == 0
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest engine/tests/healing/test_correction.py -v`
Expected: FAIL with `ImportError: cannot import name 'apply_corrections'`

**Step 3: Write minimal implementation**

Create `engine/src/margin_engine/healing/correction.py`:

```python
"""Correction engine for the self-healing data layer.

Applies corrections in a strict L1 → L2 → L3 priority order.
Each level is attempted only if the previous is inapplicable.
"""

from __future__ import annotations

from margin_engine.healing.models import (
    CorrectionEvent,
    CorrectionMethod,
    DetectionResult,
    DetectionSeverity,
    EXCLUDED_FIELDS,
    HealingConfig,
    SectorDistribution,
)


def _try_l1(
    flag: DetectionResult,
    secondary_values: dict[str, float],
    config: HealingConfig,
) -> CorrectionEvent | None:
    """Attempt L1 substitution from a secondary data source."""
    secondary = secondary_values.get(flag.field_path)
    if secondary is None:
        return None

    # For non-IMPOSSIBLE flags, check tolerance
    if flag.severity != DetectionSeverity.IMPOSSIBLE and flag.original_value is not None:
        original = flag.original_value
        if original != 0:
            diff_pct = abs(secondary - original) / abs(original)
            if diff_pct > config.substitution_tolerance:
                return None

    return CorrectionEvent(
        field_path=flag.field_path,
        detection_severity=flag.severity,
        detection_detail=flag.detail,
        original_value=flag.original_value,
        corrected_value=secondary,
        correction_method=CorrectionMethod.L1_SUBSTITUTE,
        correction_source="secondary_provider",
        correction_confidence=0.95,
    )


def _try_l2(
    flag: DetectionResult,
    prior_valid_values: dict[str, tuple[float, int]],
    config: HealingConfig,
) -> CorrectionEvent | None:
    """Attempt L2 carry-forward from the ticker's own prior valid value.

    prior_valid_values maps field_path -> (value, quarters_stale).
    """
    entry = prior_valid_values.get(flag.field_path)
    if entry is None:
        return None

    value, quarters_stale = entry
    if quarters_stale > config.carry_forward_max_quarters:
        return None

    confidence = max(
        config.cross_sectional_min_confidence,
        1.0 - (quarters_stale * config.carry_forward_decay_rate),
    )

    return CorrectionEvent(
        field_path=flag.field_path,
        detection_severity=flag.severity,
        detection_detail=flag.detail,
        original_value=flag.original_value,
        corrected_value=value,
        correction_method=CorrectionMethod.L2_CARRY_FORWARD,
        correction_source=f"self_Q-{quarters_stale}",
        correction_confidence=round(confidence, 2),
    )


def _try_l3(
    flag: DetectionResult,
    sector_distributions: list[SectorDistribution],
    config: HealingConfig,
) -> CorrectionEvent | None:
    """Attempt L3 cross-sectional imputation from sector median."""
    # Extract the base field name for excluded-field check
    base_field = flag.field_path.split(".")[-1] if "." in flag.field_path else flag.field_path
    if base_field in config.excluded_fields or flag.field_path in config.excluded_fields:
        return None

    dist_map = {d.field_path: d for d in sector_distributions}
    dist = dist_map.get(flag.field_path)
    if dist is None:
        return None

    return CorrectionEvent(
        field_path=flag.field_path,
        detection_severity=flag.severity,
        detection_detail=flag.detail,
        original_value=flag.original_value,
        corrected_value=dist.median,
        correction_method=CorrectionMethod.L3_SECTOR_MEDIAN,
        correction_source="sector_median",
        correction_confidence=0.5,
    )


def apply_corrections(
    flags: list[DetectionResult],
    config: HealingConfig,
    secondary_values: dict[str, float],
    prior_valid_values: dict[str, tuple[float, int]],
    sector_distributions: list[SectorDistribution],
) -> list[CorrectionEvent]:
    """Apply corrections for detected anomalies using L1 → L2 → L3 hierarchy.

    Args:
        flags: Detection results to correct.
        config: Healing configuration.
        secondary_values: Values from secondary data providers, keyed by field_path.
        prior_valid_values: Ticker's own prior valid values as (value, quarters_stale).
        sector_distributions: Current sector distributions for L3 imputation.

    Returns:
        List of CorrectionEvents for successfully corrected fields.
        Fields with no available correction source are omitted.
    """
    events: list[CorrectionEvent] = []

    for flag in flags:
        event = _try_l1(flag, secondary_values, config)
        if event is None:
            event = _try_l2(flag, prior_valid_values, config)
        if event is None:
            event = _try_l3(flag, sector_distributions, config)
        if event is not None:
            events.append(event)

    return events
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest engine/tests/healing/test_correction.py -v`
Expected: All 10 tests PASS

**Step 5: Commit**

```bash
git add engine/src/margin_engine/healing/correction.py engine/tests/healing/test_correction.py
git commit -m "feat(engine): add L1/L2/L3 correction hierarchy"
```

---

### Task 6: Circuit Breakers — Breadth Suspension + Variance Guard

**Files:**
- Create: `engine/src/margin_engine/healing/circuit_breakers.py`
- Test: `engine/tests/healing/test_circuit_breakers.py`

**Step 1: Write the failing test**

```python
"""Tests for healing circuit breakers."""

from margin_engine.healing.circuit_breakers import (
    check_sector_breadth,
    check_variance_compression,
)
from margin_engine.healing.models import (
    DetectionResult,
    DetectionSeverity,
    HealingConfig,
)


def _flag(field_path: str, ticker: str = "AAPL") -> DetectionResult:
    return DetectionResult(
        field_path=field_path,
        severity=DetectionSeverity.OUTLIER,
        detail=f"Test flag on {ticker}:{field_path}",
        original_value=100.0,
    )


class TestSectorBreadthSuspension:
    def test_below_threshold_not_suspended(self):
        """10% of sector flagged → no suspension (threshold is 15%)."""
        config = HealingConfig()
        # 10 tickers in sector, 1 flagged (10%)
        flagged_tickers = {"AAPL"}
        sector_size = 10
        result = check_sector_breadth(flagged_tickers, sector_size, config)
        assert result is False

    def test_above_threshold_suspended(self):
        """20% of sector flagged → suspend corrections."""
        config = HealingConfig()
        flagged_tickers = {"AAPL", "MSFT"}
        sector_size = 10
        result = check_sector_breadth(flagged_tickers, sector_size, config)
        assert result is True

    def test_exactly_at_threshold_suspended(self):
        """Exactly 15% → suspend (>=, not >)."""
        config = HealingConfig()
        flagged_tickers = {"AAPL", "MSFT", "GOOGL"}
        sector_size = 20  # 3/20 = 15%
        result = check_sector_breadth(flagged_tickers, sector_size, config)
        assert result is True

    def test_zero_sector_size_not_suspended(self):
        config = HealingConfig()
        result = check_sector_breadth(set(), 0, config)
        assert result is False


class TestVarianceCompression:
    def test_no_compression_ok(self):
        """Corrected variance close to raw variance → no warning."""
        config = HealingConfig()
        raw_values = [10.0, 20.0, 30.0, 40.0, 50.0]
        corrected_values = [12.0, 22.0, 28.0, 38.0, 48.0]
        warning = check_variance_compression(raw_values, corrected_values, config)
        assert warning is False

    def test_heavy_compression_flagged(self):
        """Corrected variance much smaller than raw → compression warning."""
        config = HealingConfig()
        raw_values = [10.0, 50.0, 90.0, 130.0, 170.0]
        # Corrected values clustered tightly around mean
        corrected_values = [85.0, 88.0, 90.0, 92.0, 95.0]
        warning = check_variance_compression(raw_values, corrected_values, config)
        assert warning is True

    def test_insufficient_data_no_warning(self):
        """Need at least 3 values to assess variance."""
        config = HealingConfig()
        warning = check_variance_compression([10.0, 20.0], [10.0, 20.0], config)
        assert warning is False
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest engine/tests/healing/test_circuit_breakers.py -v`
Expected: FAIL with `ModuleNotFoundError`

**Step 3: Write minimal implementation**

Create `engine/src/margin_engine/healing/circuit_breakers.py`:

```python
"""Circuit breakers for the self-healing data layer.

Prevents the correction layer from operating during regime shifts or
from compressing real variance out of the data.
"""

from __future__ import annotations

import statistics

from margin_engine.healing.models import HealingConfig


def check_sector_breadth(
    flagged_tickers: set[str],
    sector_size: int,
    config: HealingConfig,
) -> bool:
    """Check if too many tickers in a sector are simultaneously flagged.

    Returns True if corrections should be SUSPENDED for this sector.
    """
    if sector_size <= 0:
        return False
    breadth = len(flagged_tickers) / sector_size
    return breadth >= config.sector_breadth_threshold


def check_variance_compression(
    raw_values: list[float],
    corrected_values: list[float],
    config: HealingConfig,
) -> bool:
    """Check if corrections are compressing real variance.

    Returns True if the variance ratio drops below the floor (warning).
    """
    if len(raw_values) < 3 or len(corrected_values) < 3:
        return False

    raw_std = statistics.stdev(raw_values)
    if raw_std == 0:
        return False

    corrected_std = statistics.stdev(corrected_values)
    ratio = corrected_std / raw_std
    return ratio < config.variance_compression_floor
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest engine/tests/healing/test_circuit_breakers.py -v`
Expected: All 7 tests PASS

**Step 5: Commit**

```bash
git add engine/src/margin_engine/healing/circuit_breakers.py engine/tests/healing/test_circuit_breakers.py
git commit -m "feat(engine): add healing circuit breakers (breadth + variance)"
```

---

### Task 7: Healing Pipeline Orchestrator

**Files:**
- Create: `engine/src/margin_engine/healing/pipeline.py`
- Test: `engine/tests/healing/test_pipeline.py`

**Step 1: Write the failing test**

```python
"""Tests for the HealingPipeline orchestrator."""

from decimal import Decimal

import pytest

from margin_engine.healing.models import (
    CorrectionMethod,
    DetectionSeverity,
    HealingConfig,
    SectorDistribution,
)
from margin_engine.healing.pipeline import HealingPipeline, HealingResult
from margin_engine.models.financial import (
    BalanceSheet,
    CashFlowStatement,
    FinancialPeriod,
    IncomeStatement,
)


def _make_period(
    revenue: int = 100_000,
    shares_outstanding: int = 1_000_000,
    total_assets: int = 500_000,
    total_liabilities: int = 200_000,
    total_equity: int = 300_000,
) -> FinancialPeriod:
    return FinancialPeriod(
        period_end="2024-12-31",
        filing_date="2024-12-31",
        current_income=IncomeStatement(
            revenue=Decimal(str(revenue)),
            ebit=Decimal("20000"),
            net_income=Decimal("15000"),
            shares_outstanding=shares_outstanding,
        ),
        current_balance=BalanceSheet(
            total_assets=Decimal(str(total_assets)),
            total_liabilities=Decimal(str(total_liabilities)),
            total_equity=Decimal(str(total_equity)),
            shares_outstanding=shares_outstanding,
        ),
        current_cash_flow=CashFlowStatement(
            operating_cash_flow=Decimal("25000"),
            capital_expenditures=Decimal("-5000"),
        ),
    )


class TestHealingPipelineCleanData:
    def test_clean_data_passes_through(self):
        """Data with no anomalies returns unchanged period and empty events."""
        pipeline = HealingPipeline(config=HealingConfig())
        period = _make_period()
        result = pipeline.heal(
            period=period,
            sector="TECHNOLOGY",
            sector_distributions=[],
            prior_sector_distributions=[],
            ticker_history={},
            secondary_values={},
            prior_valid_values={},
            sector_ticker_count=50,
            sector_flagged_tickers=set(),
        )
        assert isinstance(result, HealingResult)
        assert result.period == period
        assert len(result.corrections) == 0
        assert len(result.detections) == 0
        assert result.excluded is False


class TestHealingPipelineTier1:
    def test_negative_revenue_detected(self):
        """Tier 1 detects negative revenue."""
        pipeline = HealingPipeline(config=HealingConfig())
        period = _make_period(revenue=-50_000)
        result = pipeline.heal(
            period=period,
            sector="TECHNOLOGY",
            sector_distributions=[],
            prior_sector_distributions=[],
            ticker_history={},
            secondary_values={},
            prior_valid_values={},
            sector_ticker_count=50,
            sector_flagged_tickers=set(),
        )
        assert len(result.detections) >= 1
        assert any(d.severity == DetectionSeverity.IMPOSSIBLE for d in result.detections)

    def test_zero_shares_detected_and_excluded(self):
        """Zero shares on an excluded field → ticker excluded from scoring."""
        pipeline = HealingPipeline(config=HealingConfig())
        period = _make_period(shares_outstanding=0)
        result = pipeline.heal(
            period=period,
            sector="TECHNOLOGY",
            sector_distributions=[],
            prior_sector_distributions=[],
            ticker_history={},
            secondary_values={},
            prior_valid_values={},
            sector_ticker_count=50,
            sector_flagged_tickers=set(),
        )
        # shares_outstanding is an excluded field; if L1/L2 unavailable → excluded
        assert result.excluded is True


class TestHealingPipelineSectorBreadthSuspension:
    def test_breadth_suspension_skips_corrections(self):
        """When sector breadth breaker fires, detections happen but corrections don't."""
        pipeline = HealingPipeline(config=HealingConfig())
        period = _make_period(revenue=-50_000)
        result = pipeline.heal(
            period=period,
            sector="TECHNOLOGY",
            sector_distributions=[],
            prior_sector_distributions=[],
            ticker_history={},
            secondary_values={},
            prior_valid_values={},
            sector_ticker_count=10,
            sector_flagged_tickers={"A", "B"},  # 20% > 15% threshold
        )
        assert len(result.detections) >= 1
        assert len(result.corrections) == 0
        assert result.breadth_suspended is True
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest engine/tests/healing/test_pipeline.py -v`
Expected: FAIL with `ImportError`

**Step 3: Write minimal implementation**

Create `engine/src/margin_engine/healing/pipeline.py`:

```python
"""HealingPipeline orchestrator.

Coordinates detection (Tier 1-3), correction (L1-L3), and circuit
breakers into a single heal() call that takes a FinancialPeriod
and returns a (potentially corrected) FinancialPeriod plus audit records.
"""

from __future__ import annotations

from copy import deepcopy
from decimal import Decimal

from pydantic import BaseModel

from margin_engine.healing.circuit_breakers import check_sector_breadth
from margin_engine.healing.correction import apply_corrections
from margin_engine.healing.detection import detect_tier1, detect_tier2, detect_tier3
from margin_engine.healing.models import (
    CorrectionEvent,
    DetectionResult,
    EXCLUDED_FIELDS,
    HealingConfig,
    SectorDistribution,
)
from margin_engine.models.financial import FinancialPeriod


class HealingResult(BaseModel):
    """Result of running the healing pipeline on a single FinancialPeriod."""

    period: FinancialPeriod
    detections: list[DetectionResult] = []
    corrections: list[CorrectionEvent] = []
    excluded: bool = False
    breadth_suspended: bool = False


def _extract_field_values(period: FinancialPeriod) -> dict[str, float]:
    """Extract numeric field values from a FinancialPeriod for Tier 2/3 detection."""
    values: dict[str, float] = {}
    income = period.current_income
    balance = period.current_balance

    if income.revenue != 0:
        values["income_statement.gross_margin"] = income.gross_margin
        values["income_statement.net_margin"] = income.net_margin
    values["balance_sheet.debt_to_equity"] = balance.debt_to_equity
    values["balance_sheet.current_ratio"] = balance.current_ratio

    return values


def _apply_correction_to_period(
    period: FinancialPeriod,
    event: CorrectionEvent,
) -> FinancialPeriod:
    """Apply a single correction to a FinancialPeriod, returning a new copy."""
    period = period.model_copy(deep=True)
    parts = event.field_path.split(".")

    if len(parts) == 2:
        section, field = parts
        if section == "income_statement":
            obj = period.current_income
        elif section == "balance_sheet":
            obj = period.current_balance
        elif section == "cash_flow":
            obj = period.current_cash_flow
        else:
            return period

        if hasattr(obj, field):
            current_val = getattr(obj, field)
            if isinstance(current_val, Decimal):
                setattr(obj, field, Decimal(str(event.corrected_value)))
            elif isinstance(current_val, int):
                setattr(obj, field, int(event.corrected_value))
            else:
                setattr(obj, field, event.corrected_value)

    return period


class HealingPipeline:
    """Orchestrates detection, correction, and circuit breakers."""

    def __init__(self, config: HealingConfig | None = None) -> None:
        self.config = config or HealingConfig()

    def heal(
        self,
        period: FinancialPeriod,
        sector: str,
        sector_distributions: list[SectorDistribution],
        prior_sector_distributions: list[SectorDistribution],
        ticker_history: dict[str, list[float]],
        secondary_values: dict[str, float],
        prior_valid_values: dict[str, tuple[float, int]],
        sector_ticker_count: int = 0,
        sector_flagged_tickers: set[str] | None = None,
    ) -> HealingResult:
        """Run the full healing pipeline on a FinancialPeriod.

        Args:
            period: The financial period to validate and potentially correct.
            sector: GICS sector name for this ticker.
            sector_distributions: Current rolling distributions for this sector.
            prior_sector_distributions: Previous period's distributions.
            ticker_history: Trailing 8-quarter values per field path.
            secondary_values: Values from fallback data providers.
            prior_valid_values: Ticker's own prior valid values as (value, quarters_stale).
            sector_ticker_count: Total tickers in this sector (for breadth breaker).
            sector_flagged_tickers: Set of ticker symbols flagged this period.

        Returns:
            HealingResult with (potentially corrected) period, detections, and corrections.
        """
        if sector_flagged_tickers is None:
            sector_flagged_tickers = set()

        all_detections: list[DetectionResult] = []

        # --- Tier 1: Deterministic impossibility checks ---
        tier1_flags = detect_tier1(period)
        all_detections.extend(tier1_flags)

        # --- Tier 2: MAD-based outlier detection ---
        field_values = _extract_field_values(period)
        tier2_flags = detect_tier2(
            field_values=field_values,
            sector_distributions=sector_distributions,
            config=self.config,
        )
        all_detections.extend(tier2_flags)

        # --- Tier 3: Cross-sectional + historical consistency ---
        tier3_flags = detect_tier3(
            field_values=field_values,
            ticker_history=ticker_history,
            sector_distributions=sector_distributions,
            prior_sector_distributions=prior_sector_distributions,
            config=self.config,
        )
        all_detections.extend(tier3_flags)

        # If no detections, return unchanged
        if not all_detections:
            return HealingResult(period=period)

        # --- Circuit breaker: sector breadth ---
        breadth_suspended = check_sector_breadth(
            sector_flagged_tickers, sector_ticker_count, self.config,
        )
        if breadth_suspended:
            return HealingResult(
                period=period,
                detections=all_detections,
                breadth_suspended=True,
            )

        # --- Apply corrections ---
        corrections = apply_corrections(
            flags=all_detections,
            config=self.config,
            secondary_values=secondary_values,
            prior_valid_values=prior_valid_values,
            sector_distributions=sector_distributions,
        )

        # Check if any uncorrectable detection is on an excluded field
        corrected_fields = {e.field_path for e in corrections}
        excluded = False
        for det in all_detections:
            if det.field_path not in corrected_fields:
                base_field = det.field_path.split(".")[-1] if "." in det.field_path else det.field_path
                if base_field in EXCLUDED_FIELDS:
                    excluded = True
                    break

        # Apply corrections to period
        corrected_period = period
        for event in corrections:
            corrected_period = _apply_correction_to_period(corrected_period, event)

        return HealingResult(
            period=corrected_period,
            detections=all_detections,
            corrections=corrections,
            excluded=excluded,
        )
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest engine/tests/healing/test_pipeline.py -v`
Expected: All 5 tests PASS

**Step 5: Commit**

```bash
git add engine/src/margin_engine/healing/pipeline.py engine/tests/healing/test_pipeline.py
git commit -m "feat(engine): add HealingPipeline orchestrator"
```

---

### Task 8: DB Models + Alembic Migration for CorrectionEvent Storage

**Files:**
- Modify: `api/src/margin_api/db/models.py`
- Create: `api/alembic/versions/<hash>_add_correction_events_and_sector_distributions.py`
- Test: `api/tests/db/test_correction_models.py`

**Step 1: Write the failing test**

```python
"""Tests for CorrectionEvent and SectorDistributionSnapshot DB models."""

import pytest
import pytest_asyncio
from datetime import datetime, UTC
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from margin_api.db.models import Base, CorrectionEventRecord, SectorDistributionSnapshot


@pytest_asyncio.fixture()
async def async_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture()
async def session(async_engine):
    factory = async_sessionmaker(async_engine, class_=AsyncSession)
    async with factory() as sess:
        yield sess


@pytest.mark.asyncio
async def test_create_correction_event(session: AsyncSession):
    event = CorrectionEventRecord(
        correction_id=uuid4(),
        asset_id=1,
        period_end="2024-12-31",
        field_path="income_statement.sga_expense",
        detection_tier="outlier",
        detection_detail="MAD deviation: 7.2",
        original_value=-5000.0,
        corrected_value=12000.0,
        correction_method="l1_substitute",
        correction_source="fmp",
        correction_confidence=0.95,
        correction_config_version="1.0.0",
        sector_distribution_snapshot={"median": 11000, "mad": 800, "n": 45},
    )
    session.add(event)
    await session.commit()

    result = await session.execute(
        select(CorrectionEventRecord).where(CorrectionEventRecord.asset_id == 1)
    )
    row = result.scalar_one()
    assert row.field_path == "income_statement.sga_expense"
    assert row.correction_confidence == pytest.approx(0.95)
    assert row.correction_config_version == "1.0.0"


@pytest.mark.asyncio
async def test_create_sector_distribution_snapshot(session: AsyncSession):
    snap = SectorDistributionSnapshot(
        scoring_run_id=uuid4(),
        sector="TECHNOLOGY",
        field_path="income_statement.gross_margin",
        median=0.55,
        mad=0.08,
        n_observations=45,
        period="2026-Q1",
    )
    session.add(snap)
    await session.commit()

    result = await session.execute(
        select(SectorDistributionSnapshot).where(
            SectorDistributionSnapshot.sector == "TECHNOLOGY"
        )
    )
    row = result.scalar_one()
    assert row.median == pytest.approx(0.55)
    assert row.mad == pytest.approx(0.08)
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/db/test_correction_models.py -v`
Expected: FAIL with `ImportError: cannot import name 'CorrectionEventRecord'`

**Step 3: Write minimal implementation**

Add to `api/src/margin_api/db/models.py` (after existing model classes):

```python
class CorrectionEventRecord(Base):
    """Audit log for every correction applied by the healing layer."""

    __tablename__ = "correction_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    correction_id: Mapped[str] = mapped_column(
        String(36), unique=True, index=True
    )  # UUID as string for SQLite compat
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), index=True)
    period_end: Mapped[str] = mapped_column(String(10))
    field_path: Mapped[str] = mapped_column(String(100))
    detection_tier: Mapped[str] = mapped_column(String(20))
    detection_detail: Mapped[str] = mapped_column(String(500))
    original_value: Mapped[float | None] = mapped_column(nullable=True)
    corrected_value: Mapped[float] = mapped_column()
    correction_method: Mapped[str] = mapped_column(String(30))
    correction_source: Mapped[str] = mapped_column(String(100))
    correction_confidence: Mapped[float] = mapped_column()
    correction_config_version: Mapped[str] = mapped_column(String(20))
    sector_distribution_snapshot: Mapped[dict | None] = mapped_column(
        JSONVariant, nullable=True
    )
    scoring_run_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class SectorDistributionSnapshot(Base):
    """Rolling distribution stats per sector/field, snapshotted each scoring run."""

    __tablename__ = "sector_distribution_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    scoring_run_id: Mapped[str] = mapped_column(String(36), index=True)
    sector: Mapped[str] = mapped_column(String(50))
    field_path: Mapped[str] = mapped_column(String(100))
    median: Mapped[float] = mapped_column()
    mad: Mapped[float] = mapped_column()
    n_observations: Mapped[int] = mapped_column()
    period: Mapped[str] = mapped_column(String(10))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
```

Then generate the Alembic migration:

```bash
uv run alembic revision --autogenerate -m "add correction_events and sector_distribution_snapshots"
```

Verify the migration is idempotent by adding inspector checks.

**Step 4: Run test to verify it passes**

Run: `uv run pytest api/tests/db/test_correction_models.py -v`
Expected: All 2 tests PASS

**Step 5: Commit**

```bash
git add api/src/margin_api/db/models.py api/alembic/versions/ api/tests/db/test_correction_models.py
git commit -m "feat(api): add CorrectionEvent and SectorDistribution DB models"
```

---

### Task 9: Wire Healing Pipeline into Scoring Service

**Files:**
- Modify: `api/src/margin_api/services/scoring.py` (lines 87-130, `build_financial_period`)
- Test: `api/tests/services/test_scoring_healing.py`

**Step 1: Write the failing test**

```python
"""Tests for healing integration in the scoring service."""

from decimal import Decimal
from unittest.mock import patch

import pytest

from margin_api.services.scoring import build_financial_period
from margin_engine.healing.models import HealingConfig
from margin_engine.healing.pipeline import HealingPipeline


class TestBuildFinancialPeriodWithHealing:
    def test_clean_data_unchanged(self):
        """Normal data passes through without modification."""
        income_raw = {"revenue": 100000, "ebit": 20000, "netIncome": 15000,
                      "sharesOutstanding": 1000000}
        balance_raw = {"totalAssets": 500000, "totalLiabilities": 200000,
                       "totalStockholdersEquity": 300000}
        cashflow_raw = {"operatingCashFlow": 25000, "capitalExpenditure": -5000}

        period = build_financial_period(
            income_raw, balance_raw, cashflow_raw,
            period_end="2024-12-31", filing_date="2024-12-31",
        )
        assert float(period.current_income.revenue) == 100000

    def test_negative_revenue_detected_when_healing_enabled(self):
        """When healing pipeline is provided, Tier 1 detects negative revenue."""
        income_raw = {"revenue": -50000, "ebit": 20000, "netIncome": 15000,
                      "sharesOutstanding": 1000000}
        balance_raw = {"totalAssets": 500000, "totalLiabilities": 200000,
                       "totalStockholdersEquity": 300000}
        cashflow_raw = {"operatingCashFlow": 25000, "capitalExpenditure": -5000}

        pipeline = HealingPipeline(config=HealingConfig())
        period, result = build_financial_period(
            income_raw, balance_raw, cashflow_raw,
            period_end="2024-12-31", filing_date="2024-12-31",
            healing_pipeline=pipeline,
            sector="TECHNOLOGY",
        )
        assert result is not None
        assert len(result.detections) >= 1
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest api/tests/services/test_scoring_healing.py -v`
Expected: FAIL (build_financial_period doesn't accept `healing_pipeline`)

**Step 3: Write minimal implementation**

Modify `api/src/margin_api/services/scoring.py` — update `build_financial_period()` to accept an optional healing pipeline. The function signature changes:

```python
def build_financial_period(
    income_raw: dict,
    balance_raw: dict,
    cashflow_raw: dict,
    period_end: str,
    filing_date: str,
    prior_income_raw: dict | None = None,
    prior_balance_raw: dict | None = None,
    prior_cashflow_raw: dict | None = None,
    # Healing pipeline (optional)
    healing_pipeline: HealingPipeline | None = None,
    sector: str = "",
    sector_distributions: list | None = None,
    prior_sector_distributions: list | None = None,
    ticker_history: dict | None = None,
    secondary_values: dict | None = None,
    prior_valid_values: dict | None = None,
    sector_ticker_count: int = 0,
    sector_flagged_tickers: set | None = None,
) -> FinancialPeriod | tuple[FinancialPeriod, HealingResult | None]:
    """Convert raw JSON dicts into a FinancialPeriod engine model.

    When healing_pipeline is provided, returns a tuple of (period, healing_result).
    When healing_pipeline is None (default), returns just the period for backward compat.
    """
    current_income = normalize_income_statement(income_raw)
    current_balance = normalize_balance_sheet(balance_raw)
    current_cash_flow = normalize_cash_flow(cashflow_raw)

    prior_income = normalize_income_statement(prior_income_raw) if prior_income_raw else None
    prior_balance = normalize_balance_sheet(prior_balance_raw) if prior_balance_raw else None
    prior_cash_flow = normalize_cash_flow(prior_cashflow_raw) if prior_cashflow_raw else None

    period = FinancialPeriod(
        period_end=period_end,
        filing_date=filing_date,
        current_income=current_income,
        prior_income=prior_income,
        current_balance=current_balance,
        prior_balance=prior_balance,
        current_cash_flow=current_cash_flow,
        prior_cash_flow=prior_cash_flow,
    )

    if healing_pipeline is None:
        return period

    healing_result = healing_pipeline.heal(
        period=period,
        sector=sector,
        sector_distributions=sector_distributions or [],
        prior_sector_distributions=prior_sector_distributions or [],
        ticker_history=ticker_history or {},
        secondary_values=secondary_values or {},
        prior_valid_values=prior_valid_values or {},
        sector_ticker_count=sector_ticker_count,
        sector_flagged_tickers=sector_flagged_tickers,
    )

    return healing_result.period, healing_result
```

Add imports at top of file:

```python
from margin_engine.healing.pipeline import HealingPipeline, HealingResult
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest api/tests/services/test_scoring_healing.py -v`
Expected: All 2 tests PASS

Then run full API tests to verify no regressions:

Run: `uv run pytest api/tests/ -v --timeout=120`
Expected: All existing tests still PASS (backward compatible — healing_pipeline defaults to None)

**Step 5: Commit**

```bash
git add api/src/margin_api/services/scoring.py api/tests/services/test_scoring_healing.py
git commit -m "feat(api): wire healing pipeline into build_financial_period"
```

---

### Task 10: Distribution Computation Service

**Files:**
- Create: `engine/src/margin_engine/healing/distributions.py`
- Test: `engine/tests/healing/test_distributions.py`

**Step 1: Write the failing test**

```python
"""Tests for rolling sector distribution computation."""

import pytest

from margin_engine.healing.distributions import compute_sector_distributions
from margin_engine.healing.models import SectorDistribution


class TestComputeSectorDistributions:
    def test_basic_computation(self):
        """Compute median and MAD for a single field across tickers."""
        ticker_data = {
            "AAPL": {"income_statement.gross_margin": 0.45},
            "MSFT": {"income_statement.gross_margin": 0.70},
            "GOOGL": {"income_statement.gross_margin": 0.55},
            "META": {"income_statement.gross_margin": 0.80},
            "NVDA": {"income_statement.gross_margin": 0.65},
        }
        dists = compute_sector_distributions(
            ticker_field_values=ticker_data,
            sector="TECHNOLOGY",
            period="2026-Q1",
        )
        assert len(dists) == 1
        d = dists[0]
        assert d.sector == "TECHNOLOGY"
        assert d.field_path == "income_statement.gross_margin"
        assert d.median == pytest.approx(0.65, abs=0.01)
        assert d.n_observations == 5
        assert d.mad > 0

    def test_multiple_fields(self):
        """Each unique field gets its own distribution."""
        ticker_data = {
            "AAPL": {"income_statement.gross_margin": 0.45, "balance_sheet.debt_to_equity": 1.5},
            "MSFT": {"income_statement.gross_margin": 0.70, "balance_sheet.debt_to_equity": 0.5},
        }
        dists = compute_sector_distributions(ticker_data, "TECHNOLOGY", "2026-Q1")
        assert len(dists) == 2
        field_paths = {d.field_path for d in dists}
        assert field_paths == {"income_statement.gross_margin", "balance_sheet.debt_to_equity"}

    def test_single_ticker_returns_zero_mad(self):
        """With one ticker, MAD is 0 (detection will skip this field)."""
        ticker_data = {"AAPL": {"income_statement.gross_margin": 0.45}}
        dists = compute_sector_distributions(ticker_data, "TECHNOLOGY", "2026-Q1")
        assert dists[0].mad == 0.0

    def test_empty_input(self):
        dists = compute_sector_distributions({}, "TECHNOLOGY", "2026-Q1")
        assert dists == []

    def test_uses_raw_values_only(self):
        """Distribution is computed from the values as given (assumed raw, not corrected)."""
        # This is a contract test — the caller is responsible for passing raw values
        ticker_data = {
            "A": {"f": 10.0},
            "B": {"f": 20.0},
            "C": {"f": 30.0},
        }
        dists = compute_sector_distributions(ticker_data, "TECH", "Q1")
        assert dists[0].median == pytest.approx(20.0)
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest engine/tests/healing/test_distributions.py -v`
Expected: FAIL with `ImportError`

**Step 3: Write minimal implementation**

Create `engine/src/margin_engine/healing/distributions.py`:

```python
"""Rolling sector distribution computation for the healing layer.

Computes per-field median and MAD across all tickers in a sector.
These distributions are used by Tier 2 and Tier 3 detection.

CRITICAL: Distributions must be computed from RAW data only, never
from corrected data. This prevents the feedback loop described in
the design doc (Section 5, Failure Mode 3).
"""

from __future__ import annotations

import statistics
from collections import defaultdict

from margin_engine.healing.models import SectorDistribution


def _compute_mad(values: list[float]) -> float:
    """Compute Median Absolute Deviation."""
    if len(values) < 2:
        return 0.0
    med = statistics.median(values)
    return statistics.median(abs(v - med) for v in values)


def compute_sector_distributions(
    ticker_field_values: dict[str, dict[str, float]],
    sector: str,
    period: str,
) -> list[SectorDistribution]:
    """Compute rolling sector distributions from raw ticker data.

    Args:
        ticker_field_values: Mapping of ticker -> {field_path: raw_value}.
        sector: GICS sector name.
        period: Period label (e.g., "2026-Q1").

    Returns:
        List of SectorDistribution, one per unique field_path.
    """
    if not ticker_field_values:
        return []

    # Group values by field_path
    field_values: dict[str, list[float]] = defaultdict(list)
    for ticker_values in ticker_field_values.values():
        for field_path, value in ticker_values.items():
            field_values[field_path].append(value)

    distributions: list[SectorDistribution] = []
    for field_path, values in sorted(field_values.items()):
        distributions.append(SectorDistribution(
            sector=sector,
            field_path=field_path,
            median=statistics.median(values),
            mad=_compute_mad(values),
            n_observations=len(values),
            period=period,
        ))

    return distributions
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest engine/tests/healing/test_distributions.py -v`
Expected: All 5 tests PASS

**Step 5: Commit**

```bash
git add engine/src/margin_engine/healing/distributions.py engine/tests/healing/test_distributions.py
git commit -m "feat(engine): add sector distribution computation for healing layer"
```

---

### Task 11: Integration Test — Full Healing Pipeline End-to-End

**Files:**
- Test: `engine/tests/healing/test_integration.py`

**Step 1: Write the integration test**

```python
"""End-to-end integration test for the full healing pipeline."""

from decimal import Decimal

import pytest

from margin_engine.healing.distributions import compute_sector_distributions
from margin_engine.healing.models import (
    CorrectionMethod,
    DetectionSeverity,
    HealingConfig,
)
from margin_engine.healing.pipeline import HealingPipeline
from margin_engine.models.financial import (
    BalanceSheet,
    CashFlowStatement,
    FinancialPeriod,
    IncomeStatement,
)


def _make_period(revenue: int = 100_000, shares: int = 1_000_000) -> FinancialPeriod:
    return FinancialPeriod(
        period_end="2024-12-31",
        filing_date="2024-12-31",
        current_income=IncomeStatement(
            revenue=Decimal(str(revenue)),
            cost_of_revenue=Decimal(str(int(revenue * 0.55))),
            gross_profit=Decimal(str(int(revenue * 0.45))),
            ebit=Decimal(str(int(revenue * 0.20))),
            net_income=Decimal(str(int(revenue * 0.15))),
            shares_outstanding=shares,
        ),
        current_balance=BalanceSheet(
            total_assets=Decimal(str(int(revenue * 2))),
            total_liabilities=Decimal(str(int(revenue * 0.8))),
            total_equity=Decimal(str(int(revenue * 1.2))),
            shares_outstanding=shares,
        ),
        current_cash_flow=CashFlowStatement(
            operating_cash_flow=Decimal(str(int(revenue * 0.20))),
            capital_expenditures=Decimal(str(int(-revenue * 0.05))),
        ),
    )


class TestFullPipelineIntegration:
    def test_clean_universe_no_corrections(self):
        """A clean 5-ticker universe produces zero corrections."""
        tickers = {
            "AAPL": _make_period(100_000),
            "MSFT": _make_period(120_000),
            "GOOGL": _make_period(90_000),
            "META": _make_period(110_000),
            "NVDA": _make_period(95_000),
        }

        # Build distributions from raw data
        raw_field_values = {}
        for ticker, period in tickers.items():
            raw_field_values[ticker] = {
                "income_statement.gross_margin": period.current_income.gross_margin,
            }
        sector_dists = compute_sector_distributions(raw_field_values, "TECHNOLOGY", "2026-Q1")

        pipeline = HealingPipeline(config=HealingConfig())
        for ticker, period in tickers.items():
            result = pipeline.heal(
                period=period,
                sector="TECHNOLOGY",
                sector_distributions=sector_dists,
                prior_sector_distributions=sector_dists,
                ticker_history={},
                secondary_values={},
                prior_valid_values={},
                sector_ticker_count=5,
                sector_flagged_tickers=set(),
            )
            assert len(result.corrections) == 0
            assert result.excluded is False

    def test_tier1_detection_with_l1_correction(self):
        """Negative revenue detected by Tier 1, corrected via L1 substitute."""
        period = _make_period(revenue=-50_000)
        pipeline = HealingPipeline(config=HealingConfig())

        result = pipeline.heal(
            period=period,
            sector="TECHNOLOGY",
            sector_distributions=[],
            prior_sector_distributions=[],
            ticker_history={},
            secondary_values={"income_statement.revenue": 100_000.0},
            prior_valid_values={},
            sector_ticker_count=50,
            sector_flagged_tickers=set(),
        )

        assert any(d.severity == DetectionSeverity.IMPOSSIBLE for d in result.detections)
        revenue_corrections = [c for c in result.corrections
                               if c.field_path == "income_statement.revenue"]
        assert len(revenue_corrections) == 1
        assert revenue_corrections[0].correction_method == CorrectionMethod.L1_SUBSTITUTE
        assert revenue_corrections[0].corrected_value == 100_000.0

    def test_excluded_field_causes_exclusion(self):
        """Zero shares (excluded field) with no L1/L2 → ticker excluded."""
        period = _make_period(shares=0)
        pipeline = HealingPipeline(config=HealingConfig())

        result = pipeline.heal(
            period=period,
            sector="TECHNOLOGY",
            sector_distributions=[],
            prior_sector_distributions=[],
            ticker_history={},
            secondary_values={},
            prior_valid_values={},
            sector_ticker_count=50,
            sector_flagged_tickers=set(),
        )
        assert result.excluded is True

    def test_breadth_suspension_blocks_corrections(self):
        """When >15% of sector flagged, corrections are suspended."""
        period = _make_period(revenue=-50_000)
        pipeline = HealingPipeline(config=HealingConfig())

        result = pipeline.heal(
            period=period,
            sector="TECHNOLOGY",
            sector_distributions=[],
            prior_sector_distributions=[],
            ticker_history={},
            secondary_values={"income_statement.revenue": 100_000.0},
            prior_valid_values={},
            sector_ticker_count=10,
            sector_flagged_tickers={"A", "B", "C"},  # 30% > 15%
        )
        assert result.breadth_suspended is True
        assert len(result.corrections) == 0
        assert len(result.detections) >= 1
```

**Step 2: Run the integration test**

Run: `uv run pytest engine/tests/healing/test_integration.py -v`
Expected: All 4 tests PASS

**Step 3: Run the full engine test suite to verify no regressions**

Run: `uv run pytest engine/tests/ -v --timeout=120`
Expected: All existing tests + all new healing tests PASS

**Step 4: Commit**

```bash
git add engine/tests/healing/test_integration.py
git commit -m "test(engine): add end-to-end integration tests for healing pipeline"
```

---

### Task 12: Run Full Test Suite + Final Verification

**Step 1: Run all engine tests**

Run: `uv run pytest engine/tests/ -v --timeout=120`
Expected: All tests PASS (existing + ~45 new healing tests)

**Step 2: Run all API tests**

Run: `uv run pytest api/tests/ -v --timeout=120`
Expected: All tests PASS (existing + 2 new DB model tests + 2 scoring healing tests)

**Step 3: Run Alembic migration check**

Run: `uv run alembic heads`
Expected: Single head (no branch forks)

**Step 4: Commit any fixups if needed, then verify clean state**

```bash
git status
git log --oneline -10
```

---

## Dependency Graph

```
Task 1 (Models)
  ├── Task 2 (Tier 1 Detection) ──┐
  ├── Task 3 (Tier 2 Detection) ──┤
  └── Task 4 (Tier 3 Detection) ──┤
                                   ├── Task 5 (Correction Engine)
                                   ├── Task 6 (Circuit Breakers)
                                   └── Task 10 (Distributions)
                                         │
                              ┌───────────┤
                              ▼           ▼
                    Task 7 (Pipeline)   Task 8 (DB Models)
                              │           │
                              ▼           ▼
                    Task 9 (Wire into Scoring)
                              │
                              ▼
                    Task 11 (Integration Tests)
                              │
                              ▼
                    Task 12 (Full Verification)
```

**Parallelizable groups:**
- **Group A** (independent): Tasks 2, 3, 4, 6, 10 (all depend only on Task 1)
- **Group B** (after Group A): Tasks 5, 7, 8
- **Group C** (after Group B): Task 9
- **Group D** (after Group C): Tasks 11, 12
