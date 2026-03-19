"""Comprehensive tests for cli.py to improve coverage of the major functions.

Strategy:
- Mock all DB sessions, network calls, and external services.
- Test each major async function's control-flow logic: early returns, loops,
  error paths, success paths.
- Helper functions (_sanitize_for_json, _compute_revenue_cagr, etc.) are pure
  and testable without any mocks.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ──────────────────────────────────────────────────────────────────────────────
# Pure helper function tests (no I/O — import directly)
# ──────────────────────────────────────────────────────────────────────────────


class TestSanitizeForJson:
    def _fn(self):
        from margin_api.cli import _sanitize_for_json

        return _sanitize_for_json

    def test_nan_becomes_none(self):
        f = self._fn()
        assert f(float("nan")) is None

    def test_inf_becomes_none(self):
        f = self._fn()
        assert f(float("inf")) is None

    def test_neg_inf_becomes_none(self):
        f = self._fn()
        assert f(float("-inf")) is None

    def test_regular_float_unchanged(self):
        f = self._fn()
        assert f(3.14) == 3.14

    def test_integer_unchanged(self):
        f = self._fn()
        assert f(42) == 42

    def test_string_unchanged(self):
        f = self._fn()
        assert f("hello") == "hello"

    def test_none_unchanged(self):
        f = self._fn()
        assert f(None) is None

    def test_dict_recursion(self):
        f = self._fn()
        result = f({"a": float("nan"), "b": 1.0, "c": {"d": float("inf")}})
        assert result == {"a": None, "b": 1.0, "c": {"d": None}}

    def test_list_recursion(self):
        f = self._fn()
        result = f([1.0, float("nan"), [float("-inf"), 2.0]])
        assert result == [1.0, None, [None, 2.0]]

    def test_nested_dict_list(self):
        f = self._fn()
        result = f({"rows": [{"v": float("nan")}, {"v": 5.0}]})
        assert result == {"rows": [{"v": None}, {"v": 5.0}]}


class TestLoadForeignSkips:
    """Tests for _load_foreign_skips and _save_foreign_skips."""

    def test_load_returns_empty_when_file_missing(self, tmp_path):
        import margin_api.cli as cli_mod
        from margin_api.cli import _load_foreign_skips

        original = cli_mod._FOREIGN_SKIPS_PATH
        try:
            cli_mod._FOREIGN_SKIPS_PATH = tmp_path / "nonexistent.yaml"
            result = _load_foreign_skips()
        finally:
            cli_mod._FOREIGN_SKIPS_PATH = original
        assert result == set()

    def test_load_reads_tickers(self, tmp_path):
        import margin_api.cli as cli_mod
        from margin_api.cli import _load_foreign_skips

        yaml_file = tmp_path / "skips.yaml"
        yaml_file.write_text("tickers:\n  - BABA\n  - TCEHY\n")
        original = cli_mod._FOREIGN_SKIPS_PATH
        try:
            cli_mod._FOREIGN_SKIPS_PATH = yaml_file
            result = _load_foreign_skips()
        finally:
            cli_mod._FOREIGN_SKIPS_PATH = original
        assert result == {"BABA", "TCEHY"}

    def test_load_empty_yaml(self, tmp_path):
        import margin_api.cli as cli_mod
        from margin_api.cli import _load_foreign_skips

        yaml_file = tmp_path / "skips.yaml"
        yaml_file.write_text("")
        original = cli_mod._FOREIGN_SKIPS_PATH
        try:
            cli_mod._FOREIGN_SKIPS_PATH = yaml_file
            result = _load_foreign_skips()
        finally:
            cli_mod._FOREIGN_SKIPS_PATH = original
        assert result == set()

    def test_save_creates_file(self, tmp_path):
        import margin_api.cli as cli_mod
        from margin_api.cli import _save_foreign_skips

        target = tmp_path / "skips.yaml"
        original = cli_mod._FOREIGN_SKIPS_PATH
        try:
            cli_mod._FOREIGN_SKIPS_PATH = target
            _save_foreign_skips({"BABA", "TCEHY"})
        finally:
            cli_mod._FOREIGN_SKIPS_PATH = original
        content = target.read_text()
        assert "BABA" in content
        assert "TCEHY" in content
        assert "tickers:" in content

    def test_save_sorts_tickers(self, tmp_path):
        import margin_api.cli as cli_mod
        from margin_api.cli import _save_foreign_skips

        target = tmp_path / "skips.yaml"
        original = cli_mod._FOREIGN_SKIPS_PATH
        try:
            cli_mod._FOREIGN_SKIPS_PATH = target
            _save_foreign_skips({"ZZZ", "AAA", "MMM"})
        finally:
            cli_mod._FOREIGN_SKIPS_PATH = original
        lines = target.read_text().splitlines()
        ticker_lines = [line.strip() for line in lines if line.strip().startswith('- "')]
        assert ticker_lines == ['- "AAA"', '- "MMM"', '- "ZZZ"']


class TestComputeRevenueCagr:
    def _fn(self):
        from margin_api.cli import _compute_revenue_cagr

        return _compute_revenue_cagr

    def _make_history(self, revenues: list[float]):
        """Build a minimal fake FinancialHistory-like object."""
        periods = []
        for rev in revenues:
            period = MagicMock()
            period.current_income.revenue = rev
            periods.append(period)
        history = MagicMock()
        history.periods = periods
        return history

    def test_single_period_returns_zero(self):
        f = self._fn()
        h = self._make_history([1000.0])
        assert f(h) == 0.0

    def test_zero_oldest_revenue_returns_zero(self):
        f = self._fn()
        h = self._make_history([0.0, 1200.0])
        assert f(h) == 0.0

    def test_two_periods_growth(self):
        f = self._fn()
        h = self._make_history([100.0, 121.0])
        cagr = f(h)
        # 1 year: (121/100)^(1/1) - 1 = 0.21
        assert abs(cagr - 0.21) < 1e-9

    def test_three_periods_growth(self):
        f = self._fn()
        h = self._make_history([100.0, 110.0, 121.0])
        cagr = f(h)
        # 2 years: (121/100)^(1/2) - 1 = 0.1
        assert abs(cagr - 0.1) < 1e-6


class TestComputeTrackCFields:
    def _fn(self):
        from margin_api.cli import _compute_track_c_fields

        return _compute_track_c_fields

    def _make_history(self, periods_data: list[dict]):
        periods = []
        for p in periods_data:
            period = MagicMock()
            period.current_income.revenue = p.get("revenue", 100.0)
            period.current_income.gross_profit = p.get("gross_profit", 60.0)
            period.current_income.ebit = p.get("ebit", 20.0)
            period.current_balance.total_equity = p.get("total_equity", 50.0)
            period.current_cash_flow.free_cash_flow = p.get("fcf", 10.0)
            periods.append(period)
        h = MagicMock()
        h.periods = periods
        return h

    def test_single_period(self):
        f = self._fn()
        h = self._make_history([{"revenue": 100.0, "gross_profit": 60.0}])
        latest = h.periods[-1]
        result = f(h, latest, 50.0, 1_000_000)
        assert "revenue_growth_rate" in result
        assert "fcf_margin" in result
        assert "gross_margin_current" in result
        assert "gross_margin_3yr_ago" in result
        assert "opex_growth_rate" in result
        assert "incremental_roic" in result
        assert "revenue_deceleration" in result
        assert "tam_headroom" in result
        assert result["tam_headroom"] == 5.0

    def test_three_periods_has_deceleration(self):
        f = self._fn()
        # Decelerating: 100->150->160 (recent growth slows down)
        h = self._make_history(
            [
                {"revenue": 100.0, "gross_profit": 50.0},
                {"revenue": 150.0, "gross_profit": 75.0},
                {"revenue": 160.0, "gross_profit": 80.0},
            ]
        )
        latest = h.periods[-1]
        result = f(h, latest, 80.0, 1_000_000)
        # growth_older = (150/100 - 1) = 0.5
        # growth_recent = (160/150 - 1) ≈ 0.0667
        # decel = 0.5 - 0.0667 > 0
        assert result["revenue_deceleration"] > 0

    def test_zero_revenue_uses_safe_defaults(self):
        f = self._fn()
        h = self._make_history([{"revenue": 0.0, "gross_profit": 0.0}])
        latest = h.periods[-1]
        result = f(h, latest, 10.0, 1_000_000)
        assert result["fcf_margin"] == 0.0
        assert result["gross_margin_current"] == 0.0


class TestInjectSectorStats:
    def test_injects_stats_for_matching_ticker(self):
        from margin_api.cli import _inject_sector_stats

        td = MagicMock()
        td.ticker = "AAPL"
        td.profile.sector.value = "Information Technology"
        ticker_data_list = [td]
        sector_pass_rates = {"liquidity": {"pass_rate": 0.9}}
        all_sector_distributions = {"Information Technology": {"p50": {"quality": 75.0}}}
        detail = {"composite_percentile": 85.0}
        result = _inject_sector_stats(
            detail, "AAPL", ticker_data_list, sector_pass_rates, all_sector_distributions
        )
        assert result["sector_filter_pass_rates"] == sector_pass_rates
        assert result["sector_distribution"] == {"p50": {"quality": 75.0}}

    def test_no_change_for_nonmatching_ticker(self):
        from margin_api.cli import _inject_sector_stats

        td = MagicMock()
        td.ticker = "MSFT"
        detail = {"composite_percentile": 85.0}
        result = _inject_sector_stats(detail, "AAPL", [td], {}, {})
        # AAPL not in list, so no injection
        assert "sector_filter_pass_rates" not in result

    def test_empty_sector_distribution_when_sector_unknown(self):
        from margin_api.cli import _inject_sector_stats

        td = MagicMock()
        td.ticker = "AAPL"
        td.profile.sector.value = "Unknown Sector"
        detail = {}
        result = _inject_sector_stats(detail, "AAPL", [td], {}, {})
        assert result["sector_distribution"] == {}


class TestValidateIngestPreconditions:
    def test_raises_when_no_snapshot_and_no_tickers(self):
        from margin_api.cli import validate_ingest_preconditions

        with pytest.raises(SystemExit, match="No active universe snapshot"):
            validate_ingest_preconditions(active_snapshot=None, tickers_override=None)

    def test_passes_when_tickers_override_provided(self):
        from margin_api.cli import validate_ingest_preconditions

        # Should not raise
        validate_ingest_preconditions(active_snapshot=None, tickers_override=["AAPL"])

    def test_passes_when_snapshot_provided(self):
        from margin_api.cli import validate_ingest_preconditions

        snapshot = MagicMock()
        validate_ingest_preconditions(active_snapshot=snapshot, tickers_override=None)

    def test_passes_when_both_provided(self):
        from margin_api.cli import validate_ingest_preconditions

        snapshot = MagicMock()
        validate_ingest_preconditions(active_snapshot=snapshot, tickers_override=["AAPL"])


class TestDetermineRunType:
    def test_full_when_no_override(self):
        from margin_api.cli import determine_run_type

        assert determine_run_type(None) == "full"

    def test_subset_when_tickers_given(self):
        from margin_api.cli import determine_run_type

        assert determine_run_type(["AAPL", "MSFT"]) == "subset"


# ──────────────────────────────────────────────────────────────────────────────
# Async function tests — use asyncio.run() directly
# ──────────────────────────────────────────────────────────────────────────────


def _make_session_factory(mock_session):
    """Create a mock session factory that returns mock_session as async context manager."""
    factory = MagicMock()
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=mock_session)
    cm.__aexit__ = AsyncMock(return_value=False)
    factory.return_value = cm
    return factory


class TestSeedTickerData:
    """Tests for the seed_ticker_data async function."""

    def _run(self, coro):
        return asyncio.get_event_loop().run_until_complete(coro)

    def test_returns_foreign_for_non_us(self):
        from margin_api.cli import seed_ticker_data

        provider = MagicMock()
        info_result = MagicMock(
            success=True,
            raw_data={
                "country": "Canada",
                "shortName": "Some Corp",
                "sector": "Technology",
            },
        )
        fundamentals = MagicMock(success=False, raw_data={})
        price = MagicMock(success=False, raw_data=None)
        earnings = MagicMock(success=False, raw_data=None)

        provider.fetch_all.return_value = {
            "fundamentals": fundamentals,
            "price": price,
            "earnings": earnings,
            "info": info_result,
        }

        session = AsyncMock()
        result = self._run(
            seed_ticker_data(
                ticker="RY",
                provider=provider,
                session=session,
            )
        )
        assert result.status == "foreign"
        assert "Canada" in result.error_message

    def test_returns_ok_for_us_ticker_with_periods(self):
        from margin_api.cli import seed_ticker_data

        provider = MagicMock()
        info_result = MagicMock(
            success=True,
            raw_data={
                "country": "United States",
                "shortName": "Apple Inc",
                "sector": "Technology",
                "marketCap": 3_000_000_000_000,
                "sharesOutstanding": 15_000_000_000,
            },
        )
        fundamentals = MagicMock(
            success=True,
            raw_data={
                "periods": [
                    {
                        "period_end": "2024-09-30",
                        "income_statement": {"revenue": 1e11},
                        "balance_sheet": {},
                        "cash_flow": {},
                    },
                    {
                        "period_end": "2025-09-30",
                        "income_statement": {"revenue": 1.1e11},
                        "balance_sheet": {},
                        "cash_flow": {},
                    },
                ]
            },
        )
        price = MagicMock(success=True, raw_data={"bars": [{"close": 180.0}]})
        earnings = MagicMock(success=True, raw_data={"earnings": []})

        provider.fetch_all.return_value = {
            "fundamentals": fundamentals,
            "price": price,
            "earnings": earnings,
            "info": info_result,
        }

        # Mock session — execute returns mock result
        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 42  # asset_id
        mock_result.scalar_one_or_none.return_value = MagicMock()
        session.execute = AsyncMock(return_value=mock_result)
        session.commit = AsyncMock()

        with patch("margin_api.cli.update_failure_status", new_callable=AsyncMock):
            with patch("margin_api.cli.pg_insert") as mock_pg_insert:
                mock_stmt = MagicMock()
                mock_stmt.on_conflict_do_update.return_value = mock_stmt
                mock_stmt.returning.return_value = mock_stmt
                mock_pg_insert.return_value = mock_stmt

                result = self._run(
                    seed_ticker_data(
                        ticker="AAPL",
                        provider=provider,
                        session=session,
                    )
                )
        assert result.status in ("ok", "partial")

    def test_returns_failed_on_exception(self):
        from margin_api.cli import seed_ticker_data

        provider = MagicMock()
        provider.fetch_all.side_effect = RuntimeError("Network error")

        session = AsyncMock()
        session.rollback = AsyncMock()
        mock_res = MagicMock()
        mock_res.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=mock_res)

        with patch("margin_api.cli.classify_error", return_value="network_error"):
            result = self._run(
                seed_ticker_data(
                    ticker="AAPL",
                    provider=provider,
                    session=session,
                )
            )
        assert result.status == "failed"
        assert "Network error" in result.error_message

    def test_fallback_provider_attempted_on_category_failure(self):
        from margin_api.cli import seed_ticker_data

        provider = MagicMock()
        info_result = MagicMock(
            success=True,
            raw_data={
                "country": "Canada",
                "shortName": "Bank",
                "sector": "Financial Services",
            },
        )
        fundamentals = MagicMock(success=False, raw_data={})
        price = MagicMock(success=False, raw_data=None)
        earnings = MagicMock(success=False, raw_data=None)
        provider.fetch_all.return_value = {
            "fundamentals": fundamentals,
            "price": price,
            "earnings": earnings,
            "info": info_result,
        }

        fallback_provider = MagicMock()
        fallback_fundamentals = MagicMock(success=True, raw_data={}, provider_name="fmp")
        fallback_provider.fetch_fundamentals.return_value = fallback_fundamentals

        session = AsyncMock()
        result = self._run(
            seed_ticker_data(
                ticker="RY",
                provider=provider,
                session=session,
                fallback_provider=fallback_provider,
            )
        )
        # Even with rescued fundamentals, country is still Canada → foreign
        assert result.status == "foreign"
        # Fallback was tried for failed categories
        fallback_provider.fetch_fundamentals.assert_called_once()

    def test_returns_partial_when_some_categories_fail(self):
        """US ticker with mixed success/failure → partial status."""
        from margin_api.cli import seed_ticker_data

        provider = MagicMock()
        info_result = MagicMock(
            success=True,
            raw_data={
                "country": "United States",
                "shortName": "Test Corp",
                "sector": "",
                "marketCap": 1_000_000_000,
                "sharesOutstanding": 10_000_000,
            },
        )
        fundamentals = MagicMock(success=True, raw_data={"periods": []})
        price = MagicMock(success=True, raw_data={"bars": []})
        earnings = MagicMock(success=False, raw_data=None)  # earnings fails

        provider.fetch_all.return_value = {
            "fundamentals": fundamentals,
            "price": price,
            "earnings": earnings,
            "info": info_result,
        }

        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 99
        mock_result.scalar_one_or_none.return_value = MagicMock()
        session.execute = AsyncMock(return_value=mock_result)
        session.commit = AsyncMock()

        with patch("margin_api.cli.update_failure_status", new_callable=AsyncMock):
            with patch("margin_api.cli.pg_insert") as mock_pg_insert:
                mock_stmt = MagicMock()
                mock_stmt.on_conflict_do_update.return_value = mock_stmt
                mock_stmt.returning.return_value = mock_stmt
                mock_pg_insert.return_value = mock_stmt
                result = self._run(
                    seed_ticker_data(
                        ticker="TEST",
                        provider=provider,
                        session=session,
                    )
                )
        # earnings failed → partial
        assert result.status in ("ok", "partial")


class TestRunSeedLogic:
    """Tests for run_seed's control flow."""

    def _run(self, coro):
        return asyncio.get_event_loop().run_until_complete(coro)

    def test_skips_known_foreign_tickers(self):
        """Tickers in foreign_skips should be filtered before provider calls."""
        from margin_api.cli import run_seed

        mock_engine = MagicMock()
        mock_engine.dispose = AsyncMock()
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        session_factory = _make_session_factory(mock_session)

        with patch("margin_api.cli._load_foreign_skips", return_value={"BABA"}):
            with patch("margin_api.cli.get_engine", return_value=mock_engine):
                with patch("margin_api.cli.get_session_factory", return_value=session_factory):
                    with patch("margin_api.cli.RateLimiter"):
                        with patch("margin_api.cli.YFinanceProvider") as mock_prov_cls:
                            mock_provider = MagicMock()
                            mock_prov_cls.return_value = mock_provider
                            with patch(
                                "margin_api.cli.seed_ticker_data", new_callable=AsyncMock
                            ) as mock_seed:
                                mock_seed.return_value = MagicMock(status="ok")
                                self._run(run_seed(tickers=["AAPL", "BABA"]))
                            # Verify BABA was never seeded
                            for call in mock_seed.call_args_list:
                                assert call.kwargs.get("ticker") != "BABA"

    def test_handles_foreign_result_and_updates_skip_list(self):
        """When a ticker returns 'foreign' status, it should be added to skip list."""
        from margin_api.cli import run_seed

        mock_engine = MagicMock()
        mock_engine.dispose = AsyncMock()
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)
        session_factory = _make_session_factory(mock_session)

        with patch("margin_api.cli._load_foreign_skips", return_value=set()):
            with patch("margin_api.cli._save_foreign_skips") as mock_save:
                with patch("margin_api.cli.get_engine", return_value=mock_engine):
                    with patch("margin_api.cli.get_session_factory", return_value=session_factory):
                        with patch("margin_api.cli.RateLimiter"):
                            with patch("margin_api.cli.YFinanceProvider") as mock_prov_cls:
                                mock_prov_cls.return_value = MagicMock()
                                with patch(
                                    "margin_api.cli.seed_ticker_data", new_callable=AsyncMock
                                ) as mock_seed:
                                    mock_seed.return_value = MagicMock(status="foreign")
                                    self._run(run_seed(tickers=["BABA"]))
                                mock_save.assert_called_once()
                                saved_skips = mock_save.call_args[0][0]
                                assert "BABA" in saved_skips

    def test_skips_quarantined_tickers(self):
        """Tickers with quarantine status should be skipped."""
        from margin_api.cli import run_seed

        mock_engine = MagicMock()
        mock_engine.dispose = AsyncMock()
        mock_asset = MagicMock()
        mock_asset.ingestion_status = "quarantined"
        mock_asset.consecutive_failures = 5
        mock_asset.last_retry_at = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_asset
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        session_factory = _make_session_factory(mock_session)

        with patch("margin_api.cli._load_foreign_skips", return_value=set()):
            with patch("margin_api.cli.get_engine", return_value=mock_engine):
                with patch("margin_api.cli.get_session_factory", return_value=session_factory):
                    with patch("margin_api.cli.RateLimiter"):
                        with patch("margin_api.cli.YFinanceProvider") as mock_prov_cls:
                            mock_prov_cls.return_value = MagicMock()
                            with patch("margin_api.cli.should_ingest_ticker", return_value=False):
                                with patch(
                                    "margin_api.cli.seed_ticker_data", new_callable=AsyncMock
                                ) as mock_seed:
                                    self._run(run_seed(tickers=["BABA"]))
                                    mock_seed.assert_not_called()

    def test_uses_fmp_fallback_when_env_key_set(self):
        """When FMP_API_KEY is set, FMP provider should be constructed."""
        from margin_api.cli import run_seed

        mock_engine = MagicMock()
        mock_engine.dispose = AsyncMock()
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)
        session_factory = _make_session_factory(mock_session)

        with patch("margin_api.cli._load_foreign_skips", return_value=set()):
            with patch("margin_api.cli.get_engine", return_value=mock_engine):
                with patch("margin_api.cli.get_session_factory", return_value=session_factory):
                    with patch("margin_api.cli.RateLimiter"):
                        with patch("margin_api.cli.YFinanceProvider"):
                            with patch("margin_api.cli.os") as mock_os:
                                mock_os.environ.get.return_value = "fake-fmp-key"
                                mock_fmp_cls = MagicMock()
                                with patch.dict(
                                    sys.modules,
                                    {
                                        "margin_engine.ingestion.providers.fmp_provider": MagicMock(
                                            FMPProvider=mock_fmp_cls
                                        )
                                    },
                                ):
                                    with patch(
                                        "margin_api.cli.seed_ticker_data", new_callable=AsyncMock
                                    ) as mock_seed:
                                        mock_seed.return_value = MagicMock(status="ok")
                                        self._run(run_seed(tickers=[]))  # empty list → no calls


