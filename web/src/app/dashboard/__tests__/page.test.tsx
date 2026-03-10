import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen } from "@testing-library/react"

// Mock auth
const mockAuth = vi.fn()
vi.mock("@/lib/auth", () => ({
  auth: () => mockAuth(),
}))

// Mock redirect
const mockRedirect = vi.fn()
vi.mock("next/navigation", () => ({
  redirect: (path: string) => {
    mockRedirect(path)
    throw new Error(`NEXT_REDIRECT: ${path}`)
  },
  usePathname: () => "/dashboard",
  useRouter: () => ({ push: vi.fn() }),
}))

// Mock serverFetch
const mockServerFetch = vi.fn()
vi.mock("@/lib/api/server", () => ({
  serverFetch: (...args: unknown[]) => mockServerFetch(...args),
}))

// Mock next-auth/react for child components that may use it
vi.mock("next-auth/react", () => ({
  useSession: () => ({
    data: { user: { name: "Test User" } },
    status: "authenticated",
  }),
  signOut: vi.fn(),
}))

// Mock getScore for StockCard child component
vi.mock("@/lib/api/scores", () => ({
  getScore: vi.fn(),
}))

import type { DashboardResponse } from "@/lib/api/types"

const mockDashboardData: DashboardResponse = {
  picks: [
    {
      score_id: 1,
      ticker: "AAPL",
      name: "Apple Inc.",
      score: 82,
      universe_percentile: 92,
      composite_percentile: 92,
      composite_tier: "exceptional",
      signal: "strong",
      quality_percentile: 88,
      value_percentile: 72,
      momentum_percentile: 95,
      actual_price: 185.50,
      buy_price: 150.00,
      sell_price: 210.00,
      price_upside: 13.2,
    },
    {
      score_id: 2,
      ticker: "MSFT",
      name: "Microsoft Corporation",
      score: 75,
      universe_percentile: 85,
      composite_percentile: 85,
      composite_tier: "high",
      signal: "strong",
      quality_percentile: 90,
      value_percentile: 65,
      momentum_percentile: 80,
      actual_price: 420.00,
      buy_price: 380.00,
      sell_price: 480.00,
      price_upside: 14.3,
    },
  ],
  watchlist: [
    {
      ticker: "GOOG",
      name: "Alphabet Inc.",
      composite_raw_score: 68,
      composite_tier: "medium",
      sector: "Communication Services",
      actual_price: 175.50,
      price_upside: 0.12,
    },
    {
      ticker: "AMZN",
      name: "Amazon.com Inc.",
      composite_raw_score: 62,
      composite_tier: "medium",
      sector: "Consumer Discretionary",
      actual_price: 185.00,
      price_upside: 0.08,
    },
  ],
  last_updated: "2026-02-12T10:30:00Z",
  total_scored: 500,
  universe: null,
}

