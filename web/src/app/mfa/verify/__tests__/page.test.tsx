import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import MfaVerifyPage from "../page"

vi.mock("next-auth/react", () => ({
  signIn: (...args: unknown[]) => mockSignIn(...args),
}))

vi.mock("@simplewebauthn/browser", () => ({
  startAuthentication: vi.fn(),
}))

const mockSignIn = vi.fn()

function mockFetchForChallenge() {
  vi.spyOn(globalThis, "fetch").mockImplementation(async (url) => {
    const urlStr = typeof url === "string" ? url : url.toString()
    if (urlStr.includes("/api/mfa-challenge")) {
      return new Response(
        JSON.stringify({ userId: "1", challengeToken: "test-token" }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      )
    }
    return new Response("{}", { status: 404 })
  })
}

function mockFetchForChallengeAndComplete() {
  vi.spyOn(globalThis, "fetch").mockImplementation(async (url) => {
    const urlStr = typeof url === "string" ? url : url.toString()
    if (urlStr.includes("/api/mfa-challenge")) {
      return new Response(
        JSON.stringify({ userId: "1", challengeToken: "test-token" }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      )
    }
    if (urlStr.includes("mfa/complete")) {
      return new Response(
        JSON.stringify({ mfa_completion_token: "test-completion-token" }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      )
    }
    return new Response("{}", { status: 404 })
  })
}

describe("MFA Verify Page", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.restoreAllMocks()
  })

  it("renders 'Verify Your Identity' heading", async () => {
    mockFetchForChallenge()
    render(<MfaVerifyPage />)
    await waitFor(() => {
      expect(
        screen.getByRole("heading", { name: /verify your identity/i })
      ).toBeInTheDocument()
    })
  })

  it("renders TOTP code input labeled 'Verification Code'", async () => {
    mockFetchForChallenge()
    render(<MfaVerifyPage />)
    await waitFor(() => {
      expect(screen.getByLabelText(/verification code/i)).toBeInTheDocument()
    })
  })

  it("renders 'Verify' button", async () => {
    mockFetchForChallenge()
    render(<MfaVerifyPage />)
    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /^verify$/i })
      ).toBeInTheDocument()
    })
  })

  it("renders 'Security Key' tab option", async () => {
    mockFetchForChallenge()
    render(<MfaVerifyPage />)
    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /security key/i })
      ).toBeInTheDocument()
    })
  })

  it("shows 'Use a recovery code' link on TOTP view", async () => {
    mockFetchForChallenge()
    render(<MfaVerifyPage />)
    await waitFor(() => {
      expect(screen.getByText("Use a recovery code")).toBeInTheDocument()
    })
  })

  it("reveals recovery code input when link is clicked", async () => {
    mockFetchForChallenge()
    const user = userEvent.setup()
    render(<MfaVerifyPage />)

    await waitFor(() => {
      expect(screen.getByText("Use a recovery code")).toBeInTheDocument()
    })

    await user.click(screen.getByText("Use a recovery code"))

    expect(screen.getByLabelText("Recovery code")).toBeInTheDocument()
    expect(screen.getByPlaceholderText("xxxx-xxxx")).toBeInTheDocument()
  })

  it("shows Contact support link in recovery mode", async () => {
    mockFetchForChallenge()
    const user = userEvent.setup()
    render(<MfaVerifyPage />)

    await waitFor(() => {
      expect(screen.getByText("Use a recovery code")).toBeInTheDocument()
    })

    await user.click(screen.getByText("Use a recovery code"))

    const supportLink = screen.getByText("Contact support")
    expect(supportLink).toBeInTheDocument()
    expect(supportLink.closest("a")).toHaveAttribute(
      "href",
      "/support?subject=MFA+recovery"
    )
  })

  it("can switch back to authenticator from recovery", async () => {
    mockFetchForChallenge()
    const user = userEvent.setup()
    render(<MfaVerifyPage />)

    await waitFor(() => {
      expect(screen.getByText("Use a recovery code")).toBeInTheDocument()
    })

    // Switch to recovery
    await user.click(screen.getByText("Use a recovery code"))
    expect(screen.getByLabelText("Recovery code")).toBeInTheDocument()

    // Switch back
    await user.click(screen.getByText("Back to authenticator"))
    expect(screen.getByLabelText("Verification Code")).toBeInTheDocument()
  })

  it("submits TOTP code to mfa/complete endpoint and signs in with completion token", async () => {
    mockFetchForChallengeAndComplete()
    const user = userEvent.setup()

    render(<MfaVerifyPage />)

    await waitFor(() => {
      expect(screen.getByLabelText(/verification code/i)).toBeInTheDocument()
    })

    // Enter code and submit
    await user.type(screen.getByPlaceholderText("000000"), "123456")
    await user.click(screen.getByRole("button", { name: /^verify$/i }))

    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalledWith(
        "/api/v1/auth/mfa/complete",
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({ totp_code: "123456" }),
          credentials: "include",
        })
      )
    })

    // Should sign in with mfaCompletionToken (no password)
    await waitFor(() => {
      expect(mockSignIn).toHaveBeenCalledWith("credentials", {
        mfaCompletionToken: "test-completion-token",
        callbackUrl: "/dashboard",
      })
    })
  })

  it("submits recovery code to mfa/complete endpoint", async () => {
    mockFetchForChallengeAndComplete()
    const user = userEvent.setup()

    render(<MfaVerifyPage />)

    await waitFor(() => {
      expect(screen.getByText("Use a recovery code")).toBeInTheDocument()
    })

    // Switch to recovery
    await user.click(screen.getByText("Use a recovery code"))

    // Enter code and submit
    await user.type(screen.getByPlaceholderText("xxxx-xxxx"), "aaaa-bbbb")
    await user.click(screen.getByRole("button", { name: "Verify" }))

    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalledWith(
        "/api/v1/auth/mfa/complete",
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({ recovery_code: "aaaa-bbbb" }),
          credentials: "include",
        })
      )
    })

    // Should sign in with mfaCompletionToken
    await waitFor(() => {
      expect(mockSignIn).toHaveBeenCalledWith("credentials", {
        mfaCompletionToken: "test-completion-token",
        callbackUrl: "/dashboard",
      })
    })
  })

  it("shows error when verification fails", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (url) => {
      const urlStr = typeof url === "string" ? url : url.toString()
      if (urlStr.includes("/api/mfa-challenge")) {
        return new Response(
          JSON.stringify({ userId: "1", challengeToken: "test-token" }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
      }
      if (urlStr.includes("mfa/complete")) {
        return new Response(
          JSON.stringify({ detail: "Invalid verification code" }),
          { status: 401, headers: { "Content-Type": "application/json" } }
        )
      }
      return new Response("{}", { status: 404 })
    })

    const user = userEvent.setup()
    render(<MfaVerifyPage />)

    await waitFor(() => {
      expect(screen.getByLabelText(/verification code/i)).toBeInTheDocument()
    })

    await user.type(screen.getByPlaceholderText("000000"), "000000")
    await user.click(screen.getByRole("button", { name: /^verify$/i }))

    await waitFor(() => {
      expect(
        screen.getByText("Invalid verification code")
      ).toBeInTheDocument()
    })
  })
})
