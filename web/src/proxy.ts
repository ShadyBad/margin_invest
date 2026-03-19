import { auth } from "@/lib/auth"
import { NextResponse } from "next/server"
import type { NextRequest } from "next/server"

export async function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl

  // Admin routes: check admin_session cookie
  if (pathname.startsWith("/admin")) {
    if (pathname === "/admin/login") {
      return NextResponse.next()
    }
    const adminSession = request.cookies.get("admin_session")?.value
    if (!adminSession) {
      return NextResponse.redirect(new URL("/admin/login", request.url))
    }
    return NextResponse.next()
  }

  // All other matched routes: delegate to NextAuth
  // auth() overload for middleware use isn't exported with a clean type signature
  return (auth as (req: NextRequest) => Promise<NextResponse>)(request)
}

export const config = {
  matcher: [
    "/dashboard/:path*",
    "/account/:path*",
    "/settings/:path*",
    "/backtesting/:path*",
    "/admin/:path*",
  ],
}
