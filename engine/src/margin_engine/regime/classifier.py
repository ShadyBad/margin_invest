"""Multi-dimensional regime classifier.

Takes market observables (realized volatility, trailing returns, CAPE, credit
spread) and produces a :class:`RegimeState` with per-axis confidence metrics.

Each axis is classified independently using either expanding-window percentile
thresholds (volatility, credit) or fixed thresholds (valuation, trend).
Confidence measures how far the current reading is from the nearest bucket
boundary -- 0.0 right at the boundary, 1.0 deep inside the bucket.
"""

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

# ---------------------------------------------------------------------------
# Confidence helper
# ---------------------------------------------------------------------------


def compute_confidence(value: float, lower_bound: float, upper_bound: float) -> float:
    """Distance-from-boundary confidence metric.

    Returns 0.0 when *value* sits exactly on a boundary, trending toward 1.0
    as the value moves deeper into the bucket.  The metric is the minimum
    distance from either boundary, normalised by half the bucket width, then
    clamped to [0.0, 1.0].

    For degenerate cases where ``lower_bound == upper_bound`` the function
    returns 1.0 (there is no meaningful boundary to be near).
    """
    width = upper_bound - lower_bound
    if width == 0.0:
        return 1.0

    half_width = width / 2.0
    dist_from_lower = abs(value - lower_bound)
    dist_from_upper = abs(value - upper_bound)
    min_dist = min(dist_from_lower, dist_from_upper)
    return float(min(min_dist / half_width, 1.0))


def _tail_confidence(value: float, boundary: float, scale: float, *, side: str) -> float:
    """Confidence for open-ended tail buckets (only one meaningful boundary).

    *side* is ``"above"`` if the bucket extends above the boundary or
    ``"below"`` if it extends below.  Confidence grows linearly from 0.0 at
    the boundary to 1.0 at one *scale* unit away, then clamps.
    """
    if scale <= 0.0:
        return 1.0
    if side == "above":
        dist = value - boundary
    else:
        dist = boundary - value
    return float(min(max(dist / scale, 0.0), 1.0))


# ---------------------------------------------------------------------------
# Per-axis classifiers
# ---------------------------------------------------------------------------


def classify_volatility(current: float, history: np.ndarray) -> tuple[VolatilityState, float]:
    """Classify volatility using expanding-window percentile thresholds.

    Thresholds:
        LOW      current < P10
        NORMAL   P10 <= current < P75
        ELEVATED P75 <= current < P95
        CRISIS   current >= P95

    Returns ``(state, confidence)``.
    """
    p10 = float(np.percentile(history, 10))
    p75 = float(np.percentile(history, 75))
    p95 = float(np.percentile(history, 95))

    if current < p10:
        state = VolatilityState.LOW
        # Open-ended tail: confidence = distance from p10, scaled by (p75-p10) range
        tail_scale = p75 - p10  # use NORMAL bucket width as reference scale
        conf = _tail_confidence(current, p10, tail_scale, side="below")
    elif current < p75:
        state = VolatilityState.NORMAL
        conf = compute_confidence(current, p10, p75)
    elif current < p95:
        state = VolatilityState.ELEVATED
        conf = compute_confidence(current, p75, p95)
    else:
        state = VolatilityState.CRISIS
        # Open-ended tail: confidence = distance from p95, scaled by (p95-p75) range
        tail_scale = p95 - p75
        conf = _tail_confidence(current, p95, tail_scale, side="above")

    return state, conf


def classify_trend(
    trailing_12m_return: float, drawdown_from_peak: float
) -> tuple[TrendState, float]:
    """Classify trend from trailing return and current drawdown.

    DRAWDOWN overrides any return-based classification when
    ``drawdown_from_peak >= 0.20``.

    Fixed thresholds:
        BULL     return > +0.10
        BEAR     return < -0.10
        SIDEWAYS -0.10 <= return <= +0.10

    Returns ``(state, confidence)``.
    """
    # Drawdown override
    if drawdown_from_peak >= 0.20:
        # Confidence increases with depth of drawdown beyond threshold
        conf = compute_confidence(drawdown_from_peak, 0.20, 0.50)
        return TrendState.DRAWDOWN, conf

    ret = trailing_12m_return

    if ret > 0.10:
        state = TrendState.BULL
        # Bucket: (0.10, +inf); use [0.10, 0.40] as practical range
        conf = compute_confidence(ret, 0.10, 0.40)
    elif ret < -0.10:
        state = TrendState.BEAR
        # Bucket: (-inf, -0.10); use [-0.40, -0.10] as practical range
        conf = compute_confidence(ret, -0.40, -0.10)
    else:
        state = TrendState.SIDEWAYS
        # Bucket: [-0.10, 0.10]
        conf = compute_confidence(ret, -0.10, 0.10)

    return state, conf


