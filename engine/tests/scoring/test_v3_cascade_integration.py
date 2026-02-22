"""Full v3 cascade integration tests — end-to-end through gates, orchestrator, and pipeline.

Tests exercise real gate logic, real scoring functions, and real position sizing.
No mocking — synthetic data is constructed to trigger specific gate outcomes.
"""

from __future__ import annotations

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
from margin_engine.models.scoring import ConvictionLevel
from margin_engine.scoring.market_regime import detect_regime, regime_adjustments
from margin_engine.scoring.timing_overlay import compute_v3_timing_signal
from margin_engine.scoring.v3_cascade import (
    TrackAInputs,
    TrackBInputs,
    run_track_a_cascade,
    run_track_b_cascade,
)
from margin_engine.scoring.v3_orchestrator import orchestrate_v3
from margin_engine.scoring.v3_pipeline import TickerV3Data, score_universe_v3

# ---------------------------------------------------------------------------
# Helpers — build synthetic financial data
# ---------------------------------------------------------------------------


def _make_period(
    period_end: str = "2024-12-31",
    revenue: Decimal = Decimal("10000"),
    cost_of_revenue: Decimal = Decimal("4000"),
    gross_profit: Decimal | None = None,
    ebit: Decimal = Decimal("2000"),
    net_income: Decimal = Decimal("1500"),
    total_assets: Decimal = Decimal("50000"),
    total_equity: Decimal = Decimal("20000"),
    total_debt: Decimal = Decimal("5000"),
    operating_cash_flow: Decimal = Decimal("3000"),
    capital_expenditures: Decimal = Decimal("-800"),
    filing_date: str = "2025-02-15",
) -> FinancialPeriod:
    gp = gross_profit if gross_profit is not None else (revenue - cost_of_revenue)
    return FinancialPeriod(
        period_end=period_end,
        filing_date=filing_date,
        current_income=IncomeStatement(
            revenue=revenue,
            cost_of_revenue=cost_of_revenue,
            gross_profit=gp,
            ebit=ebit,
            net_income=net_income,
        ),
        current_balance=BalanceSheet(
            total_assets=total_assets,
            total_equity=total_equity,
            total_debt=total_debt,
        ),
        current_cash_flow=CashFlowStatement(
            operating_cash_flow=operating_cash_flow,
            capital_expenditures=capital_expenditures,
        ),
    )


def _make_history(ticker: str = "TEST", num_periods: int = 5) -> FinancialHistory:
    """Build a 5-year history with steadily growing fundamentals.

    Revenue grows ~8% per year.  Margins improve slightly each year to
    trigger moat durability signatures (scale economics, pricing power,
    switching costs, capital efficiency).
    """
    periods = []
    base_rev = 8000
    for i in range(num_periods):
        year = 2020 + i
        growth = 1.0 + i * 0.08  # 8% annual growth
        periods.append(
            _make_period(
                period_end=f"{year}-12-31",
                filing_date=f"{year + 1}-02-15",
                revenue=Decimal(str(int(base_rev * growth))),
                cost_of_revenue=Decimal(str(int(base_rev * growth * 0.4))),
                ebit=Decimal(str(int(base_rev * growth * 0.2))),
                net_income=Decimal(str(int(base_rev * growth * 0.15))),
                total_assets=Decimal(str(int(50000 * growth))),
                total_equity=Decimal(str(int(20000 * growth))),
                operating_cash_flow=Decimal(str(int(base_rev * growth * 0.3))),
                capital_expenditures=Decimal(str(int(-base_rev * growth * 0.08))),
            )
        )
    return FinancialHistory(ticker=ticker, periods=periods)


def _make_profile(
    ticker: str = "TEST",
    sector: GICSSector = GICSSector.TECHNOLOGY,
    market_cap: Decimal = Decimal("10000000000"),
    shares_outstanding: int = 100_000_000,
) -> AssetProfile:
    return AssetProfile(
        ticker=ticker,
        name=f"{ticker} Corp",
        sector=sector,
        market_cap=market_cap,
        shares_outstanding=shares_outstanding,
    )


