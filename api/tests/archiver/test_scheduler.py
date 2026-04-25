"""Tests for holiday-aware trading day detection."""

from __future__ import annotations

from datetime import date

from margin_api.archiver.scheduler import is_trading_day


class TestIsTradingDay:
    def test_normal_weekday(self) -> None:
        assert is_trading_day(date(2026, 4, 21)) is True

    def test_saturday(self) -> None:
        assert is_trading_day(date(2026, 4, 25)) is False

    def test_sunday(self) -> None:
        assert is_trading_day(date(2026, 4, 26)) is False

    def test_mlk_day_2026(self) -> None:
        assert is_trading_day(date(2026, 1, 19)) is False

    def test_christmas_2026(self) -> None:
        assert is_trading_day(date(2026, 12, 25)) is False

    def test_day_after_thanksgiving_is_open(self) -> None:
        assert is_trading_day(date(2026, 11, 27)) is True

    def test_new_years_day_2026(self) -> None:
        assert is_trading_day(date(2026, 1, 1)) is False

    def test_independence_day_observed_2026(self) -> None:
        assert is_trading_day(date(2026, 7, 3)) is False

    def test_normal_friday(self) -> None:
        assert is_trading_day(date(2026, 4, 24)) is True
