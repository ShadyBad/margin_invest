import { NextResponse } from "next/server"
import { auth } from "@/lib/auth"

const API_URL = process.env.API_URL || "http://localhost:8000"

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ ticker: string }> },
) {
  const session = await auth()
  if (!session) {
    return NextResponse.json(
      { error_code: "UNAUTHORIZED", message: "Authentication required", status_code: 401 },
      { status: 401 },
    )
  }

  const { ticker } = await params

  try {
    const response = await fetch(`${API_URL}/api/v1/scores/${ticker}/valuation-audit`, {
      headers: {
        "Content-Type": "application/json",
        "X-User-Id": (session.userId as string) || "",
        "X-User-Email": session.user?.email || "",
      },
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
    console.error(`Failed to proxy valuation audit for ${ticker}:`, error)
    return NextResponse.json(
      { error_code: "PROXY_ERROR", message: "Failed to fetch valuation audit", status_code: 502 },
      { status: 502 },
    )
  }
}
