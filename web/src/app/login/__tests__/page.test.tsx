import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import LoginPage from "../page"

// Mock the LoginButtons client component
vi.mock("../login-buttons", () => ({
  LoginButtons: () => <div data-testid="login-buttons">Mocked LoginButtons</div>,
}))

describe("Login Page", () => {
  it("renders the sign-in heading", () => {
    render(<LoginPage />)

    expect(
      screen.getByRole("heading", { name: /sign in to margin invest/i })
    ).toBeInTheDocument()
  })

  it("renders the LoginButtons component", () => {
    render(<LoginPage />)

    expect(screen.getByTestId("login-buttons")).toBeInTheDocument()
  })
})
