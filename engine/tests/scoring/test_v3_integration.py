"""Integration test -- full v3 pipeline from financial data to conviction output."""

import pytest
from decimal import Decimal

from margin_engine.models.financial import (
    BalanceSheet,
    CashFlowStatement,
    FinancialHistory,
    FinancialPeriod,
    GICSSector,
    IncomeStatement,
)
from margin_engine.models.scoring import ConvictionLevel
from margin_engine.scoring.quantitative.moat_durability import moat_durability_score
from margin_engine.scoring.quantitative.reverse_dcf import reverse_dcf_growth_gap
from margin_engine.scoring.quantitative.ensemble_valuation import compute_ensemble_valuation
from margin_engine.scoring.v3_composite import compute_track_a_score, compute_track_b_score
from margin_engine.scoring.v3_thresholds import assess_track_a_conviction, assess_track_b_conviction
from margin_engine.scoring.v3_orchestrator import V3TrackResult, orchestrate_v3
from margin_engine.scoring.timing_overlay import compute_v3_timing_signal


def _make_compounder_history() -> FinancialHistory:
    """5 years of data resembling a strong compounder (rising ROIC, margins)."""
    periods = []
    for i, year in enumerate(range(2019, 2024)):
        revenue = Decimal(str(500 + i * 200))
        ebit = Decimal(str(80 + i * 50))
        equity = Decimal(str(300 + i * 100))
        gross_profit = revenue * Decimal("0.45") + Decimal(str(i * 20))
        periods.append(
            FinancialPeriod(
                period_end=f"{year}-12-31",
                filing_date=f"{year + 1}-02-15",
                current_income=IncomeStatement(
                    revenue=revenue,
                    ebit=ebit,
                    cost_of_revenue=revenue - gross_profit,
                    gross_profit=gross_profit,
                    depreciation=Decimal("30"),
                    net_income=ebit * Decimal("0.79"),
                    shares_outstanding=100,
                ),
                current_balance=BalanceSheet(
                    total_assets=Decimal("1500"),
                    total_equity=equity,
                    long_term_debt=Decimal("200"),
                    short_term_debt=Decimal("50"),
                    cash_and_equivalents=Decimal("50"),
                    shares_outstanding=100,
                ),
                current_cash_flow=CashFlowStatement(
                    operating_cash_flow=ebit * Decimal("1.1"),
                    capital_expenditures=Decimal("-80"),
                ),
            )
        )
    return FinancialHistory(ticker="COMP", periods=periods)


