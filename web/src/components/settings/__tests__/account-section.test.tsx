import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen } from "@testing-library/react"

describe("AccountSection", () => {
  beforeEach(() => {
    vi.resetModules()
  })

  describe("credentials user (authMethod='credentials')", () => {
    it("should show Multi-Factor Authentication section", async () => {
      vi.doMock("next-auth/react", () => ({
        useSession: () => ({
          data: {
            user: {
              name: "Cred User",
              email: "cred@example.com",
              image: null,
            },
            authMethod: "credentials",
            mfaVerified: true,
          },
          status: "authenticated",
        }),
      }))

      const { AccountSection } = await import("../account-section")
      render(<AccountSection />)
      expect(screen.getByText("Multi-Factor Authentication")).toBeInTheDocument()
    })
  })

  describe("OAuth user (authMethod='oauth')", () => {
    it("should NOT show Multi-Factor Authentication section", async () => {
      vi.doMock("next-auth/react", () => ({
        useSession: () => ({
          data: {
            user: {
              name: "OAuth User",
              email: "oauth@example.com",
              image: "https://example.com/avatar.jpg",
            },
            authMethod: "oauth",
            mfaVerified: false,
          },
          status: "authenticated",
        }),
      }))

      const { AccountSection } = await import("../account-section")
      render(<AccountSection />)
      expect(screen.queryByText("Multi-Factor Authentication")).not.toBeInTheDocument()
    })
  })
})
