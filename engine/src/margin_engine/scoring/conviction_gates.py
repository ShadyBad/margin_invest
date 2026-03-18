"""Conviction gates — absolute quality thresholds that must pass for high-conviction ratings.

Track A (Compounder) gates enforce minimum compounder characteristics.
Track B (Mispricing) gates enforce minimum mispricing characteristics.
Stocks that fail absolute gates but pass percentile thresholds are capped at MEDIUM.

ROIC-conditional reinvestment: Track A reinvestment requirement scales with ROIC tier.
Trajectory overrides: assets with sustained ROIC improvement can earn conditional passes.
"""

from __future__ import annotations

import math

from pydantic import BaseModel

from margin_engine.config.v3_scoring_config import ConvictionGateConfig


class ConvictionGateResult(BaseModel):
    """Result of checking absolute conviction gates."""

    passed: bool
    conditional: bool = False
    failures: list[str]


# ---------------------------------------------------------------------------
# Track A (Compounder) thresholds — backward-compat fallbacks
# ---------------------------------------------------------------------------
_A_ROIC_MIN = 0.15
_A_CV_MAX = 0.30
_A_REINVESTMENT_MIN = 0.30
_A_PRICE_IV_MAX = 2.0  # "not above 2x" means <= 2.0
_A_COVERAGE_MIN = 0.85

# ---------------------------------------------------------------------------
# Track B (Mispricing) thresholds — backward-compat fallbacks
# ---------------------------------------------------------------------------
_B_ROIC_FLOOR = 0.08
_B_PRICE_IV_MAX = 0.60
_B_NET_CASH_MIN = 0.50
_B_TANGIBLE_BOOK_MIN = 0.50
_B_CURRENT_RATIO_MIN = 2.0


def _check_trajectory_override(
    roic_quarterly: list[float],
    min_delta: float,
    min_periods: int,
) -> bool:
    """True if ROIC improved by *min_delta* for *min_periods* consecutive quarters.

    Filters NaN/Inf values with ``math.isfinite()`` before computing deltas.
    Uses a small epsilon (1e-9) for floating-point comparison tolerance.
    """
    eps = 1e-9
    clean = [v for v in roic_quarterly if math.isfinite(v)]
    if len(clean) < 2:
        return False

    consecutive = 0
    for i in range(1, len(clean)):
        delta = clean[i] - clean[i - 1]
        if delta >= min_delta - eps:
            consecutive += 1
            if consecutive >= min_periods:
                return True
        else:
            consecutive = 0
    return False


def _roic_conditional_reinvestment_required(
    roic_median: float,
    config: ConvictionGateConfig,
) -> float | None:
    """Return the reinvestment threshold for *roic_median*, or ``None`` for no requirement.

    Returns ``-1.0`` sentinel when ROIC is below the minimum tier (needs trajectory override).
    """
    if roic_median >= config.roic_exceptional:
        # Capital-light path — no reinvestment required
        return None
    if roic_median >= config.roic_strong:
        return config.reinvestment_strong
    if roic_median >= config.roic_adequate:
        return config.reinvestment_adequate
    if roic_median >= config.roic_minimum:
        return config.reinvestment_minimum
    # Below minimum — only trajectory can save this
    return -1.0


