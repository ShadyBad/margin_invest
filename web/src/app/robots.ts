import type { MetadataRoute } from "next"

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: "/",
      disallow: [
        "/dashboard",
        "/account",
        "/settings",
        "/admin/",
        "/api/v1/",
        "/login",
        "/register",
        "/reset-password",
        "/mfa/",
      ],
    },
    sitemap: "https://www.margin-invest.com/sitemap.xml",
  }
}
