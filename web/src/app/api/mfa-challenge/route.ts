import { NextRequest, NextResponse } from "next/server"

export async function GET(request: NextRequest) {
  const cookie = request.cookies.get("__mfa_challenge")
  if (!cookie) {
    return NextResponse.json({ error: "No MFA challenge" }, { status: 401 })
  }

  try {
    const data = JSON.parse(cookie.value)
    return NextResponse.json({
      userId: data.userId,
      challengeToken: data.challengeToken,
    })
  } catch {
    return NextResponse.json({ error: "Invalid MFA challenge" }, { status: 401 })
  }
}
