import { NextRequest, NextResponse } from "next/server"
import { auth } from "@/lib/auth"

const API_URL = process.env.API_URL || "http://localhost:8000"

type Params = { params: Promise<{ path: string[] }> }

export async function GET(request: NextRequest, { params }: Params) {
  const session = await auth()
  if (!session) {
    return NextResponse.json(
      { error_code: "UNAUTHORIZED", message: "Authentication required", status_code: 401 },
      { status: 401 },
    )
  }

  const { path } = await params
  const { search } = new URL(request.url)

  try {
    const response = await fetch(`${API_URL}/api/v1/13f/${path.join("/")}${search}`, {
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
    console.error("Failed to proxy 13f request:", error)
    return NextResponse.json(
      { error_code: "PROXY_ERROR", message: "Failed to fetch 13f data", status_code: 502 },
      { status: 502 },
    )
  }
}

export async function POST(request: NextRequest, { params }: Params) {
  const session = await auth()
  if (!session) {
    return NextResponse.json(
      { error_code: "UNAUTHORIZED", message: "Authentication required", status_code: 401 },
      { status: 401 },
    )
  }

  const { path } = await params

  try {
    const body = await request.json()

    const response = await fetch(`${API_URL}/api/v1/13f/${path.join("/")}`, {
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
        const responseBody = await response.json()
        return NextResponse.json(responseBody, { status: response.status })
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
    console.error("Failed to proxy 13f request:", error)
    return NextResponse.json(
      { error_code: "PROXY_ERROR", message: "Failed to post 13f data", status_code: 502 },
      { status: 502 },
    )
  }
}
