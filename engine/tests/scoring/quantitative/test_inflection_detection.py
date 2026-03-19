"""Tests for inflection detection module — OpEx deleverage, FCF crossover, margin expansion."""

from decimal import Decimal

import pytest
from margin_engine.models.financial import (
    BalanceSheet,
    CashFlowStatement,
    FinancialHistory,
    FinancialPeriod,
    IncomeStatement,
)
from margin_engine.scoring.quantitative.inflection_detection import (
    fcf_crossover_score,
    inflection_score,
    margin_expansion_score,
    opex_deleverage_score,
)


def _make_period(
    revenue: Decimal,
    cost_of_revenue: Decimal,
    sga: Decimal | None = None,
    depreciation: Decimal | None = None,
    net_income: Decimal | None = None,
    gross_profit: Decimal | None = None,
    period_end: str = "2024-12-31",
) -> FinancialPeriod:
    """Build a minimal FinancialPeriod for inflection detection tests."""
    gp = gross_profit if gross_profit is not None else (revenue - cost_of_revenue)
    ni = net_income if net_income is not None else Decimal("0")
    income = IncomeStatement(
        revenue=revenue,
        cost_of_revenue=cost_of_revenue,
        gross_profit=gp,
        sga_expense=sga,
        depreciation=depreciation,
        net_income=ni,
        ebit=ni,
    )
    balance = BalanceSheet(
        total_assets=Decimal("1000"),
        total_equity=Decimal("500"),
    )
    cf = CashFlowStatement(
        operating_cash_flow=Decimal("0"),
        capital_expenditures=Decimal("0"),
    )
    return FinancialPeriod(
        period_end=period_end,
        filing_date="2025-01-15",
        current_income=income,
        current_balance=balance,
        current_cash_flow=cf,
    )


# ---------------------------------------------------------------------------
# Task 1: OpEx Deleverage Signal
# ---------------------------------------------------------------------------


