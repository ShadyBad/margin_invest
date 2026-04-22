"""Pydantic schemas for the risk factor diffing API."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel


class MaterialChangeResponse(BaseModel):
    change_type: str
    topic: str
    severity: int
    summary_50_words: str
    verbatim_new_text: str | None = None
    verbatim_old_text: str | None = None


class RiskFactorAnalysisResponse(BaseModel):
    ticker: str
    current_period: date
    prior_period: date
    overall_risk_delta_score: float
    model_confidence: float
    material_changes: list[MaterialChangeResponse]
    prompt_version: str
    analyzed_at: datetime
