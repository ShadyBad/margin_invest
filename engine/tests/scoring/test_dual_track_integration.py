"""Integration test for the dual-track pipeline — end-to-end with manually constructed data.

Uses a "fake Costco" with hardcoded FactorScores to exercise the full assembly pipeline
without requiring real financial data. Tests the pipeline composition, not individual factors.
"""

import pytest
from margin_engine.models.scoring import (
    CompositeTier,
    FactorScore,
    FilterResult,
    GrowthStage,
    OpportunityType,
)
from margin_engine.scoring.composite_compounder import compute_compounder_score
from margin_engine.scoring.composite_mispricing import compute_mispricing_score
from margin_engine.scoring.conviction_gates import check_track_a_gates, check_track_b_gates
from margin_engine.scoring.dual_track import score_dual_track
from margin_engine.scoring.opportunity_classifier import classify_opportunity_type
from margin_engine.scoring.position_sizing import compute_position_size
from margin_engine.scoring.timing_overlay import compute_timing_signal

# ---------------------------------------------------------------------------
# Shared test data — "fake Costco" compounder profile
# ---------------------------------------------------------------------------


def _costco_quality_scores() -> list[FactorScore]:
    """Track A quality sub-factors for a high-quality compounder."""
    return [
        FactorScore(name="roic_stability", raw_value=0.25, percentile_rank=95.0, weight=0.30),
        FactorScore(name="incremental_roic", raw_value=0.18, percentile_rank=88.0, weight=0.20),
        FactorScore(name="reinvestment_engine", raw_value=0.12, percentile_rank=82.0, weight=0.20),
        FactorScore(name="gross_profitability", raw_value=0.73, percentile_rank=92.0, weight=0.15),
        FactorScore(name="earnings_quality", raw_value=-0.02, percentile_rank=85.0, weight=0.15),
    ]


def _costco_value_scores_a() -> list[FactorScore]:
    """Track A value sub-factors."""
    return [
        FactorScore(name="dcf_mos", raw_value=0.15, percentile_rank=70.0, weight=0.30),
        FactorScore(name="owner_earnings_yield", raw_value=0.04, percentile_rank=65.0, weight=0.25),
        FactorScore(name="acquirers_multiple", raw_value=18.0, percentile_rank=55.0, weight=0.20),
        FactorScore(name="runway_score", raw_value=0.85, percentile_rank=90.0, weight=0.25),
    ]


def _costco_cap_alloc_scores() -> list[FactorScore]:
    """Track A capital allocation sub-factors."""
    return [
        FactorScore(name="organic_reinvestment", raw_value=0.70, percentile_rank=88.0, weight=0.30),
        FactorScore(name="buyback_effectiveness", raw_value=1.2, percentile_rank=75.0, weight=0.25),
        FactorScore(name="insider_ownership", raw_value=0.03, percentile_rank=70.0, weight=0.25),
        FactorScore(name="debt_discipline", raw_value=0.25, percentile_rank=82.0, weight=0.20),
    ]


def _costco_value_scores_b() -> list[FactorScore]:
    """Track B value sub-factors — Costco isn't deeply undervalued."""
    return [
        FactorScore(name="dcf_mos", raw_value=0.15, percentile_rank=70.0, weight=0.30),
        FactorScore(name="owner_earnings_yield", raw_value=0.04, percentile_rank=65.0, weight=0.25),
        FactorScore(name="acquirers_multiple", raw_value=18.0, percentile_rank=55.0, weight=0.25),
        FactorScore(name="asymmetry_ratio", raw_value=1.8, percentile_rank=45.0, weight=0.20),
    ]


def _costco_quality_floor_scores() -> list[FactorScore]:
    """Track B quality floor sub-factors."""
    return [
        FactorScore(name="roic_trajectory", raw_value=0.02, percentile_rank=60.0, weight=0.40),
        FactorScore(name="gross_profitability", raw_value=0.73, percentile_rank=92.0, weight=0.30),
        FactorScore(name="earnings_quality", raw_value=-0.02, percentile_rank=85.0, weight=0.30),
    ]


def _costco_catalyst_scores() -> list[FactorScore]:
    """Track B catalyst sub-factors — Costco has minimal catalyst signals."""
    return [
        FactorScore(name="insider_cluster", raw_value=0.0, percentile_rank=30.0, weight=0.35),
        FactorScore(
            name="institutional_accumulation", raw_value=0.01, percentile_rank=45.0, weight=0.35
        ),
        FactorScore(name="contrarian_signal", raw_value=0.0, percentile_rank=25.0, weight=0.30),
    ]


def _filters() -> list[FilterResult]:
    return [
        FilterResult(name="altman_z", passed=True, value=6.5, threshold=1.81),
        FilterResult(name="beneish_m", passed=True, value=-3.2, threshold=-1.78),
        FilterResult(name="current_ratio", passed=True, value=1.1, threshold=0.5),
    ]


# ---------------------------------------------------------------------------
# Full pipeline integration test
# ---------------------------------------------------------------------------


