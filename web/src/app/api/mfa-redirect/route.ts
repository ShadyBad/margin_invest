import { NextRequest, NextResponse } from "next/server"

export async function GET(request: NextRequest) {
  const userId = request.nextUrl.searchParams.get("userId")
  const challengeToken = request.nextUrl.searchParams.get("challengeToken")
  const setup = request.nextUrl.searchParams.get("setup") === "true"

  if (!userId || !challengeToken) {
    return NextResponse.redirect(new URL("/login", request.url))
  }

  const destination = setup ? "/mfa/setup" : "/mfa/verify"
  const response = NextResponse.redirect(new URL(destination, request.url))

  // Set challenge data in httpOnly cookie -- never exposed to client JS
  response.cookies.set("__mfa_challenge", JSON.stringify({ userId, challengeToken }), {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    maxAge: 300, // 5 minutes, matches challenge token TTL
    path: "/",
  })

  return response
}
