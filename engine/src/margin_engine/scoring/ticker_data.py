"""Shared base model for scoring pipeline ticker data."""

from __future__ import annotations

from pydantic import BaseModel

from margin_engine.models.financial import AssetProfile, FinancialHistory, FinancialPeriod


class TickerDataBase(BaseModel):
    """Shared fields for all scoring pipeline ticker data."""

    ticker: str
    history: FinancialHistory
    latest_period: FinancialPeriod
    profile: AssetProfile
    current_price: float
    current_fcf_per_share: float
    sustainable_growth_rate: float
    buyback_yield: float | None = None
    insider_ownership_pct: float | None = None
    sbc_pct: float | None = None
    recent_acquisition_count: int = 0
    sue_percentile: float = 0.0
    beta: float | None = None
    momentum_percentile: float = 50.0
    dcf_iv: float = 0.0

    # Score modifier inputs (Tier B)
    fundamental_trajectory: float = 0.5
    high_52w: float | None = None
    short_interest_percentile: float = 50.0
    analyst_divergence: float = 0.0
    eps_revision_strength: float = 0.0
    insider_cluster_score_value: float = 0.0
    insider_cluster_detected: bool = False
    insider_total_buy_value: float = 0.0
    insider_has_first_buy: bool = False