class TestOpExDeleverage:
    def test_declining_ratio_scores_positive(self):
        """Three consecutive declining OpEx/Revenue ratios should score > 0."""
        # Period 1: opex/rev = 0.60
        # Period 2: opex/rev = 0.58 (delta = -0.02)
        # Period 3: opex/rev = 0.55 (delta = -0.03)
        # total_magnitude = 0.05; score = min(0.05/0.01, 4.0) = 4.0
        periods = [
            _make_period(
                revenue=Decimal("1000"),
                cost_of_revenue=Decimal("500"),
                sga=Decimal("100"),
                period_end="2022-12-31",
            ),
            _make_period(
                revenue=Decimal("1000"),
                cost_of_revenue=Decimal("480"),
                sga=Decimal("100"),
                period_end="2023-12-31",
            ),
            _make_period(
                revenue=Decimal("1000"),
                cost_of_revenue=Decimal("450"),
                sga=Decimal("100"),
                period_end="2024-12-31",
            ),
        ]
        history = FinancialHistory(ticker="TEST", periods=periods)
        score = opex_deleverage_score(history)
        assert score > 0.0

    def test_flat_ratio_scores_zero(self):
        """Flat OpEx/Revenue ratios should score zero (no consecutive declines)."""
        periods = [
            _make_period(
                revenue=Decimal("1000"),
                cost_of_revenue=Decimal("600"),
                period_end="2022-12-31",
            ),
            _make_period(
                revenue=Decimal("1100"),
                cost_of_revenue=Decimal("660"),
                period_end="2023-12-31",
            ),
            _make_period(
                revenue=Decimal("1200"),
                cost_of_revenue=Decimal("720"),
                period_end="2024-12-31",
            ),
        ]
        history = FinancialHistory(ticker="TEST", periods=periods)
        score = opex_deleverage_score(history)
        assert score == 0.0

    def test_single_period_scores_zero(self):
        """Single period cannot have consecutive declines — must return 0."""
        periods = [
            _make_period(
                revenue=Decimal("1000"),
                cost_of_revenue=Decimal("600"),
                period_end="2024-12-31",
            )
        ]
        history = FinancialHistory(ticker="TEST", periods=periods)
        score = opex_deleverage_score(history)
        assert score == 0.0

    def test_capped_at_four(self):
        """Very large consecutive declines should be capped at 4.0."""
        # 3 periods: ratio 0.90 -> 0.70 -> 0.40
        # delta1 = 0.20, delta2 = 0.30 -> total_magnitude = 0.50
        # score = min(0.50/0.01, 4.0) = min(50.0, 4.0) = 4.0
        periods = [
            _make_period(
                revenue=Decimal("1000"),
                cost_of_revenue=Decimal("900"),
                period_end="2022-12-31",
            ),
            _make_period(
                revenue=Decimal("1000"),
                cost_of_revenue=Decimal("700"),
                period_end="2023-12-31",
            ),
            _make_period(
                revenue=Decimal("1000"),
                cost_of_revenue=Decimal("400"),
                period_end="2024-12-31",
            ),
        ]
        history = FinancialHistory(ticker="TEST", periods=periods)
        score = opex_deleverage_score(history)
        assert score == pytest.approx(4.0)

    def test_one_decline_not_two_consecutive_scores_zero(self):
        """Only 1 decline period (need 2+) -> 0."""
        periods = [
            _make_period(
                revenue=Decimal("1000"),
                cost_of_revenue=Decimal("600"),
                period_end="2022-12-31",
            ),
            _make_period(
                revenue=Decimal("1000"),
                cost_of_revenue=Decimal("580"),
                period_end="2023-12-31",
            ),
        ]
        history = FinancialHistory(ticker="TEST", periods=periods)
        score = opex_deleverage_score(history)
        assert score == 0.0

    def test_sga_included_in_opex(self):
        """SGA is included in OpEx ratio computation when present."""
        # With SGA: ratio = (CoR + SGA) / rev
        # Period 1: (400 + 200) / 1000 = 0.60
        # Period 2: (380 + 180) / 1000 = 0.56 (delta = -0.04)
        # Period 3: (360 + 160) / 1000 = 0.52 (delta = -0.04)
        periods = [
            _make_period(
                revenue=Decimal("1000"),
                cost_of_revenue=Decimal("400"),
                sga=Decimal("200"),
                period_end="2022-12-31",
            ),
            _make_period(
                revenue=Decimal("1000"),
                cost_of_revenue=Decimal("380"),
                sga=Decimal("180"),
                period_end="2023-12-31",
            ),
            _make_period(
                revenue=Decimal("1000"),
                cost_of_revenue=Decimal("360"),
                sga=Decimal("160"),
                period_end="2024-12-31",
            ),
        ]
        history = FinancialHistory(ticker="TEST", periods=periods)
        score = opex_deleverage_score(history)
        assert score > 0.0
        # total_magnitude = 0.08, score = min(0.08/0.01, 4.0) = 4.0
        assert score == pytest.approx(4.0)


# ---------------------------------------------------------------------------
# Task 2: FCF Crossover Signal
# ---------------------------------------------------------------------------


