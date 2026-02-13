"""Quantitative scoring factors for the Margin scoring engine."""

from margin_engine.scoring.quantitative.accrual_ratio import sloan_accrual_ratio
from margin_engine.scoring.quantitative.acquirers_multiple import acquirers_multiple
from margin_engine.scoring.quantitative.dcf_mos import dcf_margin_of_safety
from margin_engine.scoring.quantitative.ev_fcf import ev_fcf
from margin_engine.scoring.quantitative.f_score import (
    compute_f_score_signals,
    piotroski_f_score,
)
from margin_engine.scoring.quantitative.gross_profitability import gross_profitability
from margin_engine.scoring.quantitative.roic_wacc import compute_roic, roic_wacc_spread
from margin_engine.scoring.quantitative.shareholder_yield import shareholder_yield

__all__ = [
    "acquirers_multiple",
    "compute_f_score_signals",
    "compute_roic",
    "dcf_margin_of_safety",
    "ev_fcf",
    "gross_profitability",
    "piotroski_f_score",
    "roic_wacc_spread",
    "shareholder_yield",
    "sloan_accrual_ratio",
]
