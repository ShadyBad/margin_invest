"""Tests for non-linear transaction cost model."""

from __future__ import annotations

import numpy as np
from margin_engine.backtesting.cost_model import (
    ACADEMIC_BENCHMARKS,
    COST_ASSUMPTIONS,
    CostModelConfig,
    TransactionCost,
    compute_market_impact_bps,
    compute_spread_bps,
    compute_transaction_cost,
    validate_cost_assumptions,
)


class TestComputeSpreadBps:
    def test_large_cap_tight_spread(self):
        """Large-cap ($100B) should have tight spread ~8 bps."""
        spread = compute_spread_bps(100e9)
        # 3.0 + 50.0 / sqrt(100) = 3.0 + 5.0 = 8.0
        assert abs(spread - 8.0) < 0.01

    def test_small_cap_wide_spread(self):
        """Small-cap ($500M) should have wider spread."""
        spread = compute_spread_bps(500e6)
        assert spread > 50  # 3 + 50/sqrt(0.5) ~ 73.7

    def test_micro_cap_very_wide(self):
        """Micro-cap has very wide spread."""
        spread = compute_spread_bps(50e6)
        assert spread > 100

    def test_floor_on_tiny_market_cap(self):
        """Very small market cap doesn't cause errors."""
        spread = compute_spread_bps(100)  # $100 market cap
        assert spread > 0 and not np.isinf(spread)


class TestComputeMarketImpact:
    def test_small_trade_low_impact(self):
        """Small trade relative to ADV has low impact."""
        # 0.1 * sqrt(10_000 / 10_000_000) * 10000 = 0.1 * 0.03162 * 10000 ~ 31.6
        # Use a truly tiny trade: $100 vs $10M ADV
        impact = compute_market_impact_bps(100, 10_000_000, 0.1)
        assert impact < 5.0

    def test_large_trade_high_impact(self):
        """Large trade relative to ADV has high impact."""
        impact = compute_market_impact_bps(5_000_000, 1_000_000, 0.1)
        assert impact > 100

    def test_zero_adv_returns_zero(self):
        impact = compute_market_impact_bps(10_000, 0, 0.1)
        assert impact == 0.0

    def test_zero_trade_returns_zero(self):
        impact = compute_market_impact_bps(0, 10_000_000, 0.1)
        assert impact == 0.0

    def test_square_root_scaling(self):
        """Impact should scale with sqrt of trade fraction."""
        impact_1x = compute_market_impact_bps(100_000, 10_000_000, 0.1)
        impact_4x = compute_market_impact_bps(400_000, 10_000_000, 0.1)
        # 4x trade -> 2x impact (sqrt scaling)
        assert abs(impact_4x / impact_1x - 2.0) < 0.01


class TestComputeTransactionCost:
    def test_default_config(self):
        """Default config produces reasonable costs."""
        cost = compute_transaction_cost(100_000, 10_000_000, 50e9)
        assert cost.total_bps > 0
        assert cost.total_bps == cost.commission_bps + cost.spread_bps + cost.market_impact_bps

    def test_returns_transaction_cost_model(self):
        """Return type is TransactionCost."""
        cost = compute_transaction_cost(100_000, 10_000_000, 50e9)
        assert isinstance(cost, TransactionCost)

    def test_golden_value(self):
        """Golden-value test with known inputs."""
        config = CostModelConfig(base_commission_bps=5.0, market_impact_coefficient=0.1)
        cost = compute_transaction_cost(
            trade_value=1_000_000,
            adv=10_000_000,
            market_cap=50e9,
            config=config,
        )
        # commission = 5.0 bps
        # spread = 3.0 + 50.0/sqrt(50) ~ 10.07 bps
        # impact = 0.1 * sqrt(1e6/1e7) * 10000 ~ 316.2 bps
        assert cost.commission_bps == 5.0
        assert abs(cost.spread_bps - 10.07) < 0.1
        assert abs(cost.market_impact_bps - 316.2) < 1.0

    def test_nonlinear_exceeds_flat(self):
        """Non-linear costs > flat 15 bps for large trades on illiquid stocks."""
        cost = compute_transaction_cost(
            trade_value=2_000_000,
            adv=500_000,
            market_cap=500e6,
        )
        assert cost.total_bps > 15.0


