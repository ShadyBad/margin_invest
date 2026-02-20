import { NextResponse } from "next/server";

export function middleware() {
  if (process.env.MAINTENANCE_MODE === "true") {
    return new NextResponse("Coming Soon", {
      status: 503,
      headers: { "Retry-After": "3600" },
    });
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
