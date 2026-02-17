"""Scoring package — exports for the conviction engine (v1 + v2 dual-track)."""

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
]
