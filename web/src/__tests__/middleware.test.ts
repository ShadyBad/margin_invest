import { describe, it, expect, vi } from "vitest"

describe("Security Headers", () => {
  it("should define all required security headers", async () => {
    const mod = await import("../middleware")
    expect(mod.middleware).toBeDefined()
    expect(mod.config).toBeDefined()
    expect(mod.config.matcher).toBeDefined()
  })

  it("matcher should exclude static files", async () => {
    const { config } = await import("../middleware")
    const matcher = config.matcher[0]
    expect(matcher).toContain("_next/static")
    expect(matcher).toContain("favicon.ico")
  })

  it("should set security headers on response", async () => {
    const { middleware } = await import("../middleware")

    // Create a minimal mock request
    const mockRequest = {
      nextUrl: { pathname: "/" },
      headers: new Headers(),
      url: "http://localhost:3000/",
    } as any

    const response = middleware(mockRequest)

    expect(response.headers.get("X-Frame-Options")).toBe("DENY")
    expect(response.headers.get("X-Content-Type-Options")).toBe("nosniff")
    expect(response.headers.get("X-DNS-Prefetch-Control")).toBe("off")
    expect(response.headers.get("Strict-Transport-Security")).toContain(
      "max-age=31536000"
    )
    expect(response.headers.get("Referrer-Policy")).toBe(
      "strict-origin-when-cross-origin"
    )
    expect(response.headers.get("Permissions-Policy")).toContain("camera=()")
    expect(
      response.headers.get("Content-Security-Policy-Report-Only")
    ).toContain("default-src 'self'")
  })
})
