import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { OnboardingFlow } from "../onboarding-flow"

const mockPush = vi.fn()
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
}))

let mockApiFetchResponse: unknown = null
let mockApiFetchShouldFail = false
vi.mock("@/lib/api/client", () => ({
  apiFetch: vi.fn(async () => {
    if (mockApiFetchShouldFail) throw new Error("API error")
    return mockApiFetchResponse
  }),
}))

vi.mock("sonner", () => ({
  toast: { error: vi.fn() },
}))

describe("OnboardingFlow", () => {
  beforeEach(() => {
    mockPush.mockClear()
    mockApiFetchShouldFail = false
    mockApiFetchResponse = {
      ticker: "AAPL",
      company_name: "Apple Inc.",
      composite_score: 72,
      composite_tier: "high",
      signal: "strong",
      factor_summary: { quality_percentile: 80, value_percentile: 65, momentum_percentile: 70 },
      eliminated: false,
      elimination_reason: null,
      scored_at: "2026-03-17T00:00:00Z",
    }
  })

  it("renders input stage initially", () => {
    render(<OnboardingFlow />)
    expect(screen.getByText("Score your portfolio.")).toBeInTheDocument()
  })

  it("redirects to /asset/AAPL on successful scoring", async () => {
    render(<OnboardingFlow />)
    const input = screen.getByPlaceholderText(/AAPL/i)
    await userEvent.type(input, "AAPL{enter}")

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith("/asset/AAPL")
    }, { timeout: 5000 })
  })

  it("redirects to /dashboard on API failure", async () => {
    mockApiFetchShouldFail = true
    render(<OnboardingFlow />)
    const input = screen.getByPlaceholderText(/AAPL/i)
    await userEvent.type(input, "AAPL{enter}")

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith("/dashboard")
    }, { timeout: 12000 })
  }, 15000)
})
