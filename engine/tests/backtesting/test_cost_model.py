"""Tests for non-linear transaction cost model."""

from __future__ import annotations

import numpy as np
from margin_engine.backtesting.cost_model import (
    CostModelConfig,
    TransactionCost,
    compute_market_impact_bps,
    compute_spread_bps,
    compute_transaction_cost,
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