class TestFCFCrossover:
    def test_crossover_scores_positive(self):
        """Last 2 periods FCF positive, 3 prior periods negative -> score = min(3, 3) = 3.0."""
        # FCF = net_income + depreciation
        # Negative: net_income=-100, depreciation=10 -> FCF = -90
        # Positive: net_income=50, depreciation=10 -> FCF = 60
        periods = [
            _make_period(
                revenue=Decimal("1000"),
                cost_of_revenue=Decimal("600"),
                net_income=Decimal("-100"),
                depreciation=Decimal("10"),
                period_end="2020-12-31",
            ),
            _make_period(
                revenue=Decimal("1000"),
                cost_of_revenue=Decimal("600"),
                net_income=Decimal("-80"),
                depreciation=Decimal("10"),
                period_end="2021-12-31",
            ),
            _make_period(
                revenue=Decimal("1000"),
                cost_of_revenue=Decimal("600"),
                net_income=Decimal("-50"),
                depreciation=Decimal("10"),
                period_end="2022-12-31",
            ),
            _make_period(
                revenue=Decimal("1000"),
                cost_of_revenue=Decimal("600"),
                net_income=Decimal("50"),
                depreciation=Decimal("10"),
                period_end="2023-12-31",
            ),
            _make_period(
                revenue=Decimal("1000"),
                cost_of_revenue=Decimal("600"),
                net_income=Decimal("80"),
                depreciation=Decimal("10"),
                period_end="2024-12-31",
            ),
        ]
        history = FinancialHistory(ticker="TEST", periods=periods)
        score = fcf_crossover_score(history)
        assert score == pytest.approx(3.0)

    def test_no_prior_negative_scores_zero(self):
        """All periods positive FCF -> no crossover -> 0."""
        periods = [
            _make_period(
                revenue=Decimal("1000"),
                cost_of_revenue=Decimal("600"),
                net_income=Decimal("100"),
                depreciation=Decimal("20"),
                period_end="2022-12-31",
            ),
            _make_period(
                revenue=Decimal("1000"),
                cost_of_revenue=Decimal("600"),
                net_income=Decimal("120"),
                depreciation=Decimal("20"),
                period_end="2023-12-31",
            ),
            _make_period(
                revenue=Decimal("1000"),
                cost_of_revenue=Decimal("600"),
                net_income=Decimal("150"),
                depreciation=Decimal("20"),
                period_end="2024-12-31",
            ),
        ]
        history = FinancialHistory(ticker="TEST", periods=periods)
        score = fcf_crossover_score(history)
        assert score == 0.0

    def test_last_period_still_negative_scores_zero(self):
        """Last period FCF is still negative -> no crossover detected."""
        periods = [
            _make_period(
                revenue=Decimal("1000"),
                cost_of_revenue=Decimal("600"),
                net_income=Decimal("-100"),
                depreciation=Decimal("10"),
                period_end="2023-12-31",
            ),
            _make_period(
                revenue=Decimal("1000"),
                cost_of_revenue=Decimal("600"),
                net_income=Decimal("-20"),
                depreciation=Decimal("10"),
                period_end="2024-12-31",
            ),
        ]
        history = FinancialHistory(ticker="TEST", periods=periods)
        score = fcf_crossover_score(history)
        assert score == 0.0

    def test_single_period_scores_zero(self):
        """Single period cannot establish a crossover."""
        periods = [
            _make_period(
                revenue=Decimal("1000"),
                cost_of_revenue=Decimal("600"),
                net_income=Decimal("50"),
                depreciation=Decimal("10"),
                period_end="2024-12-31",
            )
        ]
        history = FinancialHistory(ticker="TEST", periods=periods)
        score = fcf_crossover_score(history)
        assert score == 0.0

    def test_capped_at_three(self):
        """Prior negative streak of 10 should be capped at 3.0."""
        neg_periods = [
            _make_period(
                revenue=Decimal("1000"),
                cost_of_revenue=Decimal("600"),
                net_income=Decimal("-50"),
                depreciation=Decimal("5"),
                period_end=f"201{i}-12-31",
            )
            for i in range(8)
        ]
        pos_periods = [
            _make_period(
                revenue=Decimal("1000"),
                cost_of_revenue=Decimal("600"),
                net_income=Decimal("60"),
                depreciation=Decimal("5"),
                period_end="2023-12-31",
            ),
            _make_period(
                revenue=Decimal("1000"),
                cost_of_revenue=Decimal("600"),
                net_income=Decimal("80"),
                depreciation=Decimal("5"),
                period_end="2024-12-31",
            ),
        ]
        history = FinancialHistory(ticker="TEST", periods=neg_periods + pos_periods)
        score = fcf_crossover_score(history)
        assert score == pytest.approx(3.0)

    def test_one_prior_negative_scores_one(self):
        """1 prior negative period, 2 recent positive -> score = min(1, 3) = 1.0."""
        periods = [
            _make_period(
                revenue=Decimal("1000"),
                cost_of_revenue=Decimal("600"),
                net_income=Decimal("-30"),
                depreciation=Decimal("5"),
                period_end="2022-12-31",
            ),
            _make_period(
                revenue=Decimal("1000"),
                cost_of_revenue=Decimal("600"),
                net_income=Decimal("50"),
                depreciation=Decimal("5"),
                period_end="2023-12-31",
            ),
            _make_period(
                revenue=Decimal("1000"),
                cost_of_revenue=Decimal("600"),
                net_income=Decimal("70"),
                depreciation=Decimal("5"),
                period_end="2024-12-31",
            ),
        ]
        history = FinancialHistory(ticker="TEST", periods=periods)
        score = fcf_crossover_score(history)
        assert score == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Task 3: Margin Expansion Signal
