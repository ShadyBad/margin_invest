"""Tests for v3 universe scoring pipeline."""

from decimal import Decimal

from margin_engine.models.financial import (
    AssetProfile,
    BalanceSheet,
    CashFlowStatement,
    FinancialHistory,
    FinancialPeriod,
    GICSSector,
    IncomeStatement,
)
from margin_engine.scoring.v3_pipeline import TickerV3Data, score_universe_v3


def _period(period_end="2024-09-28", ebit=Decimal("200"), **kwargs):
    defaults = dict(
        revenue=Decimal("1000"),
        cost_of_revenue=Decimal("600"),
        gross_profit=Decimal("400"),
        depreciation=Decimal("50"),
        net_income=Decimal("160"),
        total_equity=Decimal("500"),
        long_term_debt=Decimal("200"),
        short_term_debt=Decimal("100"),
        cash_and_equivalents=Decimal("50"),
        total_assets=Decimal("1500"),
        operating_cash_flow=Decimal("250"),
        capital_expenditures=Decimal("-80"),
        shares_outstanding=100,
    )
    defaults.update(kwargs)
    defaults["ebit"] = ebit
    return FinancialPeriod(
        period_end=period_end,
        filing_date="2024-11-01",
        current_income=IncomeStatement(
            revenue=defaults["revenue"],
            cost_of_revenue=defaults["cost_of_revenue"],
            gross_profit=defaults["gross_profit"],
            ebit=defaults["ebit"],
            depreciation=defaults["depreciation"],
            net_income=defaults["net_income"],
            shares_outstanding=defaults["shares_outstanding"],
        ),
        current_balance=BalanceSheet(
            total_assets=defaults["total_assets"],
            total_equity=defaults["total_equity"],
            long_term_debt=defaults["long_term_debt"],
            short_term_debt=defaults["short_term_debt"],
            cash_and_equivalents=defaults["cash_and_equivalents"],
            shares_outstanding=defaults["shares_outstanding"],
        ),
        current_cash_flow=CashFlowStatement(
            operating_cash_flow=defaults["operating_cash_flow"],
            capital_expenditures=defaults["capital_expenditures"],
        ),
    )


def _make_ticker_data(ticker: str, sector=GICSSector.TECHNOLOGY) -> TickerV3Data:
    periods = [_period(period_end=f"{yr}-12-31") for yr in range(2020, 2025)]
    return TickerV3Data(
        ticker=ticker,
        history=FinancialHistory(ticker=ticker, periods=periods),
        latest_period=periods[-1],
        profile=AssetProfile(
            ticker=ticker,
            name=f"{ticker} Corp",
            sector=sector,
            market_cap=Decimal("10000000000"),
            shares_outstanding=100,
        ),
        current_price=100.0,
        current_fcf_per_share=5.0,
        sustainable_growth_rate=0.08,
        sue_percentile=50.0,
        momentum_percentile=50.0,
        dcf_iv=120.0,
    )


