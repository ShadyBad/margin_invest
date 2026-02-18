import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"

import { FooterSection } from "../footer-section"

describe("FooterSection", () => {
  it("renders all 7 navigation links", () => {
    render(<FooterSection />)
    expect(screen.getByText("Support")).toBeInTheDocument()
    expect(screen.getByText("Methodology")).toBeInTheDocument()
    expect(screen.getByText("Security")).toBeInTheDocument()
    expect(screen.getByText("Legal")).toBeInTheDocument()
    expect(screen.getByText("Status")).toBeInTheDocument()
    expect(screen.getByText("API")).toBeInTheDocument()
    expect(screen.getByText("Contact")).toBeInTheDocument()
  })

  it("renders engine version", () => {
    render(<FooterSection />)
    expect(screen.getByText(/engine v1.3.2/i)).toBeInTheDocument()
  })

  it("renders copyright", () => {
    render(<FooterSection />)
    expect(screen.getByText(/2026 margin invest/i)).toBeInTheDocument()
  })
})
