"""Beneish M-Score earnings manipulation filter.

The M-Score is a probabilistic model that uses eight financial ratios
to identify whether a company has manipulated its reported earnings.
A score above -1.78 suggests a high probability of manipulation.

Reference: Beneish, M.D. (1999). "The Detection of Earnings Manipulation."
Financial Analysts Journal, 55(5), 24-36.
"""

from __future__ import annotations

from decimal import Decimal

from margin_engine.config.filter_config import BeneishConfig
from margin_engine.models.financial import FinancialHistory, FinancialPeriod
from margin_engine.models.scoring import FilterResult

_THRESHOLD = -1.78


def _safe_div(numerator: float, denominator: float, default: float = 1.0) -> float:
    """Divide numerator by denominator, returning default if denominator is zero."""
    if denominator == 0.0:
        return default
    return numerator / denominator


def _d(val: Decimal | None, default: Decimal = Decimal("0")) -> float:
    """Convert optional Decimal to float, using default if None."""
    if val is None:
        return float(default)
    return float(val)


def beneish_m_score(
    period: FinancialPeriod,
    config: BeneishConfig | None = None,
) -> FilterResult:
    """Compute Beneish M-Score and return filter result.

    Requires both current and prior period data. If prior data is missing,
    return a PASS with detail explaining insufficient data.

    Args:
        period: Financial data with current and prior period statements.
        config: Optional BeneishConfig. When provided, threshold is read
            from config. When None, the hardcoded constant is used.
    """
    name = "beneish_m_score"
    threshold = config.threshold if config else _THRESHOLD

    # Guard: need prior period data for year-over-year comparisons
    if period.prior_income is None or period.prior_balance is None:
        missing = []
        if period.prior_income is None:
            missing.append("prior_income")
        if period.prior_balance is None:
            missing.append("prior_balance")
        return FilterResult(
            name=name,
            passed=True,
            threshold=threshold,
            insufficient_data=True,
            missing_fields=missing,
            detail="Insufficient historical data for M-Score",
        )

    # Current period values
    ci = period.current_income
    cb = period.current_balance
    cf = period.current_cash_flow

    # Prior period values
    pi = period.prior_income
    pb = period.prior_balance

    # --- Component 1: DSRI (Days Sales in Receivables Index) ---
    # (receivables_t / revenue_t) / (receivables_t-1 / revenue_t-1)
    recv_t = _d(cb.receivables)
    rev_t = _d(ci.revenue)
    recv_t1 = _d(pb.receivables)
    rev_t1 = _d(pi.revenue)

    dsri_num = _safe_div(recv_t, rev_t, default=0.0)
    dsri_den = _safe_div(recv_t1, rev_t1, default=0.0)
    dsri = _safe_div(dsri_num, dsri_den)

    # --- Component 2: GMI (Gross Margin Index) ---
    # gross_margin_t-1 / gross_margin_t
    gm_t = _safe_div(_d(ci.gross_profit), rev_t, default=0.0)
    gm_t1 = _safe_div(_d(pi.gross_profit), rev_t1, default=0.0)
    gmi = _safe_div(gm_t1, gm_t)

    # --- Component 3: AQI (Asset Quality Index) ---
    # [1 - (PPE_t + CA_t) / TA_t] / [1 - (PPE_t-1 + CA_t-1) / TA_t-1]
    ppe_t = _d(cb.pp_and_e)
    ca_t = _d(cb.current_assets)
    ta_t = _d(cb.total_assets)
    ppe_t1 = _d(pb.pp_and_e)
    ca_t1 = _d(pb.current_assets)
    ta_t1 = _d(pb.total_assets)

    aqi_num = 1.0 - _safe_div(ppe_t + ca_t, ta_t, default=1.0)
    aqi_den = 1.0 - _safe_div(ppe_t1 + ca_t1, ta_t1, default=1.0)
    aqi = _safe_div(aqi_num, aqi_den)

    # --- Component 4: SGI (Sales Growth Index) ---
    # revenue_t / revenue_t-1
    sgi = _safe_div(rev_t, rev_t1)

    # --- Component 5: DEPI (Depreciation Index) ---
    # dep_rate_t-1 / dep_rate_t
    # where dep_rate = depreciation / (depreciation + pp_and_e)
    dep_t = _d(ci.depreciation)
    dep_t1 = _d(pi.depreciation)
    dep_rate_t = _safe_div(dep_t, dep_t + ppe_t, default=0.0)
    dep_rate_t1 = _safe_div(dep_t1, dep_t1 + ppe_t1, default=0.0)
    depi = _safe_div(dep_rate_t1, dep_rate_t)

    # --- Component 6: SGAI (SGA Index) ---
    # (sga_t / revenue_t) / (sga_t-1 / revenue_t-1)
    sga_t = _d(ci.sga_expense)
    sga_t1 = _d(pi.sga_expense)
    sgai_num = _safe_div(sga_t, rev_t, default=0.0)
    sgai_den = _safe_div(sga_t1, rev_t1, default=0.0)
    sgai = _safe_div(sgai_num, sgai_den)

    # --- Component 7: TATA (Total Accruals to Total Assets) ---
    # (net_income - operating_cash_flow) / total_assets
    net_income = _d(ci.net_income)
    ocf = _d(cf.operating_cash_flow)
    tata = _safe_div(net_income - ocf, ta_t, default=0.0)

    # --- Component 8: LVGI (Leverage Index) ---
    # [(CL_t + LTD_t) / TA_t] / [(CL_t-1 + LTD_t-1) / TA_t-1]
    cl_t = _d(cb.current_liabilities)
    ltd_t = _d(cb.long_term_debt)
    cl_t1 = _d(pb.current_liabilities)
    ltd_t1 = _d(pb.long_term_debt)

    lvgi_num = _safe_div(cl_t + ltd_t, ta_t, default=0.0)
    lvgi_den = _safe_div(cl_t1 + ltd_t1, ta_t1, default=0.0)
    lvgi = _safe_div(lvgi_num, lvgi_den)

    # --- M-Score formula ---
    m_score = (
        -4.84
        + 0.920 * dsri
        + 0.528 * gmi
        + 0.404 * aqi
        + 0.892 * sgi
        + 0.115 * depi
        - 0.172 * sgai
        + 4.679 * tata
        - 0.327 * lvgi
    )

    passed = m_score <= threshold

    components = (
        f"DSRI={dsri:.4f}, GMI={gmi:.4f}, AQI={aqi:.4f}, SGI={sgi:.4f}, "
        f"DEPI={depi:.4f}, SGAI={sgai:.4f}, TATA={tata:.4f}, LVGI={lvgi:.4f}"
    )
    detail = (
        f"M-Score={m_score:.4f} ({'PASS' if passed else 'FAIL'}, "
        f"threshold={threshold}). {components}"
    )

    return FilterResult(
        name=name,
        passed=passed,
        value=round(m_score, 4),
        threshold=threshold,
        detail=detail,
    )


