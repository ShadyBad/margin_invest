import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import TermsPage from "../page"

vi.mock("next/navigation", () => ({
  usePathname: () => "/terms",
  useRouter: () => ({ push: vi.fn() }),
}))

vi.mock("next-auth/react", () => ({
  useSession: () => ({
    data: null,
    status: "unauthenticated",
  }),
  signOut: vi.fn(),
}))

describe("Terms of Service Page", () => {
  it("renders the page heading", () => {
    render(<TermsPage />)
    expect(screen.getByRole("heading", { level: 1, name: /terms of service/i })).toBeInTheDocument()
  })

  it("renders Eligibility section", () => {
    render(<TermsPage />)
    expect(screen.getByText("2. Eligibility")).toBeInTheDocument()
    expect(screen.getByText(/at least 18 years of age/)).toBeInTheDocument()
  })

  it("renders Service Description section", () => {
    render(<TermsPage />)
    expect(screen.getByText("3. Service Description")).toBeInTheDocument()
    expect(screen.getByText(/informational and educational purposes only/)).toBeInTheDocument()
  })

  it("renders Subscriptions section", () => {
    render(<TermsPage />)
    expect(screen.getByText("5. Subscriptions and Payments")).toBeInTheDocument()
    expect(screen.getByText(/cancel your subscription at any time/)).toBeInTheDocument()
  })

  it("renders Limitation of Liability section", () => {
    render(<TermsPage />)
    expect(screen.getByText("9. Limitation of Liability")).toBeInTheDocument()
    expect(screen.getByText(/SHALL NOT BE LIABLE/)).toBeInTheDocument()
  })

  it("renders Disclaimers section with AS IS language", () => {
    render(<TermsPage />)
    expect(screen.getByText("8. Disclaimers")).toBeInTheDocument()
  })

  it("renders Governing Law section mentioning Delaware", () => {
    render(<TermsPage />)
    expect(screen.getByText("11. Governing Law and Disputes")).toBeInTheDocument()
    expect(screen.getByText(/State of Delaware/)).toBeInTheDocument()
  })

  it("renders contact email link", () => {
    render(<TermsPage />)
    const emailLinks = screen.getAllByRole("link", { name: /legal@margin-invest\.com/ })
    expect(emailLinks.length).toBeGreaterThanOrEqual(1)
    expect(emailLinks[0]).toHaveAttribute("href", "mailto:legal@margin-invest.com")
  })

  it("renders the back to home link", () => {
    render(<TermsPage />)
    const backLink = screen.getByRole("link", { name: /back to home/i })
    expect(backLink).toHaveAttribute("href", "/")
  })

  it("renders last updated date", () => {
    render(<TermsPage />)
    expect(screen.getByText(/last updated.*february 27, 2026/i)).toBeInTheDocument()
  })
})
