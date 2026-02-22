"""Wasserstein Distributionally Robust mean-variance portfolio optimization.

Implements the DRO formulation from Esfahani & Kuhn where the
ambiguity set is a Wasserstein ball around the empirical distribution.

For the 2-Wasserstein ball of radius epsilon, the robust problem
reformulates to a norm-regularized quadratic program:

    maximize  mu.T @ w - epsilon * ||w||_2 - gamma * w.T @ Sigma @ w
    subject to:
        w >= 0                      (long-only)
        sum(w) == 1                 (fully invested)
        w <= max_position           (position cap)
        A_sector @ w <= max_sector  (per-sector caps)

This is a QP solvable by OSQP (primary) or SCS (fallback).
"""

from __future__ import annotations

from collections import defaultdict

import cvxpy as cp
import numpy as np

from margin_engine.optimization.models import (
    DROConfig,
    OptimizationConstraints,
    OptimizedPortfolio,
    PortfolioCandidate,
)


def optimize_dro_meanvar(
    candidates: list[PortfolioCandidate],
    covariance: np.ndarray,
    tickers: list[str],
    constraints: OptimizationConstraints | None = None,
    dro_config: DROConfig | None = None,
    regime: str = "normal",
) -> OptimizedPortfolio:
    """Run Wasserstein DRO mean-variance optimization.

    Args:
        candidates: Scored candidates with expected_alpha.
        covariance: (n_assets, n_assets) covariance matrix (from ANLS or linear shrinkage).
        tickers: Ticker list matching covariance matrix column order.
        constraints: Position/sector/turnover constraints.
        dro_config: DRO parameters (epsilon, gamma, norm type).
        regime: Market regime string for epsilon/gamma scaling.

    Returns:
        OptimizedPortfolio with optimal weights and diagnostics.
    """
    if constraints is None:
        constraints = OptimizationConstraints()
    if dro_config is None:
        dro_config = DROConfig()

    n_assets = len(tickers)
    if n_assets == 0:
        return _empty_portfolio(dro_config, regime)

    # Scale epsilon and gamma by regime
    epsilon = dro_config.epsilon_base * dro_config.regime_epsilon_multipliers.get(regime, 1.0)
    gamma = dro_config.gamma_base * dro_config.regime_gamma_multipliers.get(regime, 1.0)

    # Trivial case: single asset gets 100%
    if n_assets == 1:
        candidate_map = {c.ticker: c for c in candidates}
        t = tickers[0]
        alpha = candidate_map[t].expected_alpha if t in candidate_map else 0.0
        risk = float(np.sqrt(covariance[0, 0])) if covariance.size > 0 else 0.0
        sector = candidate_map[t].sector if t in candidate_map else "unknown"
        return OptimizedPortfolio(
            weights={t: 1.0},
            expected_return=alpha,
            portfolio_risk=risk,
            diversification_ratio=1.0,
            sector_exposures={sector: 1.0},
            constraints_binding=[],
            solver_status="optimal",
            epsilon_used=epsilon,
            gamma_used=gamma,
        )

    # Map candidates to the covariance matrix ordering
    candidate_map = {c.ticker: c for c in candidates}
    mu = np.zeros(n_assets)
    for i, t in enumerate(tickers):
        if t in candidate_map:
            mu[i] = candidate_map[t].expected_alpha

    # Decision variable
    w = cp.Variable(n_assets, nonneg=True)

    # Objective: maximize mu.T @ w - epsilon * ||w||_2 - gamma * w.T @ Sigma @ w
    # cvxpy maximizes, so: objective = mu @ w - epsilon * norm(w, 2) - gamma * quad_form(w, Sigma)
    expected_return_term = mu @ w
    dro_penalty = epsilon * cp.norm(w, 2)
    risk_term = gamma * cp.quad_form(w, covariance)

    objective = cp.Maximize(expected_return_term - dro_penalty - risk_term)

    # Constraints
    constraint_list = [
        cp.sum(w) == 1.0,
        w <= constraints.max_position,
    ]

    # Sector constraints
    sector_map: dict[str, list[int]] = defaultdict(list)
    for i, t in enumerate(tickers):
        if t in candidate_map:
            sector_map[candidate_map[t].sector].append(i)
    for sector, indices in sector_map.items():
        if len(indices) > 0:
            constraint_list.append(
                cp.sum(w[indices]) <= constraints.max_sector
            )

    # Cardinality constraint (max_holdings) via big-M relaxation
    # This makes the problem a MIQP which is much harder. For now,
    # we rely on the min_position threshold and post-processing to
    # enforce cardinality. The optimizer naturally concentrates.

    prob = cp.Problem(objective, constraint_list)

    # Solve with SCS (handles SOCP due to norm term), fall back to CLARABEL
    solver_status = "unsolved"
    try:
        prob.solve(solver=cp.SCS, verbose=False, max_iters=10000)
        solver_status = str(prob.status)
    except (cp.SolverError, Exception):
        try:
            prob.solve(solver=cp.CLARABEL, verbose=False)
            solver_status = str(prob.status)
        except (cp.SolverError, Exception):
            return _infeasible_portfolio(dro_config, regime, epsilon, gamma)

    if prob.status not in ("optimal", "optimal_inaccurate"):
        return _infeasible_portfolio(dro_config, regime, epsilon, gamma)

    raw_weights = np.array(w.value).flatten()

    # Post-processing: zero out tiny weights, enforce max_holdings
    raw_weights = np.maximum(raw_weights, 0.0)  # Numerical cleanup
    raw_weights[raw_weights < constraints.min_position / 2] = 0.0

    # Enforce max_holdings by keeping top N by weight
    if np.sum(raw_weights > 0) > constraints.max_holdings:
        sorted_indices = np.argsort(-raw_weights)
        cutoff_idx = constraints.max_holdings
        raw_weights[sorted_indices[cutoff_idx:]] = 0.0

    # Renormalize
    total = np.sum(raw_weights)
    if total < 1e-10:
        return _infeasible_portfolio(dro_config, regime, epsilon, gamma)
    weights = raw_weights / total

    # Build result
    weight_dict = {}
    for i, t in enumerate(tickers):
        if weights[i] > 1e-8:
            weight_dict[t] = float(weights[i])

    # Portfolio risk
    portfolio_variance = float(weights @ covariance @ weights)
    portfolio_risk = float(np.sqrt(max(portfolio_variance, 0.0)))

    # Expected return
    expected_ret = float(mu @ weights)

    # Diversification ratio: weighted avg volatility / portfolio volatility
    individual_vols = np.sqrt(np.diag(covariance))
    weighted_avg_vol = float(weights @ individual_vols)
    div_ratio = weighted_avg_vol / portfolio_risk if portfolio_risk > 1e-10 else 1.0

    # Sector exposures
    sector_exposures: dict[str, float] = defaultdict(float)
    for i, t in enumerate(tickers):
        if weights[i] > 1e-8 and t in candidate_map:
            sector_exposures[candidate_map[t].sector] += float(weights[i])

    # Identify binding constraints
    binding = _find_binding_constraints(weights, constraints, sector_exposures)

    return OptimizedPortfolio(
        weights=weight_dict,
        expected_return=expected_ret,
        portfolio_risk=portfolio_risk,
        diversification_ratio=div_ratio,
        sector_exposures=dict(sector_exposures),
        constraints_binding=binding,
        solver_status=solver_status,
        epsilon_used=epsilon,
        gamma_used=gamma,
    )