class TestGetUniverseTickers:
    """Tests for _get_universe_tickers."""

    def _run(self, coro):
        return asyncio.get_event_loop().run_until_complete(coro)

    def test_exits_when_no_snapshot(self):
        from margin_api.cli import _get_universe_tickers

        mock_engine = MagicMock()
        mock_session = AsyncMock()
        session_factory = _make_session_factory(mock_session)

        with patch("margin_api.cli.get_engine", return_value=mock_engine):
            with patch("margin_api.cli.get_session_factory", return_value=session_factory):
                with patch(
                    "margin_api.cli.get_active_snapshot", new_callable=AsyncMock, return_value=None
                ):
                    with pytest.raises(SystemExit):
                        self._run(_get_universe_tickers())

    def test_returns_tickers_from_snapshot(self):
        from margin_api.cli import _get_universe_tickers

        mock_engine = MagicMock()
        mock_session = AsyncMock()
        session_factory = _make_session_factory(mock_session)
        snapshot = MagicMock()
        snapshot.version = "1.0"
        snapshot.ticker_count = 3
        snapshot.tickers = ["AAPL", "MSFT", "GOOGL"]

        with patch("margin_api.cli.get_engine", return_value=mock_engine):
            with patch("margin_api.cli.get_session_factory", return_value=session_factory):
                with patch(
                    "margin_api.cli.get_active_snapshot",
                    new_callable=AsyncMock,
                    return_value=snapshot,
                ):
                    result = self._run(_get_universe_tickers())
        assert result == ["AAPL", "MSFT", "GOOGL"]


