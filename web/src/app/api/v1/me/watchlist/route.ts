import { NextResponse } from "next/server"
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
    const response = await fetch(`${API_URL}/api/v1/me/watchlist`, {
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
    console.error("Failed to proxy watchlist request:", error)
    return NextResponse.json(
      { error_code: "PROXY_ERROR", message: "Failed to fetch watchlist", status_code: 502 },
      { status: 502 },
    )
  }
}
