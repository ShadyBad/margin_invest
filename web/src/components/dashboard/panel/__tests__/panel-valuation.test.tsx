import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, fireEvent, waitFor } from "@testing-library/react"
import { PanelValuation } from "../panel-valuation"
import type { ValuationAuditResponse } from "@/lib/api/types"

// Mock the API module
vi.mock("@/lib/api/scores", () => ({
  getValuationAudit: vi.fn(),
}))

import { getValuationAudit } from "@/lib/api/scores"

const mockAuditResponse: ValuationAuditResponse = {
  margin_invest_value: 28.5,
  margin_of_safety: 0.26,
  buy_price: 22.0,
  sell_price: 35.0,
  actual_price: 21.0,
  methods: [
    {
      method: "dcf",
      result_per_share: 32.1,
      weight: 0.4,
      renormalized_weight: 0.45,
      included: true,
      exclusion_reason: null,
      inputs: { free_cash_flow: 5_000_000_000, growth_rate: 0.08, shares_outstanding: 1_500_000_000 },
      intermediates: { pv_stage_1: 25_000_000_000, terminal_value: 80_000_000_000 },
    },
    {
      method: "ev_fcf",
      result_per_share: 24.8,
      weight: 0.3,
      renormalized_weight: 0.33,
      included: true,
      exclusion_reason: null,
      inputs: { enterprise_value: 40_000_000_000 },
      intermediates: {},
    },
    {
      method: "acquirers_multiple",
      result_per_share: null,
      weight: 0.2,
      renormalized_weight: null,
      included: false,
      exclusion_reason: "Negative EBIT",
      inputs: {},
      intermediates: {},
    },
    {
      method: "shareholder_yield",
      result_per_share: 27.2,
      weight: 0.1,
      renormalized_weight: 0.22,
      included: true,
      exclusion_reason: null,
      inputs: {},
      intermediates: {},
    },
  ],
  mos_base: 0.3,
  mos_cv: 0.12,
  mos_adjustment: -0.04,
  was_clamped: false,
  clamp_reason: null,
}

