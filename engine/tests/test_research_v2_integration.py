"""Cross-phase integration tests for Research V2.

Verifies that the 6 phases work together end-to-end:
- Phase 1 (ANLS covariance) -> Phase 2 (DRO optimizer)
- Phase 3 (regime) -> Phase 2 (regime-scaled optimizer params)
- Phase 4 (cost model + turnover) -> Phase 2 (post-optimization)
- Phase 5 (ML) -> Phase 2 (blended alpha -> optimizer)
- Phase 6 (Rank IC + publication bias) -> backtest validation
"""

from __future__ import annotations

import numpy as np
import pytest
from margin_engine.backtesting.cost_model import compute_transaction_cost
from margin_engine.backtesting.models import (
    BacktestConfig,
    BacktestResult,
    DROConfig,
    OptimizationConstraints,
    PerformanceMetrics,
    SelectionMode,
)
from margin_engine.backtesting.publication_bias import haircut_returns, signal_significance
from margin_engine.backtesting.rank_ic import compute_rank_ic, compute_rank_ic_report
from margin_engine.backtesting.turnover import enforce_turnover_limit
from margin_engine.ml.blend import blend_alpha, blend_with_vae
from margin_engine.ml.clustering import cluster_stocks
from margin_engine.ml.signal_model import predict_alpha, train_cluster_models
from margin_engine.optimization.alpha_mapper import calibrate_alpha, v4_to_candidates
from margin_engine.optimization.cvar import optimize_cvar
from margin_engine.optimization.dro_meanvar import optimize_dro_meanvar
from margin_engine.optimization.models import PortfolioCandidate
from margin_engine.risk.covariance import compute_covariance
from margin_engine.risk.regime import detect_composite_regime


class TestPhase1ToPhase2:
    """Test: ANLS covariance -> DRO optimizer pipeline."""

    def test_anls_covariance_feeds_dro_optimizer(self):
        """Covariance from Phase 1 feeds directly into Phase 2 optimizer."""
        rng = np.random.default_rng(42)
        n_assets = 5
        n_obs = 200
        returns = rng.standard_normal((n_obs, n_assets)) * 0.02

        tickers = [f"STOCK{i}" for i in range(n_assets)]

        # Phase 1: Compute ANLS covariance
        cov_result = compute_covariance(returns, tickers, method="auto")
        assert cov_result.method == "anls"  # T >= N
        assert cov_result.matrix.shape == (n_assets, n_assets)

        # Phase 2: Feed into optimizer
        candidates = [
            PortfolioCandidate(
                ticker=t,
                expected_alpha=0.03 - 0.005 * i,
                track="compounder",
                conviction="high",
                sector=["Tech", "Healthcare", "Financials", "Energy", "Industrials"][i],
            )
            for i, t in enumerate(tickers)
        ]

        constraints = OptimizationConstraints(max_position=0.40, max_sector=0.50)
        result = optimize_dro_meanvar(
            candidates, cov_result.matrix, tickers, constraints=constraints
        )

        assert result.solver_status in ("optimal", "optimal_inaccurate")
        assert abs(sum(result.weights.values()) - 1.0) < 1e-3
        assert all(w >= -1e-8 for w in result.weights.values())
        assert all(w <= 0.40 + 1e-3 for w in result.weights.values())
        assert result.portfolio_risk > 0

    def test_linear_shrinkage_fallback_still_works(self):
        """When T < N, auto-selects linear shrinkage and optimizer still solves."""
        rng = np.random.default_rng(42)
        n_assets = 20
        n_obs = 15  # T < N -> linear shrinkage
        returns = rng.standard_normal((n_obs, n_assets)) * 0.02

        tickers = [f"S{i}" for i in range(n_assets)]
        cov_result = compute_covariance(returns, tickers, method="auto")
        assert cov_result.method == "linear"

        candidates = [
            PortfolioCandidate(
                ticker=t,
                expected_alpha=0.02,
                track="compounder",
                conviction="high",
                sector="Tech",
            )
            for t in tickers
        ]

        result = optimize_dro_meanvar(
            candidates,
            cov_result.matrix,
            tickers,
            constraints=OptimizationConstraints(max_position=0.20, max_sector=1.0),
        )
        assert result.solver_status in ("optimal", "optimal_inaccurate")
        assert abs(sum(result.weights.values()) - 1.0) < 1e-3