class TestCostAssumptions:
    def test_assumptions_has_required_keys(self):
        assert "base_commission_bps" in COST_ASSUMPTIONS
        assert "market_impact_coefficient" in COST_ASSUMPTIONS
        assert "spread_formula" in COST_ASSUMPTIONS

    def test_assumptions_values_are_positive(self):
        assert COST_ASSUMPTIONS["base_commission_bps"] > 0
        assert COST_ASSUMPTIONS["market_impact_coefficient"] > 0

    def test_assumptions_has_description_keys(self):
        assert "spread_description" in COST_ASSUMPTIONS
        assert "impact_formula" in COST_ASSUMPTIONS
        assert "impact_description" in COST_ASSUMPTIONS

    def test_assumptions_not_modeled_is_list(self):
        assert isinstance(COST_ASSUMPTIONS["not_modeled"], list)
        assert len(COST_ASSUMPTIONS["not_modeled"]) > 0

    def test_assumptions_not_modeled_items(self):
        not_modeled = COST_ASSUMPTIONS["not_modeled"]
        assert "short-selling costs" in not_modeled
        assert "taxes" in not_modeled
        assert "management fees" in not_modeled
        assert "opportunity cost" in not_modeled
        assert "time-of-day effects" in not_modeled


class TestAcademicBenchmarks:
    def test_benchmarks_non_empty(self):
        assert len(ACADEMIC_BENCHMARKS) >= 2

    def test_benchmark_structure(self):
        for b in ACADEMIC_BENCHMARKS:
            assert "source" in b
            assert "paper" in b
            assert "asset_class" in b
            assert "market_cap_range" in b
            assert "cost_range_bps" in b
            assert len(b["cost_range_bps"]) == 2
            assert b["cost_range_bps"][0] <= b["cost_range_bps"][1]

    def test_frazzini_large_cap_benchmark(self):
        large_cap = [b for b in ACADEMIC_BENCHMARKS if b["market_cap_range"] == "large_cap"]
        assert len(large_cap) >= 1
        assert large_cap[0]["cost_range_bps"] == (10, 20)

    def test_frazzini_small_cap_benchmark(self):
        small_cap = [b for b in ACADEMIC_BENCHMARKS if b["market_cap_range"] == "small_cap"]
        assert len(small_cap) >= 1
        assert small_cap[0]["cost_range_bps"] == (30, 60)

    def test_novy_marx_all_cap_benchmark(self):
        all_cap = [b for b in ACADEMIC_BENCHMARKS if b["market_cap_range"] == "all_cap"]
        assert len(all_cap) >= 1
        assert all_cap[0]["cost_range_bps"] == (10, 50)


class TestValidateCostAssumptions:
    def test_within_range(self):
        result = validate_cost_assumptions(model_cost_bps=15.0, market_cap_billions=50.0)
        assert result["status"] == "within_range"

    def test_below_benchmark_optimistic(self):
        result = validate_cost_assumptions(model_cost_bps=3.0, market_cap_billions=50.0)
        assert result["status"] == "below_benchmark"

    def test_above_benchmark_conservative(self):
        result = validate_cost_assumptions(model_cost_bps=100.0, market_cap_billions=50.0)
        assert result["status"] == "above_benchmark"

    def test_small_cap_uses_small_cap_range(self):
        result = validate_cost_assumptions(model_cost_bps=40.0, market_cap_billions=0.5)
        assert result["status"] == "within_range"

    def test_result_contains_source(self):
        result = validate_cost_assumptions(model_cost_bps=15.0, market_cap_billions=50.0)
        assert "source" in result
        assert "Frazzini" in result["source"]

    def test_result_contains_model_cost(self):
        result = validate_cost_assumptions(model_cost_bps=15.0, market_cap_billions=50.0)
        assert result["model_cost_bps"] == 15.0

    def test_result_contains_benchmark_range(self):
        result = validate_cost_assumptions(model_cost_bps=15.0, market_cap_billions=50.0)
        assert "benchmark_range_bps" in result
        assert isinstance(result["benchmark_range_bps"], tuple)

    def test_mid_cap_uses_all_cap_range(self):
        """Market cap >=2B but <10B uses all_cap benchmark."""
        result = validate_cost_assumptions(model_cost_bps=25.0, market_cap_billions=5.0)
        assert result["status"] == "within_range"
        assert "Novy-Marx" in result["source"]

    def test_boundary_10b_uses_large_cap(self):
        """Exactly 10B should use large_cap benchmark."""
        result = validate_cost_assumptions(model_cost_bps=15.0, market_cap_billions=10.0)
        assert result["benchmark_range_bps"] == (10, 20)

    def test_boundary_2b_uses_all_cap(self):
        """Exactly 2B should use all_cap benchmark."""
        result = validate_cost_assumptions(model_cost_bps=25.0, market_cap_billions=2.0)
        assert result["benchmark_range_bps"] == (10, 50)

    def test_below_2b_uses_small_cap(self):
        """Below 2B should use small_cap benchmark."""
        result = validate_cost_assumptions(model_cost_bps=40.0, market_cap_billions=1.0)
        assert result["benchmark_range_bps"] == (30, 60)
