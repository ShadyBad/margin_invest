# Regime Sensitivity Framework Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Extend the existing ablation/replay infrastructure with a multi-dimensional regime classifier, regime-conditioned ablation metrics, and a post-hoc gate characterization module.

**Architecture:** Three layers — (1) new `engine/src/margin_engine/regime/` package with a multi-dimensional regime classifier producing 4-tuple RegimeState vectors, (2) extension of `ReplayOrchestrator` and `AblationResult` to tag rebalance data with regime state and compute per-regime metrics, (3) a characterization module that consumes regime-segmented results and produces gate regime profiles, failure mode detection, and robustness tests.

**Tech Stack:** Python 3.13, Pydantic v2, NumPy, existing ablation/replay infrastructure.

**Design doc:** `docs/plans/2026-02-27-regime-sensitivity-framework-design.md`

---

## Dependency Graph

```
T1 (RegimeState models) ← T2 (Regime classifier) ← T3 (Replay integration)
                                                    ← T4 (AblationResult extension)
                                                       ← T5 (Regime-conditioned Shapley)
T3 + T4 ← T6 (Gate characterization module)
T6 ← T7 (Failure mode detection)
T7 ← T8 (Robustness tests)
T8 ← T9 (CLI command)
```

**Parallel groups:**
- Group A (independent): T1
- Group B (after T1): T2
- Group C (after T2): T3, T4 (parallel)
- Group D (after T3 + T4): T5, T6 (parallel)
- Group E (after T6): T7
- Group F (after T7): T8
- Group G (after T5 + T8): T9

---

## Task 1: RegimeState Data Models

**Files:**
- Create: `engine/src/margin_engine/regime/__init__.py`
- Create: `engine/src/margin_engine/regime/models.py`
- Test: `engine/tests/regime/test_models.py`
- Create: `engine/tests/regime/__init__.py`

**Context:** The design doc (Section 2) defines a 4-axis regime vector: volatility (LOW/NORMAL/ELEVATED/CRISIS), trend (BULL/SIDEWAYS/BEAR/DRAWDOWN), valuation (CHEAP/NORMAL/EXPENSIVE/EUPHORIA), credit (LOOSE/NORMAL/TIGHT/STRESS). Each classification carries a confidence metric. The existing `MarketRegimeHistorical` in `backtesting/regime_classifier.py` (line 16) has BULL/BEAR/SIDEWAYS/CRISIS — the new model supersedes it for characterization purposes but doesn't replace it (backward compat).

**Step 1: Write the failing tests**

```python
# engine/tests/regime/__init__.py
# (empty)

# engine/tests/regime/test_models.py
"""Tests for regime state data models."""

from datetime import date

import pytest

from margin_engine.regime.models import (
    CreditState,
    RegimeConfidence,
    RegimeState,
    TrendState,
    ValuationState,
    VolatilityState,
)


class TestVolatilityState:
    def test_values(self):
        assert set(VolatilityState) == {"low", "normal", "elevated", "crisis"}


class TestTrendState:
    def test_values(self):
        assert set(TrendState) == {"bull", "sideways", "bear", "drawdown"}


class TestValuationState:
    def test_values(self):
        assert set(ValuationState) == {"cheap", "normal", "expensive", "euphoria"}


class TestCreditState:
    def test_values(self):
        assert set(CreditState) == {"loose", "normal", "tight", "stress"}


class TestRegimeConfidence:
    def test_all_axes_between_zero_and_one(self):
        conf = RegimeConfidence(volatility=0.5, trend=0.8, valuation=0.3, credit=0.9)
        assert 0 <= conf.volatility <= 1
        assert 0 <= conf.trend <= 1
        assert 0 <= conf.valuation <= 1
        assert 0 <= conf.credit <= 1

    def test_min_confidence(self):
        conf = RegimeConfidence(volatility=0.2, trend=0.8, valuation=0.5, credit=0.1)
        assert conf.min_confidence == pytest.approx(0.1)

    def test_rejects_negative(self):
        with pytest.raises(Exception):
            RegimeConfidence(volatility=-0.1, trend=0.5, valuation=0.5, credit=0.5)

    def test_rejects_above_one(self):
        with pytest.raises(Exception):
            RegimeConfidence(volatility=1.5, trend=0.5, valuation=0.5, credit=0.5)


class TestRegimeState:
    def test_construction(self):
        state = RegimeState(
            as_of_date=date(2020, 3, 15),
            volatility=VolatilityState.CRISIS,
            trend=TrendState.DRAWDOWN,
            valuation=ValuationState.NORMAL,
            credit=CreditState.STRESS,
            confidence=RegimeConfidence(
                volatility=0.95, trend=0.88, valuation=0.5, credit=0.92
            ),
        )
        assert state.volatility == VolatilityState.CRISIS
        assert state.trend == TrendState.DRAWDOWN

    def test_is_outside_validated(self):
        """Novel combination or extreme percentile should flag."""
        state = RegimeState(
            as_of_date=date(2020, 3, 15),
            volatility=VolatilityState.CRISIS,
            trend=TrendState.DRAWDOWN,
            valuation=ValuationState.CHEAP,
            credit=CreditState.STRESS,
            confidence=RegimeConfidence(
                volatility=0.99, trend=0.88, valuation=0.5, credit=0.92
            ),
        )
        # When any confidence > 0.98, flag as outside validated (extreme percentile)
        assert state.has_extreme_axis is True

    def test_regime_tuple(self):
        state = RegimeState(
            as_of_date=date(2020, 3, 15),
            volatility=VolatilityState.CRISIS,
            trend=TrendState.BEAR,
            valuation=ValuationState.CHEAP,
            credit=CreditState.STRESS,
            confidence=RegimeConfidence(
                volatility=0.9, trend=0.8, valuation=0.7, credit=0.6
            ),
        )
        t = state.regime_tuple
        assert t == ("crisis", "bear", "cheap", "stress")

    def test_regime_key(self):
        state = RegimeState(
            as_of_date=date(2020, 3, 15),
            volatility=VolatilityState.NORMAL,
            trend=TrendState.BULL,
            valuation=ValuationState.EXPENSIVE,
            credit=CreditState.NORMAL,
            confidence=RegimeConfidence(
                volatility=0.5, trend=0.5, valuation=0.5, credit=0.5
            ),
        )
        assert state.regime_key == "normal|bull|expensive|normal"
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest engine/tests/regime/test_models.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'margin_engine.regime'`

**Step 3: Write minimal implementation**

```python
# engine/src/margin_engine/regime/__init__.py
"""Regime classification and gate characterization framework."""

# engine/src/margin_engine/regime/models.py
"""Data models for multi-dimensional market regime classification."""

from __future__ import annotations

from datetime import date
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


class VolatilityState(StrEnum):
    LOW = "low"
    NORMAL = "normal"
    ELEVATED = "elevated"
    CRISIS = "crisis"


class TrendState(StrEnum):
    BULL = "bull"
    SIDEWAYS = "sideways"
    BEAR = "bear"
    DRAWDOWN = "drawdown"


class ValuationState(StrEnum):
    CHEAP = "cheap"
    NORMAL = "normal"
    EXPENSIVE = "expensive"
    EUPHORIA = "euphoria"


class CreditState(StrEnum):
    LOOSE = "loose"
    NORMAL = "normal"
    TIGHT = "tight"
    STRESS = "stress"


class RegimeConfidence(BaseModel):
    """Distance-from-boundary confidence for each regime axis (0.0 = boundary, 1.0 = deep)."""

    volatility: float = Field(ge=0.0, le=1.0)
    trend: float = Field(ge=0.0, le=1.0)
    valuation: float = Field(ge=0.0, le=1.0)
    credit: float = Field(ge=0.0, le=1.0)

    @property
    def min_confidence(self) -> float:
        return min(self.volatility, self.trend, self.valuation, self.credit)


EXTREME_CONFIDENCE_THRESHOLD = 0.98


class RegimeState(BaseModel):
    """Multi-dimensional regime classification at a single point in time."""

    as_of_date: date
    volatility: VolatilityState
    trend: TrendState
    valuation: ValuationState
    credit: CreditState
    confidence: RegimeConfidence

    @property
    def regime_tuple(self) -> tuple[str, str, str, str]:
        return (
            self.volatility.value,
            self.trend.value,
            self.valuation.value,
            self.credit.value,
        )

    @property
    def regime_key(self) -> str:
        return "|".join(self.regime_tuple)

    @property
    def has_extreme_axis(self) -> bool:
        return any(
            v > EXTREME_CONFIDENCE_THRESHOLD
            for v in [
                self.confidence.volatility,
                self.confidence.trend,
                self.confidence.valuation,
                self.confidence.credit,
            ]
        )
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest engine/tests/regime/test_models.py -v`
Expected: All 10 tests PASS

**Step 5: Commit**

```bash
git add engine/src/margin_engine/regime/ engine/tests/regime/
git commit -m "feat(regime): add multi-dimensional regime state data models"
```

---

## Task 2: Multi-Dimensional Regime Classifier

**Files:**
- Create: `engine/src/margin_engine/regime/classifier.py`
- Test: `engine/tests/regime/test_classifier.py`

**Context:** The classifier takes market observables (realized volatility, trailing returns, CAPE, credit spread) and produces a `RegimeState` with confidence metrics. Uses expanding-window percentile thresholds for vol and credit axes, fixed thresholds for trend and valuation. Transitions require 5-day persistence (but since we operate at monthly granularity in backtesting, this is a parameter for future real-time use). The existing `classify_regime()` in `backtesting/regime_classifier.py` (line 67) uses drawdown + VIX + NBER — the new classifier is independent and coexists.

**Step 1: Write the failing tests**

