"""Tests for market pulse schemas."""

from margin_api.schemas.thirteenf import ConsensusPick, MarketPulseResponse, SectorFlowItem


def test_market_pulse_schema_defaults():
    """MarketPulseResponse can be constructed with empty data."""
    resp = MarketPulseResponse(
        breadth_pct=0.0,
        breadth_direction="flat",
        sector_flows=[],
        consensus_picks=[],
        flow_trend_pct=0.0,
        flow_trend_direction="flat",
        as_of_quarter="Q1 2026",
    )
    assert resp.breadth_pct == 0.0
    assert resp.sector_flows == []
    assert resp.consensus_picks == []


def test_market_pulse_schema_with_data():
    """MarketPulseResponse with populated fields."""
    resp = MarketPulseResponse(
        breadth_pct=62.5,
        breadth_direction="up",
        sector_flows=[
            SectorFlowItem(sector="Technology", net_shares=150000, direction="up"),
        ],
        consensus_picks=[
            ConsensusPick(ticker="AAPL", curated_holders=12, agreement_pct=48.0),
        ],
        flow_trend_pct=8.3,
        flow_trend_direction="up",
        as_of_quarter="Q1 2026",
    )
    assert resp.breadth_pct == 62.5
    assert len(resp.sector_flows) == 1
    assert resp.sector_flows[0].sector == "Technology"
    assert len(resp.consensus_picks) == 1
    assert resp.consensus_picks[0].ticker == "AAPL"
