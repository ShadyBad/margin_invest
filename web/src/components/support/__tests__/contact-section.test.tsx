import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { ContactSection } from "../contact-section"
import type { ContactCard } from "../support-data"

const mockCards: ContactCard[] = [
  {
    title: "General Support",
    email: "support@margin-invest.com",
    description: "Platform questions",
  },
  {
    title: "Security",
    email: "security@margin-invest.com",
    description: "Vulnerability reports",
  },
]

describe("ContactSection", () => {
  it("renders the heading", () => {
    render(<ContactSection cards={mockCards} />)
    expect(screen.getByText("Still need help?")).toBeInTheDocument()
  })

  it("renders all contact card titles", () => {
    render(<ContactSection cards={mockCards} />)
    expect(screen.getByText("General Support")).toBeInTheDocument()
    expect(screen.getByText("Security")).toBeInTheDocument()
  })

  it("renders mailto links for each email", () => {
    render(<ContactSection cards={mockCards} />)
    const links = screen.getAllByRole("link")
    const mailtoLinks = links.filter((l) => l.getAttribute("href")?.startsWith("mailto:"))
    expect(mailtoLinks).toHaveLength(2)
    expect(mailtoLinks[0]).toHaveAttribute("href", "mailto:support@margin-invest.com")
    expect(mailtoLinks[1]).toHaveAttribute("href", "mailto:security@margin-invest.com")
  })

  it("renders descriptions", () => {
    render(<ContactSection cards={mockCards} />)
    expect(screen.getByText("Platform questions")).toBeInTheDocument()
    expect(screen.getByText("Vulnerability reports")).toBeInTheDocument()
  })

  it("renders the status page link", () => {
    render(<ContactSection cards={mockCards} />)
    const statusLink = screen.getByRole("link", { name: /system status/i })
    expect(statusLink).toHaveAttribute("href", "/status")
  })
})
