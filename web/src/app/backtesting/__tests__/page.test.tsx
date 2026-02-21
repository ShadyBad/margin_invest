import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
import BacktestingPage from "../page"
import type {
  BacktestResult,
  BacktestListResponse,
} from "@/lib/api/types"

const mockGetBacktestResults = vi.fn()
const mockGetBacktestResult = vi.fn()

vi.mock("@/lib/api/backtest", () => ({
  getBacktestResults: (...args: unknown[]) => mockGetBacktestResults(...args),
  getBacktestResult: (...args: unknown[]) => mockGetBacktestResult(...args),
}))

vi.mock("next-auth/react", () => ({
  useSession: () => ({
    data: {
      user: {
        name: "Test User",
        email: "test@example.com",
        image: "https://example.com/avatar.jpg",
      },
    },
    status: "authenticated",
  }),
  signOut: vi.fn(),
}))

vi.mock("next/navigation", () => ({
  usePathname: () => "/backtesting",
}))

const mockBacktestResult: BacktestResult = {
  config: {
    start_date: "2020-01-01",
    end_date: "2025-01-01",
    rebalance_frequency: "monthly",
    top_percentile: 10,
    transaction_cost_bps: 10,
    slippage_bps: 5,
    benchmark_ticker: "SPY",
  },
  metrics: {
    cagr: 0.1234,
    excess_cagr: 0.0456,
    sharpe_ratio: 1.52,
    sortino_ratio: 2.13,
    max_drawdown: 0.2145,
    win_rate: 0.5832,
    information_ratio: 0.87,
    total_return: 0.7523,
    benchmark_total_return: 0.5012,
    num_months: 60,
    avg_turnover: 0.15,
  },
  validation: {
    overall_pass: true,
    passed_count: 4,
    total_checks: 4,
    checks: [
      { name: "excess_cagr", threshold: 0.02, actual: 0.0456, passed: true },
      { name: "sharpe_ratio", threshold: 0.5, actual: 1.52, passed: true },
      { name: "max_drawdown", threshold: 0.35, actual: 0.2145, passed: true },
      { name: "win_rate", threshold: 0.5, actual: 0.5832, passed: true },
    ],
  },
  num_snapshots: 60,
  run_at: "2026-02-12T10:30:00Z",
  duration_seconds: 3.5,
}

const mockListResponse: BacktestListResponse = {
  results: [
    {
      id: "bt-001",
      run_at: "2026-02-12T10:30:00Z",
      config: mockBacktestResult.config,
      overall_pass: true,
      excess_cagr: 0.0456,
      sharpe_ratio: 1.52,
    },
  ],
  total: 1,
}

const mockMultipleResults: BacktestListResponse = {
  results: [
    {
      id: "bt-002",
      run_at: "2026-02-14T08:00:00Z",
      config: mockBacktestResult.config,
      overall_pass: true,
      excess_cagr: 0.051,
      sharpe_ratio: 1.6,
    },
    {
      id: "bt-001",
      run_at: "2026-02-12T10:30:00Z",
      config: mockBacktestResult.config,
      overall_pass: true,
      excess_cagr: 0.0456,
      sharpe_ratio: 1.52,
    },
  ],
  total: 2,
}

const mockEmptyListResponse: BacktestListResponse = {
  results: [],
  total: 0,
}

