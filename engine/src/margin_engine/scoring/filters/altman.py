"""Altman Z'' Score financial distress filter.

The Z'' Score (non-manufacturing variant) predicts the probability of
corporate bankruptcy using balance sheet and income statement ratios.
A score below 1.1 indicates financial distress.

Formula:
    Z'' = 6.56(WC/TA) + 3.26(RE/TA) + 6.72(EBIT/TA) + 1.05(Equity/TL)

Reference: Altman, E.I. (1993). "Corporate Financial Distress and Bankruptcy."
"""

from __future__ import annotations

from decimal import Decimal

from margin_engine.config.filter_config import AltmanConfig
from margin_engine.models.financial import FinancialPeriod, GICSSector
from margin_engine.models.scoring import FilterResult

_THRESHOLD = 1.1
_EQUITY_TL_CAP = 10.0  # Cap for Equity/TL when total_liabilities == 0


def _d(val: Decimal | None, default: Decimal = Decimal("0")) -> float:
    """Convert optional Decimal to float, using default if None."""
    if val is None:
        return float(default)
    return float(val)


def altman_z_score(
    period: FinancialPeriod,
    sector: GICSSector | None = None,
    config: AltmanConfig | None = None,
) -> FilterResult:
    """Compute Altman Z'' Score and return filter result.

    Args:
        period: Financial data with current balance sheet and income statement.
        sector: GICS sector for exclusion rules. Utilities are exempt.
        config: Optional AltmanConfig. When provided, threshold, equity_tl_cap,
            and exempt_sectors are read from config. When None, hardcoded
            constants are used.
    """
    name = "altman_z_score"
    threshold = config.threshold if config else _THRESHOLD
    equity_tl_cap = config.equity_tl_cap if config else _EQUITY_TL_CAP

    # Determine exempt sectors
    if config is not None:
        exempt_sectors = set(config.exempt_sectors)
    else:
        exempt_sectors = {"Utilities"}

    # Sector exemption: different capital structures make Z'' unreliable
    sector_value = sector.value if sector else None
    if sector_value in exempt_sectors:
        return FilterResult(
            name=name,
            passed=True,
            threshold=threshold,
            detail=f"Altman Z'' not applicable to {sector_value}",
        )

    cb = period.current_balance
    ci = period.current_income

    ta = _d(cb.total_assets)
    tl = _d(cb.total_liabilities)

    # Guard: zero total assets makes all ratios undefined
    if ta == 0.0:
        return FilterResult(
            name=name,
            passed=False,
            threshold=threshold,
            detail="Invalid: zero total assets",
        )

    # Component values
    wc = _d(cb.current_assets) - _d(cb.current_liabilities)
    re = _d(cb.retained_earnings)  # defaults to 0 if None
    ebit = _d(ci.ebit)
    equity = _d(cb.total_equity)

    # Ratios
    wc_ta = wc / ta
    re_ta = re / ta
    ebit_ta = ebit / ta

    # Handle zero total liabilities: cap the ratio at a large positive value
    if tl == 0.0:
        equity_tl = equity_tl_cap
    else:
        equity_tl = equity / tl

    # Z'' Score formula (non-manufacturing)
    z_score = 6.56 * wc_ta + 3.26 * re_ta + 6.72 * ebit_ta + 1.05 * equity_tl

    passed = z_score >= threshold

    components = (
        f"WC/TA={wc_ta:.4f}, RE/TA={re_ta:.4f}, "
        f"EBIT/TA={ebit_ta:.4f}, Equity/TL={equity_tl:.4f}"
    )
    detail = (
        f"Z''={z_score:.4f} ({'PASS' if passed else 'FAIL'}, "
        f"threshold={threshold}). {components}"
    )

    return FilterResult(
        name=name,
        passed=passed,
        value=round(z_score, 4),
        threshold=threshold,
        detail=detail,
    )
