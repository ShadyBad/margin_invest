import { NextResponse } from "next/server"
import { auth } from "@/lib/auth"

const API_URL = process.env.API_URL || "http://localhost:8000"

export async function POST(request: Request) {
  const session = await auth()
  if (!session) {
    return NextResponse.json(
      { error_code: "UNAUTHORIZED", message: "Authentication required", status_code: 401 },
      { status: 401 },
    )
  }

  try {
    const body = await request.json()
    const response = await fetch(`${API_URL}/api/v1/auth/change-password`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-User-Id": (session.userId as string) || "",
        "X-User-Email": session.user?.email || "",
      },
      body: JSON.stringify(body),
    })

    if (!response.ok) {
      try {
        const body = await response.json()
        return NextResponse.json(body, { status: response.status })
      } catch {
        return NextResponse.json(
          { error_code: "UPSTREAM_ERROR", message: "Password change failed", status_code: response.status },
          { status: response.status },
        )
      }
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error("Failed to proxy password change:", error)
    return NextResponse.json(
      { error_code: "PROXY_ERROR", message: "Failed to change password", status_code: 502 },
      { status: 502 },
    )
  }
}
