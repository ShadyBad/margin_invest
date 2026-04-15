import { describe, it, expect } from "vitest"
import sitemap from "../sitemap"

describe("sitemap", () => {
  it("returns an array of sitemap entries", () => {
    const entries = sitemap()
    expect(Array.isArray(entries)).toBe(true)
    expect(entries.length).toBeGreaterThan(0)
  })

  it("includes all public pages", () => {
    const entries = sitemap()
    const urls = entries.map((e) => e.url)
    expect(urls).toContain("https://www.margin-invest.com/")
    expect(urls).toContain("https://www.margin-invest.com/methodology")
    expect(urls).toContain("https://www.margin-invest.com/legal")
    expect(urls).toContain("https://www.margin-invest.com/support")
    expect(urls).toContain("https://www.margin-invest.com/status")
    expect(urls).toContain("https://www.margin-invest.com/guides")
    expect(urls).toContain("https://www.margin-invest.com/security")
    expect(urls).toContain("https://www.margin-invest.com/api-docs")
    expect(urls).toContain("https://www.margin-invest.com/contact")
  })

  it("excludes authenticated routes", () => {
    const entries = sitemap()
    const urls = entries.map((e) => e.url)
    expect(urls).not.toContain("https://www.margin-invest.com/dashboard")
    expect(urls).not.toContain("https://www.margin-invest.com/account")
    expect(urls).not.toContain("https://www.margin-invest.com/settings")
  })

  it("each entry has lastModified and changeFrequency", () => {
    const entries = sitemap()
    for (const entry of entries) {
      expect(entry.lastModified).toBeDefined()
      expect(entry.changeFrequency).toBeDefined()
    }
  })
})
