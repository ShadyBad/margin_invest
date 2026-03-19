import { describe, it, expect, vi, beforeEach } from "vitest"
import { NextRequest, NextResponse } from "next/server"

// Mock NextAuth auth handler
vi.mock("@/lib/auth", () => ({
  auth: vi.fn(),
}))

import { auth } from "@/lib/auth"
import { proxy, config } from "../proxy"

const mockedAuth = vi.mocked(auth)

function createRequest(path: string, cookies: Record<string, string> = {}): NextRequest {
  const req = new NextRequest(new URL(`http://localhost:3000${path}`))
  for (const [name, value] of Object.entries(cookies)) {
    req.cookies.set(name, value)
  }
  return req
}

describe("proxy", () => {
  beforeEach(() => {
    mockedAuth.mockReset()
    mockedAuth.mockResolvedValue(NextResponse.next() as never)
  })

  // Admin route protection
  it("redirects unauthenticated requests from /admin/approvals to /admin/login", async () => {
    const req = createRequest("/admin/approvals")
    const res = await proxy(req)
    expect(res?.status).toBe(307)
    expect(res?.headers.get("location")).toContain("/admin/login")
  })

  it("redirects unauthenticated requests from /admin to /admin/login", async () => {
    const req = createRequest("/admin")
    const res = await proxy(req)
    expect(res?.status).toBe(307)
    expect(res?.headers.get("location")).toContain("/admin/login")
  })

  it("allows requests to /admin/login without a cookie", async () => {
    const req = createRequest("/admin/login")
    const res = await proxy(req)
    expect(res?.status).not.toBe(307)
  })

  it("allows admin requests with a valid admin_session cookie", async () => {
    const req = createRequest("/admin/approvals", { admin_session: "valid-token" })
    const res = await proxy(req)
    expect(res?.status).not.toBe(307)
  })

  // Non-admin routes delegate to NextAuth
  it("delegates /dashboard to the auth handler", async () => {
    const req = createRequest("/dashboard")
    await proxy(req)
    expect(mockedAuth).toHaveBeenCalledWith(req)
  })

  it("delegates /account to the auth handler", async () => {
    const req = createRequest("/account/settings")
    await proxy(req)
    expect(mockedAuth).toHaveBeenCalledWith(req)
  })

  it("delegates /backtesting to the auth handler", async () => {
    const req = createRequest("/backtesting")
    await proxy(req)
    expect(mockedAuth).toHaveBeenCalledWith(req)
  })

  // Config
  it("exports a matcher config that includes admin routes", () => {
    expect(config.matcher).toContain("/admin/:path*")
  })

  it("exports a matcher config that includes dashboard routes", () => {
    expect(config.matcher).toContain("/dashboard/:path*")
  })
})
