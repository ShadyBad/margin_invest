import { describe, it, expect, vi } from "vitest"

// Use vi.hoisted to ensure mock variables are available when vi.mock factory runs
const { mockAuth, mockHandlers, mockSignIn, mockSignOut, mockNextAuth } = vi.hoisted(() => {
  const mockAuth = vi.fn()
  const mockHandlers = { GET: vi.fn(), POST: vi.fn() }
  const mockSignIn = vi.fn()
  const mockSignOut = vi.fn()
  const mockNextAuth = vi.fn(() => ({
    handlers: mockHandlers,
    auth: mockAuth,
    signIn: mockSignIn,
    signOut: mockSignOut,
  }))
  return { mockAuth, mockHandlers, mockSignIn, mockSignOut, mockNextAuth }
})

vi.mock("next-auth", () => ({
  default: mockNextAuth,
}))

vi.mock("next-auth/providers/google", () => ({
  default: vi.fn(() => ({ id: "google", name: "Google" })),
}))

vi.mock("next-auth/providers/github", () => ({
  default: vi.fn(() => ({ id: "github", name: "GitHub" })),
}))

vi.mock("next-auth/providers/credentials", () => ({
  default: vi.fn((config: Record<string, unknown>) => ({
    id: "credentials",
    name: "Credentials",
    ...config,
  })),
}))

// Import after mocks are set up
import { handlers, auth, signIn, signOut } from "@/lib/auth"

describe("Auth configuration", () => {
  it("exports handlers, auth, signIn, and signOut", () => {
    expect(handlers).toBeDefined()
    expect(auth).toBeDefined()
    expect(signIn).toBeDefined()
    expect(signOut).toBeDefined()
  })

  it("exports handlers with GET and POST methods", () => {
    expect(handlers.GET).toBeDefined()
    expect(handlers.POST).toBeDefined()
  })

  it("configures exactly 3 providers", () => {
    expect(mockNextAuth).toHaveBeenCalled()

    const config = mockNextAuth.mock.calls[0]?.[0] as Record<string, unknown> | undefined
    expect(config).toBeDefined()
    expect(config!.providers).toHaveLength(3)
  })

  it("does not include Microsoft Entra ID provider", () => {
    const config = mockNextAuth.mock.calls[0]?.[0] as Record<string, unknown> | undefined
    const providers = config!.providers as Array<{ id: string }>
    const providerIds = providers.map((p) => p.id)
    expect(providerIds).not.toContain("microsoft-entra-id")
  })

  it("does not include Facebook provider", () => {
    const config = mockNextAuth.mock.calls[0]?.[0] as Record<string, unknown> | undefined
    const providers = config!.providers as Array<{ id: string }>
    const providerIds = providers.map((p) => p.id)
    expect(providerIds).not.toContain("facebook")
  })

  it("configures JWT session strategy", () => {
    const config = mockNextAuth.mock.calls[0]?.[0] as Record<string, unknown> | undefined
    expect(config!.session).toEqual({ strategy: "jwt" })
  })

  it("configures custom sign-in page at /login", () => {
    const config = mockNextAuth.mock.calls[0]?.[0] as Record<string, unknown> | undefined
    const pages = config!.pages as Record<string, string>
    expect(pages.signIn).toBe("/login")
  })

  it("configures custom error page at /auth/error", () => {
    const config = mockNextAuth.mock.calls[0]?.[0] as Record<string, unknown> | undefined
    const pages = config!.pages as Record<string, string>
    expect(pages.error).toBe("/auth/error")
  })

  it("configures signIn callback", () => {
    const config = mockNextAuth.mock.calls[0]?.[0] as Record<string, unknown> | undefined
    const callbacks = config!.callbacks as Record<string, unknown>
    expect(callbacks.signIn).toBeDefined()
    expect(typeof callbacks.signIn).toBe("function")
  })

  it("configures jwt callback", () => {
    const config = mockNextAuth.mock.calls[0]?.[0] as Record<string, unknown> | undefined
    const callbacks = config!.callbacks as Record<string, unknown>
    expect(callbacks.jwt).toBeDefined()
    expect(typeof callbacks.jwt).toBe("function")
  })

  it("configures session callback", () => {
    const config = mockNextAuth.mock.calls[0]?.[0] as Record<string, unknown> | undefined
    const callbacks = config!.callbacks as Record<string, unknown>
    expect(callbacks.session).toBeDefined()
    expect(typeof callbacks.session).toBe("function")
  })
})
