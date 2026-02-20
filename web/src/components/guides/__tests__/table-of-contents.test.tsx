import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { TableOfContents } from "../table-of-contents"

const headings = [
  { level: 2, text: "Getting Started", id: "getting-started" },
  { level: 3, text: "Prerequisites", id: "prerequisites" },
  { level: 3, text: "Installation", id: "installation" },
  { level: 2, text: "Advanced Usage", id: "advanced-usage" },
]

describe("TableOfContents", () => {
  it("renders all heading links", () => {
    render(<TableOfContents headings={headings} />)
    expect(screen.getByText("Getting Started")).toBeInTheDocument()
    expect(screen.getByText("Prerequisites")).toBeInTheDocument()
    expect(screen.getByText("Installation")).toBeInTheDocument()
    expect(screen.getByText("Advanced Usage")).toBeInTheDocument()
  })

  it("renders H3 items with indentation", () => {
    render(<TableOfContents headings={headings} />)
    const prerequisites = screen.getByText("Prerequisites").closest("li")
    const installation = screen.getByText("Installation").closest("li")
    expect(prerequisites).toHaveClass("pl-4")
    expect(installation).toHaveClass("pl-4")

    // H2 items should NOT have pl-4
    const gettingStarted = screen.getByText("Getting Started").closest("li")
    expect(gettingStarted).not.toHaveClass("pl-4")
  })

  it("links to correct heading IDs", () => {
    render(<TableOfContents headings={headings} />)
    const gettingStartedLink = screen.getByText("Getting Started").closest("a")
    const prerequisitesLink = screen.getByText("Prerequisites").closest("a")
    const installationLink = screen.getByText("Installation").closest("a")
    const advancedUsageLink = screen.getByText("Advanced Usage").closest("a")

    expect(gettingStartedLink).toHaveAttribute("href", "#getting-started")
    expect(prerequisitesLink).toHaveAttribute("href", "#prerequisites")
    expect(installationLink).toHaveAttribute("href", "#installation")
    expect(advancedUsageLink).toHaveAttribute("href", "#advanced-usage")
  })

  it("renders nothing when headings is empty", () => {
    const { container } = render(<TableOfContents headings={[]} />)
    expect(container.innerHTML).toBe("")
  })
})
