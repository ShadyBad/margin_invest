"""Post-composite score modifiers.

Each modifier returns a float multiplier. Combined product clamped to [0.75, 1.25].
Applied after v3/v4 cascade -- affects ranking and position sizing, not conviction tier.
"""

from __future__ import annotations

import math

from margin_engine.models.financial import FinancialHistory, FinancialPeriod

_COMBINED_FLOOR = 0.75
_COMBINED_CEILING = 1.25

_LIQ_FLOOR = 0.85
_LIQ_CEILING = 1.0


def liquidity_modifier(
    market_cap: float,
    avg_daily_dollar_volume: float,
    divergence_ratio: float | None,
) -> float:
    """Returns multiplier 0.85-1.00. Never boosts, only penalizes.

    Three components (equal weight):
    1. Market cap tier: log-scaled, $100B+=1.0, $100M=0.0
    2. Turnover adequacy: ADV/market_cap, >=0.5%=1.0, <=0.01%=0.0
    3. Liquidity stability: from divergence ratio, <=1.5=1.0, >=3.0=0.5, None=0.7
    """
    # Component 1: Market cap tier (log-scaled)
    if market_cap <= 0:
        cap_score = 0.0
    else:
        log_cap = math.log10(max(market_cap, 1))
        cap_score = max(0.0, min(1.0, (log_cap - 8.0) / 3.0))

    # Component 2: Turnover adequacy
    if market_cap <= 0:
        turnover_score = 0.0
    else:
        turnover = avg_daily_dollar_volume / market_cap
        if turnover >= 0.005:
            turnover_score = 1.0
        elif turnover <= 0.0001:
            turnover_score = 0.0
        else:
            log_t = math.log10(turnover)
            turnover_score = max(0.0, min(1.0, (log_t + 4.0) / 1.7))

    # Component 3: Liquidity stability
    if divergence_ratio is None:
        stability_score = 0.7
    elif divergence_ratio <= 1.5:
        stability_score = 1.0
    elif divergence_ratio >= 3.0:
        stability_score = 0.5
    else:
        stability_score = 1.0 - 0.5 * (divergence_ratio - 1.5) / 1.5

    avg = (cap_score + turnover_score + stability_score) / 3.0
    return _LIQ_FLOOR + (_LIQ_CEILING - _LIQ_FLOOR) * avg


def insider_signal_modifier(
    cluster_score: float,
    cluster_detected: bool,
    total_buy_value: float,
    price_drawdown_pct: float | None,
    has_first_ever_buy: bool,
) -> float:
    """Returns multiplier 1.00 - 1.15. Never penalizes.

    No cluster -> 1.0.
    Cluster detected -> base 1.05.
    + drawdown > 10% -> +0.03
    + magnitude $5M+ -> +0.03
    + first-ever-buy  -> +0.04
    Maximum: 1.15.
    """
    if not cluster_detected:
        return 1.0
    modifier = 1.05
    if price_drawdown_pct is not None and price_drawdown_pct < -0.10:
        modifier += 0.03
    if total_buy_value >= 5_000_000:
        modifier += 0.03
    if has_first_ever_buy:
        modifier += 0.04
    return min(modifier, 1.15)


# ---------------------------------------------------------------------------
# Fundamental trajectory
# ---------------------------------------------------------------------------


def _compute_roic(period: FinancialPeriod) -> float | None:
    """Compute ROIC from a FinancialPeriod's income + balance sheet.

    ROIC = EBIT * (1 - effective_tax_rate) / invested_capital
    invested_capital = total_equity + total_debt - cash_and_equivalents
    """
    inc = period.current_income
    bal = period.current_balance
    ebit = float(inc.ebit)
    tax_rate = inc.effective_tax_rate
    equity = float(bal.total_equity)
    debt = float(bal.total_debt)
    cash = float(bal.cash_and_equivalents or 0)
    invested_capital = equity + debt - cash
    if invested_capital <= 0:
        return None
    return ebit * (1.0 - tax_rate) / invested_capital


