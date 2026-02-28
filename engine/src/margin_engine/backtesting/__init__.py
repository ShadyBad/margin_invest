"""Backtesting engine — walk-forward simulation and validation."""

from margin_engine.backtesting.factor_registry import FactorAvailability, FactorRegistry
from margin_engine.backtesting.failure_audit import FailurePeriod, compute_failure_audit
from margin_engine.backtesting.metrics import PerformanceCalculator
from margin_engine.backtesting.models import (
    BacktestConfig,
    BacktestResult,
    HoldingRecord,
    MonthlySnapshot,
    PassThreshold,
    PerformanceMetrics,
    RebalanceFrequency,
    SelectionMode,
    ValidationResult,
)
from margin_engine.backtesting.pit_provider import (
    AsyncPointInTimeProvider,
    DelistingEvent,
    DelistingType,
    InMemoryPITProvider,
    PITSnapshot,
    PointInTimeProvider,
)
from margin_engine.backtesting.publication_bias import haircut_returns, signal_significance
from margin_engine.backtesting.rank_ic import (
    RankICReport,
    compute_rank_ic,
    compute_rank_ic_report,
)
from margin_engine.backtesting.regime_classifier import (
    MarketRegimeHistorical,
    RegimeSegment,
    classify_regime,
    segment_by_regime,
)
from margin_engine.backtesting.replay_orchestrator import (
    RebalanceAuditRecord,
    ReplayConfig,
    ReplayOrchestrator,
    ReplayResult,
)
from margin_engine.backtesting.shadow_portfolio import (
    ShadowPortfolio,
    ShadowPosition,
    ShadowSnapshot,
)
from margin_engine.backtesting.simulator import (
    BenchmarkProvider,
    ScoredStock,
    ScoredUniverseProvider,
    WalkForwardSimulator,
)
from margin_engine.backtesting.validation import MethodologyComparison, ValidationGate
from margin_engine.backtesting.walk_forward import (
    WalkForwardPartition,
    generate_walk_forward_partitions,
)

__all__ = [
    "AsyncPointInTimeProvider",
    "BacktestConfig",
    "BacktestResult",
    "BenchmarkProvider",
    "DelistingEvent",
    "DelistingType",
    "FactorAvailability",
    "FactorRegistry",
    "FailurePeriod",
    "HoldingRecord",
    "InMemoryPITProvider",
    "MarketRegimeHistorical",
    "MethodologyComparison",
    "MonthlySnapshot",
    "PITSnapshot",
    "PassThreshold",
    "PerformanceCalculator",
    "PerformanceMetrics",
    "PointInTimeProvider",
    "RankICReport",
    "RebalanceAuditRecord",
    "RebalanceFrequency",
    "RegimeSegment",
    "ReplayConfig",
    "ReplayOrchestrator",
    "ReplayResult",
    "ScoredStock",
    "ScoredUniverseProvider",
    "SelectionMode",
    "ShadowPortfolio",
    "ShadowPosition",
    "ShadowSnapshot",
    "ValidationGate",
    "ValidationResult",
    "WalkForwardPartition",
    "WalkForwardSimulator",
    "classify_regime",
    "compute_failure_audit",
    "compute_rank_ic",
    "compute_rank_ic_report",
    "generate_walk_forward_partitions",
    "haircut_returns",
    "segment_by_regime",
    "signal_significance",
]