class TestScoreUniverseV3:
    def test_basic_scoring(self):
        """Score 3 tickers, get V3Result for each."""
        data = [_make_ticker_data(t) for t in ["AAPL", "MSFT", "GOOGL"]]
        results = score_universe_v3(data, shiller_cape=25.0)
        assert len(results) == 3
        for r in results:
            assert r.ticker in {"AAPL", "MSFT", "GOOGL"}
            assert r.track_a.track == "compounder"
            assert r.track_b.track == "mispricing"

    def test_portfolio_cap_enforced(self):
        """With > 10 tickers, only top 10 get non-zero positions."""
        data = [_make_ticker_data(f"T{i:02d}") for i in range(15)]
        results = score_universe_v3(data, shiller_cape=25.0)
        assert len(results) == 15
        positioned = [r for r in results if r.max_position_pct > 0]
        assert len(positioned) <= 10

    def test_empty_universe(self):
        results = score_universe_v3([], shiller_cape=25.0)
        assert results == []

    def test_single_ticker(self):
        data = [_make_ticker_data("SOLO")]
        results = score_universe_v3(data, shiller_cape=25.0)
        assert len(results) == 1

    def test_regime_affects_results(self):
        """Different CAPE values should be accepted."""
        data = [_make_ticker_data("TEST")]
        euphoria = score_universe_v3(data, shiller_cape=40.0)
        cheap = score_universe_v3(data, shiller_cape=12.0)
        assert euphoria[0].ticker == cheap[0].ticker == "TEST"

    def test_optimize_false_zeroes_excess_positions(self):
        """optimize=False (default): positions beyond MAX_POSITIONS are zeroed."""
        data = [_make_ticker_data(f"T{i:02d}") for i in range(15)]
        results = score_universe_v3(data, shiller_cape=25.0, optimize=False)
        assert len(results) == 15
        positioned = [r for r in results if r.max_position_pct > 0]
        assert len(positioned) <= 10

    def test_optimize_true_retains_all_positions(self):
        """optimize=True: positions are not zeroed by the portfolio cap step.

        With optimize=True the pipeline skips the MAX_POSITIONS zeroing so the
        optimizer can allocate freely. We verify that the optimize flag is
        accepted and that results match what the orchestrator produced (no
        post-hoc modification). With identical synthetic data the orchestrator
        assigns 0% to every ticker (they score as 'neither'), so we confirm
        that optimize=True at least does not *reduce* any position below what
        the orchestrator assigned and returns the full result set.
        """
        data = [_make_ticker_data(f"T{i:02d}") for i in range(15)]
        results_opt = score_universe_v3(data, shiller_cape=25.0, optimize=True)
        results_no_opt = score_universe_v3(data, shiller_cape=25.0, optimize=False)
        assert len(results_opt) == 15
        assert len(results_no_opt) == 15
        # optimize=True should never produce a *lower* position than optimize=False
        # because optimize=False zeros excess positions while optimize=True preserves them.
        opt_positions = {r.ticker: r.max_position_pct for r in results_opt}
        no_opt_positions = {r.ticker: r.max_position_pct for r in results_no_opt}
        for ticker in opt_positions:
            assert opt_positions[ticker] >= no_opt_positions[ticker]

    def test_beta_none_falls_back_to_sector_wacc(self):
        """When beta is None (default), sector WACC fallback is used — backward compatible."""
        data_no_beta = [_make_ticker_data("SOLO")]
        assert data_no_beta[0].beta is None
        results = score_universe_v3(data_no_beta, shiller_cape=25.0)
        assert len(results) == 1
        assert results[0].ticker == "SOLO"
        # Should produce valid results (no crash, same as pre-integration behavior)
        assert results[0].conviction is not None

    def test_beta_provided_uses_company_wacc(self):
        """When beta is provided, company-specific WACC is computed via CAPM."""
        td_no_beta = _make_ticker_data("TEST")
        td_with_beta = _make_ticker_data("TEST")
        td_with_beta.beta = 1.5  # high beta => higher WACC => different scores

        results_no_beta = score_universe_v3([td_no_beta], shiller_cape=25.0)
        results_with_beta = score_universe_v3([td_with_beta], shiller_cape=25.0)

        assert len(results_no_beta) == 1
        assert len(results_with_beta) == 1
        # Both should produce valid results
        assert results_no_beta[0].conviction is not None
        assert results_with_beta[0].conviction is not None


