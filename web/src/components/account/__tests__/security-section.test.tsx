import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
import userEvent from "@testing-library/user-event"

vi.mock("next-auth/react", () => ({
  useSession: vi.fn(),
}))

import { useSession } from "next-auth/react"
const mockUseSession = vi.mocked(useSession)

import { SecuritySection } from "../security-section"

function mockSession(overrides: Record<string, unknown> = {}) {
  const base = {
    user: {
      name: "Jane Doe",
      email: "jane@example.com",
      image: null,
    },
    authMethod: "credentials" as const,
    oauthProvider: null as string | null,
    mfaVerified: false,
    expires: "2099-01-01",
    ...overrides,
  }
  mockUseSession.mockReturnValue({
    data: base,
    status: "authenticated",
    update: vi.fn(),
  } as ReturnType<typeof useSession>)
}

describe("SecuritySection", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("renders security heading for credentials user", () => {
    mockSession()
    render(<SecuritySection />)
    expect(screen.getByRole("heading", { name: /security/i })).toBeInTheDocument()
  })

  it("shows change password form for credentials user", () => {
    mockSession()
    render(<SecuritySection />)
    expect(screen.getByLabelText("Current password")).toBeInTheDocument()
    expect(screen.getByLabelText("New password")).toBeInTheDocument()
    expect(screen.getByLabelText("Confirm new password")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /update password/i })).toBeInTheDocument()
  })

  it('shows "secured by Google" message for Google OAuth user', () => {
    mockSession({ authMethod: "oauth", oauthProvider: "google" })
    render(<SecuritySection />)
    expect(screen.getByText(/secured by Google/)).toBeInTheDocument()
  })

  it('shows "secured by GitHub" message for GitHub OAuth user', () => {
    mockSession({ authMethod: "oauth", oauthProvider: "github" })
    render(<SecuritySection />)
    expect(screen.getByText(/secured by GitHub/)).toBeInTheDocument()
  })

  it("shows MFA enabled indicator when mfaVerified is true", () => {
    mockSession({ mfaVerified: true })
    render(<SecuritySection />)
    expect(screen.getByText("MFA is enabled")).toBeInTheDocument()
  })

  it("shows MFA not configured when mfaVerified is false", () => {
    mockSession({ mfaVerified: false })
    render(<SecuritySection />)
    expect(screen.getByText("MFA is not configured")).toBeInTheDocument()
  })

  it("shows error when passwords don't match", async () => {
    mockSession()
    global.fetch = vi.fn()
    const user = userEvent.setup()
    render(<SecuritySection />)

    await user.type(screen.getByLabelText("Current password"), "OldPassword123!")
    await user.type(screen.getByLabelText("New password"), "NewPassword123!")
    await user.type(screen.getByLabelText("Confirm new password"), "DifferentPass123!")
    await user.click(screen.getByRole("button", { name: /update password/i }))

    expect(screen.getByText("Passwords do not match.")).toBeInTheDocument()
    expect(global.fetch).not.toHaveBeenCalled()
  })

  it("shows error when password too short (< 12 chars)", async () => {
    mockSession()
    global.fetch = vi.fn()
    const user = userEvent.setup()
    render(<SecuritySection />)

    await user.type(screen.getByLabelText("Current password"), "OldPassword123!")
    await user.type(screen.getByLabelText("New password"), "Short1!")
    await user.type(screen.getByLabelText("Confirm new password"), "Short1!")

    // Use fireEvent.submit to bypass HTML5 minLength validation
    const form = screen.getByRole("button", { name: /update password/i }).closest("form")!
    fireEvent.submit(form)

    expect(
      screen.getByText("New password must be at least 12 characters.")
    ).toBeInTheDocument()
    expect(global.fetch).not.toHaveBeenCalled()
  })

  it("returns null when no session user", () => {
    mockUseSession.mockReturnValue({
      data: null,
      status: "unauthenticated",
      update: vi.fn(),
    } as ReturnType<typeof useSession>)
    const { container } = render(<SecuritySection />)
    expect(container.innerHTML).toBe("")
  })
})
