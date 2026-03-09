import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, fireEvent, waitFor } from "@testing-library/react"
import { HeroSearch } from "../hero-search"

// Mock apiFetch
const mockApiFetch = vi.fn()
vi.mock("@/lib/api/client", () => ({
  apiFetch: (...args: unknown[]) => mockApiFetch(...args),
  ApiError: class extends Error {
    status: number
    errorCode: string
    constructor(status: number, errorCode: string, message?: string) {
      super(message)
      this.status = status
      this.errorCode = errorCode
    }
  },
}))

const MOCK_RESULT = {
  ticker: "AAPL",
  company_name: "Apple Inc",
  composite_score: 78.5,
  composite_tier: "high",
  signal: "strong",
  factor_summary: {
    quality_percentile: 72.0,
    value_percentile: 81.0,
    momentum_percentile: 65.0,
  },
  eliminated: false,
  elimination_reason: null,
  scored_at: "2026-02-27T12:00:00+00:00",
}

const MOCK_ELIMINATED = {
  ...MOCK_RESULT,
  ticker: "XYZ",
  company_name: "XYZ Corp",
  composite_score: 22.0,
  composite_tier: "none",
  signal: "failed",
  eliminated: true,
  elimination_reason: "negative_earnings",
}

describe("HeroSearch", () => {
  beforeEach(() => {
    mockApiFetch.mockReset()
  })

  it("renders search input and button", () => {
    render(<HeroSearch />)
    expect(screen.getByPlaceholderText(/search any ticker/i)).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /search/i })).toBeInTheDocument()
  })

  it("shows loading state on submit", async () => {
    mockApiFetch.mockImplementation(() => new Promise(() => {})) // never resolves
    render(<HeroSearch />)
    const input = screen.getByPlaceholderText(/search any ticker/i)
    fireEvent.change(input, { target: { value: "AAPL" } })
    fireEvent.submit(input.closest("form")!)
    await waitFor(() => {
      expect(screen.getByTestId("hero-search-loading")).toBeInTheDocument()
    })
  })

  it("shows result card with score data on success", async () => {
    mockApiFetch.mockResolvedValueOnce(MOCK_RESULT)
    render(<HeroSearch />)
    const input = screen.getByPlaceholderText(/search any ticker/i)
    fireEvent.change(input, { target: { value: "AAPL" } })
    fireEvent.submit(input.closest("form")!)
    await waitFor(() => {
      expect(screen.getByText("AAPL")).toBeInTheDocument()
      expect(screen.getByText("Apple Inc")).toBeInTheDocument()
      expect(screen.getByText("79")).toBeInTheDocument() // Math.round(78.5)
    })
  })

  it("shows factor percentile bars", async () => {
    mockApiFetch.mockResolvedValueOnce(MOCK_RESULT)
    render(<HeroSearch />)
    const input = screen.getByPlaceholderText(/search any ticker/i)
    fireEvent.change(input, { target: { value: "AAPL" } })
    fireEvent.submit(input.closest("form")!)
    await waitFor(() => {
      expect(screen.getByText("Quality")).toBeInTheDocument()
      expect(screen.getByText("Value")).toBeInTheDocument()
      expect(screen.getByText("Momentum")).toBeInTheDocument()
    })
  })

  it("shows eliminated badge for eliminated tickers", async () => {
    mockApiFetch.mockResolvedValueOnce(MOCK_ELIMINATED)
    render(<HeroSearch />)
    const input = screen.getByPlaceholderText(/search any ticker/i)
    fireEvent.change(input, { target: { value: "XYZ" } })
    fireEvent.submit(input.closest("form")!)
    await waitFor(() => {
      expect(screen.getByText(/eliminated/i)).toBeInTheDocument()
      expect(screen.getByText(/negative_earnings/i)).toBeInTheDocument()
    })
  })

  it("shows error for 404 response", async () => {
    const { ApiError } = await import("@/lib/api/client")
    mockApiFetch.mockRejectedValueOnce(new ApiError(404, "NOT_FOUND", "No score found for ZZZZ"))
    render(<HeroSearch />)
    const input = screen.getByPlaceholderText(/search any ticker/i)
    fireEvent.change(input, { target: { value: "ZZZZ" } })
    fireEvent.submit(input.closest("form")!)
    await waitFor(() => {
      expect(screen.getByText(/not found/i)).toBeInTheDocument()
    })
  })

  it("shows generic error for network failure", async () => {
    mockApiFetch.mockRejectedValueOnce(new Error("Network error"))
    render(<HeroSearch />)
    const input = screen.getByPlaceholderText(/search any ticker/i)
    fireEvent.change(input, { target: { value: "AAPL" } })
    fireEvent.submit(input.closest("form")!)
    await waitFor(() => {
      expect(screen.getByText(/something went wrong/i)).toBeInTheDocument()
    })
  })

  it("CTA links to asset detail page", async () => {
    mockApiFetch.mockResolvedValueOnce(MOCK_RESULT)
    render(<HeroSearch />)
    const input = screen.getByPlaceholderText(/search any ticker/i)
    fireEvent.change(input, { target: { value: "AAPL" } })
    fireEvent.submit(input.closest("form")!)
    await waitFor(() => {
      const link = screen.getByRole("link", { name: /full forensic report/i })
      expect(link).toHaveAttribute("href", "/asset/AAPL")
    })
  })

  it("shows suggestion chips in idle state", () => {
    render(<HeroSearch />)
    expect(screen.getByText("Try:")).toBeInTheDocument()
    expect(screen.getByText("AAPL")).toBeInTheDocument()
    expect(screen.getByText("TSLA")).toBeInTheDocument()
    expect(screen.getByText("JNJ")).toBeInTheDocument()
    expect(screen.getByText("COST")).toBeInTheDocument()
    expect(screen.getByText("ETSY")).toBeInTheDocument()
  })

  it("hides suggestion chips when not idle", async () => {
    mockApiFetch.mockResolvedValueOnce(MOCK_RESULT)
    render(<HeroSearch />)
    const input = screen.getByPlaceholderText(/search any ticker/i)
    fireEvent.change(input, { target: { value: "AAPL" } })
    fireEvent.submit(input.closest("form")!)
    await waitFor(() => {
      expect(screen.getByText("Apple Inc")).toBeInTheDocument()
    })
    expect(screen.queryByText("Try:")).not.toBeInTheDocument()
  })
})