class TestPhase3ToPhase2:
    """Test: Regime detection -> optimizer parameter scaling."""

    def test_regime_drives_epsilon_gamma_scaling(self):
        """Stressed regime produces more conservative portfolio (higher epsilon/gamma)."""
        rng = np.random.default_rng(42)
        returns = rng.standard_normal((100, 3)) * 0.02
        cov = (returns - returns.mean(axis=0)).T @ (returns - returns.mean(axis=0)) / 100
        tickers = ["A", "B", "C"]
        candidates = [
            PortfolioCandidate(
                ticker=t, expected_alpha=a, track="compounder", conviction="high", sector=s
            )
            for t, a, s in [("A", 0.04, "Tech"), ("B", 0.02, "Health"), ("C", 0.01, "Fin")]
        ]
        constraints = OptimizationConstraints(max_position=0.50)

        # Detect regimes
        normal_regime = detect_composite_regime(cape=20.0, vix=17.0)
        stressed_regime = detect_composite_regime(cape=38.0, vix=35.0, credit_spread=6.0)

        assert normal_regime.overall.value in ("cheap", "normal")
        assert stressed_regime.overall.value == "euphoria"

        # Run optimizer with regime string
        normal_result = optimize_dro_meanvar(
            candidates, cov, tickers, constraints=constraints,
            regime=normal_regime.overall.value,
        )
        stressed_result = optimize_dro_meanvar(
            candidates, cov, tickers, constraints=constraints,
            regime=stressed_regime.overall.value,
        )

        # Stressed regime uses higher epsilon (more conservative DRO penalty)
        assert stressed_result.epsilon_used > normal_result.epsilon_used
        assert stressed_result.gamma_used > normal_result.gamma_used


class TestPhase4PostOptimization:
    """Test: Cost model + turnover applied after optimizer output."""

    def test_cost_and_turnover_post_optimization_pipeline(self):
        """Optimizer output -> turnover enforcement -> cost estimation."""
        rng = np.random.default_rng(42)
        n = 5
        returns = rng.standard_normal((200, n)) * 0.02
        cov = (returns - returns.mean(axis=0)).T @ (returns - returns.mean(axis=0)) / 200
        tickers = [f"T{i}" for i in range(n)]

        candidates = [
            PortfolioCandidate(
                ticker=t, expected_alpha=0.03 - 0.005 * i,
                track="compounder", conviction="high",
                sector=["Tech", "HC", "Fin", "Eng", "Ind"][i],
            )
            for i, t in enumerate(tickers)
        ]

        # Previous weights (simulating rebalance)
        old_weights = {"T0": 0.20, "T1": 0.20, "T2": 0.20, "T3": 0.20, "T4": 0.20}

        # Phase 2: Optimize
        result = optimize_dro_meanvar(
            candidates, cov, tickers,
            constraints=OptimizationConstraints(max_position=0.40),
        )
        new_weights = result.weights

        # Phase 4: Enforce turnover
        adjusted = enforce_turnover_limit(old_weights, new_weights, max_turnover=0.15)
        assert abs(sum(adjusted.values()) - 1.0) < 1e-6

        # Phase 4: Compute costs per trade
        portfolio_value = 1_000_000
        for ticker, weight in adjusted.items():
            old_w = old_weights.get(ticker, 0.0)
            trade_value = portfolio_value * abs(weight - old_w)
            if trade_value > 0:
                cost = compute_transaction_cost(
                    trade_value=trade_value,
                    adv=5_000_000,
                    market_cap=10e9,
                )
                assert cost.total_bps > 0
                assert cost.spread_bps > 0
                assert cost.commission_bps == 5.0


