import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import MfaVerifyPage from "../page"

const mockPush = vi.fn()

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: mockPush,
  }),
  useSearchParams: () => new URLSearchParams("userId=1"),
}))

vi.mock("next-auth/react", () => ({
  signIn: vi.fn(),
}))

describe("MFA Verify Page", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("renders 'Verify Your Identity' heading", () => {
    render(<MfaVerifyPage />)
    expect(
      screen.getByRole("heading", { name: /verify your identity/i })
    ).toBeInTheDocument()
  })

  it("renders TOTP code input labeled 'Verification Code'", () => {
    render(<MfaVerifyPage />)
    expect(screen.getByLabelText(/verification code/i)).toBeInTheDocument()
  })

  it("renders 'Verify' button", () => {
    render(<MfaVerifyPage />)
    expect(
      screen.getByRole("button", { name: /^verify$/i })
    ).toBeInTheDocument()
  })

  it("renders 'Security Key' tab option", async () => {
    render(<MfaVerifyPage />)
    expect(
      screen.getByRole("button", { name: /security key/i })
    ).toBeInTheDocument()
  })
})
