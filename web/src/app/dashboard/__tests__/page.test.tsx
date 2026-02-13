import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import DashboardPage from "../page"
import type { DashboardResponse, ScoreResponse } from "@/lib/api/types"

const mockGetDashboard = vi.fn()
const mockGetScore = vi.fn()

vi.mock("@/lib/api/dashboard", () => ({
  getDashboard: (...args: unknown[]) => mockGetDashboard(...args),
}))

vi.mock("@/lib/api/scores", () => ({
  getScore: (...args: unknown[]) => mockGetScore(...args),
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
  usePathname: () => "/dashboard",
}))

const mockDashboardData: DashboardResponse = {
  picks: [
    {
      ticker: "AAPL",
      name: "Apple Inc.",
      composite_percentile: 92,
      conviction_level: "exceptional",
      signal: "buy",
      quality_percentile: 88,
      value_percentile: 72,
      momentum_percentile: 95,
    },
    {
      ticker: "MSFT",
      name: "Microsoft Corporation",
      composite_percentile: 85,
      conviction_level: "high",
      signal: "buy",
      quality_percentile: 90,
      value_percentile: 65,
      momentum_percentile: 80,
    },
  ],
  watchlist: [
    {
      ticker: "GOOG",
      name: "Alphabet Inc.",
      composite_percentile: 68,
      conviction_level: "watchlist",
    },
    {
      ticker: "AMZN",
      name: "Amazon.com Inc.",
      composite_percentile: 62,
      conviction_level: "watchlist",
    },
  ],
  last_updated: "2026-02-12T10:30:00Z",
  total_scored: 500,
}

const mockScoreData: ScoreResponse = {
  ticker: "AAPL",
  name: "Apple Inc.",
  composite_percentile: 92,
  conviction_level: "exceptional",
  signal: "buy",
  quality_percentile: 88,
  value_percentile: 72,
  momentum_percentile: 95,
  growth_stage: "mature",
  factor_breakdown: {
    quality: {
      factor_name: "quality",
      weight: 0.4,
      average_percentile: 88,
      sub_scores: [
        { name: "ROE", raw_value: 1.45, percentile: 92, weight: 0.5 },
        { name: "Debt/Equity", raw_value: 0.32, percentile: 84, weight: 0.5 },
      ],
    },
    value: {
      factor_name: "value",
      weight: 0.3,
      average_percentile: 72,
      sub_scores: [
        { name: "P/E", raw_value: 18.5, percentile: 70, weight: 0.5 },
        { name: "P/B", raw_value: 3.2, percentile: 74, weight: 0.5 },
      ],
    },
    momentum: {
      factor_name: "momentum",
      weight: 0.3,
      average_percentile: 95,
      sub_scores: [
        { name: "12M Return", raw_value: 0.35, percentile: 96, weight: 0.5 },
        { name: "6M Return", raw_value: 0.2, percentile: 94, weight: 0.5 },
      ],
    },
  },
  filters_passed: [
    { name: "Minimum Market Cap", passed: true },
    { name: "Minimum Volume", passed: true },
    { name: "Not Penny Stock", passed: true, reason: "Price > $5" },
  ],
  scored_at: "2026-02-12T08:00:00Z",
  data_coverage: 0.95,
}

