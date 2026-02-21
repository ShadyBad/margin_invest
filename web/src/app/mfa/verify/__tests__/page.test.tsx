import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import MfaVerifyPage from "../page"

vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams("userId=1&challengeToken=test-token"),
}))

const mockSignIn = vi.fn()
vi.mock("next-auth/react", () => ({
  signIn: (...args: unknown[]) => mockSignIn(...args),
}))

vi.mock("@simplewebauthn/browser", () => ({
  startAuthentication: vi.fn(),
}))

// Mock sessionStorage
const mockSessionStorage: Record<string, string> = {
  mfa_username: "testuser",
  mfa_password: "testpass",
}
Object.defineProperty(window, "sessionStorage", {
  value: {
    getItem: (key: string) => mockSessionStorage[key] ?? "",
    setItem: (key: string, value: string) => {
      mockSessionStorage[key] = value
    },
    removeItem: (key: string) => {
      delete mockSessionStorage[key]
    },
  },
  writable: true,
})

describe("MFA Verify Page", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.restoreAllMocks()
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

  it("shows 'Use a recovery code' link on TOTP view", () => {
    render(<MfaVerifyPage />)
    expect(screen.getByText("Use a recovery code")).toBeInTheDocument()
  })

  it("reveals recovery code input when link is clicked", async () => {
    const user = userEvent.setup()
    render(<MfaVerifyPage />)

    await user.click(screen.getByText("Use a recovery code"))

    expect(screen.getByLabelText("Recovery code")).toBeInTheDocument()
    expect(screen.getByPlaceholderText("xxxx-xxxx")).toBeInTheDocument()
  })

  it("shows Contact support link in recovery mode", async () => {
    const user = userEvent.setup()
    render(<MfaVerifyPage />)

    await user.click(screen.getByText("Use a recovery code"))

    const supportLink = screen.getByText("Contact support")
    expect(supportLink).toBeInTheDocument()
    expect(supportLink.closest("a")).toHaveAttribute(
      "href",
      "/support?subject=MFA+recovery"
    )
  })

  it("can switch back to authenticator from recovery", async () => {
    const user = userEvent.setup()
    render(<MfaVerifyPage />)

    // Switch to recovery
    await user.click(screen.getByText("Use a recovery code"))
    expect(screen.getByLabelText("Recovery code")).toBeInTheDocument()

    // Switch back
    await user.click(screen.getByText("Back to authenticator"))
    expect(screen.getByLabelText("Verification Code")).toBeInTheDocument()
  })

  it("submits recovery code to verify-recovery endpoint", async () => {
    const user = userEvent.setup()

    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({ verified: true, mfa_token: "recovery-mfa-token" }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      )
    )

    render(<MfaVerifyPage />)

    // Switch to recovery
    await user.click(screen.getByText("Use a recovery code"))

    // Enter code and submit
    await user.type(screen.getByPlaceholderText("xxxx-xxxx"), "aaaa-bbbb")
    await user.click(screen.getByRole("button", { name: "Verify" }))

    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalledWith(
        "/api/v1/auth/mfa/verify-recovery",
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({
            user_id: 1,
            code: "aaaa-bbbb",
            challenge_token: "test-token",
          }),
        })
      )
    })

    // Should sign in with credentials and mfaToken
    await waitFor(() => {
      expect(mockSignIn).toHaveBeenCalledWith("credentials", {
        username: "testuser",
        password: "testpass",
        mfaToken: "recovery-mfa-token",
        callbackUrl: "/dashboard",
      })
    })
  })

  it("shows error when recovery code is invalid", async () => {
    const user = userEvent.setup()

    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({ detail: "Invalid or already used recovery code" }),
        { status: 400, headers: { "Content-Type": "application/json" } }
      )
    )

    render(<MfaVerifyPage />)

    await user.click(screen.getByText("Use a recovery code"))
    await user.type(screen.getByPlaceholderText("xxxx-xxxx"), "bad-code")
    await user.click(screen.getByRole("button", { name: "Verify" }))

    await waitFor(() => {
      expect(
        screen.getByText("Invalid or already used recovery code")
      ).toBeInTheDocument()
    })
  })
})
