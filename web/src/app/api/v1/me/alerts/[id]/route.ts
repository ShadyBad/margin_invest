import { NextResponse } from "next/server"
import { auth } from "@/lib/auth"

const API_URL = process.env.API_URL || "http://localhost:8000"

type Params = { params: Promise<{ id: string }> }

export async function DELETE(_request: Request, { params }: Params) {
  const session = await auth()
  if (!session) {
    return NextResponse.json(
      { error_code: "UNAUTHORIZED", message: "Authentication required", status_code: 401 },
      { status: 401 },
    )
  }

  const { id } = await params

  try {
    const response = await fetch(`${API_URL}/api/v1/me/alerts/${id}`, {
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
    console.error("Failed to proxy alert delete:", error)
    return NextResponse.json(
      { error_code: "PROXY_ERROR", message: "Failed to delete alert", status_code: 502 },
      { status: 502 },
    )
  }
}
