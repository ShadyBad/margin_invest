import { NextRequest, NextResponse } from "next/server"
import { auth } from "@/lib/auth"

const API_URL = process.env.API_URL || "http://localhost:8000"

export async function GET() {
  const session = await auth()
  if (!session) {
    return NextResponse.json(
      { error_code: "UNAUTHORIZED", message: "Authentication required", status_code: 401 },
      { status: 401 },
    )
  }

  try {
    const response = await fetch(`${API_URL}/api/v1/me/alerts`, {
      headers: {
        "Content-Type": "application/json",
        "X-User-Id": (session.userId as string) || "",
        "X-User-Email": session.user?.email || "",
      },
      cache: "no-store",
    })

    const data = await response.json()
    return NextResponse.json(data, { status: response.status })
  } catch (error) {
    console.error("Failed to proxy alerts request:", error)
    return NextResponse.json(
      { error_code: "PROXY_ERROR", message: "Failed to fetch alerts", status_code: 502 },
      { status: 502 },
    )
  }
}

export async function POST(request: NextRequest) {
  const session = await auth()
  if (!session) {
    return NextResponse.json(
      { error_code: "UNAUTHORIZED", message: "Authentication required", status_code: 401 },
      { status: 401 },
    )
  }

  try {
    const body = await request.json()
    const response = await fetch(`${API_URL}/api/v1/me/alerts`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-User-Id": (session.userId as string) || "",
        "X-User-Email": session.user?.email || "",
      },
      body: JSON.stringify(body),
    })

    const data = await response.json()
    return NextResponse.json(data, { status: response.status })
  } catch (error) {
    console.error("Failed to proxy alert create:", error)
    return NextResponse.json(
      { error_code: "PROXY_ERROR", message: "Failed to create alert", status_code: 502 },
      { status: 502 },
    )
  }
}
