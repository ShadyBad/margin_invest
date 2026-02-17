import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import LoginPage from "../page"

// Mock the client components
vi.mock("@/components/login/login-scene", () => ({
  LoginScene: () => <div data-testid="login-scene">Mocked LoginScene</div>,
}))

vi.mock("@/components/login/login-card", () => ({
  LoginCard: () => <div data-testid="login-card">Mocked LoginCard</div>,
}))

describe("Login Page", () => {
  it("renders the LoginCard component", () => {
    render(<LoginPage />)
    expect(screen.getByTestId("login-card")).toBeInTheDocument()
  })

  it("renders the LoginScene component", () => {
    render(<LoginPage />)
    expect(screen.getByTestId("login-scene")).toBeInTheDocument()
  })
})
