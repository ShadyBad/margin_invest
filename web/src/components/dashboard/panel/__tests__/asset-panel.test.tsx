import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
import { AssetPanel } from "../asset-panel"
import type { ScoreResponse, InstitutionalMetricsResponse } from "@/lib/api/types"
import * as scoresApi from "@/lib/api/scores"

// Mock all child components to isolate orchestration logic
vi.mock("../panel-backdrop", () => ({
  PanelBackdrop: ({ onClose }: { onClose: () => void }) => <div data-testid="panel-backdrop" onClick={onClose} />,
}))
vi.mock("../executive-header", () => ({
  ExecutiveHeader: (props: { ticker: string }) => <div data-testid="executive-header">{props.ticker}</div>,
}))
vi.mock("@/lib/api/scores", () => ({
  getScoreHistory: vi.fn(),
}))

vi.mock("../score-chart", () => ({
  ScoreChart: (props: { status?: string; onRetry?: () => void }) => (
    <div data-testid="score-chart" data-status={props.status ?? "none"} onClick={props.onRetry} />
  ),
}))
vi.mock("../panel-factor-breakdown", () => ({
  PanelFactorBreakdown: () => <div data-testid="panel-factor-breakdown" />,
}))
vi.mock("../kpi-grid", () => ({
  KpiGrid: () => <div data-testid="kpi-grid" />,
}))
vi.mock("../insight-panel", () => ({
  InsightPanel: () => <div data-testid="insight-panel" />,
}))
vi.mock("../panel-valuation", () => ({
  PanelValuation: (props: { buyPrice?: number | null }) => (
    <div data-testid="panel-valuation" data-buy-price={props.buyPrice ?? "none"} />
  ),
}))
vi.mock("../panel-filter-list", () => ({
  PanelFilterList: () => <div data-testid="panel-filter-list" />,
}))
vi.mock("../score-history-table", () => ({
  ScoreHistoryTable: (props: { status?: string }) => (
    <div data-testid="score-history-table" data-status={props.status ?? "none"} />
  ),
}))
vi.mock("../../pro-gate", () => ({
  ProGate: ({ children }: { children: React.ReactNode }) => <div data-testid="pro-gate">{children}</div>,
}))

vi.mock("framer-motion", async () => {
  const actual = await vi.importActual("framer-motion")
  return {
    ...actual,
    AnimatePresence: ({ children }: { children: React.ReactNode }) => <>{children}</>,
    motion: {
      ...(actual as Record<string, unknown>).motion as Record<string, unknown>,
      div: ({ children, ...props }: Record<string, unknown> & { children?: React.ReactNode }) => <div {...props as React.HTMLAttributes<HTMLDivElement>}>{children}</div>,
    },
  }
})

vi.mock("@/lib/compose-ai-summary", () => ({
  composeAiSummary: () => ({
    summary: "Strong quality characteristics with above-average momentum.",
    confidence: 75,
  }),
}))

const mockScore: ScoreResponse = {
  ticker: "AAPL",
  name: "Apple Inc.",
  score: 92,
  universe_percentile: 95,
  composite_percentile: 95,
  composite_raw_score: 88,
  composite_tier: "exceptional",
  signal: "strong",
  quality: { factor_name: "quality", weight: 0.35, average_percentile: 90, sub_scores: [] },
  value: { factor_name: "value", weight: 0.30, average_percentile: 85, sub_scores: [] },
  momentum: { factor_name: "momentum", weight: 0.20, average_percentile: 88, sub_scores: [] },
  filters_passed: [],
  data_coverage: 0.95,
  margin_invest_value: 180,
  buy_price: 140,
  sell_price: 200,
  actual_price: 150,
  price_upside: 0.2,
  margin_of_safety: 0.17,
  valuation_methods: { dcf: 190, ev_fcf: 170 },
}

const mockMetrics: InstitutionalMetricsResponse = {
  sharpe_ratio: { value: 1.5, unavailable_reason: null },
  sharpe_ratio_3y: { value: 1.3, unavailable_reason: null },
  max_drawdown: { value: -0.15, unavailable_reason: null },
  max_drawdown_3y: { value: -0.22, unavailable_reason: null },
  volatility: { value: 22.5, unavailable_reason: null },
  volatility_3y: { value: 20.1, unavailable_reason: null },
  avg_profit_margin: { value: 25.0, unavailable_reason: null },
  delta: { value: 0.12, unavailable_reason: null },
  risk_classification: "Moderate",
  margin_of_safety: { value: 0.10, unavailable_reason: null },
}