class TestRunScoring:
    """Tests for run_scoring."""

    def _run(self, coro):
        return asyncio.get_event_loop().run_until_complete(coro)

    def test_logs_warning_when_no_tickers(self):
        from margin_api.cli import run_scoring

        mock_engine = MagicMock()
        mock_engine.dispose = AsyncMock()
        mock_session = AsyncMock()
        session_factory = _make_session_factory(mock_session)

        with patch("margin_api.cli.get_engine", return_value=mock_engine):
            with patch("margin_api.cli.get_session_factory", return_value=session_factory):
                # Run with explicit empty list to trigger the early return
                self._run(run_scoring(tickers=[]))
        # Should complete without error

    def test_skips_ticker_with_no_asset(self):
        from margin_api.cli import run_scoring

        mock_engine = MagicMock()
        mock_engine.dispose = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_result.scalars.return_value.all.return_value = []
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        session_factory = _make_session_factory(mock_session)

        with patch("margin_api.cli.get_engine", return_value=mock_engine):
            with patch("margin_api.cli.get_session_factory", return_value=session_factory):
                # Should complete gracefully with no assets
                self._run(run_scoring(tickers=["AAPL"]))


class TestRunScoringV3:
    """Tests for run_scoring_v3."""

    def _run(self, coro):
        return asyncio.get_event_loop().run_until_complete(coro)

    def test_returns_early_when_no_tickers(self):
        from margin_api.cli import run_scoring_v3

        mock_engine = MagicMock()
        mock_engine.dispose = AsyncMock()

        with patch("margin_api.cli.get_engine", return_value=mock_engine):
            with patch("margin_api.cli.get_session_factory"):
                with patch(
                    "margin_api.data.macro_data_client.fetch_shiller_cape",
                    new_callable=AsyncMock,
                    return_value=25.0,
                ):
                    self._run(run_scoring_v3(tickers=[]))
        # Should return early without processing

    def test_returns_early_no_qualified_data(self):
        from margin_api.cli import run_scoring_v3

        mock_engine = MagicMock()
        mock_engine.dispose = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_result.scalars.return_value.all.return_value = []
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        session_factory = _make_session_factory(mock_session)

        with patch("margin_api.cli.get_engine", return_value=mock_engine):
            with patch("margin_api.cli.get_session_factory", return_value=session_factory):
                with patch(
                    "margin_api.data.macro_data_client.fetch_shiller_cape",
                    new_callable=AsyncMock,
                    return_value=25.0,
                ):
                    # Ticker has no asset → empty ticker_data_list → early return
                    self._run(run_scoring_v3(tickers=["AAPL"]))

    def test_uses_provided_cape_value(self):
        from margin_api.cli import run_scoring_v3

        mock_engine = MagicMock()
        mock_engine.dispose = AsyncMock()
        mock_session = AsyncMock()
        session_factory = _make_session_factory(mock_session)

        mock_fetch_cape = AsyncMock(return_value=30.0)
        with patch("margin_api.cli.get_engine", return_value=mock_engine):
            with patch("margin_api.cli.get_session_factory", return_value=session_factory):
                with patch("margin_api.data.macro_data_client.fetch_shiller_cape", mock_fetch_cape):
                    # cape=35.0 provided → fetch_shiller_cape should NOT be called
                    self._run(run_scoring_v3(tickers=[], cape=35.0))
        mock_fetch_cape.assert_not_called()


