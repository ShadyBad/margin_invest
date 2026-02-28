import type { MetadataRoute } from "next"

const BASE_URL = "https://margin-invest.com"

export default function sitemap(): MetadataRoute.Sitemap {
  return [
    {
      url: `${BASE_URL}/`,
      lastModified: new Date("2026-02-27"),
      changeFrequency: "weekly",
      priority: 1.0,
    },
    {
      url: `${BASE_URL}/methodology`,
      lastModified: new Date("2026-02-27"),
      changeFrequency: "monthly",
      priority: 0.8,
    },
    {
      url: `${BASE_URL}/legal`,
      lastModified: new Date("2026-02-27"),
      changeFrequency: "monthly",
      priority: 0.3,
    },
    {
      url: `${BASE_URL}/support`,
      lastModified: new Date("2026-02-27"),
      changeFrequency: "monthly",
      priority: 0.6,
    },
    {
      url: `${BASE_URL}/status`,
      lastModified: new Date("2026-02-27"),
      changeFrequency: "daily",
      priority: 0.4,
    },
    {
      url: `${BASE_URL}/guides`,
      lastModified: new Date("2026-02-27"),
      changeFrequency: "weekly",
      priority: 0.7,
    },
    {
      url: `${BASE_URL}/security`,
      lastModified: new Date("2026-02-27"),
      changeFrequency: "monthly",
      priority: 0.6,
    },
    {
      url: `${BASE_URL}/api-docs`,
      lastModified: new Date("2026-02-27"),
      changeFrequency: "monthly",
      priority: 0.7,
    },
    {
      url: `${BASE_URL}/contact`,
      lastModified: new Date("2026-02-27"),
      changeFrequency: "monthly",
      priority: 0.5,
    },
  ]
}
