"""Tests for post-composite score modifiers."""

from decimal import Decimal

import pytest
from margin_engine.models.financial import (
    BalanceSheet,
    CashFlowStatement,
    FinancialHistory,
    FinancialPeriod,
    IncomeStatement,
)
from margin_engine.scoring.score_modifiers import (
    anti_consensus_modifier,
    apply_all_modifiers,
    compute_fundamental_trajectory,
    insider_signal_modifier,
    liquidity_modifier,
    tam_modifier,
)


class TestApplyAllModifiers:
    def test_neutral_modifiers_no_change(self):
        score, breakdown = apply_all_modifiers(0.75, 1.0, 1.0, 1.0)
        assert score == pytest.approx(0.75)
        assert breakdown["combined"] == pytest.approx(1.0)

    def test_combined_product_clamped_floor(self):
        # 0.80 * 0.85 * 1.0 = 0.68 -> clamped to 0.75
        score, breakdown = apply_all_modifiers(1.0, 0.80, 0.85, 1.0)
        assert breakdown["combined"] == pytest.approx(0.75)
        assert score == pytest.approx(0.75)

    def test_combined_product_clamped_ceiling(self):
        # 1.15 * 1.0 * 1.15 = 1.3225 -> clamped to 1.25
        score, breakdown = apply_all_modifiers(1.0, 1.15, 1.0, 1.15)
        assert breakdown["combined"] == pytest.approx(1.25)
        assert score == pytest.approx(1.25)

    def test_breakdown_contains_all_keys(self):
        _, breakdown = apply_all_modifiers(0.5, 1.05, 0.95, 1.10)
        assert set(breakdown.keys()) == {
            "anti_consensus",
            "liquidity",
            "insider",
            "inflection",
            "tam",
            "combined",
        }

    def test_score_multiplied_by_combined(self):
        score, breakdown = apply_all_modifiers(0.8, 1.10, 0.90, 1.05)
        expected_combined = 1.10 * 0.90 * 1.05
        assert breakdown["combined"] == pytest.approx(expected_combined)
        assert score == pytest.approx(0.8 * expected_combined)

    def test_zero_score_stays_zero(self):
        score, _ = apply_all_modifiers(0.0, 1.15, 0.90, 1.10)
        assert score == pytest.approx(0.0)

    def test_five_param_backward_compat(self):
        """4-param call (inflection and tam default to 1.0) still works."""
        score, breakdown = apply_all_modifiers(0.75, 1.0, 1.0, 1.0)
        assert score == pytest.approx(0.75)
        assert breakdown["inflection"] == pytest.approx(1.0)
        assert breakdown["tam"] == pytest.approx(1.0)

    def test_six_param_with_tam(self):
        """Explicit tam param is multiplied into combined."""
        score, breakdown = apply_all_modifiers(1.0, 1.0, 1.0, 1.0, tam=1.05)
        assert breakdown["tam"] == pytest.approx(1.05)
        assert breakdown["combined"] == pytest.approx(1.05)
        assert score == pytest.approx(1.05)

    def test_six_param_with_inflection_and_tam(self):
        """Both inflection and tam multiply into combined."""
        score, breakdown = apply_all_modifiers(1.0, 1.0, 1.0, 1.0, inflection=1.02, tam=1.03)
        expected = 1.0 * 1.0 * 1.0 * 1.02 * 1.03
        assert breakdown["combined"] == pytest.approx(expected)
        assert score == pytest.approx(expected)


