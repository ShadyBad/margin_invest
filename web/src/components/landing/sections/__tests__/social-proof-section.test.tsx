import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import { SocialProofSection } from "../social-proof-section"

vi.mock("next/link", () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}))

const mockData = {
  candidates: [],
  allPicks: [],
  last_updated: "2026-03-17T12:00:00Z",
  universe_size: 3200,
  eligible_count: 200,
  total_scored: 3100,
  total_universe: 3200,
  surviving_count: 180,
}

describe("SocialProofSection", () => {
  it("renders scored positions stat", () => {
    render(<SocialProofSection data={mockData} />)
    expect(screen.getByText(/3,100/)).toBeInTheDocument()
    expect(screen.getByText(/positions scored/i)).toBeInTheDocument()
  })

  it("renders forensic filter stat", () => {
    render(<SocialProofSection data={mockData} />)
    expect(screen.getByText(/94%/)).toBeInTheDocument()
  })

  it("renders auditability stat", () => {
    render(<SocialProofSection data={mockData} />)
    expect(screen.getByText(/every score links to its formula/i)).toBeInTheDocument()
  })

  it("renders null when data is null", () => {
    const { container } = render(<SocialProofSection data={null} />)
    expect(container.firstChild).toBeNull()
  })
})
