"""Rarity engine orchestrator.

Coordinates all rarity signals, computes composite scores,
applies the gate cascade, and produces RarityResult for each stock.
"""

from __future__ import annotations

import numpy as np

from margin_engine.models.scoring import CompositeScore
from margin_engine.rarity.combination_signature import build_signature
from margin_engine.rarity.convergence import compute_convergence
from margin_engine.rarity.historical_rarity import compute_historical_frequency
from margin_engine.rarity.joint_rarity import compute_all_joint_rarities
from margin_engine.rarity.models import (
    RarityConfig,
    RarityDimensionScores,
    RarityRegime,
    RarityResult,
)
from margin_engine.rarity.pillar_extraction import extract_pillar_percentiles
from margin_engine.rarity.quality_momentum import compute_quality_momentum
from margin_engine.rarity.regime import compute_regime_alignment
from margin_engine.rarity.smart_money import compute_smart_money_convergence


def _build_factor_matrix(all_pillars: list[dict[str, float]]) -> np.ndarray:
    """Build N×4 numpy matrix. Col 2 = momentum or catalyst; col 3 = growth (NaN if missing)."""
    rows = []
    for pillars in all_pillars:
        row = [
            pillars.get("quality", 0.0),
            pillars.get("value", 0.0),
            pillars.get("momentum", pillars.get("catalyst", 0.0)),
            pillars.get("growth", float("nan")),
        ]
        rows.append(row)
    return np.array(rows, dtype=np.float64)


def _extract_smart_money_signals(
    composite: CompositeScore,
) -> tuple[float, float, dict | None, dict | None]:
    """Extract accumulation and insider signals from CompositeScore sub_scores."""
    accum_pctl = 50.0
    insider_pctl = 50.0
    accum_meta = None
    insider_meta = None

    breakdowns = [composite.quality, composite.value, composite.momentum]
    for bd in [composite.growth, composite.capital_allocation, composite.catalyst]:
        if bd is not None:
            breakdowns.append(bd)

    for breakdown in breakdowns:
        for sub in breakdown.sub_scores:
            name_lower = sub.name.lower()
            if "accumulation" in name_lower or "institutional" in name_lower:
                accum_pctl = sub.percentile_rank
                accum_meta = sub.metadata
            elif "insider" in name_lower or "cluster" in name_lower:
                insider_pctl = sub.percentile_rank
                insider_meta = sub.metadata

    return accum_pctl, insider_pctl, accum_meta, insider_meta


def compute_rarity_for_universe(
    composites: list[CompositeScore],
    regime: RarityRegime,
    historical_snapshots: list[dict],
    config: RarityConfig | None = None,
    historical_pillars_by_ticker: dict[str, list[dict[str, float]]] | None = None,
) -> list[RarityResult]:
    """Compute rarity scores for all composites in the universe."""
    if not composites:
        return []

    if config is None:
        config = RarityConfig()
    if historical_pillars_by_ticker is None:
        historical_pillars_by_ticker = {}

    # 1. Extract pillars
    all_pillars = [extract_pillar_percentiles(c) for c in composites]

    # 2. Build factor matrix and compute joint rarity
    matrix = _build_factor_matrix(all_pillars)
    joint_rarities = compute_all_joint_rarities(matrix)

    # 3. Per-stock scoring
    results: list[RarityResult] = []
    for i, composite in enumerate(composites):
        pillars = all_pillars[i]
        pillar_values = list(pillars.values())

        joint_rarity_pctl = joint_rarities[i]
        convergence = compute_convergence(pillar_values)
        signature = build_signature(pillars)
        hist_score = compute_historical_frequency(signature, historical_snapshots)
        hist_pillars = historical_pillars_by_ticker.get(composite.ticker, [])
        qm_score = compute_quality_momentum(pillars, hist_pillars)

        accum_pctl, insider_pctl, accum_meta, insider_meta = _extract_smart_money_signals(composite)
        sm_score = compute_smart_money_convergence(
            accum_pctl, insider_pctl, accum_meta, insider_meta
        )

        winning_track = composite.winning_track or "compounder"
        regime_score = compute_regime_alignment(regime, winning_track)

        rarity_score = (
            config.joint_rarity_weight * joint_rarity_pctl
            + config.convergence_weight * convergence
            + config.historical_rarity_weight * hist_score
            + config.quality_momentum_weight * qm_score
            + config.smart_money_weight * sm_score
            + config.regime_alignment_weight * regime_score
        )
        rarity_score = round(min(max(rarity_score, 0.0), 100.0), 2)

        tier = composite.composite_tier
        gate1 = tier in ("exceptional", "high")
        gate2 = all(p >= config.min_pillar_pctl for p in pillar_values) if gate1 else False
        gate3 = convergence >= config.convergence_gate if gate2 else False
        gate4 = rarity_score >= config.rarity_score_gate if gate3 else False

        n_pillars = len(pillar_values)
        pillars_above_80 = sum(1 for p in pillar_values if p >= 80)
        required_above_80 = 3 if n_pillars >= 4 else 2
        is_generational = (
            joint_rarity_pctl >= config.generational_joint_rarity_pctl
            and all(p >= config.min_pillar_pctl for p in pillar_values)
            and pillars_above_80 >= required_above_80
            and hist_score >= (1.0 - config.generational_hist_freq) * 100
            and composite.composite_raw_score >= config.generational_composite_raw
        )

        results.append(
            RarityResult(
                ticker=composite.ticker,
                rarity_score=rarity_score,
                dimensions=RarityDimensionScores(
                    joint_rarity_pctl=joint_rarity_pctl,
                    convergence_score=convergence,
                    historical_frequency=hist_score,
                    quality_momentum=qm_score,
                    smart_money_score=sm_score,
                    regime_alignment=regime_score,
                ),
                combination_signature=signature,
                pillar_percentiles=pillars,
                regime=regime,
                is_generational=is_generational,
                passed_gates=[gate1, gate2, gate3, gate4],
                universe_size=len(composites),
                composite_raw_score=composite.composite_raw_score,
                composite_tier=composite.composite_tier,
            ),
        )

    return results