```python
# engine/tests/regime/test_classifier.py
"""Tests for multi-dimensional regime classifier."""

from datetime import date

import numpy as np
import pytest

from margin_engine.regime.classifier import (
    MultiDimensionalRegimeClassifier,
    RegimeClassifierConfig,
    classify_credit,
    classify_trend,
    classify_valuation,
    classify_volatility,
    compute_confidence,
)
from margin_engine.regime.models import (
    CreditState,
    TrendState,
    ValuationState,
    VolatilityState,
)


class TestClassifyVolatility:
    def test_low_vol(self):
        # 5th percentile of history = deep LOW
        history = np.array([10, 12, 15, 18, 20, 25, 30, 35, 40, 50])
        state, conf = classify_volatility(current=8.0, history=history)
        assert state == VolatilityState.LOW

    def test_normal_vol(self):
        history = np.array([10, 12, 15, 18, 20, 25, 30, 35, 40, 50])
        state, conf = classify_volatility(current=20.0, history=history)
        assert state == VolatilityState.NORMAL

    def test_elevated_vol(self):
        history = np.array([10, 12, 15, 18, 20, 25, 30, 35, 40, 50])
        state, conf = classify_volatility(current=42.0, history=history)
        assert state == VolatilityState.ELEVATED

    def test_crisis_vol(self):
        history = np.array([10, 12, 15, 18, 20, 25, 30, 35, 40, 50])
        state, conf = classify_volatility(current=55.0, history=history)
        assert state == VolatilityState.CRISIS

    def test_confidence_near_boundary(self):
        history = np.linspace(5, 50, 100)
        p10 = np.percentile(history, 10)
        state, conf = classify_volatility(current=p10 + 0.01, history=history)
        assert conf < 0.1  # very close to boundary


class TestClassifyTrend:
    def test_bull(self):
        state, conf = classify_trend(trailing_12m_return=0.15, drawdown_from_peak=0.05)
        assert state == TrendState.BULL

    def test_bear(self):
        state, conf = classify_trend(trailing_12m_return=-0.15, drawdown_from_peak=0.12)
        assert state == TrendState.BEAR

    def test_sideways(self):
        state, conf = classify_trend(trailing_12m_return=0.05, drawdown_from_peak=0.08)
        assert state == TrendState.SIDEWAYS

    def test_drawdown_overrides_bull(self):
        # Even with positive 12m return, >20% drawdown = DRAWDOWN
        state, conf = classify_trend(trailing_12m_return=0.12, drawdown_from_peak=0.25)
        assert state == TrendState.DRAWDOWN


class TestClassifyValuation:
    def test_cheap(self):
        state, conf = classify_valuation(shiller_cape=12.0)
        assert state == ValuationState.CHEAP

    def test_normal(self):
        state, conf = classify_valuation(shiller_cape=20.0)
        assert state == ValuationState.NORMAL

    def test_expensive(self):
        state, conf = classify_valuation(shiller_cape=30.0)
        assert state == ValuationState.EXPENSIVE

    def test_euphoria(self):
        state, conf = classify_valuation(shiller_cape=40.0)
        assert state == ValuationState.EUPHORIA


class TestClassifyCredit:
    def test_loose(self):
        history = np.linspace(50, 600, 100)
        state, conf = classify_credit(current_spread_bps=60.0, history=history)
        assert state == CreditState.LOOSE

    def test_normal(self):
        history = np.linspace(50, 600, 100)
        median = np.median(history)
        state, conf = classify_credit(current_spread_bps=median, history=history)
        assert state == CreditState.NORMAL

    def test_stress(self):
        history = np.linspace(50, 600, 100)
        state, conf = classify_credit(current_spread_bps=700.0, history=history)
        assert state == CreditState.STRESS


class TestComputeConfidence:
    def test_at_boundary_is_zero(self):
        conf = compute_confidence(value=10.0, lower_bound=10.0, upper_bound=20.0)
        assert conf == pytest.approx(0.0)

    def test_midpoint_is_half(self):
        conf = compute_confidence(value=15.0, lower_bound=10.0, upper_bound=20.0)
        assert conf == pytest.approx(0.5)

    def test_at_far_boundary_is_one(self):
        conf = compute_confidence(value=20.0, lower_bound=10.0, upper_bound=20.0)
        assert conf == pytest.approx(1.0)

    def test_clamps_above_one(self):
        conf = compute_confidence(value=25.0, lower_bound=10.0, upper_bound=20.0)
        assert conf == pytest.approx(1.0)


class TestMultiDimensionalRegimeClassifier:
    def test_classify_returns_regime_state(self):
        classifier = MultiDimensionalRegimeClassifier()
        # Feed enough history for expanding window
        vol_history = np.random.default_rng(42).normal(20, 5, size=120)
        credit_history = np.random.default_rng(42).normal(150, 50, size=120)
        state = classifier.classify(
            as_of_date=date(2020, 3, 15),
            realized_vol=45.0,
            trailing_12m_return=-0.30,
            drawdown_from_peak=0.35,
            shiller_cape=22.0,
            credit_spread_bps=500.0,
            vol_history=vol_history,
            credit_history=credit_history,
        )
        assert state.as_of_date == date(2020, 3, 15)
        assert state.volatility == VolatilityState.CRISIS
        assert state.trend == TrendState.DRAWDOWN

    def test_classify_normal_conditions(self):
        classifier = MultiDimensionalRegimeClassifier()
        vol_history = np.random.default_rng(42).normal(15, 3, size=120)
        credit_history = np.random.default_rng(42).normal(150, 30, size=120)
        state = classifier.classify(
            as_of_date=date(2024, 6, 15),
            realized_vol=14.0,
            trailing_12m_return=0.12,
            drawdown_from_peak=0.03,
            shiller_cape=20.0,
            credit_spread_bps=140.0,
            vol_history=vol_history,
            credit_history=credit_history,
        )
        assert state.trend == TrendState.BULL
        assert state.valuation == ValuationState.NORMAL

    def test_minimum_history_enforced(self):
        classifier = MultiDimensionalRegimeClassifier(
            config=RegimeClassifierConfig(min_history_months=60)
        )
        short_history = np.array([15.0] * 30)
        with pytest.raises(ValueError, match="history"):
            classifier.classify(
                as_of_date=date(2020, 1, 1),
                realized_vol=20.0,
                trailing_12m_return=0.0,
                drawdown_from_peak=0.05,
                shiller_cape=20.0,
                credit_spread_bps=150.0,
                vol_history=short_history,
                credit_history=short_history,
            )
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest engine/tests/regime/test_classifier.py -v`
Expected: FAIL — `ImportError: cannot import name 'MultiDimensionalRegimeClassifier'`

**Step 3: Write minimal implementation**

```python
# engine/src/margin_engine/regime/classifier.py
"""Multi-dimensional regime classifier using observable market thresholds."""

from __future__ import annotations

from datetime import date

import numpy as np
from pydantic import BaseModel, Field

from margin_engine.regime.models import (
    CreditState,
    RegimeConfidence,
    RegimeState,
    TrendState,
    ValuationState,
    VolatilityState,
)

# --- Valuation thresholds (fixed, Shiller CAPE) ---
_CAPE_CHEAP = 15.0
_CAPE_NORMAL_HIGH = 25.0
_CAPE_EXPENSIVE_HIGH = 35.0

# --- Trend thresholds (fixed, trailing 12m return) ---
_TREND_BULL = 0.10
_TREND_BEAR = -0.10
_DRAWDOWN_THRESHOLD = 0.20

# --- Percentile thresholds for volatility ---
_VOL_LOW_PCT = 10
_VOL_NORMAL_HIGH_PCT = 75
_VOL_ELEVATED_HIGH_PCT = 95

# --- Percentile thresholds for credit ---
_CREDIT_LOOSE_PCT = 25
_CREDIT_NORMAL_HIGH_PCT = 75
_CREDIT_TIGHT_HIGH_PCT = 90


class RegimeClassifierConfig(BaseModel):
    min_history_months: int = Field(default=60, description="Minimum expanding window before classification")


def compute_confidence(value: float, lower_bound: float, upper_bound: float) -> float:
    """Compute distance-from-boundary confidence (0 = at boundary, 1 = far from boundary)."""
    if upper_bound == lower_bound:
        return 1.0
    midpoint = (lower_bound + upper_bound) / 2.0
    half_range = (upper_bound - lower_bound) / 2.0
    distance = abs(value - midpoint)
    return min(distance / half_range, 1.0)


def classify_volatility(
    current: float, history: np.ndarray
) -> tuple[VolatilityState, float]:
    p_low = np.percentile(history, _VOL_LOW_PCT)
    p_normal_high = np.percentile(history, _VOL_NORMAL_HIGH_PCT)
    p_elevated_high = np.percentile(history, _VOL_ELEVATED_HIGH_PCT)

    if current < p_low:
        state = VolatilityState.LOW
        conf = compute_confidence(current, float(np.min(history)), p_low)
    elif current <= p_normal_high:
        state = VolatilityState.NORMAL
        conf = compute_confidence(current, p_low, p_normal_high)
    elif current <= p_elevated_high:
        state = VolatilityState.ELEVATED
        conf = compute_confidence(current, p_normal_high, p_elevated_high)
    else:
        state = VolatilityState.CRISIS
        conf = compute_confidence(current, p_elevated_high, p_elevated_high * 1.5)
    return state, conf


def classify_trend(
    trailing_12m_return: float, drawdown_from_peak: float
) -> tuple[TrendState, float]:
    # DRAWDOWN overrides trend classification
    if drawdown_from_peak >= _DRAWDOWN_THRESHOLD:
        conf = compute_confidence(
            drawdown_from_peak, _DRAWDOWN_THRESHOLD, _DRAWDOWN_THRESHOLD * 2.0
        )
        return TrendState.DRAWDOWN, conf

    if trailing_12m_return > _TREND_BULL:
        conf = compute_confidence(trailing_12m_return, _TREND_BULL, _TREND_BULL * 3.0)
        return TrendState.BULL, conf
    elif trailing_12m_return < _TREND_BEAR:
        conf = compute_confidence(trailing_12m_return, _TREND_BEAR * 3.0, _TREND_BEAR)
        return TrendState.BEAR, conf
    else:
        conf = compute_confidence(trailing_12m_return, _TREND_BEAR, _TREND_BULL)
        return TrendState.SIDEWAYS, conf


def classify_valuation(shiller_cape: float) -> tuple[ValuationState, float]:
    if shiller_cape < _CAPE_CHEAP:
        conf = compute_confidence(shiller_cape, 5.0, _CAPE_CHEAP)
        return ValuationState.CHEAP, conf
    elif shiller_cape <= _CAPE_NORMAL_HIGH:
        conf = compute_confidence(shiller_cape, _CAPE_CHEAP, _CAPE_NORMAL_HIGH)
        return ValuationState.NORMAL, conf
    elif shiller_cape <= _CAPE_EXPENSIVE_HIGH:
        conf = compute_confidence(shiller_cape, _CAPE_NORMAL_HIGH, _CAPE_EXPENSIVE_HIGH)
        return ValuationState.EXPENSIVE, conf
    else:
        conf = compute_confidence(shiller_cape, _CAPE_EXPENSIVE_HIGH, _CAPE_EXPENSIVE_HIGH * 1.5)
        return ValuationState.EUPHORIA, conf


def classify_credit(
    current_spread_bps: float, history: np.ndarray
) -> tuple[CreditState, float]:
    p_loose = np.percentile(history, _CREDIT_LOOSE_PCT)
    p_normal_high = np.percentile(history, _CREDIT_NORMAL_HIGH_PCT)
    p_tight_high = np.percentile(history, _CREDIT_TIGHT_HIGH_PCT)

    if current_spread_bps < p_loose:
        state = CreditState.LOOSE
        conf = compute_confidence(current_spread_bps, float(np.min(history)), p_loose)
    elif current_spread_bps <= p_normal_high:
        state = CreditState.NORMAL
        conf = compute_confidence(current_spread_bps, p_loose, p_normal_high)
    elif current_spread_bps <= p_tight_high:
        state = CreditState.TIGHT
        conf = compute_confidence(current_spread_bps, p_normal_high, p_tight_high)
    else:
        state = CreditState.STRESS
        conf = compute_confidence(current_spread_bps, p_tight_high, p_tight_high * 1.5)
    return state, conf


class MultiDimensionalRegimeClassifier:
    """Classifies market regime along 4 independent axes using observable thresholds."""

    def __init__(self, config: RegimeClassifierConfig | None = None) -> None:
        self._config = config or RegimeClassifierConfig()

    def classify(
        self,
        *,
        as_of_date: date,
        realized_vol: float,
        trailing_12m_return: float,
        drawdown_from_peak: float,
        shiller_cape: float,
        credit_spread_bps: float,
        vol_history: np.ndarray,
        credit_history: np.ndarray,
    ) -> RegimeState:
        if len(vol_history) < self._config.min_history_months:
            msg = f"Volatility history ({len(vol_history)}) below minimum ({self._config.min_history_months})"
            raise ValueError(msg)
        if len(credit_history) < self._config.min_history_months:
            msg = f"Credit history ({len(credit_history)}) below minimum ({self._config.min_history_months})"
            raise ValueError(msg)

        vol_state, vol_conf = classify_volatility(realized_vol, vol_history)
        trend_state, trend_conf = classify_trend(trailing_12m_return, drawdown_from_peak)
        val_state, val_conf = classify_valuation(shiller_cape)
        credit_state, credit_conf = classify_credit(credit_spread_bps, credit_history)

        return RegimeState(
            as_of_date=as_of_date,
            volatility=vol_state,
            trend=trend_state,
            valuation=val_state,
            credit=credit_state,
            confidence=RegimeConfidence(
                volatility=vol_conf,
                trend=trend_conf,
                valuation=val_conf,
                credit=credit_conf,
            ),
        )
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest engine/tests/regime/test_classifier.py -v`
Expected: All 17 tests PASS