describe("Backtesting Page (read-only)", () => {
  beforeEach(() => {
    mockGetBacktestResults.mockReset()
    mockGetBacktestResult.mockReset()
  })

  it("renders loading skeleton while fetching", () => {
    mockGetBacktestResults.mockReturnValue(new Promise(() => {}))
    render(<BacktestingPage />)

    expect(screen.getByTestId("loading-skeleton")).toBeInTheDocument()
  })

  it("does not render a Run Backtest button", async () => {
    mockGetBacktestResults.mockResolvedValue(mockEmptyListResponse)
    render(<BacktestingPage />)

    await waitFor(() => {
      expect(screen.queryByTestId("loading-skeleton")).not.toBeInTheDocument()
    })

    expect(screen.queryByTestId("run-backtest-button")).not.toBeInTheDocument()
    expect(screen.queryByText("Run Backtest")).not.toBeInTheDocument()
  })

  it("shows automatic validation note", async () => {
    mockGetBacktestResults.mockResolvedValue(mockEmptyListResponse)
    render(<BacktestingPage />)

    await waitFor(() => {
      expect(screen.queryByTestId("loading-skeleton")).not.toBeInTheDocument()
    })

    expect(screen.getByTestId("auto-validation-note")).toBeInTheDocument()
    expect(
      screen.getByText(/runs automatically after each scoring cycle/i),
    ).toBeInTheDocument()
  })

  it("renders metrics when data loads", async () => {
    mockGetBacktestResults.mockResolvedValue(mockListResponse)
    mockGetBacktestResult.mockResolvedValue(mockBacktestResult)
    render(<BacktestingPage />)

    await waitFor(() => {
      expect(screen.getByTestId("metrics-summary")).toBeInTheDocument()
    })

    expect(screen.getByTestId("metric-cagr")).toBeInTheDocument()
    expect(screen.getByTestId("metric-excess-cagr")).toBeInTheDocument()
    expect(screen.getByTestId("metric-sharpe-ratio")).toBeInTheDocument()
    expect(screen.getByTestId("metric-sortino-ratio")).toBeInTheDocument()
    expect(screen.getByTestId("metric-max-drawdown")).toBeInTheDocument()
    expect(screen.getByTestId("metric-win-rate")).toBeInTheDocument()
    expect(screen.getByTestId("metric-information-ratio")).toBeInTheDocument()
    expect(screen.getByTestId("metric-total-return")).toBeInTheDocument()
    expect(screen.getByTestId("metric-benchmark-return")).toBeInTheDocument()
  })

  it("shows empty state when no validations exist", async () => {
    mockGetBacktestResults.mockResolvedValue(mockEmptyListResponse)
    render(<BacktestingPage />)

    await waitFor(() => {
      expect(screen.getByText("No validations yet")).toBeInTheDocument()
    })

    expect(
      screen.getByText(
        "Validation results will appear here after the next scoring cycle completes.",
      ),
    ).toBeInTheDocument()
  })

  it("shows error on fetch failure", async () => {
    mockGetBacktestResults.mockRejectedValue(new Error("Network error"))
    render(<BacktestingPage />)

    await waitFor(() => {
      expect(screen.getByTestId("error-message")).toBeInTheDocument()
    })

    expect(screen.getByText("Network error")).toBeInTheDocument()
  })

  it("validation badges shown when validation data present", async () => {
    mockGetBacktestResults.mockResolvedValue(mockListResponse)
    mockGetBacktestResult.mockResolvedValue(mockBacktestResult)
    render(<BacktestingPage />)

    await waitFor(() => {
      expect(screen.getByTestId("validation-badges")).toBeInTheDocument()
    })

    expect(screen.getByTestId("validation-verdict")).toBeInTheDocument()
    expect(screen.getByText("ALL CHECKS PASSED")).toBeInTheDocument()
    expect(screen.getByTestId("check-excess_cagr")).toBeInTheDocument()
    expect(screen.getByTestId("check-sharpe_ratio")).toBeInTheDocument()
    expect(screen.getByTestId("check-max_drawdown")).toBeInTheDocument()
    expect(screen.getByTestId("check-win_rate")).toBeInTheDocument()
  })

  it("metrics show correct formatting (percentages, decimals)", async () => {
    mockGetBacktestResults.mockResolvedValue(mockListResponse)
    mockGetBacktestResult.mockResolvedValue(mockBacktestResult)
    render(<BacktestingPage />)

    await waitFor(() => {
      expect(screen.getByTestId("metrics-summary")).toBeInTheDocument()
    })

    expect(screen.getByTestId("metric-cagr")).toHaveTextContent("12.34%")
    expect(screen.getByTestId("metric-excess-cagr")).toHaveTextContent("4.56%")
    expect(screen.getByTestId("metric-sharpe-ratio")).toHaveTextContent("1.52")
    expect(screen.getByTestId("metric-sortino-ratio")).toHaveTextContent("2.13")
    expect(screen.getByTestId("metric-max-drawdown")).toHaveTextContent("21.45%")
    expect(screen.getByTestId("metric-win-rate")).toHaveTextContent("58.32%")
    expect(screen.getByTestId("metric-information-ratio")).toHaveTextContent("0.87")
    expect(screen.getByTestId("metric-total-return")).toHaveTextContent("75.23%")
    expect(screen.getByTestId("metric-benchmark-return")).toHaveTextContent("50.12%")
  })

  it("does not show validation section when validation is null", async () => {
    const resultNoValidation: BacktestResult = {
      ...mockBacktestResult,
      validation: null,
    }
    mockGetBacktestResults.mockResolvedValue(mockListResponse)
    mockGetBacktestResult.mockResolvedValue(resultNoValidation)
    render(<BacktestingPage />)

    await waitFor(() => {
      expect(screen.getByTestId("metrics-summary")).toBeInTheDocument()
    })

    expect(screen.queryByTestId("validation-badges")).not.toBeInTheDocument()
  })

  it("shows partial pass verdict when some checks fail", async () => {
    const partialResult: BacktestResult = {
      ...mockBacktestResult,
      validation: {
        overall_pass: false,
        passed_count: 2,
        total_checks: 4,
        checks: [
          { name: "excess_cagr", threshold: 0.02, actual: 0.0456, passed: true },
          { name: "sharpe_ratio", threshold: 0.5, actual: 1.52, passed: true },
          { name: "max_drawdown", threshold: 0.15, actual: 0.2145, passed: false },
          { name: "win_rate", threshold: 0.6, actual: 0.5832, passed: false },
        ],
      },
    }
    mockGetBacktestResults.mockResolvedValue(mockListResponse)
    mockGetBacktestResult.mockResolvedValue(partialResult)
    render(<BacktestingPage />)

    await waitFor(() => {
      expect(screen.getByTestId("validation-badges")).toBeInTheDocument()
    })

    expect(screen.getByText("2/4 CHECKS PASSED")).toBeInTheDocument()

    const excessCheck = screen.getByTestId("check-excess_cagr")
    expect(excessCheck).toHaveTextContent("PASS")

    const drawdownCheck = screen.getByTestId("check-max_drawdown")
    expect(drawdownCheck).toHaveTextContent("FAIL")
  })

  it("renders validation history section with past results", async () => {
    mockGetBacktestResults.mockResolvedValue(mockMultipleResults)
    mockGetBacktestResult.mockResolvedValue(mockBacktestResult)
    render(<BacktestingPage />)

    await waitFor(() => {
      expect(screen.getByTestId("validation-history")).toBeInTheDocument()
    })

    const historyItems = screen.getAllByTestId(/^history-item-/)
    expect(historyItems).toHaveLength(2)
  })

  it("renders historical performance section with chart", async () => {
    mockGetBacktestResults.mockResolvedValue(mockListResponse)
    mockGetBacktestResult.mockResolvedValue(mockBacktestResult)
    render(<BacktestingPage />)

    await waitFor(() => {
      expect(screen.getByText("Historical Performance")).toBeInTheDocument()
    })

    // Chart renders (empty state since mock has no snapshots)
    expect(screen.getByTestId("performance-chart-empty")).toBeInTheDocument()
  })

  it("shows page title as Validation instead of Backtesting", async () => {
    mockGetBacktestResults.mockResolvedValue(mockEmptyListResponse)
    render(<BacktestingPage />)

    await waitFor(() => {
      expect(screen.queryByTestId("loading-skeleton")).not.toBeInTheDocument()
    })

    expect(screen.getByText("Methodology Validation")).toBeInTheDocument()
  })
})
