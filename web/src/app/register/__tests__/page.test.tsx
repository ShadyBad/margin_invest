import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import RegisterPage from "../page"

const mockPush = vi.fn()

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: mockPush,
  }),
}))

describe("Register Page", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("renders 'Create an Account' heading", () => {
    render(<RegisterPage />)
    expect(
      screen.getByRole("heading", { name: /create an account/i })
    ).toBeInTheDocument()
  })

  it("renders username, email, and password fields", () => {
    render(<RegisterPage />)
    expect(screen.getByLabelText(/username/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument()
  })

  it("renders 'Create Account' submit button", () => {
    render(<RegisterPage />)
    expect(
      screen.getByRole("button", { name: /create account/i })
    ).toBeInTheDocument()
  })

  it("renders 'Sign in' link to /login", () => {
    render(<RegisterPage />)
    const link = screen.getByRole("link", { name: /sign in/i })
    expect(link).toBeInTheDocument()
    expect(link).toHaveAttribute("href", "/login")
  })

  it("shows error on failed registration", async () => {
    const user = userEvent.setup()
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      json: () => Promise.resolve({ detail: "Username already taken" }),
    })

    render(<RegisterPage />)

    await user.type(screen.getByLabelText(/username/i), "testuser")
    await user.type(screen.getByLabelText(/email/i), "test@example.com")
    await user.type(screen.getByLabelText(/password/i), "securepassword123")
    await user.click(screen.getByRole("button", { name: /create account/i }))

    await waitFor(() => {
      expect(screen.getByText("Username already taken")).toBeInTheDocument()
    })
  })
})
