import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import PrivacyPage from "../page"

vi.mock("next/navigation", () => ({
  usePathname: () => "/privacy",
  useRouter: () => ({ push: vi.fn() }),
}))

vi.mock("next-auth/react", () => ({
  useSession: () => ({
    data: null,
    status: "unauthenticated",
  }),
  signOut: vi.fn(),
}))

describe("Privacy Policy Page", () => {
  it("renders the page heading", () => {
    render(<PrivacyPage />)
    expect(screen.getByRole("heading", { level: 1, name: /privacy policy/i })).toBeInTheDocument()
  })

  it("renders Information We Collect section", () => {
    render(<PrivacyPage />)
    expect(screen.getByText("2. Information We Collect")).toBeInTheDocument()
    expect(screen.getByText(/account information/i)).toBeInTheDocument()
  })

  it("renders How We Use Your Information section", () => {
    render(<PrivacyPage />)
    expect(screen.getByText("3. How We Use Your Information")).toBeInTheDocument()
    expect(screen.getByText(/provide, operate, and maintain/i)).toBeInTheDocument()
  })

  it("renders How We Share Your Information section", () => {
    render(<PrivacyPage />)
    expect(screen.getByText("4. How We Share Your Information")).toBeInTheDocument()
    expect(screen.getByText(/do not sell your personal information/i)).toBeInTheDocument()
  })

  it("renders Your Rights section with CCPA mention", () => {
    render(<PrivacyPage />)
    expect(screen.getByText("5. Your Rights")).toBeInTheDocument()
    expect(screen.getByText(/CCPA\/CPRA/)).toBeInTheDocument()
  })

  it("renders Data Security section", () => {
    render(<PrivacyPage />)
    expect(screen.getByText("7. Data Security")).toBeInTheDocument()
    expect(screen.getByText(/industry-standard security measures/i)).toBeInTheDocument()
  })

  it("renders contact email link", () => {
    render(<PrivacyPage />)
    const emailLinks = screen.getAllByRole("link", { name: /legal@margin-invest\.com/ })
    expect(emailLinks.length).toBeGreaterThanOrEqual(1)
    expect(emailLinks[0]).toHaveAttribute("href", "mailto:legal@margin-invest.com")
  })

  it("renders the back to home link", () => {
    render(<PrivacyPage />)
    const backLink = screen.getByRole("link", { name: /back to home/i })
    expect(backLink).toHaveAttribute("href", "/")
  })

  it("renders last updated date", () => {
    render(<PrivacyPage />)
    expect(screen.getByText(/last updated.*february 27, 2026/i)).toBeInTheDocument()
  })

  it("renders Children's Privacy section", () => {
    render(<PrivacyPage />)
    expect(screen.getByText(/Children/)).toBeInTheDocument()
    expect(screen.getByText(/not directed to individuals under 18/i)).toBeInTheDocument()
  })
})
