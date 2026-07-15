"""Holiday-aware trading day detection using NYSE calendar."""

from __future__ import annotations

from datetime import date

import pandas_market_calendars as mcal


def is_trading_day(d: date) -> bool:
    """Return True if the given date is a NYSE trading day."""
    nyse = mcal.get_calendar("NYSE")
    schedule = nyse.schedule(start_date=d.isoformat(), end_date=d.isoformat())
    return len(schedule) > 0
