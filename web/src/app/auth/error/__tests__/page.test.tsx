import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import AuthErrorPage from "../page"

vi.mock("next/navigation", () => ({
  useSearchParams: () =>
    new URLSearchParams("error=CredentialsSignin&code=invalid_credentials"),
}))

describe("Auth Error Page", () => {
  it("renders 'Authentication Error' heading", () => {
    render(<AuthErrorPage />)
    expect(
      screen.getByRole("heading", { name: /authentication error/i })
    ).toBeInTheDocument()
  })

  it("renders 'Try again' link to /login", () => {
    render(<AuthErrorPage />)
    const link = screen.getByRole("link", { name: /try again/i })
    expect(link).toBeInTheDocument()
    expect(link).toHaveAttribute("href", "/login")
  })

  it("shows error message for invalid_credentials", () => {
    render(<AuthErrorPage />)
    expect(
      screen.getByText("Invalid username or password.")
    ).toBeInTheDocument()
  })
})
