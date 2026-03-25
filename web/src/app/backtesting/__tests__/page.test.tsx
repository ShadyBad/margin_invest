import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
import BacktestingPage from "../page"
import type {
  BacktestResult,
  BacktestListResponse,
  FullBacktestResponse,
  ShadowPortfolioResponse,
} from "@/lib/api/types"

const mockGetBacktestResults = vi.fn()
const mockGetBacktestResult = vi.fn()
const mockGetDefaultBacktest = vi.fn()
const mockGetShadowPortfolio = vi.fn()

vi.mock("@/lib/api/backtest", () => ({
  getBacktestResults: (...args: unknown[]) => mockGetBacktestResults(...args),
  getBacktestResult: (...args: unknown[]) => mockGetBacktestResult(...args),
  getDefaultBacktest: (...args: unknown[]) => mockGetDefaultBacktest(...args),
  getShadowPortfolio: (...args: unknown[]) => mockGetShadowPortfolio(...args),
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
  useRouter: () => ({ push: vi.fn() }),
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

const mockReplayData: FullBacktestResponse = {
  config: {
    start_date: "2006-01-01",
    end_date: "2025-12-31",
    rebalance_frequency: "monthly",
    conviction_threshold: 0.10,
    weighting: "equal",
    sector_exclusions: [],
    transaction_cost_bps: 20,
  },
  metrics: mockBacktestResult.metrics,
  regime_segments: [
    { regime: "bull", num_months: 156, total_return: 2.34, benchmark_return: 1.87, max_drawdown: 0.12 },
    { regime: "bear", num_months: 36, total_return: -0.72, benchmark_return: -1.08, max_drawdown: 0.28 },
    { regime: "sideways", num_months: 30, total_return: 0.09, benchmark_return: 0.06, max_drawdown: 0.08 },
    { regime: "crisis", num_months: 18, total_return: -0.72, benchmark_return: -0.9, max_drawdown: 0.35 },
  ],
  audit_log: [
    { rebalance_date: "2025-12-31", universe_size: 502, eliminated_count: 350, survivor_count: 152, selected_count: 5, top_holdings: [], notable_events: [], factor_coverage: 0.95, regime: "bull" },
  ],
  factor_timeline: [
    { as_of_date: "2006-01-01", available: ["PE", "PB", "ROE"], missing: ["FCF"], coverage_ratio: 0.75 },
  ],
  failure_audit: [
    { rebalance_date: "2008-10-01", portfolio_return: -0.38, benchmark_return: -0.52, relative_underperformance: 0.14, holdings: [], regime: "crisis", regime_context: "GFC" },
  ],
  equity_curve: [
    { date: "2006-01-31", portfolio_value: 1.01, benchmark_value: 1.005 },
    { date: "2006-02-28", portfolio_value: 1.02, benchmark_value: 1.01 },
  ],
  walk_forward_note: "Walk-forward test note",
  honesty_disclosure: "Test disclosure",
}

const mockShadowData: ShadowPortfolioResponse = {
  start_date: "2026-02-24",
  snapshots: [],
  total_return: 0.0,
  max_drawdown: 0.0,
  num_days: 0,
  cannot_be_backdated: true,
}

describe("Backtesting Page (read-only)", () => {
  beforeEach(() => {
    mockGetBacktestResults.mockReset()
    mockGetBacktestResult.mockReset()
    mockGetDefaultBacktest.mockReset()
    mockGetShadowPortfolio.mockReset()
    mockGetDefaultBacktest.mockResolvedValue(mockReplayData)
    mockGetShadowPortfolio.mockResolvedValue(mockShadowData)
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
      expect(screen.getByText("Backtest validation in progress")).toBeInTheDocument()
    })

    expect(
      screen.getByText(/scoring engine runs automated backtests weekly/i),
    ).toBeInTheDocument()
    expect(screen.getByText(/learn about our methodology/i)).toBeInTheDocument()
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

  it("shows page title as Replay Backtesting", async () => {
    mockGetBacktestResults.mockResolvedValue(mockEmptyListResponse)
    render(<BacktestingPage />)

    await waitFor(() => {
      expect(screen.queryByTestId("loading-skeleton")).not.toBeInTheDocument()
    })

    expect(screen.getByText("Replay Backtesting")).toBeInTheDocument()
  })

  it("shows walk-forward subtitle", async () => {
    mockGetBacktestResults.mockResolvedValue(mockEmptyListResponse)
    render(<BacktestingPage />)

    await waitFor(() => {
      expect(screen.queryByTestId("loading-skeleton")).not.toBeInTheDocument()
    })

    expect(
      screen.getByText(/Walk-forward simulation of the scoring model/i),
    ).toBeInTheDocument()
  })

  it("renders regime cards when data loads", async () => {
    mockGetBacktestResults.mockResolvedValue(mockListResponse)
    mockGetBacktestResult.mockResolvedValue(mockBacktestResult)
    render(<BacktestingPage />)

    await waitFor(() => {
      expect(screen.getByTestId("regime-cards")).toBeInTheDocument()
    })

    expect(screen.getByTestId("regime-card-bull")).toBeInTheDocument()
    expect(screen.getByTestId("regime-card-bear")).toBeInTheDocument()
    expect(screen.getByTestId("regime-card-sideways")).toBeInTheDocument()
    expect(screen.getByTestId("regime-card-crisis")).toBeInTheDocument()
  })

  it("renders equity curve when data loads", async () => {
    mockGetBacktestResults.mockResolvedValue(mockListResponse)
    mockGetBacktestResult.mockResolvedValue(mockBacktestResult)
    render(<BacktestingPage />)

    await waitFor(() => {
      expect(screen.getByTestId("equity-curve-chart")).toBeInTheDocument()
    })
  })

  it("renders knobs panel when data loads", async () => {
    mockGetBacktestResults.mockResolvedValue(mockListResponse)
    mockGetBacktestResult.mockResolvedValue(mockBacktestResult)
    render(<BacktestingPage />)

    await waitFor(() => {
      expect(screen.getByTestId("knobs-panel")).toBeInTheDocument()
    })
  })

  it("renders stats summary when data loads", async () => {
    mockGetBacktestResults.mockResolvedValue(mockListResponse)
    mockGetBacktestResult.mockResolvedValue(mockBacktestResult)
    render(<BacktestingPage />)

    await waitFor(() => {
      expect(screen.getByTestId("stats-summary")).toBeInTheDocument()
    })
  })

  it("renders audit log when data loads", async () => {
    mockGetBacktestResults.mockResolvedValue(mockListResponse)
    mockGetBacktestResult.mockResolvedValue(mockBacktestResult)
    render(<BacktestingPage />)

    await waitFor(() => {
      expect(screen.getByTestId("audit-log")).toBeInTheDocument()
    })
  })

  it("renders failure audit when data loads", async () => {
    mockGetBacktestResults.mockResolvedValue(mockListResponse)
    mockGetBacktestResult.mockResolvedValue(mockBacktestResult)
    render(<BacktestingPage />)

    await waitFor(() => {
      expect(screen.getByTestId("failure-audit")).toBeInTheDocument()
    })
  })

  it("renders shadow portfolio section when data loads", async () => {
    mockGetBacktestResults.mockResolvedValue(mockListResponse)
    mockGetBacktestResult.mockResolvedValue(mockBacktestResult)
    render(<BacktestingPage />)

    await waitFor(() => {
      expect(screen.getByTestId("shadow-portfolio-section")).toBeInTheDocument()
    })

    expect(screen.getByTestId("shadow-no-backdate")).toBeInTheDocument()
  })

  it("renders backtest disclosure footer when data loads", async () => {
    mockGetBacktestResults.mockResolvedValue(mockListResponse)
    mockGetBacktestResult.mockResolvedValue(mockBacktestResult)
    render(<BacktestingPage />)

    await waitFor(() => {
      expect(screen.getByTestId("backtest-disclosure")).toBeInTheDocument()
    })

    // Uses honesty_disclosure from API when available
    expect(screen.getByTestId("backtest-disclosure")).toHaveTextContent("Test disclosure")
  })

  it("renders factor timeline when data loads", async () => {
    mockGetBacktestResults.mockResolvedValue(mockListResponse)
    mockGetBacktestResult.mockResolvedValue(mockBacktestResult)
    render(<BacktestingPage />)

    await waitFor(() => {
      expect(screen.getByTestId("factor-timeline")).toBeInTheDocument()
    })
  })

  it("renders shadow portfolio section when shadow data is available", async () => {
    mockGetBacktestResults.mockResolvedValue(mockListResponse)
    mockGetBacktestResult.mockResolvedValue(mockBacktestResult)
    mockGetShadowPortfolio.mockResolvedValue(mockShadowData)
    render(<BacktestingPage />)

    await waitFor(() => {
      expect(screen.getByTestId("shadow-portfolio-section")).toBeInTheDocument()
    })

    expect(screen.getByText("Shadow Portfolio")).toBeInTheDocument()
    expect(screen.getByText("2026-02-24")).toBeInTheDocument()
    expect(screen.getByTestId("shadow-no-backdate")).toBeInTheDocument()
  })

  it("renders honesty disclosure in footer when replay data has one", async () => {
    mockGetBacktestResults.mockResolvedValue(mockListResponse)
    mockGetBacktestResult.mockResolvedValue(mockBacktestResult)
    mockGetDefaultBacktest.mockResolvedValue(mockReplayData)
    render(<BacktestingPage />)

    await waitFor(() => {
      expect(screen.getByTestId("backtest-disclosure")).toBeInTheDocument()
    })

    expect(screen.getByTestId("backtest-disclosure")).toHaveTextContent("Test disclosure")
  })

  it("does not render shadow or disclosure when APIs fail", async () => {
    mockGetBacktestResults.mockResolvedValue(mockListResponse)
    mockGetBacktestResult.mockResolvedValue(mockBacktestResult)
    mockGetDefaultBacktest.mockRejectedValue(new Error("fail"))
    mockGetShadowPortfolio.mockRejectedValue(new Error("fail"))
    render(<BacktestingPage />)

    await waitFor(() => {
      expect(screen.getByTestId("metrics-summary")).toBeInTheDocument()
    })

    expect(screen.queryByTestId("shadow-portfolio-section")).not.toBeInTheDocument()
  })

  it("calls getDefaultBacktest and getShadowPortfolio on mount", async () => {
    mockGetBacktestResults.mockResolvedValue(mockListResponse)
    mockGetBacktestResult.mockResolvedValue(mockBacktestResult)
    render(<BacktestingPage />)

    await waitFor(() => {
      expect(screen.getByTestId("metrics-summary")).toBeInTheDocument()
    })

    expect(mockGetDefaultBacktest).toHaveBeenCalledTimes(1)
    expect(mockGetShadowPortfolio).toHaveBeenCalledTimes(1)
  })
})
