"""Backtesting engine — walk-forward simulation and validation."""

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
from margin_engine.backtesting.publication_bias import haircut_returns, signal_significance
from margin_engine.backtesting.rank_ic import (
    RankICReport,
    compute_rank_ic,
    compute_rank_ic_report,
)
from margin_engine.backtesting.simulator import (
    BenchmarkProvider,
    ScoredStock,
    ScoredUniverseProvider,
    WalkForwardSimulator,
)
from margin_engine.backtesting.validation import MethodologyComparison, ValidationGate

__all__ = [
    "BacktestConfig",
    "BacktestResult",
    "BenchmarkProvider",
    "HoldingRecord",
    "MethodologyComparison",
    "MonthlySnapshot",
    "PassThreshold",
    "PerformanceCalculator",
    "PerformanceMetrics",
    "RankICReport",
    "RebalanceFrequency",
    "ScoredStock",
    "ScoredUniverseProvider",
    "SelectionMode",
    "ValidationGate",
    "ValidationResult",
    "WalkForwardSimulator",
    "compute_rank_ic",
    "compute_rank_ic_report",
    "haircut_returns",
    "signal_significance",
]
