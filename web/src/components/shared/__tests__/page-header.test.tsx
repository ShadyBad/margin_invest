import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { PageHeader } from "../page-header"

describe("PageHeader", () => {
  it("renders category, title, and description", () => {
    render(
      <PageHeader
        category="GUIDES"
        title="Investment Guides"
        description="Learn the system."
      />
    )
    expect(screen.getByText("GUIDES")).toBeInTheDocument()
    expect(screen.getByText("Investment Guides")).toBeInTheDocument()
    expect(screen.getByText("Learn the system.")).toBeInTheDocument()
  })

  it("renders the status dot", () => {
    const { container } = render(
      <PageHeader
        category="METHODOLOGY"
        title="How It Works"
        description="Our process."
      />
    )
    const dot = container.querySelector(".bg-accent.rounded-full")
    expect(dot).toBeInTheDocument()
  })

  it("uses correct typography classes", () => {
    render(
      <PageHeader
        category="REFERENCE"
        title="Factor Reference"
        description="All 17 factors explained."
      />
    )
    const title = screen.getByText("Factor Reference")
    expect(title.tagName).toBe("H1")
    expect(title.className).toContain("text-display-2")
  })

  it("renders the header element with bottom margin", () => {
    const { container } = render(
      <PageHeader
        category="TEST"
        title="Test Title"
        description="Test description."
      />
    )
    const header = container.querySelector("header")
    expect(header).toBeInTheDocument()
    expect(header?.className).toContain("mb-16")
  })
})
