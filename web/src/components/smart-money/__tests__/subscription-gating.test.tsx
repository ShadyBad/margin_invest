import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen } from "@testing-library/react"

// Mock useSubscriptionTier before importing components
const mockUseSubscriptionTier = vi.fn()
vi.mock("@/lib/hooks/use-subscription-tier", () => ({
  useSubscriptionTier: () => mockUseSubscriptionTier(),
}))

// Mock AppShell to passthrough
vi.mock("@/components/layout", () => ({
  AppShell: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}))

// Mock the smart-money tab components to avoid their internal fetches
vi.mock("@/components/smart-money/fund-tracker", () => ({
  FundTracker: () => <div data-testid="fund-tracker-content">Fund Tracker Content</div>,
}))
vi.mock("@/components/smart-money/market-signals", () => ({
  MarketSignals: () => <div data-testid="market-signals-content">Market Signals Content</div>,
}))
vi.mock("@/components/smart-money/clone-lab", () => ({
  CloneLab: () => <div data-testid="clone-lab-content">Clone Lab Content</div>,
}))

import SmartMoneyPage from "@/app/smart-money/page"

describe("Smart Money page subscription gating", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("renders tab content normally for pro tier users", () => {
    mockUseSubscriptionTier.mockReturnValue({ tier: "pro", loading: false })

    render(<SmartMoneyPage />)

    // Header should be visible
    expect(screen.getByText("Smart Money")).toBeInTheDocument()
    expect(
      screen.getByText("Track institutional 13F filings and fund positioning")
    ).toBeInTheDocument()

    // Tab content should render without blur
    expect(screen.getByTestId("fund-tracker-content")).toBeInTheDocument()
    expect(screen.queryByTestId("pro-gate-overlay")).not.toBeInTheDocument()
  })

  it("shows blur overlay and upgrade CTA for free tier users", () => {
    mockUseSubscriptionTier.mockReturnValue({ tier: "free", loading: false })

    render(<SmartMoneyPage />)

    // Header should still be visible (not gated)
    expect(screen.getByText("Smart Money")).toBeInTheDocument()
    expect(
      screen.getByText("Track institutional 13F filings and fund positioning")
    ).toBeInTheDocument()

    // Tab content should be blurred
    expect(screen.getByTestId("pro-gate-overlay")).toBeInTheDocument()

    // CTA text should be visible
    expect(screen.getByText(/unlock institutional-grade analytics/i)).toBeInTheDocument()
  })

  it("renders content normally during loading state (no flash)", () => {
    mockUseSubscriptionTier.mockReturnValue({ tier: "free", loading: true })

    render(<SmartMoneyPage />)

    // During loading, ProGate renders children without blur
    expect(screen.getByTestId("fund-tracker-content")).toBeInTheDocument()
    expect(screen.queryByTestId("pro-gate-overlay")).not.toBeInTheDocument()
  })
})