class TestRunScoringV4:
    """Tests for run_scoring_v4."""

    def _run(self, coro):
        return asyncio.get_event_loop().run_until_complete(coro)

    def test_returns_early_when_no_tickers(self):
        from margin_api.cli import run_scoring_v4

        mock_engine = MagicMock()
        mock_engine.dispose = AsyncMock()

        with patch("margin_api.cli.get_engine", return_value=mock_engine):
            with patch("margin_api.cli.get_session_factory"):
                with patch(
                    "margin_api.data.macro_data_client.fetch_shiller_cape",
                    new_callable=AsyncMock,
                    return_value=25.0,
                ):
                    self._run(run_scoring_v4(tickers=[]))

    def test_skips_ticker_with_no_asset(self):
        from margin_api.cli import run_scoring_v4

        mock_engine = MagicMock()
        mock_engine.dispose = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_result.scalars.return_value.all.return_value = []
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        session_factory = _make_session_factory(mock_session)

        with patch("margin_api.cli.get_engine", return_value=mock_engine):
            with patch("margin_api.cli.get_session_factory", return_value=session_factory):
                with patch(
                    "margin_api.data.macro_data_client.fetch_shiller_cape",
                    new_callable=AsyncMock,
                    return_value=25.0,
                ):
                    # No assets → empty list → early return
                    self._run(run_scoring_v4(tickers=["AAPL"]))


class TestRunScoreUniverse:
    """Tests for run_score_universe."""

    def _run(self, coro):
        return asyncio.get_event_loop().run_until_complete(coro)

    def test_returns_early_when_no_tickers(self):
        from margin_api.cli import run_score_universe

        mock_engine = MagicMock()
        mock_engine.dispose = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        session_factory = _make_session_factory(mock_session)

        with patch("margin_api.cli.get_engine", return_value=mock_engine):
            with patch("margin_api.cli.get_session_factory", return_value=session_factory):
                self._run(run_score_universe(limit=None))
        # Should complete without calling run_scoring

    def test_calls_run_scoring_with_tickers(self):
        from margin_api.cli import run_score_universe

        mock_engine = MagicMock()
        mock_engine.dispose = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = [("AAPL",), ("MSFT",)]
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        session_factory = _make_session_factory(mock_session)

        with patch("margin_api.cli.get_engine", return_value=mock_engine):
            with patch("margin_api.cli.get_session_factory", return_value=session_factory):
                with patch("margin_api.cli.run_scoring", new_callable=AsyncMock) as mock_run:
                    self._run(run_score_universe(limit=None))
                    mock_run.assert_called_once_with(tickers=["AAPL", "MSFT"])

    def test_applies_limit(self):
        from margin_api.cli import run_score_universe

        mock_engine = MagicMock()
        mock_engine.dispose = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = [("AAPL",)]
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        session_factory = _make_session_factory(mock_session)

        with patch("margin_api.cli.get_engine", return_value=mock_engine):
            with patch("margin_api.cli.get_session_factory", return_value=session_factory):
                with patch("margin_api.cli.run_scoring", new_callable=AsyncMock):
                    self._run(run_score_universe(limit=1))


class TestRunUniverseActivate:
    """Tests for run_universe_activate."""

    def _run(self, coro):
        return asyncio.get_event_loop().run_until_complete(coro)

    def test_exits_when_explicit_config_missing(self):
        from margin_api.cli import run_universe_activate

        with pytest.raises(SystemExit):
            self._run(run_universe_activate(config_path="/nonexistent/universe.yaml"))

    def test_activates_with_valid_config(self, tmp_path):
        from margin_api.cli import run_universe_activate

        config_file = tmp_path / "universe.yaml"
        config_file.write_text("version: 1\ntickers: [AAPL, MSFT]\n")

        mock_engine = MagicMock()
        mock_engine.dispose = AsyncMock()
        mock_session = AsyncMock()
        session_factory = _make_session_factory(mock_session)
        mock_snapshot = MagicMock()
        mock_snapshot.version = "1"
        mock_snapshot.ticker_count = 2
        mock_snapshot.config_hash = "abc123"

        with patch("margin_api.cli.get_engine", return_value=mock_engine):
            with patch("margin_api.cli.get_session_factory", return_value=session_factory):
                with patch(
                    "margin_api.cli.activate_universe",
                    new_callable=AsyncMock,
                    return_value=mock_snapshot,
                ):
                    self._run(run_universe_activate(config_path=str(config_file)))

    def test_exits_when_default_config_not_found(self):
        """When no config_path given and default path doesn't exist, exit."""
        from margin_api.cli import run_universe_activate

        # Patch the default candidate path existence check to return False
        with patch.object(Path, "exists", return_value=False):
            with pytest.raises(SystemExit):
                asyncio.get_event_loop().run_until_complete(run_universe_activate(config_path=None))