class TestPhase5MLPipeline:
    """Test: ML pipeline -> alpha blending -> optimizer."""

    def test_clustering_gbm_blend_to_optimizer(self):
        """Features -> cluster -> GBM train -> predict -> blend -> optimize."""
        rng = np.random.default_rng(42)
        n_samples = 200
        n_features = 10
        n_assets = 5

        features = rng.standard_normal((n_samples, n_features))
        forward_returns = rng.standard_normal(n_samples) * 0.02
        tickers = [f"T{i}" for i in range(n_samples)]

        # Cluster
        clusters = cluster_stocks(features, tickers, n_clusters=3, seed=42)
        assert len(clusters) > 0
        all_clustered = sum(len(v) for v in clusters.values())
        assert all_clustered == n_samples

        # Convert clusters to index-based for training
        ticker_to_idx = {t: i for i, t in enumerate(tickers)}
        idx_clusters = {
            cid: [ticker_to_idx[t] for t in ts]
            for cid, ts in clusters.items()
        }

        # Train GBM models
        models = train_cluster_models(features, forward_returns, idx_clusters, seed=42)
        assert len(models) == len(clusters)

        # Predict on a small subset (first 5 assets)
        subset_features = features[:n_assets]
        # Use first cluster's model for prediction
        first_model_bytes = next(iter(models.values()))
        predictions = predict_alpha(first_model_bytes, subset_features)
        assert predictions.shape == (n_assets,)

        # Blend with composite alphas
        composite_alphas = [0.03, 0.02, 0.015, 0.01, 0.005]
        blended = [
            blend_alpha(c, float(p), ml_weight=0.30)
            for c, p in zip(composite_alphas, predictions)
        ]
        assert len(blended) == n_assets

        # Feed into optimizer
        opt_tickers = [f"OPT{i}" for i in range(n_assets)]
        candidates = [
            PortfolioCandidate(
                ticker=t, expected_alpha=a, track="compounder",
                conviction="high", sector="Tech",
            )
            for t, a in zip(opt_tickers, blended)
        ]
        cov = np.eye(n_assets) * 0.01

        result = optimize_dro_meanvar(
            candidates, cov, opt_tickers,
            constraints=OptimizationConstraints(max_position=0.40, max_sector=1.0),
        )
        assert result.solver_status in ("optimal", "optimal_inaccurate")
        assert len(result.weights) > 0

    def test_vae_uncertainty_feeds_optimizer(self):
        """VAE variance -> uncertainty -> optimizer can use it."""
        pytest.importorskip("torch", reason="torch required for FactorVAE")
        from margin_engine.ml.factor_vae import (
            FactorVAEConfig,
            predict_factor_vae,
            train_factor_vae,
        )

        rng = np.random.default_rng(42)
        features = rng.standard_normal((100, 10)).astype(np.float32)
        forward_returns = rng.standard_normal(100).astype(np.float32) * 0.02

        config = FactorVAEConfig(epochs=20, latent_dim=4, hidden_dim=32)
        model_bytes, metrics = train_factor_vae(features, forward_returns, config, seed=42)

        # Predict on subset
        subset = features[:5]
        means, variances = predict_factor_vae(model_bytes, subset, config, seed=42)
        assert means.shape == (5,)
        assert variances.shape == (5,)
        assert all(v > 0 for v in variances)

        # Blend with VAE
        composite_alpha = 0.025
        gbm_alpha = 0.020
        blended, uncertainty = blend_with_vae(
            composite_alpha, gbm_alpha,
            vae_mean=float(means[0]), vae_var=float(variances[0]),
            gbm_weight=0.30, vae_weight=0.15,
        )
        assert uncertainty > 0
        # remaining=0.55, gbm=0.30, vae=0.15
        expected = 0.55 * composite_alpha + 0.30 * gbm_alpha + 0.15 * float(means[0])
        assert abs(blended - expected) < 1e-6

        # The uncertainty can be attached to PortfolioCandidate
        candidate = PortfolioCandidate(
            ticker="TEST", expected_alpha=blended,
            uncertainty=uncertainty, track="compounder",
            conviction="high", sector="Tech",
        )
        assert candidate.uncertainty is not None
        assert candidate.uncertainty > 0


