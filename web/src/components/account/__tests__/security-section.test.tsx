import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen } from "@testing-library/react"

vi.mock("next-auth/react", () => ({
  useSession: vi.fn(),
}))

vi.mock("next/link", () => ({
  default: ({ children, href, ...props }: { children: React.ReactNode; href: string; [key: string]: unknown }) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
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
    hasPassword: true,
    mfaEnabled: false,
    mfaGraceDeadline: null as string | null,
    linkedProviders: [] as string[],
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

  it("renders security heading", () => {
    mockSession()
    render(<SecuritySection />)
    expect(screen.getByRole("heading", { name: /security/i })).toBeInTheDocument()
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

  it("renders Google and GitHub provider icons", () => {
    mockSession()
    render(<SecuritySection />)
    expect(screen.getByText("Google")).toBeInTheDocument()
    expect(screen.getByText("GitHub")).toBeInTheDocument()
  })

  it("shows OAuth-only message for OAuth user without password", () => {
    mockSession({
      authMethod: "oauth",
      oauthProvider: "google",
      hasPassword: false,
      linkedProviders: ["google"],
    })
    render(<SecuritySection />)
    expect(screen.getByText(/secured by Google OAuth/)).toBeInTheDocument()
  })

  it("does not show OAuth-only message for credentials user with password", () => {
    mockSession({ authMethod: "credentials", hasPassword: true })
    render(<SecuritySection />)
    expect(screen.queryByText(/secured by.*OAuth/)).not.toBeInTheDocument()
  })

  it("renders password section", () => {
    mockSession()
    render(<SecuritySection />)
    expect(screen.getByText("Password")).toBeInTheDocument()
  })

  it("renders MFA section", () => {
    mockSession()
    render(<SecuritySection />)
    expect(screen.getByText("Multi-Factor Authentication")).toBeInTheDocument()
  })

  describe("credentials user with password, MFA not enabled", () => {
    it("shows change password button and MFA not configured", () => {
      mockSession({ hasPassword: true, mfaEnabled: false })
      render(<SecuritySection />)
      expect(
        screen.getByRole("button", { name: /change password/i })
      ).toBeInTheDocument()
      expect(screen.getByText("Not configured")).toBeInTheDocument()
    })

    it("shows Set Up MFA link", () => {
      mockSession({ hasPassword: true, mfaEnabled: false })
      render(<SecuritySection />)
      const link = screen.getByText("Set Up MFA")
      expect(link.closest("a")).toHaveAttribute("href", "/mfa/setup")
    })
  })

  describe("credentials user with password, MFA enabled", () => {
    it("shows MFA enabled status", () => {
      mockSession({ hasPassword: true, mfaEnabled: true })
      render(<SecuritySection />)
      expect(screen.getByText(/Authenticator app/)).toBeInTheDocument()
    })

    it("shows regenerate and remove MFA buttons", () => {
      mockSession({ hasPassword: true, mfaEnabled: true })
      render(<SecuritySection />)
      expect(screen.getByText("Regenerate Recovery Codes")).toBeInTheDocument()
      expect(screen.getByText("Remove MFA")).toBeInTheDocument()
    })
  })

  describe("OAuth user without password", () => {
    it("shows set password option", () => {
      mockSession({
        authMethod: "oauth",
        oauthProvider: "google",
        hasPassword: false,
        linkedProviders: ["google"],
      })
      render(<SecuritySection />)
      expect(
        screen.getByRole("button", { name: /set password/i })
      ).toBeInTheDocument()
    })

    it("shows MFA managed through provider", () => {
      mockSession({
        authMethod: "oauth",
        oauthProvider: "google",
        hasPassword: false,
        linkedProviders: ["google"],
      })
      render(<SecuritySection />)
      expect(
        screen.getByText(/Multi-factor authentication is managed through your Google account/)
      ).toBeInTheDocument()
    })
  })

  describe("hybrid user (OAuth + password)", () => {
    it("shows both change password and remove password", () => {
      mockSession({
        authMethod: "oauth",
        oauthProvider: "google",
        hasPassword: true,
        linkedProviders: ["google"],
      })
      render(<SecuritySection />)
      expect(
        screen.getByRole("button", { name: /change password/i })
      ).toBeInTheDocument()
      expect(
        screen.getByRole("button", { name: /remove password/i })
      ).toBeInTheDocument()
    })

    it("shows MFA section with set up option when MFA not enabled", () => {
      mockSession({
        authMethod: "oauth",
        oauthProvider: "google",
        hasPassword: true,
        mfaEnabled: false,
        linkedProviders: ["google"],
      })
      render(<SecuritySection />)
      expect(screen.getByText("Set Up MFA")).toBeInTheDocument()
    })
  })

  describe("grace period", () => {
    it("shows grace period warning banner", () => {
      const futureDate = new Date(Date.now() + 5 * 24 * 60 * 60 * 1000).toISOString()
      mockSession({
        hasPassword: true,
        mfaEnabled: false,
        mfaGraceDeadline: futureDate,
      })
      render(<SecuritySection />)
      expect(screen.getByRole("alert")).toBeInTheDocument()
    })
  })

  describe("connected providers", () => {
    it("shows connected state for linked provider", () => {
      mockSession({
        linkedProviders: ["google"],
      })
      render(<SecuritySection />)
      expect(screen.getByLabelText("Google \u2014 Connected")).toBeInTheDocument()
    })

    it("shows not connected for unlinked available provider", () => {
      mockSession({
        linkedProviders: [],
      })
      render(<SecuritySection />)
      expect(screen.getByLabelText("GitHub \u2014 Not connected")).toBeInTheDocument()
    })
  })

  it("calls session update on mount", () => {
    const mockUpdate = vi.fn()
    mockUseSession.mockReturnValue({
      data: {
        user: { name: "Jane", email: "jane@example.com", image: null },
        authMethod: "oauth" as const,
        oauthProvider: "google",
        mfaVerified: true,
        hasPassword: false,
        mfaEnabled: false,
        mfaGraceDeadline: null,
        linkedProviders: ["google"],
        expires: "2099-01-01",
      },
      status: "authenticated",
      update: mockUpdate,
    } as ReturnType<typeof useSession>)

    render(<SecuritySection />)
    expect(mockUpdate).toHaveBeenCalledTimes(1)
  })
})
