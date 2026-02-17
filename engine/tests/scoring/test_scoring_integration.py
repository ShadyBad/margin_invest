"""Integration tests for the full Phase 6 scoring pipeline.

Verifies that normalizer, classifier, and composite scorer work together
end-to-end with synthetic data.
"""

from decimal import Decimal

import pytest
from margin_engine.models.financial import (
    AssetProfile,
    BalanceSheet,
    CashFlowStatement,
    FinancialPeriod,
    GICSSector,
    IncomeStatement,
)
from margin_engine.models.scoring import (
    ConvictionLevel,
    FactorScore,
    FilterResult,
    GrowthStage,
)
from margin_engine.scoring import (
    classify_growth_stage,
    compute_composite_score,
    compute_percentile_ranks,
    sector_neutral_ranks,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_factor_score(
    name: str = "test_factor",
    raw_value: float = 1.0,
    percentile_rank: float = 0.0,
) -> FactorScore:
    return FactorScore(
        name=name, raw_value=raw_value, percentile_rank=percentile_rank
    )


def _make_filter(name: str = "altman_z", passed: bool = True) -> FilterResult:
    return FilterResult(name=name, passed=passed, value=3.0, threshold=1.81)


def _make_period(
    revenue: Decimal = Decimal("10000"),
    cost_of_revenue: Decimal = Decimal("5000"),
    gross_profit: Decimal | None = None,
    operating_cash_flow: Decimal = Decimal("1000"),
    capital_expenditures: Decimal = Decimal("-200"),
    net_income: Decimal = Decimal("500"),
) -> FinancialPeriod:
    gp = gross_profit if gross_profit is not None else (revenue - cost_of_revenue)
    return FinancialPeriod(
        period_end="2024-09-28",
        filing_date="2024-11-01",
        current_income=IncomeStatement(
            revenue=revenue,
            cost_of_revenue=cost_of_revenue,
            gross_profit=gp,
            net_income=net_income,
        ),
        current_balance=BalanceSheet(total_assets=Decimal("50000")),
        current_cash_flow=CashFlowStatement(
            operating_cash_flow=operating_cash_flow,
            capital_expenditures=capital_expenditures,
        ),
    )


def _make_profile(
    ticker: str = "TEST",
    sector: GICSSector = GICSSector.TECHNOLOGY,
    market_cap: Decimal = Decimal("10000000000"),
) -> AssetProfile:
    return AssetProfile(
        ticker=ticker,
        name=f"{ticker} Corp",
        sector=sector,
        market_cap=market_cap,
    )


# ---------------------------------------------------------------------------
# test_full_scoring_pipeline
# ---------------------------------------------------------------------------


class TestFullScoringPipeline:
    """End-to-end: rank raw scores, classify, composite, verify ordering."""

    def test_full_scoring_pipeline(self):
        """Create 5 synthetic stocks, rank, classify, composite.

        The stock with the highest raw scores across all factors should
        end up with the highest composite percentile.
        """
        # 5 stocks with varying quality raw scores (higher = better)
        quality_raw = [
            _make_factor_score("gross_prof", raw_value=0.20),
            _make_factor_score("gross_prof", raw_value=0.35),
            _make_factor_score("gross_prof", raw_value=0.50),
            _make_factor_score("gross_prof", raw_value=0.65),
            _make_factor_score("gross_prof", raw_value=0.80),
        ]
        value_raw = [
            _make_factor_score("ev_fcf", raw_value=5.0),
            _make_factor_score("ev_fcf", raw_value=10.0),
            _make_factor_score("ev_fcf", raw_value=15.0),
            _make_factor_score("ev_fcf", raw_value=20.0),
            _make_factor_score("ev_fcf", raw_value=25.0),
        ]
        momentum_raw = [
            _make_factor_score("price_mom", raw_value=0.02),
            _make_factor_score("price_mom", raw_value=0.08),
            _make_factor_score("price_mom", raw_value=0.14),
            _make_factor_score("price_mom", raw_value=0.20),
            _make_factor_score("price_mom", raw_value=0.30),
        ]

        # Step 1: percentile rank each factor across the universe
        quality_ranked = compute_percentile_ranks(quality_raw)
        value_ranked = compute_percentile_ranks(value_raw)
        momentum_ranked = compute_percentile_ranks(momentum_raw)

        # Step 2: classify one stock (the best one) as Steady Growth
        period = _make_period(
            operating_cash_flow=Decimal("500"),
            capital_expenditures=Decimal("-100"),
        )
        profile = _make_profile(ticker="BEST")
        stage = classify_growth_stage(
            period=period, profile=profile, revenue_cagr_3yr=0.10
        )
        assert stage == GrowthStage.STEADY_GROWTH

        # Step 3: composite score for the best stock (index 4)
        best_composite = compute_composite_score(
            ticker="BEST",
            quality_scores=[quality_ranked[4]],
            value_scores=[value_ranked[4]],
            momentum_scores=[momentum_ranked[4]],
            filters_passed=[_make_filter()],
            growth_stage=stage,
        )

        # Step 4: composite score for the worst stock (index 0)
        worst_composite = compute_composite_score(
            ticker="WORST",
            quality_scores=[quality_ranked[0]],
            value_scores=[value_ranked[0]],
            momentum_scores=[momentum_ranked[0]],
            filters_passed=[_make_filter()],
            growth_stage=stage,
        )

        # The best stock should have the highest composite percentile
        assert best_composite.composite_percentile > worst_composite.composite_percentile
        assert best_composite.composite_percentile == pytest.approx(100.0)
        assert worst_composite.composite_percentile == pytest.approx(20.0)


# ---------------------------------------------------------------------------
# test_sector_neutral_pipeline
# ---------------------------------------------------------------------------


class TestSectorNeutralPipeline:
    """Sector-neutral ranking: each sector's top stock gets 100.0."""

    def test_sector_neutral_pipeline(self):
        """Two sectors with 3 stocks each; top in each sector gets 100.0."""
        tech_scores = [
            _make_factor_score("roic", raw_value=0.10),
            _make_factor_score("roic", raw_value=0.30),
            _make_factor_score("roic", raw_value=0.50),
        ]
        healthcare_scores = [
            _make_factor_score("roic", raw_value=0.05),
            _make_factor_score("roic", raw_value=0.15),
            _make_factor_score("roic", raw_value=0.25),
        ]

        result = sector_neutral_ranks(
            {
                "Information Technology": tech_scores,
                "Health Care": healthcare_scores,
            }
        )

        assert len(result) == 6

        # Tech top stock (raw_value=0.50) should get 100.0
        tech_top = [s for s in result if s.raw_value == 0.50]
        assert len(tech_top) == 1
        assert tech_top[0].percentile_rank == pytest.approx(100.0)

        # Healthcare top stock (raw_value=0.25) should get 100.0
        hc_top = [s for s in result if s.raw_value == 0.25]
        assert len(hc_top) == 1
        assert hc_top[0].percentile_rank == pytest.approx(100.0)


# ---------------------------------------------------------------------------
# test_growth_stage_affects_weights
# ---------------------------------------------------------------------------


class TestGrowthStageAffectsWeights:
    """Same sub-scores, different growth stages produce different composites."""

    def test_growth_stage_affects_weights(self):
        """High Growth vs Mature: same percentiles but different composites.

        Using asymmetric percentiles so that the different weight distributions
        produce distinct composite values.
        """
        quality = [_make_factor_score("gp", percentile_rank=90.0)]
        value = [_make_factor_score("ev_fcf", percentile_rank=50.0)]
        momentum = [_make_factor_score("price_mom", percentile_rank=70.0)]

        high_growth = compute_composite_score(
            ticker="HG",
            quality_scores=quality,
            value_scores=value,
            momentum_scores=momentum,
            filters_passed=[],
            growth_stage=GrowthStage.HIGH_GROWTH,
        )

        mature = compute_composite_score(
            ticker="MAT",
            quality_scores=quality,
            value_scores=value,
            momentum_scores=momentum,
            filters_passed=[],
            growth_stage=GrowthStage.MATURE,
        )

        # High Growth: Q=0.40, V=0.25, M=0.35
        # 90*0.40 + 50*0.25 + 70*0.35 = 36 + 12.5 + 24.5 = 73.0
        assert high_growth.composite_percentile == pytest.approx(73.0)

        # Mature: Q=0.30, V=0.40, M=0.30
        # 90*0.30 + 50*0.40 + 70*0.30 = 27 + 20 + 21 = 68.0
        assert mature.composite_percentile == pytest.approx(68.0)

        # They must differ
        assert high_growth.composite_percentile != pytest.approx(
            mature.composite_percentile
        )


# ---------------------------------------------------------------------------
# test_conviction_levels_from_pipeline
# ---------------------------------------------------------------------------


class TestConvictionLevelsFromPipeline:
    """Synthetic stocks hitting conviction thresholds from the pipeline."""

    def test_exceptional_conviction(self):
        """Stock with all sub-scores at 99.97th percentile -> EXCEPTIONAL."""
        quality = [_make_factor_score("gp", percentile_rank=99.97)]
        value = [_make_factor_score("ev_fcf", percentile_rank=99.97)]
        momentum = [_make_factor_score("price_mom", percentile_rank=99.97)]

        result = compute_composite_score(
            ticker="TOP1",
            quality_scores=quality,
            value_scores=value,
            momentum_scores=momentum,
            filters_passed=[_make_filter()],
        )

        assert result.composite_percentile >= 99.95
        assert result.conviction_level == ConvictionLevel.EXCEPTIONAL

    def test_high_conviction(self):
        """Stock with all sub-scores at 99.4th percentile -> HIGH."""
        quality = [_make_factor_score("gp", percentile_rank=99.4)]
        value = [_make_factor_score("ev_fcf", percentile_rank=99.4)]
        momentum = [_make_factor_score("price_mom", percentile_rank=99.4)]

        result = compute_composite_score(
            ticker="TOP5",
            quality_scores=quality,
            value_scores=value,
            momentum_scores=momentum,
            filters_passed=[_make_filter()],
        )

        assert result.composite_percentile >= 99.3
        assert result.composite_percentile < 99.95
        assert result.conviction_level == ConvictionLevel.HIGH


# ---------------------------------------------------------------------------
# test_imports_from_package
# ---------------------------------------------------------------------------


class TestImportsFromPackage:
    """All 4 public functions are importable from margin_engine.scoring."""

    def test_imports_from_package(self):
        from margin_engine.scoring import classify_growth_stage as cgs
        from margin_engine.scoring import compute_composite_score as ccs
        from margin_engine.scoring import compute_percentile_ranks as cpr
        from margin_engine.scoring import sector_neutral_ranks as snr

        assert callable(cgs)
        assert callable(ccs)
        assert callable(cpr)
        assert callable(snr)

    def test_all_exports_present(self):
        import margin_engine.scoring as scoring_pkg

        assert hasattr(scoring_pkg, "__all__")
        assert set(scoring_pkg.__all__) == {
            # v1 exports
            "classify_growth_stage",
            "compute_composite_score",
            "compute_percentile_ranks",
            "rerank_composites",
            "sector_neutral_ranks",
            # v2 dual-track exports
            "classify_opportunity_type",
            "compute_compounder_score",
            "compute_mispricing_score",
            "score_dual_track",
            "compute_timing_signal",
            "compute_position_size",
            "check_track_a_gates",
            "check_track_b_gates",
            "mediocrity_gate",
            # v3 exports
            "MarketRegime",
            "MAX_POSITIONS",
            "V3Result",
            "V3TrackResult",
            "assess_track_a_conviction",
            "assess_track_b_conviction",
            "compute_track_a_score",
            "compute_track_b_score",
            "compute_v3_position_size",
            "compute_v3_timing_signal",
            "detect_regime",
            "orchestrate_v3",
            "regime_adjustments",
            # v3 cascade exports
            "TrackAInputs",
            "TrackBInputs",
            "TickerV3Data",
            "compute_capital_allocation_composite",
            "compute_catalyst_strength",
            "compute_compounding_power",
            "compute_downside_protection",
            "compute_owner_earnings_iv",
            "compute_quality_floor_factor",
            "compute_valuation_convergence_factor",
            "run_track_a_cascade",
            "run_track_b_cascade",
            "score_universe_v3",
        }
