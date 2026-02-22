"""Piotroski F-Score quality factor.

The F-Score is a composite accounting signal (0-9) that measures
the financial strength of a company across profitability, leverage/
liquidity, and operating efficiency.

Academic reference: Piotroski (2000), "Value Investing: The Use of
Historical Financial Statement Information to Separate Winners from Losers."
"""

from __future__ import annotations

from margin_engine.models.financial import FinancialPeriod
from margin_engine.models.scoring import FactorScore

SIGNAL_NAMES = [
    "roa",
    "cfo",
    "roa_change",
    "accruals",
    "leverage",
    "liquidity",
    "dilution",
    "gross_margin",
    "asset_turnover",
]


def compute_f_score_signals(period: FinancialPeriod) -> dict[str, int]:
    """Compute individual F-Score signals.

    Returns a dict of signal_name -> 0 or 1.
    Signals requiring prior data return 0 if prior data is unavailable.
    """
    income = period.current_income
    balance = period.current_balance
    cash_flow = period.current_cash_flow

    total_assets = balance.total_assets
    net_income = income.net_income
    cfo = cash_flow.operating_cash_flow

    # 1. ROA: Net Income / Total Assets > 0
    roa_current = float(net_income / total_assets) if total_assets != 0 else 0.0
    roa = 1 if roa_current > 0 else 0

    # 2. Operating Cash Flow: CFO > 0
    cfo_signal = 1 if cfo > 0 else 0

    # 3. ROA Change: ROA_t > ROA_t-1 (requires prior)
    roa_change = 0
    if period.prior_income is not None and period.prior_balance is not None:
        prior_ta = period.prior_balance.total_assets
        if prior_ta != 0:
            roa_prior = float(period.prior_income.net_income / prior_ta)
            roa_change = 1 if roa_current > roa_prior else 0

    # 4. Accruals: CFO > Net Income
    accruals = 1 if cfo > net_income else 0

    # 5. Leverage Change: LT Debt/TA decreased YoY (requires prior)
    leverage = 0
    if period.prior_balance is not None:
        current_ltd_ta = (
            float((balance.long_term_debt or 0) / total_assets) if total_assets != 0 else 0.0
        )
        prior_ta = period.prior_balance.total_assets
        prior_ltd_ta = (
            float((period.prior_balance.long_term_debt or 0) / prior_ta) if prior_ta != 0 else 0.0
        )
        leverage = 1 if current_ltd_ta < prior_ltd_ta else 0

    # 6. Liquidity: Current Ratio increased YoY (requires prior)
    liquidity = 0
    if period.prior_balance is not None:
        current_cr = balance.current_ratio
        prior_cr = period.prior_balance.current_ratio
        liquidity = 1 if current_cr > prior_cr else 0

    # 7. Dilution: Shares outstanding_t <= shares_t-1 (requires prior)
    dilution = 0
    if period.prior_balance is not None:
        current_shares = balance.shares_outstanding
        prior_shares = period.prior_balance.shares_outstanding
        dilution = 1 if current_shares <= prior_shares else 0

    # 8. Gross Margin Change: Gross Margin improved YoY (requires prior)
    gross_margin = 0
    if period.prior_income is not None:
        current_gm = income.gross_margin
        prior_gm = period.prior_income.gross_margin
        gross_margin = 1 if current_gm > prior_gm else 0

    # 9. Asset Turnover Change: Revenue/Assets improved YoY (requires prior)
    asset_turnover = 0
    if period.prior_income is not None and period.prior_balance is not None:
        current_at = float(income.revenue / total_assets) if total_assets != 0 else 0.0
        prior_ta = period.prior_balance.total_assets
        prior_at = float(period.prior_income.revenue / prior_ta) if prior_ta != 0 else 0.0
        asset_turnover = 1 if current_at > prior_at else 0

    return {
        "roa": roa,
        "cfo": cfo_signal,
        "roa_change": roa_change,
        "accruals": accruals,
        "leverage": leverage,
        "liquidity": liquidity,
        "dilution": dilution,
        "gross_margin": gross_margin,
        "asset_turnover": asset_turnover,
    }


def piotroski_f_score(period: FinancialPeriod) -> FactorScore:
    """Compute Piotroski F-Score quality factor.

    Returns a FactorScore with:
    - raw_value: F-Score (0-9), the sum of 9 binary signals
    - percentile_rank: 0.0 (placeholder -- filled by composite scorer in Phase 6)
    - name: "piotroski_f_score"
    """
    signals = compute_f_score_signals(period)
    f_score = sum(signals.values())

    detail_parts = [f"{name}={'PASS' if value else 'FAIL'}" for name, value in signals.items()]
    detail = f"F-Score={f_score}/9 | {', '.join(detail_parts)}"

    return FactorScore(
        name="piotroski_f_score",
        raw_value=float(f_score),
        percentile_rank=0.0,
        detail=detail,
    )
