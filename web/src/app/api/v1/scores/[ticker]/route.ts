import { NextResponse } from "next/server"
import { auth } from "@/lib/auth"

const API_URL = process.env.API_URL || "http://localhost:8000"

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ ticker: string }> },
) {
  const session = await auth()
  if (!session) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
  }

  const { ticker } = await params
  const { search } = new URL(_request.url)

  try {
    const response = await fetch(`${API_URL}/api/v1/scores/${ticker}${search}`, {
      headers: {
        "Content-Type": "application/json",
        "X-User-Id": (session.userId as string) || "",
        "X-User-Email": session.user?.email || "",
      },
      cache: "no-store",
    })

    if (!response.ok) {
      const text = await response.text().catch(() => "Upstream error")
      return NextResponse.json(
        { error: text },
        { status: response.status },
      )
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error(`Failed to proxy score for ${ticker}:`, error)
    return NextResponse.json(
      { error: "Failed to fetch score data" },
      { status: 502 },
    )
  }
}
