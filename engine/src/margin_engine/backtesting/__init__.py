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
    ValidationResult,
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
    "RebalanceFrequency",
    "ScoredStock",
    "ScoredUniverseProvider",
    "ValidationGate",
    "ValidationResult",
    "WalkForwardSimulator",
]