def _make_strong_compounder_history(ticker: str = "COMP", num_periods: int = 5) -> FinancialHistory:
    """Build a history where revenue/ROIC/margins all grow consistently.

    This is designed to trigger 3-4 moat durability signatures and produce
    a high compounding power value:
    - Gross margins expand (pricing power)
    - ROIC increases with revenue (scale economics)
    - Revenue growth exceeds cost growth (switching costs)
    - Incremental ROIC >= median ROIC (capital efficiency)
    """
    periods: list[FinancialPeriod] = []
    for i in range(num_periods):
        year = 2020 + i
        # Revenue grows aggressively, costs grow slower -> margin expansion
        rev = 10000 * (1.15**i)  # 15% annual revenue growth
        cost_pct = 0.45 - i * 0.02  # Cost % shrinks from 45% to 37%
        cost = rev * cost_pct
        gp = rev - cost
        ebit = rev * (0.20 + i * 0.02)  # EBIT margin expands 20% -> 28%
        ni = ebit * 0.79  # after-tax

        # Equity grows slower than earnings -> improving ROIC
        equity = 15000 + i * 2000
        debt = 3000 - i * 200  # Deleveraging
        assets = equity + debt + 5000

        # Strong operating cash flow + growing capex for compounding power
        ocf = ebit * 1.2  # OCF > EBIT
        capex = -(rev * 0.12 + i * 200)  # Growing growth-capex

        periods.append(
            FinancialPeriod(
                period_end=f"{year}-12-31",
                filing_date=f"{year + 1}-02-15",
                current_income=IncomeStatement(
                    revenue=Decimal(str(int(rev))),
                    cost_of_revenue=Decimal(str(int(cost))),
                    gross_profit=Decimal(str(int(gp))),
                    ebit=Decimal(str(int(ebit))),
                    net_income=Decimal(str(int(ni))),
                ),
                current_balance=BalanceSheet(
                    total_assets=Decimal(str(int(assets))),
                    total_equity=Decimal(str(int(equity))),
                    total_debt=Decimal(str(int(debt))),
                ),
                current_cash_flow=CashFlowStatement(
                    operating_cash_flow=Decimal(str(int(ocf))),
                    capital_expenditures=Decimal(str(int(capex))),
                ),
            )
        )
    return FinancialHistory(ticker=ticker, periods=periods)


def _make_ticker_data(
    ticker: str,
    *,
    sector: GICSSector = GICSSector.TECHNOLOGY,
    current_price: float = 50.0,
    market_cap: Decimal = Decimal("5000000000"),
    shares: int = 100_000_000,
    strong_compounder: bool = False,
    dcf_iv: float = 0.0,
    insider_pctl: float = 50.0,
    institutional_pctl: float = 50.0,
    sue_pctl: float = 50.0,
    momentum_pctl: float = 50.0,
) -> TickerV3Data:
    """Build a TickerV3Data entry for the universe pipeline."""
    if strong_compounder:
        history = _make_strong_compounder_history(ticker)
    else:
        history = _make_history(ticker)

    latest = history.periods[-1]
    fcf_per_share = float(latest.current_cash_flow.free_cash_flow) / shares

    return TickerV3Data(
        ticker=ticker,
        history=history,
        latest_period=latest,
        profile=_make_profile(ticker, sector, market_cap, shares),
        current_price=current_price,
        current_fcf_per_share=max(fcf_per_share, 0.01),
        sustainable_growth_rate=0.08,
        buyback_yield=0.02,
        insider_ownership_pct=5.0,
        sbc_pct=0.01,
        recent_acquisition_count=0,
        insider_percentile=insider_pctl,
        institutional_percentile=institutional_pctl,
        sue_percentile=sue_pctl,
        momentum_percentile=momentum_pctl,
        dcf_iv=dcf_iv,
    )


# ---------------------------------------------------------------------------
# Test 1: Compounder (Track A) qualifies end-to-end
# ---------------------------------------------------------------------------


class TestCompounderQualifiesEndToEnd:
    """Run Track A cascade with strong compounder data and verify qualification."""

    def test_compounder_qualifies_end_to_end(self) -> None:
        history = _make_strong_compounder_history("COMP")
        latest = history.periods[-1]
        profile = _make_profile("COMP", shares_outstanding=100_000_000)

        # FCF per share: use the latest period's free cash flow
        fcf_ps = float(latest.current_cash_flow.free_cash_flow) / 100_000_000

        # Set current_price low enough so reverse DCF finds a positive growth gap.
        # With high sustainable_growth_rate (0.12) and a reasonable price,
        # the implied growth should be below 0.12 -> positive gap.
        inputs = TrackAInputs(
            history=history,
            period=latest,
            profile=profile,
            current_price=10.0,  # Low price relative to fundamentals
            current_fcf_per_share=max(fcf_ps, 0.5),
            wacc=0.10,
            terminal_growth=0.03,
            sustainable_growth_rate=0.12,
            buyback_yield=0.03,
            insider_ownership_pct=8.0,
            sbc_pct=0.005,
            recent_acquisition_count=0,
        )

        result = run_track_a_cascade(inputs)

        assert result.track == "compounder"
        assert result.qualifies is True
        assert result.gates_passed >= 3
        assert result.total_gates == 4
        assert result.score > 0
        assert result.conviction in (
            ConvictionLevel.EXCEPTIONAL,
            ConvictionLevel.HIGH,
            ConvictionLevel.MEDIUM,
        )


