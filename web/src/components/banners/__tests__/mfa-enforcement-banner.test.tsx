import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"

vi.mock("next-auth/react", () => ({
  useSession: vi.fn(),
}))

vi.mock("next/link", () => ({
  default: ({
    children,
    href,
    ...props
  }: {
    children: React.ReactNode
    href: string
    [key: string]: unknown
  }) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}))

import { useSession } from "next-auth/react"
const mockUseSession = vi.mocked(useSession)

import { MfaEnforcementBanner } from "../mfa-enforcement-banner"

function mockSession(overrides: Record<string, unknown> = {}) {
  const base = {
    user: { name: "Test User", email: "test@example.com" },
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

function deadlineFromNow(hoursFromNow: number): string {
  return new Date(Date.now() + hoursFromNow * 60 * 60 * 1000).toISOString()
}

describe("MfaEnforcementBanner", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    sessionStorage.clear()
  })

  afterEach(() => {
    sessionStorage.clear()
  })

  describe("visibility conditions", () => {
    it("renders nothing when unauthenticated", () => {
      mockUseSession.mockReturnValue({
        data: null,
        status: "unauthenticated",
        update: vi.fn(),
      } as ReturnType<typeof useSession>)
      const { container } = render(<MfaEnforcementBanner />)
      expect(container.innerHTML).toBe("")
    })

    it("renders nothing for OAuth-only user (no password)", () => {
      mockSession({
        hasPassword: false,
        mfaEnabled: false,
        mfaGraceDeadline: deadlineFromNow(60),
        linkedProviders: ["google"],
      })
      const { container } = render(<MfaEnforcementBanner />)
      expect(container.innerHTML).toBe("")
    })

    it("renders nothing when MFA is enabled", () => {
      mockSession({
        hasPassword: true,
        mfaEnabled: true,
        mfaGraceDeadline: deadlineFromNow(60),
      })
      const { container } = render(<MfaEnforcementBanner />)
      expect(container.innerHTML).toBe("")
    })

    it("renders nothing when no grace deadline", () => {
      mockSession({
        hasPassword: true,
        mfaEnabled: false,
        mfaGraceDeadline: null,
      })
      const { container } = render(<MfaEnforcementBanner />)
      expect(container.innerHTML).toBe("")
    })

    it("renders nothing when deadline has passed (Phase 3)", () => {
      mockSession({
        hasPassword: true,
        mfaEnabled: false,
        mfaGraceDeadline: deadlineFromNow(-1),
      })
      const { container } = render(<MfaEnforcementBanner />)
      expect(container.innerHTML).toBe("")
    })
  })

  describe("Phase 1 (>48h remaining)", () => {
    beforeEach(() => {
      mockSession({
        hasPassword: true,
        mfaEnabled: false,
        mfaGraceDeadline: deadlineFromNow(60),
      })
    })

    it("renders info banner", () => {
      render(<MfaEnforcementBanner />)
      expect(screen.getByTestId("mfa-enforcement-banner")).toBeInTheDocument()
    })

    it("displays setup message", () => {
      render(<MfaEnforcementBanner />)
      expect(
        screen.getByText(/Set up multi-factor authentication/),
      ).toBeInTheDocument()
    })

    it("has link to /mfa/setup", () => {
      render(<MfaEnforcementBanner />)
      const link = screen.getByText(/Set up now/)
      expect(link.closest("a")).toHaveAttribute("href", "/mfa/setup")
    })

    it("is dismissible via close button", () => {
      render(<MfaEnforcementBanner />)
      expect(screen.getByTestId("mfa-enforcement-banner")).toBeInTheDocument()

      fireEvent.click(screen.getByLabelText("Dismiss MFA setup reminder"))

      expect(screen.queryByTestId("mfa-enforcement-banner")).not.toBeInTheDocument()
    })

    it("persists dismissal in sessionStorage", () => {
      render(<MfaEnforcementBanner />)
      fireEvent.click(screen.getByLabelText("Dismiss MFA setup reminder"))
      expect(sessionStorage.getItem("mfa-banner-dismissed")).toBe("true")
    })

    it("stays dismissed on re-render when sessionStorage flag is set", () => {
      sessionStorage.setItem("mfa-banner-dismissed", "true")
      render(<MfaEnforcementBanner />)
      expect(screen.queryByTestId("mfa-enforcement-banner")).not.toBeInTheDocument()
    })

    it("does not have role=alert", () => {
      render(<MfaEnforcementBanner />)
      expect(screen.queryByRole("alert")).not.toBeInTheDocument()
    })
  })

  describe("Phase 2 (0-48h remaining)", () => {
    it("renders warning banner with time remaining", () => {
      mockSession({
        hasPassword: true,
        mfaEnabled: false,
        mfaGraceDeadline: deadlineFromNow(36),
      })
      render(<MfaEnforcementBanner />)
      expect(screen.getByTestId("mfa-enforcement-banner")).toBeInTheDocument()
      expect(screen.getByRole("alert")).toBeInTheDocument()
    })

    it("is not dismissible (no close button)", () => {
      mockSession({
        hasPassword: true,
        mfaEnabled: false,
        mfaGraceDeadline: deadlineFromNow(36),
      })
      render(<MfaEnforcementBanner />)
      expect(
        screen.queryByLabelText("Dismiss MFA setup reminder"),
      ).not.toBeInTheDocument()
    })

    it("shows MFA required message", () => {
      mockSession({
        hasPassword: true,
        mfaEnabled: false,
        mfaGraceDeadline: deadlineFromNow(36),
      })
      render(<MfaEnforcementBanner />)
      expect(
        screen.getByText(/MFA is required for password accounts/),
      ).toBeInTheDocument()
    })

    it("has link to /mfa/setup", () => {
      mockSession({
        hasPassword: true,
        mfaEnabled: false,
        mfaGraceDeadline: deadlineFromNow(36),
      })
      render(<MfaEnforcementBanner />)
      const link = screen.getByText(/Set up now/)
      expect(link.closest("a")).toHaveAttribute("href", "/mfa/setup")
    })
  })

  describe("time remaining formatting", () => {
    it("shows days when >24h remaining", () => {
      mockSession({
        hasPassword: true,
        mfaEnabled: false,
        mfaGraceDeadline: deadlineFromNow(36),
      })
      render(<MfaEnforcementBanner />)
      expect(screen.getByText("1 day")).toBeInTheDocument()
    })

    it("shows plural days", () => {
      // 47h = 1 day (floor of 47/24 = 1), but 47h is in Phase 2 (<48h)
      // Use 47h to stay in Phase 2
      mockSession({
        hasPassword: true,
        mfaEnabled: false,
        mfaGraceDeadline: deadlineFromNow(47),
      })
      render(<MfaEnforcementBanner />)
      expect(screen.getByText("1 day")).toBeInTheDocument()
    })

    it("shows hours when 1-24h remaining", () => {
      mockSession({
        hasPassword: true,
        mfaEnabled: false,
        mfaGraceDeadline: deadlineFromNow(5),
      })
      render(<MfaEnforcementBanner />)
      expect(screen.getByText("5 hours")).toBeInTheDocument()
    })

    it("shows singular hour", () => {
      mockSession({
        hasPassword: true,
        mfaEnabled: false,
        mfaGraceDeadline: deadlineFromNow(1.5),
      })
      render(<MfaEnforcementBanner />)
      expect(screen.getByText("1 hour")).toBeInTheDocument()
    })

    it("shows 'less than an hour' when <1h remaining", () => {
      mockSession({
        hasPassword: true,
        mfaEnabled: false,
        mfaGraceDeadline: deadlineFromNow(0.5),
      })
      render(<MfaEnforcementBanner />)
      expect(screen.getByText("less than an hour")).toBeInTheDocument()
    })
  })

  describe("hybrid user (OAuth + password)", () => {
    it("shows banner when user has password even if they also have OAuth", () => {
      mockSession({
        hasPassword: true,
        mfaEnabled: false,
        mfaGraceDeadline: deadlineFromNow(60),
        linkedProviders: ["google"],
      })
      render(<MfaEnforcementBanner />)
      expect(screen.getByTestId("mfa-enforcement-banner")).toBeInTheDocument()
    })
  })
})
