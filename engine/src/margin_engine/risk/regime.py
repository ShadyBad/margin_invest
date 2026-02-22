"""Enhanced multi-dimensional regime detection.

Extends the existing CAPE-only regime with VIX, cross-asset
correlation, and credit spread dimensions. Uses worst-of (most
conservative) logic for the overall regime.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel

from margin_engine.scoring.market_regime import MarketRegime


class RegimeDimension(StrEnum):
    """Dimensions of market regime assessment."""

    VALUATION = "valuation"
    VOLATILITY = "volatility"
    CORRELATION = "correlation"
    CREDIT = "credit"


class RegimeLevel(StrEnum):
    """Regime stress level for each dimension."""

    CHEAP = "cheap"  # Only for VALUATION / low-vol
    NORMAL = "normal"
    ELEVATED = "elevated"
    EXTREME = "extreme"


class RegimeState(BaseModel):
    """Single-dimension regime assessment."""

    dimension: RegimeDimension
    level: RegimeLevel
    raw_value: float
    percentile: float | None = None  # Optional historical percentile


class CompositeRegime(BaseModel):
    """Multi-dimensional composite regime assessment."""

    states: list[RegimeState]
    overall: MarketRegime  # Worst-of all dimensions, mapped to existing enum
    risk_budget_multiplier: float  # 0.5 (EXTREME) to 1.2 (CHEAP)
    kappa_adjustment: float  # Multiplier for optimizer risk aversion


# ---------------------------------------------------------------------------
# Single-dimension detectors
# ---------------------------------------------------------------------------


def detect_valuation_regime(cape: float) -> RegimeState:
    """Detect valuation regime from Shiller CAPE ratio.

    Thresholds mirror :func:`margin_engine.scoring.market_regime.detect_regime`:
      <15 CHEAP, 15-25 NORMAL, 25-35 ELEVATED, >35 EXTREME
    """
    if cape < 15.0:
        level = RegimeLevel.CHEAP
    elif cape <= 25.0:
        level = RegimeLevel.NORMAL
    elif cape <= 35.0:
        level = RegimeLevel.ELEVATED
    else:
        level = RegimeLevel.EXTREME

    return RegimeState(dimension=RegimeDimension.VALUATION, level=level, raw_value=cape)


def detect_volatility_regime(vix: float) -> RegimeState:
    """Detect volatility regime from VIX level.

    <15 CHEAP (low vol favorable), 15-20 NORMAL, 20-30 ELEVATED, >30 EXTREME.
    """
    if vix < 15.0:
        level = RegimeLevel.CHEAP
    elif vix <= 20.0:
        level = RegimeLevel.NORMAL
    elif vix <= 30.0:
        level = RegimeLevel.ELEVATED
    else:
        level = RegimeLevel.EXTREME

    return RegimeState(dimension=RegimeDimension.VOLATILITY, level=level, raw_value=vix)


def detect_correlation_regime(cross_corr: float) -> RegimeState:
    """Detect correlation regime from average cross-asset correlation.

    <0.6 NORMAL (low correlation is favorable), 0.6-0.8 ELEVATED, >0.8 EXTREME.
    """
    if cross_corr <= 0.6:
        level = RegimeLevel.NORMAL
    elif cross_corr <= 0.8:
        level = RegimeLevel.ELEVATED
    else:
        level = RegimeLevel.EXTREME

    return RegimeState(dimension=RegimeDimension.CORRELATION, level=level, raw_value=cross_corr)


def detect_credit_regime(credit_spread_oas: float) -> RegimeState:
    """Detect credit regime from option-adjusted spread (OAS) in percentage points.

    <3.0 NORMAL (tight spreads favorable), 3.0-5.0 ELEVATED, >5.0 EXTREME.
    """
    if credit_spread_oas < 3.0:
        level = RegimeLevel.NORMAL
    elif credit_spread_oas <= 5.0:
        level = RegimeLevel.ELEVATED
    else:
        level = RegimeLevel.EXTREME

    return RegimeState(dimension=RegimeDimension.CREDIT, level=level, raw_value=credit_spread_oas)


# ---------------------------------------------------------------------------
# Severity mapping helpers
# ---------------------------------------------------------------------------

_LEVEL_SEVERITY: dict[RegimeLevel, int] = {
    RegimeLevel.CHEAP: 0,
    RegimeLevel.NORMAL: 1,
    RegimeLevel.ELEVATED: 2,
    RegimeLevel.EXTREME: 3,
}

_SEVERITY_TO_REGIME: dict[int, MarketRegime] = {
    0: MarketRegime.CHEAP,
    1: MarketRegime.NORMAL,
    2: MarketRegime.EXPENSIVE,
    3: MarketRegime.EUPHORIA,
}

_RISK_BUDGET: dict[MarketRegime, float] = {
    MarketRegime.CHEAP: 1.2,
    MarketRegime.NORMAL: 1.0,
    MarketRegime.EXPENSIVE: 0.7,
    MarketRegime.EUPHORIA: 0.5,
}

_KAPPA: dict[MarketRegime, float] = {
    MarketRegime.CHEAP: 0.7,
    MarketRegime.NORMAL: 1.0,
    MarketRegime.EXPENSIVE: 1.5,
    MarketRegime.EUPHORIA: 2.5,
}


def _level_to_severity(level: RegimeLevel) -> int:
    """Return integer severity for a :class:`RegimeLevel`."""
    return _LEVEL_SEVERITY[level]


def _severity_to_market_regime(severity: int) -> MarketRegime:
    """Map integer severity back to the existing :class:`MarketRegime` enum."""
    return _SEVERITY_TO_REGIME[severity]


def _regime_risk_budget(regime: MarketRegime) -> float:
    """Return risk-budget multiplier for *regime*."""
    return _RISK_BUDGET[regime]


def _regime_kappa_adjustment(regime: MarketRegime) -> float:
    """Return kappa (risk-aversion) multiplier for *regime*."""
    return _KAPPA[regime]


# ---------------------------------------------------------------------------
# Composite detector
# ---------------------------------------------------------------------------


def detect_composite_regime(
    cape: float,
    vix: float | None = None,
    cross_corr: float | None = None,
    credit_spread: float | None = None,
) -> CompositeRegime:
    """Detect composite market regime across multiple dimensions.

    Always computes VALUATION from *cape*. Optionally adds VOLATILITY
    (*vix*), CORRELATION (*cross_corr*), and CREDIT (*credit_spread*).
    Missing dimensions default to NORMAL and do not influence the
    overall regime.

    The overall regime is the **worst-of** (highest severity) across
    all active dimensions, mapped back to :class:`MarketRegime`.
    """
    states: list[RegimeState] = [detect_valuation_regime(cape)]

    if vix is not None:
        states.append(detect_volatility_regime(vix))
    if cross_corr is not None:
        states.append(detect_correlation_regime(cross_corr))
    if credit_spread is not None:
        states.append(detect_credit_regime(credit_spread))

    worst_severity = max(_level_to_severity(s.level) for s in states)
    overall = _severity_to_market_regime(worst_severity)

    return CompositeRegime(
        states=states,
        overall=overall,
        risk_budget_multiplier=_regime_risk_budget(overall),
        kappa_adjustment=_regime_kappa_adjustment(overall),
    )