describe("Dashboard Page", () => {
  beforeEach(() => {
    mockGetDashboard.mockReset()
    mockGetScore.mockReset()
  })

  it("renders loading skeleton while data is being fetched", () => {
    mockGetDashboard.mockReturnValue(new Promise(() => {}))
    render(<DashboardPage />)

    expect(screen.getByTestId("loading-skeleton")).toBeInTheDocument()
  })

  it("renders the dashboard heading", async () => {
    mockGetDashboard.mockResolvedValue(mockDashboardData)
    render(<DashboardPage />)

    expect(
      screen.getByRole("heading", { level: 1, name: "Dashboard" }),
    ).toBeInTheDocument()
  })

  it("renders picks when data loads", async () => {
    mockGetDashboard.mockResolvedValue(mockDashboardData)
    render(<DashboardPage />)

    await waitFor(() => {
      expect(screen.getByTestId("picks-grid")).toBeInTheDocument()
    })

    expect(screen.getByTestId("stock-card-AAPL")).toBeInTheDocument()
    expect(screen.getByTestId("stock-card-MSFT")).toBeInTheDocument()
    expect(screen.getByText("Apple Inc.")).toBeInTheDocument()
    expect(screen.getByText("Microsoft Corporation")).toBeInTheDocument()
  })

  it("sorts picks by composite_percentile descending", async () => {
    mockGetDashboard.mockResolvedValue(mockDashboardData)
    render(<DashboardPage />)

    await waitFor(() => {
      expect(screen.getByTestId("picks-grid")).toBeInTheDocument()
    })

    const grid = screen.getByTestId("picks-grid")
    const cards = grid.children
    expect(cards[0]).toHaveAttribute("data-testid", "stock-card-AAPL")
    expect(cards[1]).toHaveAttribute("data-testid", "stock-card-MSFT")
  })

  it("renders watchlist section", async () => {
    mockGetDashboard.mockResolvedValue(mockDashboardData)
    render(<DashboardPage />)

    await waitFor(() => {
      expect(screen.getByTestId("watchlist-table")).toBeInTheDocument()
    })

    expect(screen.getByTestId("watchlist-row-GOOG")).toBeInTheDocument()
    expect(screen.getByTestId("watchlist-row-AMZN")).toBeInTheDocument()
    expect(screen.getByText("Alphabet Inc.")).toBeInTheDocument()
    expect(screen.getByText("Amazon.com Inc.")).toBeInTheDocument()
  })

  it("displays last updated timestamp", async () => {
    mockGetDashboard.mockResolvedValue(mockDashboardData)
    render(<DashboardPage />)

    await waitFor(() => {
      expect(screen.getByText(/Last updated:/)).toBeInTheDocument()
    })
  })

  it("shows empty state when no picks are available", async () => {
    mockGetDashboard.mockResolvedValue({
      ...mockDashboardData,
      picks: [],
      watchlist: [],
    })
    render(<DashboardPage />)

    await waitFor(() => {
      expect(screen.getByText("No picks yet")).toBeInTheDocument()
    })

    expect(
      screen.getByText(
        "Scored stocks with exceptional or high conviction will appear here.",
      ),
    ).toBeInTheDocument()
  })

  it("shows error message on fetch failure", async () => {
    mockGetDashboard.mockRejectedValue(new Error("Network error"))
    render(<DashboardPage />)

    await waitFor(() => {
      expect(screen.getByText("Network error")).toBeInTheDocument()
    })
  })

  it("renders composite scores with gold styling", async () => {
    mockGetDashboard.mockResolvedValue(mockDashboardData)
    render(<DashboardPage />)

    await waitFor(() => {
      expect(screen.getByTestId("stock-card-AAPL")).toBeInTheDocument()
    })

    const aaplCard = screen.getByTestId("stock-card-AAPL")
    const scoreEl = aaplCard.querySelector(".text-3xl.text-gold")
    expect(scoreEl).toBeInTheDocument()
    expect(scoreEl?.textContent).toBe("92")
  })

  it("expands stock card on click and shows detail view", async () => {
    const user = userEvent.setup()
    mockGetDashboard.mockResolvedValue(mockDashboardData)
    mockGetScore.mockResolvedValue(mockScoreData)
    render(<DashboardPage />)

    await waitFor(() => {
      expect(screen.getByTestId("stock-card-AAPL")).toBeInTheDocument()
    })

    const aaplCard = screen.getByTestId("stock-card-AAPL")
    await user.click(aaplCard)

    await waitFor(() => {
      expect(screen.getByTestId("asset-detail-AAPL")).toBeInTheDocument()
    })

    expect(mockGetScore).toHaveBeenCalledWith("AAPL")
    expect(screen.getByTestId("factor-breakdown")).toBeInTheDocument()
    expect(screen.getByTestId("filter-list")).toBeInTheDocument()
    expect(screen.getByTestId("asset-metadata")).toBeInTheDocument()
  })

  it("shows loading indicator while fetching detail data", async () => {
    const user = userEvent.setup()
    mockGetDashboard.mockResolvedValue(mockDashboardData)
    mockGetScore.mockReturnValue(new Promise(() => {}))
    render(<DashboardPage />)

    await waitFor(() => {
      expect(screen.getByTestId("stock-card-AAPL")).toBeInTheDocument()
    })

    const aaplCard = screen.getByTestId("stock-card-AAPL")
    await user.click(aaplCard)

    expect(screen.getByTestId("loading-detail-AAPL")).toBeInTheDocument()
    expect(screen.getByText("Loading details...")).toBeInTheDocument()
  })

  it("collapses stock card on second click", async () => {
    const user = userEvent.setup()
    mockGetDashboard.mockResolvedValue(mockDashboardData)
    mockGetScore.mockResolvedValue(mockScoreData)
    render(<DashboardPage />)

    await waitFor(() => {
      expect(screen.getByTestId("stock-card-AAPL")).toBeInTheDocument()
    })

    const aaplCard = screen.getByTestId("stock-card-AAPL")

    // Expand
    await user.click(aaplCard)
    await waitFor(() => {
      expect(screen.getByTestId("asset-detail-AAPL")).toBeInTheDocument()
    })

    // Collapse
    await user.click(aaplCard)
    await waitFor(() => {
      expect(screen.queryByTestId("asset-detail-AAPL")).not.toBeInTheDocument()
    })
  })

  it("displays factor breakdown with sub-scores", async () => {
    const user = userEvent.setup()
    mockGetDashboard.mockResolvedValue(mockDashboardData)
    mockGetScore.mockResolvedValue(mockScoreData)
    render(<DashboardPage />)

    await waitFor(() => {
      expect(screen.getByTestId("stock-card-AAPL")).toBeInTheDocument()
    })

    await user.click(screen.getByTestId("stock-card-AAPL"))

    await waitFor(() => {
      expect(screen.getByTestId("factor-section-quality")).toBeInTheDocument()
    })

    expect(screen.getByTestId("factor-section-value")).toBeInTheDocument()
    expect(screen.getByTestId("factor-section-momentum")).toBeInTheDocument()
    expect(screen.getByText("ROE")).toBeInTheDocument()
    expect(screen.getByText("Debt/Equity")).toBeInTheDocument()
    expect(screen.getByText("P/E")).toBeInTheDocument()
    expect(screen.getByText("P/B")).toBeInTheDocument()
  })

  it("displays filter results with pass status", async () => {
    const user = userEvent.setup()
    mockGetDashboard.mockResolvedValue(mockDashboardData)
    mockGetScore.mockResolvedValue(mockScoreData)
    render(<DashboardPage />)

    await waitFor(() => {
      expect(screen.getByTestId("stock-card-AAPL")).toBeInTheDocument()
    })

    await user.click(screen.getByTestId("stock-card-AAPL"))

    await waitFor(() => {
      expect(screen.getByTestId("filter-list")).toBeInTheDocument()
    })

    expect(screen.getByTestId("filter-Minimum Market Cap")).toBeInTheDocument()
    expect(screen.getByTestId("filter-Minimum Volume")).toBeInTheDocument()
    expect(screen.getByTestId("filter-Not Penny Stock")).toBeInTheDocument()
  })

  it("displays metadata including growth stage and data coverage", async () => {
    const user = userEvent.setup()
    mockGetDashboard.mockResolvedValue(mockDashboardData)
    mockGetScore.mockResolvedValue(mockScoreData)
    render(<DashboardPage />)

    await waitFor(() => {
      expect(screen.getByTestId("stock-card-AAPL")).toBeInTheDocument()
    })

    await user.click(screen.getByTestId("stock-card-AAPL"))

    await waitFor(() => {
      expect(screen.getByTestId("asset-metadata")).toBeInTheDocument()
    })

    expect(screen.getByText("Growth Stage")).toBeInTheDocument()
    expect(screen.getByText("mature")).toBeInTheDocument()
    expect(screen.getByText("Data Coverage")).toBeInTheDocument()
    expect(screen.getByText("95%")).toBeInTheDocument()
    expect(screen.getByText("Scored At")).toBeInTheDocument()
  })

  it("sets aria-expanded attribute on stock card", async () => {
    const user = userEvent.setup()
    mockGetDashboard.mockResolvedValue(mockDashboardData)
    mockGetScore.mockResolvedValue(mockScoreData)
    render(<DashboardPage />)

    await waitFor(() => {
      expect(screen.getByTestId("stock-card-AAPL")).toBeInTheDocument()
    })

    const aaplCard = screen.getByTestId("stock-card-AAPL")
    expect(aaplCard).toHaveAttribute("aria-expanded", "false")

    await user.click(aaplCard)
    expect(aaplCard).toHaveAttribute("aria-expanded", "true")

    await waitFor(() => {
      expect(screen.getByTestId("asset-detail-AAPL")).toBeInTheDocument()
    })

    await user.click(aaplCard)
    expect(aaplCard).toHaveAttribute("aria-expanded", "false")
  })
})
