import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { AuthorityStrip } from "../authority-strip"
import type { HomepageData } from "../../shared/types"

const mockData: HomepageData = {
  candidates: [],
  allPicks: [],
  last_updated: new Date(Date.now() - 2 * 60 * 60_000).toISOString(), // 2 hours ago
  universe_size: 1842,
  eligible_count: 143,
  total_scored: 1842,
  total_universe: 3056,
  surviving_count: 143,
}

describe("AuthorityStrip", () => {
  it("renders 4 columns", () => {
    render(<AuthorityStrip data={mockData} />)
    expect(screen.getByText("UNIVERSE")).toBeInTheDocument()
    expect(screen.getByText("SCORED")).toBeInTheDocument()
    expect(screen.getByText("SURVIVING")).toBeInTheDocument()
    expect(screen.getByText("LAST CYCLE")).toBeInTheDocument()
  })

  it("displays data values when data is provided", () => {
    render(<AuthorityStrip data={mockData} />)
    expect(screen.getByTestId("universe-value")).toHaveTextContent("3,056")
    expect(screen.getByTestId("scored-value")).toHaveTextContent("1,842")
    expect(screen.getByTestId("surviving-value")).toHaveTextContent("143")
    expect(screen.getByTestId("last-cycle-value")).toHaveTextContent("2h ago")
  })

  it("shows dashes when data is null", () => {
    render(<AuthorityStrip data={null} />)
    expect(screen.getByTestId("universe-value")).toHaveTextContent("\u2014")
    expect(screen.getByTestId("scored-value")).toHaveTextContent("\u2014")
    expect(screen.getByTestId("surviving-value")).toHaveTextContent("\u2014")
    expect(screen.getByTestId("last-cycle-value")).toHaveTextContent("\u2014")
  })

  it("shows StalenessIndicator when isFallback is true", () => {
    const fallbackData: HomepageData = { ...mockData, isFallback: true }
    render(<AuthorityStrip data={fallbackData} />)
    expect(screen.getByText(/sample data/i)).toBeInTheDocument()
  })

  it("does not show StalenessIndicator when isFallback is false", () => {
    render(<AuthorityStrip data={mockData} />)
    expect(screen.queryByText(/sample data/i)).not.toBeInTheDocument()
  })

  it("status dot has pulse animation class", () => {
    const { container } = render(<AuthorityStrip data={mockData} />)
    const dot = container.querySelector(".animate-pulse")
    expect(dot).toBeInTheDocument()
    expect(dot?.classList.contains("rounded-full")).toBe(true)
  })

  it("uses max-w-6xl container width", () => {
    const { container } = render(<AuthorityStrip data={mockData} />)
    const wrapper = container.querySelector(".max-w-6xl")
    expect(wrapper).toBeInTheDocument()
  })

  it("renders relative time for recent last_updated", () => {
    const recentData: HomepageData = {
      ...mockData,
      last_updated: new Date(Date.now() - 15 * 60_000).toISOString(), // 15 minutes ago
    }
    render(<AuthorityStrip data={recentData} />)
    expect(screen.getByTestId("last-cycle-value")).toHaveTextContent("15m ago")
  })
})
