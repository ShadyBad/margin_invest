"""Tests for 13F holdings API response schemas."""

from datetime import date

from margin_api.schemas.thirteenf import (
    ChangesSummary,
    ClonePerformance,
    ClonePosition,
    CloneResponse,
    CrowdedTrade,
    HolderResponse,
    HoldingsHistoryQuarter,
    HoldingsHistoryResponse,
    HoldingsResponse,
    HoldingsSummary,
    ManagerPortfolioResponse,
    ManagerResponse,
    NewPositionEntry,
    NewPositionResponse,
    OverlapEntry,
    OverlapResponse,
    PortfolioHolding,
)


def test_holdings_response_serialization():
    """Full nested HoldingsResponse serializes correctly via model_dump()."""
    holder = HolderResponse(
        manager_name="Berkshire Hathaway",
        tier="god_tier",
        shares_held=1_000_000,
        value_millions=150.5,
        shares_changed=50_000,
        pct_portfolio=2.3,
        is_new_position=False,
        quarters_held=12,
    )
    summary = HoldingsSummary(
        total_holders=45,
        curated_holders=8,
        net_shares_changed=200_000,
        signal_score=0.85,
    )
    resp = HoldingsResponse(
        ticker="AAPL",
        period_of_report=date(2025, 12, 31),
        curated_holders=[holder],
        other_holders=[],
        summary=summary,
    )
    data = resp.model_dump()
    assert data["ticker"] == "AAPL"
    assert data["period_of_report"] == date(2025, 12, 31)
    assert len(data["curated_holders"]) == 1
    assert data["curated_holders"][0]["manager_name"] == "Berkshire Hathaway"
    assert data["curated_holders"][0]["quarters_held"] == 12
    assert data["other_holders"] == []
    assert data["summary"]["signal_score"] == 0.85
    assert data["summary"]["curated_holders"] == 8


def test_manager_response():
    """ManagerResponse has all expected fields."""
    mgr = ManagerResponse(
        id=1,
        name="Renaissance Technologies",
        tier="quant_legend",
        aum_millions=130_000.0,
        total_holdings=3500,
        top_positions=["AAPL", "MSFT", "GOOG"],
        last_filing=date(2026, 2, 14),
        period_of_report=date(2025, 12, 31),
    )
    assert mgr.id == 1
    assert mgr.name == "Renaissance Technologies"
    assert mgr.tier == "quant_legend"
    assert mgr.aum_millions == 130_000.0
    assert mgr.total_holdings == 3500
    assert mgr.top_positions == ["AAPL", "MSFT", "GOOG"]
    assert mgr.last_filing == date(2026, 2, 14)
    assert mgr.period_of_report == date(2025, 12, 31)


def test_manager_portfolio_response():
    """ManagerPortfolioResponse with PortfolioHolding and ChangesSummary."""
    holding = PortfolioHolding(
        ticker="NVDA",
        cusip="67066G104",
        shares_held=500_000,
        value_millions=60.0,
        pct_portfolio=4.5,
        shares_changed=100_000,
        is_new_position=True,
    )
    changes = ChangesSummary(
        new_positions=["NVDA", "TSLA"],
        exited_positions=["META"],
        increased=10,
        decreased=5,
        unchanged=20,
    )
    resp = ManagerPortfolioResponse(
        manager="Bridgewater Associates",
        period_of_report=date(2025, 12, 31),
        aum_millions=150_000.0,
        holdings=[holding],
        changes_summary=changes,
    )
    data = resp.model_dump()
    assert data["manager"] == "Bridgewater Associates"
    assert len(data["holdings"]) == 1
    assert data["holdings"][0]["is_new_position"] is True
    assert data["holdings"][0]["cusip"] == "67066G104"
    assert data["changes_summary"]["new_positions"] == ["NVDA", "TSLA"]
    assert data["changes_summary"]["exited_positions"] == ["META"]
    assert data["changes_summary"]["increased"] == 10


def test_overlap_response():
    """OverlapResponse with OverlapEntry and CrowdedTrade."""
    overlap = OverlapEntry(ticker="AAPL", holder_count=30, curated_count=8)
    crowded = CrowdedTrade(ticker="PLTR", new_position_count=5, pct_funds_adding=0.25)
    resp = OverlapResponse(
        period_of_report=date(2025, 12, 31),
        most_held=[overlap],
        crowded_trades=[crowded],
    )
    data = resp.model_dump()
    assert data["most_held"][0]["ticker"] == "AAPL"
    assert data["most_held"][0]["curated_count"] == 8
    assert data["crowded_trades"][0]["pct_funds_adding"] == 0.25
    assert data["crowded_trades"][0]["new_position_count"] == 5


def test_new_position_response():
    """NewPositionResponse with NewPositionEntry."""
    entry = NewPositionEntry(
        ticker="SMCI",
        managers=["Soros Fund Management", "Tiger Global"],
        total_new_funds=12,
        curated_new_funds=3,
        total_value_millions=450.0,
    )
    resp = NewPositionResponse(
        period_of_report=date(2025, 12, 31),
        new_positions=[entry],
    )
    data = resp.model_dump()
    assert len(data["new_positions"]) == 1
    assert data["new_positions"][0]["ticker"] == "SMCI"
    assert data["new_positions"][0]["managers"] == ["Soros Fund Management", "Tiger Global"]
    assert data["new_positions"][0]["curated_new_funds"] == 3
    assert data["new_positions"][0]["total_value_millions"] == 450.0


def test_clone_response():
    """CloneResponse with ClonePosition and ClonePerformance."""
    position = ClonePosition(ticker="AAPL", target_weight=0.15)
    perf = ClonePerformance(
        return_1y=0.32,
        cagr_3y=0.18,
        max_drawdown=-0.22,
        sharpe=1.45,
    )
    resp = CloneResponse(
        manager="Berkshire Hathaway",
        strategy="conviction_weighted",
        period_of_report=date(2025, 12, 31),
        positions=[position],
        historical_performance=perf,
    )
    data = resp.model_dump()
    assert data["manager"] == "Berkshire Hathaway"
    assert data["strategy"] == "conviction_weighted"
    assert data["positions"][0]["target_weight"] == 0.15
    assert data["historical_performance"]["sharpe"] == 1.45
    assert data["historical_performance"]["max_drawdown"] == -0.22


def test_holdings_history_response():
    """HoldingsHistoryResponse with HoldingsHistoryQuarter."""
    quarter = HoldingsHistoryQuarter(
        period="2025-Q4",
        curated_holders=8,
        total_holders=45,
        total_shares=5_000_000,
        net_change=200_000,
    )
    resp = HoldingsHistoryResponse(
        ticker="AAPL",
        quarters=[quarter],
    )
    data = resp.model_dump()
    assert data["ticker"] == "AAPL"
    assert len(data["quarters"]) == 1
    assert data["quarters"][0]["period"] == "2025-Q4"
    assert data["quarters"][0]["curated_holders"] == 8
    assert data["quarters"][0]["total_shares"] == 5_000_000
    assert data["quarters"][0]["net_change"] == 200_000


def test_optional_fields_default():
    """HolderResponse optional fields use correct defaults."""
    holder = HolderResponse(
        manager_name="Unknown Fund",
        tier="other",
        shares_held=1000,
        value_millions=0.5,
        shares_changed=0,
    )
    assert holder.pct_portfolio is None
    assert holder.is_new_position is False
    assert holder.quarters_held is None
