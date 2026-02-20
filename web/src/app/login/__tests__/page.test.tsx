import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import LoginPage from "../page"

// Mock the client components
vi.mock("@/components/login/login-scene", () => ({
  LoginScene: () => <div data-testid="login-scene">Mocked LoginScene</div>,
}))

vi.mock("@/components/login/login-card", () => ({
  LoginCard: ({ initialMode }: { initialMode?: string }) => (
    <div data-testid="login-card" data-initial-mode={initialMode}>Mocked LoginCard</div>
  ),
}))

describe("Login Page", () => {
  it("renders the LoginCard component", async () => {
    const page = await LoginPage({ searchParams: Promise.resolve({}) })
    render(page)
    expect(screen.getByTestId("login-card")).toBeInTheDocument()
  })

  it("renders the LoginScene component", async () => {
    const page = await LoginPage({ searchParams: Promise.resolve({}) })
    render(page)
    expect(screen.getByTestId("login-scene")).toBeInTheDocument()
  })

  it("passes initialMode=signup when mode=signup search param is present", async () => {
    const page = await LoginPage({ searchParams: Promise.resolve({ mode: "signup" }) })
    render(page)
    expect(screen.getByTestId("login-card")).toHaveAttribute("data-initial-mode", "signup")
  })

  it("passes initialMode=signin by default", async () => {
    const page = await LoginPage({ searchParams: Promise.resolve({}) })
    render(page)
    expect(screen.getByTestId("login-card")).toHaveAttribute("data-initial-mode", "signin")
  })
})