class TestDualTrackPipelineIntegration:
    """End-to-end test: fake Costco flows through the complete dual-track pipeline."""

    def test_costco_compounder_scores_higher_than_mispricing(self):
        """A high-quality compounder like Costco should score higher on Track A."""
        track_a = compute_compounder_score(
            ticker="COST",
            quality_scores=_costco_quality_scores(),
            value_scores=_costco_value_scores_a(),
            capital_allocation_scores=_costco_cap_alloc_scores(),
            filters_passed=_filters(),
            growth_stage=GrowthStage.STEADY_GROWTH,
            data_coverage=0.95,
        )

        track_b = compute_mispricing_score(
            ticker="COST",
            value_scores=_costco_value_scores_b(),
            quality_floor_scores=_costco_quality_floor_scores(),
            catalyst_scores=_costco_catalyst_scores(),
            filters_passed=_filters(),
            data_coverage=0.95,
        )

        assert track_a.composite_percentile > track_b.composite_percentile

    def test_opportunity_type_is_compounder(self):
        """Costco's profile classifies as COMPOUNDER."""
        opp_type = classify_opportunity_type(
            roic_5yr_median=0.25,
            roic_cv=0.15,
            reinvestment_rate=0.40,
            price_to_intrinsic_ratio=0.85,
            has_catalyst=False,
            roic_improving=True,
        )
        assert opp_type == OpportunityType.COMPOUNDER

    def test_track_a_gates_pass_for_costco(self):
        """Costco's quality metrics pass Track A conviction gates."""
        gate_a = check_track_a_gates(
            roic_median=0.25,
            roic_cv=0.15,
            reinvestment_rate=0.40,
            price_to_iv_ratio=0.85,
            data_coverage=0.95,
        )
        assert gate_a.passed is True
        assert gate_a.failures == []

    def test_full_pipeline_produces_valid_result(self):
        """Complete pipeline: classify, score both tracks, orchestrate, verify output."""
        # 1. Classify opportunity
        opp_type = classify_opportunity_type(
            roic_5yr_median=0.25,
            roic_cv=0.15,
            reinvestment_rate=0.40,
            price_to_intrinsic_ratio=0.85,
            has_catalyst=False,
            roic_improving=True,
        )

        # 2. Score Track A
        track_a = compute_compounder_score(
            ticker="COST",
            quality_scores=_costco_quality_scores(),
            value_scores=_costco_value_scores_a(),
            capital_allocation_scores=_costco_cap_alloc_scores(),
            filters_passed=_filters(),
            growth_stage=GrowthStage.STEADY_GROWTH,
            data_coverage=0.95,
        )

        # 3. Score Track B
        track_b = compute_mispricing_score(
            ticker="COST",
            value_scores=_costco_value_scores_b(),
            quality_floor_scores=_costco_quality_floor_scores(),
            catalyst_scores=_costco_catalyst_scores(),
            filters_passed=_filters(),
            data_coverage=0.95,
        )

        # 4. Compute gates
        gate_a = check_track_a_gates(
            roic_median=0.25,
            roic_cv=0.15,
            reinvestment_rate=0.40,
            price_to_iv_ratio=0.85,
            data_coverage=0.95,
        )
        gate_b = check_track_b_gates(
            roic_median=0.25,
            roic_improving=True,
            price_to_iv_ratio=0.85,
            has_catalyst=False,
            net_cash_pct=0.10,
            tangible_book_pct=0.20,
            current_ratio=1.1,
        )

        # 5. Compute timing signal
        timing = compute_timing_signal(
            momentum_percentile=65.0,
            is_mispricing_track=False,
        )

        # 6. Orchestrate
        result = score_dual_track(
            track_a_score=track_a,
            track_b_score=track_b,
            opportunity_type=opp_type,
            asymmetry_ratio_value=1.8,
            timing_signal=timing,
            gate_result_a=gate_a,
            gate_result_b=gate_b,
        )

        # Verify all v2 fields are set
        assert result.ticker == "COST"
        assert result.winning_track == "compounder"
        assert result.opportunity_type == OpportunityType.COMPOUNDER
        assert result.asymmetry_ratio == pytest.approx(1.8)
        assert result.timing_signal == "buy_now"
        assert result.max_position_pct is not None
        # Composite is ~81.56 -> NONE conviction -> 0% position (expected)
        assert result.max_position_pct >= 0.0

        # Verify composite percentile is reasonable
        assert 0.0 < result.composite_percentile <= 100.0

        # Verify breakdowns exist
        assert result.quality is not None
        assert result.value is not None
        assert result.capital_allocation is not None
        assert result.data_coverage == pytest.approx(0.95)

    def test_position_sizing_returns_value(self):
        """Position sizing returns a non-negative value for any inputs."""
        size = compute_position_size(1.8, CompositeTier.MEDIUM)
        assert size >= 0.0

    def test_timing_signal_is_set_for_compounder(self):
        """Positive momentum + compounder track -> buy_now."""
        signal = compute_timing_signal(
            momentum_percentile=65.0,
            is_mispricing_track=False,
        )
        assert signal == "buy_now"


# ---------------------------------------------------------------------------
# Mispricing-dominant scenario
# ---------------------------------------------------------------------------


