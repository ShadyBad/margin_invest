"""Quantitative scoring factors for the Margin scoring engine."""

from margin_engine.scoring.quantitative.accrual_ratio import sloan_accrual_ratio
from margin_engine.scoring.quantitative.acquirers_multiple import acquirers_multiple

# v3 quantitative exports
from margin_engine.scoring.quantitative.asset_floor import asset_floor_valuation
from margin_engine.scoring.quantitative.capital_allocation import (
    ma_discipline,
    sbc_dilution_tax,
)
from margin_engine.scoring.quantitative.dcf_mos import dcf_margin_of_safety
from margin_engine.scoring.quantitative.ensemble_valuation import (
    EnsembleResult,
    compute_ensemble_valuation,
)
from margin_engine.scoring.quantitative.ev_fcf import ev_fcf
from margin_engine.scoring.quantitative.f_score import (
    compute_f_score_signals,
    piotroski_f_score,
)
from margin_engine.scoring.quantitative.gross_profitability import gross_profitability
from margin_engine.scoring.quantitative.insider_cluster import insider_cluster_score
from margin_engine.scoring.quantitative.institutional_accumulation import (
    institutional_accumulation,
)
from margin_engine.scoring.quantitative.moat_durability import moat_durability_score
from margin_engine.scoring.quantitative.price_momentum import price_momentum
from margin_engine.scoring.quantitative.price_targets import (
    PriceTargets,
    compute_price_targets,
)
from margin_engine.scoring.quantitative.reverse_dcf import (
    reverse_dcf_growth_gap,
    solve_implied_growth_rate,
)
from margin_engine.scoring.quantitative.roic_wacc import compute_roic, roic_wacc_spread
from margin_engine.scoring.quantitative.sentiment_score import sentiment_score
from margin_engine.scoring.quantitative.shareholder_yield import shareholder_yield
from margin_engine.scoring.quantitative.sue import sue_score
from margin_engine.scoring.quantitative.wacc_sector import get_sector_wacc

__all__ = [
    "EnsembleResult",
    "PriceTargets",
    "acquirers_multiple",
    "compute_ensemble_valuation",
    "compute_f_score_signals",
    "compute_price_targets",
    "compute_roic",
    "dcf_margin_of_safety",
    "ev_fcf",
    "gross_profitability",
    "insider_cluster_score",
    "institutional_accumulation",
    "piotroski_f_score",
    "price_momentum",
    "roic_wacc_spread",
    "sentiment_score",
    "shareholder_yield",
    "sloan_accrual_ratio",
    "sue_score",
    # v3 quantitative exports
    "asset_floor_valuation",
    "ma_discipline",
    "moat_durability_score",
    "reverse_dcf_growth_gap",
    "sbc_dilution_tax",
    "solve_implied_growth_rate",
    "get_sector_wacc",
]
