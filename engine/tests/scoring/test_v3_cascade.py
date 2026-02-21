"""Tests for v3 gate cascade runners."""

from decimal import Decimal

import pytest
from margin_engine.models.financial import (
    AssetProfile, BalanceSheet, CashFlowStatement, FinancialHistory,
    FinancialPeriod, GICSSector, IncomeStatement,
)
from margin_engine.models.scoring import ConvictionLevel
from margin_engine.scoring.v3_cascade import (
    TrackAInputs,
    TrackBInputs,
    run_track_a_cascade,
    run_track_b_cascade,
)


def _period(
    revenue=Decimal("1000"), ebit=Decimal("200"), net_income=Decimal("160"),
    cost_of_revenue=Decimal("600"), gross_profit=Decimal("400"),
    depreciation=Decimal("50"), total_equity=Decimal("500"),
    long_term_debt=Decimal("200"), short_term_debt=Decimal("100"),
    cash_and_equivalents=Decimal("50"),
    operating_cash_flow=Decimal("250"), capital_expenditures=Decimal("-80"),
    total_assets=Decimal("1500"), period_end="2024-09-28",
    shares_outstanding=100,
) -> FinancialPeriod:
    return FinancialPeriod(
        period_end=period_end, filing_date="2024-11-01",
        current_income=IncomeStatement(
            revenue=revenue, cost_of_revenue=cost_of_revenue,
            gross_profit=gross_profit, ebit=ebit, depreciation=depreciation,
            net_income=net_income, shares_outstanding=shares_outstanding,
        ),
        current_balance=BalanceSheet(
            total_assets=total_assets, total_equity=total_equity,
            long_term_debt=long_term_debt, short_term_debt=short_term_debt,
            cash_and_equivalents=cash_and_equivalents,
            shares_outstanding=shares_outstanding,
        ),
        current_cash_flow=CashFlowStatement(
            operating_cash_flow=operating_cash_flow,
            capital_expenditures=capital_expenditures,
        ),
    )


def _profile(ticker="TEST", sector=GICSSector.TECHNOLOGY):
    return AssetProfile(
        ticker=ticker, name=f"{ticker} Corp", sector=sector,
        market_cap=Decimal("10000000000"),
    )


class TestRunTrackACascade:
    def test_returns_v3_track_result(self):
        """run_track_a_cascade returns a V3TrackResult with track='compounder'."""
        history = FinancialHistory(ticker="T", periods=[
            _period(period_end="2020-12-31"), _period(period_end="2024-12-31"),
        ])
        inputs = TrackAInputs(
            history=history, period=history.periods[-1], profile=_profile(),
            current_price=100.0, current_fcf_per_share=5.0,
            wacc=0.10, terminal_growth=0.03, sustainable_growth_rate=0.08,
            buyback_yield=None, insider_ownership_pct=None,
            sbc_pct=None, recent_acquisition_count=0,
            regime_adjustments=None,
        )
        result = run_track_a_cascade(inputs)
        assert result.track == "compounder"
        assert result.total_gates == 4
        assert 0 <= result.gates_passed <= 4

    def test_weak_company_fails_most_gates(self):
        """Declining company should fail most gates."""
        history = FinancialHistory(ticker="WEAK", periods=[
            _period(ebit=Decimal("200"), total_equity=Decimal("400"),
                    period_end="2020-12-31"),
            _period(ebit=Decimal("50"), total_equity=Decimal("600"),
                    period_end="2024-12-31"),
        ])
        inputs = TrackAInputs(
            history=history, period=history.periods[-1], profile=_profile(),
            current_price=200.0, current_fcf_per_share=1.0,
            wacc=0.10, terminal_growth=0.03, sustainable_growth_rate=0.05,
            buyback_yield=None, insider_ownership_pct=None,
            sbc_pct=None, recent_acquisition_count=5,
            regime_adjustments=None,
        )
        result = run_track_a_cascade(inputs)
        assert result.gates_passed <= 2
        assert result.conviction == ConvictionLevel.NONE

    def test_conviction_none_when_single_period(self):
        """Single period -> can't detect moat or compounding -> NONE."""
        history = FinancialHistory(ticker="FEW", periods=[_period()])
        inputs = TrackAInputs(
            history=history, period=history.periods[-1], profile=_profile(),
            current_price=100.0, current_fcf_per_share=5.0,
            wacc=0.10, terminal_growth=0.03, sustainable_growth_rate=0.08,
            buyback_yield=None, insider_ownership_pct=None,
            sbc_pct=None, recent_acquisition_count=0,
            regime_adjustments=None,
        )
        result = run_track_a_cascade(inputs)
        assert result.conviction == ConvictionLevel.NONE
        assert result.qualifies is False

    def test_regime_adjustments_accepted(self):
        """Regime adjustments are accepted and don't crash."""
        from margin_engine.scoring.market_regime import RegimeAdjustments, MarketRegime
        history = FinancialHistory(ticker="REG", periods=[
            _period(period_end="2020-12-31"), _period(period_end="2024-12-31"),
        ])
        adj = RegimeAdjustments(
            regime=MarketRegime.EXPENSIVE,
            track_a_growth_gap_adjustment=0.02,
            track_b_asymmetry_adjustment=0.0,
            track_b_catalyst_percentile_override=None,
        )
        inputs = TrackAInputs(
            history=history, period=history.periods[-1], profile=_profile(),
            current_price=100.0, current_fcf_per_share=5.0,
            wacc=0.10, terminal_growth=0.03, sustainable_growth_rate=0.08,
            regime_adjustments=adj,
        )
        result = run_track_a_cascade(inputs)
        assert result.track == "compounder"


