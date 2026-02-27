"""Tests for ReplayOrchestrator filter_config and disabled_filters support."""

from __future__ import annotations

from datetime import date

from margin_engine.backtesting.factor_registry import FactorRegistry
from margin_engine.backtesting.replay_orchestrator import (
    ReplayConfig,
    ReplayOrchestrator,
)
from margin_engine.config.filter_config import FilterConfig

from tests.backtesting.helpers import build_pit_provider_with_tickers

# Short date range — 3 months is enough to exercise the pipeline.
START = date(2020, 1, 1)
END = date(2020, 3, 1)
TICKERS = ["AAPL", "MSFT", "GOOGL"]


def _make_config() -> ReplayConfig:
    return ReplayConfig(start_date=START, end_date=END, rebalance_frequency="monthly")


def _make_registry() -> FactorRegistry:
    return FactorRegistry.default()


def test_orchestrator_accepts_filter_config() -> None:
    """Passing a custom FilterConfig runs without error."""
    custom_config = FilterConfig(
        beneish=FilterConfig.model_fields["beneish"].default_factory(),  # type: ignore[misc]
    )
    # Just make sure thresholds are customizable
    custom_config.beneish.threshold = -2.0

    provider = build_pit_provider_with_tickers(TICKERS, START, END)
    orchestrator = ReplayOrchestrator(
        config=_make_config(),
        pit_provider=provider,
        factor_registry=_make_registry(),
        filter_config=custom_config,
    )
    result = orchestrator.run()

    assert result.snapshots, "Expected at least one snapshot"
    assert result.audit_log, "Expected at least one audit record"


def test_orchestrator_accepts_disabled_filters() -> None:
    """Passing disabled_filters runs without error."""
    provider = build_pit_provider_with_tickers(TICKERS, START, END)
    orchestrator = ReplayOrchestrator(
        config=_make_config(),
        pit_provider=provider,
        factor_registry=_make_registry(),
        disabled_filters={"beneish_m_score", "altman_z_score"},
    )
    result = orchestrator.run()

    assert result.snapshots, "Expected at least one snapshot"
    assert result.audit_log, "Expected at least one audit record"


def test_disabled_filters_increases_survivors() -> None:
    """With filters disabled, survivor count >= full filtering."""
    provider = build_pit_provider_with_tickers(TICKERS, START, END)

    # Full filtering (no disabled)
    full_orch = ReplayOrchestrator(
        config=_make_config(),
        pit_provider=provider,
        factor_registry=_make_registry(),
    )
    full_result = full_orch.run()

    # All filters disabled — every ticker survives
    all_disabled = {
        "liquidity",
        "beneish_m_score",
        "altman_z_score",
        "fcf_distress",
        "interest_coverage",
        "current_ratio",
        "mediocrity_gate",
    }
    relaxed_orch = ReplayOrchestrator(
        config=_make_config(),
        pit_provider=provider,
        factor_registry=_make_registry(),
        disabled_filters=all_disabled,
    )
    relaxed_result = relaxed_orch.run()

    # Compare survivor counts from audit logs
    for full_audit, relaxed_audit in zip(
        full_result.audit_log, relaxed_result.audit_log, strict=False
    ):
        assert relaxed_audit.survivor_count >= full_audit.survivor_count, (
            f"On {full_audit.rebalance_date}: relaxed survivors "
            f"({relaxed_audit.survivor_count}) < full survivors "
            f"({full_audit.survivor_count})"
        )
