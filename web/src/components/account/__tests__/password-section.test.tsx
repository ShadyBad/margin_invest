import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, fireEvent, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { PasswordSection } from "../password-section"

describe("PasswordSection", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe("No password state (OAuth-only)", () => {
    it("shows message about not having a password", () => {
      render(
        <PasswordSection
          hasPassword={false}
          oauthProvider="google"
          linkedProviders={["google"]}
        />
      )
      expect(
        screen.getByText(/don't have a password on this account/)
      ).toBeInTheDocument()
    })

    it("mentions the OAuth provider name", () => {
      render(
        <PasswordSection
          hasPassword={false}
          oauthProvider="google"
          linkedProviders={["google"]}
        />
      )
      expect(screen.getByText(/alternative to Google/)).toBeInTheDocument()
    })

    it("shows Set Password button", () => {
      render(
        <PasswordSection
          hasPassword={false}
          oauthProvider="google"
          linkedProviders={["google"]}
        />
      )
      expect(
        screen.getByRole("button", { name: /set password/i })
      ).toBeInTheDocument()
    })

    it("reveals set password form when Set Password clicked", async () => {
      const user = userEvent.setup()
      render(
        <PasswordSection
          hasPassword={false}
          oauthProvider="google"
          linkedProviders={["google"]}
        />
      )

      await user.click(screen.getByRole("button", { name: /set password/i }))

      expect(screen.getByLabelText("New password")).toBeInTheDocument()
      expect(screen.getByLabelText("Confirm password")).toBeInTheDocument()
    })

    it("hides form when Cancel clicked", async () => {
      const user = userEvent.setup()
      render(
        <PasswordSection
          hasPassword={false}
          oauthProvider="google"
          linkedProviders={["google"]}
        />
      )

      await user.click(screen.getByRole("button", { name: /set password/i }))
      expect(screen.getByLabelText("New password")).toBeInTheDocument()

      await user.click(screen.getByRole("button", { name: /cancel/i }))
      expect(screen.queryByLabelText("New password")).not.toBeInTheDocument()
    })

    it("shows error when passwords don't match on set", async () => {
      const user = userEvent.setup()
      global.fetch = vi.fn()
      render(
        <PasswordSection
          hasPassword={false}
          oauthProvider="google"
          linkedProviders={["google"]}
        />
      )

      await user.click(screen.getByRole("button", { name: /set password/i }))
      await user.type(screen.getByLabelText("New password"), "SecurePass1234!")
      await user.type(screen.getByLabelText("Confirm password"), "DifferentPass!")

      const form = screen.getByRole("button", { name: /^set password$/i }).closest("form")!
      fireEvent.submit(form)

      expect(screen.getByText("Passwords do not match.")).toBeInTheDocument()
      expect(global.fetch).not.toHaveBeenCalled()
    })

    it("calls set-password API on successful submit", async () => {
      const user = userEvent.setup()
      global.fetch = vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve({}) })
      render(
        <PasswordSection
          hasPassword={false}
          oauthProvider="google"
          linkedProviders={["google"]}
        />
      )

      await user.click(screen.getByRole("button", { name: /set password/i }))
      await user.type(screen.getByLabelText("New password"), "SecurePass1234!")
      await user.type(screen.getByLabelText("Confirm password"), "SecurePass1234!")
      await user.click(screen.getByRole("button", { name: /^set password$/i }))

      expect(global.fetch).toHaveBeenCalledWith("/api/v1/auth/set-password", expect.objectContaining({
        method: "POST",
      }))
    })
  })

  describe("Has password state", () => {
    it("shows Change Password button", () => {
      render(
        <PasswordSection
          hasPassword={true}
          oauthProvider={null}
          linkedProviders={[]}
        />
      )
      expect(
        screen.getByRole("button", { name: /change password/i })
      ).toBeInTheDocument()
    })

    it("shows password last changed time when provided", () => {
      const oneHourAgo = new Date(Date.now() - 3600000).toISOString()
      render(
        <PasswordSection
          hasPassword={true}
          oauthProvider={null}
          linkedProviders={[]}
          passwordLastChanged={oneHourAgo}
        />
      )
      expect(screen.getByText(/Password last changed/)).toBeInTheDocument()
    })

    it("reveals change password form when Change Password clicked", async () => {
      const user = userEvent.setup()
      render(
        <PasswordSection
          hasPassword={true}
          oauthProvider={null}
          linkedProviders={[]}
        />
      )

      await user.click(screen.getByRole("button", { name: /change password/i }))

      expect(screen.getByLabelText("Current password")).toBeInTheDocument()
      expect(screen.getByLabelText("New password")).toBeInTheDocument()
      expect(screen.getByLabelText("Confirm new password")).toBeInTheDocument()
    })

    it("shows Remove Password button when user has linked providers", () => {
      render(
        <PasswordSection
          hasPassword={true}
          oauthProvider="google"
          linkedProviders={["google"]}
        />
      )
      expect(
        screen.getByRole("button", { name: /remove password/i })
      ).toBeInTheDocument()
    })

    it("does not show Remove Password button when no linked providers", () => {
      render(
        <PasswordSection
          hasPassword={true}
          oauthProvider={null}
          linkedProviders={[]}
        />
      )
      expect(
        screen.queryByRole("button", { name: /remove password/i })
      ).not.toBeInTheDocument()
    })

    it("shows error when passwords don't match on change", async () => {
      const user = userEvent.setup()
      global.fetch = vi.fn()
      render(
        <PasswordSection
          hasPassword={true}
          oauthProvider={null}
          linkedProviders={[]}
        />
      )

      await user.click(screen.getByRole("button", { name: /change password/i }))
      await user.type(screen.getByLabelText("Current password"), "OldPassword123!")
      await user.type(screen.getByLabelText("New password"), "NewPassword1234!")
      await user.type(screen.getByLabelText("Confirm new password"), "DifferentPass!")

      const form = screen.getByRole("button", { name: /update password/i }).closest("form")!
      fireEvent.submit(form)

      expect(screen.getByText("Passwords do not match.")).toBeInTheDocument()
      expect(global.fetch).not.toHaveBeenCalled()
    })

    it("calls change-password API on successful submit", async () => {
      const user = userEvent.setup()
      global.fetch = vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve({}) })
      render(
        <PasswordSection
          hasPassword={true}
          oauthProvider={null}
          linkedProviders={[]}
        />
      )

      await user.click(screen.getByRole("button", { name: /change password/i }))
      await user.type(screen.getByLabelText("Current password"), "OldPassword123!")
      await user.type(screen.getByLabelText("New password"), "NewPassword1234!")
      await user.type(screen.getByLabelText("Confirm new password"), "NewPassword1234!")
      await user.click(screen.getByRole("button", { name: /update password/i }))

      expect(global.fetch).toHaveBeenCalledWith("/api/v1/auth/change-password", expect.objectContaining({
        method: "POST",
      }))
    })

    it("opens confirmation modal and calls remove-password API", async () => {
      const user = userEvent.setup()
      global.fetch = vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve({}) })
      render(
        <PasswordSection
          hasPassword={true}
          oauthProvider="google"
          linkedProviders={["google"]}
        />
      )

      // Click Remove Password to open the modal
      await user.click(screen.getByRole("button", { name: /remove password/i }))

      // Modal should be visible
      const dialog = screen.getByRole("dialog")
      expect(dialog).toBeInTheDocument()

      // Fill in the password field in the modal
      const passwordInput = within(dialog).getByLabelText("Current password")
      await user.type(passwordInput, "MyCurrentPass1!")

      // Click the Remove confirm button inside the modal
      await user.click(within(dialog).getByRole("button", { name: /^Remove$/i }))

      expect(global.fetch).toHaveBeenCalledWith("/api/v1/auth/remove-password", expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ current_password: "MyCurrentPass1!" }),
      }))
    })
  })
})