describe("Dashboard Page (Server Component)", () => {
  beforeEach(() => {
    mockAuth.mockReset()
    mockServerFetch.mockReset()
    mockRedirect.mockReset()
  })

  it("redirects to /login when not authenticated", async () => {
    mockAuth.mockResolvedValue(null)

    const DashboardPage = (await import("../page")).default

    await expect(DashboardPage()).rejects.toThrow("NEXT_REDIRECT: /login")
    expect(mockRedirect).toHaveBeenCalledWith("/login")
  })

  it("renders picks and watchlist when authenticated", async () => {
    mockAuth.mockResolvedValue({ userId: "user-123" })
    mockServerFetch.mockResolvedValue(mockDashboardData)

    const DashboardPage = (await import("../page")).default
    const jsx = await DashboardPage()
    render(jsx)

    expect(screen.getByTestId("dashboard-greeting")).toBeInTheDocument()
    expect(screen.getByRole("heading", { level: 1 })).toBeInTheDocument()
    expect(screen.getByTestId("picks-grid")).toBeInTheDocument()
    expect(screen.getByTestId("stock-card-AAPL")).toBeInTheDocument()
    expect(screen.getByTestId("stock-card-MSFT")).toBeInTheDocument()
    expect(screen.getByText("Apple Inc.")).toBeInTheDocument()
  })

  it("sorts picks by composite_percentile descending", async () => {
    mockAuth.mockResolvedValue({ userId: "user-123" })
    mockServerFetch.mockResolvedValue(mockDashboardData)

    const DashboardPage = (await import("../page")).default
    const jsx = await DashboardPage()
    render(jsx)

    const grid = screen.getByTestId("picks-grid")
    const cards = grid.querySelectorAll("[data-testid^='stock-card-']")
    expect(cards[0]).toHaveAttribute("data-testid", "stock-card-AAPL")
    expect(cards[1]).toHaveAttribute("data-testid", "stock-card-MSFT")
  })

  it("renders watchlist section", async () => {
    mockAuth.mockResolvedValue({ userId: "user-123" })
    mockServerFetch.mockResolvedValue(mockDashboardData)

    const DashboardPage = (await import("../page")).default
    const jsx = await DashboardPage()
    render(jsx)

    expect(screen.getByTestId("watchlist-picks-list")).toBeInTheDocument()
    expect(screen.getByTestId("watchlist-row-GOOG")).toBeInTheDocument()
    expect(screen.getByTestId("watchlist-row-AMZN")).toBeInTheDocument()
  })

  it("displays last updated timestamp", async () => {
    mockAuth.mockResolvedValue({ userId: "user-123" })
    mockServerFetch.mockResolvedValue(mockDashboardData)

    const DashboardPage = (await import("../page")).default
    const jsx = await DashboardPage()
    render(jsx)

    expect(screen.getByText(/Last updated:/)).toBeInTheDocument()
  })

  it("shows empty state when no picks", async () => {
    mockAuth.mockResolvedValue({ userId: "user-123" })
    mockServerFetch.mockResolvedValue({
      ...mockDashboardData,
      picks: [],
      watchlist: [],
    })

    const DashboardPage = (await import("../page")).default
    const jsx = await DashboardPage()
    render(jsx)

    expect(screen.getByText(/system is working/i)).toBeInTheDocument()
  })

  it("calls serverFetch with /api/v1/dashboard", async () => {
    mockAuth.mockResolvedValue({ userId: "user-123" })
    mockServerFetch.mockResolvedValue(mockDashboardData)

    const DashboardPage = (await import("../page")).default
    await DashboardPage()

    expect(mockServerFetch).toHaveBeenCalledWith("/api/v1/dashboard")
  })

  it("renders system status strip", async () => {
    mockAuth.mockResolvedValue({ userId: "user-123" })
    mockServerFetch.mockResolvedValue(mockDashboardData)

    const DashboardPage = (await import("../page")).default
    const jsx = await DashboardPage()
    render(jsx)

    expect(screen.getByTestId("system-status-strip")).toBeInTheDocument()
    expect(screen.getByText(/SCORED 500/)).toBeInTheDocument()
  })

  it("renders market context panel", async () => {
    mockAuth.mockResolvedValue({ userId: "user-123" })
    mockServerFetch.mockResolvedValue(mockDashboardData)

    const DashboardPage = (await import("../page")).default
    const jsx = await DashboardPage()
    render(jsx)

    expect(screen.getByTestId("market-context-panel")).toBeInTheDocument()
    expect(screen.getByText("Market Context")).toBeInTheDocument()
  })

  it("uses fallback data when API fails — no raw error messages shown", async () => {
    mockAuth.mockResolvedValue({ userId: "user-123", user: { name: "Test" } })
    mockServerFetch.mockRejectedValue(new Error("Connection refused"))

    const DashboardPage = (await import("../page")).default
    const jsx = await DashboardPage()
    render(jsx)

    // Should NOT show raw developer-facing error messages
    expect(screen.queryByText(/uvicorn/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/Connection refused/i)).not.toBeInTheDocument()

    // Should show fallback notice
    expect(screen.getByTestId("fallback-notice")).toBeInTheDocument()
    expect(screen.getByText(/cached data/i)).toBeInTheDocument()

    // Should still render picks from fallback data
    expect(screen.getByTestId("picks-grid")).toBeInTheDocument()
  })

  it("shows system offline in status strip when using fallback", async () => {
    mockAuth.mockResolvedValue({ userId: "user-123", user: { name: "Test" } })
    mockServerFetch.mockRejectedValue(new Error("Connection refused"))

    const DashboardPage = (await import("../page")).default
    const jsx = await DashboardPage()
    render(jsx)

    expect(screen.getByText(/SYSTEM OFFLINE/)).toBeInTheDocument()
  })
})