def compute_fundamental_trajectory(history: FinancialHistory) -> float:
    """Compare latest vs prior ROIC and gross margin trends. Returns 0-1.

    - 1.0: both ROIC and GM improving for all consecutive periods
    - 0.5: neutral (single period, or mixed/flat signals)
    - 0.0: both declining for all consecutive periods

    Examines up to the last 3 period transitions. For each transition,
    checks whether ROIC improved and whether gross margin improved.
    The trajectory score is the average of the per-transition scores,
    where each transition scores 1.0 (both improving), 0.5 (mixed/flat),
    or 0.0 (both declining).
    """
    periods = history.periods
    if len(periods) < 2:
        return 0.5

    # Use at most last 4 periods (3 transitions)
    recent = periods[-4:] if len(periods) >= 4 else periods

    # Compute ROIC and GM for each period
    roics: list[float | None] = []
    gms: list[float] = []
    for p in recent:
        roics.append(_compute_roic(p))
        gms.append(p.current_income.gross_margin)

    transition_scores: list[float] = []
    for i in range(1, len(recent)):
        prev_roic = roics[i - 1]
        curr_roic = roics[i]
        prev_gm = gms[i - 1]
        curr_gm = gms[i]

        # Determine ROIC direction
        if prev_roic is None or curr_roic is None:
            roic_improving = None  # Unknown
        elif curr_roic > prev_roic:
            roic_improving = True
        elif curr_roic < prev_roic:
            roic_improving = False
        else:
            roic_improving = None  # Flat

        # Determine GM direction
        if curr_gm > prev_gm:
            gm_improving = True
        elif curr_gm < prev_gm:
            gm_improving = False
        else:
            gm_improving = None  # Flat

        # Score this transition
        if roic_improving is True and gm_improving is True:
            transition_scores.append(1.0)
        elif roic_improving is False and gm_improving is False:
            transition_scores.append(0.0)
        else:
            transition_scores.append(0.5)

    if not transition_scores:
        return 0.5

    return sum(transition_scores) / len(transition_scores)


# ---------------------------------------------------------------------------
# Anti-consensus modifier
# ---------------------------------------------------------------------------

_ANTI_CONSENSUS_FLOOR = 0.90
_ANTI_CONSENSUS_CEILING = 1.15


def anti_consensus_modifier(
    short_interest_percentile: float,
    analyst_divergence: float,
    eps_revision_strength: float,
    fundamental_trajectory: float,
) -> float:
    """Returns multiplier 0.90 - 1.15.

    Three weighted components:
    - Short interest divergence (40%): high short + improving fundamentals
    - Analyst rating divergence (30%): downgrades while fundamentals improve
    - Earnings revision strength (30%): positive surprises

    Only fires meaningfully when fundamental_trajectory > 0.5.
    When trajectory < 0.3, bearish sentiment is correct -> mild penalty.

    Args:
        short_interest_percentile: 0-100, sector-relative rank
        analyst_divergence: -1 to +1 (negative = bearish consensus)
        eps_revision_strength: -1 to +1 (positive = upward revisions)
        fundamental_trajectory: 0-1 from compute_fundamental_trajectory
    """
    # Component 1: Short interest divergence (40%)
    # High short interest (percentile > 50) + improving fundamentals = bullish signal
    short_signal = (short_interest_percentile - 50.0) / 50.0  # -1 to +1

    # Component 2: Analyst divergence (30%)
    # Negative analyst_divergence (bearish consensus) + strong fundamentals = bullish signal
    analyst_signal = -analyst_divergence  # Flip: bearish consensus -> positive signal

    # Component 3: Earnings revision strength (30%)
    # Positive EPS revisions are directly bullish
    eps_signal = eps_revision_strength  # -1 to +1

    # Weighted raw signal
    raw_signal = 0.40 * short_signal + 0.30 * analyst_signal + 0.30 * eps_signal

    # Apply trajectory gating
    if fundamental_trajectory > 0.5:
        # Fundamentals improving -> divergence from bearish consensus is meaningful
        # Scale by how strong the trajectory is above 0.5
        trajectory_scale = (fundamental_trajectory - 0.5) * 2.0  # 0 to 1
        effective_signal = raw_signal * trajectory_scale
    elif fundamental_trajectory < 0.3:
        # Fundamentals weak -> bearish consensus is likely correct
        # Apply mild penalty proportional to how weak trajectory is
        weakness = (0.3 - fundamental_trajectory) / 0.3  # 0 to 1
        effective_signal = -0.4 * weakness  # Mild penalty up to -0.4
    else:
        # Transition zone (0.3-0.5): near-neutral
        effective_signal = 0.0

    # Map effective_signal to modifier range
    # Center at 1.0; positive signal -> boost toward 1.15, negative -> penalty toward 0.90
    half_range_up = _ANTI_CONSENSUS_CEILING - 1.0  # 0.15
    half_range_down = 1.0 - _ANTI_CONSENSUS_FLOOR  # 0.10

    if effective_signal >= 0:
        modifier = 1.0 + effective_signal * half_range_up
    else:
        modifier = 1.0 + effective_signal * half_range_down

    return max(_ANTI_CONSENSUS_FLOOR, min(_ANTI_CONSENSUS_CEILING, modifier))


def apply_all_modifiers(
    composite_score: float,
    anti_consensus: float,
    liquidity: float,
    insider: float,
) -> tuple[float, dict[str, float]]:
    """Apply all post-composite modifiers with combined bounds.

    Returns (modified_score, breakdown) where breakdown contains
    each modifier value and the combined product.
    """
    combined = anti_consensus * liquidity * insider
    combined = max(_COMBINED_FLOOR, min(_COMBINED_CEILING, combined))
    return composite_score * combined, {
        "anti_consensus": anti_consensus,
        "liquidity": liquidity,
        "insider": insider,
        "combined": combined,
    }
