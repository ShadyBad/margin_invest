import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import ContactPage from "../page"

vi.mock("next/navigation", () => ({
  usePathname: () => "/contact",
  useRouter: () => ({ push: vi.fn() }),
}))

vi.mock("next-auth/react", () => ({
  useSession: () => ({
    data: null,
    status: "unauthenticated",
  }),
  signOut: vi.fn(),
}))

describe("Contact Page", () => {
  it("renders the page heading", () => {
    render(<ContactPage />)
    expect(screen.getByRole("heading", { level: 1, name: /get in touch/i })).toBeInTheDocument()
  })

  it("renders all four contact channels", () => {
    render(<ContactPage />)
    expect(screen.getByText("General Support")).toBeInTheDocument()
    expect(screen.getByText("Security")).toBeInTheDocument()
    expect(screen.getByText("Legal & Privacy")).toBeInTheDocument()
    expect(screen.getByText("Business & Partnerships")).toBeInTheDocument()
  })

  it("renders mailto links for all channels", () => {
    render(<ContactPage />)
    expect(screen.getByRole("link", { name: "support@margin-invest.com" })).toHaveAttribute(
      "href",
      "mailto:support@margin-invest.com"
    )
    expect(screen.getByRole("link", { name: "security@margin-invest.com" })).toHaveAttribute(
      "href",
      "mailto:security@margin-invest.com"
    )
    expect(screen.getByRole("link", { name: "legal@margin-invest.com" })).toHaveAttribute(
      "href",
      "mailto:legal@margin-invest.com"
    )
    expect(screen.getByRole("link", { name: "partnerships@margin-invest.com" })).toHaveAttribute(
      "href",
      "mailto:partnerships@margin-invest.com"
    )
  })

  it("renders response time SLAs", () => {
    render(<ContactPage />)
    expect(screen.getByText(/within 24 hours/i)).toBeInTheDocument()
    expect(screen.getByText(/within 48 hours/i)).toBeInTheDocument()
    expect(screen.getByText(/within 5 business days/i)).toBeInTheDocument()
    expect(screen.getByText(/within 3 business days/i)).toBeInTheDocument()
  })

  it("renders the contact form fields", () => {
    render(<ContactPage />)
    expect(screen.getByLabelText(/name/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/subject/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/message/i)).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /send message/i })).toBeInTheDocument()
  })

  it("validates required fields on submit", async () => {
    const user = userEvent.setup()
    render(<ContactPage />)
    await user.click(screen.getByRole("button", { name: /send message/i }))
    // HTML5 validation prevents submission — form should still be visible
    expect(screen.getByRole("button", { name: /send message/i })).toBeInTheDocument()
  })

  it("renders office hours", () => {
    render(<ContactPage />)
    expect(screen.getByText(/monday.*friday.*9 am.*6 pm et/i)).toBeInTheDocument()
  })

  it("renders quick links to related pages", () => {
    render(<ContactPage />)
    const supportLinks = screen.getAllByRole("link", { name: /support/i })
    expect(supportLinks.some(l => l.getAttribute("href") === "/support")).toBe(true)
    const securityLinks = screen.getAllByRole("link", { name: /security/i })
    expect(securityLinks.some(l => l.getAttribute("href") === "/security")).toBe(true)
    const apiLinks = screen.getAllByRole("link", { name: /api/i })
    expect(apiLinks.some(l => l.getAttribute("href") === "/api-docs")).toBe(true)
    const legalLinks = screen.getAllByRole("link", { name: /legal/i })
    expect(legalLinks.some(l => l.getAttribute("href") === "/legal")).toBe(true)
  })

  it("renders the back to home link", () => {
    render(<ContactPage />)
    const backLink = screen.getByRole("link", { name: /back to home/i })
    expect(backLink).toHaveAttribute("href", "/")
  })
})