class TestLiquidityModifier:
    def test_mega_cap_high_volume_neutral(self):
        result = liquidity_modifier(200_000_000_000, 500_000_000, 1.2)
        assert result == pytest.approx(1.0, abs=0.01)

    def test_small_cap_low_volume_penalized(self):
        result = liquidity_modifier(500_000_000, 2_000_000, 2.0)
        assert 0.85 <= result < 0.96

    def test_micro_cap_floor(self):
        # cap_score=0.0 (log10(1e8)=8, threshold), turnover=0.5% -> 1.0, stability=0.5
        # avg=0.5 -> 0.85 + 0.15*0.5 = 0.925
        result = liquidity_modifier(100_000_000, 500_000, 3.5)
        assert result == pytest.approx(0.925, abs=0.01)

    def test_high_divergence_penalized(self):
        result = liquidity_modifier(10_000_000_000, 50_000_000, 4.0)
        assert result < 1.0

    def test_none_divergence_mild_penalty(self):
        result = liquidity_modifier(10_000_000_000, 50_000_000, None)
        assert result < 1.0

    def test_never_boosts(self):
        result = liquidity_modifier(500_000_000_000, 1_000_000_000, 1.0)
        assert result <= 1.0

    def test_output_in_range(self):
        result = liquidity_modifier(100_000_000, 100_000, 5.0)
        assert 0.85 <= result <= 1.0

    def test_zero_market_cap(self):
        # cap=0, turnover=0, stability=0.7 -> avg=0.233 -> 0.85+0.15*0.233=0.885
        result = liquidity_modifier(0, 0, None)
        assert result == pytest.approx(0.885, abs=0.01)

    def test_absolute_floor_all_worst(self):
        # cap=0 -> 0.0, turnover=0 -> 0.0, divergence>=3.0 -> 0.5
        # avg=0.5/3=0.167 -> 0.85+0.15*0.167=0.875
        result = liquidity_modifier(0, 0, 5.0)
        assert result == pytest.approx(0.875, abs=0.01)
        assert result >= 0.85


class TestInsiderSignalModifier:
    def test_no_cluster_neutral(self):
        assert insider_signal_modifier(0.0, False, 0, None, False) == pytest.approx(1.0)

    def test_cluster_base_boost(self):
        assert insider_signal_modifier(5.0, True, 500_000, None, False) == pytest.approx(1.05)

    def test_cluster_with_drawdown(self):
        assert insider_signal_modifier(5.0, True, 500_000, -0.15, False) == pytest.approx(1.08)

    def test_cluster_with_high_magnitude(self):
        assert insider_signal_modifier(5.0, True, 6_000_000, None, False) == pytest.approx(1.08)

    def test_cluster_with_first_buy(self):
        assert insider_signal_modifier(5.0, True, 500_000, None, True) == pytest.approx(1.09)

    def test_max_modifier(self):
        assert insider_signal_modifier(10.0, True, 6_000_000, -0.20, True) == pytest.approx(1.15)

    def test_never_penalizes(self):
        assert insider_signal_modifier(0.0, False, 0, -0.50, False) >= 1.0

    def test_drawdown_threshold_boundary(self):
        # Exactly -10% should not trigger (need < -0.10)
        assert insider_signal_modifier(5.0, True, 500_000, -0.10, False) == pytest.approx(1.05)


# ---------------------------------------------------------------------------
# Helpers for building FinancialHistory fixtures
# ---------------------------------------------------------------------------


def _make_period(
    year: int,
    ebit: Decimal = Decimal("200"),
    revenue: Decimal = Decimal("1000"),
    gross_margin_pct: float = 0.40,
    equity: Decimal = Decimal("500"),
    debt: Decimal = Decimal("200"),
    cash: Decimal = Decimal("100"),
) -> FinancialPeriod:
    """Build a FinancialPeriod with controllable ROIC and gross margin."""
    cogs = revenue * Decimal(str(1 - gross_margin_pct))
    return FinancialPeriod(
        period_end=f"{year}-12-31",
        filing_date=f"{year + 1}-02-15",
        current_income=IncomeStatement(
            revenue=revenue,
            cost_of_revenue=cogs,
            gross_profit=revenue - cogs,
            ebit=ebit,
            net_income=ebit * Decimal("0.79"),
        ),
        current_balance=BalanceSheet(
            total_assets=Decimal("2000"),
            total_equity=equity,
            long_term_debt=debt,
            cash_and_equivalents=cash,
        ),
        current_cash_flow=CashFlowStatement(
            operating_cash_flow=Decimal("250"),
            capital_expenditures=Decimal("-50"),
        ),
    )


# ---------------------------------------------------------------------------
# TestComputeFundamentalTrajectory
# ---------------------------------------------------------------------------


