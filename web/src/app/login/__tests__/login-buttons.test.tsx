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

  it("renders all 4 provider buttons", () => {
    render(<LoginButtons />)

    expect(screen.getByText("Sign in with Google")).toBeInTheDocument()
    expect(screen.getByText("Sign in with Microsoft")).toBeInTheDocument()
    expect(screen.getByText("Sign in with Facebook")).toBeInTheDocument()
    expect(screen.getByText("Sign in with GitHub")).toBeInTheDocument()
  })

  it("renders exactly 4 buttons", () => {
    render(<LoginButtons />)

    const buttons = screen.getAllByRole("button")
    expect(buttons).toHaveLength(4)
  })

  it("calls signIn with 'google' when Google button is clicked", async () => {
    const user = userEvent.setup()
    render(<LoginButtons />)

    await user.click(screen.getByText("Sign in with Google"))

    expect(mockSignIn).toHaveBeenCalledWith("google", {
      callbackUrl: "/dashboard",
    })
  })

  it("calls signIn with 'microsoft-entra-id' when Microsoft button is clicked", async () => {
    const user = userEvent.setup()
    render(<LoginButtons />)

    await user.click(screen.getByText("Sign in with Microsoft"))

    expect(mockSignIn).toHaveBeenCalledWith("microsoft-entra-id", {
      callbackUrl: "/dashboard",
    })
  })

  it("calls signIn with 'facebook' when Facebook button is clicked", async () => {
    const user = userEvent.setup()
    render(<LoginButtons />)

    await user.click(screen.getByText("Sign in with Facebook"))

    expect(mockSignIn).toHaveBeenCalledWith("facebook", {
      callbackUrl: "/dashboard",
    })
  })

  it("calls signIn with 'github' when GitHub button is clicked", async () => {
    const user = userEvent.setup()
    render(<LoginButtons />)

    await user.click(screen.getByText("Sign in with GitHub"))

    expect(mockSignIn).toHaveBeenCalledWith("github", {
      callbackUrl: "/dashboard",
    })
  })
})