describe("PanelValuation", () => {
  const baseProps = {
    intrinsicValue: 28.5,
    currentPrice: 21.0,
    marginOfSafety: 0.26,
    methods: { dcf: 32.1, ev_fcf: 24.8, acquirers_multiple: 28.9, shareholder_yield: 27.2 },
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("renders Margin Invest Value", () => {
    render(<PanelValuation {...baseProps} />)
    expect(screen.getByText("Margin Invest Value")).toBeInTheDocument()
    expect(screen.getByText("$28.50")).toBeInTheDocument()
  })

  it("renders current price and margin of safety in header trio", () => {
    render(<PanelValuation {...baseProps} />)
    expect(screen.getByText("Current Price")).toBeInTheDocument()
    expect(screen.getByText("$21.00")).toBeInTheDocument()
    expect(screen.getByText("Margin of Safety")).toBeInTheDocument()
    expect(screen.getByText("26%")).toBeInTheDocument()
  })

  it("renders all valuation method bars", () => {
    render(<PanelValuation {...baseProps} />)
    expect(screen.getByText("DCF Model")).toBeInTheDocument()
    expect(screen.getByText("EV/FCF")).toBeInTheDocument()
    expect(screen.getByText("EV/EBIT")).toBeInTheDocument()
    expect(screen.getByText("Shareholder Yield")).toBeInTheDocument()
  })

  it("renders empty state when no methods and no intrinsic value", () => {
    render(<PanelValuation {...baseProps} intrinsicValue={null} methods={{}} />)
    expect(screen.getByText("No valuation data")).toBeInTheDocument()
  })

  it("renders price ladder when buyBelow and sellPrice provided", () => {
    render(<PanelValuation {...baseProps} buyBelow={22.0} sellPrice={35.0} />)
    expect(screen.getByText("Buy Zone")).toBeInTheDocument()
    expect(screen.getByText("Hold Zone")).toBeInTheDocument()
    expect(screen.getByText("Sell Zone")).toBeInTheDocument()
  })

  it("does not render price ladder when buyBelow is null", () => {
    render(<PanelValuation {...baseProps} buyBelow={null} sellPrice={35.0} />)
    expect(screen.queryByText("Buy Zone")).not.toBeInTheDocument()
  })

  it("does not render price ladder when sellPrice is null", () => {
    render(<PanelValuation {...baseProps} buyBelow={22.0} sellPrice={null} />)
    expect(screen.queryByText("Buy Zone")).not.toBeInTheDocument()
  })

  it("renders valuation methods even without intrinsic value", () => {
    render(<PanelValuation {...baseProps} intrinsicValue={null} />)
    expect(screen.getByText("DCF Model")).toBeInTheDocument()
    expect(screen.queryByText("Margin Invest Value")).not.toBeInTheDocument()
  })

  it("method bars are clickable with cursor-pointer", () => {
    render(<PanelValuation {...baseProps} ticker="AAPL" />)
    const dcfBar = screen.getByTestId("method-bar-dcf")
    expect(dcfBar).toHaveClass("cursor-pointer")
  })

  it("clicking a method bar shows loading state then audit detail", async () => {
    const mockGetAudit = vi.mocked(getValuationAudit)
    mockGetAudit.mockResolvedValueOnce(mockAuditResponse)

    render(<PanelValuation {...baseProps} ticker="AAPL" />)
    const dcfBar = screen.getByTestId("method-bar-dcf")
    fireEvent.click(dcfBar)

    // Loading state appears
    expect(screen.getByText("Loading audit data...")).toBeInTheDocument()

    // Wait for audit data to load
    await waitFor(() => {
      expect(screen.getByTestId("method-audit-detail")).toBeInTheDocument()
    })

    // Verify audit detail content
    expect(screen.getByText("Included")).toBeInTheDocument()
    expect(screen.getByText("Result: $32.10")).toBeInTheDocument()
    expect(screen.getByText("Weight: 40%")).toBeInTheDocument()
    expect(screen.getByText("Renorm: 45.0%")).toBeInTheDocument()
  })

  it("clicking an excluded method shows exclusion reason", async () => {
    const mockGetAudit = vi.mocked(getValuationAudit)
    mockGetAudit.mockResolvedValueOnce(mockAuditResponse)

    render(<PanelValuation {...baseProps} ticker="AAPL" />)

    // First click DCF to load the audit data
    fireEvent.click(screen.getByTestId("method-bar-dcf"))
    await waitFor(() => {
      expect(screen.getByTestId("method-audit-detail")).toBeInTheDocument()
    })

    // Collapse DCF
    fireEvent.click(screen.getByTestId("method-bar-dcf"))
    expect(screen.queryByTestId("method-audit-detail")).not.toBeInTheDocument()

    // Click acquirers_multiple (excluded method)
    fireEvent.click(screen.getByTestId("method-bar-acquirers_multiple"))
    await waitFor(() => {
      expect(screen.getByTestId("method-audit-detail")).toBeInTheDocument()
    })

    expect(screen.getByText("Excluded")).toBeInTheDocument()
    expect(screen.getByText("Negative EBIT")).toBeInTheDocument()
  })

  it("toggles expansion off when clicking same method bar again", async () => {
    const mockGetAudit = vi.mocked(getValuationAudit)
    mockGetAudit.mockResolvedValueOnce(mockAuditResponse)

    render(<PanelValuation {...baseProps} ticker="AAPL" />)
    const dcfBar = screen.getByTestId("method-bar-dcf")

    // First click — expand
    fireEvent.click(dcfBar)
    await waitFor(() => {
      expect(screen.getByTestId("method-audit-detail")).toBeInTheDocument()
    })

    // Second click — collapse
    fireEvent.click(dcfBar)
    expect(screen.queryByTestId("method-audit-detail")).not.toBeInTheDocument()
  })

  it("does not fetch audit data when ticker is not provided", () => {
    const mockGetAudit = vi.mocked(getValuationAudit)

    render(<PanelValuation {...baseProps} />)
    fireEvent.click(screen.getByTestId("method-bar-dcf"))

    expect(mockGetAudit).not.toHaveBeenCalled()
  })

  it("only fetches audit data once across multiple expansions", async () => {
    const mockGetAudit = vi.mocked(getValuationAudit)
    mockGetAudit.mockResolvedValueOnce(mockAuditResponse)

    render(<PanelValuation {...baseProps} ticker="AAPL" />)

    // First click — fetches
    fireEvent.click(screen.getByTestId("method-bar-dcf"))
    await waitFor(() => {
      expect(screen.getByTestId("method-audit-detail")).toBeInTheDocument()
    })

    // Collapse
    fireEvent.click(screen.getByTestId("method-bar-dcf"))

    // Expand another — should NOT fetch again
    fireEvent.click(screen.getByTestId("method-bar-ev_fcf"))
    await waitFor(() => {
      expect(screen.getByTestId("method-audit-detail")).toBeInTheDocument()
    })

    expect(mockGetAudit).toHaveBeenCalledTimes(1)
  })

  it("renders input and intermediate values with large number formatting", async () => {
    const mockGetAudit = vi.mocked(getValuationAudit)
    mockGetAudit.mockResolvedValueOnce(mockAuditResponse)

    render(<PanelValuation {...baseProps} ticker="AAPL" />)
    fireEvent.click(screen.getByTestId("method-bar-dcf"))

    await waitFor(() => {
      expect(screen.getByTestId("method-audit-detail")).toBeInTheDocument()
    })

    // Check inputs are rendered with formatted labels
    expect(screen.getByText("Free Cash Flow")).toBeInTheDocument()
    expect(screen.getByText("5.00B")).toBeInTheDocument()
    expect(screen.getByText("Growth Rate")).toBeInTheDocument()

    // Check intermediates
    expect(screen.getByText("Pv Stage 1")).toBeInTheDocument()
    expect(screen.getByText("25.00B")).toBeInTheDocument()
    expect(screen.getByText("Terminal Value")).toBeInTheDocument()
    expect(screen.getByText("80.00B")).toBeInTheDocument()
  })
})