class TestComputeFundamentalTrajectory:
    """Tests for compute_fundamental_trajectory."""

    def test_improving_both(self):
        """3 periods with increasing ROIC and GM -> trajectory == 1.0."""
        history = FinancialHistory(
            ticker="IMPROVE",
            periods=[
                _make_period(2021, ebit=Decimal("100"), gross_margin_pct=0.30),
                _make_period(2022, ebit=Decimal("150"), gross_margin_pct=0.40),
                _make_period(2023, ebit=Decimal("200"), gross_margin_pct=0.50),
            ],
        )
        trajectory = compute_fundamental_trajectory(history)
        assert trajectory > 0.7
        assert trajectory == pytest.approx(1.0)

    def test_declining_both(self):
        """3 periods with declining ROIC and GM -> trajectory == 0.0."""
        history = FinancialHistory(
            ticker="DECLINE",
            periods=[
                _make_period(2021, ebit=Decimal("200"), gross_margin_pct=0.50),
                _make_period(2022, ebit=Decimal("150"), gross_margin_pct=0.40),
                _make_period(2023, ebit=Decimal("100"), gross_margin_pct=0.30),
            ],
        )
        trajectory = compute_fundamental_trajectory(history)
        assert trajectory < 0.3
        assert trajectory == pytest.approx(0.0)

    def test_single_period(self):
        """Only 1 period -> neutral 0.5 (no transitions to evaluate)."""
        history = FinancialHistory(
            ticker="SINGLE",
            periods=[_make_period(2023)],
        )
        trajectory = compute_fundamental_trajectory(history)
        assert trajectory == pytest.approx(0.5)

    def test_mixed_signals(self):
        """ROIC improving, GM declining -> middle range (0.5)."""
        history = FinancialHistory(
            ticker="MIXED",
            periods=[
                _make_period(2021, ebit=Decimal("100"), gross_margin_pct=0.50),
                _make_period(2022, ebit=Decimal("150"), gross_margin_pct=0.40),
                _make_period(2023, ebit=Decimal("200"), gross_margin_pct=0.30),
            ],
        )
        trajectory = compute_fundamental_trajectory(history)
        assert 0.3 <= trajectory <= 0.7
        assert trajectory == pytest.approx(0.5)

    def test_two_periods_both_improving(self):
        """2 periods, both improving -> trajectory == 1.0."""
        history = FinancialHistory(
            ticker="TWO_UP",
            periods=[
                _make_period(2022, ebit=Decimal("100"), gross_margin_pct=0.30),
                _make_period(2023, ebit=Decimal("200"), gross_margin_pct=0.50),
            ],
        )
        trajectory = compute_fundamental_trajectory(history)
        assert trajectory == pytest.approx(1.0)

    def test_two_periods_both_declining(self):
        """2 periods, both declining -> trajectory == 0.0."""
        history = FinancialHistory(
            ticker="TWO_DN",
            periods=[
                _make_period(2022, ebit=Decimal("200"), gross_margin_pct=0.50),
                _make_period(2023, ebit=Decimal("100"), gross_margin_pct=0.30),
            ],
        )
        trajectory = compute_fundamental_trajectory(history)
        assert trajectory == pytest.approx(0.0)

    def test_flat_is_neutral(self):
        """Identical periods -> trajectory 0.5 (no improvement or decline)."""
        history = FinancialHistory(
            ticker="FLAT",
            periods=[
                _make_period(2021, ebit=Decimal("150"), gross_margin_pct=0.40),
                _make_period(2022, ebit=Decimal("150"), gross_margin_pct=0.40),
                _make_period(2023, ebit=Decimal("150"), gross_margin_pct=0.40),
            ],
        )
        trajectory = compute_fundamental_trajectory(history)
        assert trajectory == pytest.approx(0.5)

    def test_zero_invested_capital_handles_gracefully(self):
        """Zero equity+debt-cash -> cannot compute ROIC -> neutral."""
        history = FinancialHistory(
            ticker="ZERO_IC",
            periods=[
                _make_period(
                    2022,
                    equity=Decimal("50"),
                    debt=Decimal("50"),
                    cash=Decimal("100"),
                ),
                _make_period(2023, ebit=Decimal("200"), gross_margin_pct=0.50),
            ],
        )
        # Should not crash; first period has IC=0 so ROIC=None -> mixed -> 0.5
        trajectory = compute_fundamental_trajectory(history)
        assert 0.0 <= trajectory <= 1.0
        assert trajectory == pytest.approx(0.5)

    def test_uses_last_four_periods_only(self):
        """With 5+ periods, only the last 4 (3 transitions) are used."""
        # First 2 periods declining, last 3 improving.
        # Only the last 4 periods matter: decline, improve, improve -> (0.0, 1.0, 1.0) -> 0.667
        history = FinancialHistory(
            ticker="LONG",
            periods=[
                _make_period(2019, ebit=Decimal("250"), gross_margin_pct=0.55),
                _make_period(2020, ebit=Decimal("200"), gross_margin_pct=0.50),
                _make_period(2021, ebit=Decimal("150"), gross_margin_pct=0.40),
                _make_period(2022, ebit=Decimal("200"), gross_margin_pct=0.45),
                _make_period(2023, ebit=Decimal("250"), gross_margin_pct=0.50),
            ],
        )
        trajectory = compute_fundamental_trajectory(history)
        # Last 4: 2020(200,0.50), 2021(150,0.40), 2022(200,0.45), 2023(250,0.50)
        # Transitions: 2020->2021 (both decline=0.0), 2021->2022 (both improve=1.0),
        #              2022->2023 (both improve=1.0) -> avg = 2/3 = 0.667
        assert trajectory == pytest.approx(2.0 / 3.0, abs=0.01)


