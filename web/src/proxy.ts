export { auth as proxy } from "@/lib/auth"

export const config = {
  matcher: ["/dashboard/:path*", "/account/:path*", "/settings/:path*", "/backtesting/:path*"],
}
