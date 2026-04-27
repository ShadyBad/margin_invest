from __future__ import annotations

from datetime import date

import pytest
from margin_api.audit.forward_returns import compute_part_a, compute_total_return
from margin_api.audit.schema import DataStatus
from sqlalchemy.ext.asyncio import AsyncSession


def test_compute_total_return_simple() -> None:
    prices = {date(2026, 1, 5): 100.0, date(2026, 2, 5): 110.0}
    assert compute_total_return(prices, date(2026, 1, 5), date(2026, 2, 5)) == pytest.approx(0.10)


def test_compute_total_return_missing_endpoint_returns_none() -> None:
    prices = {date(2026, 1, 5): 100.0}
    assert compute_total_return(prices, date(2026, 1, 5), date(2026, 2, 5)) is None


def test_compute_total_return_zero_start_returns_none() -> None:
    prices = {date(2026, 1, 5): 0.0, date(2026, 2, 5): 110.0}
    assert compute_total_return(prices, date(2026, 1, 5), date(2026, 2, 5)) is None


@pytest.mark.asyncio
async def test_compute_part_a_emits_one_row_per_candidate(
    synthetic_audit_db: AsyncSession,
) -> None:
    """Part A emits exactly one row per scored candidate, regardless of data availability."""
    rows = await compute_part_a(
        session=synthetic_audit_db,
        report_date=date(2026, 4, 27),
        windows=(30, 60, 63),
    )
    assert len(rows) == 3
    by_ticker = {r.ticker: r for r in rows}

    # AAPL and MSFT should have complete 30d, 60d, 63d returns (windows closed)
    assert by_ticker["AAPL"].alpha_60d is not None
    assert by_ticker["MSFT"].alpha_60d is not None

    # DEAD should have no candidate returns (data unavailable)
    assert by_ticker["DEAD"].candidate_return_30d is None
    assert by_ticker["DEAD"].data_status == DataStatus.DATA_UNAVAILABLE

    # SPY returns should always be present when windows are closed
    assert by_ticker["DEAD"].spy_return_30d is not None
