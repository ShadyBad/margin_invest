import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { FooterInstitutional } from "../footer-institutional"

describe("FooterInstitutional", () => {
  it("renders all navigation links", () => {
    render(<FooterInstitutional />)
    expect(screen.getByText("Support")).toBeInTheDocument()
    expect(screen.getByText("Methodology")).toBeInTheDocument()
    expect(screen.getByText("Legal")).toBeInTheDocument()
    expect(screen.getByText("API")).toBeInTheDocument()
  })

  it("renders copyright and version", () => {
    render(<FooterInstitutional />)
    expect(screen.getByText(/margin invest/i)).toBeInTheDocument()
    expect(screen.getByText(/engine v/i)).toBeInTheDocument()
  })
})
