import { NextResponse } from "next/server"

const API_URL = process.env.API_URL || "http://localhost:8000"

export async function GET() {
  try {
    const response = await fetch(`${API_URL}/api/v1/universe/funnel`, {
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
    console.error("Failed to proxy universe funnel:", error)
    return NextResponse.json(
      { error_code: "PROXY_ERROR", message: "Failed to fetch funnel data", status_code: 502 },
      { status: 502 },
    )
  }
}