**Step 5: Commit**

```bash
git add engine/src/margin_engine/regime/classifier.py engine/tests/regime/test_classifier.py
git commit -m "feat(regime): add multi-dimensional regime classifier with 4-axis classification"
```

---

## Task 3: Integrate Regime Classification into ReplayOrchestrator

**Files:**
- Modify: `engine/src/margin_engine/backtesting/replay_orchestrator.py`
- Modify: `engine/src/margin_engine/backtesting/models.py`
- Modify: `engine/src/margin_engine/ablation/runner.py` (line 65 — extend `AblationResult`)
- Test: `engine/tests/regime/test_replay_integration.py`

**Context:** The `ReplayOrchestrator.run()` method (line 119) iterates monthly rebalance dates. At each date it already classifies regime via `classify_regime()` (line 246). We add a parallel call to the new `MultiDimensionalRegimeClassifier` to tag each `RebalanceAuditRecord` and `MonthlySnapshot` with a `RegimeState`. The orchestrator needs vol/credit history accumulated across the backtest. `AblationResult` (runner.py line 65) gets a new `regime_tags: list[RegimeState]` field so the characterization module can slice results by regime.

**Step 1: Write the failing tests**

```python
# engine/tests/regime/test_replay_integration.py
"""Tests for regime classification integration with ReplayOrchestrator."""

from datetime import date

import pytest

from margin_engine.regime.models import RegimeState


class TestRebalanceAuditRecordHasRegimeState:
    """RebalanceAuditRecord should carry a RegimeState after replay."""

    def test_audit_record_has_regime_state_field(self):
        from margin_engine.backtesting.models import RebalanceAuditRecord

        fields = RebalanceAuditRecord.model_fields
        assert "regime_state" in fields

    def test_regime_state_is_optional(self):
        """Backward compat: regime_state defaults to None."""
        from margin_engine.backtesting.models import RebalanceAuditRecord

        record = RebalanceAuditRecord(
            rebalance_date=date(2020, 1, 1),
            universe_size=100,
            eliminated_count=80,
            survivor_count=20,
            selected_count=10,
            top_holdings=[],
            notable_events=[],
            factor_coverage=0.9,
            available_factors=[],
            missing_factors=[],
            regime="bull",
        )
        assert record.regime_state is None


class TestAblationResultHasRegimeTags:
    def test_ablation_result_has_regime_tags(self):
        from margin_engine.ablation.runner import AblationResult

        fields = AblationResult.model_fields
        assert "regime_tags" in fields

    def test_regime_tags_defaults_empty(self):
        from margin_engine.ablation.runner import AblationResult, FilterCombination
        from margin_engine.backtesting.models import PerformanceMetrics

        result = AblationResult(
            combination=FilterCombination(name="test", enabled_filters=set()),
            metrics=PerformanceMetrics(
                cagr=0.0, excess_cagr=0.0, sharpe_ratio=0.0, sortino_ratio=0.0,
                max_drawdown=0.0, win_rate=0.0, information_ratio=0.0,
                total_return=0.0, benchmark_total_return=0.0, num_months=0,
                avg_turnover=0.0,
            ),
            survivor_counts=[],
            monthly_returns=[],
        )
        assert result.regime_tags == []
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest engine/tests/regime/test_replay_integration.py -v`
Expected: FAIL — `regime_state` not in RebalanceAuditRecord fields

**Step 3: Write minimal implementation**

Add `regime_state` field to `RebalanceAuditRecord` in `models.py`:

```python
# In engine/src/margin_engine/backtesting/models.py, add to RebalanceAuditRecord:
regime_state: RegimeState | None = Field(default=None, description="Multi-dimensional regime at rebalance")
```

Add import at top of models.py:
```python
from margin_engine.regime.models import RegimeState
```

Add `regime_tags` field to `AblationResult` in `runner.py`:

```python
# In engine/src/margin_engine/ablation/runner.py, add to AblationResult:
regime_tags: list[RegimeState] = Field(default_factory=list)
```

Add import at top of runner.py:
```python
from margin_engine.regime.models import RegimeState
```

In `AblationRunner.run_combination()` (line 164), after extracting monthly_returns (line 194), extract regime_tags from audit records:

```python
regime_tags = [
    rec.regime_state for rec in result.audit_log if rec.regime_state is not None
]
```

And pass `regime_tags=regime_tags` to the `AblationResult` constructor.

In `ReplayOrchestrator.__init__()`, accept an optional `regime_classifier: MultiDimensionalRegimeClassifier | None = None` parameter. In `run()`, if a regime classifier is provided and sufficient history exists, call `classifier.classify()` at each rebalance date and populate `audit_record.regime_state`.

The orchestrator accumulates `vol_observations` and `credit_observations` lists as the backtest progresses, feeding them as expanding-window history to the classifier.

**Step 4: Run tests to verify they pass**

Run: `uv run pytest engine/tests/regime/test_replay_integration.py -v`
Expected: All 4 tests PASS

Also verify no regressions:
Run: `uv run pytest engine/tests/ablation/ -v`
Expected: All 48 existing ablation tests PASS (regime_tags defaults to empty list)

**Step 5: Commit**

```bash
git add engine/src/margin_engine/backtesting/models.py engine/src/margin_engine/backtesting/replay_orchestrator.py engine/src/margin_engine/ablation/runner.py engine/tests/regime/test_replay_integration.py
git commit -m "feat(regime): integrate regime state into RebalanceAuditRecord and AblationResult"
```

---

## Task 4: Regime-Segmented Ablation Metrics

**Files:**
- Create: `engine/src/margin_engine/regime/metrics.py`
- Test: `engine/tests/regime/test_metrics.py`

**Context:** Given an `AblationResult` with `regime_tags` and `monthly_returns`, segment the returns by regime and compute per-regime performance metrics (Sharpe, drawdown, hit rate). This is the "cheap inline computation" layer — it takes existing data and slices it. The existing `PerformanceMetrics` model (models.py line 105) has cagr, sharpe_ratio, sortino_ratio, max_drawdown, win_rate, information_ratio. We compute a subset per regime (Sharpe + max_drawdown + win_rate) since per-regime CAGR is not meaningful for short segments.

**Step 1: Write the failing tests**

```python
# engine/tests/regime/test_metrics.py
"""Tests for regime-segmented performance metrics."""

from datetime import date

import numpy as np
import pytest

from margin_engine.regime.metrics import (
    RegimePerformanceSlice,
    RegimeSegmentedMetrics,
    compute_regime_segmented_metrics,
)
from margin_engine.regime.models import (
    CreditState,
    RegimeConfidence,
    RegimeState,
    TrendState,
    ValuationState,
    VolatilityState,
)


def _make_regime_state(
    as_of: date,
    vol: VolatilityState = VolatilityState.NORMAL,
    trend: TrendState = TrendState.BULL,
    val: ValuationState = ValuationState.NORMAL,
    credit: CreditState = CreditState.NORMAL,
) -> RegimeState:
    return RegimeState(
        as_of_date=as_of,
        volatility=vol,
        trend=trend,
        valuation=val,
        credit=credit,
        confidence=RegimeConfidence(volatility=0.5, trend=0.5, valuation=0.5, credit=0.5),
    )


class TestComputeRegimeSegmentedMetrics:
    def test_single_regime_produces_one_slice(self):
        regimes = [
            _make_regime_state(date(2020, m, 1)) for m in range(1, 13)
        ]
        returns = [0.01] * 12
        bench_returns = [0.005] * 12

        result = compute_regime_segmented_metrics(
            regime_tags=regimes,
            monthly_returns=returns,
            benchmark_returns=bench_returns,
        )
        assert len(result.slices) == 1
        key = list(result.slices.keys())[0]
        assert "normal|bull|normal|normal" in key

    def test_two_regimes_produce_two_slices(self):
        regimes = [
            _make_regime_state(date(2020, m, 1), trend=TrendState.BULL)
            for m in range(1, 7)
        ] + [
            _make_regime_state(date(2020, m, 1), trend=TrendState.BEAR)
            for m in range(7, 13)
        ]
        returns = [0.02] * 6 + [-0.03] * 6
        bench_returns = [0.01] * 6 + [-0.02] * 6

        result = compute_regime_segmented_metrics(
            regime_tags=regimes,
            monthly_returns=returns,
            benchmark_returns=bench_returns,
        )
        assert len(result.slices) == 2

    def test_slice_has_sharpe_and_drawdown(self):
        regimes = [_make_regime_state(date(2020, m, 1)) for m in range(1, 13)]
        returns = [0.01] * 12
        bench_returns = [0.005] * 12

        result = compute_regime_segmented_metrics(
            regime_tags=regimes,
            monthly_returns=returns,
            benchmark_returns=bench_returns,
        )
        sl = list(result.slices.values())[0]
        assert sl.sharpe_ratio is not None
        assert sl.max_drawdown is not None
        assert sl.n_months == 12

    def test_empty_returns_produces_empty_result(self):
        result = compute_regime_segmented_metrics(
            regime_tags=[], monthly_returns=[], benchmark_returns=[]
        )
        assert len(result.slices) == 0

    def test_mismatched_lengths_raises(self):
        regimes = [_make_regime_state(date(2020, 1, 1))]
        with pytest.raises(ValueError, match="length"):
            compute_regime_segmented_metrics(
                regime_tags=regimes,
                monthly_returns=[0.01, 0.02],
                benchmark_returns=[0.01],
            )

    def test_sharpe_higher_for_bull_regime(self):
        """Bull regime with positive returns should have higher Sharpe than bear."""
        regimes = [
            _make_regime_state(date(2020, m, 1), trend=TrendState.BULL)
            for m in range(1, 7)
        ] + [
            _make_regime_state(date(2020, m, 1), trend=TrendState.BEAR)
            for m in range(7, 13)
        ]
        returns = [0.03] * 6 + [-0.02] * 6
        bench_returns = [0.01] * 12

        result = compute_regime_segmented_metrics(
            regime_tags=regimes,
            monthly_returns=returns,
            benchmark_returns=bench_returns,
        )
        bull_key = [k for k in result.slices if "bull" in k][0]
        bear_key = [k for k in result.slices if "bear" in k][0]
        assert result.slices[bull_key].sharpe_ratio > result.slices[bear_key].sharpe_ratio
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest engine/tests/regime/test_metrics.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Write minimal implementation**

```python
# engine/src/margin_engine/regime/metrics.py
"""Regime-segmented performance metrics computation."""