# ---------------------------------------------------------------------------


class TestMarginExpansion:
    def test_expanding_margins_near_ath_score_positive(self):
        """2+ consecutive expansions near ATH (within 200bps) should score > 0."""
        # gross_margin = gross_profit / revenue
        # P1: 400/1000 = 0.40, P2: 430/1000 = 0.43, P3: 450/1000 = 0.45
        # Consecutive expansions: 2. ATH = 0.45, latest = 0.45 (within 200bps -> 0 bps away)
        periods = [
            _make_period(
                revenue=Decimal("1000"),
                cost_of_revenue=Decimal("600"),
                gross_profit=Decimal("400"),
                period_end="2022-12-31",
            ),
            _make_period(
                revenue=Decimal("1000"),
                cost_of_revenue=Decimal("570"),
                gross_profit=Decimal("430"),
                period_end="2023-12-31",
            ),
            _make_period(
                revenue=Decimal("1000"),
                cost_of_revenue=Decimal("550"),
                gross_profit=Decimal("450"),
                period_end="2024-12-31",
            ),
        ]
        history = FinancialHistory(ticker="TEST", periods=periods)
        score = margin_expansion_score(history)
        assert score > 0.0
        assert score <= 3.0

    def test_contracting_margins_score_zero(self):
        """Declining gross margins should score zero."""
        periods = [
            _make_period(
                revenue=Decimal("1000"),
                cost_of_revenue=Decimal("500"),
                gross_profit=Decimal("500"),
                period_end="2022-12-31",
            ),
            _make_period(
                revenue=Decimal("1000"),
                cost_of_revenue=Decimal("550"),
                gross_profit=Decimal("450"),
                period_end="2023-12-31",
            ),
            _make_period(
                revenue=Decimal("1000"),
                cost_of_revenue=Decimal("600"),
                gross_profit=Decimal("400"),
                period_end="2024-12-31",
            ),
        ]
        history = FinancialHistory(ticker="TEST", periods=periods)
        score = margin_expansion_score(history)
        assert score == 0.0

    def test_single_period_scores_zero(self):
        """Single period cannot have consecutive expansions."""
        periods = [
            _make_period(
                revenue=Decimal("1000"),
                cost_of_revenue=Decimal("600"),
                gross_profit=Decimal("400"),
                period_end="2024-12-31",
            )
        ]
        history = FinancialHistory(ticker="TEST", periods=periods)
        score = margin_expansion_score(history)
        assert score == 0.0

    def test_expansion_far_from_ath_scores_low(self):
        """Expanding margins but far below historical ATH should score lower."""
        # ATH is 0.70, latest is 0.45 -> 2500bps away from ATH (> 200bps threshold)
        periods = [
            _make_period(
                revenue=Decimal("1000"),
                cost_of_revenue=Decimal("300"),
                gross_profit=Decimal("700"),
                period_end="2019-12-31",
            ),
            _make_period(
                revenue=Decimal("1000"),
                cost_of_revenue=Decimal("600"),
                gross_profit=Decimal("400"),
                period_end="2022-12-31",
            ),
            _make_period(
                revenue=Decimal("1000"),
                cost_of_revenue=Decimal("570"),
                gross_profit=Decimal("430"),
                period_end="2023-12-31",
            ),
            _make_period(
                revenue=Decimal("1000"),
                cost_of_revenue=Decimal("550"),
                gross_profit=Decimal("450"),
                period_end="2024-12-31",
            ),
        ]
        history = FinancialHistory(ticker="TEST", periods=periods)
        score_far = margin_expansion_score(history)
        # Score near ATH (ATH=0.45, latest=0.45)
        periods_near = [
            _make_period(
                revenue=Decimal("1000"),
                cost_of_revenue=Decimal("600"),
                gross_profit=Decimal("400"),
                period_end="2022-12-31",
            ),
            _make_period(
                revenue=Decimal("1000"),
                cost_of_revenue=Decimal("570"),
                gross_profit=Decimal("430"),
                period_end="2023-12-31",
            ),
            _make_period(
                revenue=Decimal("1000"),
                cost_of_revenue=Decimal("550"),
                gross_profit=Decimal("450"),
                period_end="2024-12-31",
            ),
        ]
        history_near = FinancialHistory(ticker="TEST", periods=periods_near)
        score_near = margin_expansion_score(history_near)
        assert score_near > score_far

    def test_capped_at_three(self):
        """Score is always <= 3.0."""
        # Massive margin expansions
        periods = [
            _make_period(
                revenue=Decimal("1000"),
                cost_of_revenue=Decimal("900"),
                gross_profit=Decimal("100"),
                period_end="2022-12-31",
            ),
            _make_period(
                revenue=Decimal("1000"),
                cost_of_revenue=Decimal("700"),
                gross_profit=Decimal("300"),
                period_end="2023-12-31",
            ),
            _make_period(
                revenue=Decimal("1000"),
                cost_of_revenue=Decimal("500"),
                gross_profit=Decimal("500"),
                period_end="2024-12-31",
            ),
        ]
        history = FinancialHistory(ticker="TEST", periods=periods)
        score = margin_expansion_score(history)
        assert score <= 3.0


