import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { AuthorityStrip } from "../sections/authority-strip"
import type { HomepageData } from "../shared/types"

const mockData: HomepageData = {
  candidates: [],
  allPicks: [],
  last_updated: new Date().toISOString(),
  universe_size: 1842,
  eligible_count: 143,
  total_scored: 1842,
  total_universe: 3056,
  surviving_count: 143,
}

describe("AuthorityStrip", () => {
  it("renders the section", () => {
    const { container } = render(<AuthorityStrip data={mockData} />)
    const section = container.querySelector("section")
    expect(section).toBeInTheDocument()
  })

  it("renders four column labels", () => {
    render(<AuthorityStrip data={mockData} />)
    expect(screen.getByText("UNIVERSE")).toBeInTheDocument()
    expect(screen.getByText("SCORED")).toBeInTheDocument()
    expect(screen.getByText("SURVIVING")).toBeInTheDocument()
    expect(screen.getByText("LAST CYCLE")).toBeInTheDocument()
  })

  it("renders live data values", () => {
    render(<AuthorityStrip data={mockData} />)
    expect(screen.getByTestId("universe-value")).toHaveTextContent("3,056")
    expect(screen.getByTestId("scored-value")).toHaveTextContent("1,842")
    expect(screen.getByTestId("surviving-value")).toHaveTextContent("143")
  })

  it("renders dashes when data is null", () => {
    render(<AuthorityStrip data={null} />)
    expect(screen.getByTestId("universe-value")).toHaveTextContent("\u2014")
    expect(screen.getByTestId("scored-value")).toHaveTextContent("\u2014")
    expect(screen.getByTestId("surviving-value")).toHaveTextContent("\u2014")
    expect(screen.getByTestId("last-cycle-value")).toHaveTextContent("\u2014")
  })
})
