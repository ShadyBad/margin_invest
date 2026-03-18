"""Insider Cluster Buying factor.

Detects coordinated insider purchasing — a strong bullish signal when
multiple distinct insiders make significant open-market purchases within
a short window. Selling is ignored because insider sales are noisy
(tax planning, diversification, etc.) while buys are unambiguous.

Design rules:
- 3+ distinct insiders buying within 90 days = cluster buy signal
- Only purchases >= $100,000 are considered significant
- CEO/CFO weighted 2x vs directors and other insiders
- Selling is ignored (asymmetric signal — only buys matter)

Extended signals (opt-in):
- price_drawdown_pct: when < -0.10, score is multiplied by 1.5
- apply_magnitude: when True, score is multiplied by tier based on total_buy_value
- is_first_purchase: when True on a transaction, that insider's weight is 10x

Academic reference: Lakonishok & Lee (2001), "Are Insider Trades
Informative?"
"""

from __future__ import annotations

import datetime
from decimal import Decimal

from margin_engine.models.financial import InsiderTransaction
from margin_engine.models.scoring import FactorScore

_CLUSTER_WINDOW_DAYS = 90
_MIN_PURCHASE_VALUE = Decimal("100000")
_HIGH_WEIGHT_TITLES = frozenset({"CEO", "CFO"})
_FIRST_PURCHASE_MULTIPLIER = 10.0
_DRAWDOWN_THRESHOLD = -0.10
_DRAWDOWN_MULTIPLIER = 1.5


def _magnitude_boost(total_buy_value: float) -> float:
    """Return a magnitude multiplier based on total buy value.

    Tiers:
    - $5M+  -> 2.0
    - $1M+  -> 1.5
    - $100K+ -> 1.0
    - below  -> 0.5
    """
    if total_buy_value >= 5_000_000:
        return 2.0
    if total_buy_value >= 1_000_000:
        return 1.5
    if total_buy_value >= 100_000:
        return 1.0
    return 0.5


def insider_cluster_score(
    transactions: list[InsiderTransaction],
    *,
    price_drawdown_pct: float | None = None,
    apply_magnitude: bool = False,
) -> FactorScore:
    """Compute the insider cluster buying score.

    Algorithm:
    1. Filter to only "buy" transactions (ignore sells).
    2. Filter to significant purchases (value >= $100,000).
    3. Find the most recent 90-day window of buy transactions.
    4. Count distinct insiders who bought in that window.
    5. Compute a weighted score:
       - Each insider buy counts as 1 point.
       - CEO/CFO title gets 2x weight (2 points instead of 1).
       - is_first_purchase=True multiplies the insider's weight by 10.
       - Score = sum of weighted points.
    6. Apply optional multipliers (drawdown, magnitude).

    Args:
        transactions: List of insider transactions to analyze.
        price_drawdown_pct: Current price drawdown percentage (e.g. -0.15 for 15% down).
            When < -0.10, the score is multiplied by 1.5.
        apply_magnitude: When True, multiply score by a tier based on total_buy_value.

    Returns a FactorScore with:
    - name: "insider_cluster"
    - raw_value: the weighted score as float (0.0 if no qualifying buys)
    - percentile_rank: 0.0 (placeholder -- filled by composite scorer in Phase 6)
    - detail: human-readable breakdown
    """
    if not transactions:
        return FactorScore(
            name="insider_cluster",
            raw_value=0.0,
            percentile_rank=0.0,
            detail="no transactions provided",
        )

    # 1. Filter to buys only.
    buys = [t for t in transactions if t.transaction_type == "buy"]
    if not buys:
        return FactorScore(
            name="insider_cluster",
            raw_value=0.0,
            percentile_rank=0.0,
            detail="no buy transactions found (all sells or other)",
        )

    # 2. Filter to significant purchases (>= $100K).
    significant = [t for t in buys if t.value >= _MIN_PURCHASE_VALUE]
    if not significant:
        return FactorScore(
            name="insider_cluster",
            raw_value=0.0,
            percentile_rank=0.0,
            detail=(
                f"no significant buys (all {len(buys)} buy(s) below "
                f"${_MIN_PURCHASE_VALUE:,} threshold)"
            ),
        )

    # 3. Sort by date and find the most recent 90-day window.
    significant.sort(key=lambda t: t.date)
    dates = [datetime.date.fromisoformat(t.date) for t in significant]
    most_recent_date = dates[-1]
    window_start = most_recent_date - datetime.timedelta(days=_CLUSTER_WINDOW_DAYS)

    # 4. Filter to transactions within the 90-day window.
    in_window = [t for t, d in zip(significant, dates) if d >= window_start]

    # 5. Count distinct insiders and compute weighted score.
    #    For each distinct insider, use the highest-weight title they hold
    #    and track whether any of their transactions is a first purchase.
    insider_titles: dict[str, str] = {}
    insider_first_purchase: dict[str, bool] = {}
    for t in in_window:
        name = t.insider_name
        if name not in insider_titles:
            insider_titles[name] = t.title
            insider_first_purchase[name] = bool(t.is_first_purchase)
        else:
            # Keep the highest-weight title (CEO/CFO > other).
            if t.title in _HIGH_WEIGHT_TITLES:
                insider_titles[name] = t.title
            # If any transaction for this insider is a first purchase, mark it.
            if t.is_first_purchase:
                insider_first_purchase[name] = True

    # 6. Compute weighted score.
    weighted_score = 0.0
    insider_weights: list[str] = []
    for name, title in sorted(insider_titles.items()):
        weight = 2.0 if title in _HIGH_WEIGHT_TITLES else 1.0
        if insider_first_purchase.get(name):
            weight *= _FIRST_PURCHASE_MULTIPLIER
        weighted_score += weight
        insider_weights.append(f"{name} ({title}, {weight:.0f}x)")

    distinct_count = len(insider_titles)
    is_cluster = distinct_count >= 3
    window_desc = f"{window_start.isoformat()} to {most_recent_date.isoformat()}"

    total_buy_value = float(sum(t.value for t in in_window))

    # 7. Apply optional multipliers.
    if price_drawdown_pct is not None and price_drawdown_pct < _DRAWDOWN_THRESHOLD:
        weighted_score *= _DRAWDOWN_MULTIPLIER

    if apply_magnitude:
        weighted_score *= _magnitude_boost(total_buy_value)

    detail = (
        f"{distinct_count} distinct insider(s) in {_CLUSTER_WINDOW_DAYS}-day window "
        f"({window_desc}); "
        f"weighted_score={weighted_score:.1f}; "
        f"cluster={'YES' if is_cluster else 'NO'} (need 3+); "
        f"insiders: {', '.join(insider_weights)}"
    )

    return FactorScore(
        name="insider_cluster",
        raw_value=weighted_score,
        percentile_rank=0.0,
        detail=detail,
        metadata={
            "cluster_buy_detected": is_cluster,
            "n_distinct_insiders": distinct_count,
            "total_buy_value": total_buy_value,
            "window_start": window_start.isoformat(),
            "window_end": most_recent_date.isoformat(),
        },
    )
