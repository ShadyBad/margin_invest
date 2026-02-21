import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { MfaStatus } from "../mfa-status"

// Mock next/link
vi.mock("next/link", () => ({
  default: ({ children, href, ...props }: { children: React.ReactNode; href: string; [key: string]: unknown }) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}))

describe("MfaStatus", () => {
  describe("State 1: OAuth-only, no password", () => {
    it("shows MFA managed through OAuth provider", () => {
      render(
        <MfaStatus
          hasPassword={false}
          mfaEnabled={false}
          mfaGraceDeadline={null}
          oauthProvider="google"
        />
      )
      expect(
        screen.getByText(/managed through your Google account/)
      ).toBeInTheDocument()
    })

    it("shows provider name for GitHub", () => {
      render(
        <MfaStatus
          hasPassword={false}
          mfaEnabled={false}
          mfaGraceDeadline={null}
          oauthProvider="github"
        />
      )
      expect(
        screen.getByText(/managed through your GitHub account/)
      ).toBeInTheDocument()
    })
  })

  describe("State 2: Has password, MFA not enabled", () => {
    it("shows not configured status with yellow dot", () => {
      render(
        <MfaStatus
          hasPassword={true}
          mfaEnabled={false}
          mfaGraceDeadline={null}
          oauthProvider={null}
        />
      )
      expect(screen.getByText("Not configured")).toBeInTheDocument()
      const dot = screen.getByLabelText("MFA status: Not configured")
      expect(dot.className).toContain("bg-amber-500")
    })

    it("shows status with role='status'", () => {
      render(
        <MfaStatus
          hasPassword={true}
          mfaEnabled={false}
          mfaGraceDeadline={null}
          oauthProvider={null}
        />
      )
      expect(screen.getByRole("status")).toBeInTheDocument()
    })

    it("shows description text about MFA", () => {
      render(
        <MfaStatus
          hasPassword={true}
          mfaEnabled={false}
          mfaGraceDeadline={null}
          oauthProvider={null}
        />
      )
      expect(
        screen.getByText(/adds a second layer of verification/)
      ).toBeInTheDocument()
    })

    it("shows Set Up MFA link pointing to /mfa/setup", () => {
      render(
        <MfaStatus
          hasPassword={true}
          mfaEnabled={false}
          mfaGraceDeadline={null}
          oauthProvider={null}
        />
      )
      const link = screen.getByText("Set Up MFA")
      expect(link).toBeInTheDocument()
      expect(link.closest("a")).toHaveAttribute("href", "/mfa/setup")
    })

    it("shows grace period warning banner when deadline is in the future", () => {
      const futureDate = new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString()
      render(
        <MfaStatus
          hasPassword={true}
          mfaEnabled={false}
          mfaGraceDeadline={futureDate}
          oauthProvider={null}
        />
      )
      const alert = screen.getByRole("alert")
      expect(alert).toBeInTheDocument()
      expect(alert.textContent).toContain("days to set up MFA")
    })

    it("shows expired grace period banner when deadline is in the past", () => {
      const pastDate = new Date(Date.now() - 1000).toISOString()
      render(
        <MfaStatus
          hasPassword={true}
          mfaEnabled={false}
          mfaGraceDeadline={pastDate}
          oauthProvider={null}
        />
      )
      const alert = screen.getByRole("alert")
      expect(alert).toBeInTheDocument()
      expect(alert.textContent).toContain("grace period has expired")
    })

    it("does not show grace period banner when no deadline", () => {
      render(
        <MfaStatus
          hasPassword={true}
          mfaEnabled={false}
          mfaGraceDeadline={null}
          oauthProvider={null}
        />
      )
      expect(screen.queryByRole("alert")).not.toBeInTheDocument()
    })
  })

  describe("State 3: Has password, MFA enabled", () => {
    it("shows enabled status with green dot", () => {
      render(
        <MfaStatus
          hasPassword={true}
          mfaEnabled={true}
          mfaGraceDeadline={null}
          oauthProvider={null}
        />
      )
      const dot = screen.getByLabelText("MFA status: Enabled")
      expect(dot.className).toContain("bg-emerald-500")
    })

    it("shows authenticator app label", () => {
      render(
        <MfaStatus
          hasPassword={true}
          mfaEnabled={true}
          mfaGraceDeadline={null}
          oauthProvider={null}
        />
      )
      expect(screen.getByText(/Authenticator app/)).toBeInTheDocument()
    })

    it("shows protected message", () => {
      render(
        <MfaStatus
          hasPassword={true}
          mfaEnabled={true}
          mfaGraceDeadline={null}
          oauthProvider={null}
        />
      )
      expect(
        screen.getByText(/protected by an authenticator app/)
      ).toBeInTheDocument()
    })

    it("shows regenerate recovery codes button", () => {
      const onRegenerate = vi.fn()
      render(
        <MfaStatus
          hasPassword={true}
          mfaEnabled={true}
          mfaGraceDeadline={null}
          oauthProvider={null}
          onRegenerateCodes={onRegenerate}
        />
      )
      expect(
        screen.getByText("Regenerate Recovery Codes")
      ).toBeInTheDocument()
    })

    it("calls onRegenerateCodes when regenerate button clicked", async () => {
      const user = userEvent.setup()
      const onRegenerate = vi.fn()
      render(
        <MfaStatus
          hasPassword={true}
          mfaEnabled={true}
          mfaGraceDeadline={null}
          oauthProvider={null}
          onRegenerateCodes={onRegenerate}
        />
      )
      await user.click(screen.getByText("Regenerate Recovery Codes"))
      expect(onRegenerate).toHaveBeenCalledTimes(1)
    })

    it("shows remove MFA button", () => {
      const onDisable = vi.fn()
      render(
        <MfaStatus
          hasPassword={true}
          mfaEnabled={true}
          mfaGraceDeadline={null}
          oauthProvider={null}
          onDisableMfa={onDisable}
        />
      )
      expect(screen.getByText("Remove MFA")).toBeInTheDocument()
    })

    it("calls onDisableMfa when remove button clicked", async () => {
      const user = userEvent.setup()
      const onDisable = vi.fn()
      render(
        <MfaStatus
          hasPassword={true}
          mfaEnabled={true}
          mfaGraceDeadline={null}
          oauthProvider={null}
          onDisableMfa={onDisable}
        />
      )
      await user.click(screen.getByText("Remove MFA"))
      expect(onDisable).toHaveBeenCalledTimes(1)
    })

    it("shows regenerating state", () => {
      render(
        <MfaStatus
          hasPassword={true}
          mfaEnabled={true}
          mfaGraceDeadline={null}
          oauthProvider={null}
          onRegenerateCodes={() => {}}
          regenerating={true}
        />
      )
      expect(screen.getByText("Regenerating...")).toBeInTheDocument()
    })

    it("shows disabling state", () => {
      render(
        <MfaStatus
          hasPassword={true}
          mfaEnabled={true}
          mfaGraceDeadline={null}
          oauthProvider={null}
          onDisableMfa={() => {}}
          disabling={true}
        />
      )
      expect(screen.getByText("Removing...")).toBeInTheDocument()
    })
  })

  describe("Fallback state", () => {
    it("shows fallback when no password and no OAuth provider", () => {
      render(
        <MfaStatus
          hasPassword={false}
          mfaEnabled={false}
          mfaGraceDeadline={null}
          oauthProvider={null}
        />
      )
      expect(
        screen.getByText(/Set a password to enable multi-factor authentication/)
      ).toBeInTheDocument()
    })
  })
})
