"""Scenario-weighted intrinsic value — bear/base/bull DCF with confidence score.

Computes three DCF scenarios by varying growth rate and WACC:
- Bear: lower growth, higher WACC
- Base: as provided
- Bull: higher growth, lower WACC

Weighted IV = 0.25*bear + 0.50*base + 0.25*bull
Confidence = 1.0 - (bull - bear) / base (clamped to 0-1)
"""

from __future__ import annotations

from margin_engine.models.scoring import ScenarioIV


def _two_stage_dcf(
    fcf: float,
    growth: float,
    wacc: float,
    terminal_growth: float,
    projection_years: int = 10,
) -> float:
    """Two-stage DCF: projected FCF + terminal value."""
    if fcf <= 0 or wacc <= terminal_growth or wacc <= 0:
        return 0.0

    pv_sum = 0.0
    for t in range(1, projection_years + 1):
        projected = fcf * (1 + growth) ** t
        pv_sum += projected / (1 + wacc) ** t

    terminal_fcf = fcf * (1 + growth) ** projection_years
    terminal_value = terminal_fcf * (1 + terminal_growth) / (wacc - terminal_growth)
    pv_terminal = terminal_value / (1 + wacc) ** projection_years

    return pv_sum + pv_terminal


def compute_scenario_iv(
    base_fcf: float,
    base_growth: float,
    wacc: float,
    terminal_growth: float,
    shares_outstanding: int,
    growth_spread: float = 0.02,
    wacc_spread: float = 0.01,
    projection_years: int = 10,
) -> ScenarioIV:
    """Compute bear/base/bull intrinsic value with confidence score.

    Args:
        base_fcf: Current free cash flow (total, not per share).
        base_growth: Base-case FCF growth rate.
        wacc: Weighted average cost of capital.
        terminal_growth: Long-term terminal growth rate.
        shares_outstanding: Total shares outstanding.
        growth_spread: +/- applied to growth for bear/bull.
        wacc_spread: +/- applied to WACC for bear/bull.
        projection_years: DCF projection horizon.
    """
    if base_fcf <= 0 or shares_outstanding <= 0:
        return ScenarioIV(
            bear_iv=0.0, base_iv=0.0, bull_iv=0.0,
            weighted_iv=0.0, confidence=0.0, range_pct=0.0,
        )

    bear_total = _two_stage_dcf(
        base_fcf, base_growth - growth_spread, wacc + wacc_spread,
        terminal_growth, projection_years,
    )
    base_total = _two_stage_dcf(
        base_fcf, base_growth, wacc, terminal_growth, projection_years,
    )
    bull_total = _two_stage_dcf(
        base_fcf, base_growth + growth_spread, wacc - wacc_spread,
        terminal_growth, projection_years,
    )

    bear_iv = max(bear_total / shares_outstanding, 0.0)
    base_iv = max(base_total / shares_outstanding, 0.0)
    bull_iv = max(bull_total / shares_outstanding, 0.0)

    weighted_iv = 0.25 * bear_iv + 0.50 * base_iv + 0.25 * bull_iv

    if base_iv > 0:
        range_pct = (bull_iv - bear_iv) / base_iv
        confidence = max(1.0 - range_pct, 0.0)
    else:
        range_pct = 0.0
        confidence = 0.0

    return ScenarioIV(
        bear_iv=bear_iv, base_iv=base_iv, bull_iv=bull_iv,
        weighted_iv=weighted_iv, confidence=min(confidence, 1.0),
        range_pct=range_pct,
    )