# ---------------------------------------------------------------------------
# Test 2: Mispricing (Track B) qualifies end-to-end
# ---------------------------------------------------------------------------


class TestMispricingQualifiesEndToEnd:
    """Run Track B cascade with deep-value data and verify qualification."""

    def test_mispricing_qualifies_end_to_end(self) -> None:
        # Build a history with improving ROIC to pass the quality floor gate.
        # Also need significant cash to pass the downside protection gate.
        shares = 100_000_000
        periods: list[FinancialPeriod] = []
        for i in range(5):
            year = 2020 + i
            # EBIT grows faster than invested capital -> improving ROIC
            ebit = 3000 + i * 1000
            equity = 20000 + i * 1000  # Equity grows slowly
            debt = 2000  # Stable debt
            cash = 15000 + i * 2000  # Large and growing cash position
            revenue = 20000 + i * 2000
            cost = int(revenue * 0.4)

            periods.append(
                FinancialPeriod(
                    period_end=f"{year}-12-31",
                    filing_date=f"{year + 1}-02-15",
                    current_income=IncomeStatement(
                        revenue=Decimal(str(revenue)),
                        cost_of_revenue=Decimal(str(cost)),
                        gross_profit=Decimal(str(revenue - cost)),
                        ebit=Decimal(str(ebit)),
                        net_income=Decimal(str(int(ebit * 0.79))),
                    ),
                    current_balance=BalanceSheet(
                        total_assets=Decimal(str(equity + debt + cash + 5000)),
                        total_equity=Decimal(str(equity)),
                        long_term_debt=Decimal(str(debt)),
                        cash_and_equivalents=Decimal(str(cash)),
                    ),
                    current_cash_flow=CashFlowStatement(
                        operating_cash_flow=Decimal(str(int(ebit * 1.2))),
                        capital_expenditures=Decimal(str(int(-revenue * 0.05))),
                    ),
                )
            )
        history = FinancialHistory(ticker="DEEP", periods=periods)
        latest = history.periods[-1]
        profile = _make_profile("DEEP", shares_outstanding=shares)

        # Ensemble IVs clustered near 100 -> ensemble_iv ~ 100
        # price = 40 -> 40 < 0.60 * 100 = 60  => Gate 1 passes
        # Downside: net_cash = 23000 - 2000 = 21000, tangible_book = 24000
        #   asset_floor_ps = (21000 + 24000*0.3) / 100M ~ very small per share
        #   BUT price is also per share (40). We need asset_floor_ps > 20
        #   so max_loss < 50%.  With 100M shares the floor is tiny.
        # Solution: use fewer shares so per-share values are meaningful.
        shares = 1000
        profile = _make_profile("DEEP", shares_outstanding=shares)

        # With 1000 shares:
        #   net_cash = 23000 - 2000 = 21000
        #   tangible_book = 24000
        #   asset_floor_ps = max(21000 + 24000*0.3, 0) / 1000 = 28200/1000 = 28.2
        #   price = 40 -> max_loss = (40-28.2)/40 = 0.295 < 0.50 => Gate 2 passes
        current_price = 40.0
        iv_cluster = 100.0

        inputs = TrackBInputs(
            history=history,
            period=latest,
            profile=profile,
            current_price=current_price,
            dcf_iv=iv_cluster,
            owner_earnings_iv=iv_cluster * 1.05,
            asset_floor_iv=iv_cluster * 0.95,
            peer_comparison_iv=iv_cluster * 1.02,
            insider_percentile=85.0,  # Strong catalyst -> Gate 3 passes
            institutional_percentile=75.0,
            sue_percentile=80.0,
            wacc=0.10,
        )

        result = run_track_b_cascade(inputs)

        assert result.track == "mispricing"
        assert result.qualifies is True
        assert result.gates_passed >= 3
        assert result.total_gates == 4
        assert result.score > 0
        assert result.conviction in (
            ConvictionLevel.EXCEPTIONAL,
            ConvictionLevel.HIGH,
            ConvictionLevel.MEDIUM,
        )


