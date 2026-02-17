import { describe, it, expect, vi } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
import { AssetPanel } from "../asset-panel"
import type { ScoreResponse } from "@/lib/api/types"

// Mock all child components to isolate orchestration logic
vi.mock("../panel-backdrop", () => ({
  PanelBackdrop: ({ onClose }: any) => <div data-testid="panel-backdrop" onClick={onClose} />,
}))
vi.mock("../executive-header", () => ({
  ExecutiveHeader: (props: any) => <div data-testid="executive-header">{props.ticker}</div>,
}))
vi.mock("../score-chart", () => ({
  ScoreChart: () => <div data-testid="score-chart" />,
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
  PanelValuation: () => <div data-testid="panel-valuation" />,
}))
vi.mock("../panel-filter-list", () => ({
  PanelFilterList: () => <div data-testid="panel-filter-list" />,
}))
vi.mock("../score-history-table", () => ({
  ScoreHistoryTable: () => <div data-testid="score-history-table" />,
}))
vi.mock("../../pro-gate", () => ({
  ProGate: ({ children }: any) => <div data-testid="pro-gate">{children}</div>,
}))

vi.mock("framer-motion", async () => {
  const actual = await vi.importActual("framer-motion")
  return {
    ...actual,
    AnimatePresence: ({ children }: any) => <>{children}</>,
    motion: {
      ...(actual as any).motion,
      div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    },
  }
})

vi.mock("@/lib/compute-institutional-metrics", () => ({
  computeInstitutionalMetrics: () => ({
    sharpeRatio: 1.5,
    maxDrawdown: 15,
    volatility: 12,
    avgProfitMargin: 25,
    riskClassification: "moderate",
    allocationWeight: 5,
  }),
}))

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
  conviction_level: "exceptional",
  signal: "buy",
  quality: { factor_name: "quality", weight: 0.35, average_percentile: 90, sub_scores: [] },
  value: { factor_name: "value", weight: 0.30, average_percentile: 85, sub_scores: [] },
  momentum: { factor_name: "momentum", weight: 0.20, average_percentile: 88, sub_scores: [] },
  filters_passed: [],
  data_coverage: 0.95,
  intrinsic_value: 180,
  buy_price: 140,
  sell_price: 200,
  actual_price: 150,
  price_upside: 0.2,
  margin_of_safety: 0.17,
  valuation_methods: { dcf: 190, ev_fcf: 170 },
}

describe("AssetPanel", () => {
  it("renders nothing when isOpen is false", () => {
    render(<AssetPanel isOpen={false} onClose={vi.fn()} ticker="AAPL" scoredResult={mockScore} />)
    expect(screen.queryByTestId("asset-panel")).not.toBeInTheDocument()
  })

  it("renders all sections when open", () => {
    render(<AssetPanel isOpen={true} onClose={vi.fn()} ticker="AAPL" scoredResult={mockScore} />)
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
    render(<AssetPanel isOpen={true} onClose={onClose} ticker="AAPL" scoredResult={mockScore} />)
    fireEvent.click(screen.getByTestId("panel-backdrop"))
    expect(onClose).toHaveBeenCalledOnce()
  })

  it("passes ticker to ExecutiveHeader", () => {
    render(<AssetPanel isOpen={true} onClose={vi.fn()} ticker="AAPL" scoredResult={mockScore} />)
    expect(screen.getByTestId("executive-header")).toHaveTextContent("AAPL")
  })

  it("calls onClose when Escape key is pressed", () => {
    const onClose = vi.fn()
    render(<AssetPanel isOpen={true} onClose={onClose} ticker="AAPL" scoredResult={mockScore} />)
    fireEvent.keyDown(document, { key: "Escape" })
    expect(onClose).toHaveBeenCalledOnce()
  })

  it("has role=dialog and aria-modal on the panel container", () => {
    render(<AssetPanel isOpen={true} onClose={vi.fn()} ticker="AAPL" scoredResult={mockScore} />)
    const dialog = screen.getByRole("dialog")
    expect(dialog).toHaveAttribute("aria-modal", "true")
    expect(dialog).toHaveAttribute("aria-label", "AAPL analysis panel")
  })
})