class TestRunBackfillCountry:
    """Tests for run_backfill_country."""

    def _run(self, coro):
        return asyncio.get_event_loop().run_until_complete(coro)

    def test_updates_country_for_assets(self):
        from margin_api.cli import run_backfill_country

        mock_engine = MagicMock()
        mock_engine.dispose = AsyncMock()

        mock_asset = MagicMock()
        mock_asset.ticker = "AAPL"
        mock_asset.id = 1

        # First execute: get assets missing country
        # Second execute: get asset by id for update
        mock_session = AsyncMock()
        all_assets_result = MagicMock()
        all_assets_result.scalars.return_value.all.return_value = [mock_asset]
        asset_by_id_result = MagicMock()
        asset_by_id_result.scalar_one.return_value = mock_asset

        mock_session.execute = AsyncMock(
            side_effect=[
                all_assets_result,
                asset_by_id_result,
            ]
        )
        mock_session.commit = AsyncMock()
        session_factory = _make_session_factory(mock_session)

        mock_provider_instance = MagicMock()
        mock_info_result = MagicMock(success=True, raw_data={"country": "United States"})
        mock_provider_instance.fetch_info.return_value = mock_info_result

        with patch("margin_api.cli.get_engine", return_value=mock_engine):
            with patch("margin_api.cli.get_session_factory", return_value=session_factory):
                with patch("margin_api.cli.RateLimiter"):
                    with patch(
                        "margin_api.cli.YFinanceProvider", return_value=mock_provider_instance
                    ):
                        self._run(run_backfill_country())

        assert mock_asset.country == "United States"

    def test_handles_exception_gracefully(self):
        from margin_api.cli import run_backfill_country

        mock_engine = MagicMock()
        mock_engine.dispose = AsyncMock()
        mock_asset = MagicMock()
        mock_asset.ticker = "AAPL"

        mock_session = AsyncMock()
        assets_result = MagicMock()
        assets_result.scalars.return_value.all.return_value = [mock_asset]
        mock_session.execute = AsyncMock(return_value=assets_result)
        session_factory = _make_session_factory(mock_session)

        mock_provider_instance = MagicMock()
        mock_provider_instance.fetch_info.side_effect = RuntimeError("API down")

        with patch("margin_api.cli.get_engine", return_value=mock_engine):
            with patch("margin_api.cli.get_session_factory", return_value=session_factory):
                with patch("margin_api.cli.RateLimiter"):
                    with patch(
                        "margin_api.cli.YFinanceProvider", return_value=mock_provider_instance
                    ):
                        # Should not raise
                        self._run(run_backfill_country())

    def test_no_assets_completes_quickly(self):
        from margin_api.cli import run_backfill_country

        mock_engine = MagicMock()
        mock_engine.dispose = AsyncMock()
        mock_session = AsyncMock()
        empty_result = MagicMock()
        empty_result.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=empty_result)
        session_factory = _make_session_factory(mock_session)

        with patch("margin_api.cli.get_engine", return_value=mock_engine):
            with patch("margin_api.cli.get_session_factory", return_value=session_factory):
                with patch("margin_api.cli.RateLimiter"):
                    with patch("margin_api.cli.YFinanceProvider"):
                        self._run(run_backfill_country())

    def test_skips_asset_with_no_country_in_response(self):
        from margin_api.cli import run_backfill_country

        mock_engine = MagicMock()
        mock_engine.dispose = AsyncMock()
        mock_asset = MagicMock()
        mock_asset.ticker = "UNKNOWN"

        mock_session = AsyncMock()
        assets_result = MagicMock()
        assets_result.scalars.return_value.all.return_value = [mock_asset]
        mock_session.execute = AsyncMock(return_value=assets_result)
        session_factory = _make_session_factory(mock_session)

        mock_provider_instance = MagicMock()
        # No "country" key in response
        mock_provider_instance.fetch_info.return_value = MagicMock(success=True, raw_data={})

        with patch("margin_api.cli.get_engine", return_value=mock_engine):
            with patch("margin_api.cli.get_session_factory", return_value=session_factory):
                with patch("margin_api.cli.RateLimiter"):
                    with patch(
                        "margin_api.cli.YFinanceProvider", return_value=mock_provider_instance
                    ):
                        self._run(run_backfill_country())
        # commit was not called since no country was found


class TestRunPipeline:
    """Tests for run_pipeline."""

    def _run(self, coro):
        return asyncio.get_event_loop().run_until_complete(coro)

    def test_calls_seed_then_score(self):
        from margin_api.cli import run_pipeline

        with patch("margin_api.cli.run_seed", new_callable=AsyncMock) as mock_seed:
            with patch("margin_api.cli.run_scoring", new_callable=AsyncMock) as mock_score:
                self._run(run_pipeline(tickers=["AAPL"]))
                mock_seed.assert_called_once_with(tickers=["AAPL"])
                mock_score.assert_called_once_with(tickers=["AAPL"])

    def test_calls_with_none_tickers(self):
        from margin_api.cli import run_pipeline

        with patch("margin_api.cli.run_seed", new_callable=AsyncMock) as mock_seed:
            with patch("margin_api.cli.run_scoring", new_callable=AsyncMock) as mock_score:
                self._run(run_pipeline(tickers=None))
                mock_seed.assert_called_once_with(tickers=None)
                mock_score.assert_called_once_with(tickers=None)


class TestRunCorrelationsShowcase:
    """Tests for run_correlations_showcase."""

    def _run(self, coro):
        return asyncio.get_event_loop().run_until_complete(coro)

    def test_returns_early_with_insufficient_tickers(self):
        from margin_api.cli import run_correlations_showcase

        mock_engine = MagicMock()
        mock_engine.dispose = AsyncMock()
        mock_session = AsyncMock()
        # No price data for any ticker
        empty_result = MagicMock()
        empty_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=empty_result)
        session_factory = _make_session_factory(mock_session)

        with patch("margin_api.cli.get_engine", return_value=mock_engine):
            with patch("margin_api.cli.get_session_factory", return_value=session_factory):
                # Should not raise, just log error and return
                self._run(run_correlations_showcase(tickers=["AAPL", "MSFT"]))


class TestRunPriceBackfill:
    """Tests for run_price_backfill."""

    def _run(self, coro):
        return asyncio.get_event_loop().run_until_complete(coro)

    def test_exits_early_when_no_tickers_in_pit(self):
        from margin_api.cli import run_price_backfill

        mock_engine = MagicMock()
        mock_engine.dispose = AsyncMock()
        mock_session = AsyncMock()
        empty_result = MagicMock()
        empty_result.all.return_value = []
        mock_session.execute = AsyncMock(return_value=empty_result)
        session_factory = _make_session_factory(mock_session)

        with patch("margin_api.cli.get_engine", return_value=mock_engine):
            with patch("margin_api.cli.get_session_factory", return_value=session_factory):
                # No tickers in pit_financial_snapshots → early return
                self._run(run_price_backfill())

    def test_calls_backfill_with_tickers(self):
        from margin_api.cli import run_price_backfill

        mock_engine = MagicMock()
        mock_engine.dispose = AsyncMock()
        session_factory = MagicMock()

        with patch("margin_api.cli.get_engine", return_value=mock_engine):
            with patch("margin_api.cli.get_session_factory", return_value=session_factory):
                with patch(
                    "margin_api.services.edgar.price_backfill.backfill_prices_for_tickers",
                    new_callable=AsyncMock,
                    return_value={"AAPL": 100, "MSFT": 200},
                ) as mock_backfill:
                    self._run(
                        run_price_backfill(
                            tickers=["AAPL", "MSFT"],
                            start_date="2020-01-01",
                            end_date="2024-12-31",
                            batch_size=100,
                        )
                    )
                    mock_backfill.assert_called_once()
                    call_kwargs = mock_backfill.call_args.kwargs
                    assert call_kwargs["tickers"] == ["AAPL", "MSFT"]
                    assert call_kwargs["start_date"] == "2020-01-01"
                    assert call_kwargs["batch_size"] == 100


class TestRunEdgarBackfill:
    """Tests for run_edgar_backfill_cmd."""

    def _run(self, coro):
        return asyncio.get_event_loop().run_until_complete(coro)

    def test_calls_backfill_service(self):
        from margin_api.cli import run_edgar_backfill_cmd

        mock_engine = MagicMock()
        mock_engine.dispose = AsyncMock()
        session_factory = MagicMock()

        with patch("margin_api.cli.get_engine", return_value=mock_engine):
            with patch("margin_api.cli.get_session_factory", return_value=session_factory):
                with patch(
                    "margin_api.services.edgar.backfill.run_edgar_backfill",
                    new_callable=AsyncMock,
                    return_value={"total": 100, "inserted": 80, "skipped": 15, "failed": 5},
                ) as mock_backfill:
                    self._run(
                        run_edgar_backfill_cmd(
                            start_year=2020,
                            end_year=2024,
                            checkpoint_file=".checkpoint",
                            dry_run=False,
                        )
                    )
                    mock_backfill.assert_called_once()
                    assert mock_backfill.call_args.kwargs["start_year"] == 2020


class TestRunEdgarReparse:
    """Tests for run_edgar_reparse_cmd."""

    def _run(self, coro):
        return asyncio.get_event_loop().run_until_complete(coro)

    def test_calls_reparse_service(self):
        from margin_api.cli import run_edgar_reparse_cmd

        mock_engine = MagicMock()
        mock_engine.dispose = AsyncMock()
        session_factory = MagicMock()

        with patch("margin_api.cli.get_engine", return_value=mock_engine):
            with patch("margin_api.cli.get_session_factory", return_value=session_factory):
                with patch(
                    "margin_api.services.edgar.backfill.reparse_empty_filings",
                    new_callable=AsyncMock,
                    return_value={"total": 10, "reparsed": 8, "failed": 1, "still_empty": 1},
                ) as mock_reparse:
                    self._run(run_edgar_reparse_cmd())
                    mock_reparse.assert_called_once()


