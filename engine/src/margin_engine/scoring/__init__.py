"""Scoring package — exports for the conviction engine (v1 + v2 + v3)."""

from margin_engine.scoring.classifier import classify_growth_stage
from margin_engine.scoring.composite import compute_composite_score
from margin_engine.scoring.composite_compounder import compute_compounder_score
from margin_engine.scoring.composite_mispricing import compute_mispricing_score
from margin_engine.scoring.conviction_gates import check_track_a_gates, check_track_b_gates
from margin_engine.scoring.dual_track import score_dual_track
from margin_engine.scoring.filters.mediocrity_gate import mediocrity_gate
from margin_engine.scoring.normalizer import (
    compute_percentile_ranks,
    rerank_composites,
    sector_neutral_ranks,
)
from margin_engine.scoring.opportunity_classifier import classify_opportunity_type
from margin_engine.scoring.position_sizing import compute_position_size
from margin_engine.scoring.timing_overlay import compute_timing_signal
# v3 exports
from margin_engine.scoring.market_regime import MarketRegime, detect_regime, regime_adjustments
from margin_engine.scoring.timing_overlay import compute_v3_timing_signal
from margin_engine.scoring.v3_composite import compute_track_a_score, compute_track_b_score
from margin_engine.scoring.v3_orchestrator import V3Result, V3TrackResult, orchestrate_v3
from margin_engine.scoring.v3_position_sizing import MAX_POSITIONS, compute_v3_position_size
from margin_engine.scoring.v3_thresholds import assess_track_a_conviction, assess_track_b_conviction
# v3 cascade exports
from margin_engine.scoring.v3_cascade import TrackAInputs, TrackBInputs, run_track_a_cascade, run_track_b_cascade
from margin_engine.scoring.v3_intermediates import (
    compute_capital_allocation_composite,
    compute_catalyst_strength,
    compute_compounding_power,
    compute_downside_protection,
    compute_owner_earnings_iv,
    compute_quality_floor_factor,
    compute_valuation_convergence_factor,
)
from margin_engine.scoring.v3_pipeline import TickerV3Data, score_universe_v3
# Risk metrics exports
from margin_engine.scoring.risk_metrics import (
    RiskMetrics,
    compute_max_drawdown,
    compute_risk_metrics,
    compute_sharpe_ratio,
    compute_volatility,
)

__all__ = [
    # v1 exports
    "classify_growth_stage",
    "compute_composite_score",
    "compute_percentile_ranks",
    "rerank_composites",
    "sector_neutral_ranks",
    # v2 dual-track exports
    "classify_opportunity_type",
    "compute_compounder_score",
    "compute_mispricing_score",
    "score_dual_track",
    "compute_timing_signal",
    "compute_position_size",
    "check_track_a_gates",
    "check_track_b_gates",
    "mediocrity_gate",
    # v3 exports
    "MarketRegime",
    "MAX_POSITIONS",
    "V3Result",
    "V3TrackResult",
    "assess_track_a_conviction",
    "assess_track_b_conviction",
    "compute_track_a_score",
    "compute_track_b_score",
    "compute_v3_position_size",
    "compute_v3_timing_signal",
    "detect_regime",
    "orchestrate_v3",
    "regime_adjustments",
    # v3 cascade exports
    "TrackAInputs",
    "TrackBInputs",
    "TickerV3Data",
    "compute_capital_allocation_composite",
    "compute_catalyst_strength",
    "compute_compounding_power",
    "compute_downside_protection",
    "compute_owner_earnings_iv",
    "compute_quality_floor_factor",
    "compute_valuation_convergence_factor",
    "run_track_a_cascade",
    "run_track_b_cascade",
    "score_universe_v3",
    # Risk metrics exports
    "RiskMetrics",
    "compute_max_drawdown",
    "compute_risk_metrics",
    "compute_sharpe_ratio",
    "compute_volatility",
]
