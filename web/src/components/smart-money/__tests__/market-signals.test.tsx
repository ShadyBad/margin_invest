import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
import { MarketSignals } from "../market-signals"

const mockGetOverlap = vi.fn()
const mockGetNewPositions = vi.fn()

vi.mock("@/lib/api/thirteenf", () => ({
  getOverlap: (...args: unknown[]) => mockGetOverlap(...args),
  getNewPositions: (...args: unknown[]) => mockGetNewPositions(...args),
}))

const MOCK_OVERLAP = {
  period_of_report: "2025-09-30",
  most_held: [
    { ticker: "AAPL", holder_count: 45, curated_count: 12 },
    { ticker: "MSFT", holder_count: 42, curated_count: 10 },
    { ticker: "GOOGL", holder_count: 38, curated_count: 8 },
  ],
  crowded_trades: [
    { ticker: "NVDA", holder_count: 8, concentration_pct: 0.32, total_value_millions: 1200.5 },
    { ticker: "META", holder_count: 5, concentration_pct: 0.2, total_value_millions: 850.0 },
  ],
  total_managers: 25,
}

const MOCK_NEW_POSITIONS = {
  period_of_report: "2025-09-30",
  previous_quarter: "2025-06-30",
  new_positions: [
    {
      ticker: "PLTR",
      managers: ["Soros Fund Management", "Baupost Group"],
      total_new_funds: 3,
      curated_new_funds: 2,
      total_value_millions: 245.3,
    },
  ],
}

const MOCK_EMPTY_NEW_POSITIONS = {
  period_of_report: "2025-09-30",
  previous_quarter: "2025-06-30",
  new_positions: [],
}

describe("MarketSignals", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("renders most held positions table", async () => {
    mockGetOverlap.mockResolvedValue(MOCK_OVERLAP)
    mockGetNewPositions.mockResolvedValue(MOCK_NEW_POSITIONS)

    render(<MarketSignals />)

    await waitFor(() => {
      expect(screen.getByText("AAPL")).toBeInTheDocument()
    })

    expect(screen.getByText("MSFT")).toBeInTheDocument()
    expect(screen.getByText("GOOGL")).toBeInTheDocument()

    // Holder counts
    expect(screen.getByText("45")).toBeInTheDocument()
    expect(screen.getByText("42")).toBeInTheDocument()
  })

  it("renders empty state for new positions when array is empty", async () => {
    mockGetOverlap.mockResolvedValue(MOCK_OVERLAP)
    mockGetNewPositions.mockResolvedValue(MOCK_EMPTY_NEW_POSITIONS)

    render(<MarketSignals />)

    await waitFor(() => {
      expect(screen.getByText("AAPL")).toBeInTheDocument()
    })

    expect(
      screen.getByText("No data available for this quarter")
    ).toBeInTheDocument()
  })

  it("renders new positions when available", async () => {
    mockGetOverlap.mockResolvedValue(MOCK_OVERLAP)
    mockGetNewPositions.mockResolvedValue(MOCK_NEW_POSITIONS)

    render(<MarketSignals />)

    await waitFor(() => {
      expect(screen.getByText("PLTR")).toBeInTheDocument()
    })

    expect(screen.getByText("Soros Fund Management")).toBeInTheDocument()
    expect(screen.getByText("Baupost Group")).toBeInTheDocument()
  })

  it("renders crowded trades when available", async () => {
    mockGetOverlap.mockResolvedValue(MOCK_OVERLAP)
    mockGetNewPositions.mockResolvedValue(MOCK_NEW_POSITIONS)

    render(<MarketSignals />)

    await waitFor(() => {
      expect(screen.getByText("NVDA")).toBeInTheDocument()
    })

    expect(screen.getByText("META")).toBeInTheDocument()
    // concentration_pct displayed as percentage
    expect(screen.getByText("32.0%")).toBeInTheDocument()
  })

  it("renders crowded trades empty state when array is empty", async () => {
    mockGetOverlap.mockResolvedValue({
      ...MOCK_OVERLAP,
      crowded_trades: [],
    })
    mockGetNewPositions.mockResolvedValue(MOCK_NEW_POSITIONS)

    render(<MarketSignals />)

    await waitFor(() => {
      expect(screen.getByText("AAPL")).toBeInTheDocument()
    })

    expect(
      screen.getByTestId("crowded-trades-empty")
    ).toBeInTheDocument()
  })

  it("loading state shows skeleton", () => {
    mockGetOverlap.mockReturnValue(new Promise(() => {}))
    mockGetNewPositions.mockReturnValue(new Promise(() => {}))

    render(<MarketSignals />)

    expect(screen.getByTestId("market-signals-loading")).toBeInTheDocument()
  })

  it("renders empty state when all data fails", async () => {
    mockGetOverlap.mockRejectedValue(new Error("Network error"))
    mockGetNewPositions.mockRejectedValue(new Error("Network error"))

    render(<MarketSignals />)

    await waitFor(() => {
      expect(screen.getByText("No market signals data available")).toBeInTheDocument()
    })
  })
})
