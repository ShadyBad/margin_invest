"""Data models for portfolio optimization."""

from __future__ import annotations

from pydantic import BaseModel, Field


class PortfolioCandidate(BaseModel):
    """A single asset candidate for portfolio optimization."""

    ticker: str
    expected_alpha: float  # Calibrated expected excess return
    uncertainty: float | None = None  # From VAE variance (Phase 5)
    track: str = "unknown"  # "compounder", "mispricing", "both", etc.
    conviction: str = "none"  # CompositeTier value
    sector: str = "unknown"  # GICS sector


class OptimizationConstraints(BaseModel):
    """Constraints for portfolio optimization."""

    max_position: float = Field(default=0.20, description="Max weight per asset")
    min_position: float = Field(default=0.02, description="Min weight if included")
    max_sector: float = Field(default=0.40, description="Max weight per GICS sector")
    max_holdings: int = Field(default=10, description="Max number of holdings")
    max_turnover: float = Field(default=0.30, description="Max one-way turnover per rebalance")


class DROConfig(BaseModel):
    """Configuration for Distributionally Robust Optimization."""

    epsilon_base: float = Field(
        default=0.05,
        description="Base Wasserstein radius for ambiguity set",
    )
    gamma_base: float = Field(
        default=1.0,
        description="Base risk aversion parameter",
    )
    norm_type: str = Field(
        default="L2",
        description="Norm type for DRO penalty: 'L2' (QP) or 'Linf' (LP-convertible)",
    )
    regime_epsilon_multipliers: dict[str, float] = Field(
        default_factory=lambda: {
            "cheap": 0.7,
            "normal": 1.0,
            "expensive": 1.5,
            "euphoria": 2.5,
        },
    )
    regime_gamma_multipliers: dict[str, float] = Field(
        default_factory=lambda: {
            "cheap": 0.7,
            "normal": 1.0,
            "expensive": 1.5,
            "euphoria": 2.5,
        },
    )


class OptimizedPortfolio(BaseModel):
    """Result of portfolio optimization."""

    weights: dict[str, float]  # ticker -> weight (sums to 1.0)
    expected_return: float
    portfolio_risk: float  # sqrt(w.T @ Sigma @ w)
    diversification_ratio: float  # weighted avg vol / portfolio vol
    sector_exposures: dict[str, float]  # sector -> total weight
    constraints_binding: list[str]  # Which constraints are at their limits
    solver_status: str  # "optimal", "optimal_inaccurate", "infeasible", etc.
    epsilon_used: float
    gamma_used: float