def beneish_m_score_v2(
    history_or_period: FinancialHistory | FinancialPeriod,
    config: BeneishConfig | None = None,
) -> FilterResult:
    """Compute Beneish M-Score across multiple periods with trend analysis.

    When given a ``FinancialHistory`` with multiple periods, computes M-Score
    for every period that has both current AND prior data, stores historical
    scores, detects deteriorating trends, and evaluates the most recent
    M-Score against the threshold.

    When given a single ``FinancialPeriod``, delegates to the original
    ``beneish_m_score()`` for backward compatibility.

    Args:
        history_or_period: Either a multi-year FinancialHistory or a single
            FinancialPeriod for backward-compatible single-period check.
        config: Optional BeneishConfig controlling threshold.

    Returns:
        FilterResult with computed_metrics containing current_m_score,
        historical_m_scores_count, and trend indicator.
    """
    name = "beneish_m_score"

    # --- Single-period fallback ---
    if isinstance(history_or_period, FinancialPeriod):
        return beneish_m_score(history_or_period, config=config)

    history = history_or_period
    threshold = config.threshold if config else _THRESHOLD

    # --- Compute M-Score for each period that has prior data ---
    historical_m_scores: list[tuple[str, float]] = []

    for period in history.periods:
        result = beneish_m_score(period, config=config)
        if not result.insufficient_data and result.value is not None:
            historical_m_scores.append((period.period_end, result.value))

    # --- INCONCLUSIVE: no computable M-Scores ---
    if not historical_m_scores:
        return FilterResult(
            name=name,
            passed=True,
            threshold=threshold,
            insufficient_data=True,
            detail="Insufficient historical data for multi-period M-Score: "
            "no periods have both current and prior financial data",
        )

    # --- Evaluate most recent M-Score ---
    current_period_end, current_m_score = historical_m_scores[-1]
    passed = current_m_score <= threshold

    # --- Trend detection ---
    # A deteriorating trend means M-Scores are increasing (getting closer to
    # or exceeding -1.78) over consecutive periods.
    trend = _detect_trend(historical_m_scores)
    trend_label = "deteriorating" if trend else "stable"

    # --- Build detail string ---
    scores_str = ", ".join(f"{pe}={ms:.4f}" for pe, ms in historical_m_scores)
    status = "PASS" if passed else "FAIL"
    detail = (
        f"M-Score={current_m_score:.4f} ({status}, threshold={threshold}). "
        f"historical=[{scores_str}], trend={trend_label}"
    )

    # --- Warning for deteriorating trend ---
    warning = trend
    warning_reason: str | None = None
    if trend:
        warning_reason = (
            f"M-Score trend is deteriorating over {len(historical_m_scores)} periods: "
            f"scores are moving toward the manipulation threshold ({threshold})"
        )

    return FilterResult(
        name=name,
        passed=passed,
        value=round(current_m_score, 4),
        threshold=threshold,
        detail=detail,
        warning=warning,
        warning_reason=warning_reason,
        computed_metrics={
            "current_m_score": round(current_m_score, 4),
            "historical_m_scores_count": float(len(historical_m_scores)),
            "trend": 1.0 if trend else 0.0,
        },
    )


def _detect_trend(scores: list[tuple[str, float]]) -> bool:
    """Detect if M-Scores are deteriorating (moving toward -1.78).

    A deteriorating trend means each successive M-Score is higher (closer
    to zero / closer to the manipulation threshold) than the previous one.
    Requires at least 2 scores and that the last 2+ consecutive scores
    are strictly increasing.

    Args:
        scores: List of (period_end, m_score) tuples in chronological order.

    Returns:
        True if the trend is deteriorating, False otherwise.
    """
    if len(scores) < 2:
        return False

    # Check if the most recent 2+ consecutive scores are increasing
    # (i.e., each is higher / closer to threshold than the prior)
    consecutive_increases = 0
    for i in range(len(scores) - 1, 0, -1):
        if scores[i][1] > scores[i - 1][1]:
            consecutive_increases += 1
        else:
            break

    # Need at least 2 consecutive increases to flag deterioration
    return consecutive_increases >= 2