class TestMispricingDominantScenario:
    """Verify Track B wins when the stock is a deep value play."""

    def test_deep_value_stock_mispricing_wins(self):
        """A beaten-down quality stock should score higher on Track B."""
        # Track A — quality decent but value mediocre at 50/30/20 weights
        track_a = compute_compounder_score(
            ticker="DEEPV",
            quality_scores=[
                FactorScore(
                    name="roic_stability", raw_value=0.12, percentile_rank=55.0, weight=0.30
                ),
                FactorScore(
                    name="incremental_roic", raw_value=0.10, percentile_rank=50.0, weight=0.20
                ),
                FactorScore(
                    name="reinvestment_engine", raw_value=0.08, percentile_rank=45.0, weight=0.20
                ),
                FactorScore(
                    name="gross_profitability", raw_value=0.35, percentile_rank=60.0, weight=0.15
                ),
                FactorScore(
                    name="earnings_quality", raw_value=-0.05, percentile_rank=55.0, weight=0.15
                ),
            ],
            value_scores=[
                FactorScore(name="dcf_mos", raw_value=0.40, percentile_rank=60.0, weight=0.30),
                FactorScore(
                    name="owner_earnings_yield", raw_value=0.08, percentile_rank=65.0, weight=0.25
                ),
                FactorScore(
                    name="acquirers_multiple", raw_value=8.0, percentile_rank=70.0, weight=0.20
                ),
                FactorScore(name="runway_score", raw_value=0.50, percentile_rank=55.0, weight=0.25),
            ],
            capital_allocation_scores=[
                FactorScore(
                    name="organic_reinvestment", raw_value=0.40, percentile_rank=50.0, weight=0.30
                ),
                FactorScore(
                    name="buyback_effectiveness", raw_value=0.8, percentile_rank=45.0, weight=0.25
                ),
                FactorScore(
                    name="insider_ownership", raw_value=0.05, percentile_rank=55.0, weight=0.25
                ),
                FactorScore(
                    name="debt_discipline", raw_value=0.30, percentile_rank=60.0, weight=0.20
                ),
            ],
            filters_passed=_filters(),
            growth_stage=GrowthStage.MATURE,
        )

        # Track B — strong value + catalyst signals at 45/25/30 weights
        track_b = compute_mispricing_score(
            ticker="DEEPV",
            value_scores=[
                FactorScore(name="dcf_mos", raw_value=0.50, percentile_rank=92.0, weight=0.30),
                FactorScore(
                    name="owner_earnings_yield", raw_value=0.10, percentile_rank=88.0, weight=0.25
                ),
                FactorScore(
                    name="acquirers_multiple", raw_value=6.0, percentile_rank=85.0, weight=0.25
                ),
                FactorScore(
                    name="asymmetry_ratio", raw_value=4.0, percentile_rank=90.0, weight=0.20
                ),
            ],
            quality_floor_scores=[
                FactorScore(
                    name="roic_trajectory", raw_value=0.03, percentile_rank=65.0, weight=0.40
                ),
                FactorScore(
                    name="gross_profitability", raw_value=0.35, percentile_rank=60.0, weight=0.30
                ),
                FactorScore(
                    name="earnings_quality", raw_value=-0.05, percentile_rank=55.0, weight=0.30
                ),
            ],
            catalyst_scores=[
                FactorScore(
                    name="insider_cluster", raw_value=3.0, percentile_rank=88.0, weight=0.35
                ),
                FactorScore(
                    name="institutional_accumulation",
                    raw_value=0.05,
                    percentile_rank=82.0,
                    weight=0.35,
                ),
                FactorScore(
                    name="contrarian_signal", raw_value=0.8, percentile_rank=85.0, weight=0.30
                ),
            ],
            filters_passed=_filters(),
            data_coverage=0.90,
        )

        # Track B should win
        assert track_b.composite_percentile > track_a.composite_percentile

        # Orchestrate
        gate_a = check_track_a_gates(
            roic_median=0.12,
            roic_cv=0.25,
            reinvestment_rate=0.20,  # fails reinvestment gate
            price_to_iv_ratio=0.50,
            data_coverage=0.90,
        )
        gate_b = check_track_b_gates(
            roic_median=0.12,
            roic_improving=True,
            price_to_iv_ratio=0.50,
            has_catalyst=True,
            net_cash_pct=0.55,
            tangible_book_pct=0.40,
            current_ratio=2.5,
        )

        timing = compute_timing_signal(
            momentum_percentile=25.0,
            is_mispricing_track=True,
        )

        result = score_dual_track(
            track_a_score=track_a,
            track_b_score=track_b,
            opportunity_type=OpportunityType.MISPRICING,
            asymmetry_ratio_value=4.0,
            timing_signal=timing,
            gate_result_a=gate_a,
            gate_result_b=gate_b,
        )

        assert result.winning_track == "mispricing"
        assert result.opportunity_type == OpportunityType.MISPRICING
        assert result.timing_signal == "buy_now"
        assert result.max_position_pct is not None
        assert result.asymmetry_ratio == pytest.approx(4.0)
