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

  const formData = await request.formData()

  try {
    const response = await fetch(`${API_URL}/api/v1/users/me/avatar`, {
      method: "POST",
      headers: {
        "X-User-Id": (session.userId as string) || "",
        "X-User-Email": session.user?.email || "",
      },
      body: formData,
    })

    if (!response.ok) {
      try {
        const body = await response.json()
        return NextResponse.json(body, { status: response.status })
      } catch {
        return NextResponse.json(
          { error_code: "UPSTREAM_ERROR", message: "Upload failed", status_code: response.status },
          { status: response.status },
        )
      }
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error("Failed to proxy avatar upload:", error)
    return NextResponse.json(
      { error_code: "PROXY_ERROR", message: "Failed to upload avatar", status_code: 502 },
      { status: 502 },
    )
  }
}

export async function DELETE() {
  const session = await auth()
  if (!session) {
    return NextResponse.json(
      { error_code: "UNAUTHORIZED", message: "Authentication required", status_code: 401 },
      { status: 401 },
    )
  }

  try {
    const response = await fetch(`${API_URL}/api/v1/users/me/avatar`, {
      method: "DELETE",
      headers: {
        "X-User-Id": (session.userId as string) || "",
        "X-User-Email": session.user?.email || "",
      },
    })

    if (!response.ok) {
      try {
        const body = await response.json()
        return NextResponse.json(body, { status: response.status })
      } catch {
        return NextResponse.json(
          { error_code: "UPSTREAM_ERROR", message: "Delete failed", status_code: response.status },
          { status: response.status },
        )
      }
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error("Failed to proxy avatar delete:", error)
    return NextResponse.json(
      { error_code: "PROXY_ERROR", message: "Failed to delete avatar", status_code: 502 },
      { status: 502 },
    )
  }
}
