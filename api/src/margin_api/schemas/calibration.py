"""Calibration status response schema."""

from __future__ import annotations

from pydantic import BaseModel


class CalibrationStatusResponse(BaseModel):
    """Current calibration status of the scoring engine."""

    pit_data_available: bool
    pit_date_range_start: str | None = None
    pit_date_range_end: str | None = None
    pit_ticker_count: int = 0
    last_backtest_run: str | None = None
    validation_passed: bool | None = None
    validation_details: dict | None = None
    current_thresholds: dict
    scoring_version: str = "v4"