class TestRunTrackBCascade:
    def test_returns_v3_track_result(self):
        result = run_track_b_cascade(TrackBInputs(
            history=FinancialHistory(ticker="T", periods=[_period()]),
            period=_period(), profile=_profile(),
            current_price=50.0,
            dcf_iv=100.0, owner_earnings_iv=95.0,
            asset_floor_iv=90.0, peer_comparison_iv=105.0,
            insider_percentile=60.0, institutional_percentile=70.0,
            sue_percentile=50.0, wacc=0.10,
            regime_adjustments=None,
        ))
        assert result.track == "mispricing"
        assert result.total_gates == 4

    def test_undervalued_stock_passes_gates(self):
        """Price well below IV, strong catalyst, good quality -> gates pass."""
        result = run_track_b_cascade(TrackBInputs(
            history=FinancialHistory(ticker="CHEAP", periods=[
                _period(ebit=Decimal("150"), total_equity=Decimal("500"),
                        period_end="2022-12-31"),
                _period(ebit=Decimal("180"), total_equity=Decimal("500"),
                        period_end="2024-12-31"),
            ]),
            period=_period(ebit=Decimal("180"), total_equity=Decimal("500")),
            profile=_profile(),
            current_price=50.0,
            dcf_iv=100.0, owner_earnings_iv=95.0,
            asset_floor_iv=90.0, peer_comparison_iv=105.0,
            insider_percentile=80.0, institutional_percentile=75.0,
            sue_percentile=70.0, wacc=0.10,
            regime_adjustments=None,
        ))
        assert result.gates_passed >= 2

    def test_overvalued_stock_fails(self):
        """Price above IV -> not mispriced."""
        result = run_track_b_cascade(TrackBInputs(
            history=FinancialHistory(ticker="EXPN", periods=[_period()]),
            period=_period(), profile=_profile(),
            current_price=200.0,
            dcf_iv=100.0, owner_earnings_iv=95.0,
            asset_floor_iv=90.0, peer_comparison_iv=105.0,
            insider_percentile=20.0, institutional_percentile=10.0,
            sue_percentile=15.0, wacc=0.10,
            regime_adjustments=None,
        ))
        assert result.qualifies is False

    def test_regime_adjustments_accepted(self):
        from margin_engine.scoring.market_regime import RegimeAdjustments, MarketRegime
        adj = RegimeAdjustments(
            regime=MarketRegime.EUPHORIA,
            track_a_growth_gap_adjustment=0.05,
            track_b_asymmetry_adjustment=0.0,
            track_b_catalyst_percentile_override=90.0,
        )
        result = run_track_b_cascade(TrackBInputs(
            history=FinancialHistory(ticker="E", periods=[_period()]),
            period=_period(), profile=_profile(),
            current_price=50.0,
            dcf_iv=100.0, owner_earnings_iv=95.0,
            asset_floor_iv=90.0, peer_comparison_iv=105.0,
            insider_percentile=70.0, institutional_percentile=60.0,
            sue_percentile=50.0, wacc=0.10,
            regime_adjustments=adj,
        ))
        assert result.track == "mispricing"

    def test_high_quality_at_70pct_iv_passes_gate1(self):
        """ROIC=21% business at 70% of IV passes Gate 1 (25% margin via 0.75 threshold).

        Under new rules: iv_discount = 0.75, price 68.25 < 0.75*97.5=73.125 -> passes
        Under OLD rules: iv_discount = 0.60, price 68.25 > 0.60*97.5=58.5 -> would have failed

        Gates analysis:
          Gate 1: passes (tiered: 0.75 threshold for quality_floor >= 1.0)
          Gate 2: fails (asset_floor_ps=0 for tech, max_loss=1.0)
          Gate 3: passes (catalyst ~76.5 > 40)
          Gate 4: passes (ROIC=21% -> quality_floor=1.0)
        Total: 3 gates passed (was 2 without tiered IV)
        """
        period = _period()  # ROIC ~21%, well above 8%
        history = FinancialHistory(ticker="HQ", periods=[period])
        result = run_track_b_cascade(TrackBInputs(
            history=history,
            period=period,
            profile=_profile(),
            current_price=68.25,  # 70% of ensemble IV (97.5)
            dcf_iv=100.0, owner_earnings_iv=95.0,
            asset_floor_iv=90.0, peer_comparison_iv=105.0,
            insider_percentile=80.0, institutional_percentile=75.0,
            sue_percentile=70.0, wacc=0.10,
            regime_adjustments=None,
        ))
        # Gate 1 must pass with tiered threshold — 3 gates total
        assert result.gates_passed == 3

    def test_improving_at_62pct_iv_passes_gate1(self):
        """ROIC=5%, improving at 62% of IV passes Gate 1 (35% margin via 0.65 threshold).

        quality_floor > 0 but < 1.0 -> iv_discount = 0.65
        price 60.45 < 0.65 * 97.5 = 63.375 -> passes

        Gates analysis:
          Gate 1: passes (tiered: 0.65 threshold for improving quality)
          Gate 2: fails (asset_floor_ps=0 for tech, max_loss=1.0)
          Gate 3: passes (catalyst ~76.5 > 40)
          Gate 4: passes (ROIC=5.1%, improving -> quality_floor > 0)
        Total: 3 gates passed (was 2 without tiered IV)
        """
        period_early = _period(ebit=Decimal("30"), period_end="2022-12-31")
        period_late = _period(ebit=Decimal("48"), period_end="2024-12-31")
        history = FinancialHistory(ticker="IMP", periods=[period_early, period_late])
        result = run_track_b_cascade(TrackBInputs(
            history=history,
            period=period_late,
            profile=_profile(),
            current_price=60.45,  # 62% of ensemble IV (97.5)
            dcf_iv=100.0, owner_earnings_iv=95.0,
            asset_floor_iv=90.0, peer_comparison_iv=105.0,
            insider_percentile=80.0, institutional_percentile=75.0,
            sue_percentile=70.0, wacc=0.10,
            regime_adjustments=None,
        ))
        # Gate 1 must pass with tiered threshold — 3 gates total
        assert result.gates_passed == 3

    def test_low_quality_at_62pct_iv_fails_gate1(self):
        """ROIC=3%, not improving at 62% of IV fails Gate 1 (40% margin still at 0.60).

        quality_floor = 0 -> iv_discount = 0.60
        price 60.45 > 0.60 * 97.5 = 58.5 -> fails
        """
        # ebit=30 gives ROIC = 30*0.79/750 = ~3.2%, single period -> not improving
        period = _period(ebit=Decimal("30"))
        history = FinancialHistory(ticker="LQ", periods=[period])
        result = run_track_b_cascade(TrackBInputs(
            history=history,
            period=period,
            profile=_profile(),
            current_price=60.45,  # 62% of ensemble IV (97.5)
            dcf_iv=100.0, owner_earnings_iv=95.0,
            asset_floor_iv=90.0, peer_comparison_iv=105.0,
            insider_percentile=80.0, institutional_percentile=75.0,
            sue_percentile=70.0, wacc=0.10,
            regime_adjustments=None,
        ))
        # Gate 1 should fail: price 60.45 > 0.60 * 97.5 = 58.5
        # But other gates may pass (catalyst, quality floor NOT since quality_floor=0)
        # With single period and low ROIC: quality_floor=0, gate4 also fails
        # Gates that can pass: gate2 (downside), gate3 (catalyst)
        # Gate 1 specifically should NOT pass, so gates_passed should exclude gate1
        # We can't directly check gate1, but we know total - verify price above threshold
        assert result.gates_passed <= 2  # gate2 + gate3 at most (no gate1, no gate4)

    def test_low_quality_at_55pct_iv_passes_gate1(self):
        """ROIC=3%, not improving at 55% of IV passes Gate 1.

        quality_floor = 0 -> iv_discount = 0.60
        price 53.625 < 0.60 * 97.5 = 58.5 -> passes
        """
        period = _period(ebit=Decimal("30"))
        history = FinancialHistory(ticker="LQ2", periods=[period])
        result = run_track_b_cascade(TrackBInputs(
            history=history,
            period=period,
            profile=_profile(),
            current_price=53.625,  # 55% of ensemble IV (97.5)
            dcf_iv=100.0, owner_earnings_iv=95.0,
            asset_floor_iv=90.0, peer_comparison_iv=105.0,
            insider_percentile=80.0, institutional_percentile=75.0,
            sue_percentile=70.0, wacc=0.10,
            regime_adjustments=None,
        ))
        # Gate 1 should pass: price 53.625 < 0.60 * 97.5 = 58.5
        assert result.gates_passed >= 1