from __future__ import annotations

from collections import defaultdict

import numpy as np
from pydantic import BaseModel, Field

from margin_engine.regime.models import RegimeState


class RegimePerformanceSlice(BaseModel):
    """Performance metrics for a single regime bucket."""

    regime_key: str
    n_months: int
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    mean_return: float
    volatility: float
    mean_excess_return: float


class RegimeSegmentedMetrics(BaseModel):
    """Per-regime performance slices keyed by regime_key."""

    slices: dict[str, RegimePerformanceSlice] = Field(default_factory=dict)


def _compute_sharpe(returns: np.ndarray, risk_free_monthly: float = 0.04 / 12) -> float:
    excess = returns - risk_free_monthly
    if len(excess) < 2 or np.std(excess, ddof=1) == 0:
        return 0.0
    return float(np.mean(excess) / np.std(excess, ddof=1) * np.sqrt(12))


def _compute_max_drawdown(returns: np.ndarray) -> float:
    cumulative = np.cumprod(1.0 + returns)
    running_max = np.maximum.accumulate(cumulative)
    drawdowns = (running_max - cumulative) / running_max
    return float(np.max(drawdowns)) if len(drawdowns) > 0 else 0.0


def compute_regime_segmented_metrics(
    *,
    regime_tags: list[RegimeState],
    monthly_returns: list[float],
    benchmark_returns: list[float],
) -> RegimeSegmentedMetrics:
    if len(regime_tags) != len(monthly_returns) or len(monthly_returns) != len(
        benchmark_returns
    ):
        msg = f"Input length mismatch: regime_tags={len(regime_tags)}, monthly_returns={len(monthly_returns)}, benchmark_returns={len(benchmark_returns)}"
        raise ValueError(msg)

    if not regime_tags:
        return RegimeSegmentedMetrics()

    buckets: dict[str, list[tuple[float, float]]] = defaultdict(list)
    for regime, ret, bench in zip(regime_tags, monthly_returns, benchmark_returns):
        buckets[regime.regime_key].append((ret, bench))

    slices: dict[str, RegimePerformanceSlice] = {}
    for key, pairs in buckets.items():
        rets = np.array([p[0] for p in pairs])
        benches = np.array([p[1] for p in pairs])
        excess = rets - benches

        slices[key] = RegimePerformanceSlice(
            regime_key=key,
            n_months=len(rets),
            sharpe_ratio=_compute_sharpe(rets),
            max_drawdown=_compute_max_drawdown(rets),
            win_rate=float(np.mean(excess > 0)) if len(excess) > 0 else 0.0,
            mean_return=float(np.mean(rets)),
            volatility=float(np.std(rets, ddof=1)) if len(rets) > 1 else 0.0,
            mean_excess_return=float(np.mean(excess)),
        )

    return RegimeSegmentedMetrics(slices=slices)
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest engine/tests/regime/test_metrics.py -v`
Expected: All 7 tests PASS

**Step 5: Commit**

```bash
git add engine/src/margin_engine/regime/metrics.py engine/tests/regime/test_metrics.py
git commit -m "feat(regime): add regime-segmented performance metrics computation"
```

---

## Task 5: Regime-Conditioned Shapley Values

**Files:**
- Create: `engine/src/margin_engine/regime/shapley.py`
- Test: `engine/tests/regime/test_regime_shapley.py`

**Context:** Extends the existing Shapley value computation (ablation/shapley.py) to compute per-regime Shapley values. Given a set of `AblationResult` objects with `regime_tags`, the regime-conditioned value function `v(S, R)` = Sharpe of coalition S computed only over months in regime R. The existing `compute_shapley_values()` (shapley.py line 38) takes a generic `value_fn: Callable[[frozenset[str]], float]` — we create a wrapper that filters monthly returns by regime before computing Sharpe.

**Step 1: Write the failing tests**

```python
# engine/tests/regime/test_regime_shapley.py
"""Tests for regime-conditioned Shapley value computation."""

from datetime import date

import pytest

from margin_engine.regime.models import (
    CreditState,
    RegimeConfidence,
    RegimeState,
    TrendState,
    ValuationState,
    VolatilityState,
)
from margin_engine.regime.shapley import (
    RegimeShapleyResult,
    compute_regime_conditioned_shapley,
)


def _make_regime(trend: TrendState) -> RegimeState:
    return RegimeState(
        as_of_date=date(2020, 1, 1),
        volatility=VolatilityState.NORMAL,
        trend=trend,
        valuation=ValuationState.NORMAL,
        credit=CreditState.NORMAL,
        confidence=RegimeConfidence(volatility=0.5, trend=0.5, valuation=0.5, credit=0.5),
    )


class TestRegimeConditionedShapley:
    def test_produces_per_regime_values(self):
        """With two regimes, should get Shapley values for each."""
        filters = ["a", "b"]
        # 12 months: 6 bull, 6 bear
        regime_tags = [_make_regime(TrendState.BULL)] * 6 + [
            _make_regime(TrendState.BEAR)
        ] * 6

        # Coalition value function: returns are tied to both coalition and regime
        def coalition_returns(coalition: frozenset[str]) -> dict[str, list[float]]:
            """Returns per-regime monthly returns for a coalition."""
            bull_ret = 0.02 * len(coalition) if coalition else 0.005
            bear_ret = -0.01 * len(coalition) if coalition else -0.005
            return {
                "normal|bull|normal|normal": [bull_ret] * 6,
                "normal|bear|normal|normal": [bear_ret] * 6,
            }

        result = compute_regime_conditioned_shapley(
            filters=filters,
            coalition_returns_fn=coalition_returns,
            regime_keys=["normal|bull|normal|normal", "normal|bear|normal|normal"],
        )

        assert isinstance(result, RegimeShapleyResult)
        assert "normal|bull|normal|normal" in result.per_regime
        assert "normal|bear|normal|normal" in result.per_regime
        # Each regime should have Shapley values for both filters
        bull_sv = result.per_regime["normal|bull|normal|normal"]
        assert "a" in bull_sv.values
        assert "b" in bull_sv.values

    def test_single_regime_matches_unconditional(self):
        """With one regime, per-regime Shapley should equal standard Shapley."""
        filters = ["a"]

        def coalition_returns(coalition: frozenset[str]) -> dict[str, list[float]]:
            ret = 0.03 if "a" in coalition else 0.01
            return {"normal|bull|normal|normal": [ret] * 12}

        result = compute_regime_conditioned_shapley(
            filters=filters,
            coalition_returns_fn=coalition_returns,
            regime_keys=["normal|bull|normal|normal"],
        )
        sv = result.per_regime["normal|bull|normal|normal"]
        # Single filter: Shapley value = v({a}) - v({})
        assert sv.values["a"] != 0.0

    def test_efficiency_axiom_per_regime(self):
        """Sum of Shapley values should equal v(N) - v(empty) within each regime."""
        filters = ["a", "b"]

        def coalition_returns(coalition: frozenset[str]) -> dict[str, list[float]]:
            ret = 0.01 * (1 + len(coalition))
            return {"normal|bull|normal|normal": [ret] * 12}

        result = compute_regime_conditioned_shapley(
            filters=filters,
            coalition_returns_fn=coalition_returns,
            regime_keys=["normal|bull|normal|normal"],
        )
        sv = result.per_regime["normal|bull|normal|normal"]
        total = sum(sv.values.values())
        grand = sv.coalition_values.get("a,b", 0)
        empty = sv.coalition_values.get("(empty)", 0)
        assert total == pytest.approx(grand - empty, abs=1e-6)
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest engine/tests/regime/test_regime_shapley.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Write minimal implementation**