# ---------------------------------------------------------------------------
# Task 4: Inflection Composite + Metadata
# ---------------------------------------------------------------------------


class TestInflectionScore:
    def test_returns_factor_score(self):
        """inflection_score should return a FactorScore with expected fields."""
        from margin_engine.models.scoring import FactorScore

        periods = [
            _make_period(
                revenue=Decimal("1000"),
                cost_of_revenue=Decimal("600"),
                period_end="2024-12-31",
            )
        ]
        history = FinancialHistory(ticker="TEST", periods=periods)
        result = inflection_score(history)
        assert isinstance(result, FactorScore)
        assert result.name == "inflection_detection"
        assert 0.0 <= result.raw_value <= 10.0
        assert 0.0 <= result.percentile_rank <= 100.0

    def test_metadata_keys_present(self):
        """FactorScore metadata must include required keys."""
        periods = [
            _make_period(
                revenue=Decimal("1000"),
                cost_of_revenue=Decimal("600"),
                net_income=Decimal("50"),
                depreciation=Decimal("10"),
                period_end="2024-12-31",
            )
        ]
        history = FinancialHistory(ticker="TEST", periods=periods)
        result = inflection_score(history)
        assert result.metadata is not None
        assert "opex_deleverage_detected" in result.metadata
        assert "fcf_crossover_detected" in result.metadata
        assert "margin_expansion_magnitude" in result.metadata
        assert "periods_since_inflection" in result.metadata

    def test_metadata_types(self):
        """Metadata values must have correct types."""
        periods = [
            _make_period(
                revenue=Decimal("1000"),
                cost_of_revenue=Decimal("600"),
                period_end="2024-12-31",
            )
        ]
        history = FinancialHistory(ticker="TEST", periods=periods)
        result = inflection_score(history)
        meta = result.metadata
        assert isinstance(meta["opex_deleverage_detected"], bool)
        assert isinstance(meta["fcf_crossover_detected"], bool)
        assert isinstance(meta["margin_expansion_magnitude"], float)
        assert isinstance(meta["periods_since_inflection"], int)

    def test_composite_combines_sub_scores(self):
        """All three signals active -> composite raw_value > zero."""
        # Setup: declining opex ratio, FCF crossover, margin expansion
        neg_periods = [
            _make_period(
                revenue=Decimal("1000"),
                cost_of_revenue=Decimal("600"),
                net_income=Decimal("-50"),
                depreciation=Decimal("5"),
                gross_profit=Decimal("400"),
                period_end="2021-12-31",
            ),
            _make_period(
                revenue=Decimal("1000"),
                cost_of_revenue=Decimal("600"),
                net_income=Decimal("-30"),
                depreciation=Decimal("5"),
                gross_profit=Decimal("400"),
                period_end="2022-12-31",
            ),
        ]
        pos_periods = [
            _make_period(
                revenue=Decimal("1000"),
                cost_of_revenue=Decimal("560"),
                net_income=Decimal("50"),
                depreciation=Decimal("5"),
                gross_profit=Decimal("440"),
                period_end="2023-12-31",
            ),
            _make_period(
                revenue=Decimal("1000"),
                cost_of_revenue=Decimal("540"),
                net_income=Decimal("70"),
                depreciation=Decimal("5"),
                gross_profit=Decimal("460"),
                period_end="2024-12-31",
            ),
        ]
        history = FinancialHistory(ticker="TEST", periods=neg_periods + pos_periods)
        result = inflection_score(history)
        assert result.raw_value > 0.0

    def test_raw_value_scaled_to_ten(self):
        """raw_value should be on a 0-10 scale."""
        periods = [
            _make_period(
                revenue=Decimal("1000"),
                cost_of_revenue=Decimal("600"),
                period_end="2024-12-31",
            )
        ]
        history = FinancialHistory(ticker="TEST", periods=periods)
        result = inflection_score(history)
        assert result.raw_value <= 10.0
        assert result.raw_value >= 0.0

    def test_opex_deleverage_detected_flag(self):
        """opex_deleverage_detected is True when opex signal > 0."""
        periods = [
            _make_period(
                revenue=Decimal("1000"),
                cost_of_revenue=Decimal("620"),
                period_end="2022-12-31",
            ),
            _make_period(
                revenue=Decimal("1000"),
                cost_of_revenue=Decimal("600"),
                period_end="2023-12-31",
            ),
            _make_period(
                revenue=Decimal("1000"),
                cost_of_revenue=Decimal("570"),
                period_end="2024-12-31",
            ),
        ]
        history = FinancialHistory(ticker="TEST", periods=periods)
        result = inflection_score(history)
        assert result.metadata["opex_deleverage_detected"] is True

    def test_fcf_crossover_detected_flag(self):
        """fcf_crossover_detected is True when FCF signal > 0."""
        periods = [
            _make_period(
                revenue=Decimal("1000"),
                cost_of_revenue=Decimal("600"),
                net_income=Decimal("-50"),
                depreciation=Decimal("5"),
                period_end="2022-12-31",
            ),
            _make_period(
                revenue=Decimal("1000"),
                cost_of_revenue=Decimal("600"),
                net_income=Decimal("60"),
                depreciation=Decimal("5"),
                period_end="2023-12-31",
            ),
            _make_period(
                revenue=Decimal("1000"),
                cost_of_revenue=Decimal("600"),
                net_income=Decimal("80"),
                depreciation=Decimal("5"),
                period_end="2024-12-31",
            ),
        ]
        history = FinancialHistory(ticker="TEST", periods=periods)
        result = inflection_score(history)
        assert result.metadata["fcf_crossover_detected"] is True


# ---------------------------------------------------------------------------
# Task 5: Inflection Composite Edge Cases
# ---------------------------------------------------------------------------


class TestInflectionComposite:
    def test_no_inflection_scores_zero(self):
        """Stable company with no signals -> composite 0."""
        periods = [
            _make_period(1000, 650),
            _make_period(1100, 715),
            _make_period(1200, 780),
        ]
        history = FinancialHistory(ticker="TEST", periods=periods)
        result = inflection_score(history)
        assert result.raw_value == 0.0
        assert result.metadata["opex_deleverage_detected"] is False
        assert result.metadata["fcf_crossover_detected"] is False