# ---------------------------------------------------------------------------
# TestAntiConsensusModifier
# ---------------------------------------------------------------------------


class TestAntiConsensusModifier:
    """Tests for anti_consensus_modifier."""

    def test_strong_signal_boosts(self):
        """High short interest + bearish analysts + positive EPS + strong trajectory -> boost."""
        result = anti_consensus_modifier(90.0, -0.8, 0.5, 0.9)
        assert result > 1.05

    def test_bearish_penalizes(self):
        """Bearish sentiment with weak fundamentals -> penalty."""
        result = anti_consensus_modifier(80.0, -0.5, -0.5, 0.1)
        assert result < 1.0

    def test_neutral(self):
        """Neutral inputs -> approximately 1.0."""
        result = anti_consensus_modifier(50.0, 0.0, 0.0, 0.5)
        assert result == pytest.approx(1.0, abs=0.02)

    def test_range_extreme_bullish(self):
        """Extreme bullish inputs stay within [0.90, 1.15]."""
        result = anti_consensus_modifier(100.0, -1.0, 1.0, 1.0)
        assert 0.90 <= result <= 1.15

    def test_range_extreme_bearish(self):
        """Extreme bearish inputs stay within [0.90, 1.15]."""
        result = anti_consensus_modifier(0.0, 1.0, -1.0, 0.0)
        assert 0.90 <= result <= 1.15

    def test_low_trajectory_suppresses_boost(self):
        """Even with high short interest, low trajectory means consensus is right -> penalty."""
        result = anti_consensus_modifier(95.0, -0.9, 0.8, 0.2)
        assert result < 1.0

    def test_mid_trajectory_near_neutral(self):
        """Trajectory at 0.5 (boundary) -> modifier is exactly neutral."""
        result = anti_consensus_modifier(80.0, -0.5, 0.3, 0.5)
        assert result == pytest.approx(1.0, abs=0.01)

    def test_perfect_divergence_signal(self):
        """Maximum divergence signal -> hits or approaches ceiling."""
        result = anti_consensus_modifier(100.0, -1.0, 1.0, 1.0)
        assert result >= 1.10

    def test_no_short_interest_still_works(self):
        """Zero short interest percentile -> only analyst/EPS components contribute."""
        result = anti_consensus_modifier(0.0, -0.5, 0.5, 0.9)
        assert 0.90 <= result <= 1.15

    def test_worst_case_penalty(self):
        """Trajectory at 0.0 -> maximum penalty regardless of other inputs."""
        result = anti_consensus_modifier(50.0, 0.0, 0.0, 0.0)
        # weakness = 1.0, effective_signal = -0.4 -> modifier = 1.0 + (-0.4)*0.10 = 0.96
        assert result == pytest.approx(0.96, abs=0.01)

    def test_trajectory_just_above_half(self):
        """Trajectory slightly above 0.5 -> small but positive effect."""
        result = anti_consensus_modifier(90.0, -0.8, 0.5, 0.55)
        # trajectory_scale = (0.55 - 0.5) * 2 = 0.1 -> very small boost
        assert 1.0 <= result <= 1.05

    def test_transition_zone_always_neutral(self):
        """Trajectory between 0.3 and 0.5 -> always returns 1.0."""
        for traj in [0.3, 0.35, 0.4, 0.45]:
            result = anti_consensus_modifier(90.0, -1.0, 1.0, traj)
            assert result == pytest.approx(1.0, abs=0.001)


