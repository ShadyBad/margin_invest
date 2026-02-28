import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import ApiDocsPage from "../page"

vi.mock("next-auth/react", () => ({
  useSession: () => ({
    data: {
      user: {
        name: "Test User",
        email: "test@example.com",
        image: "https://example.com/avatar.jpg",
      },
    },
    status: "authenticated",
  }),
  signOut: vi.fn(),
}))

vi.mock("next/navigation", () => ({
  usePathname: () => "/api-docs",
  useRouter: () => ({ push: vi.fn() }),
}))

describe("API Docs Page", () => {
  it("renders the page heading", () => {
    render(<ApiDocsPage />)
    expect(screen.getByRole("heading", { level: 1, name: /api reference/i })).toBeInTheDocument()
  })

  it("renders all section headings", () => {
    render(<ApiDocsPage />)
    expect(
      screen.getByRole("heading", { level: 2, name: /authentication/i })
    ).toBeInTheDocument()
    expect(screen.getByRole("heading", { level: 2, name: /rate limits/i })).toBeInTheDocument()
    expect(screen.getByRole("heading", { level: 2, name: /endpoints/i })).toBeInTheDocument()
    expect(
      screen.getByRole("heading", { level: 2, name: /response format/i })
    ).toBeInTheDocument()
    expect(
      screen.getByRole("heading", { level: 2, name: /sdks & support/i })
    ).toBeInTheDocument()
  })

  it("renders endpoint paths", () => {
    render(<ApiDocsPage />)
    expect(screen.getByText("/api/v1/scores/{ticker}")).toBeInTheDocument()
    expect(screen.getByText("/api/v1/backtest/default")).toBeInTheDocument()
    expect(screen.getByText("/api/v1/13f/holdings/{ticker}")).toBeInTheDocument()
  })

  it("renders the authentication example", () => {
    render(<ApiDocsPage />)
    const codeElements = screen.getAllByText(/X-API-Key/)
    expect(codeElements.length).toBeGreaterThanOrEqual(1)
  })

  it("renders HTTP status codes", () => {
    render(<ApiDocsPage />)
    // Status codes appear in the error codes table
    const code401 = screen.getAllByText("401")
    expect(code401.length).toBeGreaterThanOrEqual(1)
    const code403 = screen.getAllByText("403")
    expect(code403.length).toBeGreaterThanOrEqual(1)
    const code429 = screen.getAllByText("429")
    expect(code429.length).toBeGreaterThanOrEqual(1)
  })

  it("renders the request API key link", () => {
    render(<ApiDocsPage />)
    const link = screen.getByRole("link", { name: /request.*api key/i })
    expect(link).toHaveAttribute("href", "/account")
  })

  it("renders the back to home link", () => {
    render(<ApiDocsPage />)
    const backLink = screen.getByRole("link", { name: /back to home/i })
    expect(backLink).toHaveAttribute("href", "/")
  })
})
