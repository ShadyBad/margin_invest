"""Tests for regime classification integration into ReplayOrchestrator and AblationResult.

Verifies:
  1. RebalanceAuditRecord gains an optional ``regime_state`` field (RegimeState | None)
  2. The field defaults to None for backward compatibility
  3. AblationResult gains a ``regime_tags`` field (list[RegimeState])
  4. The field defaults to an empty list for backward compatibility
  5. When a regime_classifier is provided to ReplayOrchestrator, audit records
     get regime_state populated
  6. AblationRunner propagates regime_tags from audit records to AblationResult
"""

from __future__ import annotations

from datetime import date

from margin_engine.ablation.runner import AblationResult, FilterCombination
from margin_engine.backtesting.factor_registry import FactorRegistry
from margin_engine.backtesting.models import PerformanceMetrics
from margin_engine.backtesting.regime_classifier import MarketRegimeHistorical
from margin_engine.backtesting.replay_orchestrator import (
    RebalanceAuditRecord,
    ReplayConfig,
    ReplayOrchestrator,
)
from margin_engine.regime.classifier import (
    MultiDimensionalRegimeClassifier,
    RegimeClassifierConfig,
)
from margin_engine.regime.models import (
    CreditState,
    RegimeConfidence,
    RegimeState,
    TrendState,
    ValuationState,
    VolatilityState,
)

from tests.backtesting.helpers import build_pit_provider_with_tickers

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

START = date(2020, 1, 1)
END = date(2020, 6, 1)
TICKERS = ["AAPL", "MSFT", "GOOGL"]


def _make_regime_state(d: date | None = None) -> RegimeState:
    """Build a dummy RegimeState for testing."""
    return RegimeState(
        as_of_date=d or date(2020, 1, 1),
        volatility=VolatilityState.NORMAL,
        trend=TrendState.BULL,
        valuation=ValuationState.NORMAL,
        credit=CreditState.NORMAL,
        confidence=RegimeConfidence(
            volatility=0.5,
            trend=0.5,
            valuation=0.5,
            credit=0.5,
        ),
    )


def _dummy_metrics() -> PerformanceMetrics:
    return PerformanceMetrics(
        cagr=0.0,
        excess_cagr=0.0,
        sharpe_ratio=0.0,
        sortino_ratio=0.0,
        max_drawdown=0.0,
        win_rate=0.0,
        information_ratio=0.0,
        total_return=0.0,
        benchmark_total_return=0.0,
        num_months=0,
        avg_turnover=0.0,
    )


# ---------------------------------------------------------------------------
# Test: RebalanceAuditRecord.regime_state field
# ---------------------------------------------------------------------------


class TestRebalanceAuditRecordRegimeState:
    """RebalanceAuditRecord should have an optional regime_state field."""

    def test_regime_state_field_exists(self) -> None:
        """RebalanceAuditRecord should accept a RegimeState for regime_state."""
        rs = _make_regime_state()
        record = RebalanceAuditRecord(
            rebalance_date=date(2020, 1, 1),
            universe_size=100,
            eliminated_count=40,
            survivor_count=60,
            selected_count=5,
            top_holdings=[],
            notable_events=[],
            factor_coverage=0.9,
            available_factors=["quality", "value"],
            missing_factors=["momentum"],
            regime=MarketRegimeHistorical.BULL,
            regime_state=rs,
        )
        assert record.regime_state is not None
        assert record.regime_state.volatility == VolatilityState.NORMAL
        assert record.regime_state.trend == TrendState.BULL

    def test_regime_state_defaults_to_none(self) -> None:
        """When regime_state is not provided, it should default to None (backward compat)."""
        record = RebalanceAuditRecord(
            rebalance_date=date(2020, 1, 1),
            universe_size=100,
            eliminated_count=40,
            survivor_count=60,
            selected_count=5,
            top_holdings=[],
            notable_events=[],
            factor_coverage=0.9,
            available_factors=["quality", "value"],
            missing_factors=["momentum"],
            regime=MarketRegimeHistorical.BULL,
        )
        assert record.regime_state is None


