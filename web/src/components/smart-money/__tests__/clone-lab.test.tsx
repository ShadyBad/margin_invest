import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { CloneLab } from "../clone-lab"

const mockGetManagers = vi.fn()
const mockGetClonePortfolio = vi.fn()

vi.mock("@/lib/api/thirteenf", () => ({
  getManagers: (...args: any[]) => mockGetManagers(...args),
  getClonePortfolio: (...args: any[]) => mockGetClonePortfolio(...args),
}))

const MOCK_CURATED_MANAGERS = [
  {
    id: 1,
    name: "Berkshire Hathaway",
    tier: "curated",
    aum_millions: 350000,
    total_holdings: 42,
    top_positions: ["AAPL", "BAC"],
    last_filing: "2025-11-15",
    period_of_report: "2025-09-30",
  },
  {
    id: 3,
    name: "Pershing Square",
    tier: "curated",
    aum_millions: 18000,
    total_holdings: 8,
    top_positions: ["CMG", "HLT"],
    last_filing: "2025-11-14",
    period_of_report: "2025-09-30",
  },
]

const MOCK_CLONE = {
  manager: "Berkshire Hathaway",
  strategy: "equal_weight_top_10",
  period_of_report: "2025-09-30",
  positions: [
    { ticker: "AAPL", target_weight: 0.1 },
    { ticker: "BAC", target_weight: 0.1 },
    { ticker: "CVX", target_weight: 0.1 },
    { ticker: "KO", target_weight: 0.1 },
    { ticker: "AXP", target_weight: 0.1 },
    { ticker: "OXY", target_weight: 0.1 },
    { ticker: "KHC", target_weight: 0.1 },
    { ticker: "MCO", target_weight: 0.1 },
    { ticker: "DVA", target_weight: 0.1 },
    { ticker: "ATVI", target_weight: 0.1 },
  ],
  historical_performance: null,
}

const MOCK_CLONE_WITH_PERF = {
  ...MOCK_CLONE,
  historical_performance: {
    return_1y: 0.234,
    cagr_3y: 0.156,
    max_drawdown: -0.182,
    sharpe: 1.42,
  },
}

describe("CloneLab", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("renders manager dropdown with options", async () => {
    mockGetManagers.mockResolvedValue(MOCK_CURATED_MANAGERS)

    render(<CloneLab />)

    await waitFor(() => {
      expect(screen.getByTestId("manager-select")).toBeInTheDocument()
    })

    const select = screen.getByTestId("manager-select") as HTMLSelectElement
    // Default option + 2 managers
    expect(select.options.length).toBe(3)
    expect(select.options[1].textContent).toBe("Berkshire Hathaway")
    expect(select.options[2].textContent).toBe("Pershing Square")
  })

  it("strategy selector changes active strategy", async () => {
    mockGetManagers.mockResolvedValue(MOCK_CURATED_MANAGERS)
    mockGetClonePortfolio.mockResolvedValue(MOCK_CLONE)

    const user = userEvent.setup()
    render(<CloneLab />)

    await waitFor(() => {
      expect(screen.getByTestId("manager-select")).toBeInTheDocument()
    })

    // All 3 strategy options should be present
    expect(screen.getByLabelText("Equal-weight top 10")).toBeInTheDocument()
    expect(screen.getByLabelText("Equal-weight top 20")).toBeInTheDocument()
    expect(screen.getByLabelText("Market-cap weighted")).toBeInTheDocument()

    // Select a manager first
    await user.selectOptions(screen.getByTestId("manager-select"), "1")

    await waitFor(() => {
      expect(mockGetClonePortfolio).toHaveBeenCalledWith(1, "equal_weight_top_10")
    })

    // Change strategy
    await user.click(screen.getByLabelText("Equal-weight top 20"))

    await waitFor(() => {
      expect(mockGetClonePortfolio).toHaveBeenCalledWith(1, "equal_weight_top_20")
    })
  })

  it("portfolio table renders positions with weights", async () => {
    mockGetManagers.mockResolvedValue(MOCK_CURATED_MANAGERS)
    mockGetClonePortfolio.mockResolvedValue(MOCK_CLONE)

    const user = userEvent.setup()
    render(<CloneLab />)

    await waitFor(() => {
      expect(screen.getByTestId("manager-select")).toBeInTheDocument()
    })

    await user.selectOptions(screen.getByTestId("manager-select"), "1")

    await waitFor(() => {
      expect(screen.getByText("AAPL")).toBeInTheDocument()
    })

    expect(screen.getByText("BAC")).toBeInTheDocument()
    // Weight displayed as percentage
    expect(screen.getAllByText("10.0%").length).toBeGreaterThan(0)
  })

  it("disclaimer always visible", async () => {
    mockGetManagers.mockResolvedValue(MOCK_CURATED_MANAGERS)

    render(<CloneLab />)

    await waitFor(() => {
      expect(screen.getByTestId("manager-select")).toBeInTheDocument()
    })

    expect(screen.getByTestId("clone-disclaimer")).toBeInTheDocument()
    expect(
      screen.getByText(/clone portfolios are based on 13f filings/i)
    ).toBeInTheDocument()
  })

  it("empty state when no manager selected", async () => {
    mockGetManagers.mockResolvedValue(MOCK_CURATED_MANAGERS)

    render(<CloneLab />)

    await waitFor(() => {
      expect(screen.getByTestId("manager-select")).toBeInTheDocument()
    })

    expect(
      screen.getByText("Select a manager to generate a clone portfolio")
    ).toBeInTheDocument()
  })

  it("shows performance data not yet available when null", async () => {
    mockGetManagers.mockResolvedValue(MOCK_CURATED_MANAGERS)
    mockGetClonePortfolio.mockResolvedValue(MOCK_CLONE)

    const user = userEvent.setup()
    render(<CloneLab />)

    await waitFor(() => {
      expect(screen.getByTestId("manager-select")).toBeInTheDocument()
    })

    await user.selectOptions(screen.getByTestId("manager-select"), "1")

    await waitFor(() => {
      expect(screen.getByText("AAPL")).toBeInTheDocument()
    })

    expect(
      screen.getByText("Performance data not yet available")
    ).toBeInTheDocument()
  })

  it("shows performance data when available", async () => {
    mockGetManagers.mockResolvedValue(MOCK_CURATED_MANAGERS)
    mockGetClonePortfolio.mockResolvedValue(MOCK_CLONE_WITH_PERF)

    const user = userEvent.setup()
    render(<CloneLab />)

    await waitFor(() => {
      expect(screen.getByTestId("manager-select")).toBeInTheDocument()
    })

    await user.selectOptions(screen.getByTestId("manager-select"), "1")

    await waitFor(() => {
      expect(screen.getByText("AAPL")).toBeInTheDocument()
    })

    // Performance metrics should be displayed
    expect(screen.getByText("23.4%")).toBeInTheDocument() // 1y return
    expect(screen.getByText("15.6%")).toBeInTheDocument() // 3y CAGR
    expect(screen.getByText("1.42")).toBeInTheDocument() // sharpe
  })
})
