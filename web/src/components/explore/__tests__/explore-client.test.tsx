import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import { ExploreClient } from "../explore-client"

vi.mock("@/lib/api/client", () => ({
  apiFetch: vi.fn(),
}))

const mockScores = {
  scores: [
    {
      ticker: "AAPL",
      name: "Apple Inc.",
      sector: "Technology",
      composite_percentile: 85,
      composite_tier: "high",
      score: 72,
      signal: "strong",
    },
    {
      ticker: "MSFT",
      name: "Microsoft Corp.",
      sector: "Technology",
      composite_percentile: 78,
      composite_tier: "high",
      score: 68,
      signal: "strong",
    },
  ],
  total: 2,
  page: 1,
  page_size: 20,
}

describe("ExploreClient", () => {
  it("renders score cards for initial data", () => {
    render(<ExploreClient initialData={mockScores} />)
    expect(screen.getByText("AAPL")).toBeInTheDocument()
    expect(screen.getByText("MSFT")).toBeInTheDocument()
  })

  it("renders company names", () => {
    render(<ExploreClient initialData={mockScores} />)
    expect(screen.getByText("Apple Inc.")).toBeInTheDocument()
  })

  it("renders empty state when no data", () => {
    render(<ExploreClient initialData={{ scores: [], total: 0, page: 1, page_size: 20 }} />)
    expect(screen.getByText(/no scored assets/i)).toBeInTheDocument()
  })
})
