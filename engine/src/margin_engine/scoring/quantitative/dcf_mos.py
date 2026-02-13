"""DCF Margin of Safety (Klarman/Buffett) value factor.

Estimates intrinsic value via a two-stage Discounted Cash Flow model
and computes the margin of safety relative to the current market cap.

Positive margin = undervalued, negative = overvalued.

Formula (Two-Stage DCF):
1. FCF_0 = current free cash flow (CFO + CapEx)
2. For t in 1..projection_years:
   projected_fcf_t = FCF_0 * (1 + growth_rate)^t
   pv_t = projected_fcf_t / (1 + discount_rate)^t
3. Terminal Value = FCF_0 * (1 + growth_rate)^n * (1 + terminal_growth_rate)
                    / (discount_rate - terminal_growth_rate)
4. PV of Terminal = Terminal Value / (1 + discount_rate)^n
5. Intrinsic Value = sum(pv_t) + PV of Terminal
6. Margin of Safety = (Intrinsic Value - Market Cap) / Intrinsic Value
"""

from __future__ import annotations

from decimal import Decimal

from margin_engine.models.financial import FinancialPeriod
from margin_engine.models.scoring import FactorScore

FACTOR_NAME = "dcf_margin_of_safety"


def dcf_margin_of_safety(
    period: FinancialPeriod,
    market_cap: Decimal,
    growth_rate: float,
    discount_rate: float,
    terminal_growth_rate: float = 0.025,
    projection_years: int = 10,
) -> FactorScore:
    """Compute DCF-based margin of safety for a single financial period.

    Returns a FactorScore with:
    - raw_value: margin of safety (positive = undervalued, negative = overvalued),
      or 0.0 for edge cases
    - percentile_rank: 0.0 (placeholder -- filled by composite scorer in Phase 6)
    - name: "dcf_margin_of_safety"
    """
    fcf_0 = period.current_cash_flow.free_cash_flow

    if fcf_0 <= 0:
        return FactorScore(
            name=FACTOR_NAME,
            raw_value=0.0,
            percentile_rank=0.0,
            detail=f"FCF={fcf_0}; negative/zero free cash flow, DCF undefined",
        )

    if market_cap <= 0:
        return FactorScore(
            name=FACTOR_NAME,
            raw_value=0.0,
            percentile_rank=0.0,
            detail=f"market_cap={market_cap}; invalid market cap, DCF undefined",
        )

    if discount_rate <= terminal_growth_rate:
        return FactorScore(
            name=FACTOR_NAME,
            raw_value=0.0,
            percentile_rank=0.0,
            detail=(
                f"discount_rate={discount_rate} <= terminal_growth_rate={terminal_growth_rate}"
                "; terminal value undefined"
            ),
        )

    # Stage 1: Present value of projected free cash flows
    fcf_0_float = float(fcf_0)
    pv_projected_sum = 0.0
    for t in range(1, projection_years + 1):
        projected_fcf = fcf_0_float * (1 + growth_rate) ** t
        pv = projected_fcf / (1 + discount_rate) ** t
        pv_projected_sum += pv

    # Stage 2: Terminal value and its present value
    final_year_fcf = fcf_0_float * (1 + growth_rate) ** projection_years
    terminal_value = final_year_fcf * (1 + terminal_growth_rate) / (
        discount_rate - terminal_growth_rate
    )
    pv_terminal = terminal_value / (1 + discount_rate) ** projection_years

    intrinsic_value = pv_projected_sum + pv_terminal

    if intrinsic_value <= 0:
        return FactorScore(
            name=FACTOR_NAME,
            raw_value=0.0,
            percentile_rank=0.0,
            detail=f"intrinsic_value={intrinsic_value:.2f}; non-positive, MoS undefined",
        )

    market_cap_float = float(market_cap)
    mos = (intrinsic_value - market_cap_float) / intrinsic_value

    return FactorScore(
        name=FACTOR_NAME,
        raw_value=mos,
        percentile_rank=0.0,
        detail=(
            f"FCF={fcf_0}"
            f"; PV_projected={pv_projected_sum:,.0f}"
            f"; terminal_value={terminal_value:,.0f}"
            f"; PV_terminal={pv_terminal:,.0f}"
            f"; intrinsic_value={intrinsic_value:,.0f}"
            f"; market_cap={market_cap}"
            f"; margin_of_safety={mos:.4f}"
        ),
    )