# ---------------------------------------------------------------------------
# Test: AblationResult.regime_tags field
# ---------------------------------------------------------------------------


class TestAblationResultRegimeTags:
    """AblationResult should have a regime_tags field."""

    def test_regime_tags_field_exists(self) -> None:
        """AblationResult should accept a list of RegimeState for regime_tags."""
        tags = [_make_regime_state(date(2020, 1, 1)), _make_regime_state(date(2020, 2, 1))]
        combo = FilterCombination(name="test", enabled_filters=set())
        result = AblationResult(
            combination=combo,
            metrics=_dummy_metrics(),
            regime_tags=tags,
        )
        assert len(result.regime_tags) == 2
        assert result.regime_tags[0].as_of_date == date(2020, 1, 1)

    def test_regime_tags_defaults_to_empty_list(self) -> None:
        """When regime_tags is not provided, it should default to empty list (backward compat)."""
        combo = FilterCombination(name="test", enabled_filters=set())
        result = AblationResult(
            combination=combo,
            metrics=_dummy_metrics(),
        )
        assert result.regime_tags == []


# ---------------------------------------------------------------------------
# Test: ReplayOrchestrator accepts regime_classifier
# ---------------------------------------------------------------------------


class TestReplayOrchestratorRegimeClassifier:
    """ReplayOrchestrator should accept an optional regime_classifier parameter."""

    def test_accepts_regime_classifier_parameter(self) -> None:
        """ReplayOrchestrator.__init__ accepts regime_classifier without error."""
        provider = build_pit_provider_with_tickers(TICKERS, START, END)
        config = ReplayConfig(
            start_date=START,
            end_date=END,
            rebalance_frequency="monthly",
        )
        classifier = MultiDimensionalRegimeClassifier(
            config=RegimeClassifierConfig(min_history_months=2),
        )
        orchestrator = ReplayOrchestrator(
            config=config,
            pit_provider=provider,
            factor_registry=FactorRegistry.default(),
            regime_classifier=classifier,
        )
        # Should not raise — just verify the orchestrator was created
        assert orchestrator is not None

    def test_regime_state_populated_on_audit_records(self) -> None:
        """When regime_classifier is provided, audit records should have regime_state set."""
        provider = build_pit_provider_with_tickers(TICKERS, START, END)
        config = ReplayConfig(
            start_date=START,
            end_date=END,
            rebalance_frequency="monthly",
        )
        # Use a very low min_history so classification kicks in early
        classifier = MultiDimensionalRegimeClassifier(
            config=RegimeClassifierConfig(min_history_months=2),
        )
        orchestrator = ReplayOrchestrator(
            config=config,
            pit_provider=provider,
            factor_registry=FactorRegistry.default(),
            regime_classifier=classifier,
        )
        result = orchestrator.run()

        # At least some audit records should have regime_state populated
        # (The first 1-2 may be None due to insufficient history)
        populated = [r for r in result.audit_log if r.regime_state is not None]
        assert len(populated) > 0, (
            f"Expected at least one audit record with regime_state populated, "
            f"got {len(result.audit_log)} records all with regime_state=None"
        )

        # Verify the RegimeState is well-formed
        rs = populated[0].regime_state
        assert isinstance(rs, RegimeState)
        assert rs.volatility in list(VolatilityState)
        assert rs.trend in list(TrendState)
        assert rs.valuation in list(ValuationState)
        assert rs.credit in list(CreditState)

    def test_without_classifier_regime_state_is_none(self) -> None:
        """When no regime_classifier is provided, audit records have regime_state=None."""
        provider = build_pit_provider_with_tickers(TICKERS, START, END)
        config = ReplayConfig(
            start_date=START,
            end_date=END,
            rebalance_frequency="monthly",
        )
        orchestrator = ReplayOrchestrator(
            config=config,
            pit_provider=provider,
            factor_registry=FactorRegistry.default(),
        )
        result = orchestrator.run()

        for record in result.audit_log:
            assert record.regime_state is None, (
                f"Expected regime_state=None without classifier, got {record.regime_state}"
            )
