import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { InstitutionalPositioning } from "../institutional-positioning"

vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: any) => (
    <div data-testid="responsive-container">{children}</div>
  ),
  AreaChart: ({ children }: any) => <div data-testid="area-chart">{children}</div>,
  Area: () => <div data-testid="area" />,
  XAxis: () => <div data-testid="x-axis" />,
  YAxis: () => <div data-testid="y-axis" />,
  Tooltip: () => <div data-testid="tooltip" />,
  CartesianGrid: () => <div data-testid="cartesian-grid" />,
}))

const mockGetHoldings = vi.fn()
const mockGetHoldingsHistory = vi.fn()

vi.mock("@/lib/api/thirteenf", () => ({
  getHoldings: (...args: any[]) => mockGetHoldings(...args),
  getHoldingsHistory: (...args: any[]) => mockGetHoldingsHistory(...args),
}))

const MOCK_HOLDINGS = {
  ticker: "AAPL",
  period_of_report: "2025-12-31",
  curated_holders: [
    {
      manager_name: "Berkshire Hathaway",
      tier: "curated",
      shares_held: 915_560_382,
      value_millions: 75.4,
      shares_changed: 12_340_000,
      pct_portfolio: 48.2,
      is_new_position: false,
      quarters_held: 12,
    },
    {
      manager_name: "Baupost Group",
      tier: "curated",
      shares_held: 3_200_000,
      value_millions: 0.26,
      shares_changed: -500_000,
      pct_portfolio: 2.1,
      is_new_position: false,
      quarters_held: 4,
    },
  ],
  other_holders: [
    {
      manager_name: "Vanguard Total Stock Market",
      tier: "tracked",
      shares_held: 120_000_000,
      value_millions: 9.9,
      shares_changed: 0,
      pct_portfolio: null,
      is_new_position: false,
      quarters_held: null,
    },
  ],
  summary: {
    total_holders: 3,
    curated_holders: 2,
    net_shares_changed: 11_840_000,
    signal_score: 0.72,
  },
}

const MOCK_HISTORY = {
  ticker: "AAPL",
  quarters: [
    { period: "2025-03-31", curated_holders: 1, total_holders: 2, total_shares: 900_000_000, net_change: 5_000_000 },
    { period: "2025-06-30", curated_holders: 2, total_holders: 3, total_shares: 910_000_000, net_change: 10_000_000 },
    { period: "2025-09-30", curated_holders: 2, total_holders: 3, total_shares: 920_000_000, net_change: 10_000_000 },
    { period: "2025-12-31", curated_holders: 2, total_holders: 3, total_shares: 930_000_000, net_change: 11_840_000 },
  ],
}

