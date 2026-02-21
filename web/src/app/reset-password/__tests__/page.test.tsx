import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import ResetPasswordPage from "../page"

// Mock useSearchParams
const mockSearchParams = new URLSearchParams()
vi.mock("next/navigation", () => ({
  useSearchParams: () => mockSearchParams,
  useRouter: () => ({ push: vi.fn() }),
}))

describe("ResetPasswordPage", () => {
  const originalFetch = global.fetch

  beforeEach(() => {
    mockSearchParams.delete("token")
    mockSearchParams.delete("userId")
    global.fetch = originalFetch
  })

  it("renders password and confirm password fields", () => {
    mockSearchParams.set("token", "abc123")
    mockSearchParams.set("userId", "1")
    render(<ResetPasswordPage />)
    expect(screen.getByLabelText("New Password")).toBeInTheDocument()
    expect(screen.getByLabelText("Confirm Password")).toBeInTheDocument()
  })

  it("shows password validation checklist", () => {
    mockSearchParams.set("token", "abc123")
    mockSearchParams.set("userId", "1")
    render(<ResetPasswordPage />)
    expect(screen.getByText("At least 12 characters")).toBeInTheDocument()
  })

  it("shows error when passwords do not match", async () => {
    mockSearchParams.set("token", "abc123")
    mockSearchParams.set("userId", "1")
    const user = userEvent.setup()
    render(<ResetPasswordPage />)

    await user.type(screen.getByLabelText("New Password"), "NewPassword2@")
    await user.type(screen.getByLabelText("Confirm Password"), "Different2@!")
    await user.click(screen.getByRole("button", { name: /reset password/i }))

    expect(screen.getByText("Passwords do not match")).toBeInTheDocument()
  })

  it("calls API and shows success on valid submission", async () => {
    mockSearchParams.set("token", "abc123")
    mockSearchParams.set("userId", "1")
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ message: "Password has been reset." }),
    })

    const user = userEvent.setup()
    render(<ResetPasswordPage />)

    await user.type(screen.getByLabelText("New Password"), "NewPassword2@")
    await user.type(screen.getByLabelText("Confirm Password"), "NewPassword2@")
    await user.click(screen.getByRole("button", { name: /reset password/i }))

    await waitFor(() => {
      expect(screen.getByText(/password reset successfully/i)).toBeInTheDocument()
    })
  })

  it("shows error on API failure", async () => {
    mockSearchParams.set("token", "abc123")
    mockSearchParams.set("userId", "1")
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      json: () => Promise.resolve({ detail: "Invalid or expired reset token" }),
    })

    const user = userEvent.setup()
    render(<ResetPasswordPage />)

    await user.type(screen.getByLabelText("New Password"), "NewPassword2@")
    await user.type(screen.getByLabelText("Confirm Password"), "NewPassword2@")
    await user.click(screen.getByRole("button", { name: /reset password/i }))

    await waitFor(() => {
      expect(screen.getByText(/invalid or expired/i)).toBeInTheDocument()
    })
  })

  it("shows error when token is missing", () => {
    // No token in search params
    render(<ResetPasswordPage />)
    expect(screen.getByText(/invalid or missing/i)).toBeInTheDocument()
  })
})
