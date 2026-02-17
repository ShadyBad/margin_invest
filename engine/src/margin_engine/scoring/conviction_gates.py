"""Conviction gates — absolute quality thresholds that must pass for high-conviction ratings.

Track A (Compounder) gates enforce minimum compounder characteristics.
Track B (Mispricing) gates enforce minimum mispricing characteristics.
Stocks that fail absolute gates but pass percentile thresholds are capped at WATCHLIST.
"""

from __future__ import annotations

from pydantic import BaseModel


class ConvictionGateResult(BaseModel):
    """Result of checking absolute conviction gates."""

    passed: bool
    failures: list[str]


# ---------------------------------------------------------------------------
# Track A (Compounder) thresholds
# ---------------------------------------------------------------------------
_A_ROIC_MIN = 0.15
_A_CV_MAX = 0.30
_A_REINVESTMENT_MIN = 0.30
_A_PRICE_IV_MAX = 2.0  # "not above 2x" means <= 2.0
_A_COVERAGE_MIN = 0.85

# ---------------------------------------------------------------------------
# Track B (Mispricing) thresholds
# ---------------------------------------------------------------------------
_B_ROIC_FLOOR = 0.08
_B_PRICE_IV_MAX = 0.60
_B_NET_CASH_MIN = 0.50
_B_TANGIBLE_BOOK_MIN = 0.50
_B_CURRENT_RATIO_MIN = 2.0


def check_track_a_gates(
    roic_median: float,
    roic_cv: float,
    reinvestment_rate: float,
    price_to_iv_ratio: float,
    data_coverage: float,
) -> ConvictionGateResult:
    """Check absolute conviction gates for Track A (Compounder).

    Requirements:
        - 5yr median ROIC > 15%
        - ROIC CV < 0.30
        - Reinvestment Rate > 30%
        - Not trading above 2x intrinsic value (price/IV <= 2.0)
        - Data coverage > 85%
    """
    failures: list[str] = []

    if roic_median <= _A_ROIC_MIN:
        failures.append(f"ROIC median {roic_median:.1%} <= {_A_ROIC_MIN:.0%} minimum")

    if roic_cv >= _A_CV_MAX:
        failures.append(f"ROIC CV {roic_cv:.2f} >= {_A_CV_MAX:.2f} stability threshold")

    if reinvestment_rate <= _A_REINVESTMENT_MIN:
        failures.append(
            f"Reinvestment rate {reinvestment_rate:.1%} <= {_A_REINVESTMENT_MIN:.0%} minimum"
        )

    if price_to_iv_ratio > _A_PRICE_IV_MAX:
        failures.append(
            f"Valuation {price_to_iv_ratio:.2f}x intrinsic value exceeds {_A_PRICE_IV_MAX:.1f}x max"
        )

    if data_coverage <= _A_COVERAGE_MIN:
        failures.append(f"Data coverage {data_coverage:.0%} <= {_A_COVERAGE_MIN:.0%} minimum")

    return ConvictionGateResult(passed=len(failures) == 0, failures=failures)


def check_track_b_gates(
    roic_median: float,
    roic_improving: bool,
    price_to_iv_ratio: float,
    has_catalyst: bool,
    net_cash_pct: float,
    tangible_book_pct: float,
    current_ratio: float,
) -> ConvictionGateResult:
    """Check absolute conviction gates for Track B (Mispricing).

    Requirements:
        - Quality floor: 5yr median ROIC > 8% OR improving trajectory
        - Valuation depth: trading below 0.6x intrinsic value
        - Catalyst present
        - Downside floor: net_cash_pct > 50% OR tangible_book_pct > 50% OR current_ratio > 2.0
    """
    failures: list[str] = []

    quality_floor_met = roic_median > _B_ROIC_FLOOR or roic_improving
    if not quality_floor_met:
        failures.append(
            f"Quality floor not met: ROIC {roic_median:.1%} <= {_B_ROIC_FLOOR:.0%} "
            f"and not improving"
        )

    if price_to_iv_ratio >= _B_PRICE_IV_MAX:
        failures.append(
            f"Valuation depth insufficient: price/IV {price_to_iv_ratio:.2f} "
            f">= {_B_PRICE_IV_MAX:.2f} threshold"
        )

    if not has_catalyst:
        failures.append("No catalyst present")

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

    return ConvictionGateResult(passed=len(failures) == 0, failures=failures)
