"""Tests for v4 universe scoring pipeline."""

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
from margin_engine.models.scoring import ConvictionLevel, InvestmentStyle
from margin_engine.scoring.v4_pipeline import (
    V4_MAX_POSITIONS,
    TickerV4Data,
    V4ResultWithML,
    score_universe_v4,
)


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


def _make_ticker_data(
    ticker: str,
    sector=GICSSector.TECHNOLOGY,
    style: InvestmentStyle = InvestmentStyle.BLEND,
) -> TickerV4Data:
    periods = [_period(period_end=f"{yr}-12-31") for yr in range(2020, 2025)]
    return TickerV4Data(
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
        style=style,
    )


class TestScoreUniverseV4:
    def test_empty_universe_returns_empty(self):
        results = score_universe_v4([], shiller_cape=25.0)
        assert results == []

    def test_single_ticker_scores(self):
        """One ticker runs through all three tracks, produces V4ResultWithML."""
        data = [_make_ticker_data("AAPL")]
        results = score_universe_v4(data, shiller_cape=25.0)
        assert len(results) == 1
        r = results[0]
        assert isinstance(r, V4ResultWithML)
        assert r.ticker == "AAPL"
        assert r.track_a is not None
        assert r.track_b is not None
        assert r.track_c is not None
        assert r.style == InvestmentStyle.BLEND
        assert r.conviction is not None
        assert r.rules_conviction is not None
        assert r.ml_override == "none"  # no ML predictions provided
        assert r.ml_alpha is None
        assert r.ml_confidence is None

    def test_results_sorted_by_conviction(self):
        """Results are sorted by conviction order then max_position_pct descending."""
        data = [_make_ticker_data(f"T{i:02d}") for i in range(5)]
        results = score_universe_v4(data, shiller_cape=25.0)
        assert len(results) == 5
        # Verify sort order: conviction order should be non-decreasing
        conviction_order = {
            ConvictionLevel.EXCEPTIONAL: 0,
            ConvictionLevel.HIGH: 1,
            ConvictionLevel.MEDIUM: 2,
            ConvictionLevel.NONE: 3,
        }
        for i in range(len(results) - 1):
            curr_ord = conviction_order[results[i].conviction]
            next_ord = conviction_order[results[i + 1].conviction]
            if curr_ord == next_ord:
                assert results[i].max_position_pct >= results[i + 1].max_position_pct
            else:
                assert curr_ord <= next_ord

    def test_ml_predictions_applied(self):
        """With model_qualifies=False, ML has no effect."""
        data = [_make_ticker_data("TEST")]
        ml_preds = {
            "model_qualifies": False,
            "alphas": {"TEST": 0.5},
            "vae_means": {"TEST": 0.3},
            "vae_variances": {"TEST": 0.1},
        }
        results = score_universe_v4(data, shiller_cape=25.0, ml_predictions=ml_preds)
        assert len(results) == 1
        r = results[0]
        # model_qualifies=False => no override
        assert r.ml_override == "none"
        assert r.conviction == r.rules_conviction

    def test_position_cap_enforced(self):
        """55 tickers, last 5 get 0% position."""
        data = [_make_ticker_data(f"T{i:03d}") for i in range(55)]
        results = score_universe_v4(data, shiller_cape=25.0)
        assert len(results) == 55
        positioned = [r for r in results if r.max_position_pct > 0]
        assert len(positioned) <= V4_MAX_POSITIONS

    def test_growth_ticker_gets_track_c(self):
        """GROWTH-style ticker enters Track C."""
        data = [_make_ticker_data("GROW", style=InvestmentStyle.GROWTH)]
        results = score_universe_v4(data, shiller_cape=25.0)
        assert len(results) == 1
        r = results[0]
        assert r.style == InvestmentStyle.GROWTH
        # Track C should be the efficient_growth track (not a NONE placeholder)
        assert r.track_c.track == "efficient_growth"
        # Track C was actually run, so it has some score
        assert r.track_c.total_gates == 4

    def test_non_growth_ticker_skips_track_c(self):
        """BLEND/VALUE ticker gets NONE Track C."""
        for style in [InvestmentStyle.BLEND, InvestmentStyle.VALUE]:
            data = [_make_ticker_data("NONG", style=style)]
            results = score_universe_v4(data, shiller_cape=25.0)
            assert len(results) == 1
            r = results[0]
            assert r.style == style
            # Track C should be a NONE placeholder
            assert r.track_c.track == "efficient_growth"
            assert r.track_c.qualifies is False
            assert r.track_c.conviction == ConvictionLevel.NONE

    def test_three_tickers_mixed_styles(self):
        """Mix of GROWTH, BLEND, VALUE tickers all score correctly."""
        data = [
            _make_ticker_data("GRW", style=InvestmentStyle.GROWTH),
            _make_ticker_data("BLN", style=InvestmentStyle.BLEND),
            _make_ticker_data("VAL", style=InvestmentStyle.VALUE),
        ]
        results = score_universe_v4(data, shiller_cape=25.0)
        assert len(results) == 3
        styles = {r.ticker: r.style for r in results}
        assert styles["GRW"] == InvestmentStyle.GROWTH
        assert styles["BLN"] == InvestmentStyle.BLEND
        assert styles["VAL"] == InvestmentStyle.VALUE

    def test_composite_score_equals_max_qualifying_track_score(self):
        """composite_score equals the max score among qualifying tracks."""
        data = [_make_ticker_data("AAPL")]
        results = score_universe_v4(data, shiller_cape=25.0)
        assert len(results) == 1
        r = results[0]
        # composite_score should always equal the max of the qualifying track scores
        expected_scores = []
        if r.track_a.qualifies:
            expected_scores.append(r.track_a.score)
        if r.track_b.qualifies:
            expected_scores.append(r.track_b.score)
        if r.track_c.qualifies:
            expected_scores.append(r.track_c.score)
        expected = max(expected_scores) if expected_scores else 0.0
        assert r.composite_score == expected

    def test_composite_score_reflects_qualifying_track(self):
        """composite_score is set from the winning qualifying track score, not left at 0."""
        data = [_make_ticker_data("TEST")]
        results = score_universe_v4(data, shiller_cape=25.0)
        r = results[0]
        # Directly verify the relationship: composite_score = max of qualifying track scores
        qualifying_scores = [t.score for t in [r.track_a, r.track_b, r.track_c] if t.qualifies]
        if qualifying_scores:
            assert r.composite_score == max(qualifying_scores)
            assert r.composite_score > 0.0
        else:
            # No track qualifies => composite is 0.0 (which is correct)
            assert r.composite_score == 0.0

        # Also verify the V4ResultWithML model accepts composite_score properly
        patched = r.model_copy(update={"composite_score": 75.5})
        assert patched.composite_score == 75.5

    def test_optimize_true_retains_all_positions(self):
        """optimize=True: positions are not zeroed by the portfolio cap step."""
        data = [_make_ticker_data(f"T{i:03d}") for i in range(55)]
        results_opt = score_universe_v4(data, shiller_cape=25.0, optimize=True)
        results_no_opt = score_universe_v4(data, shiller_cape=25.0, optimize=False)
        assert len(results_opt) == 55
        assert len(results_no_opt) == 55
        # optimize=True should never produce a *lower* position than optimize=False
        opt_positions = {r.ticker: r.max_position_pct for r in results_opt}
        no_opt_positions = {r.ticker: r.max_position_pct for r in results_no_opt}
        for ticker in opt_positions:
            assert opt_positions[ticker] >= no_opt_positions[ticker]
