import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import MfaSetupPage from "../page"

const mockPush = vi.fn()

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: mockPush,
  }),
  useSearchParams: () => new URLSearchParams("userId=1"),
}))

vi.mock("qrcode.react", () => ({
  QRCodeSVG: ({ value }: { value: string }) => (
    <svg data-testid="qr-code" data-value={value} />
  ),
}))

describe("MFA Setup Page", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("renders 'Set Up MFA' heading", () => {
    render(<MfaSetupPage />)
    expect(
      screen.getByRole("heading", { name: /set up mfa/i })
    ).toBeInTheDocument()
  })

  it("renders 'Authenticator App' and 'Security Key' options", () => {
    render(<MfaSetupPage />)
    expect(
      screen.getByRole("button", { name: /authenticator app/i })
    ).toBeInTheDocument()
    expect(
      screen.getByRole("button", { name: /security key/i })
    ).toBeInTheDocument()
  })

  it("renders 'Verification Code' input field after choosing authenticator", async () => {
    const user = userEvent.setup()

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          provisioning_uri: "otpauth://totp/MarginInvest:user?secret=ABC123",
        }),
    })

    render(<MfaSetupPage />)

    await user.click(
      screen.getByRole("button", { name: /authenticator app/i })
    )

    await waitFor(() => {
      expect(screen.getByLabelText(/verification code/i)).toBeInTheDocument()
    })
  })
})
