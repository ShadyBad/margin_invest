"""Response schemas for the valuation audit endpoint."""

from __future__ import annotations

from pydantic import BaseModel


class MethodAuditResponse(BaseModel):
    method: str
    result_per_share: float | None = None
    weight: float
    renormalized_weight: float | None = None
    included: bool = True
    exclusion_reason: str | None = None
    inputs: dict[str, float] = {}
    intermediates: dict[str, float] = {}


class ValuationAuditResponse(BaseModel):
    margin_invest_value: float | None = None
    margin_of_safety: float | None = None
    buy_price: float | None = None
    sell_price: float | None = None
    actual_price: float | None = None
    methods: list[MethodAuditResponse] = []
    mos_base: float | None = None
    mos_cv: float | None = None
    mos_adjustment: float | None = None
    was_clamped: bool = False
    clamp_reason: str | None = None