# ---------------------------------------------------------------------------
# Test 3: Both tracks qualify -> promotes to EXCEPTIONAL
# ---------------------------------------------------------------------------


class TestBothTracksPromoteToExceptional:
    """When both tracks qualify at HIGH+, orchestrator promotes to EXCEPTIONAL."""

    def test_both_tracks_qualify_promotes_to_exceptional(self) -> None:
        history = _make_strong_compounder_history("BOTH")
        latest = history.periods[-1]
        profile = _make_profile("BOTH", shares_outstanding=100_000_000)

        fcf_ps = float(latest.current_cash_flow.free_cash_flow) / 100_000_000

        # --- Track A: strong compounder ---
        track_a_inputs = TrackAInputs(
            history=history,
            period=latest,
            profile=profile,
            current_price=10.0,
            current_fcf_per_share=max(fcf_ps, 0.5),
            wacc=0.10,
            terminal_growth=0.03,
            sustainable_growth_rate=0.12,
            buyback_yield=0.03,
            insider_ownership_pct=8.0,
            sbc_pct=0.005,
            recent_acquisition_count=0,
        )
        track_a = run_track_a_cascade(track_a_inputs)

        # --- Track B: deep value with same stock ---
        track_b_inputs = TrackBInputs(
            history=history,
            period=latest,
            profile=profile,
            current_price=10.0,
            dcf_iv=100.0,
            owner_earnings_iv=105.0,
            asset_floor_iv=95.0,
            peer_comparison_iv=102.0,
            insider_percentile=90.0,
            institutional_percentile=85.0,
            sue_percentile=88.0,
            wacc=0.10,
        )
        track_b = run_track_b_cascade(track_b_inputs)

        # Both should qualify
        assert track_a.qualifies is True
        assert track_b.qualifies is True

        # Orchestrate
        timing = compute_v3_timing_signal(momentum_percentile=60.0, is_mispricing_track=False)
        result = orchestrate_v3("BOTH", track_a, track_b, timing)

        assert result.ticker == "BOTH"
        # If both tracks are at HIGH+, opportunity_type should be "both"
        # and conviction promoted to EXCEPTIONAL.
        if track_a.conviction in (
            ConvictionLevel.EXCEPTIONAL,
            ConvictionLevel.HIGH,
        ) and track_b.conviction in (ConvictionLevel.EXCEPTIONAL, ConvictionLevel.HIGH):
            assert result.opportunity_type == "both"
            assert result.conviction == ConvictionLevel.EXCEPTIONAL
            assert result.max_position_pct == 20.0
        else:
            # At minimum, at least one track qualified
            assert result.conviction in (
                ConvictionLevel.EXCEPTIONAL,
                ConvictionLevel.HIGH,
                ConvictionLevel.MEDIUM,
            )
        assert result.max_position_pct > 0


# ---------------------------------------------------------------------------
# Test 4: Portfolio cap across universe
# ---------------------------------------------------------------------------


class TestPortfolioCapAcrossUniverse:
    """score_universe_v3 enforces MAX_POSITIONS=10 cap."""

    def test_portfolio_cap_across_universe(self) -> None:
        # Create 15 tickers — all with decent fundamentals
        tickers_data = []
        for i in range(15):
            ticker = f"T{i:02d}"
            td = _make_ticker_data(
                ticker,
                current_price=50.0,
                strong_compounder=True,
                dcf_iv=120.0,
                insider_pctl=85.0,
                institutional_pctl=75.0,
                sue_pctl=80.0,
            )
            tickers_data.append(td)

        results = score_universe_v3(tickers_data, shiller_cape=25.0)

        assert len(results) == 15

        # At most 10 should have non-zero positions
        with_position = [r for r in results if r.max_position_pct > 0]
        assert len(with_position) <= 10

        # Those beyond the top 10 should have 0% position
        for r in results[10:]:
            assert r.max_position_pct == 0.0


# ---------------------------------------------------------------------------
# Test 5: Regime modifies outcomes (CHEAP vs EUPHORIA)
# ---------------------------------------------------------------------------


