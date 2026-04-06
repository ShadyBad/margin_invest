import { NextResponse } from "next/server"
import { auth } from "@/lib/auth"

const API_URL = process.env.API_URL || "http://localhost:8000"

type Params = { params: Promise<{ ticker: string }> }

export async function POST(_request: Request, { params }: Params) {
  const session = await auth()
  if (!session) {
    return NextResponse.json(
      { error_code: "UNAUTHORIZED", message: "Authentication required", status_code: 401 },
      { status: 401 },
    )
  }

  const { ticker } = await params

  try {
    const response = await fetch(`${API_URL}/api/v1/me/watchlist/${ticker}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-User-Id": (session.userId as string) || "",
        "X-User-Email": session.user?.email || "",
      },
    })

    const data = await response.json()
    return NextResponse.json(data, { status: response.status })
  } catch (error) {
    console.error("Failed to proxy watchlist add:", error)
    return NextResponse.json(
      { error_code: "PROXY_ERROR", message: "Failed to add to watchlist", status_code: 502 },
      { status: 502 },
    )
  }
}

export async function DELETE(_request: Request, { params }: Params) {
  const session = await auth()
  if (!session) {
    return NextResponse.json(
      { error_code: "UNAUTHORIZED", message: "Authentication required", status_code: 401 },
      { status: 401 },
    )
  }

  const { ticker } = await params

  try {
    const response = await fetch(`${API_URL}/api/v1/me/watchlist/${ticker}`, {
      method: "DELETE",
      headers: {
        "X-User-Id": (session.userId as string) || "",
        "X-User-Email": session.user?.email || "",
      },
    })

    if (response.status === 204) {
      return new NextResponse(null, { status: 204 })
    }

    const data = await response.json()
    return NextResponse.json(data, { status: response.status })
  } catch (error) {
    console.error("Failed to proxy watchlist remove:", error)
    return NextResponse.json(
      { error_code: "PROXY_ERROR", message: "Failed to remove from watchlist", status_code: 502 },
      { status: 502 },
    )
  }
}
