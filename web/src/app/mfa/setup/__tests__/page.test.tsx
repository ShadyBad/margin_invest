import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import MfaSetupPage from "../page"

const mockPush = vi.fn()

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: mockPush,
  }),
}))

vi.mock("qrcode.react", () => ({
  QRCodeSVG: ({ value }: { value: string }) => (
    <svg data-testid="qr-code" data-value={value} />
  ),
}))

vi.mock("@simplewebauthn/browser", () => ({
  startRegistration: vi.fn(),
}))

const mockRecoveryCodes = [
  "aaaa-bbbb",
  "cccc-dddd",
  "eeee-ffff",
  "gggg-hhhh",
  "iiii-jjjj",
  "kkkk-llll",
  "mmmm-nnnn",
  "oooo-pppp",
]

function mockFetchForSetup() {
  vi.spyOn(globalThis, "fetch").mockImplementation(async (url) => {
    const urlStr = typeof url === "string" ? url : url.toString()
    if (urlStr.includes("/api/mfa-challenge")) {
      return new Response(
        JSON.stringify({ userId: "1", challengeToken: "test-token" }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      )
    }
    if (urlStr.includes("setup-totp")) {
      return new Response(
        JSON.stringify({
          provisioning_uri: "otpauth://totp/MarginInvest:user?secret=ABC123",
          secret_id: 42,
        }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      )
    }
    if (urlStr.includes("confirm-totp")) {
      return new Response(
        JSON.stringify({
          confirmed: true,
          recovery_codes: mockRecoveryCodes,
        }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      )
    }
    return new Response("{}", { status: 404 })
  })
}

function mockFetchForChallengeOnly() {
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

describe("MFA Setup Page", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.restoreAllMocks()
  })

  it("renders 'Set Up MFA' heading", async () => {
    mockFetchForChallengeOnly()
    render(<MfaSetupPage />)
    await waitFor(() => {
      expect(
        screen.getByRole("heading", { name: /set up mfa/i })
      ).toBeInTheDocument()
    })
  })

  it("renders 'Authenticator App' and 'Security Key' options", async () => {
    mockFetchForChallengeOnly()
    render(<MfaSetupPage />)
    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /authenticator app/i })
      ).toBeInTheDocument()
    })
    expect(
      screen.getByRole("button", { name: /security key/i })
    ).toBeInTheDocument()
  })

  it("renders 'Verification Code' input field after choosing authenticator", async () => {
    const user = userEvent.setup()
    mockFetchForSetup()

    render(<MfaSetupPage />)

    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /authenticator app/i })
      ).toBeInTheDocument()
    })

    await user.click(
      screen.getByRole("button", { name: /authenticator app/i })
    )

    await waitFor(() => {
      expect(screen.getByLabelText(/verification code/i)).toBeInTheDocument()
    })
  })

  it("shows recovery codes step after TOTP confirmation", async () => {
    const user = userEvent.setup()
    mockFetchForSetup()

    render(<MfaSetupPage />)

    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /authenticator app/i })
      ).toBeInTheDocument()
    })

    // Choose authenticator
    await user.click(screen.getByRole("button", { name: /authenticator app/i }))
    await waitFor(() => expect(screen.getByTestId("qr-code")).toBeInTheDocument())

    // Enter code and submit
    await user.type(screen.getByPlaceholderText("000000"), "123456")
    await user.click(screen.getByRole("button", { name: /verify & enable/i }))

    // Recovery codes step should appear
    await waitFor(() => {
      expect(screen.getByText("Save your recovery codes")).toBeInTheDocument()
    })
    const codeElements = screen.getAllByTestId("recovery-code")
    expect(codeElements).toHaveLength(8)

    // Should NOT have redirected yet
    expect(mockPush).not.toHaveBeenCalled()
  })

  it("redirects to /account after confirming recovery codes saved", async () => {
    const user = userEvent.setup()
    mockFetchForSetup()

    render(<MfaSetupPage />)

    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /authenticator app/i })
      ).toBeInTheDocument()
    })

    // Go through full setup flow
    await user.click(screen.getByRole("button", { name: /authenticator app/i }))
    await waitFor(() => expect(screen.getByTestId("qr-code")).toBeInTheDocument())
    await user.type(screen.getByPlaceholderText("000000"), "123456")
    await user.click(screen.getByRole("button", { name: /verify & enable/i }))

    // Wait for recovery codes
    await waitFor(() => expect(screen.getByText("Save your recovery codes")).toBeInTheDocument())

    // Check the checkbox and click Continue
    await user.click(screen.getByTestId("saved-checkbox"))
    await user.click(screen.getByRole("button", { name: "Continue" }))

    expect(mockPush).toHaveBeenCalledWith("/account")
  })
})