class TestPhase6BacktestValidation:
    """Test: Rank IC + publication bias + full-pipeline validation."""

    def test_rank_ic_across_multiple_periods(self):
        """Simulate multi-period scoring and Rank IC tracking."""
        rng = np.random.default_rng(42)
        ic_series = []

        for period in range(12):
            n_stocks = 50
            # Predicted scores have some signal: base rank + noise
            true_alphas = rng.standard_normal(n_stocks) * 0.03
            predicted_scores = true_alphas + rng.standard_normal(n_stocks) * 0.02
            realized_returns = true_alphas + rng.standard_normal(n_stocks) * 0.05

            ic = compute_rank_ic(predicted_scores, realized_returns)
            ic_series.append(ic)

        report = compute_rank_ic_report(ic_series)
        assert report.n_periods == 12
        # With actual signal in the data, mean IC should be positive
        assert report.ic_mean > 0
        assert 0.0 < report.hit_rate <= 1.0
        assert len(report.ic_series) == 12

    def test_publication_bias_haircut_realistic(self):
        """12% haircut on a realistic backtest should produce conservative estimates."""
        metrics = PerformanceMetrics(
            cagr=0.18,
            excess_cagr=0.10,
            sharpe_ratio=1.4,
            sortino_ratio=1.8,
            max_drawdown=0.25,
            win_rate=0.62,
            information_ratio=0.9,
            total_return=2.5,
            benchmark_total_return=1.0,
            num_months=60,
            avg_turnover=0.35,
        )

        haircut = haircut_returns(metrics, decay_rate=0.12)

        # All return metrics reduced by 12%
        assert haircut.cagr < metrics.cagr
        assert abs(haircut.cagr - 0.18 * 0.88) < 1e-6
        assert haircut.excess_cagr < metrics.excess_cagr
        assert haircut.sharpe_ratio < metrics.sharpe_ratio

        # Risk metrics unchanged
        assert haircut.max_drawdown == metrics.max_drawdown
        assert haircut.win_rate == metrics.win_rate
        assert haircut.avg_turnover == metrics.avg_turnover
        assert haircut.benchmark_total_return == metrics.benchmark_total_return

    def test_signal_significance_on_rank_ic(self):
        """Combine Rank IC report with significance testing."""
        ic_series = [0.05, 0.08, 0.03, 0.06, 0.09, 0.04, 0.07, 0.05, 0.06, 0.08,
                     0.04, 0.07]
        report = compute_rank_ic_report(ic_series)

        t_stat, passes = signal_significance(report.ic_mean, report.n_periods)
        # IC ~0.06, n=12, t = 0.06 * sqrt(12) = ~0.208 -> does not pass 1.8
        assert not passes

        # With more data (higher n), same IC would pass
        t_stat2, passes2 = signal_significance(report.ic_mean, 1000)
        assert passes2  # 0.06 * sqrt(1000) = ~1.9 -> passes

    def test_backtest_config_with_optimized_mode(self):
        """BacktestConfig supports OPTIMIZED mode with DRO params."""
        config = BacktestConfig(
            selection_mode=SelectionMode.OPTIMIZED,
            optimization_constraints=OptimizationConstraints(
                max_position=0.15, max_holdings=20
            ),
            dro_config=DROConfig(epsilon_base=0.08, gamma_base=1.5),
        )
        assert config.selection_mode == SelectionMode.OPTIMIZED
        assert config.optimization_constraints is not None
        assert config.optimization_constraints.max_position == 0.15
        assert config.dro_config is not None
        assert config.dro_config.epsilon_base == 0.08

    def test_backtest_result_with_rank_ic_and_haircut(self):
        """BacktestResult can hold both RankICReport and haircut metrics."""
        from margin_engine.backtesting.rank_ic import RankICReport

        metrics = PerformanceMetrics(
            cagr=0.12, excess_cagr=0.05, sharpe_ratio=1.0,
            sortino_ratio=1.2, max_drawdown=0.20, win_rate=0.58,
            information_ratio=0.6, total_return=1.5,
            benchmark_total_return=0.8, num_months=48, avg_turnover=0.25,
        )
        haircut = haircut_returns(metrics)
        ic_report = RankICReport(
            ic_mean=0.06, ic_std=0.03, ic_ir=2.0,
            hit_rate=0.75, n_periods=48, ic_series=[0.06] * 48,
        )

        result = BacktestResult(
            config=BacktestConfig(),
            snapshots=[],
            metrics=metrics,
            rank_ic_report=ic_report,
            haircut_metrics=haircut,
            duration_seconds=1.5,
        )
        assert result.rank_ic_report is not None
        assert result.rank_ic_report.ic_mean == 0.06
        assert result.haircut_metrics is not None
        assert result.haircut_metrics.cagr < result.metrics.cagr