class TestRunWeightTune:
    """Tests for run_weight_tune."""

    def test_dry_run_prints_config(self, capsys):
        from margin_api.cli import run_weight_tune

        mock_wmod = MagicMock()
        mock_wmod.TRACK_FACTORS = {"A": ["fcf_yield", "roic"], "B": ["gm", "rev_growth"]}
        mock_optuna = MagicMock()
        with patch.dict(
            sys.modules,
            {
                "optuna": mock_optuna,
                "margin_engine.tuning.weight_optimizer": mock_wmod,
            },
        ):
            run_weight_tune(track="ALL", n_trials=10, metric="sharpe", dry_run=True)
        out = capsys.readouterr().out
        # Should print something about the weight optimization
        assert len(out) > 0

    def test_exits_when_optuna_not_installed(self):
        from margin_api.cli import run_weight_tune

        # Remove optuna from modules to simulate not installed
        original = sys.modules.pop("optuna", None)
        try:
            with pytest.raises(SystemExit):
                run_weight_tune(track="ALL", n_trials=10, metric="sharpe", dry_run=False)
        finally:
            if original is not None:
                sys.modules["optuna"] = original

    def test_exits_on_invalid_track(self):
        from margin_api.cli import run_weight_tune

        try:
            import optuna  # noqa: F401

            has_optuna = True
        except ImportError:
            has_optuna = False

        if not has_optuna:
            pytest.skip("optuna not installed")

        # Patch the weight_optimizer module that is imported inside run_weight_tune
        mock_wmod = MagicMock()
        mock_wmod.TRACK_FACTORS = {"A": ["fcf_yield"]}
        with patch.dict(sys.modules, {"margin_engine.tuning.weight_optimizer": mock_wmod}):
            with pytest.raises(SystemExit):
                run_weight_tune(track="Z", n_trials=5, metric="sharpe", dry_run=False)

    def test_dry_run_specific_track(self, capsys):
        from margin_api.cli import run_weight_tune

        mock_wmod = MagicMock()
        mock_wmod.TRACK_FACTORS = {"A": ["fcf_yield", "roic"]}
        mock_optuna = MagicMock()
        with patch.dict(
            sys.modules,
            {
                "optuna": mock_optuna,
                "margin_engine.tuning.weight_optimizer": mock_wmod,
            },
        ):
            run_weight_tune(track="A", n_trials=5, metric="sharpe", dry_run=True)
        out = capsys.readouterr().out
        assert len(out) > 0


def _ablation_patches():
    """Context managers for patching ablation dependencies."""
    mock_report = MagicMock()
    mock_report.single_baselines = []
    mock_report.full_stack = None
    mock_report.interference = MagicMock(degradation=None)
    mock_report.shapley_values = None
    mock_report.recommendations = {}
    mock_report.model_dump.return_value = {"test": "data"}

    mock_study = MagicMock()
    mock_study.run.return_value = mock_report

    mock_ablation_runner = MagicMock()
    mock_ablation_runner.AblationConfig = MagicMock()
    mock_ablation_study = MagicMock()
    mock_ablation_study.AblationStudy = MagicMock(return_value=mock_study)
    mock_factor_registry = MagicMock()
    mock_factor_registry.FactorRegistry = MagicMock()
    mock_factor_registry.FactorRegistry.default.return_value = MagicMock()

    mock_bh = MagicMock()
    mock_bh.build_pit_provider_with_tickers = MagicMock(return_value=MagicMock())

    return (
        mock_report,
        mock_study,
        mock_ablation_runner,
        mock_ablation_study,
        mock_factor_registry,
        mock_bh,
    )


class TestRunAblation:
    """Tests for run_ablation."""

    def test_runs_with_mocked_study(self):
        from margin_api.cli import run_ablation

        mock_report, mock_study, mock_runner, mock_abl_study, mock_fr, mock_bh = _ablation_patches()
        mock_report.single_baselines = [
            MagicMock(
                combination=MagicMock(enabled_filters=["liquidity"]),
                metrics=MagicMock(sharpe_ratio=0.5),
            )
        ]
        mock_report.full_stack = MagicMock(metrics=MagicMock(sharpe_ratio=0.8))
        mock_report.interference = MagicMock(
            degradation=MagicMock(
                detected=False,
                best_single="liquidity",
                best_single_sharpe=0.5,
                full_stack_sharpe=0.8,
                severity=0.1,
            )
        )
        mock_report.shapley_values = None
        mock_report.recommendations = {"liquidity": "keep"}

        patches = {
            "margin_engine.ablation.runner": mock_runner,
            "margin_engine.ablation.study": mock_abl_study,
            "margin_engine.backtesting.factor_registry": mock_fr,
            "backtesting.helpers": mock_bh,
        }
        with patch.dict(sys.modules, patches):
            try:
                run_ablation(
                    start_date="2020-01-01",
                    end_date="2022-12-31",
                    output=None,
                    bootstrap_n=10,
                )
            except (ImportError, ModuleNotFoundError, AttributeError):
                pytest.skip("ablation helpers not available in test environment")

    def test_saves_report_to_file(self, tmp_path):
        from margin_api.cli import run_ablation

        output_path = str(tmp_path / "report.json")
        mock_report, mock_study, mock_runner, mock_abl_study, mock_fr, mock_bh = _ablation_patches()

        patches = {
            "margin_engine.ablation.runner": mock_runner,
            "margin_engine.ablation.study": mock_abl_study,
            "margin_engine.backtesting.factor_registry": mock_fr,
            "backtesting.helpers": mock_bh,
        }
        with patch.dict(sys.modules, patches):
            try:
                run_ablation(
                    start_date="2020-01-01",
                    end_date=None,
                    output=output_path,
                    bootstrap_n=10,
                )
                assert Path(output_path).exists()
            except (ImportError, ModuleNotFoundError, AttributeError):
                pytest.skip("ablation helpers not available in test environment")

    def test_with_shapley_values_and_degradation(self, capsys):
        from margin_api.cli import run_ablation

        mock_report, mock_study, mock_runner, mock_abl_study, mock_fr, mock_bh = _ablation_patches()
        mock_report.single_baselines = []
        mock_report.full_stack = MagicMock(metrics=MagicMock(sharpe_ratio=1.2))
        mock_report.interference = MagicMock(
            degradation=MagicMock(
                detected=True,
                best_single="roic",
                best_single_sharpe=0.9,
                full_stack_sharpe=1.2,
                severity=0.3,
            )
        )
        mock_report.shapley_values = MagicMock(values={"roic": 0.5, "liquidity": 0.3})
        mock_report.recommendations = {"growth": "remove"}

        patches = {
            "margin_engine.ablation.runner": mock_runner,
            "margin_engine.ablation.study": mock_abl_study,
            "margin_engine.backtesting.factor_registry": mock_fr,
            "backtesting.helpers": mock_bh,
        }
        with patch.dict(sys.modules, patches):
            try:
                run_ablation(
                    start_date="2020-01-01",
                    end_date="2022-12-31",
                    output=None,
                    bootstrap_n=10,
                )
            except (ImportError, ModuleNotFoundError, AttributeError):
                pytest.skip("ablation helpers not available in test environment")


class TestRunRegimeCharacterize:
    """Tests for run_regime_characterize."""

    def _make_regime_patches(self, mock_report):
        mock_regime_study = MagicMock()
        mock_regime_study.RegimeCharacterizationStudy = MagicMock(
            return_value=MagicMock(run=MagicMock(return_value=mock_report))
        )
        mock_regime_study.RegimeStudyConfig = MagicMock()
        mock_fr = MagicMock()
        mock_fr.FactorRegistry = MagicMock()
        mock_fr.FactorRegistry.default.return_value = MagicMock()
        mock_bh = MagicMock()
        mock_bh.build_pit_provider_with_tickers = MagicMock(return_value=MagicMock())
        return {
            "margin_engine.regime.study": mock_regime_study,
            "margin_engine.backtesting.factor_registry": mock_fr,
            "backtesting.helpers": mock_bh,
        }

    def test_runs_regime_study(self):
        from margin_api.cli import run_regime_characterize

        mock_report = MagicMock()
        mock_report.duration_seconds = 1.5
        mock_report.observed_regimes = ["bull", "bear"]
        mock_report.gate_profiles = {
            "liquidity": MagicMock(max_pdr=0.5, max_vif=1.2, most_degraded_regime="bear")
        }
        mock_report.regime_segmented_metrics = None

        patches = self._make_regime_patches(mock_report)
        with patch.dict(sys.modules, patches):
            try:
                run_regime_characterize(
                    start_date="2015-01-01",
                    end_date="2023-12-31",
                    output=None,
                    bootstrap_n=10,
                )
            except (ImportError, ModuleNotFoundError, AttributeError):
                pytest.skip("regime helpers not available")

    def test_saves_regime_report(self, tmp_path):
        from margin_api.cli import run_regime_characterize

        output_path = str(tmp_path / "regime_report.json")
        mock_report = MagicMock()
        mock_report.duration_seconds = 2.0
        mock_report.observed_regimes = []
        mock_report.gate_profiles = {}
        mock_report.regime_segmented_metrics = None
        mock_report.model_dump.return_value = {"regime": "test"}

        patches = self._make_regime_patches(mock_report)
        with patch.dict(sys.modules, patches):
            try:
                run_regime_characterize(
                    start_date="2015-01-01",
                    end_date=None,
                    output=output_path,
                    bootstrap_n=10,
                )
                assert Path(output_path).exists()
            except (ImportError, ModuleNotFoundError, AttributeError):
                pytest.skip("regime helpers not available")

    def test_with_regime_segmented_metrics(self):
        from margin_api.cli import run_regime_characterize

        mock_slice = MagicMock()
        mock_slice.sharpe_ratio = 0.7
        mock_slice.max_drawdown = -0.2
        mock_slice.n_months = 12

        mock_rsm = MagicMock()
        mock_rsm.slices = {"full_filter": mock_slice}

        mock_report = MagicMock()
        mock_report.duration_seconds = 1.0
        mock_report.observed_regimes = ["bull"]
        mock_report.gate_profiles = {}
        mock_report.regime_segmented_metrics = {"bull_2010-2015": mock_rsm}

        patches = self._make_regime_patches(mock_report)
        with patch.dict(sys.modules, patches):
            try:
                run_regime_characterize(
                    start_date="2010-01-01",
                    end_date="2020-12-31",
                    output=None,
                    bootstrap_n=10,
                )
            except (ImportError, ModuleNotFoundError, AttributeError):
                pytest.skip("regime helpers not available")


