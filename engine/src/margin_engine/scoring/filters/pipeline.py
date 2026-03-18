"""Elimination filter pipeline — chains all 7 filters in sequence.

Runs every filter regardless of earlier failures (no short-circuit) to provide
complete diagnostic information about why an asset was eliminated.

Usage (v1, single-period):
    result = run_elimination_filters(period, profile)

Usage (v2, multi-period):
    result = run_elimination_filters(
        period, profile,
        history=financial_history,
        price_bars=daily_bars,
    )
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import Decimal

from margin_engine.config.filter_config import FilterConfig, load_filter_config
from margin_engine.models.financial import (
    AssetProfile,
    FinancialHistory,
    FinancialPeriod,
    PriceBar,
)
from margin_engine.models.scoring import FilterResult
from margin_engine.scoring.classifier import classify_growth_stage
from margin_engine.scoring.filters.altman import altman_z_score
from margin_engine.scoring.filters.beneish import beneish_m_score, beneish_m_score_v2
from margin_engine.scoring.filters.current_ratio import (
    current_ratio_check,
    current_ratio_check_v2,
)
from margin_engine.scoring.filters.fcf_distress import (
    fcf_distress_check,
    fcf_distress_check_v2,
)
from margin_engine.scoring.filters.interest_coverage import (
    interest_coverage_check,
    interest_coverage_check_v2,
)
from margin_engine.scoring.filters.liquidity import liquidity_check, liquidity_check_v2
from margin_engine.scoring.filters.mediocrity_gate import mediocrity_gate


@dataclass
class PipelineResult:
    """Result of running all elimination filters."""

    results: list[FilterResult]

    @property
    def passed(self) -> bool:
        """True if ALL filters passed (or conditionally passed)."""
        return all(r.passed or r.conditional for r in self.results)

    @property
    def failed_filters(self) -> list[FilterResult]:
        """List of filters that failed (excludes conditional passes)."""
        return [r for r in self.results if not r.passed and not r.conditional]

    @property
    def conditional_filters(self) -> list[FilterResult]:
        """List of filters that conditionally passed."""
        return [r for r in self.results if not r.passed and r.conditional]


def _extract_quarterly_series(
    history: FinancialHistory,
) -> dict[str, list[float]]:
    """Extract quarterly ROIC, gross margin, FCF, and net income series from financial history.

    Returns a dict with keys ``"roic"``, ``"gm"``, ``"fcf"``, ``"net_income"`` —
    each a list of finite float values suitable for trajectory analysis.
    """
    roic_vals: list[float] = []
    gm_vals: list[float] = []
    fcf_vals: list[float] = []
    net_income_vals: list[float] = []

    for p in history.periods:
        # ROIC = NOPAT / IC where NOPAT = EBIT * (1 - tax_rate), IC = equity + debt - cash
        ci = p.current_income
        cb = p.current_balance
        ebit = float(ci.ebit)
        tax_rate = ci.effective_tax_rate
        nopat = ebit * (1.0 - tax_rate)
        cash = float(cb.cash_and_equivalents or Decimal("0"))
        ic = float(cb.total_equity) + float(cb.total_debt) - cash
        if ic > 0:
            roic = nopat / ic
            if math.isfinite(roic):
                roic_vals.append(roic)

        # Gross margin
        gm = ci.gross_margin
        if math.isfinite(gm):
            gm_vals.append(gm)

        # Free cash flow
        fcf = float(p.current_cash_flow.free_cash_flow)
        if math.isfinite(fcf):
            fcf_vals.append(fcf)

        # Net income
        ni = float(ci.net_income)
        if math.isfinite(ni):
            net_income_vals.append(ni)

    return {"roic": roic_vals, "gm": gm_vals, "fcf": fcf_vals, "net_income": net_income_vals}


def run_elimination_filters(
    period: FinancialPeriod,
    profile: AssetProfile,
    config: FilterConfig | None = None,
    history: FinancialHistory | None = None,
    price_bars: list[PriceBar] | None = None,
    disabled_filters: set[str] | None = None,
) -> PipelineResult:
    """Run all elimination filters in sequence.

    All filters run regardless of earlier failures (no short-circuit).
    This gives complete diagnostic information about why an asset was eliminated.

    When ``history`` or ``price_bars`` are provided, the pipeline uses v2
    multi-period filters that offer richer diagnostics (trend analysis,
    median-based thresholds, etc.).  Without them, the original v1 single-period
    filters are used for backward compatibility.

    Args:
        period: Financial data for scoring.
        profile: Static asset metadata (ticker, sector, market cap, etc.)
        config: Optional FilterConfig. When provided, thresholds for all
            filters are read from config sub-objects. When None, defaults
            are loaded via ``load_filter_config()`` (which returns hardcoded
            defaults when no YAML file is configured).
        history: Optional FinancialHistory for multi-year analysis. When
            provided, Beneish, FCF distress, interest coverage, and current
            ratio filters use multi-period v2 variants.
        price_bars: Optional list of daily OHLCV bars. When provided, the
            liquidity filter uses v2 with position sizing and divergence
            analysis.
        disabled_filters: Optional set of filter names to exclude from the
            returned results. Filters are still executed (preserving the
            no-short-circuit guarantee) but removed before returning.
            Valid names: ``"liquidity"``, ``"beneish_m_score"``,
            ``"altman_z_score"``, ``"fcf_distress"``,
            ``"interest_coverage"``, ``"current_ratio"``,
            ``"mediocrity_gate"``.

    Returns:
        PipelineResult containing all filter outcomes.
    """
    if config is None:
        config = load_filter_config()

    sector = profile.sector

    # --- Liquidity ---
    if price_bars is not None:
        liquidity_result = liquidity_check_v2(
            profile,
            price_bars=price_bars,
            config=config.liquidity,
        )
    else:
        liquidity_result = liquidity_check(profile, config=config.liquidity)

    # --- Beneish M-Score ---
    if history is not None:
        beneish_result = beneish_m_score_v2(history, config=config.beneish)
    else:
        beneish_result = beneish_m_score(period, config=config.beneish)

    # --- Altman Z-Score (no v2 variant) ---
    altman_result = altman_z_score(period, sector=sector, config=config.altman)

    # --- FCF Distress ---
    if history is not None:
        fcf_result = fcf_distress_check_v2(history, config=config.fcf_distress, sector=sector)
    else:
        fcf_result = fcf_distress_check(period, config=config.fcf_distress)

    # --- Interest Coverage ---
    if history is not None:
        interest_result = interest_coverage_check_v2(
            history, sector=sector, config=config.interest_coverage
        )
    else:
        interest_result = interest_coverage_check(
            period, sector=sector, config=config.interest_coverage
        )

    # --- Current Ratio ---
    if history is not None:
        current_result = current_ratio_check_v2(history, sector=sector, config=config.current_ratio)
    else:
        current_result = current_ratio_check(period, sector=sector, config=config.current_ratio)

    # --- Mediocrity Gate ---
    mediocrity_history = (
        history
        if history is not None
        else FinancialHistory(ticker=profile.ticker, periods=[period])
    )
    quarterly = _extract_quarterly_series(history) if history is not None else {}

    # Classify growth stage when history is available — enables turnaround/high-growth
    # trajectory overrides in the mediocrity gate.
    growth_stage = None
    if history is not None:
        growth_stage = classify_growth_stage(
            period,
            profile,
            quarterly_net_incomes=quarterly.get("net_income"),
            quarterly_margins=quarterly.get("gm"),
        )

    mediocrity_result = mediocrity_gate(
        history=mediocrity_history,
        sector=sector,
        roic_quarterly=quarterly.get("roic"),
        gm_quarterly=quarterly.get("gm"),
        fcf_quarterly=quarterly.get("fcf"),
        growth_stage=growth_stage,
    )

    results = [
        liquidity_result,
        beneish_result,
        altman_result,
        fcf_result,
        interest_result,
        current_result,
        mediocrity_result,
    ]

    if disabled_filters:
        results = [r for r in results if r.name not in disabled_filters]

    return PipelineResult(results=results)