def classify_valuation(shiller_cape: float) -> tuple[ValuationState, float]:
    """Classify valuation using fixed Shiller CAPE thresholds.

    Fixed thresholds:
        CHEAP     CAPE < 15
        NORMAL    15 <= CAPE < 25
        EXPENSIVE 25 <= CAPE < 35
        EUPHORIA  CAPE >= 35

    Returns ``(state, confidence)``.
    """
    # Bucket width for NORMAL/EXPENSIVE is 10.0 — use as scale for tails
    bucket_width = 10.0

    if shiller_cape < 15.0:
        state = ValuationState.CHEAP
        conf = _tail_confidence(shiller_cape, 15.0, bucket_width, side="below")
    elif shiller_cape < 25.0:
        state = ValuationState.NORMAL
        conf = compute_confidence(shiller_cape, 15.0, 25.0)
    elif shiller_cape < 35.0:
        state = ValuationState.EXPENSIVE
        conf = compute_confidence(shiller_cape, 25.0, 35.0)
    else:
        state = ValuationState.EUPHORIA
        conf = _tail_confidence(shiller_cape, 35.0, bucket_width, side="above")

    return state, conf


def classify_credit(current_spread_bps: float, history: np.ndarray) -> tuple[CreditState, float]:
    """Classify credit conditions using expanding-window percentile thresholds.

    Thresholds:
        LOOSE   current < P25
        NORMAL  P25 <= current < P75
        TIGHT   P75 <= current < P90
        STRESS  current >= P90

    Returns ``(state, confidence)``.
    """
    p25 = float(np.percentile(history, 25))
    p75 = float(np.percentile(history, 75))
    p90 = float(np.percentile(history, 90))

    if current_spread_bps < p25:
        state = CreditState.LOOSE
        # Open-ended tail: confidence = distance from p25, scaled by NORMAL width
        tail_scale = p75 - p25
        conf = _tail_confidence(current_spread_bps, p25, tail_scale, side="below")
    elif current_spread_bps < p75:
        state = CreditState.NORMAL
        conf = compute_confidence(current_spread_bps, p25, p75)
    elif current_spread_bps < p90:
        state = CreditState.TIGHT
        conf = compute_confidence(current_spread_bps, p75, p90)
    else:
        state = CreditState.STRESS
        # Open-ended tail: confidence = distance from p90, scaled by (p90-p75)
        tail_scale = p90 - p75
        conf = _tail_confidence(current_spread_bps, p90, tail_scale, side="above")

    return state, conf


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


class RegimeClassifierConfig(BaseModel):
    """Configuration for :class:`MultiDimensionalRegimeClassifier`."""

    min_history_months: int = Field(
        default=60,
        description="Minimum number of monthly observations required in history arrays.",
    )


# ---------------------------------------------------------------------------
# Main classifier
# ---------------------------------------------------------------------------


class MultiDimensionalRegimeClassifier:
    """Classifies the four-axis market regime from observable inputs.

    Parameters
    ----------
    config : RegimeClassifierConfig, optional
        Override default settings (e.g. ``min_history_months``).
    """

    def __init__(self, config: RegimeClassifierConfig | None = None) -> None:
        self.config = config or RegimeClassifierConfig()

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
        """Produce a :class:`RegimeState` from current market observables.

        Raises
        ------
        ValueError
            If either history array has fewer elements than
            ``config.min_history_months``.
        """
        min_len = self.config.min_history_months

        if len(vol_history) < min_len:
            msg = f"vol_history has {len(vol_history)} observations, need at least {min_len}"
            raise ValueError(msg)

        if len(credit_history) < min_len:
            msg = f"credit_history has {len(credit_history)} observations, need at least {min_len}"
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
