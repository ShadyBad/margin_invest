import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

vi.mock("next-auth/react", () => ({
  useSession: () => ({ data: null, status: "unauthenticated" }),
  signOut: vi.fn(),
}))
vi.mock("next/navigation", () => ({
  usePathname: () => "/security",
  useRouter: () => ({ push: vi.fn() }),
}))

import SecurityPage from "../page"

describe("Security Page", () => {
  it("renders the page heading", () => {
    render(<SecurityPage />)
    expect(screen.getByRole("heading", { level: 1, name: /how we protect your data/i })).toBeInTheDocument()
  })

  it("renders all seven sections", () => {
    render(<SecurityPage />)
    expect(screen.getByText(/infrastructure & encryption/i)).toBeInTheDocument()
    expect(screen.getByText(/authentication & access control/i)).toBeInTheDocument()
    expect(screen.getByText(/data protection/i)).toBeInTheDocument()
    expect(screen.getByText(/pipeline integrity/i)).toBeInTheDocument()
    expect(screen.getByText(/compliance posture/i)).toBeInTheDocument()
    expect(screen.getByText(/vulnerability disclosure/i)).toBeInTheDocument()
  })

  it("renders the security contact email", () => {
    render(<SecurityPage />)
    const mailtoLink = screen.getByRole("link", { name: "security@margin-invest.com" })
    expect(mailtoLink).toHaveAttribute("href", "mailto:security@margin-invest.com")
  })

  it("renders the back to home link", () => {
    render(<SecurityPage />)
    const backLink = screen.getByRole("link", { name: /back to home/i })
    expect(backLink).toHaveAttribute("href", "/")
  })

  it("renders key security details", () => {
    render(<SecurityPage />)
    expect(screen.getByText(/tls everywhere/i)).toBeInTheDocument()
    expect(screen.getByText(/jwt-based session authentication/i)).toBeInTheDocument()
    expect(screen.getByText(/totp multi-factor authentication/i)).toBeInTheDocument()
    expect(screen.getByText(/48-hour acknowledgment/i)).toBeInTheDocument()
  })
})
