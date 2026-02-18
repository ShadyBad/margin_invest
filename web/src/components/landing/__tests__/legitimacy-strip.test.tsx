import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { LegitimacyStrip } from "../legitimacy-strip"

describe("LegitimacyStrip", () => {
  it("renders trust markers", () => {
    render(<LegitimacyStrip />)
    expect(screen.getByText(/sec filings/i)).toBeInTheDocument()
    expect(screen.getByText(/updated daily/i)).toBeInTheDocument()
    expect(screen.getByText(/no hidden heuristics/i)).toBeInTheDocument()
  })
})
