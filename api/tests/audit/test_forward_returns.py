from __future__ import annotations

from datetime import date

import pytest
from margin_api.audit.forward_returns import compute_total_return


def test_compute_total_return_simple() -> None:
    prices = {date(2026, 1, 5): 100.0, date(2026, 2, 5): 110.0}
    assert compute_total_return(prices, date(2026, 1, 5), date(2026, 2, 5)) == pytest.approx(0.10)


def test_compute_total_return_missing_endpoint_returns_none() -> None:
    prices = {date(2026, 1, 5): 100.0}
    assert compute_total_return(prices, date(2026, 1, 5), date(2026, 2, 5)) is None


def test_compute_total_return_zero_start_returns_none() -> None:
    prices = {date(2026, 1, 5): 0.0, date(2026, 2, 5): 110.0}
    assert compute_total_return(prices, date(2026, 1, 5), date(2026, 2, 5)) is None