class TestFullPipelineEndToEnd:
    """End-to-end test: synthetic data through all 6 phases."""

    def test_full_pipeline(self):
        """Run all 6 phases on synthetic data in sequence."""
        rng = np.random.default_rng(12345)
        n_assets = 10
        n_obs = 200

        # --- Phase 1: Covariance ---
        returns = rng.standard_normal((n_obs, n_assets)) * 0.02
        tickers = [f"STOCK{i}" for i in range(n_assets)]
        cov_result = compute_covariance(returns, tickers, method="auto")
        assert cov_result.method == "anls"  # 200 >= 10

        # --- Phase 3: Regime ---
        regime = detect_composite_regime(cape=22.0, vix=18.0)
        assert regime.overall.value in ("cheap", "normal")
        regime_str = regime.overall.value

        # --- Phase 5: ML (simplified - use synthetic features) ---
        features = rng.standard_normal((n_assets, 8))
        forward_rets = rng.standard_normal(n_assets) * 0.02
        clusters = cluster_stocks(features, tickers, n_clusters=2, seed=42)

        ticker_to_idx = {t: i for i, t in enumerate(tickers)}
        idx_clusters = {
            cid: [ticker_to_idx[t] for t in ts]
            for cid, ts in clusters.items()
        }
        models = train_cluster_models(features, forward_rets, idx_clusters, seed=42)

        # Get predictions from first cluster model (simplified)
        first_model = next(iter(models.values()))
        ml_predictions = predict_alpha(first_model, features)

        # Blend composite + ML
        composite_alphas = [(0.03 - 0.003 * i) for i in range(n_assets)]
        blended_alphas = [
            blend_alpha(c, float(ml), ml_weight=0.30)
            for c, ml in zip(composite_alphas, ml_predictions)
        ]

        # --- Phase 2: DRO Optimization ---
        sectors = ["Tech", "HC", "Fin", "Eng", "Ind"] * 2
        candidates = [
            PortfolioCandidate(
                ticker=t, expected_alpha=a, track="compounder",
                conviction="high", sector=sectors[i],
            )
            for i, (t, a) in enumerate(zip(tickers, blended_alphas))
        ]
        constraints = OptimizationConstraints(
            max_position=0.25, max_sector=0.50, max_holdings=8,
        )
        dro_config = DROConfig(epsilon_base=0.05, gamma_base=1.0)

        portfolio = optimize_dro_meanvar(
            candidates, cov_result.matrix, tickers,
            constraints=constraints, dro_config=dro_config, regime=regime_str,
        )
        assert portfolio.solver_status in ("optimal", "optimal_inaccurate")
        assert abs(sum(portfolio.weights.values()) - 1.0) < 1e-3
        assert len(portfolio.weights) <= 8

        # --- Phase 4: Cost + Turnover ---
        old_weights = {t: 1.0 / n_assets for t in tickers}
        adjusted = enforce_turnover_limit(old_weights, portfolio.weights, max_turnover=0.30)
        assert abs(sum(adjusted.values()) - 1.0) < 1e-6

        total_cost_bps = 0.0
        for ticker, weight in adjusted.items():
            trade_value = 1_000_000 * abs(weight - old_weights.get(ticker, 0.0))
            if trade_value > 100:
                cost = compute_transaction_cost(trade_value, 5_000_000, 10e9)
                total_cost_bps += cost.total_bps * abs(weight - old_weights.get(ticker, 0.0))

        # --- Phase 6: Rank IC + Publication Bias ---
        # Simulate scoring IC
        predicted_scores = np.array(blended_alphas)
        realized = rng.standard_normal(n_assets) * 0.03
        ic = compute_rank_ic(predicted_scores, realized)
        # IC is a float in [-1, 1]
        assert -1.0 <= ic <= 1.0

        # Publication bias
        metrics = PerformanceMetrics(
            cagr=0.15, excess_cagr=0.08, sharpe_ratio=1.2,
            sortino_ratio=1.5, max_drawdown=0.22, win_rate=0.60,
            information_ratio=0.7, total_return=2.0,
            benchmark_total_return=0.9, num_months=60, avg_turnover=0.28,
        )
        haircut = haircut_returns(metrics)
        assert haircut.cagr < metrics.cagr

        # Signal significance
        t_stat, sig = signal_significance(ic, n_obs=60)
        assert isinstance(t_stat, float)
        assert isinstance(sig, bool)

    def test_cvar_alternative_path(self):
        """CVaR optimizer as alternative to DRO, using same pipeline."""
        rng = np.random.default_rng(42)
        n_assets = 5
        n_scenarios = 500

        scenarios = rng.standard_normal((n_scenarios, n_assets)) * 0.02
        tickers = [f"T{i}" for i in range(n_assets)]
        candidates = [
            PortfolioCandidate(
                ticker=t, expected_alpha=0.03 - 0.005 * i,
                track="compounder", conviction="high",
                sector=["Tech", "HC", "Fin", "Eng", "Ind"][i],
            )
            for i, t in enumerate(tickers)
        ]

        result = optimize_cvar(
            candidates, scenarios, tickers,
            constraints=OptimizationConstraints(max_position=0.40),
            alpha=0.05, risk_aversion=1.0,
        )
        assert result.solver_status in ("optimal", "optimal_inaccurate")
        assert abs(sum(result.weights.values()) - 1.0) < 1e-3
        assert result.portfolio_risk > 0


