import { NextResponse } from "next/server"
import { auth } from "@/lib/auth"

const API_URL = process.env.API_URL || "http://localhost:8000"

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const session = await auth()
  if (!session) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
  }

  const { id } = await params

  try {
    const response = await fetch(`${API_URL}/api/v1/backtest/results/${id}`, {
      headers: {
        "Content-Type": "application/json",
        "X-User-Id": (session.userId as string) || "",
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
    console.error(`Failed to proxy backtest result ${id}:`, error)
    return NextResponse.json(
      { error: "Failed to fetch backtest result" },
      { status: 502 },
    )
  }
}
