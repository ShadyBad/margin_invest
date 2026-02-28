import { describe, it, expect } from "vitest"
import robots from "../robots"

describe("robots", () => {
  it("returns robots configuration", () => {
    const config = robots()
    expect(config.rules).toBeDefined()
  })

  it("allows all user agents on public paths", () => {
    const config = robots()
    const rules = Array.isArray(config.rules) ? config.rules : [config.rules]
    const wildcardRule = rules.find((r) => r.userAgent === "*")
    expect(wildcardRule).toBeDefined()
    expect(wildcardRule!.allow).toContain("/")
  })

  it("disallows authenticated and internal routes", () => {
    const config = robots()
    const rules = Array.isArray(config.rules) ? config.rules : [config.rules]
    const wildcardRule = rules.find((r) => r.userAgent === "*")
    const disallowed = Array.isArray(wildcardRule!.disallow)
      ? wildcardRule!.disallow
      : [wildcardRule!.disallow]
    expect(disallowed).toContain("/dashboard")
    expect(disallowed).toContain("/account")
    expect(disallowed).toContain("/admin/")
    expect(disallowed).toContain("/api/v1/")
  })

  it("includes sitemap URL", () => {
    const config = robots()
    expect(config.sitemap).toContain("sitemap.xml")
  })
})
