import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { FundTracker } from "../fund-tracker"

const mockGetManagers = vi.fn()
const mockGetManagerPortfolio = vi.fn()

vi.mock("@/lib/api/thirteenf", () => ({
  getManagers: (...args: unknown[]) => mockGetManagers(...args),
  getManagerPortfolio: (...args: unknown[]) => mockGetManagerPortfolio(...args),
}))

const MOCK_MANAGERS = [
  {
    id: 1,
    name: "Berkshire Hathaway",
    tier: "curated",
    aum_millions: 350000,
    total_holdings: 42,
    top_positions: ["AAPL", "BAC", "CVX"],
    last_filing: "2025-11-15",
    period_of_report: "2025-09-30",
  },
  {
    id: 2,
    name: "Bridgewater Associates",
    tier: "top_aum",
    aum_millions: 150000,
    total_holdings: 120,
    top_positions: ["SPY", "TLT", "GLD", "EEM", "VWO"],
    last_filing: "2025-11-14",
    period_of_report: "2025-09-30",
  },
]

const MOCK_PORTFOLIO = {
  manager: "Berkshire Hathaway",
  period_of_report: "2025-09-30",
  aum_millions: 350000,
  holdings: [
    {
      ticker: "AAPL",
      cusip: "037833100",
      shares_held: 915560382,
      value_millions: 75400,
      pct_portfolio: 48.2,
      shares_changed: 12340000,
      is_new_position: false,
    },
    {
      ticker: "BAC",
      cusip: "060505104",
      shares_held: 1032000000,
      value_millions: 34200,
      pct_portfolio: 21.8,
      shares_changed: -5000000,
      is_new_position: false,
    },
  ],
  changes_summary: {
    new_positions: ["OXY"],
    exited_positions: ["TSLA"],
    increased: 10,
    decreased: 5,
    unchanged: 27,
  },
}

describe("FundTracker", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("renders manager table with name, tier, and AUM", async () => {
    mockGetManagers.mockResolvedValue(MOCK_MANAGERS)

    render(<FundTracker />)

    await waitFor(() => {
      expect(screen.getByText("Berkshire Hathaway")).toBeInTheDocument()
    })

    expect(screen.getByText("Bridgewater Associates")).toBeInTheDocument()

    // Tier badges
    expect(screen.getByText("curated")).toBeInTheDocument()
    expect(screen.getByText("top_aum")).toBeInTheDocument()

    // AUM values
    expect(screen.getByText("$350,000M")).toBeInTheDocument()
    expect(screen.getByText("$150,000M")).toBeInTheDocument()
  })

  it("renders top position pills for each manager", async () => {
    mockGetManagers.mockResolvedValue(MOCK_MANAGERS)

    render(<FundTracker />)

    await waitFor(() => {
      expect(screen.getByText("Berkshire Hathaway")).toBeInTheDocument()
    })

    // Berkshire top positions
    expect(screen.getByText("AAPL")).toBeInTheDocument()
    expect(screen.getByText("BAC")).toBeInTheDocument()
    expect(screen.getByText("CVX")).toBeInTheDocument()
  })

  it("row expansion fetches and shows portfolio", async () => {
    mockGetManagers.mockResolvedValue(MOCK_MANAGERS)
    mockGetManagerPortfolio.mockResolvedValue(MOCK_PORTFOLIO)

    const user = userEvent.setup()
    render(<FundTracker />)

    await waitFor(() => {
      expect(screen.getByText("Berkshire Hathaway")).toBeInTheDocument()
    })

    // Click the row to expand
    await user.click(screen.getByTestId("manager-row-1"))

    await waitFor(() => {
      expect(mockGetManagerPortfolio).toHaveBeenCalledWith(1)
    })

    // Portfolio details should show
    await waitFor(() => {
      expect(screen.getByText("48.2%")).toBeInTheDocument()
    })

    // Changes summary
    expect(screen.getByText(/new positions/i)).toBeInTheDocument()
    expect(screen.getByText(/exited positions/i)).toBeInTheDocument()
  })

  it("loading state shows skeleton", () => {
    mockGetManagers.mockReturnValue(new Promise(() => {}))

    render(<FundTracker />)

    expect(screen.getByTestId("fund-tracker-loading")).toBeInTheDocument()
  })

  it("empty state message when no managers", async () => {
    mockGetManagers.mockResolvedValue([])

    render(<FundTracker />)

    await waitFor(() => {
      expect(screen.getByText("No manager data available")).toBeInTheDocument()
    })
  })
})
