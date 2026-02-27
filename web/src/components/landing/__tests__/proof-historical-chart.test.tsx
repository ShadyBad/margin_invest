import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen } from "@testing-library/react"

vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: any) => <div>{children}</div>,
  AreaChart: ({ children }: any) => <div data-testid="area-chart">{children}</div>,
  Area: () => null,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
  Legend: () => null,
}))

const mockFetch = vi.fn()
global.fetch = mockFetch

import { ProofHistoricalChart } from "../proof-historical-chart"

const MOCK_TEASER = {
  model_return: 5.42,
  benchmark_return: 3.80,
  max_drawdown: -0.28,
  sharpe_ratio: 0.85,
  num_months: 240,
  start_date: "2006-01-01",
  end_date: "2025-12-31",
  equity_curve: [
    { month: "2006-01", portfolio: 10000, benchmark: 10000 },
    { month: "2006-02", portfolio: 10200, benchmark: 10100 },
    { month: "2006-03", portfolio: 10400, benchmark: 10180 },
  ],
}

describe("ProofHistoricalChart", () => {
  beforeEach(() => mockFetch.mockReset())

  it("renders skeleton when fetch returns non-ok", async () => {
    mockFetch.mockResolvedValue({ ok: false, status: 500 })
    render(<ProofHistoricalChart />)
    // Wait for useEffect to settle (non-ok response, data stays null)
    await vi.waitFor(() => {
      expect(mockFetch).toHaveBeenCalled()
    })
    expect(screen.getByTestId("historical-skeleton")).toBeInTheDocument()
  })

  it("renders area chart after data loads", async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => MOCK_TEASER,
    })
    render(<ProofHistoricalChart />)
    expect(await screen.findByTestId("area-chart")).toBeInTheDocument()
  })

  it("renders metric ribbon with CAGR and Sharpe", async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => MOCK_TEASER,
    })
    render(<ProofHistoricalChart />)
    expect(await screen.findByText(/CAGR/i)).toBeInTheDocument()
    expect(screen.getByText(/Sharpe Ratio/i)).toBeInTheDocument()
    expect(screen.getByText(/Max Drawdown/i)).toBeInTheDocument()
    expect(screen.getByText(/Excess Return/i)).toBeInTheDocument()
  })

  it("renders disclaimer", async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => MOCK_TEASER,
    })
    render(<ProofHistoricalChart />)
    expect(await screen.findByText(/past performance is not indicative/i)).toBeInTheDocument()
  })
})
