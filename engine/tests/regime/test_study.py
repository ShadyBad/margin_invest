"""Tests for the regime characterization study orchestrator."""

from __future__ import annotations

from datetime import date

from margin_engine.backtesting.factor_registry import FactorRegistry
from margin_engine.regime.study import (
    RegimeCharacterizationStudy,
    RegimeStudyConfig,
    RegimeStudyReport,
)

from tests.backtesting.helpers import build_pit_provider_with_tickers

# Short date range and small ticker set for fast tests.
START = date(2015, 1, 1)
END = date(2020, 1, 1)
TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN"]


# ---------------------------------------------------------------------------
# Config / model tests
# ---------------------------------------------------------------------------


class TestRegimeStudyConfigDefaults:
    """Verify RegimeStudyConfig sensible defaults."""

    def test_default_start_date(self) -> None:
        config = RegimeStudyConfig()
        assert config.start_date == date(2006, 1, 1)

    def test_default_end_date_is_today(self) -> None:
        config = RegimeStudyConfig()
        assert config.end_date == date.today()

    def test_default_min_regime_months(self) -> None:
        config = RegimeStudyConfig()
        assert config.min_regime_months == 6

    def test_default_bootstrap_resamples(self) -> None:
        config = RegimeStudyConfig()
        assert config.bootstrap_resamples == 1000

    def test_custom_values(self) -> None:
        config = RegimeStudyConfig(
            start_date=date(2010, 1, 1),
            end_date=date(2022, 12, 31),
            min_regime_months=3,
            bootstrap_resamples=500,
        )
        assert config.start_date == date(2010, 1, 1)
        assert config.end_date == date(2022, 12, 31)
        assert config.min_regime_months == 3
        assert config.bootstrap_resamples == 500


class TestRegimeStudyReportFields:
    """Verify RegimeStudyReport has expected fields with correct defaults."""

    def test_empty_report_defaults(self) -> None:
        config = RegimeStudyConfig()
        report = RegimeStudyReport(config=config)
        assert report.config is config
        assert report.gate_profiles == {}
        assert isinstance(report.failure_modes, object)
        assert report.robustness == {}
        assert report.regime_segmented_metrics == {}
        assert report.observed_regimes == []
        assert report.duration_seconds == 0.0

    def test_report_serialization(self) -> None:
        """Report can be serialized to dict."""
        config = RegimeStudyConfig()
        report = RegimeStudyReport(config=config)
        d = report.model_dump()
        assert "config" in d
        assert "gate_profiles" in d
        assert "failure_modes" in d
        assert "robustness" in d
        assert "regime_segmented_metrics" in d
        assert "observed_regimes" in d
        assert "duration_seconds" in d


# ---------------------------------------------------------------------------
# Instantiation test
# ---------------------------------------------------------------------------


class TestRegimeCharacterizationStudyInstantiation:
    """Verify the study class can be created with valid inputs."""

    def test_basic_instantiation(self) -> None:
        config = RegimeStudyConfig(
            start_date=START,
            end_date=END,
            min_regime_months=2,
        )
        provider = build_pit_provider_with_tickers(TICKERS, START, END)
        registry = FactorRegistry.default()

        study = RegimeCharacterizationStudy(
            config=config,
            pit_provider=provider,
            factor_registry=registry,
            bootstrap_resamples=50,
        )
        assert study is not None

    def test_instantiation_with_benchmark_prices(self) -> None:
        config = RegimeStudyConfig(start_date=START, end_date=END, min_regime_months=2)
        provider = build_pit_provider_with_tickers(TICKERS, START, END)
        registry = FactorRegistry.default()
        bench = {date(2015, 1, 1): 100.0, date(2015, 2, 1): 101.0}

        study = RegimeCharacterizationStudy(
            config=config,
            pit_provider=provider,
            factor_registry=registry,
            benchmark_prices=bench,
            bootstrap_resamples=50,
        )
        assert study is not None


# ---------------------------------------------------------------------------
# Integration test — run() produces a valid report
# ---------------------------------------------------------------------------

# Cache the report across tests to avoid re-running the expensive study.
_cached_report: RegimeStudyReport | None = None


def _get_report() -> RegimeStudyReport:
    global _cached_report
    if _cached_report is None:
        config = RegimeStudyConfig(
            start_date=START,
            end_date=END,
            min_regime_months=2,
            bootstrap_resamples=50,
        )
        provider = build_pit_provider_with_tickers(TICKERS, START, END)
        registry = FactorRegistry.default()
        study = RegimeCharacterizationStudy(
            config=config,
            pit_provider=provider,
            factor_registry=registry,
            bootstrap_resamples=50,
        )
        _cached_report = study.run()
    return _cached_report


class TestRegimeStudyRun:
    """Integration tests: study.run() produces a valid report."""

    def test_report_is_regime_study_report(self) -> None:
        report = _get_report()
        assert isinstance(report, RegimeStudyReport)

    def test_observed_regimes_not_empty(self) -> None:
        """The study should observe at least one regime from the time series."""
        report = _get_report()
        assert len(report.observed_regimes) >= 1

    def test_gate_profiles_populated(self) -> None:
        """Gate profiles should have entries for each of the 6 filters."""
        report = _get_report()
        assert len(report.gate_profiles) >= 1
        # Each key should be a filter name
        for key in report.gate_profiles:
            assert isinstance(key, str)

    def test_regime_segmented_metrics_populated(self) -> None:
        """Regime segmented metrics should be populated for at least 'full_stack'."""
        report = _get_report()
        assert len(report.regime_segmented_metrics) >= 1

    def test_duration_positive(self) -> None:
        """The study should record a positive duration."""
        report = _get_report()
        assert report.duration_seconds > 0.0

    def test_config_preserved(self) -> None:
        """The report should preserve the original config."""
        report = _get_report()
        assert report.config.start_date == START
        assert report.config.end_date == END

    def test_report_can_serialize_to_json(self) -> None:
        """The full report should be JSON-serializable."""
        report = _get_report()
        d = report.model_dump()
        assert isinstance(d, dict)
        # Ensure it has all expected top-level keys
        expected_keys = {
            "config",
            "gate_profiles",
            "failure_modes",
            "robustness",
            "regime_segmented_metrics",
            "observed_regimes",
            "duration_seconds",
        }
        assert expected_keys.issubset(set(d.keys()))