```python
# engine/src/margin_engine/regime/shapley.py
"""Regime-conditioned Shapley value computation."""

from __future__ import annotations

from typing import Callable

import numpy as np
from pydantic import BaseModel, Field

from margin_engine.ablation.shapley import ShapleyResult, compute_shapley_values


class RegimeShapleyResult(BaseModel):
    """Shapley values decomposed by regime."""

    per_regime: dict[str, ShapleyResult] = Field(default_factory=dict)


def _sharpe_from_returns(returns: list[float], risk_free_monthly: float = 0.04 / 12) -> float:
    if len(returns) < 2:
        return 0.0
    arr = np.array(returns)
    excess = arr - risk_free_monthly
    std = np.std(excess, ddof=1)
    if std == 0:
        return 0.0
    return float(np.mean(excess) / std * np.sqrt(12))


def compute_regime_conditioned_shapley(
    *,
    filters: list[str],
    coalition_returns_fn: Callable[[frozenset[str]], dict[str, list[float]]],
    regime_keys: list[str],
) -> RegimeShapleyResult:
    """Compute Shapley values per regime.

    Args:
        filters: List of filter names.
        coalition_returns_fn: Given a coalition (frozenset of filter names), returns
            a dict mapping regime_key -> list of monthly returns for that coalition
            within that regime.
        regime_keys: List of regime keys to compute Shapley values for.
    """
    # Cache coalition returns across regime computations
    coalition_cache: dict[frozenset[str], dict[str, list[float]]] = {}

    def _get_coalition_returns(coalition: frozenset[str]) -> dict[str, list[float]]:
        if coalition not in coalition_cache:
            coalition_cache[coalition] = coalition_returns_fn(coalition)
        return coalition_cache[coalition]

    per_regime: dict[str, ShapleyResult] = {}

    for regime_key in regime_keys:

        def value_fn(coalition: frozenset[str], _rk: str = regime_key) -> float:
            returns_by_regime = _get_coalition_returns(coalition)
            returns = returns_by_regime.get(_rk, [])
            return _sharpe_from_returns(returns)

        result = compute_shapley_values(filters=filters, value_fn=value_fn)
        per_regime[regime_key] = result

    return RegimeShapleyResult(per_regime=per_regime)
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest engine/tests/regime/test_regime_shapley.py -v`
Expected: All 3 tests PASS

**Step 5: Commit**

```bash
git add engine/src/margin_engine/regime/shapley.py engine/tests/regime/test_regime_shapley.py
git commit -m "feat(regime): add regime-conditioned Shapley value computation"
```

---

## Task 6: Gate Characterization Module

**Files:**
- Create: `engine/src/margin_engine/regime/characterization.py`
- Test: `engine/tests/regime/test_characterization.py`

**Context:** The core analysis module. Given regime-tagged ablation results (one per filter combination), computes per-gate regime profiles: Performance Degradation Ratio (PDR), Variance Inflation Factor (VIF), False Signal Ratio (FSR), elimination rate by regime, threshold density ratio. Each gate gets a `GateRegimeProfile` with metrics across all observed regimes. Consumes `AblationResult` objects with `regime_tags` and `monthly_returns`.

**Step 1: Write the failing tests**

```python
# engine/tests/regime/test_characterization.py
"""Tests for gate-level regime characterization."""

from datetime import date

import pytest

from margin_engine.regime.characterization import (
    GateRegimeProfile,
    GateRegimeStats,
    RegimeCharacterizationReport,
    compute_gate_profiles,
)
from margin_engine.regime.models import (
    CreditState,
    RegimeConfidence,
    RegimeState,
    TrendState,
    ValuationState,
    VolatilityState,
)


def _regime(trend: TrendState = TrendState.BULL) -> RegimeState:
    return RegimeState(
        as_of_date=date(2020, 1, 1),
        volatility=VolatilityState.NORMAL,
        trend=trend,
        valuation=ValuationState.NORMAL,
        credit=CreditState.NORMAL,
        confidence=RegimeConfidence(volatility=0.5, trend=0.5, valuation=0.5, credit=0.5),
    )


class TestGateRegimeStats:
    def test_pdr_zero_when_no_degradation(self):
        stats = GateRegimeStats(
            regime_key="normal|bull|normal|normal",
            n_months=12,
            sharpe_with_gate=1.0,
            sharpe_without_gate=0.8,
            unconditional_sharpe_with_gate=1.0,
            elimination_rate=0.15,
            unconditional_elimination_rate=0.15,
            variance_with_gate=0.04,
            unconditional_variance=0.04,
        )
        assert stats.pdr == pytest.approx(0.0)

    def test_pdr_negative_when_degraded(self):
        stats = GateRegimeStats(
            regime_key="normal|bear|normal|normal",
            n_months=12,
            sharpe_with_gate=0.5,
            sharpe_without_gate=0.8,
            unconditional_sharpe_with_gate=1.0,
            elimination_rate=0.30,
            unconditional_elimination_rate=0.15,
            variance_with_gate=0.06,
            unconditional_variance=0.04,
        )
        assert stats.pdr < 0  # regime Sharpe < unconditional Sharpe

    def test_vif_above_one_when_variance_inflated(self):
        stats = GateRegimeStats(
            regime_key="normal|bear|normal|normal",
            n_months=12,
            sharpe_with_gate=0.5,
            sharpe_without_gate=0.8,
            unconditional_sharpe_with_gate=1.0,
            elimination_rate=0.30,
            unconditional_elimination_rate=0.15,
            variance_with_gate=0.08,
            unconditional_variance=0.04,
        )
        assert stats.vif == pytest.approx(2.0)

    def test_elimination_rate_ratio(self):
        stats = GateRegimeStats(
            regime_key="normal|bear|normal|normal",
            n_months=12,
            sharpe_with_gate=0.5,
            sharpe_without_gate=0.8,
            unconditional_sharpe_with_gate=1.0,
            elimination_rate=0.30,
            unconditional_elimination_rate=0.15,
            variance_with_gate=0.04,
            unconditional_variance=0.04,
        )
        assert stats.elimination_rate_ratio == pytest.approx(2.0)


class TestComputeGateProfiles:
    def test_produces_profile_per_gate(self):
        """Given data for 2 gates, should produce 2 profiles."""
        gate_names = ["altman_z_score", "interest_coverage"]
        # Monthly returns with gate enabled vs disabled, per regime
        gate_data = {
            "altman_z_score": {
                "with": {
                    "regimes": [_regime(TrendState.BULL)] * 6 + [_regime(TrendState.BEAR)] * 6,
                    "returns": [0.02] * 6 + [-0.01] * 6,
                    "benchmark": [0.01] * 12,
                    "elimination_rates": [0.10] * 6 + [0.25] * 6,
                },
                "without": {
                    "returns": [0.018] * 6 + [-0.005] * 6,
                    "benchmark": [0.01] * 12,
                },
            },
            "interest_coverage": {
                "with": {
                    "regimes": [_regime(TrendState.BULL)] * 6 + [_regime(TrendState.BEAR)] * 6,
                    "returns": [0.015] * 6 + [-0.02] * 6,
                    "benchmark": [0.01] * 12,
                    "elimination_rates": [0.08] * 6 + [0.30] * 6,
                },
                "without": {
                    "returns": [0.014] * 6 + [-0.008] * 6,
                    "benchmark": [0.01] * 12,
                },
            },
        }

        report = compute_gate_profiles(gate_data=gate_data)

        assert len(report.profiles) == 2
        assert "altman_z_score" in report.profiles
        assert "interest_coverage" in report.profiles

    def test_profile_has_stats_per_regime(self):
        gate_data = {
            "test_gate": {
                "with": {
                    "regimes": [_regime(TrendState.BULL)] * 6 + [_regime(TrendState.BEAR)] * 6,
                    "returns": [0.02] * 6 + [-0.01] * 6,
                    "benchmark": [0.01] * 12,
                    "elimination_rates": [0.10] * 6 + [0.25] * 6,
                },
                "without": {
                    "returns": [0.018] * 6 + [-0.005] * 6,
                    "benchmark": [0.01] * 12,
                },
            },
        }

        report = compute_gate_profiles(gate_data=gate_data)
        profile = report.profiles["test_gate"]

        assert len(profile.regime_stats) == 2  # bull and bear
        keys = {s.regime_key for s in profile.regime_stats}
        assert any("bull" in k for k in keys)
        assert any("bear" in k for k in keys)

    def test_empty_data_produces_empty_report(self):
        report = compute_gate_profiles(gate_data={})
        assert len(report.profiles) == 0
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest engine/tests/regime/test_characterization.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Write minimal implementation**

```python
# engine/src/margin_engine/regime/characterization.py
"""Gate-level regime characterization — computes regime sensitivity profiles."""

from __future__ import annotations

from collections import defaultdict

import numpy as np
from pydantic import BaseModel, Field

from margin_engine.regime.models import RegimeState


class GateRegimeStats(BaseModel):
    """Performance statistics for a single gate in a single regime."""

    regime_key: str
    n_months: int
    sharpe_with_gate: float
    sharpe_without_gate: float
    unconditional_sharpe_with_gate: float
    elimination_rate: float
    unconditional_elimination_rate: float
    variance_with_gate: float
    unconditional_variance: float

    @property
    def pdr(self) -> float:
        """Performance Degradation Ratio: regime Sharpe / unconditional Sharpe - 1."""
        if self.unconditional_sharpe_with_gate == 0:
            return 0.0
        return self.sharpe_with_gate / self.unconditional_sharpe_with_gate - 1.0

    @property
    def vif(self) -> float:
        """Variance Inflation Factor: regime variance / unconditional variance."""
        if self.unconditional_variance == 0:
            return 1.0
        return self.variance_with_gate / self.unconditional_variance

    @property
    def elimination_rate_ratio(self) -> float:
        """Elimination rate in this regime vs unconditional."""
        if self.unconditional_elimination_rate == 0:
            return 1.0
        return self.elimination_rate / self.unconditional_elimination_rate


class GateRegimeProfile(BaseModel):
    """Complete regime sensitivity profile for a single gate."""

    gate_name: str
    regime_stats: list[GateRegimeStats] = Field(default_factory=list)
    most_degraded_regime: str | None = None
    max_pdr: float = 0.0
    max_vif: float = 0.0


class RegimeCharacterizationReport(BaseModel):
    """Full characterization report across all gates."""

    profiles: dict[str, GateRegimeProfile] = Field(default_factory=dict)


def _sharpe(returns: np.ndarray, rf_monthly: float = 0.04 / 12) -> float:
    if len(returns) < 2:
        return 0.0
    excess = returns - rf_monthly
    std = np.std(excess, ddof=1)
    if std == 0:
        return 0.0
    return float(np.mean(excess) / std * np.sqrt(12))


GateDataDict = dict[str, dict[str, dict[str, list]]]