def _find_binding_constraints(
    weights: np.ndarray,
    constraints: OptimizationConstraints,
    sector_exposures: dict[str, float],
    tol: float = 1e-4,
) -> list[str]:
    """Identify which constraints are binding (at their limit)."""
    binding: list[str] = []

    # Position cap binding
    for i, w in enumerate(weights):
        if abs(w - constraints.max_position) < tol:
            binding.append(f"max_position[{i}]")

    # Sector cap binding
    for sector, exposure in sector_exposures.items():
        if abs(exposure - constraints.max_sector) < tol:
            binding.append(f"max_sector[{sector}]")

    return binding


def _empty_portfolio(config: DROConfig, regime: str) -> OptimizedPortfolio:
    """Return empty portfolio when no candidates."""
    return OptimizedPortfolio(
        weights={},
        expected_return=0.0,
        portfolio_risk=0.0,
        diversification_ratio=1.0,
        sector_exposures={},
        constraints_binding=[],
        solver_status="no_candidates",
        epsilon_used=config.epsilon_base * config.regime_epsilon_multipliers.get(regime, 1.0),
        gamma_used=config.gamma_base * config.regime_gamma_multipliers.get(regime, 1.0),
    )


def _infeasible_portfolio(
    config: DROConfig,
    regime: str,
    epsilon: float,
    gamma: float,
) -> OptimizedPortfolio:
    """Return empty portfolio when optimization is infeasible."""
    return OptimizedPortfolio(
        weights={},
        expected_return=0.0,
        portfolio_risk=0.0,
        diversification_ratio=1.0,
        sector_exposures={},
        constraints_binding=[],
        solver_status="infeasible",
        epsilon_used=epsilon,
        gamma_used=gamma,
    )