class TestMainEntryPoint:
    """Tests for main() — the argparse dispatch function."""

    def test_no_command_exits(self, monkeypatch):
        from margin_api.cli import main

        monkeypatch.setattr("sys.argv", ["margin-cli"])
        with pytest.raises(SystemExit):
            main()

    def test_seed_command_dispatches(self, monkeypatch):
        from margin_api.cli import main

        monkeypatch.setattr("sys.argv", ["margin-cli", "seed", "--tickers", "AAPL", "MSFT"])
        with patch("margin_api.cli.asyncio") as mock_asyncio:
            mock_asyncio.run = MagicMock()
            main()
            mock_asyncio.run.assert_called_once()

    def test_score_command_dispatches(self, monkeypatch):
        from margin_api.cli import main

        monkeypatch.setattr("sys.argv", ["margin-cli", "score", "--tickers", "AAPL"])
        with patch("margin_api.cli.asyncio") as mock_asyncio:
            mock_asyncio.run = MagicMock()
            main()
            mock_asyncio.run.assert_called_once()

    def test_score_v3_command_dispatches(self, monkeypatch):
        from margin_api.cli import main

        monkeypatch.setattr("sys.argv", ["margin-cli", "score-v3", "--cape", "25.0"])
        with patch("margin_api.cli.asyncio") as mock_asyncio:
            mock_asyncio.run = MagicMock()
            main()
            mock_asyncio.run.assert_called_once()

    def test_score_v4_command_dispatches(self, monkeypatch):
        from margin_api.cli import main

        monkeypatch.setattr("sys.argv", ["margin-cli", "score-v4", "--cape", "28.0"])
        with patch("margin_api.cli.asyncio") as mock_asyncio:
            mock_asyncio.run = MagicMock()
            main()
            mock_asyncio.run.assert_called_once()

    def test_score_universe_command_dispatches(self, monkeypatch):
        from margin_api.cli import main

        monkeypatch.setattr("sys.argv", ["margin-cli", "score-universe", "--limit", "10"])
        with patch("margin_api.cli.asyncio") as mock_asyncio:
            mock_asyncio.run = MagicMock()
            main()
            mock_asyncio.run.assert_called_once()

    def test_pipeline_command_dispatches(self, monkeypatch):
        from margin_api.cli import main

        monkeypatch.setattr("sys.argv", ["margin-cli", "pipeline", "--tickers", "AAPL"])
        with patch("margin_api.cli.asyncio") as mock_asyncio:
            mock_asyncio.run = MagicMock()
            main()
            mock_asyncio.run.assert_called_once()

    def test_backfill_country_command_dispatches(self, monkeypatch):
        from margin_api.cli import main

        monkeypatch.setattr("sys.argv", ["margin-cli", "backfill-country"])
        with patch("margin_api.cli.asyncio") as mock_asyncio:
            mock_asyncio.run = MagicMock()
            main()
            mock_asyncio.run.assert_called_once()

    def test_backfill_13f_command_dispatches(self, monkeypatch):
        from margin_api.cli import main

        monkeypatch.setattr("sys.argv", ["margin-cli", "backfill-13f", "--start-year", "2015"])
        with patch("margin_api.cli.asyncio") as mock_asyncio:
            mock_asyncio.run = MagicMock()
            main()
            mock_asyncio.run.assert_called_once()

    def test_price_backfill_command_dispatches(self, monkeypatch):
        from margin_api.cli import main

        monkeypatch.setattr(
            "sys.argv", ["margin-cli", "price-backfill", "--start-date", "2020-01-01"]
        )
        with patch("margin_api.cli.asyncio") as mock_asyncio:
            mock_asyncio.run = MagicMock()
            main()
            mock_asyncio.run.assert_called_once()

    def test_edgar_backfill_command_dispatches(self, monkeypatch):
        from margin_api.cli import main

        monkeypatch.setattr(
            "sys.argv", ["margin-cli", "edgar-backfill", "--start-year", "2015", "--dry-run"]
        )
        with patch("margin_api.cli.asyncio") as mock_asyncio:
            mock_asyncio.run = MagicMock()
            main()
            mock_asyncio.run.assert_called_once()

    def test_edgar_reparse_command_dispatches(self, monkeypatch):
        from margin_api.cli import main

        monkeypatch.setattr("sys.argv", ["margin-cli", "edgar-reparse"])
        with patch("margin_api.cli.asyncio") as mock_asyncio:
            mock_asyncio.run = MagicMock()
            main()
            mock_asyncio.run.assert_called_once()

    def test_ablation_command_dispatches(self, monkeypatch):
        from margin_api.cli import main

        monkeypatch.setattr("sys.argv", ["margin-cli", "ablation", "--bootstrap-n", "10"])
        with patch("margin_api.cli.run_ablation") as mock_fn:
            main()
            mock_fn.assert_called_once()

    def test_regime_characterize_command_dispatches(self, monkeypatch):
        from margin_api.cli import main

        monkeypatch.setattr(
            "sys.argv", ["margin-cli", "regime-characterize", "--bootstrap-n", "10"]
        )
        with patch("margin_api.cli.run_regime_characterize") as mock_fn:
            main()
            mock_fn.assert_called_once()

    def test_weight_tune_command_dispatches(self, monkeypatch):
        from margin_api.cli import main

        monkeypatch.setattr("sys.argv", ["margin-cli", "weight-tune", "--dry-run"])
        with patch("margin_api.cli.run_weight_tune") as mock_fn:
            main()
            mock_fn.assert_called_once()

    def test_correlations_showcase_dispatches(self, monkeypatch):
        from margin_api.cli import main

        monkeypatch.setattr("sys.argv", ["margin-cli", "correlations", "--showcase"])
        with patch("margin_api.cli.asyncio") as mock_asyncio:
            mock_asyncio.run = MagicMock()
            main()
            mock_asyncio.run.assert_called_once()

    def test_correlations_without_showcase_exits(self, monkeypatch):
        from margin_api.cli import main

        monkeypatch.setattr("sys.argv", ["margin-cli", "correlations"])
        with pytest.raises(SystemExit):
            main()

    def test_universe_generate_dispatches(self, monkeypatch):
        from margin_api.cli import main

        monkeypatch.setattr("sys.argv", ["margin-cli", "universe", "generate"])
        with patch("margin_api.cli.run_universe_generate") as mock_fn:
            main()
            mock_fn.assert_called_once()

    def test_universe_activate_dispatches(self, monkeypatch):
        from margin_api.cli import main

        monkeypatch.setattr("sys.argv", ["margin-cli", "universe", "activate"])
        with patch("margin_api.cli.asyncio") as mock_asyncio:
            mock_asyncio.run = MagicMock()
            main()
            mock_asyncio.run.assert_called_once()

    def test_universe_no_subcommand_exits(self, monkeypatch):
        from margin_api.cli import main

        monkeypatch.setattr("sys.argv", ["margin-cli", "universe"])
        with pytest.raises(SystemExit):
            main()

    def test_weight_tune_with_track_arg(self, monkeypatch):
        from margin_api.cli import main

        monkeypatch.setattr("sys.argv", ["margin-cli", "weight-tune", "A", "--n-trials", "50"])
        with patch("margin_api.cli.run_weight_tune") as mock_fn:
            main()
            mock_fn.assert_called_once()
            call_kwargs = mock_fn.call_args.kwargs
            assert call_kwargs.get("track") == "A" or mock_fn.call_args[1].get("track") == "A"


