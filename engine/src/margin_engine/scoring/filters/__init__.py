"""Elimination filters for the scoring pipeline."""

from margin_engine.scoring.filters.altman import altman_z_score
from margin_engine.scoring.filters.beneish import beneish_m_score
from margin_engine.scoring.filters.current_ratio import (
    current_ratio_check,
    current_ratio_check_v2,
)
from margin_engine.scoring.filters.fcf_distress import (
    fcf_distress_check,
    fcf_distress_check_v2,
)
from margin_engine.scoring.filters.interest_coverage import interest_coverage_check
from margin_engine.scoring.filters.liquidity import liquidity_check, liquidity_check_v2
from margin_engine.scoring.filters.pipeline import PipelineResult, run_elimination_filters

__all__ = [
    "altman_z_score",
    "beneish_m_score",
    "current_ratio_check",
    "current_ratio_check_v2",
    "fcf_distress_check",
    "fcf_distress_check_v2",
    "interest_coverage_check",
    "liquidity_check",
    "liquidity_check_v2",
    "PipelineResult",
    "run_elimination_filters",
]
