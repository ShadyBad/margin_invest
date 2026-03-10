import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { AuthorityStrip } from "../sections/authority-strip"

describe("AuthorityStrip", () => {
  it("renders the section", () => {
    const { container } = render(<AuthorityStrip />)
    const section = container.querySelector("section")
    expect(section).toBeInTheDocument()
  })

  it("renders the three column labels", () => {
    render(<AuthorityStrip />)
    expect(screen.getByText("Data Sources")).toBeInTheDocument()
    expect(screen.getByText("Coverage")).toBeInTheDocument()
    expect(screen.getByText("Engine")).toBeInTheDocument()
  })

  it("renders data source items", () => {
    render(<AuthorityStrip />)
    expect(screen.getByText("SEC EDGAR Filings")).toBeInTheDocument()
    expect(screen.getByText("Daily Market Data")).toBeInTheDocument()
  })

  it("renders coverage items", () => {
    render(<AuthorityStrip />)
    expect(screen.getByText("3,056 equities")).toBeInTheDocument()
    expect(screen.getByText("11 GICS sectors")).toBeInTheDocument()
  })

  it("renders engine items", () => {
    render(<AuthorityStrip />)
    expect(screen.getByText("Scored daily")).toBeInTheDocument()
  })
})