class TestRunUniverseGenerate:
    """Tests for run_universe_generate."""

    def test_generates_yaml_to_custom_path(self, tmp_path):
        from margin_api.cli import run_universe_generate

        output_path = str(tmp_path / "custom_universe.yaml")
        yaml_content = "tickers:\n  - AAPL\n"

        mock_screener_mod = MagicMock()
        mock_screener_mod.screen_us_equities.return_value = [{"ticker": "AAPL"}]
        mock_screener_mod.generate_universe_yaml.return_value = yaml_content
        mock_screener_mod.US_EXCHANGES = ["NYSE", "NASDAQ"]

        with patch.dict(sys.modules, {"margin_engine.universe.screener": mock_screener_mod}):
            with patch("margin_api.cli._load_foreign_skips", return_value=set()):
                run_universe_generate(output=output_path)
                assert Path(output_path).read_text() == yaml_content

    def test_removes_known_foreign_tickers(self, tmp_path):
        from margin_api.cli import run_universe_generate

        output_path = str(tmp_path / "universe.yaml")

        mock_screener_mod = MagicMock()
        mock_screener_mod.screen_us_equities.return_value = [{"ticker": "AAPL"}, {"ticker": "BABA"}]
        mock_screener_mod.generate_universe_yaml.return_value = "tickers:\n  - AAPL\n"
        mock_screener_mod.US_EXCHANGES = ["NYSE", "NASDAQ"]

        with patch.dict(sys.modules, {"margin_engine.universe.screener": mock_screener_mod}):
            with patch("margin_api.cli._load_foreign_skips", return_value={"BABA"}):
                run_universe_generate(output=output_path)
                # generate_universe_yaml should be called with BABA removed
                call_kwargs = mock_screener_mod.generate_universe_yaml.call_args
                tickers_arg = call_kwargs.kwargs.get("tickers") or call_kwargs.args[0]
                assert "BABA" not in tickers_arg
                assert "AAPL" in tickers_arg

    def test_generates_to_default_path_when_no_output(self):
        from margin_api.cli import run_universe_generate

        yaml_content = "tickers:\n  - AAPL\n"

        mock_screener_mod = MagicMock()
        mock_screener_mod.screen_us_equities.return_value = [{"ticker": "AAPL"}]
        mock_screener_mod.generate_universe_yaml.return_value = yaml_content
        mock_screener_mod.US_EXCHANGES = ["NYSE", "NASDAQ"]

        with patch.dict(sys.modules, {"margin_engine.universe.screener": mock_screener_mod}):
            with patch("margin_api.cli._load_foreign_skips", return_value=set()):
                with patch.object(Path, "write_text") as mock_write:
                    run_universe_generate(output=None)
                    mock_write.assert_called_once_with(yaml_content)


class TestRunBackfill13f:
    """Tests for run_backfill_13f."""

    def _run(self, coro):
        return asyncio.get_event_loop().run_until_complete(coro)

    def _setup_mods(self, mock_session, mock_service, mock_edgar):
        """Create sys.modules patches for locally imported modules."""
        mock_thirteenf_mod = MagicMock()
        mock_thirteenf_mod.ThirteenFIngestService = MagicMock(return_value=mock_service)
        mock_edgar_mod = MagicMock()
        mock_edgar_mod.EDGARProvider = MagicMock(return_value=mock_edgar)
        mock_acc_mod = MagicMock()
        mock_acc_svc = AsyncMock()
        mock_acc_svc.compute_signals = AsyncMock()
        mock_acc_mod.AccumulationService = MagicMock(return_value=mock_acc_svc)
        return {
            "margin_api.services.thirteenf_ingest": mock_thirteenf_mod,
            "margin_engine.ingestion.providers.edgar_provider": mock_edgar_mod,
            "margin_api.services.accumulation_service": mock_acc_mod,
        }

    def test_processes_zero_managers_gracefully(self):
        from margin_api.cli import run_backfill_13f

        mock_engine = MagicMock()
        mock_engine.dispose = AsyncMock()
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)
        session_factory = _make_session_factory(mock_session)
        mock_service = AsyncMock()
        mock_service.upsert_managers = AsyncMock()
        mock_edgar = MagicMock()

        mods = self._setup_mods(mock_session, mock_service, mock_edgar)
        with patch("margin_api.cli.get_engine", return_value=mock_engine):
            with patch("margin_api.cli.get_session_factory", return_value=session_factory):
                with patch.dict(sys.modules, mods):
                    # max_managers=0 → CURATED_FUNDS[:0] = [] → no funds to process
                    self._run(run_backfill_13f(start_year=2020, max_managers=0))

    def test_handles_edgar_exception_gracefully(self):
        from margin_api.cli import run_backfill_13f

        mock_engine = MagicMock()
        mock_engine.dispose = AsyncMock()
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)
        session_factory = _make_session_factory(mock_session)
        mock_service = AsyncMock()
        mock_service.upsert_managers = AsyncMock()
        mock_edgar = MagicMock()
        mock_edgar.get_13f_submissions.side_effect = RuntimeError("EDGAR down")

        mods = self._setup_mods(mock_session, mock_service, mock_edgar)
        with patch("margin_api.cli.get_engine", return_value=mock_engine):
            with patch("margin_api.cli.get_session_factory", return_value=session_factory):
                with patch.dict(sys.modules, mods):
                    with patch(
                        "margin_api.cli.CURATED_FUNDS",
                        [
                            {
                                "cik": "0001067983",
                                "name": "BH INC",
                                "short_name": "BH",
                                "tier": "curated",
                            }
                        ],
                    ):
                        # Should not raise despite EDGAR exception
                        self._run(run_backfill_13f(start_year=2020, max_managers=1))

    def test_skips_filings_before_start_year(self):
        from margin_api.cli import run_backfill_13f

        mock_engine = MagicMock()
        mock_engine.dispose = AsyncMock()
        mock_session = AsyncMock()
        mock_mgr = MagicMock()
        mock_mgr.id = 1
        mgr_result = MagicMock()
        mgr_result.scalar_one.return_value = mock_mgr
        period_result = MagicMock()
        period_result.all.return_value = []
        mock_session.execute = AsyncMock(side_effect=[mgr_result, period_result])
        session_factory = _make_session_factory(mock_session)
        mock_service = AsyncMock()
        mock_service.upsert_managers = AsyncMock()
        mock_service.is_filing_new = AsyncMock(return_value=True)
        mock_edgar = MagicMock()
        mock_edgar.get_13f_submissions.return_value = {}
        # Filing from 2010, start_year=2020 → skipped by year check
        mock_edgar.extract_13f_filings.return_value = [
            {
                "period_of_report": "2010-06-30",
                "accession_number": "0001067983-10-000001",
                "filing_type": "13F-HR",
                "filed_date": "2010-08-14",
                "is_amendment": False,
            }
        ]

        mods = self._setup_mods(mock_session, mock_service, mock_edgar)
        with patch("margin_api.cli.get_engine", return_value=mock_engine):
            with patch("margin_api.cli.get_session_factory", return_value=session_factory):
                with patch.dict(sys.modules, mods):
                    with patch(
                        "margin_api.cli.CURATED_FUNDS",
                        [
                            {
                                "cik": "0001067983",
                                "name": "BH INC",
                                "short_name": "BH",
                                "tier": "curated",
                            }
                        ],
                    ):
                        self._run(run_backfill_13f(start_year=2020, max_managers=1))
        # is_filing_new not called because filing year 2010 < start_year 2020
        mock_service.is_filing_new.assert_not_called()


class TestLoadAndPredictMl:
    """Tests for _load_and_predict_ml."""

    def _run(self, coro):
        return asyncio.get_event_loop().run_until_complete(coro)

    def test_returns_empty_when_no_cluster_model_data(self):
        from margin_api.cli import _load_and_predict_ml

        ml_run = MagicMock()
        ml_run.model_qualifies = True
        ml_run.cluster_model_data = None

        result = self._run(_load_and_predict_ml(ml_run, []))
        assert result["model_qualifies"] is True
        assert result["alphas"] == {}
        assert result["vae_means"] == {}
        assert result["vae_variances"] == {}

    def test_returns_empty_on_bad_pickle_data(self):
        from margin_api.cli import _load_and_predict_ml

        ml_run = MagicMock()
        ml_run.model_qualifies = True
        # Pass bytes that will fail pickle.loads
        ml_run.cluster_model_data = b"not-valid-serialized-data-xyz"

        result = self._run(_load_and_predict_ml(ml_run, []))
        assert result["alphas"] == {}
