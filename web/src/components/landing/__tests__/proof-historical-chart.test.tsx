import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen } from "@testing-library/react"

vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  AreaChart: ({ children }: { children: React.ReactNode }) => <div data-testid="area-chart">{children}</div>,
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

  it("renders error message when fetch returns non-ok", async () => {
    mockFetch.mockResolvedValue({ ok: false, status: 500 })
    render(<ProofHistoricalChart />)
    expect(await screen.findByTestId("historical-error")).toBeInTheDocument()
    expect(screen.getByText(/unable to load/i)).toBeInTheDocument()
  })

  it("renders error message when fetch throws", async () => {
    vi.spyOn(console, "error").mockImplementation(() => {})
    mockFetch.mockRejectedValueOnce(new Error("Network failure"))
    render(<ProofHistoricalChart />)
    expect(await screen.findByTestId("historical-error")).toBeInTheDocument()
    expect(screen.getByText(/unable to load/i)).toBeInTheDocument()
    vi.restoreAllMocks()
    global.fetch = mockFetch
  })

  it("renders timeout error when fetch is aborted", async () => {
    vi.spyOn(console, "error").mockImplementation(() => {})
    const abortError = new DOMException("The operation was aborted.", "AbortError")
    mockFetch.mockRejectedValueOnce(abortError)
    render(<ProofHistoricalChart />)
    expect(await screen.findByTestId("historical-error")).toBeInTheDocument()
    expect(screen.getByText(/timed out/i)).toBeInTheDocument()
    vi.restoreAllMocks()
    global.fetch = mockFetch
  })

  it("shows loading text in skeleton state", async () => {
    // Fetch that resolves after a delay — skeleton shows in the meantime
    let resolvePromise: (v: unknown) => void
    mockFetch.mockReturnValue(
      new Promise((resolve) => {
        resolvePromise = resolve
      })
    )
    render(<ProofHistoricalChart />)
    expect(screen.getByTestId("historical-skeleton")).toBeInTheDocument()
    expect(screen.getByText(/loading historical data/i)).toBeInTheDocument()
    // Resolve with a successful response to allow cleanup
    resolvePromise!({ ok: true, json: async () => MOCK_TEASER })
    await screen.findByTestId("area-chart")
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

  it("renders hypothetical performance disclaimer", async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => MOCK_TEASER,
    })
    render(<ProofHistoricalChart />)
    expect(await screen.findByTestId("hypothetical-disclaimer")).toBeInTheDocument()
    expect(screen.getByText(/HYPOTHETICAL PERFORMANCE RESULTS/)).toBeInTheDocument()
  })

  it("renders hypothetical badge above chart", async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => MOCK_TEASER,
    })
    render(<ProofHistoricalChart />)
    expect(await screen.findByTestId("hypothetical-badge")).toBeInTheDocument()
    expect(screen.getByText(/Simulated Performance/)).toBeInTheDocument()
  })
})