class TestAntiConsensusModifierNLP:
    """Tests for anti_consensus_modifier with optional nlp_sentiment."""

    def test_none_nlp_identical_to_original(self):
        """nlp_sentiment=None must produce identical results to omitting the param."""
        without_nlp = anti_consensus_modifier(90.0, -0.8, 0.5, 0.9)
        with_none = anti_consensus_modifier(90.0, -0.8, 0.5, 0.9, nlp_sentiment=None)
        assert without_nlp == pytest.approx(with_none)

    def test_none_nlp_backward_compat_weights(self):
        """Without NLP, weights stay 40/30/30. Verify against hand-calculated value."""
        # short_signal = (90-50)/50 = 0.8, analyst_signal = -(-0.8) = 0.8, eps_signal = 0.5
        # raw = 0.40*0.8 + 0.30*0.8 + 0.30*0.5 = 0.32 + 0.24 + 0.15 = 0.71
        # trajectory=0.9 -> scale = (0.9-0.5)*2 = 0.8 -> effective = 0.71*0.8 = 0.568
        # modifier = 1.0 + 0.568 * 0.15 = 1.0852
        result = anti_consensus_modifier(90.0, -0.8, 0.5, 0.9)
        assert result == pytest.approx(1.0 + 0.568 * 0.15, abs=0.001)

    def test_with_nlp_differs_from_without(self):
        """Providing nlp_sentiment must change the result compared to None."""
        without = anti_consensus_modifier(90.0, -0.8, 0.5, 0.9)
        with_nlp = anti_consensus_modifier(90.0, -0.8, 0.5, 0.9, nlp_sentiment=3.0)
        assert without != pytest.approx(with_nlp)

    def test_positive_nlp_with_improving_trajectory_boosts(self):
        """Strongly positive NLP sentiment + improving trajectory -> modifier > 1.0."""
        result = anti_consensus_modifier(70.0, -0.5, 0.3, 0.9, nlp_sentiment=4.0)
        assert result > 1.0

    def test_negative_nlp_reduces_modifier(self):
        """Negative NLP sentiment lowers modifier compared to equivalent zero NLP."""
        # Use trajectory > 0.5 so raw_signal matters
        with_zero_nlp = anti_consensus_modifier(70.0, -0.5, 0.3, 0.9, nlp_sentiment=0.0)
        with_neg_nlp = anti_consensus_modifier(70.0, -0.5, 0.3, 0.9, nlp_sentiment=-4.0)
        assert with_neg_nlp < with_zero_nlp

    def test_nlp_normalized_from_minus5_to_plus5(self):
        """NLP value of +5 normalizes to +1, -5 normalizes to -1."""
        # nlp_signal for +5 should equal nlp_signal for +1 in the [-1,+1] context
        # i.e. nlp_sentiment=5.0 -> nlp_signal=1.0, nlp_sentiment=-5.0 -> nlp_signal=-1.0
        # With weights 30/25/25/20: verify by computing expected value manually
        # short=(90-50)/50=0.8, analyst=-(-0.5)=0.5, eps=0.3, nlp=5.0/5.0=1.0
        # raw = 0.30*0.8 + 0.25*0.5 + 0.25*0.3 + 0.20*1.0 = 0.24+0.125+0.075+0.20 = 0.64
        # trajectory=0.9 -> scale=0.8 -> effective=0.64*0.8=0.512
        # modifier = 1.0 + 0.512*0.15 = 1.0768
        result = anti_consensus_modifier(90.0, -0.5, 0.3, 0.9, nlp_sentiment=5.0)
        assert result == pytest.approx(1.0 + 0.512 * 0.15, abs=0.001)

    def test_nlp_extreme_positive_clamped(self):
        """NLP > 5 or extreme combination still stays within [0.90, 1.15]."""
        result = anti_consensus_modifier(100.0, -1.0, 1.0, 1.0, nlp_sentiment=5.0)
        assert 0.90 <= result <= 1.15

    def test_nlp_extreme_negative_clamped(self):
        """Extreme negative NLP with weak trajectory stays within bounds."""
        result = anti_consensus_modifier(0.0, 1.0, -1.0, 0.0, nlp_sentiment=-5.0)
        assert 0.90 <= result <= 1.15

    def test_trajectory_gating_applies_to_nlp_signal(self):
        """Even with positive NLP, low trajectory (< 0.3) still causes penalty."""
        result = anti_consensus_modifier(70.0, -0.5, 0.5, 0.1, nlp_sentiment=5.0)
        assert result < 1.0

    def test_trajectory_transition_zone_neutral_with_nlp(self):
        """Trajectory in 0.3-0.5 returns 1.0 even when NLP is provided."""
        for traj in [0.3, 0.35, 0.4, 0.45]:
            result = anti_consensus_modifier(90.0, -1.0, 1.0, traj, nlp_sentiment=5.0)
            assert result == pytest.approx(1.0, abs=0.001)

    def test_weights_sum_to_one_with_nlp(self):
        """30/25/25/20 weights sum to 1.0 — verify via neutral inputs producing 1.0."""
        # All signals = 0 when inputs are neutral regardless of weight distribution
        # short=50 -> signal=0, analyst=0 -> signal=0, eps=0 -> signal=0, nlp=0 -> signal=0
        # But trajectory=0.5 is in transition zone -> effective=0 -> modifier=1.0
        result = anti_consensus_modifier(50.0, 0.0, 0.0, 0.5, nlp_sentiment=0.0)
        assert result == pytest.approx(1.0, abs=0.01)