class TestAlphaMapperIntegration:
    """Test alpha_mapper connects scoring models to optimizer."""

    def test_calibrate_alpha_to_optimizer(self):
        """calibrate_alpha -> v4_to_candidates -> optimizer."""
        from margin_engine.models.scoring import CompositeScore, FactorBreakdown, FactorScore

        # Create minimal CompositeScores
        composites = []
        for i in range(5):
            breakdown = FactorBreakdown(
                factor_name="quality",
                weight=0.40,
                sub_scores=[
                    FactorScore(name="gross_profitability", raw_value=0.3 + i * 0.05,
                                percentile_rank=50.0 + i * 10),
                ],
            )
            empty_breakdown = FactorBreakdown(
                factor_name="value", weight=0.30, sub_scores=[],
            )
            mom_breakdown = FactorBreakdown(
                factor_name="momentum", weight=0.30, sub_scores=[],
            )
            cs = CompositeScore(
                ticker=f"T{i}",
                composite_percentile=60.0 + i * 5,
                composite_raw_score=60.0 + i * 5,
                quality=breakdown,
                value=empty_breakdown,
                momentum=mom_breakdown,
                filters_passed=[],
                data_coverage=1.0,
            )
            composites.append(cs)

        # Phase 2: calibrate alpha
        alphas = calibrate_alpha(composites, target_spread=0.10)
        assert len(alphas) == 5
        # Sum of alphas should be near zero (z-scored)
        assert abs(sum(alphas.values())) < 1e-6
        # Higher-scored stock gets higher alpha
        assert alphas["T4"] > alphas["T0"]

        # Convert to candidates
        v4_results = [
            {"ticker": f"T{i}", "opportunity_type": "compounder",
             "conviction": "high", "sector": "Tech"}
            for i in range(5)
        ]
        candidates = v4_to_candidates(v4_results, composites, alphas)
        assert len(candidates) == 5
        assert all(isinstance(c, PortfolioCandidate) for c in candidates)

        # Optimize
        cov = np.eye(5) * 0.01
        tickers = [f"T{i}" for i in range(5)]
        result = optimize_dro_meanvar(
            candidates, cov, tickers,
            constraints=OptimizationConstraints(max_position=0.40, max_sector=1.0),
        )
        assert result.solver_status in ("optimal", "optimal_inaccurate")
        # Highest alpha stock should have highest weight (equal variance)
        assert result.weights.get("T4", 0) >= result.weights.get("T0", 0) - 0.05
