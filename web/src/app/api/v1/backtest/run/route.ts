import { NextResponse } from "next/server"
import { auth } from "@/lib/auth"

const API_URL = process.env.API_URL || "http://localhost:8000"

export async function POST(request: Request) {
  const session = await auth()
  if (!session) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
  }

  const body = await request.text().catch(() => "{}")

  try {
    const response = await fetch(`${API_URL}/api/v1/backtest/run`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-User-Id": (session.userId as string) || "",
        "X-User-Email": session.user?.email || "",
      },
      body: body || "{}",
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
    console.error("Failed to proxy backtest run:", error)
    return NextResponse.json(
      { error: "Failed to run backtest" },
      { status: 502 },
    )
  }
}
