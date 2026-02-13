import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { LoginButtons } from "../login-buttons"

// Use vi.hoisted so the mock function is available when vi.mock factory runs
const { mockSignIn } = vi.hoisted(() => ({
  mockSignIn: vi.fn(),
}))

vi.mock("next-auth/react", () => ({
  signIn: mockSignIn,
}))

describe("LoginButtons", () => {
  beforeEach(() => {
    mockSignIn.mockClear()
  })

  it("renders Google and GitHub OAuth buttons", () => {
    render(<LoginButtons />)

    expect(screen.getByText("Sign in with Google")).toBeInTheDocument()
    expect(screen.getByText("Sign in with GitHub")).toBeInTheDocument()
  })

  it("renders exactly 2 OAuth buttons", () => {
    render(<LoginButtons />)

    const oauthButtons = screen.getAllByText(/^Sign in with /)
    expect(oauthButtons).toHaveLength(2)
  })

  it("does not render Microsoft or Facebook buttons", () => {
    render(<LoginButtons />)

    expect(screen.queryByText("Sign in with Microsoft")).not.toBeInTheDocument()
    expect(screen.queryByText("Sign in with Facebook")).not.toBeInTheDocument()
  })

  it("renders username and password input fields with labels", () => {
    render(<LoginButtons />)

    expect(screen.getByLabelText(/username/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument()
  })

  it("renders a credentials Sign In button", () => {
    render(<LoginButtons />)

    // There should be a submit button for credentials separate from OAuth buttons
    const signInButton = screen.getByRole("button", { name: /^Sign In$/i })
    expect(signInButton).toBeInTheDocument()
  })

  it("calls signIn with 'google' on Google button click", async () => {
    const user = userEvent.setup()
    render(<LoginButtons />)

    await user.click(screen.getByText("Sign in with Google"))

    expect(mockSignIn).toHaveBeenCalledWith("google", {
      callbackUrl: "/dashboard",
    })
  })

  it("calls signIn with 'credentials' including username/password on form submit", async () => {
    const user = userEvent.setup()
    render(<LoginButtons />)

    await user.type(screen.getByLabelText(/username/i), "testuser")
    await user.type(screen.getByLabelText(/password/i), "testpass123")
    await user.click(screen.getByRole("button", { name: /^Sign In$/i }))

    expect(mockSignIn).toHaveBeenCalledWith("credentials", {
      username: "testuser",
      password: "testpass123",
      callbackUrl: "/dashboard",
    })
  })

  it("renders 'Create one' link to /register", () => {
    render(<LoginButtons />)

    const link = screen.getByRole("link", { name: /create one/i })
    expect(link).toBeInTheDocument()
    expect(link).toHaveAttribute("href", "/register")
  })
})
