import { describe, it, expect, vi, beforeEach } from "vitest"

// Mock jose before importing — SignJWT is used as a constructor (new SignJWT(...))
vi.mock("jose", () => {
  class MockSignJWT {
    setProtectedHeader() { return this }
    setIssuedAt() { return this }
    setExpirationTime() { return this }
    async sign() { return "mock.jwt.token" }
  }
  return { SignJWT: MockSignJWT }
})

describe("signServiceToken", () => {
  beforeEach(() => {
    vi.stubEnv("SERVICE_AUTH_SECRET", "a".repeat(64))
  })

  it("returns a JWT string", async () => {
    const { signServiceToken } = await import("../service-token")
    const token = await signServiceToken("42", "test@test.com")
    expect(typeof token).toBe("string")
    expect(token).toBe("mock.jwt.token")
  })

  it("returns empty string when no secret configured", async () => {
    vi.stubEnv("SERVICE_AUTH_SECRET", "")
    // Re-import to get fresh module
    vi.resetModules()
    const { signServiceToken } = await import("../service-token")
    const token = await signServiceToken("42", "test@test.com")
    expect(token).toBe("")
  })
})
