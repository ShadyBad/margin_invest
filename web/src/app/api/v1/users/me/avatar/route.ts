import { NextResponse } from "next/server"
import { auth } from "@/lib/auth"

const API_URL = process.env.API_URL || "http://localhost:8000"

export async function POST(request: Request) {
  const session = await auth()
  if (!session) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
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
      const data = await response.json().catch(() => ({ detail: "Upload failed" }))
      return NextResponse.json(data, { status: response.status })
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error("Failed to proxy avatar upload:", error)
    return NextResponse.json(
      { error: "Failed to upload avatar" },
      { status: 502 },
    )
  }
}

export async function DELETE() {
  const session = await auth()
  if (!session) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
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
      const data = await response.json().catch(() => ({ detail: "Delete failed" }))
      return NextResponse.json(data, { status: response.status })
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error("Failed to proxy avatar delete:", error)
    return NextResponse.json(
      { error: "Failed to delete avatar" },
      { status: 502 },
    )
  }
}
