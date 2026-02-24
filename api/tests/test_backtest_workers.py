"""Tests for backtest worker job stubs."""

from datetime import date

from margin_api.services.backtest import compute_config_hash
from margin_engine.backtesting.replay_orchestrator import ReplayConfig


class TestConfigHashCaching:
    def test_hash_is_deterministic(self):
        config1 = ReplayConfig(conviction_threshold=0.10, rebalance_frequency="monthly")
        config2 = ReplayConfig(conviction_threshold=0.10, rebalance_frequency="monthly")
        config3 = ReplayConfig(conviction_threshold=0.20, rebalance_frequency="monthly")
        assert compute_config_hash(config1) == compute_config_hash(config2)
        assert compute_config_hash(config1) != compute_config_hash(config3)

    def test_hash_changes_with_sector_exclusions(self):
        config1 = ReplayConfig(sector_exclusions=[])
        config2 = ReplayConfig(sector_exclusions=["Energy"])
        assert compute_config_hash(config1) != compute_config_hash(config2)

    def test_hash_excludes_end_date(self):
        config1 = ReplayConfig(end_date=date(2025, 12, 31))
        config2 = ReplayConfig(end_date=date(2024, 12, 31))
        # end_date is excluded from hash so same params = same hash
        assert compute_config_hash(config1) == compute_config_hash(config2)

    def test_hash_changes_with_weighting(self):
        config1 = ReplayConfig(weighting="equal")
        config2 = ReplayConfig(weighting="conviction")
        assert compute_config_hash(config1) != compute_config_hash(config2)

    def test_hash_is_hex_string(self):
        config = ReplayConfig()
        h = compute_config_hash(config)
        assert len(h) == 64  # SHA-256 hex
        assert all(c in "0123456789abcdef" for c in h)


class TestWorkerStubs:
    def test_precompute_backtest_is_importable(self):
        from margin_api.services.backtest import precompute_default_backtest

        assert callable(precompute_default_backtest)

    def test_run_custom_backtest_is_importable(self):
        from margin_api.services.backtest import run_custom_backtest

        assert callable(run_custom_backtest)

    def test_precompute_returns_result(self):
        from margin_api.services.backtest import precompute_default_backtest

        result = precompute_default_backtest()
        assert result is not None
        assert hasattr(result, "metrics")
        assert hasattr(result, "config")

    def test_custom_backtest_returns_result(self):
        from margin_api.services.backtest import run_custom_backtest

        config = ReplayConfig(
            rebalance_frequency="quarterly",
            conviction_threshold=0.15,
        )
        result = run_custom_backtest(config)
        assert result is not None
        assert hasattr(result, "metrics")

    def test_custom_backtest_uses_provided_config(self):
        from margin_api.services.backtest import run_custom_backtest

        config = ReplayConfig(
            rebalance_frequency="quarterly",
            conviction_threshold=0.15,
        )
        result = run_custom_backtest(config)
        assert result.config.rebalance_frequency == "quarterly"
        assert result.config.conviction_threshold == 0.15