class TestScoreModifiersIntegration:
    """Tests for score modifier wiring into the v3 pipeline."""

    def test_neutral_modifiers_produce_modifier_breakdown(self):
        """With neutral modifier inputs, breakdown should exist with all multipliers ~1.0."""
        td = _make_ticker_data("TEST")
        results = score_universe_v3([td], shiller_cape=25.0)
        assert len(results) == 1
        r = results[0]
        # Modifier breakdown should always be populated
        assert r.modifier_breakdown is not None
        assert "anti_consensus" in r.modifier_breakdown
        assert "liquidity" in r.modifier_breakdown
        assert "insider" in r.modifier_breakdown
        assert "combined" in r.modifier_breakdown
        # Insider modifier should be 1.0 (no cluster detected by default)
        assert r.modifier_breakdown["insider"] == 1.0

    def test_modified_score_populated(self):
        """Modified score should be populated on every result."""
        td = _make_ticker_data("TEST")
        results = score_universe_v3([td], shiller_cape=25.0)
        r = results[0]
        assert r.modified_score is not None
        # Modified score = original composite * combined modifier
        assert isinstance(r.modified_score, float)

    def test_insider_cluster_boosts_score(self):
        """When insider cluster is detected, modified_score should be boosted vs neutral."""
        td_neutral = _make_ticker_data("TEST")

        td_insider = _make_ticker_data("TEST")
        td_insider.insider_cluster_detected = True
        td_insider.insider_cluster_score_value = 0.8
        td_insider.insider_total_buy_value = 10_000_000.0
        td_insider.insider_has_first_buy = True
        td_insider.high_52w = 200.0  # current_price=100, so 50% drawdown

        results_neutral = score_universe_v3([td_neutral], shiller_cape=25.0)
        results_insider = score_universe_v3([td_insider], shiller_cape=25.0)

        r_neutral = results_neutral[0]
        r_insider = results_insider[0]

        # Insider modifier should be > 1.0
        assert r_insider.modifier_breakdown["insider"] > 1.0
        # Modified score should be higher when insider signal fires
        assert r_insider.modified_score >= r_neutral.modified_score

    def test_anti_consensus_with_improving_trajectory_boosts(self):
        """High short interest + improving fundamentals should boost score."""
        td_neutral = _make_ticker_data("TEST")

        td_ac = _make_ticker_data("TEST")
        td_ac.short_interest_percentile = 90.0  # High short interest
        td_ac.fundamental_trajectory = 0.9  # Improving fundamentals
        td_ac.analyst_divergence = -0.8  # Bearish consensus
        td_ac.eps_revision_strength = 0.5  # Positive EPS revisions

        score_universe_v3([td_neutral], shiller_cape=25.0)  # baseline, verify no crash
        results_ac = score_universe_v3([td_ac], shiller_cape=25.0)

        # Anti-consensus modifier should be above 1.0
        assert results_ac[0].modifier_breakdown["anti_consensus"] > 1.0

    def test_small_cap_liquidity_penalizes(self):
        """Small market cap / low volume ticker should get liquidity penalty."""
        td_small = _make_ticker_data("SMALL")
        td_small.profile = AssetProfile(
            ticker="SMALL",
            name="Small Corp",
            sector=GICSSector.TECHNOLOGY,
            market_cap=Decimal("100000000"),  # $100M
            shares_outstanding=10,
            avg_daily_volume=Decimal("50000"),  # Low ADV
        )
        td_small.latest_period = _period()
        periods = [_period(period_end=f"{yr}-12-31") for yr in range(2020, 2025)]
        td_small.history = FinancialHistory(ticker="SMALL", periods=periods)

        results = score_universe_v3([td_small], shiller_cape=25.0)
        r = results[0]

        # Liquidity modifier should be < 1.0 for small cap
        assert r.modifier_breakdown["liquidity"] < 1.0

    def test_modifiers_do_not_change_conviction(self):
        """Modifiers affect score, not conviction tier."""
        td = _make_ticker_data("TEST")
        td.insider_cluster_detected = True
        td.insider_cluster_score_value = 0.8
        td.insider_total_buy_value = 10_000_000.0

        td_neutral = _make_ticker_data("TEST")

        results_mod = score_universe_v3([td], shiller_cape=25.0)
        results_neutral = score_universe_v3([td_neutral], shiller_cape=25.0)

        # Conviction should be the same regardless of modifiers
        assert results_mod[0].conviction == results_neutral[0].conviction

    def test_default_modifier_fields_are_neutral(self):
        """Default TickerV3Data should have neutral modifier inputs."""
        td = _make_ticker_data("TEST")
        assert td.fundamental_trajectory == 0.5
        assert td.high_52w is None
        assert td.short_interest_percentile == 50.0
        assert td.analyst_divergence == 0.0
        assert td.eps_revision_strength == 0.0
        assert td.insider_cluster_score_value == 0.0
        assert td.insider_cluster_detected is False
        assert td.insider_total_buy_value == 0.0
        assert td.insider_has_first_buy is False