describe("AssetPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(scoresApi.getScoreHistory).mockResolvedValue({
      ticker: "AAPL",
      points: [],
      total_runs: 0,
    })
  })

  it("renders nothing when isOpen is false", () => {
    render(<AssetPanel isOpen={false} onClose={vi.fn()} ticker="AAPL" scoredResult={mockScore} metrics={mockMetrics} />)
    expect(screen.queryByTestId("asset-panel")).not.toBeInTheDocument()
  })

  it("renders all sections when open", () => {
    render(<AssetPanel isOpen={true} onClose={vi.fn()} ticker="AAPL" scoredResult={mockScore} metrics={mockMetrics} />)
    expect(screen.getByTestId("asset-panel")).toBeInTheDocument()
    expect(screen.getByTestId("panel-backdrop")).toBeInTheDocument()
    expect(screen.getByTestId("executive-header")).toBeInTheDocument()
    expect(screen.getByTestId("score-chart")).toBeInTheDocument()
    expect(screen.getByTestId("panel-factor-breakdown")).toBeInTheDocument()
    expect(screen.getByTestId("kpi-grid")).toBeInTheDocument()
    expect(screen.getByTestId("insight-panel")).toBeInTheDocument()
    expect(screen.getByTestId("panel-valuation")).toBeInTheDocument()
    expect(screen.getByTestId("panel-filter-list")).toBeInTheDocument()
    expect(screen.getByTestId("score-history-table")).toBeInTheDocument()
  })

  it("calls onClose when backdrop clicked", () => {
    const onClose = vi.fn()
    render(<AssetPanel isOpen={true} onClose={onClose} ticker="AAPL" scoredResult={mockScore} metrics={mockMetrics} />)
    fireEvent.click(screen.getByTestId("panel-backdrop"))
    expect(onClose).toHaveBeenCalledOnce()
  })

  it("passes ticker to ExecutiveHeader", () => {
    render(<AssetPanel isOpen={true} onClose={vi.fn()} ticker="AAPL" scoredResult={mockScore} metrics={mockMetrics} />)
    expect(screen.getByTestId("executive-header")).toHaveTextContent("AAPL")
  })

  it("calls onClose when Escape key is pressed", () => {
    const onClose = vi.fn()
    render(<AssetPanel isOpen={true} onClose={onClose} ticker="AAPL" scoredResult={mockScore} metrics={mockMetrics} />)
    fireEvent.keyDown(document, { key: "Escape" })
    expect(onClose).toHaveBeenCalledOnce()
  })

  it("has role=dialog and aria-modal on the panel container", () => {
    render(<AssetPanel isOpen={true} onClose={vi.fn()} ticker="AAPL" scoredResult={mockScore} metrics={mockMetrics} />)
    const dialog = screen.getByRole("dialog")
    expect(dialog).toHaveAttribute("aria-modal", "true")
    expect(dialog).toHaveAttribute("aria-label", "AAPL analysis panel")
  })

  it("passes buy_price to PanelValuation as buyPrice", () => {
    render(<AssetPanel isOpen={true} onClose={vi.fn()} ticker="AAPL" scoredResult={mockScore} metrics={mockMetrics} />)
    const valuation = screen.getByTestId("panel-valuation")
    expect(valuation).toHaveAttribute("data-buy-price", "140")
  })

  it("passes loading status to ScoreChart while fetching", async () => {
    // Never-resolving promise simulates in-flight request
    vi.mocked(scoresApi.getScoreHistory).mockReturnValue(new Promise(() => {}))
    render(<AssetPanel isOpen={true} onClose={vi.fn()} ticker="AAPL" scoredResult={mockScore} metrics={mockMetrics} />)
    expect(screen.getByTestId("score-chart")).toHaveAttribute("data-status", "loading")
    expect(screen.getByTestId("score-history-table")).toHaveAttribute("data-status", "loading")
  })

  it("passes loaded status after successful fetch", async () => {
    const mockHistory = {
      ticker: "AAPL",
      points: [
        { scored_at: "2026-01-01T00:00:00Z", composite_percentile: 80, composite_raw_score: 75, quality_percentile: 85, value_percentile: 80, momentum_percentile: 82, composite_tier: "high", signal: "strong", margin_invest_value: 200, buy_price: 150, sell_price: 250, actual_price: 185, delta: null },
        { scored_at: "2026-01-08T00:00:00Z", composite_percentile: 82, composite_raw_score: 77, quality_percentile: 86, value_percentile: 81, momentum_percentile: 83, composite_tier: "high", signal: "strong", margin_invest_value: 205, buy_price: 152, sell_price: 252, actual_price: 187, delta: 2 },
      ],
      total_runs: 2,
    }
    vi.mocked(scoresApi.getScoreHistory).mockResolvedValue(mockHistory)
    render(<AssetPanel isOpen={true} onClose={vi.fn()} ticker="AAPL" scoredResult={mockScore} metrics={mockMetrics} />)
    await vi.waitFor(() => {
      expect(screen.getByTestId("score-chart")).toHaveAttribute("data-status", "loaded")
      expect(screen.getByTestId("score-history-table")).toHaveAttribute("data-status", "loaded")
    })
  })

  it("passes error status when fetch fails", async () => {
    vi.mocked(scoresApi.getScoreHistory).mockRejectedValue(new Error("Network error"))
    render(<AssetPanel isOpen={true} onClose={vi.fn()} ticker="AAPL" scoredResult={mockScore} metrics={mockMetrics} />)
    await vi.waitFor(() => {
      expect(screen.getByTestId("score-chart")).toHaveAttribute("data-status", "error")
      expect(screen.getByTestId("score-history-table")).toHaveAttribute("data-status", "error")
    })
  })

  it("logs error to console when fetch fails", async () => {
    const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {})
    vi.mocked(scoresApi.getScoreHistory).mockRejectedValue(new Error("Network error"))
    render(<AssetPanel isOpen={true} onClose={vi.fn()} ticker="AAPL" scoredResult={mockScore} metrics={mockMetrics} />)
    await vi.waitFor(() => {
      expect(consoleSpy).toHaveBeenCalledWith(
        expect.stringContaining("[ScoreHistory]"),
        expect.any(Error),
      )
    })
    consoleSpy.mockRestore()
  })

  it("retries fetch when onRetry is triggered after error", async () => {
    vi.mocked(scoresApi.getScoreHistory).mockRejectedValueOnce(new Error("fail"))
    render(<AssetPanel isOpen={true} onClose={vi.fn()} ticker="AAPL" scoredResult={mockScore} metrics={mockMetrics} />)
    await vi.waitFor(() => {
      expect(screen.getByTestId("score-chart")).toHaveAttribute("data-status", "error")
    })
    // Reset to success for retry
    const mockHistory = {
      ticker: "AAPL",
      points: [
        { scored_at: "2026-01-01T00:00:00Z", composite_percentile: 80, composite_raw_score: 75, quality_percentile: 85, value_percentile: 80, momentum_percentile: 82, composite_tier: "high", signal: "strong", margin_invest_value: 200, buy_price: 150, sell_price: 250, actual_price: 185, delta: null },
        { scored_at: "2026-01-08T00:00:00Z", composite_percentile: 82, composite_raw_score: 77, quality_percentile: 86, value_percentile: 81, momentum_percentile: 83, composite_tier: "high", signal: "strong", margin_invest_value: 205, buy_price: 152, sell_price: 252, actual_price: 187, delta: 2 },
      ],
      total_runs: 2,
    }
    vi.mocked(scoresApi.getScoreHistory).mockResolvedValue(mockHistory)
    // Trigger retry via the ScoreChart mock (onClick = onRetry)
    screen.getByTestId("score-chart").click()
    await vi.waitFor(() => {
      expect(screen.getByTestId("score-chart")).toHaveAttribute("data-status", "loaded")
    })
    expect(scoresApi.getScoreHistory).toHaveBeenCalledTimes(2)
  })
})