def check_track_a_gates(
    roic_median: float,
    roic_cv: float,
    reinvestment_rate: float,
    price_to_iv_ratio: float,
    data_coverage: float,
    roic_quarterly: list[float] | None = None,
    config: ConvictionGateConfig | None = None,
) -> ConvictionGateResult:
    """Check absolute conviction gates for Track A (Compounder).

    ROIC-conditional reinvestment tiers:
        - ROIC >= 25%: no reinvestment requirement (capital-light path)
        - ROIC 15-25%: reinvestment > 10%
        - ROIC 10-15%: reinvestment > 20%
        - ROIC 8-10%:  reinvestment > 30% (original behaviour preserved)
        - ROIC < 8%:   fail unless trajectory override -> conditional=True

    Other gates unchanged:
        - ROIC CV < 0.30
        - Not trading above 2x intrinsic value (price/IV <= 2.0)
        - Data coverage > 85%
    """
    if config is None:
        config = ConvictionGateConfig()

    failures: list[str] = []
    conditional = False

    # --- ROIC stability gate (unchanged) ---
    if roic_cv >= _A_CV_MAX:
        failures.append(f"ROIC CV {roic_cv:.2f} >= {_A_CV_MAX:.2f} stability threshold")

    # --- ROIC-conditional reinvestment gate ---
    required = _roic_conditional_reinvestment_required(roic_median, config)

    if required == -1.0:
        # Below minimum ROIC — check trajectory override
        if roic_quarterly and _check_trajectory_override(
            roic_quarterly, config.trajectory_min_delta, config.trajectory_min_periods
        ):
            conditional = True
        else:
            failures.append(
                f"ROIC median {roic_median:.1%} below {config.roic_minimum:.0%} minimum "
                f"with no trajectory override"
            )
    elif required is not None and reinvestment_rate <= required:
        failures.append(
            f"Reinvestment rate {reinvestment_rate:.1%} <= {required:.0%} minimum "
            f"(ROIC tier: {roic_median:.1%})"
        )
    # else: required is None -> capital-light, no reinvestment gate

    # --- Valuation gate (unchanged) ---
    if price_to_iv_ratio > _A_PRICE_IV_MAX:
        failures.append(
            f"Valuation {price_to_iv_ratio:.2f}x intrinsic value exceeds {_A_PRICE_IV_MAX:.1f}x max"
        )

    # --- Data coverage gate (unchanged) ---
    if data_coverage <= _A_COVERAGE_MIN:
        failures.append(f"Data coverage {data_coverage:.0%} <= {_A_COVERAGE_MIN:.0%} minimum")

    passed = len(failures) == 0
    # conditional only meaningful when passed
    return ConvictionGateResult(
        passed=passed,
        conditional=conditional and passed,
        failures=failures,
    )


def check_track_b_gates(
    roic_median: float,
    roic_improving: bool,
    price_to_iv_ratio: float,
    has_catalyst: bool,
    net_cash_pct: float,
    tangible_book_pct: float,
    current_ratio: float,
    roic_quarterly: list[float] | None = None,
    config: ConvictionGateConfig | None = None,
) -> ConvictionGateResult:
    """Check absolute conviction gates for Track B (Mispricing).

    Tightened quality floor:
        - ROIC >= 8%: PASS (unchanged)
        - ROIC 6-8%: must show 200bps+ improvement for 2+ consecutive quarters -> conditional
        - ROIC < 6%: hard FAIL (no trajectory saves this)

    Other gates unchanged:
        - Valuation depth: trading below 0.6x intrinsic value
        - Catalyst present
        - Downside floor: net_cash_pct > 50% OR tangible_book_pct > 50% OR current_ratio > 2.0
    """
    if config is None:
        config = ConvictionGateConfig()

    failures: list[str] = []
    conditional = False

    # --- Tightened quality floor ---
    if roic_median >= _B_ROIC_FLOOR:
        pass  # unconditional pass
    elif roic_median >= config.track_b_roic_hard_floor:
        # In the improving zone (6-8%) — must show meaningful trajectory
        if roic_quarterly and _check_trajectory_override(
            roic_quarterly,
            config.track_b_improving_min_delta,
            config.track_b_improving_min_periods,
        ):
            conditional = True
        else:
            failures.append(
                f"Quality floor not met: ROIC {roic_median:.1%} in "
                f"{config.track_b_roic_hard_floor:.0%}-{_B_ROIC_FLOOR:.0%} range "
                f"without sufficient trajectory improvement"
            )
    else:
        # Below hard floor — no trajectory can save
        failures.append(
            f"Quality hard floor not met: ROIC {roic_median:.1%} below "
            f"{config.track_b_roic_hard_floor:.0%} hard floor"
        )

    # --- Valuation depth (unchanged) ---
    if price_to_iv_ratio >= _B_PRICE_IV_MAX:
        failures.append(
            f"Valuation depth insufficient: price/IV {price_to_iv_ratio:.2f} "
            f">= {_B_PRICE_IV_MAX:.2f} threshold"
        )

    # --- Catalyst (unchanged) ---
    if not has_catalyst:
        failures.append("No catalyst present")

    # --- Downside floor (unchanged) ---
    downside_met = (
        net_cash_pct > _B_NET_CASH_MIN
        or tangible_book_pct > _B_TANGIBLE_BOOK_MIN
        or current_ratio > _B_CURRENT_RATIO_MIN
    )
    if not downside_met:
        failures.append(
            f"Downside floor not met: net_cash {net_cash_pct:.0%}, "
            f"tangible_book {tangible_book_pct:.0%}, current_ratio {current_ratio:.1f}"
        )

    passed = len(failures) == 0
    return ConvictionGateResult(
        passed=passed,
        conditional=conditional and passed,
        failures=failures,
    )
