import { describe, it, expect, vi } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
import { AssetDetailView } from "../asset-detail-view"
import type { ScoreResponse } from "@/lib/api/types"

vi.mock("@/lib/api/backtest", () => ({
  getBacktestTeaser: vi.fn().mockResolvedValue({
    ticker: "AAPL",
    model_return: 3.87,
    benchmark_return: 2.14,
    max_drawdown: 0.31,
    benchmark_max_drawdown: 0.56,
    start_date: "2006-01-01",
    end_date: "2025-12-31",
  }),
}))

vi.mock("@/lib/api/thirteenf", () => ({
  getHoldings: vi.fn().mockResolvedValue({
    ticker: "AAPL",
    period_of_report: "2025-12-31",
    curated_holders: [],
    other_holders: [],
    summary: { total_holders: 0, curated_holders: 0, net_shares_changed: 0, signal_score: 0 },
  }),
  getHoldingsHistory: vi.fn().mockResolvedValue({ ticker: "AAPL", quarters: [] }),
}))

vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => <div data-testid="responsive-container">{children}</div>,
  RadarChart: ({ children }: { children: React.ReactNode }) => <div data-testid="radar-chart">{children}</div>,
  PolarGrid: () => <div data-testid="polar-grid" />,
  PolarAngleAxis: () => <div data-testid="polar-angle-axis" />,
  Radar: () => <div data-testid="radar" />,
  Legend: () => <div data-testid="legend" />,
  LineChart: ({ children }: { children: React.ReactNode }) => <div data-testid="line-chart">{children}</div>,
  Line: () => <div data-testid="line" />,
  XAxis: () => <div data-testid="x-axis" />,
  YAxis: () => <div data-testid="y-axis" />,
  Tooltip: () => <div data-testid="tooltip" />,
  CartesianGrid: () => <div data-testid="cartesian-grid" />,
}))

function makeScoreResponse(overrides: Partial<ScoreResponse> = {}): ScoreResponse {
  return {
    ticker: "AAPL",
    name: "Apple Inc.",
    score: 78.3,
    universe_percentile: 96,
    composite_percentile: 96,
    composite_raw_score: 78.3,
    composite_tier: "high",
    signal: "strong",
    quality: { factor_name: "quality", weight: 0.3, average_percentile: 72, sub_scores: [] },
    value: { factor_name: "value", weight: 0.4, average_percentile: 81, sub_scores: [] },
    momentum: { factor_name: "momentum", weight: 0.3, average_percentile: 68, sub_scores: [] },
    filters_passed: [
      { name: "liquidity", passed: true, value: 2890000, threshold: 200000000, detail: "", verdict: "pass", missing_fields: null },
      { name: "beneish_m_score", passed: true, value: -2.87, threshold: -2.22, detail: "", verdict: "pass", missing_fields: null },
      { name: "altman_z_score", passed: true, value: 5.12, threshold: 1.1, detail: "", verdict: "pass", missing_fields: null },
      { name: "current_ratio", passed: true, value: 0.99, threshold: 0.8, detail: "", verdict: "pass", missing_fields: null },
      { name: "fcf_distress", passed: true, value: 104300, threshold: 0, detail: "", verdict: "pass", missing_fields: null },
      { name: "interest_coverage", passed: true, value: 29.4, threshold: 3.0, detail: "", verdict: "pass", missing_fields: null },
    ],
    data_coverage: 0.94,
    growth_stage: "mature",
    scored_at: "2026-02-23T12:00:00Z",
    margin_invest_value: 165,
    buy_price: 142,
    sell_price: 214,
    actual_price: 187.42,
    price_upside: -0.119,
    margin_of_safety: -0.136,
    valuation_methods: { dcf: 158.2, ev_fcf: 172.4 },
    opportunity_type: "compounder",
    winning_track: "compounder",
    asymmetry_ratio: 4.2,
    max_position_pct: 5.0,
    timing_signal: "add_on_pullback",
    capital_allocation: null,
    catalyst: null,
    price_target_invalid_reason: null,
    ...overrides,
  } as ScoreResponse
}

