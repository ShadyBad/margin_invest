import { describe, it, expect } from "vitest"
import { existsSync } from "fs"
import { join } from "path"

/**
 * Regression test: every link in both footers must resolve to an existing page.
 * If this test fails, you added a footer link without creating the page.
 */

// Landing footer links (keep in sync with footer-section.tsx)
const landingFooterLinks = [
  "/support",
  "/methodology",
  "/security",
  "/legal",
  "/terms",
  "/privacy",
  "/status",
  "/api-docs",
  "/contact",
]

// Authenticated footer links (keep in sync with layout/footer.tsx)
const authFooterLinks = [
  "/support",
  "/methodology",
  "/legal",
  "/terms",
  "/privacy",
  "/security",
  "/api-docs",
  "/contact",
]

const APP_DIR = join(__dirname, "..")

function routeExists(route: string): boolean {
  const segment = route.replace(/^\//, "")
  const pagePath = join(APP_DIR, segment, "page.tsx")
  return existsSync(pagePath)
}

describe("Link integrity", () => {
  it("every landing footer link resolves to a page", () => {
    for (const href of landingFooterLinks) {
      expect(routeExists(href), `Missing page for landing footer link: ${href}`).toBe(true)
    }
  })

  it("every authenticated footer link resolves to a page", () => {
    for (const href of authFooterLinks) {
      expect(routeExists(href), `Missing page for auth footer link: ${href}`).toBe(true)
    }
  })
})
