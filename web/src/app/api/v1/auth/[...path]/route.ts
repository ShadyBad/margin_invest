import { NextResponse } from "next/server"

const API_URL = process.env.API_URL || "http://localhost:8000"

/**
 * Catch-all proxy for auth endpoints that don't have their own route handler.
 * Covers: register, verify-credentials, mfa/*, session-check/*, oauth-sync.
 *
 * These are pre-authentication endpoints called by client pages (register,
 * login, MFA setup/verify) — they don't require a session check.
 *
 * The /api/v1/auth/change-password route has its own handler with auth checks.
 */
async function proxy(request: Request, path: string) {
  try {
    const response = await fetch(`${API_URL}/api/v1/auth/${path}`, {
      method: request.method,
      headers: {
        "Content-Type": "application/json",
      },
      body: request.method !== "GET" ? await request.text() : undefined,
    })

    const contentType = response.headers.get("content-type") || ""
    if (contentType.includes("application/json")) {
      const data = await response.json()
      return NextResponse.json(data, { status: response.status })
    }

    return new NextResponse(await response.text(), {
      status: response.status,
      headers: { "Content-Type": contentType },
    })
  } catch (error) {
    console.error(`Failed to proxy auth/${path}:`, error)
    return NextResponse.json(
      { detail: "Failed to reach authentication service" },
      { status: 502 },
    )
  }
}

export async function GET(
  request: Request,
  { params }: { params: Promise<{ path: string[] }> },
) {
  const { path } = await params
  return proxy(request, path.join("/"))
}

export async function POST(
  request: Request,
  { params }: { params: Promise<{ path: string[] }> },
) {
  const { path } = await params
  return proxy(request, path.join("/"))
}
