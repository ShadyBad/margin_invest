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

vi.mock("next-auth/providers/microsoft-entra-id", () => ({
  default: vi.fn(() => ({ id: "microsoft-entra-id", name: "Microsoft Entra ID" })),
}))

vi.mock("next-auth/providers/facebook", () => ({
  default: vi.fn(() => ({ id: "facebook", name: "Facebook" })),
}))

vi.mock("next-auth/providers/github", () => ({
  default: vi.fn(() => ({ id: "github", name: "GitHub" })),
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

  it("calls NextAuth with provider configuration", () => {
    expect(mockNextAuth).toHaveBeenCalled()

    const config = mockNextAuth.mock.calls[0]?.[0] as Record<string, unknown> | undefined
    expect(config).toBeDefined()
    expect(config!.providers).toHaveLength(4)
  })

  it("configures JWT session strategy", () => {
    const config = mockNextAuth.mock.calls[0]?.[0] as Record<string, unknown> | undefined
    expect(config!.session).toEqual({ strategy: "jwt" })
  })

  it("configures custom sign-in page", () => {
    const config = mockNextAuth.mock.calls[0]?.[0] as Record<string, unknown> | undefined
    expect(config!.pages).toEqual({ signIn: "/login" })
  })
})