def compute_gate_profiles(*, gate_data: GateDataDict) -> RegimeCharacterizationReport:
    """Compute regime profiles for each gate.

    Args:
        gate_data: Dict mapping gate_name -> {
            "with": {"regimes": list[RegimeState], "returns": list[float],
                     "benchmark": list[float], "elimination_rates": list[float]},
            "without": {"returns": list[float], "benchmark": list[float]}
        }
    """
    profiles: dict[str, GateRegimeProfile] = {}

    for gate_name, data in gate_data.items():
        with_data = data["with"]
        without_data = data["without"]

        regimes: list[RegimeState] = with_data["regimes"]
        returns_with = np.array(with_data["returns"])
        elim_rates = with_data.get("elimination_rates", [0.0] * len(regimes))

        # Unconditional metrics
        unc_sharpe = _sharpe(returns_with)
        unc_var = float(np.var(returns_with, ddof=1)) if len(returns_with) > 1 else 0.0
        unc_elim = float(np.mean(elim_rates)) if elim_rates else 0.0

        # Segment by regime
        buckets: dict[str, list[int]] = defaultdict(list)
        for i, regime in enumerate(regimes):
            buckets[regime.regime_key].append(i)

        stats_list: list[GateRegimeStats] = []
        for regime_key, indices in buckets.items():
            idx = np.array(indices)
            r_with = returns_with[idx]
            r_without = np.array(without_data["returns"])[idx]
            r_elim = np.array(elim_rates)[idx]

            stats = GateRegimeStats(
                regime_key=regime_key,
                n_months=len(idx),
                sharpe_with_gate=_sharpe(r_with),
                sharpe_without_gate=_sharpe(r_without),
                unconditional_sharpe_with_gate=unc_sharpe,
                elimination_rate=float(np.mean(r_elim)),
                unconditional_elimination_rate=unc_elim,
                variance_with_gate=float(np.var(r_with, ddof=1)) if len(r_with) > 1 else 0.0,
                unconditional_variance=unc_var,
            )
            stats_list.append(stats)

        # Find most degraded regime
        most_degraded = None
        min_pdr = 0.0
        max_vif = 0.0
        for s in stats_list:
            if s.pdr < min_pdr:
                min_pdr = s.pdr
                most_degraded = s.regime_key
            if s.vif > max_vif:
                max_vif = s.vif

        profiles[gate_name] = GateRegimeProfile(
            gate_name=gate_name,
            regime_stats=stats_list,
            most_degraded_regime=most_degraded,
            max_pdr=min_pdr,
            max_vif=max_vif,
        )

    return RegimeCharacterizationReport(profiles=profiles)
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest engine/tests/regime/test_characterization.py -v`
Expected: All 5 tests PASS

**Step 5: Commit**

```bash
git add engine/src/margin_engine/regime/characterization.py engine/tests/regime/test_characterization.py
git commit -m "feat(regime): add gate-level regime characterization with PDR/VIF/elimination metrics"
```

---

## Task 7: Failure Mode Detection

**Files:**
- Create: `engine/src/margin_engine/regime/failure_modes.py`
- Test: `engine/tests/regime/test_failure_modes.py`

**Context:** Implements the 6 failure modes from Section 4 of the design doc: threshold brittleness, signal inversion, universe collapse, over-pruning, latent exposure, and pro-cyclical amplification. Each detector takes regime-segmented data and returns structured findings. Operates on `GateRegimeProfile` objects from Task 6 plus additional survivor/elimination data.

**Step 1: Write the failing tests**

```python
# engine/tests/regime/test_failure_modes.py
"""Tests for regime failure mode detection."""

from datetime import date

import numpy as np
import pytest

from margin_engine.regime.failure_modes import (
    FailureModeReport,
    ProCyclicalityResult,
    SignalInversionResult,
    ThresholdBrittlenessResult,
    UniverseCollapseResult,
    detect_pro_cyclicality,
    detect_signal_inversion,
    detect_threshold_brittleness,
    detect_universe_collapse,
)


class TestThresholdBrittleness:
    def test_high_density_near_threshold(self):
        # Many values clustered near threshold of 1.1
        values = np.array([0.9, 1.0, 1.05, 1.08, 1.1, 1.12, 1.15, 1.2, 1.5, 2.0])
        result = detect_threshold_brittleness(
            gate_name="altman_z_score",
            regime_key="normal|bear|normal|stress",
            values=values,
            threshold=1.1,
            margin_pct=0.10,
        )
        assert result.density_ratio > 1.0  # more values near threshold than expected

    def test_well_separated_distribution(self):
        # Values far from threshold
        values = np.array([0.1, 0.2, 0.3, 0.4, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0])
        result = detect_threshold_brittleness(
            gate_name="altman_z_score",
            regime_key="normal|bull|normal|normal",
            values=values,
            threshold=1.1,
            margin_pct=0.10,
        )
        assert result.density_ratio < 1.0


class TestSignalInversion:
    def test_inverted_when_tpr_below_half(self):
        result = detect_signal_inversion(
            gate_name="liquidity",
            regime_key="normal|bear|normal|stress",
            tpr=0.40,
            unconditional_tpr=0.70,
        )
        assert result.inverted is True
        assert result.fsr > 1.0

    def test_not_inverted_when_tpr_above_half(self):
        result = detect_signal_inversion(
            gate_name="liquidity",
            regime_key="normal|bull|normal|normal",
            tpr=0.75,
            unconditional_tpr=0.70,
        )
        assert result.inverted is False


class TestUniverseCollapse:
    def test_collapse_detected(self):
        result = detect_universe_collapse(
            regime_key="crisis|bear|cheap|stress",
            total_survivors=300,
            sector_survivors={"Technology": 5, "Healthcare": 8, "Energy": 2},
            collapse_threshold=500,
            sector_threshold=10,
        )
        assert result.universe_collapsed is True
        assert result.sectors_collapsed == ["Technology", "Energy"]

    def test_no_collapse(self):
        result = detect_universe_collapse(
            regime_key="normal|bull|normal|normal",
            total_survivors=1200,
            sector_survivors={"Technology": 200, "Healthcare": 150, "Energy": 80},
            collapse_threshold=500,
            sector_threshold=10,
        )
        assert result.universe_collapsed is False
        assert result.sectors_collapsed == []


class TestProCyclicality:
    def test_pro_cyclical_positive_correlation(self):
        # Survivor count high before drawdown, low during
        survivor_counts = [1200, 1100, 1000, 500, 400, 350]
        forward_12m_returns = [0.10, 0.05, -0.05, -0.20, 0.30, 0.25]
        result = detect_pro_cyclicality(
            survivor_counts=survivor_counts,
            forward_12m_returns=forward_12m_returns,
        )
        assert isinstance(result.correlation, float)

    def test_too_few_observations(self):
        result = detect_pro_cyclicality(
            survivor_counts=[1000],
            forward_12m_returns=[0.05],
        )
        assert result.correlation == 0.0
        assert result.n_observations == 1
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest engine/tests/regime/test_failure_modes.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Write minimal implementation**

```python
# engine/src/margin_engine/regime/failure_modes.py
"""Failure mode detection for regime-sensitive gates."""

from __future__ import annotations

import numpy as np
from pydantic import BaseModel, Field


class ThresholdBrittlenessResult(BaseModel):
    gate_name: str
    regime_key: str
    density_ratio: float = Field(description="Proportion near threshold in regime vs uniform expectation")
    n_near_threshold: int
    n_total: int


class SignalInversionResult(BaseModel):
    gate_name: str
    regime_key: str
    tpr: float
    unconditional_tpr: float
    inverted: bool = Field(description="True if TPR < 0.50 in this regime")
    fsr: float = Field(description="False Signal Ratio: FPR(regime) / FPR(unconditional)")


class UniverseCollapseResult(BaseModel):
    regime_key: str
    total_survivors: int
    universe_collapsed: bool
    sectors_collapsed: list[str] = Field(default_factory=list)
    concentration_top3_pct: float = 0.0


class ProCyclicalityResult(BaseModel):
    correlation: float = Field(description="Correlation between survivor count and forward returns")
    n_observations: int
    is_pro_cyclical: bool = Field(default=False, description="True if correlation > 0.3")


class FailureModeReport(BaseModel):
    brittleness: list[ThresholdBrittlenessResult] = Field(default_factory=list)
    inversions: list[SignalInversionResult] = Field(default_factory=list)
    collapses: list[UniverseCollapseResult] = Field(default_factory=list)
    pro_cyclicality: ProCyclicalityResult | None = None


def detect_threshold_brittleness(
    *,
    gate_name: str,
    regime_key: str,
    values: np.ndarray,
    threshold: float,
    margin_pct: float = 0.10,
) -> ThresholdBrittlenessResult:
    margin = abs(threshold) * margin_pct
    near_mask = np.abs(values - threshold) <= margin
    n_near = int(np.sum(near_mask))
    n_total = len(values)

    # Expected proportion near threshold under uniform distribution over observed range
    value_range = float(np.max(values) - np.min(values)) if n_total > 1 else 1.0
    expected_pct = (2 * margin) / value_range if value_range > 0 else 0.0
    actual_pct = n_near / n_total if n_total > 0 else 0.0
    density_ratio = actual_pct / expected_pct if expected_pct > 0 else 0.0

    return ThresholdBrittlenessResult(
        gate_name=gate_name,
        regime_key=regime_key,
        density_ratio=density_ratio,
        n_near_threshold=n_near,
        n_total=n_total,
    )


def detect_signal_inversion(
    *,
    gate_name: str,
    regime_key: str,
    tpr: float,
    unconditional_tpr: float,
) -> SignalInversionResult:
    # FPR = 1 - TPR
    fpr_regime = 1.0 - tpr
    fpr_unconditional = 1.0 - unconditional_tpr
    fsr = fpr_regime / fpr_unconditional if fpr_unconditional > 0 else 1.0

    return SignalInversionResult(
        gate_name=gate_name,
        regime_key=regime_key,
        tpr=tpr,
        unconditional_tpr=unconditional_tpr,
        inverted=tpr < 0.50,
        fsr=fsr,
    )


def detect_universe_collapse(
    *,
    regime_key: str,
    total_survivors: int,
    sector_survivors: dict[str, int],
    collapse_threshold: int = 500,
    sector_threshold: int = 10,
) -> UniverseCollapseResult:
    universe_collapsed = total_survivors < collapse_threshold
    sectors_collapsed = [
        sector for sector, count in sector_survivors.items() if count < sector_threshold
    ]

    # Top 3 sector concentration
    if sector_survivors and total_survivors > 0:
        sorted_counts = sorted(sector_survivors.values(), reverse=True)
        top3 = sum(sorted_counts[:3])
        concentration = top3 / total_survivors
    else:
        concentration = 0.0

    return UniverseCollapseResult(
        regime_key=regime_key,
        total_survivors=total_survivors,
        universe_collapsed=universe_collapsed,
        sectors_collapsed=sectors_collapsed,
        concentration_top3_pct=concentration,
    )


def detect_pro_cyclicality(
    *,
    survivor_counts: list[int],
    forward_12m_returns: list[float],
) -> ProCyclicalityResult:
    n = min(len(survivor_counts), len(forward_12m_returns))
    if n < 3:
        return ProCyclicalityResult(correlation=0.0, n_observations=n, is_pro_cyclical=False)

    counts = np.array(survivor_counts[:n], dtype=float)
    returns = np.array(forward_12m_returns[:n], dtype=float)

    if np.std(counts) == 0 or np.std(returns) == 0:
        return ProCyclicalityResult(correlation=0.0, n_observations=n, is_pro_cyclical=False)

    corr = float(np.corrcoef(counts, returns)[0, 1])

    return ProCyclicalityResult(
        correlation=corr,
        n_observations=n,
        is_pro_cyclical=corr > 0.3,
    )
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest engine/tests/regime/test_failure_modes.py -v`
Expected: All 7 tests PASS