describe("AssetDetailView", () => {
  it("renders all sections for a passing ticker", async () => {
    render(
      <AssetDetailView
        ticker="AAPL"
        scoreData={makeScoreResponse()}
        historyData={null}
        apiError={null}
      />
    )
    // New layout components
    expect(screen.getByTestId("instrument-header")).toBeInTheDocument()
    expect(screen.getByTestId("vital-signs")).toBeInTheDocument()
    expect(screen.getByTestId("factor-profile")).toBeInTheDocument()
    expect(screen.getByTestId("elimination-gauntlet")).toBeInTheDocument()
    expect(screen.getByTestId("scoring-pillars")).toBeInTheDocument()
    expect(screen.getByTestId("conviction-engine")).toBeInTheDocument()
    expect(screen.getByTestId("valuation-section")).toBeInTheDocument()
    // Model validation appears after async fetch resolves
    await waitFor(() => {
      expect(screen.getByTestId("model-validation")).toBeInTheDocument()
    })
  })

  it("renders eliminated view for a low-tier failing ticker", () => {
    const data = makeScoreResponse({
      score: 45.0,
      composite_tier: "low",
      signal: "weak",
      filters_passed: [
        { name: "liquidity", passed: true, value: 782000, threshold: 200000000, detail: "", verdict: "pass", missing_fields: null },
        { name: "beneish_m_score", passed: true, value: -2.45, threshold: -2.22, detail: "", verdict: "pass", missing_fields: null },
        { name: "altman_z_score", passed: false, value: 1.6, threshold: 1.1, detail: "", verdict: "fail", missing_fields: null },
        { name: "current_ratio", passed: true, value: 1.2, threshold: 0.8, detail: "", verdict: "pass", missing_fields: null },
        { name: "fcf_distress", passed: false, value: -2100, threshold: 0, detail: "", verdict: "fail", missing_fields: null },
        { name: "interest_coverage", passed: true, value: 8.5, threshold: 3.0, detail: "", verdict: "pass", missing_fields: null },
      ],
    })
    render(
      <AssetDetailView
        ticker="TSLA"
        scoreData={data}
        historyData={null}
        apiError={null}
      />
    )
    // Always-present sections
    expect(screen.getByTestId("instrument-header")).toBeInTheDocument()
    expect(screen.getByTestId("vital-signs")).toBeInTheDocument()
    expect(screen.getByTestId("factor-profile")).toBeInTheDocument()
    expect(screen.getByTestId("elimination-gauntlet")).toBeInTheDocument()
    // Explore link should show for eliminated
    expect(screen.getByText(/View another candidate/)).toBeInTheDocument()
    // Passing-only sections should NOT be present
    expect(screen.queryByTestId("scoring-pillars")).not.toBeInTheDocument()
    expect(screen.queryByTestId("conviction-engine")).not.toBeInTheDocument()
    expect(screen.queryByTestId("valuation-section")).not.toBeInTheDocument()
    expect(screen.queryByTestId("model-validation")).not.toBeInTheDocument()
  })

  it("renders score view for top-tier ticker with failed filters", () => {
    const data = makeScoreResponse({
      composite_tier: "none",
      filters_passed: [
        { name: "liquidity", passed: true, value: 782000, threshold: 200000000, detail: "", verdict: "pass", missing_fields: null },
        { name: "beneish_m_score", passed: true, value: -2.45, threshold: -2.22, detail: "", verdict: "pass", missing_fields: null },
        { name: "altman_z_score", passed: false, value: 1.6, threshold: 1.1, detail: "", verdict: "fail", missing_fields: null },
        { name: "current_ratio", passed: true, value: 1.2, threshold: 0.8, detail: "", verdict: "pass", missing_fields: null },
        { name: "fcf_distress", passed: true, value: 50000, threshold: 0, detail: "", verdict: "pass", missing_fields: null },
        { name: "interest_coverage", passed: true, value: 8.5, threshold: 3.0, detail: "", verdict: "pass", missing_fields: null },
      ],
    })
    render(
      <AssetDetailView
        ticker="AAPL"
        scoreData={data}
        historyData={null}
        apiError={null}
      />
    )
    // Top-tier shows score view, not eliminated
    expect(screen.getByTestId("instrument-header")).toBeInTheDocument()
    expect(screen.getByTestId("scoring-pillars")).toBeInTheDocument()
    // Explore link should NOT appear for score view
    expect(screen.queryByText(/View another candidate/)).not.toBeInTheDocument()
    // Filter gauntlet still shows
    expect(screen.getByTestId("elimination-gauntlet")).toBeInTheDocument()
  })

  it("shows error state when apiError is provided", () => {
    render(
      <AssetDetailView
        ticker="XYZA"
        scoreData={null}
        historyData={null}
        apiError="Not found"
      />
    )
    expect(screen.getByTestId("error-state")).toBeInTheDocument()
    expect(screen.getByText("Score data unavailable")).toBeInTheDocument()
    // No data sections should render
    expect(screen.queryByTestId("instrument-header")).not.toBeInTheDocument()
    expect(screen.queryByTestId("elimination-gauntlet")).not.toBeInTheDocument()
  })

  it("shows fallback error when scoreData is null and no apiError", () => {
    render(
      <AssetDetailView
        ticker="XYZA"
        scoreData={null}
        historyData={null}
        apiError={null}
      />
    )
    expect(screen.getByTestId("error-state")).toBeInTheDocument()
    expect(screen.getByText(/scored in the next cycle/i)).toBeInTheDocument()
  })
})

describe("barrel exports", () => {
  it("exports all components from index", async () => {
    const barrel = await import("../index")
    expect(barrel.AssetDetailView).toBeDefined()
    expect(barrel.InstrumentHeader).toBeDefined()
    expect(barrel.VitalSigns).toBeDefined()
    expect(barrel.FactorProfile).toBeDefined()
    expect(barrel.EliminationGauntlet).toBeDefined()
    expect(barrel.FilterPill).toBeDefined()
    expect(barrel.FilterDetail).toBeDefined()
    expect(barrel.ScoringPillars).toBeDefined()
    expect(barrel.PillarCard).toBeDefined()
    expect(barrel.ConvictionEngine).toBeDefined()
    expect(barrel.ValuationSection).toBeDefined()
    expect(barrel.InstitutionalPositioning).toBeDefined()
    expect(barrel.ModelValidation).toBeDefined()
    expect(barrel.WatchlistButton).toBeDefined()
  })
})
