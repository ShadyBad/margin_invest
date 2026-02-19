"""Valuation audit models — full computation trail for price targets."""

from __future__ import annotations

from pydantic import BaseModel


class MethodAudit(BaseModel):
    """Audit data for a single valuation method."""

    method: str  # "dcf", "ev_fcf", "acquirers", "shy"
    result_per_share: float | None = None
    weight: float  # original weight (e.g., 0.35)
    renormalized_weight: float | None = None  # after excluding methods
    included: bool = True
    exclusion_reason: str | None = None  # e.g., "negative FCF", "15x median outlier"
    inputs: dict[str, float] = {}  # e.g., {"fcf": 110e9, "growth_rate": 0.05}
    intermediates: dict[str, float] = {}  # e.g., {"pv_stage1": 1.2e12, "terminal_value": 2.8e12}


class ValuationAudit(BaseModel):
    """Full audit for the consensus valuation computation."""

    margin_invest_value: float | None = None
    margin_of_safety: float | None = None
    buy_price: float | None = None
    sell_price: float | None = None
    actual_price: float | None = None
    methods: list[MethodAudit] = []
    mos_base: float | None = None  # base MoS for growth stage
    mos_cv: float | None = None  # coefficient of variation of methods
    mos_adjustment: float | None = None  # CV-based adjustment
    was_clamped: bool = False
    clamp_reason: str | None = None