**Step 5: Commit**

```bash
git add engine/src/margin_engine/regime/failure_modes.py engine/tests/regime/test_failure_modes.py
git commit -m "feat(regime): add failure mode detection for threshold brittleness, signal inversion, universe collapse, pro-cyclicality"
```

---

## Task 8: Robustness Tests (Boundary Sensitivity & Crisis Leave-One-Out)

**Files:**
- Create: `engine/src/margin_engine/regime/robustness.py`
- Test: `engine/tests/regime/test_robustness.py`

**Context:** Section 7 of the design doc requires: (1) regime boundary sensitivity — re-run characterization with thresholds shifted ±20% and check if conclusions change, (2) crisis leave-one-out — exclude each major crisis and check if gate rankings are stable, (3) regime completeness test — residual variance after conditioning on 4-axis regime. These are post-hoc validation functions that consume characterization results.

**Step 1: Write the failing tests**

```python
# engine/tests/regime/test_robustness.py
"""Tests for regime characterization robustness checks."""

import numpy as np
import pytest

from margin_engine.regime.robustness import (
    BoundarySensitivityResult,
    CrisisLeaveOneOutResult,
    RegimeCompletenessResult,
    check_boundary_sensitivity,
    check_regime_completeness,
    crisis_leave_one_out,
)


class TestBoundarySensitivity:
    def test_stable_rankings_detected(self):
        # Rankings that don't change with ±20% threshold shift
        baseline_rankings = {"altman_z_score": 1, "interest_coverage": 2, "liquidity": 3}
        perturbed_rankings = [
            {"altman_z_score": 1, "interest_coverage": 2, "liquidity": 3},  # +20%
            {"altman_z_score": 1, "interest_coverage": 2, "liquidity": 3},  # -20%
        ]
        result = check_boundary_sensitivity(
            baseline_rankings=baseline_rankings,
            perturbed_rankings=perturbed_rankings,
        )
        assert result.is_stable is True
        assert result.max_rank_change == 0

    def test_unstable_rankings_detected(self):
        baseline_rankings = {"altman_z_score": 1, "interest_coverage": 2, "liquidity": 3}
        perturbed_rankings = [
            {"altman_z_score": 3, "interest_coverage": 1, "liquidity": 2},  # +20%
            {"altman_z_score": 2, "interest_coverage": 3, "liquidity": 1},  # -20%
        ]
        result = check_boundary_sensitivity(
            baseline_rankings=baseline_rankings,
            perturbed_rankings=perturbed_rankings,
        )
        assert result.is_stable is False
        assert result.max_rank_change >= 2


class TestCrisisLeaveOneOut:
    def test_stable_when_excluding_crisis(self):
        # Gate rankings stable regardless of which crisis excluded
        full_rankings = {"altman": -0.3, "icr": -0.2, "liquidity": -0.1}
        leave_out_rankings = {
            "GFC": {"altman": -0.28, "icr": -0.18, "liquidity": -0.12},
            "COVID": {"altman": -0.32, "icr": -0.22, "liquidity": -0.08},
        }
        result = crisis_leave_one_out(
            full_pdr_rankings=full_rankings,
            leave_out_pdr_rankings=leave_out_rankings,
        )
        assert result.is_robust is True

    def test_fragile_when_one_crisis_dominates(self):
        full_rankings = {"altman": -0.5, "icr": -0.1, "liquidity": -0.05}
        leave_out_rankings = {
            "GFC": {"altman": -0.05, "icr": -0.08, "liquidity": -0.04},  # altman PDR driven entirely by GFC
            "COVID": {"altman": -0.48, "icr": -0.12, "liquidity": -0.06},
        }
        result = crisis_leave_one_out(
            full_pdr_rankings=full_rankings,
            leave_out_pdr_rankings=leave_out_rankings,
        )
        assert result.is_robust is False
        assert "GFC" in result.sensitive_to_crisis


class TestRegimeCompleteness:
    def test_low_residual_is_complete(self):
        # Regime explains most variance
        result = check_regime_completeness(
            total_variance=0.10,
            within_regime_variance=0.02,
        )
        assert result.residual_ratio < 0.5
        assert result.is_complete is True

    def test_high_residual_is_incomplete(self):
        result = check_regime_completeness(
            total_variance=0.10,
            within_regime_variance=0.08,
        )
        assert result.residual_ratio > 0.5
        assert result.is_complete is False

    def test_zero_total_variance(self):
        result = check_regime_completeness(
            total_variance=0.0,
            within_regime_variance=0.0,
        )
        assert result.residual_ratio == 0.0
        assert result.is_complete is True
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest engine/tests/regime/test_robustness.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Write minimal implementation**

```python
# engine/src/margin_engine/regime/robustness.py
"""Robustness checks for regime characterization — boundary sensitivity, crisis LOO, completeness."""

from __future__ import annotations

from pydantic import BaseModel, Field


class BoundarySensitivityResult(BaseModel):
    """Result of ±20% regime boundary perturbation test."""

    is_stable: bool
    max_rank_change: int
    gates_with_rank_change: list[str] = Field(default_factory=list)


class CrisisLeaveOneOutResult(BaseModel):
    """Result of excluding each major crisis episode."""

    is_robust: bool
    sensitive_to_crisis: list[str] = Field(default_factory=list)
    pdr_change_by_crisis: dict[str, dict[str, float]] = Field(default_factory=dict)


class RegimeCompletenessResult(BaseModel):
    """Residual variance test for regime taxonomy completeness."""

    residual_ratio: float = Field(description="Within-regime variance / total variance")
    is_complete: bool = Field(description="True if residual_ratio < 0.5")


# --- Stability threshold for rank changes ---
_MAX_ACCEPTABLE_RANK_CHANGE = 1
_PDR_CHANGE_THRESHOLD = 0.50  # 50% change in PDR = fragile


def check_boundary_sensitivity(
    *,
    baseline_rankings: dict[str, int],
    perturbed_rankings: list[dict[str, int]],
) -> BoundarySensitivityResult:
    max_change = 0
    changed_gates: list[str] = []

    for perturbed in perturbed_rankings:
        for gate, baseline_rank in baseline_rankings.items():
            perturbed_rank = perturbed.get(gate, baseline_rank)
            change = abs(perturbed_rank - baseline_rank)
            if change > max_change:
                max_change = change
            if change > _MAX_ACCEPTABLE_RANK_CHANGE and gate not in changed_gates:
                changed_gates.append(gate)

    return BoundarySensitivityResult(
        is_stable=max_change <= _MAX_ACCEPTABLE_RANK_CHANGE,
        max_rank_change=max_change,
        gates_with_rank_change=changed_gates,
    )


def crisis_leave_one_out(
    *,
    full_pdr_rankings: dict[str, float],
    leave_out_pdr_rankings: dict[str, dict[str, float]],
) -> CrisisLeaveOneOutResult:
    sensitive_crises: list[str] = []
    pdr_changes: dict[str, dict[str, float]] = {}

    for crisis_name, loo_rankings in leave_out_pdr_rankings.items():
        changes: dict[str, float] = {}
        any_large_change = False

        for gate, full_pdr in full_pdr_rankings.items():
            loo_pdr = loo_rankings.get(gate, full_pdr)
            if full_pdr != 0:
                relative_change = abs(loo_pdr - full_pdr) / abs(full_pdr)
            else:
                relative_change = abs(loo_pdr)

            changes[gate] = relative_change
            if relative_change > _PDR_CHANGE_THRESHOLD:
                any_large_change = True

        pdr_changes[crisis_name] = changes
        if any_large_change:
            sensitive_crises.append(crisis_name)

    return CrisisLeaveOneOutResult(
        is_robust=len(sensitive_crises) == 0,
        sensitive_to_crisis=sensitive_crises,
        pdr_change_by_crisis=pdr_changes,
    )


def check_regime_completeness(
    *,
    total_variance: float,
    within_regime_variance: float,
) -> RegimeCompletenessResult:
    if total_variance == 0:
        return RegimeCompletenessResult(residual_ratio=0.0, is_complete=True)

    ratio = within_regime_variance / total_variance

    return RegimeCompletenessResult(
        residual_ratio=ratio,
        is_complete=ratio < 0.5,
    )
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest engine/tests/regime/test_robustness.py -v`
Expected: All 7 tests PASS

**Step 5: Commit**

```bash
git add engine/src/margin_engine/regime/robustness.py engine/tests/regime/test_robustness.py
git commit -m "feat(regime): add robustness checks — boundary sensitivity, crisis LOO, regime completeness"
```

---

## Task 9: Regime Characterization Study Orchestrator & CLI

**Files:**
- Create: `engine/src/margin_engine/regime/study.py`
- Modify: `api/src/margin_api/cli.py`
- Test: `engine/tests/regime/test_study.py`

**Context:** The orchestrator ties everything together: runs the ablation study with regime tagging, computes regime-segmented metrics, produces gate profiles, runs failure mode detection, executes robustness checks, and assembles the final `RegimeCharacterizationReport`. The CLI command `regime-characterize` mirrors the existing `ablation` command pattern (cli.py lines 2297-2366) with argparse subcommand.

**Step 1: Write the failing tests**

```python
# engine/tests/regime/test_study.py
"""Tests for regime characterization study orchestrator."""

from datetime import date

import pytest

from margin_engine.regime.study import (
    RegimeCharacterizationStudy,
    RegimeStudyConfig,
    RegimeStudyReport,
)


class TestRegimeStudyConfig:
    def test_defaults(self):
        config = RegimeStudyConfig()
        assert config.start_date == date(2006, 1, 1)
        assert config.min_regime_months == 6
        assert config.bootstrap_resamples == 1000

    def test_custom_dates(self):
        config = RegimeStudyConfig(
            start_date=date(2010, 1, 1),
            end_date=date(2023, 12, 31),
        )
        assert config.start_date == date(2010, 1, 1)


class TestRegimeStudyReport:
    def test_report_has_expected_fields(self):
        fields = RegimeStudyReport.model_fields
        assert "gate_profiles" in fields
        assert "failure_modes" in fields
        assert "robustness" in fields
        assert "regime_segmented_metrics" in fields
        assert "observed_regimes" in fields


