import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
import DashboardPage from "../page"
import type { DashboardResponse } from "@/lib/api/types"

const mockGetDashboard = vi.fn()

vi.mock("@/lib/api/dashboard", () => ({
  getDashboard: (...args: unknown[]) => mockGetDashboard(...args),
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

describe("Dashboard Page", () => {
  beforeEach(() => {
    mockGetDashboard.mockReset()
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
})