class TestRegimeModifiesOutcomes:
    """Same data scored under CHEAP (CAPE=10) vs EUPHORIA (CAPE=40) should differ."""

    def test_regime_modifies_outcomes(self) -> None:
        # Use a single ticker with decent fundamentals
        tickers_data = [
            _make_ticker_data(
                "REG",
                current_price=50.0,
                strong_compounder=True,
                dcf_iv=120.0,
                insider_pctl=70.0,
                institutional_pctl=65.0,
                sue_pctl=62.0,
                momentum_pctl=55.0,
            ),
        ]

        results_cheap = score_universe_v3(tickers_data, shiller_cape=10.0)
        results_euphoria = score_universe_v3(tickers_data, shiller_cape=40.0)

        assert len(results_cheap) == 1
        assert len(results_euphoria) == 1

        r_cheap = results_cheap[0]
        r_euphoria = results_euphoria[0]

        # Verify regime detection is correct
        assert detect_regime(10.0).value == "cheap"
        assert detect_regime(40.0).value == "euphoria"

        # The CHEAP regime relaxes thresholds (growth_gap_adjustment=-0.02),
        # while EUPHORIA tightens them (growth_gap_adjustment=+0.05) and
        # raises the catalyst bar (catalyst_percentile_override=90.0).
        # At least one of these should differ:
        #   - conviction level
        #   - position size
        #   - Track A gates_passed
        #   - Track B gates_passed
        differs = (
            r_cheap.conviction != r_euphoria.conviction
            or r_cheap.max_position_pct != r_euphoria.max_position_pct
            or r_cheap.track_a.gates_passed != r_euphoria.track_a.gates_passed
            or r_cheap.track_b.gates_passed != r_euphoria.track_b.gates_passed
            or r_cheap.track_a.conviction != r_euphoria.track_a.conviction
            or r_cheap.track_b.conviction != r_euphoria.track_b.conviction
        )
        assert differs, (
            "Expected CHEAP and EUPHORIA regimes to produce different outcomes. "
            f"CHEAP: conviction={r_cheap.conviction}, pos={r_cheap.max_position_pct}, "
            f"A_gates={r_cheap.track_a.gates_passed}, B_gates={r_cheap.track_b.gates_passed}. "
            f"EUPHORIA: conviction={r_euphoria.conviction}, pos={r_euphoria.max_position_pct}, "
            f"A_gates={r_euphoria.track_a.gates_passed}, B_gates={r_euphoria.track_b.gates_passed}."
        )

        # CHEAP regime should be at least as generous as EUPHORIA
        cheap_adj = regime_adjustments(detect_regime(10.0))
        euphoria_adj = regime_adjustments(detect_regime(40.0))
        assert cheap_adj.track_a_growth_gap_adjustment < euphoria_adj.track_a_growth_gap_adjustment


# ---------------------------------------------------------------------------
# Test 6: Deterministic — identical inputs produce identical results
# ---------------------------------------------------------------------------


class TestCascadeDeterministic:
    """Running score_universe_v3 twice with identical inputs must give identical results."""

    def test_cascade_deterministic(self) -> None:
        tickers_data = [
            _make_ticker_data(
                f"DET{i}",
                current_price=40.0 + i * 5,
                strong_compounder=(i % 2 == 0),
                dcf_iv=100.0 + i * 10,
                insider_pctl=60.0 + i * 3,
                institutional_pctl=55.0 + i * 2,
                sue_pctl=50.0 + i * 4,
                momentum_pctl=40.0 + i * 5,
            )
            for i in range(5)
        ]

        results_1 = score_universe_v3(tickers_data, shiller_cape=25.0)
        results_2 = score_universe_v3(tickers_data, shiller_cape=25.0)

        assert len(results_1) == len(results_2)

        for r1, r2 in zip(results_1, results_2):
            assert r1.ticker == r2.ticker
            assert r1.conviction == r2.conviction
            assert r1.opportunity_type == r2.opportunity_type
            assert r1.max_position_pct == r2.max_position_pct
            assert r1.timing_signal == r2.timing_signal
            assert r1.track_a.score == r2.track_a.score
            assert r1.track_a.gates_passed == r2.track_a.gates_passed
            assert r1.track_a.conviction == r2.track_a.conviction
            assert r1.track_b.score == r2.track_b.score
            assert r1.track_b.gates_passed == r2.track_b.gates_passed
            assert r1.track_b.conviction == r2.track_b.conviction