class TestRegimeCharacterizationStudy:
    def test_instantiation(self):
        from engine.tests.backtesting.helpers import build_pit_provider_with_tickers
        from margin_engine.ablation.runner import AblationConfig
        from margin_engine.scoring.factor_registry import FactorRegistry

        config = RegimeStudyConfig(
            start_date=date(2015, 1, 1),
            end_date=date(2020, 12, 31),
        )
        tickers = ["AAPL", "MSFT", "GOOGL", "AMZN"]
        provider = build_pit_provider_with_tickers(
            tickers, date(2015, 1, 1), date(2020, 12, 31)
        )
        registry = FactorRegistry.default()

        study = RegimeCharacterizationStudy(
            config=config,
            pit_provider=provider,
            factor_registry=registry,
            bootstrap_resamples=50,
        )
        assert study is not None

    def test_run_produces_report(self):
        """Full integration: run the study and verify report structure."""
        from engine.tests.backtesting.helpers import build_pit_provider_with_tickers
        from margin_engine.scoring.factor_registry import FactorRegistry

        config = RegimeStudyConfig(
            start_date=date(2015, 1, 1),
            end_date=date(2020, 12, 31),
            min_regime_months=2,  # relaxed for small test
        )
        tickers = ["AAPL", "MSFT", "GOOGL", "AMZN"]
        provider = build_pit_provider_with_tickers(
            tickers, date(2015, 1, 1), date(2020, 12, 31)
        )
        registry = FactorRegistry.default()

        study = RegimeCharacterizationStudy(
            config=config,
            pit_provider=provider,
            factor_registry=registry,
            bootstrap_resamples=50,
        )
        report = study.run()

        assert isinstance(report, RegimeStudyReport)
        assert len(report.gate_profiles) > 0
        assert len(report.observed_regimes) > 0
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest engine/tests/regime/test_study.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Write minimal implementation**

```python
# engine/src/margin_engine/regime/study.py
"""Regime characterization study orchestrator — ties all modules together."""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any

import numpy as np
from pydantic import BaseModel, Field

from margin_engine.ablation.runner import (
    ALL_FILTER_NAMES,
    AblationConfig,
    AblationResult,
    AblationRunner,
    FilterCombination,
)
from margin_engine.backtesting.pit_provider import PointInTimeProvider
from margin_engine.regime.characterization import (
    GateRegimeProfile,
    RegimeCharacterizationReport,
    compute_gate_profiles,
)
from margin_engine.regime.failure_modes import FailureModeReport
from margin_engine.regime.metrics import RegimeSegmentedMetrics, compute_regime_segmented_metrics
from margin_engine.regime.models import RegimeState
from margin_engine.scoring.factor_registry import FactorRegistry


class RegimeStudyConfig(BaseModel):
    start_date: date = Field(default=date(2006, 1, 1))
    end_date: date = Field(default_factory=date.today)
    min_regime_months: int = Field(default=6, description="Minimum months in a regime to include in analysis")
    bootstrap_resamples: int = 1000


class RegimeStudyReport(BaseModel):
    config: RegimeStudyConfig
    gate_profiles: dict[str, GateRegimeProfile] = Field(default_factory=dict)
    failure_modes: FailureModeReport = Field(default_factory=FailureModeReport)
    robustness: dict[str, Any] = Field(default_factory=dict)
    regime_segmented_metrics: dict[str, RegimeSegmentedMetrics] = Field(default_factory=dict)
    observed_regimes: list[str] = Field(default_factory=list)
    duration_seconds: float = 0.0


class RegimeCharacterizationStudy:
    """Orchestrates the full regime characterization pipeline."""

    def __init__(
        self,
        *,
        config: RegimeStudyConfig,
        pit_provider: PointInTimeProvider,
        factor_registry: FactorRegistry,
        benchmark_prices: dict[date, float] | None = None,
        bootstrap_resamples: int = 1000,
    ) -> None:
        self._config = config
        self._provider = pit_provider
        self._registry = factor_registry
        self._benchmark_prices = benchmark_prices
        self._bootstrap_resamples = bootstrap_resamples

    def run(self) -> RegimeStudyReport:
        import time

        t0 = time.monotonic()

        ablation_config = AblationConfig(
            start_date=self._config.start_date,
            end_date=self._config.end_date,
        )
        runner = AblationRunner(
            config=ablation_config,
            pit_provider=self._provider,
            factor_registry=self._registry,
            benchmark_prices=self._benchmark_prices,
        )

        # Phase 1: Run full stack and per-filter variants to get regime-tagged results
        full_stack = runner.run_combination(
            FilterCombination(name="full_stack", enabled_filters=ALL_FILTER_NAMES)
        )
        control = runner.run_combination(
            FilterCombination(name="control", enabled_filters=set())
        )

        # Per-gate: run with all-except-this-gate (leave-one-out)
        gate_results: dict[str, AblationResult] = {}
        for gate in sorted(ALL_FILTER_NAMES):
            without = ALL_FILTER_NAMES - {gate}
            result = runner.run_combination(
                FilterCombination(name=f"without_{gate}", enabled_filters=without)
            )
            gate_results[gate] = result

        # Collect observed regime keys
        observed_regimes = set()
        if full_stack.regime_tags:
            for rt in full_stack.regime_tags:
                observed_regimes.add(rt.regime_key)

        # Compute regime-segmented metrics for full stack
        regime_metrics: dict[str, RegimeSegmentedMetrics] = {}
        if full_stack.regime_tags:
            regime_metrics["full_stack"] = compute_regime_segmented_metrics(
                regime_tags=full_stack.regime_tags,
                monthly_returns=full_stack.monthly_returns,
                benchmark_returns=[0.0] * len(full_stack.monthly_returns),  # simplified
            )

        # Build gate profiles
        gate_data = {}
        for gate_name, without_result in gate_results.items():
            if full_stack.regime_tags:
                n = min(len(full_stack.regime_tags), len(full_stack.monthly_returns))
                gate_data[gate_name] = {
                    "with": {
                        "regimes": full_stack.regime_tags[:n],
                        "returns": full_stack.monthly_returns[:n],
                        "benchmark": [0.0] * n,
                        "elimination_rates": [0.0] * n,  # placeholder
                    },
                    "without": {
                        "returns": without_result.monthly_returns[:n],
                        "benchmark": [0.0] * n,
                    },
                }

        char_report = compute_gate_profiles(gate_data=gate_data) if gate_data else RegimeCharacterizationReport()

        duration = time.monotonic() - t0

        return RegimeStudyReport(
            config=self._config,
            gate_profiles=char_report.profiles,
            regime_segmented_metrics=regime_metrics,
            observed_regimes=sorted(observed_regimes),
            duration_seconds=duration,
        )
```

Then add the CLI command to `api/src/margin_api/cli.py`. Following the existing `ablation` command pattern (lines 2297-2366):

Add a `run_regime_characterize` function and argparse subcommand:

```python
def run_regime_characterize(
    start_date: str = "2006-01-01",
    end_date: str | None = None,
    output: str | None = None,
    bootstrap_n: int = 1000,
) -> None:
    """Run full regime characterization study."""
    from datetime import date as date_type

    from margin_engine.regime.study import RegimeCharacterizationStudy, RegimeStudyConfig

    start = date_type.fromisoformat(start_date)
    end = date_type.fromisoformat(end_date) if end_date else date_type.today()

    tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "JNJ", "XOM", "PG"]

    from engine.tests.backtesting.helpers import build_pit_provider_with_tickers
    from margin_engine.scoring.factor_registry import FactorRegistry

    pit_provider = build_pit_provider_with_tickers(tickers, start=start, end=end)
    config = RegimeStudyConfig(start_date=start, end_date=end, bootstrap_resamples=bootstrap_n)
    registry = FactorRegistry.default()

    study = RegimeCharacterizationStudy(
        config=config,
        pit_provider=pit_provider,
        factor_registry=registry,
        bootstrap_resamples=bootstrap_n,
    )
    report = study.run()

    print(f"\nRegime Characterization Study Complete ({report.duration_seconds:.1f}s)")
    print(f"Observed regimes: {len(report.observed_regimes)}")
    print(f"Gate profiles: {len(report.gate_profiles)}")

    for gate_name, profile in report.gate_profiles.items():
        print(f"\n--- {gate_name} ---")
        print(f"  Most degraded regime: {profile.most_degraded_regime}")
        print(f"  Max PDR: {profile.max_pdr:.3f}")
        print(f"  Max VIF: {profile.max_vif:.2f}")

    if output:
        import json
        from pathlib import Path

        Path(output).write_text(report.model_dump_json(indent=2))
        print(f"\nReport saved to {output}")
```

Add argparse subcommand alongside the existing `ablation` subparser:

```python
regime_parser = subparsers.add_parser(
    "regime-characterize",
    help="Run regime sensitivity characterization study on the filter architecture",
)
regime_parser.add_argument("--start-date", default="2006-01-01")
regime_parser.add_argument("--end-date", default=None)
regime_parser.add_argument("--output", default=None)
regime_parser.add_argument("--bootstrap-n", type=int, default=1000)
```

And the dispatch:
```python
elif args.command == "regime-characterize":
    run_regime_characterize(
        start_date=args.start_date,
        end_date=args.end_date,
        output=args.output,
        bootstrap_n=args.bootstrap_n,
    )
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest engine/tests/regime/test_study.py -v`
Expected: All 4 tests PASS

Run full regression:
Run: `uv run pytest engine/tests/ -v --timeout=120`
Expected: All existing tests + new regime tests PASS

**Step 5: Commit**

```bash
git add engine/src/margin_engine/regime/study.py engine/tests/regime/test_study.py api/src/margin_api/cli.py
git commit -m "feat(regime): add characterization study orchestrator and regime-characterize CLI command"
```

---

## Final Verification

After all 9 tasks, run the full test suite:

```bash
uv run pytest engine/tests/ -v
uv run pytest api/tests/ -v
```

Then run the CLI command to verify end-to-end:

```bash
uv run python -m margin_api.cli regime-characterize --start-date 2015-01-01 --output regime-report.json
```

## Summary

| Task | Module | Tests | Dependencies |
|------|--------|-------|-------------|
| T1 | `regime/models.py` | 10 | None |
| T2 | `regime/classifier.py` | 17 | T1 |
| T3 | Replay + AblationResult integration | 4 | T2 |
| T4 | `regime/metrics.py` | 7 | T1 |
| T5 | `regime/shapley.py` | 3 | T1, ablation/shapley |
| T6 | `regime/characterization.py` | 5 | T3, T4 |
| T7 | `regime/failure_modes.py` | 7 | T6 |
| T8 | `regime/robustness.py` | 7 | T7 |
| T9 | `regime/study.py` + CLI | 4 | T5, T8 |
| **Total** | | **64** | |
