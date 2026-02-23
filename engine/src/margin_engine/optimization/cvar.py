"""Conditional Value-at-Risk (CVaR) portfolio optimization.

Standard Rockafellar-Uryasev LP formulation:

    minimize  -mu.T @ w + lambda * CVaR_alpha(w)
    subject to:
        w >= 0              (long-only)
        sum(w) == 1         (fully invested)
        w <= max_position   (position cap)

CVaR is linearized via auxiliary variables:
    CVaR_alpha(w) = min_t { t + (1/(S*(1-alpha))) * sum_s max(0, -r_s.T @ w - t) }

Where S = number of scenarios, r_s = return vector for scenario s.
"""

from __future__ import annotations

from collections import defaultdict

import cvxpy as cp
import numpy as np

from margin_engine.optimization.models import (
    OptimizationConstraints,
    OptimizedPortfolio,
    PortfolioCandidate,
)


def optimize_cvar(
    candidates: list[PortfolioCandidate],
    returns_scenarios: np.ndarray,
    tickers: list[str],
    constraints: OptimizationConstraints | None = None,
    alpha: float = 0.05,
    risk_aversion: float = 1.0,
) -> OptimizedPortfolio:
    """Run CVaR portfolio optimization.

    Uses the Rockafellar-Uryasev LP reformulation to minimize
    the Conditional Value-at-Risk at the alpha quantile.

    Args:
        candidates: Scored candidates with expected_alpha.
        returns_scenarios: (n_scenarios, n_assets) matrix of return scenarios.
        tickers: Ticker list matching scenario matrix columns.
        constraints: Position/sector constraints.
        alpha: CVaR confidence level (default 0.05 = 5% tail).
        risk_aversion: Trade-off between expected return and CVaR risk.

    Returns:
        OptimizedPortfolio with optimal weights.
    """
    if constraints is None:
        constraints = OptimizationConstraints()

    n_scenarios, n_assets = returns_scenarios.shape
    if n_assets == 0 or n_scenarios == 0:
        return _empty_cvar_portfolio()

    # Trivial case: single asset gets 100%
    if n_assets == 1:
        candidate_map = {c.ticker: c for c in candidates}
        t = tickers[0]
        exp_alpha = candidate_map[t].expected_alpha if t in candidate_map else 0.0
        port_returns = returns_scenarios[:, 0]
        risk = float(np.std(port_returns))
        sector = candidate_map[t].sector if t in candidate_map else "unknown"
        return OptimizedPortfolio(
            weights={t: 1.0},
            expected_return=exp_alpha,
            portfolio_risk=risk,
            diversification_ratio=1.0,
            sector_exposures={sector: 1.0},
            constraints_binding=[],
            solver_status="optimal",
            epsilon_used=0.0,
            gamma_used=risk_aversion,
        )

    candidate_map = {c.ticker: c for c in candidates}
    mu = np.zeros(n_assets)
    for i, t in enumerate(tickers):
        if t in candidate_map:
            mu[i] = candidate_map[t].expected_alpha

    # Decision variables
    w = cp.Variable(n_assets, nonneg=True)
    t_var = cp.Variable()  # VaR threshold
    u = cp.Variable(n_scenarios, nonneg=True)  # Auxiliary for max(0, loss - t)

    # CVaR linearization
    # u_s >= -r_s.T @ w - t  (loss exceeding threshold)
    # CVaR = t + (1 / (n_scenarios * (1 - alpha))) * sum(u)
    cvar = t_var + (1.0 / (n_scenarios * (1.0 - alpha))) * cp.sum(u)

    # Objective: minimize -mu.T @ w + risk_aversion * CVaR
    objective = cp.Minimize(-mu @ w + risk_aversion * cvar)

    # Constraints
    constraint_list = [
        cp.sum(w) == 1.0,
        w <= constraints.max_position,
    ]

    # CVaR constraints: u_s >= -r_s.T @ w - t for each scenario
    # Vectorized: u >= -returns_scenarios @ w - t
    constraint_list.append(u >= -returns_scenarios @ w - t_var)

    # Sector constraints
    sector_map: dict[str, list[int]] = defaultdict(list)
    for i, t in enumerate(tickers):
        if t in candidate_map:
            sector_map[candidate_map[t].sector].append(i)
    for sector, indices in sector_map.items():
        if len(indices) > 0:
            constraint_list.append(cp.sum(w[indices]) <= constraints.max_sector)

    prob = cp.Problem(objective, constraint_list)

    # Solve with CLARABEL (robust LP/conic), fall back to SCS
    solver_status = "unsolved"
    try:
        prob.solve(solver=cp.CLARABEL, verbose=False)
        solver_status = str(prob.status)
    except (cp.SolverError, Exception):
        try:
            prob.solve(solver=cp.SCS, verbose=False, max_iters=10000)
            solver_status = str(prob.status)
        except (cp.SolverError, Exception):
            return _infeasible_cvar_portfolio()

    if prob.status not in ("optimal", "optimal_inaccurate"):
        return _infeasible_cvar_portfolio()

    raw_weights = np.array(w.value).flatten()
    raw_weights = np.maximum(raw_weights, 0.0)
    raw_weights[raw_weights < constraints.min_position / 2] = 0.0

    # Enforce max_holdings
    if np.sum(raw_weights > 0) > constraints.max_holdings:
        sorted_indices = np.argsort(-raw_weights)
        raw_weights[sorted_indices[constraints.max_holdings :]] = 0.0

    total = np.sum(raw_weights)
    if total < 1e-10:
        return _infeasible_cvar_portfolio()
    weights = raw_weights / total

    weight_dict = {}
    for i, t in enumerate(tickers):
        if weights[i] > 1e-8:
            weight_dict[t] = float(weights[i])

    # Compute portfolio risk from scenarios
    portfolio_returns = returns_scenarios @ weights
    portfolio_risk = float(np.std(portfolio_returns))
    expected_ret = float(mu @ weights)

    # Diversification ratio
    individual_vols = np.std(returns_scenarios, axis=0)
    weighted_avg_vol = float(weights @ individual_vols)
    div_ratio = weighted_avg_vol / portfolio_risk if portfolio_risk > 1e-10 else 1.0

    # Sector exposures
    sector_exposures: dict[str, float] = defaultdict(float)
    for i, t in enumerate(tickers):
        if weights[i] > 1e-8 and t in candidate_map:
            sector_exposures[candidate_map[t].sector] += float(weights[i])

    return OptimizedPortfolio(
        weights=weight_dict,
        expected_return=expected_ret,
        portfolio_risk=portfolio_risk,
        diversification_ratio=div_ratio,
        sector_exposures=dict(sector_exposures),
        constraints_binding=[],
        solver_status=solver_status,
        epsilon_used=0.0,
        gamma_used=risk_aversion,
    )


def _empty_cvar_portfolio() -> OptimizedPortfolio:
    return OptimizedPortfolio(
        weights={},
        expected_return=0.0,
        portfolio_risk=0.0,
        diversification_ratio=1.0,
        sector_exposures={},
        constraints_binding=[],
        solver_status="no_candidates",
        epsilon_used=0.0,
        gamma_used=0.0,
    )


def _infeasible_cvar_portfolio() -> OptimizedPortfolio:
    return OptimizedPortfolio(
        weights={},
        expected_return=0.0,
        portfolio_risk=0.0,
        diversification_ratio=1.0,
        sector_exposures={},
        constraints_binding=[],
        solver_status="infeasible",
        epsilon_used=0.0,
        gamma_used=0.0,
    )