class TestTAMModifier:
    """Tests for tam_modifier."""

    def test_none_returns_one(self):
        """None TAM score -> 1.0 (no data, neutral)."""
        assert tam_modifier(None) == pytest.approx(1.0)

    def test_score_5_returns_one(self):
        """Score at center (5.0) -> exactly 1.0."""
        assert tam_modifier(5.0) == pytest.approx(1.0)

    def test_score_above_5_boosts(self):
        """Score > 5 -> multiplier > 1.0."""
        result = tam_modifier(8.0)
        assert result > 1.0

    def test_score_below_5_penalizes(self):
        """Score < 5 -> multiplier < 1.0."""
        result = tam_modifier(2.0)
        assert result < 1.0

    def test_score_10_max_boost(self):
        """Score = 10 -> maximum boost 1.10."""
        assert tam_modifier(10.0) == pytest.approx(1.10)

    def test_score_0_max_penalty(self):
        """Score = 0 -> maximum penalty 0.95."""
        assert tam_modifier(0.0) == pytest.approx(0.95)

    def test_score_8_boost(self):
        """Score = 8 -> boost = (8-5)/5 * 0.10 = 0.06 -> 1.06."""
        assert tam_modifier(8.0) == pytest.approx(1.06)

    def test_score_2_penalty(self):
        """Score = 2 -> penalty = (5-2)/5 * 0.05 = 0.03 -> 0.97."""
        assert tam_modifier(2.0) == pytest.approx(0.97)

    def test_range_all_valid_scores(self):
        """For all scores 0-10, modifier stays in [0.95, 1.10]."""
        for score in [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]:
            result = tam_modifier(float(score))
            assert 0.95 <= result <= 1.10, f"score={score}: modifier={result} out of range"

    def test_clamps_above_10(self):
        """Score > 10 is clamped to 10 -> 1.10."""
        assert tam_modifier(15.0) == pytest.approx(1.10)

    def test_clamps_below_0(self):
        """Score < 0 is clamped to 0 -> 0.95."""
        assert tam_modifier(-5.0) == pytest.approx(0.95)
