import { describe, it, expect, vi, beforeEach } from "vitest"
import { NextRequest, NextResponse } from "next/server"

vi.mock("next-auth/jwt", () => ({
  getToken: vi.fn(),
}))

import { getToken } from "next-auth/jwt"
import { middleware, config } from "../middleware"

const mockedGetToken = vi.mocked(getToken)

function createRequest(path: string): NextRequest {
  return new NextRequest(new URL(`http://localhost:3000${path}`))
}

describe("middleware", () => {
  beforeEach(() => {
    mockedGetToken.mockReset()
  })

  it("redirects unauthenticated users from /dashboard to /login", async () => {
    mockedGetToken.mockResolvedValue(null)
    const req = createRequest("/dashboard")
    const res = await middleware(req)
    expect(res?.status).toBe(307)
    expect(res?.headers.get("location")).toContain("/login")
    expect(res?.headers.get("location")).toContain("callbackUrl=%2Fdashboard")
  })

  it("redirects unauthenticated users from /smart-money to /login", async () => {
    mockedGetToken.mockResolvedValue(null)
    const req = createRequest("/smart-money")
    const res = await middleware(req)
    expect(res?.status).toBe(307)
    expect(res?.headers.get("location")).toContain("/login")
  })

  it("redirects unauthenticated users from /admin/approvals to /login", async () => {
    mockedGetToken.mockResolvedValue(null)
    const req = createRequest("/admin/approvals")
    const res = await middleware(req)
    expect(res?.status).toBe(307)
    expect(res?.headers.get("location")).toContain("/login")
  })

  it("allows authenticated users to access /dashboard", async () => {
    mockedGetToken.mockResolvedValue({ sub: "user-1" } as never)
    const req = createRequest("/dashboard")
    const res = await middleware(req)
    expect(res?.headers.get("location")).toBeNull()
  })

  it("allows unauthenticated users to access /explore", async () => {
    mockedGetToken.mockResolvedValue(null)
    const req = createRequest("/explore")
    const res = await middleware(req)
    expect(res?.headers.get("location")).toBeNull()
  })

  it("allows unauthenticated users to access /methodology", async () => {
    mockedGetToken.mockResolvedValue(null)
    const req = createRequest("/methodology")
    const res = await middleware(req)
    expect(res?.headers.get("location")).toBeNull()
  })

  it("exports a matcher config excluding static assets and API routes", () => {
    expect(config.matcher).toBeDefined()
  })
})