class TestV3FullPipeline:
    def test_compounder_pipeline(self):
        """Strong compounder data flows through entire v3 pipeline."""
        history = _make_compounder_history()

        # Step 1: Moat durability
        moat = moat_durability_score(history)
        assert moat.raw_value >= 2.0, f"Expected 2+ moat signatures, got {moat.raw_value}"

        # Step 2: Reverse DCF growth gap
        # Price low enough that implied growth < sustainable growth -> positive gap
        gap = reverse_dcf_growth_gap(
            current_price=2.0,
            current_fcf=8.0,
            wacc=0.10,
            terminal_growth=0.025,
            shares_outstanding=100,
            sustainable_growth_rate=0.18,
        )
        assert gap.raw_value > 0, f"Expected positive growth gap, got {gap.raw_value}"

        # Step 3: Multiplicative score
        track_a_score = compute_track_a_score(
            moat_durability=moat.raw_value,
            compounding_power=0.15,
            capital_allocation=0.75,
            growth_gap=gap.raw_value,
        )
        assert track_a_score > 0

        # Step 4: Conviction assessment
        conviction = assess_track_a_conviction(
            gates_passed=4,
            total_gates=4,
            compounding_power=0.15,
            moat_durability=int(moat.raw_value),
            growth_gap=gap.raw_value,
        )
        assert conviction in (ConvictionLevel.HIGH, ConvictionLevel.EXCEPTIONAL)

        # Step 5: Timing
        timing = compute_v3_timing_signal(55.0, is_mispricing_track=False)
        assert timing == "buy_now"

        # Step 6: Orchestrate
        track_a = V3TrackResult(
            track="compounder",
            qualifies=True,
            conviction=conviction,
            score=track_a_score,
            gates_passed=4,
            total_gates=4,
        )
        track_b = V3TrackResult(
            track="mispricing",
            qualifies=False,
            conviction=ConvictionLevel.NONE,
            score=0.0,
            gates_passed=1,
            total_gates=4,
        )
        result = orchestrate_v3("COMP", track_a, track_b, timing)
        assert result.opportunity_type == "compounder"
        assert result.max_position_pct > 0

    def test_mispricing_pipeline(self):
        """Mispricing track produces valid result with convergent ensemble valuation."""
        # Step 1: Ensemble valuation with convergent methods
        ensemble = compute_ensemble_valuation(
            dcf_iv=120.0,
            owner_earnings_iv=115.0,
            asset_floor_iv=110.0,
            peer_comparison_iv=125.0,
        )
        assert ensemble.converged, "Expected 4-method convergence"
        assert ensemble.converging_count >= 3

        # Step 2: Asymmetry ratio (current price well below ensemble IV)
        # Need asymmetry > 3.0 for HIGH conviction
        current_price = 30.0
        asymmetry_ratio = ensemble.ensemble_iv / current_price
        assert asymmetry_ratio > 3.0, f"Expected asymmetry > 3.0, got {asymmetry_ratio}"

        # Step 3: Track B multiplicative score
        track_b_score = compute_track_b_score(
            asymmetry_ratio=asymmetry_ratio,
            catalyst_strength=85.0,
            quality_floor_factor=0.8,
            valuation_convergence=float(ensemble.converging_count),
        )
        assert track_b_score > 0

        # Step 4: Track B conviction
        conviction = assess_track_b_conviction(
            gates_passed=4,
            total_gates=4,
            asymmetry_ratio=asymmetry_ratio,
            catalyst_percentile=85.0,
            converging_methods=ensemble.converging_count,
        )
        assert conviction in (ConvictionLevel.HIGH, ConvictionLevel.EXCEPTIONAL)

        # Step 5: Timing (mispricing track -- contrarian, low momentum = buy_now)
        timing = compute_v3_timing_signal(25.0, is_mispricing_track=True)
        assert timing == "buy_now"

        # Step 6: Orchestrate
        track_a = V3TrackResult(
            track="compounder",
            qualifies=False,
            conviction=ConvictionLevel.NONE,
            score=0.0,
            gates_passed=1,
            total_gates=4,
        )
        track_b = V3TrackResult(
            track="mispricing",
            qualifies=True,
            conviction=conviction,
            score=track_b_score,
            gates_passed=4,
            total_gates=4,
        )
        result = orchestrate_v3("MISPR", track_a, track_b, timing)
        assert result.opportunity_type == "mispricing"
        assert result.max_position_pct > 0
        assert result.conviction in (ConvictionLevel.HIGH, ConvictionLevel.EXCEPTIONAL)

    def test_both_tracks_qualify_promotes_to_exceptional(self):
        """Stock qualifying on both tracks at HIGH+ gets promoted to EXCEPTIONAL."""
        track_a = V3TrackResult(
            track="compounder",
            qualifies=True,
            conviction=ConvictionLevel.HIGH,
            score=0.5,
            gates_passed=4,
            total_gates=4,
        )
        track_b = V3TrackResult(
            track="mispricing",
            qualifies=True,
            conviction=ConvictionLevel.HIGH,
            score=0.4,
            gates_passed=4,
            total_gates=4,
        )
        result = orchestrate_v3("DUAL", track_a, track_b, "buy_now")
        assert result.opportunity_type == "both"
        assert result.conviction == ConvictionLevel.EXCEPTIONAL
        assert result.max_position_pct == 20.0

    def test_neither_track_qualifies(self):
        """Mediocre company fails both tracks -> zero output."""
        track_a = V3TrackResult(
            track="compounder",
            qualifies=False,
            conviction=ConvictionLevel.NONE,
            score=0.0,
            gates_passed=1,
            total_gates=4,
        )
        track_b = V3TrackResult(
            track="mispricing",
            qualifies=False,
            conviction=ConvictionLevel.NONE,
            score=0.0,
            gates_passed=1,
            total_gates=4,
        )
        result = orchestrate_v3("MEDI", track_a, track_b, "buy_now")
        assert result.opportunity_type == "neither"
        assert result.max_position_pct == 0.0
        assert result.conviction == ConvictionLevel.NONE

    def test_timing_signal_variety(self):
        """Different momentum values produce different timing signals per track."""
        # Track A: high momentum -> buy_now
        assert compute_v3_timing_signal(75.0, is_mispricing_track=False) == "buy_now"
        # Track A: moderate momentum -> add_on_pullback
        assert compute_v3_timing_signal(40.0, is_mispricing_track=False) == "add_on_pullback"
        # Track A: low momentum -> accumulate_slowly
        assert compute_v3_timing_signal(15.0, is_mispricing_track=False) == "accumulate_slowly"
        # Track B: low momentum -> buy_now (contrarian)
        assert compute_v3_timing_signal(25.0, is_mispricing_track=True) == "buy_now"
        # Track B: high momentum -> wait_for_catalyst
        assert compute_v3_timing_signal(75.0, is_mispricing_track=True) == "wait_for_catalyst"

    def test_position_sizing_through_orchestrator(self):
        """Position sizes vary correctly by track and conviction level."""
        # Compounder at EXCEPTIONAL -> 15%
        track_a = V3TrackResult(
            track="compounder",
            qualifies=True,
            conviction=ConvictionLevel.EXCEPTIONAL,
            score=1.0,
            gates_passed=4,
            total_gates=4,
        )
        track_b_fail = V3TrackResult(
            track="mispricing",
            qualifies=False,
            conviction=ConvictionLevel.NONE,
            score=0.0,
            gates_passed=0,
            total_gates=4,
        )
        result = orchestrate_v3("BIG", track_a, track_b_fail, "buy_now")
        assert result.max_position_pct == 15.0

        # Mispricing at HIGH -> 6%
        track_a_fail = V3TrackResult(
            track="compounder",
            qualifies=False,
            conviction=ConvictionLevel.NONE,
            score=0.0,
            gates_passed=0,
            total_gates=4,
        )
        track_b = V3TrackResult(
            track="mispricing",
            qualifies=True,
            conviction=ConvictionLevel.HIGH,
            score=0.5,
            gates_passed=4,
            total_gates=4,
        )
        result = orchestrate_v3("MED", track_a_fail, track_b, "buy_now")
        assert result.max_position_pct == 6.0
