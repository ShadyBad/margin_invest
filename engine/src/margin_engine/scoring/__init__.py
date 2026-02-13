"""Scoring package — Phase 6 exports for the conviction engine."""

from margin_engine.scoring.classifier import classify_growth_stage
from margin_engine.scoring.composite import compute_composite_score
from margin_engine.scoring.normalizer import compute_percentile_ranks, sector_neutral_ranks

__all__ = [
    "classify_growth_stage",
    "compute_composite_score",
    "compute_percentile_ranks",
    "sector_neutral_ranks",
]