describe("InstitutionalPositioning", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("renders loading skeleton initially", () => {
    mockGetHoldings.mockReturnValue(new Promise(() => {})) // never resolves
    mockGetHoldingsHistory.mockReturnValue(new Promise(() => {}))

    render(<InstitutionalPositioning ticker="AAPL" />)
    expect(screen.getByTestId("institutional-positioning")).toBeInTheDocument()
    expect(screen.getByTestId("institutional-positioning-loading")).toBeInTheDocument()
  })

  it("renders holder summary when data is available", async () => {
    mockGetHoldings.mockResolvedValue(MOCK_HOLDINGS)
    mockGetHoldingsHistory.mockResolvedValue(MOCK_HISTORY)

    render(<InstitutionalPositioning ticker="AAPL" />)

    await waitFor(() => {
      expect(screen.getByText("Institutional Positioning")).toBeInTheDocument()
    })

    // Period badge
    expect(screen.getByText("Q4 2025")).toBeInTheDocument()

    // Summary stats
    expect(screen.getByText("3")).toBeInTheDocument() // total holders
    expect(screen.getByText("2")).toBeInTheDocument() // curated holders
  })

  it("renders curated fund rows with correct data", async () => {
    mockGetHoldings.mockResolvedValue(MOCK_HOLDINGS)
    mockGetHoldingsHistory.mockResolvedValue(MOCK_HISTORY)

    render(<InstitutionalPositioning ticker="AAPL" />)

    await waitFor(() => {
      expect(screen.getByText("Berkshire Hathaway")).toBeInTheDocument()
    })

    expect(screen.getByText("Baupost Group")).toBeInTheDocument()

    // Positive change for Berkshire
    expect(screen.getByText("+12,340,000")).toBeInTheDocument()

    // Negative change for Baupost
    expect(screen.getByText("-500,000")).toBeInTheDocument()
  })

  it("renders empty state when no data", async () => {
    mockGetHoldings.mockResolvedValue({
      ticker: "XYZ",
      period_of_report: "",
      curated_holders: [],
      other_holders: [],
      summary: {
        total_holders: 0,
        curated_holders: 0,
        net_shares_changed: 0,
        signal_score: 0,
      },
    })
    mockGetHoldingsHistory.mockResolvedValue({
      ticker: "XYZ",
      quarters: [],
    })

    render(<InstitutionalPositioning ticker="XYZ" />)

    await waitFor(() => {
      expect(
        screen.getByText("No institutional holdings data available for XYZ")
      ).toBeInTheDocument()
    })
  })

  it("renders error state gracefully", async () => {
    mockGetHoldings.mockRejectedValue(new Error("Network error"))
    mockGetHoldingsHistory.mockRejectedValue(new Error("Network error"))

    render(<InstitutionalPositioning ticker="AAPL" />)

    await waitFor(() => {
      expect(
        screen.getByText(/unable to load institutional data/i)
      ).toBeInTheDocument()
    })
  })

  it("renders holder count trend chart from history data", async () => {
    mockGetHoldings.mockResolvedValue(MOCK_HOLDINGS)
    mockGetHoldingsHistory.mockResolvedValue(MOCK_HISTORY)

    render(<InstitutionalPositioning ticker="AAPL" />)

    await waitFor(() => {
      expect(screen.getByTestId("area-chart")).toBeInTheDocument()
    })
  })

  it("shows net accumulation direction with bullish arrow for positive net change", async () => {
    mockGetHoldings.mockResolvedValue(MOCK_HOLDINGS)
    mockGetHoldingsHistory.mockResolvedValue(MOCK_HISTORY)

    render(<InstitutionalPositioning ticker="AAPL" />)

    await waitFor(() => {
      expect(screen.getByTestId("net-accumulation-up")).toBeInTheDocument()
    })
  })

  it("shows net accumulation direction with bearish arrow for negative net change", async () => {
    const bearishHoldings = {
      ...MOCK_HOLDINGS,
      summary: {
        ...MOCK_HOLDINGS.summary,
        net_shares_changed: -5_000_000,
      },
    }
    mockGetHoldings.mockResolvedValue(bearishHoldings)
    mockGetHoldingsHistory.mockResolvedValue(MOCK_HISTORY)

    render(<InstitutionalPositioning ticker="AAPL" />)

    await waitFor(() => {
      expect(screen.getByTestId("net-accumulation-down")).toBeInTheDocument()
    })
  })

  it("shows expandable other holders section", async () => {
    mockGetHoldings.mockResolvedValue(MOCK_HOLDINGS)
    mockGetHoldingsHistory.mockResolvedValue(MOCK_HISTORY)

    render(<InstitutionalPositioning ticker="AAPL" />)

    await waitFor(() => {
      expect(screen.getByText("Berkshire Hathaway")).toBeInTheDocument()
    })

    // Other holders should be in a collapsible section
    const expandButton = screen.getByText(/all tracked holders/i)
    expect(expandButton).toBeInTheDocument()

    // Other holders should not be visible initially
    expect(screen.queryByText("Vanguard Total Stock Market")).not.toBeInTheDocument()

    // Click to expand
    await userEvent.click(expandButton)

    expect(screen.getByText("Vanguard Total Stock Market")).toBeInTheDocument()
  })

  it("shows filing lag note", async () => {
    mockGetHoldings.mockResolvedValue(MOCK_HOLDINGS)
    mockGetHoldingsHistory.mockResolvedValue(MOCK_HISTORY)

    render(<InstitutionalPositioning ticker="AAPL" />)

    await waitFor(() => {
      expect(screen.getByText(/13F filings have a 45-day reporting lag/i)).toBeInTheDocument()
    })
  })

  it("handles zero shares_changed gracefully", async () => {
    const holdingsWithZeroChange = {
      ...MOCK_HOLDINGS,
      curated_holders: [
        {
          ...MOCK_HOLDINGS.curated_holders[0],
          shares_changed: 0,
        },
      ],
      other_holders: [],
    }
    mockGetHoldings.mockResolvedValue(holdingsWithZeroChange)
    mockGetHoldingsHistory.mockResolvedValue(MOCK_HISTORY)

    render(<InstitutionalPositioning ticker="AAPL" />)

    await waitFor(() => {
      expect(screen.getByText("Berkshire Hathaway")).toBeInTheDocument()
    })

    // Zero change should render as "0"
    expect(screen.getByText("0")).toBeInTheDocument()
  })
})
