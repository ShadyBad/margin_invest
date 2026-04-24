import { NextResponse } from "next/server"

const API_URL = process.env.API_URL || "http://localhost:8000"

export async function POST(request: Request) {
  try {
    const body = await request.json()
    const response = await fetch(`${API_URL}/api/v1/experiment/checkout`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    })

    if (!response.ok) {
      try {
        const errorBody = await response.json()
        return NextResponse.json(errorBody, { status: response.status })
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
    console.error("Failed to proxy experiment checkout:", error)
    return NextResponse.json(
      { error_code: "PROXY_ERROR", message: "Failed to create checkout session", status_code: 502 },
      { status: 502 },
    )
  }
}
