import { NextResponse } from "next/server"
import { auth } from "@/lib/auth"
import { signServiceToken } from "@/lib/api/service-token"

const API_URL = process.env.API_URL || "http://localhost:8000"

export async function GET() {
  const session = await auth()
  if (!session?.userId) {
    return NextResponse.json(
      { error_code: "UNAUTHORIZED", message: "Authentication required", status_code: 401 },
      { status: 401 },
    )
  }

  try {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    }

    const token = await signServiceToken(
      session.userId as string,
      session.user?.email,
    )
    if (token) {
      headers["Authorization"] = `Bearer ${token}`
    } else {
      headers["X-User-Id"] = session.userId as string
      headers["X-User-Email"] = session.user?.email || ""
    }

    const response = await fetch(`${API_URL}/api/v1/billing/status`, {
      headers,
      cache: "no-store",
    })

    if (!response.ok) {
      try {
        const body = await response.json()
        return NextResponse.json(body, { status: response.status })
      } catch {
        return NextResponse.json(
          { error_code: "UPSTREAM_ERROR", message: "Upstream error", status_code: response.status },
          { status: response.status },
        )
      }
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error("Failed to proxy billing status:", error)
    return NextResponse.json(
      { error_code: "PROXY_ERROR", message: "Failed to fetch billing status", status_code: 502 },
      { status: 502 },
    )
  }
}
