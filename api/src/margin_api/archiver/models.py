"""Pydantic models for the daily picks archive snapshot schema (v1.0.0)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class TrackScoreDetail(BaseModel):
    score: float
    qualifies: bool
    gates_passed: int
    total_gates: int


class PillarDetail(BaseModel):
    factors: dict[str, float]


class ModifierDetail(BaseModel):
    liquidity: float = 0.0
    insider_signal: float = 0.0
    inflection: float = 0.0
    tam: float = 0.0
    anti_consensus: float = 0.0


class MLDetail(BaseModel):
    alpha: float | None = None
    confidence: float | None = None
    override: str = "none"


class PickEntry(BaseModel):
    rank: int = Field(ge=1)
    ticker: str
    composite_score: float
    conviction: str
    opportunity_type: str
    style: str
    track_scores: dict[str, TrackScoreDetail]
    pillars: dict[str, PillarDetail]
    modifiers: ModifierDetail
    ml: MLDetail
    sector: str
    market_cap_usd: int
    price_at_close: float


class ExclusionSummary(BaseModel):
    conviction_none: int = 0


class HashChain(BaseModel):
    previous_date: str | None = None
    previous_payload_hash: str | None = None


class SnapshotPayload(BaseModel):
    snapshot_version: str = "1.0.0"
    snapshot_date: str
    generated_at_utc: datetime
    market_close_time: datetime
    universe_size: int
    methodology_version: str = "4.0.0"
    model_hash: str
    input_data_hash: str
    top_picks: list[PickEntry]
    excluded_count: int
    exclusion_summary: ExclusionSummary
    hash_chain: HashChain
    payload_hash: str
