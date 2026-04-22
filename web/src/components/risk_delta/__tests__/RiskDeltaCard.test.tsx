import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { RiskDeltaCard } from "../RiskDeltaCard"
import type { RiskFactorAnalysis } from "@/lib/api/risk_diffing"

const mockGetRiskFactorAnalysis = vi.fn()

vi.mock("@/lib/api/risk_diffing", () => ({
  getRiskFactorAnalysis: (...args: unknown[]) => mockGetRiskFactorAnalysis(...args),
}))

const MOCK_CHANGE_HIGH: RiskFactorAnalysis["material_changes"][0] = {
  change_type: "EXPANDED",
  topic: "Cybersecurity risk",
  severity: 8,
  summary_50_words:
    "The company expanded its cybersecurity risk disclosure significantly, citing increased threat actor activity and three new breach incidents that resulted in customer data exposure and regulatory scrutiny.",
  verbatim_new_text: "We face heightened cybersecurity threats...",
  verbatim_old_text: "We face cybersecurity threats...",
}

const MOCK_CHANGE_LOW: RiskFactorAnalysis["material_changes"][0] = {
  change_type: "NEW",
  topic: "Supply chain diversification",
  severity: 3,
  summary_50_words:
    "A new risk factor was added covering supply chain diversification efforts and the potential costs and delays associated with moving production away from single-source suppliers.",
  verbatim_new_text: "We are diversifying our supply chain...",
  verbatim_old_text: "",
}

const MOCK_DATA: RiskFactorAnalysis = {
  ticker: "AAPL",
  current_period: "2025-Q4",
  prior_period: "2025-Q3",
  overall_risk_delta_score: 3.5,
  model_confidence: 0.87,
  material_changes: [MOCK_CHANGE_HIGH, MOCK_CHANGE_LOW],
  prompt_version: "v1.2",
  analyzed_at: "2026-01-15T10:00:00Z",
}

describe("RiskDeltaCard", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("shows loading state when promise has not resolved", () => {
    mockGetRiskFactorAnalysis.mockReturnValue(new Promise(() => {}))

    render(<RiskDeltaCard ticker="AAPL" />)

    expect(screen.getByTestId("filing_delta_loading")).toBeInTheDocument()
  })

  it("shows empty state when API returns null", async () => {
    mockGetRiskFactorAnalysis.mockResolvedValue(null)

    render(<RiskDeltaCard ticker="AAPL" />)

    await waitFor(() => {
      expect(screen.getByTestId("filing_delta_empty")).toBeInTheDocument()
    })

    expect(screen.getByText("Insufficient data")).toBeInTheDocument()
  })

  it("renders delta score and changes when data is available", async () => {
    mockGetRiskFactorAnalysis.mockResolvedValue(MOCK_DATA)

    render(<RiskDeltaCard ticker="AAPL" />)

    await waitFor(() => {
      expect(screen.getByTestId("filing_delta_card")).toBeInTheDocument()
    })

    expect(screen.getByTestId("delta_score")).toBeInTheDocument()
    expect(screen.getByTestId("delta_score")).toHaveTextContent("+3.5")

    expect(screen.getByText("Cybersecurity risk")).toBeInTheDocument()
    expect(screen.getByText("Supply chain diversification")).toBeInTheDocument()
  })

  it("sorts material changes by severity descending", async () => {
    mockGetRiskFactorAnalysis.mockResolvedValue(MOCK_DATA)

    render(<RiskDeltaCard ticker="AAPL" />)

    await waitFor(() => {
      expect(screen.getByTestId("filing_delta_card")).toBeInTheDocument()
    })

    const pills = screen.getAllByTestId("severity_pill")
    expect(pills).toHaveLength(2)
    // First pill should be severity 8 (higher), second should be severity 3
    expect(pills[0]).toHaveTextContent("8")
    expect(pills[1]).toHaveTextContent("3")
  })

  it("expands row on click to reveal summary text", async () => {
    mockGetRiskFactorAnalysis.mockResolvedValue(MOCK_DATA)

    const user = userEvent.setup()
    render(<RiskDeltaCard ticker="AAPL" />)

    await waitFor(() => {
      expect(screen.getByTestId("filing_delta_card")).toBeInTheDocument()
    })

    // Summary should not be visible initially
    expect(
      screen.queryByText(MOCK_CHANGE_HIGH.summary_50_words),
    ).not.toBeInTheDocument()

    // Click the first row button (Cybersecurity risk — sorted first by severity 8)
    const rowButtons = screen.getAllByRole("button")
    await user.click(rowButtons[0])

    // Summary text should now be visible
    await waitFor(() => {
      expect(screen.getByText(MOCK_CHANGE_HIGH.summary_50_words)).toBeInTheDocument()
    })
  })

  it("renders 'No material changes' when material_changes is empty", async () => {
    const emptyData: RiskFactorAnalysis = {
      ...MOCK_DATA,
      material_changes: [],
    }
    mockGetRiskFactorAnalysis.mockResolvedValue(emptyData)

    render(<RiskDeltaCard ticker="AAPL" />)

    await waitFor(() => {
      expect(screen.getByTestId("filing_delta_card")).toBeInTheDocument()
    })

    expect(screen.getByText("No material changes")).toBeInTheDocument()
  })
})
