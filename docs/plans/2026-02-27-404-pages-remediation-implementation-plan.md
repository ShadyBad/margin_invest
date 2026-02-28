# 404 Pages Remediation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create Security, API Docs, and Contact pages to resolve 404 errors from landing page footer links, plus add sitemap.ts, robots.ts, and link integrity tests.

**Architecture:** Three static Next.js `page.tsx` files following the existing pattern (Navbar + inline sections + back link). Contact page has one client component for the form. Footer links updated in both landing and authenticated footers.

**Tech Stack:** Next.js 15 (App Router), React 19, Tailwind v4, Vitest + @testing-library/react

---

### Task 1: Security Page

**Files:**
- Create: `web/src/app/security/page.tsx`
- Test: `web/src/app/security/__tests__/page.test.tsx`

**Step 1: Write the failing test**

Create `web/src/app/security/__tests__/page.test.tsx`:

```tsx
import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import SecurityPage from "../page"

describe("Security Page", () => {
  it("renders the page heading", () => {
    render(<SecurityPage />)
    expect(screen.getByRole("heading", { level: 1, name: /how we protect your data/i })).toBeInTheDocument()
  })

  it("renders all seven sections", () => {
    render(<SecurityPage />)
    expect(screen.getByText(/infrastructure & encryption/i)).toBeInTheDocument()
    expect(screen.getByText(/authentication & access control/i)).toBeInTheDocument()
    expect(screen.getByText(/data protection/i)).toBeInTheDocument()
    expect(screen.getByText(/pipeline integrity/i)).toBeInTheDocument()
    expect(screen.getByText(/compliance posture/i)).toBeInTheDocument()
    expect(screen.getByText(/vulnerability disclosure/i)).toBeInTheDocument()
  })

  it("renders the security contact email", () => {
    render(<SecurityPage />)
    const mailtoLink = screen.getByRole("link", { name: "security@margin-invest.com" })
    expect(mailtoLink).toHaveAttribute("href", "mailto:security@margin-invest.com")
  })

  it("renders the back to home link", () => {
    render(<SecurityPage />)
    const backLink = screen.getByRole("link", { name: /back to home/i })
    expect(backLink).toHaveAttribute("href", "/")
  })

  it("renders key security details", () => {
    render(<SecurityPage />)
    expect(screen.getByText(/tls everywhere/i)).toBeInTheDocument()
    expect(screen.getByText(/jwt-based session authentication/i)).toBeInTheDocument()
    expect(screen.getByText(/totp multi-factor authentication/i)).toBeInTheDocument()
    expect(screen.getByText(/48-hour acknowledgment/i)).toBeInTheDocument()
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd web && npx vitest run src/app/security/__tests__/page.test.tsx`
Expected: FAIL — module not found

**Step 3: Write the Security page**

Create `web/src/app/security/page.tsx`:

```tsx
import type { Metadata } from "next"
import Link from "next/link"
import { Navbar } from "@/components/nav/navbar"

export const metadata: Metadata = {
  title: "Security | Margin Invest",
  description:
    "How Margin Invest protects your data — infrastructure, encryption, authentication, pipeline integrity, and vulnerability disclosure.",
  alternates: { canonical: "https://margin-invest.com/security" },
}

export default function SecurityPage() {
  return (
    <main className="relative bg-bg-primary min-h-screen">
      <div className="relative z-10">
        <Navbar />

        <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-16 sm:py-24">
          <h1 className="heading-2 text-text-primary mb-4">How We Protect Your Data</h1>
          <p className="body-text text-text-secondary mb-12">
            Margin Invest is built with security as a first-class constraint, not an afterthought.
          </p>

          <div className="space-y-12 text-text-secondary body-text">
            <section>
              <h2 className="heading-3 text-text-primary mb-4">Infrastructure &amp; Encryption</h2>
              <ul className="list-disc list-inside space-y-2 text-text-tertiary">
                <li>TLS everywhere — HTTPS enforced with HSTS headers</li>
                <li>Data encrypted at rest on PostgreSQL encrypted volumes</li>
                <li>Container-based hosting with isolated deployments</li>
                <li>All inter-service communication over encrypted channels</li>
                <li>
                  Security headers: <code className="font-mono text-[13px]">X-Frame-Options: DENY</code>,{" "}
                  <code className="font-mono text-[13px]">X-Content-Type-Options: nosniff</code>,{" "}
                  Strict-Transport-Security, Content-Security-Policy
                </li>
              </ul>
            </section>

            <section>
              <h2 className="heading-3 text-text-primary mb-4">Authentication &amp; Access Control</h2>
              <ul className="list-disc list-inside space-y-2 text-text-tertiary">
                <li>JWT-based session authentication with HMAC signing</li>
                <li>TOTP multi-factor authentication (MFA) via standard authenticator apps</li>
                <li>httpOnly secure cookies for session tokens</li>
                <li>Password hashing with industry-standard algorithms</li>
                <li>Rate limiting on authentication endpoints</li>
                <li>API key authentication for programmatic access</li>
              </ul>
            </section>

            <section>
              <h2 className="heading-3 text-text-primary mb-4">Data Protection</h2>
              <ul className="list-disc list-inside space-y-2 text-text-tertiary">
                <li>No sale of personal data to third parties</li>
                <li>Minimal data collection — authentication and platform functionality only</li>
                <li>Data deletion available on request</li>
                <li>Aggregated, anonymized data for analytics only</li>
                <li>Integrity checksums on all serialized ML model artifacts</li>
              </ul>
            </section>

            <section>
              <h2 className="heading-3 text-text-primary mb-4">Pipeline Integrity</h2>
              <ul className="list-disc list-inside space-y-2 text-text-tertiary">
                <li>Deterministic scoring — same inputs always produce same outputs</li>
                <li>
                  Human oversight pipeline: all scores pass through staged → approved → published
                  workflow before reaching users
                </li>
                <li>
                  Circuit breakers halt the pipeline automatically on score drift {">"}30%,
                  ingestion failure {">"}20%, or ML regression {">"}50%
                </li>
                <li>Full governance audit log with event history</li>
              </ul>
            </section>

            <section>
              <h2 className="heading-3 text-text-primary mb-4">Compliance Posture</h2>
              <p className="mb-4">
                We follow industry best practices aligned with SOC 2 principles. Formal
                certification is on our roadmap.
              </p>
              <ul className="list-disc list-inside space-y-2 text-text-tertiary">
                <li>GDPR-aligned data handling — deletion requests honored, minimal collection</li>
                <li>Regular internal security reviews</li>
                <li>Dependency vulnerability scanning</li>
              </ul>
            </section>

            <section>
              <h2 className="heading-3 text-text-primary mb-4">Vulnerability Disclosure</h2>
              <p className="mb-4">
                If you discover a security vulnerability, please report it responsibly. We take
                all reports seriously.
              </p>
              <ul className="list-disc list-inside space-y-2 text-text-tertiary">
                <li>
                  Email:{" "}
                  <a
                    href="mailto:security@margin-invest.com"
                    className="text-accent hover:text-accent-hover transition-colors underline underline-offset-2"
                  >
                    security@margin-invest.com
                  </a>
                </li>
                <li>48-hour acknowledgment SLA</li>
                <li>
                  Please include reproduction steps, affected components, and potential impact
                </li>
              </ul>
              <p className="mt-4 text-text-tertiary">
                For general security questions, visit our{" "}
                <Link
                  href="/support"
                  className="text-accent hover:text-accent-hover transition-colors underline underline-offset-2"
                >
                  support page
                </Link>
                .
              </p>
            </section>
          </div>

          <div className="mt-16 pt-8 border-t border-border-subtle">
            <Link
              href="/"
              className="text-sm text-text-tertiary hover:text-text-secondary transition-colors"
            >
              &larr; Back to home
            </Link>
          </div>
        </div>
      </div>
    </main>
  )
}
```

**Step 4: Run test to verify it passes**

Run: `cd web && npx vitest run src/app/security/__tests__/page.test.tsx`
Expected: PASS (5 tests)

**Step 5: Commit**

```bash
git add web/src/app/security/
git commit -m "feat(web): add security page with full security posture disclosure"
```

---

### Task 2: API Docs Page

**Files:**
- Create: `web/src/app/api-docs/page.tsx`
- Test: `web/src/app/api-docs/__tests__/page.test.tsx`

**Step 1: Write the failing test**

Create `web/src/app/api-docs/__tests__/page.test.tsx`:

```tsx
import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import ApiDocsPage from "../page"

describe("API Docs Page", () => {
  it("renders the page heading", () => {
    render(<ApiDocsPage />)
    expect(screen.getByRole("heading", { level: 1, name: /api reference/i })).toBeInTheDocument()
  })

  it("renders all six sections", () => {
    render(<ApiDocsPage />)
    expect(screen.getByText(/authentication/i)).toBeInTheDocument()
    expect(screen.getByText(/rate limits/i)).toBeInTheDocument()
    expect(screen.getByText(/scores/i)).toBeInTheDocument()
    expect(screen.getByText(/response format/i)).toBeInTheDocument()
    expect(screen.getByText(/sdks & support/i)).toBeInTheDocument()
  })

  it("renders endpoint paths", () => {
    render(<ApiDocsPage />)
    expect(screen.getByText(/\/api\/v1\/scores\/\{ticker\}/)).toBeInTheDocument()
    expect(screen.getByText(/\/api\/v1\/backtest\/default/)).toBeInTheDocument()
    expect(screen.getByText(/\/api\/v1\/13f\/holdings\/\{ticker\}/)).toBeInTheDocument()
  })

  it("renders the authentication example", () => {
    render(<ApiDocsPage />)
    expect(screen.getByText(/X-API-Key/)).toBeInTheDocument()
  })

  it("renders HTTP status codes", () => {
    render(<ApiDocsPage />)
    expect(screen.getByText(/401/)).toBeInTheDocument()
    expect(screen.getByText(/403/)).toBeInTheDocument()
    expect(screen.getByText(/429/)).toBeInTheDocument()
  })

  it("renders the request API key link", () => {
    render(<ApiDocsPage />)
    const link = screen.getByRole("link", { name: /request.*api key/i })
    expect(link).toHaveAttribute("href", "/account")
  })

  it("renders the back to home link", () => {
    render(<ApiDocsPage />)
    const backLink = screen.getByRole("link", { name: /back to home/i })
    expect(backLink).toHaveAttribute("href", "/")
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd web && npx vitest run src/app/api-docs/__tests__/page.test.tsx`
Expected: FAIL — module not found

**Step 3: Write the API Docs page**

Create `web/src/app/api-docs/page.tsx`:

```tsx
import type { Metadata } from "next"
import Link from "next/link"
import { Navbar } from "@/components/nav/navbar"

export const metadata: Metadata = {
  title: "API Reference | Margin Invest",
  description:
    "Margin Invest REST API documentation — authentication, endpoints, rate limits, and example requests for scores, backtesting, and institutional data.",
  alternates: { canonical: "https://margin-invest.com/api-docs" },
}

const endpoints = [
  {
    group: "Scores",
    items: [
      { method: "GET", path: "/api/v1/scores/{ticker}", description: "Conviction score, factor breakdown, composite percentile" },
      { method: "GET", path: "/api/v1/scores/{ticker}/history", description: "Historical score snapshots over time" },
      { method: "GET", path: "/api/v1/scores/{ticker}/valuation-audit", description: "Intrinsic value calculation audit trail" },
      { method: "GET", path: "/api/v1/scores", description: "List all scored assets with current scores" },
    ],
  },
  {
    group: "Backtesting",
    items: [
      { method: "GET", path: "/api/v1/backtest/default", description: "Default backtest with current scoring parameters" },
      { method: "POST", path: "/api/v1/backtest/replay", description: "Run custom backtest replay with parameter overrides" },
      { method: "GET", path: "/api/v1/backtest/shadow-portfolio", description: "Shadow portfolio tracking real-time picks" },
      { method: "GET", path: "/api/v1/backtest/teaser/{ticker}", description: "Single-asset backtest teaser" },
      { method: "GET", path: "/api/v1/backtest/portfolio-teaser", description: "Portfolio equity curve teaser (public)" },
    ],
  },
  {
    group: "Institutional (13F)",
    items: [
      { method: "GET", path: "/api/v1/13f/holdings/{ticker}", description: "Institutional holders for a ticker from SEC 13F filings" },
      { method: "GET", path: "/api/v1/13f/holdings/{ticker}/history", description: "Historical institutional holding changes" },
      { method: "GET", path: "/api/v1/13f/managers", description: "List tracked institutional managers" },
      { method: "GET", path: "/api/v1/13f/managers/{manager_id}/portfolio", description: "Full portfolio for a specific manager" },
    ],
  },
  {
    group: "Universe & Transparency",
    items: [
      { method: "GET", path: "/api/v1/universe/funnel", description: "Selectivity funnel — how many assets pass each filter stage" },
      { method: "GET", path: "/api/v1/correlations/showcase", description: "Factor correlation matrix for scored universe" },
      { method: "GET", path: "/api/v1/governance/transparency", description: "Oversight classification and pipeline health" },
    ],
  },
]

const errorCodes = [
  { code: "401", meaning: "Missing or invalid API key" },
  { code: "403", meaning: "Insufficient subscription plan for this endpoint" },
  { code: "404", meaning: "Ticker not found or no score available" },
  { code: "429", meaning: "Rate limit exceeded — retry after the duration in Retry-After header" },
  { code: "500", meaning: "Internal server error — contact support if persistent" },
]

export default function ApiDocsPage() {
  return (
    <main className="relative bg-bg-primary min-h-screen">
      <div className="relative z-10">
        <Navbar />

        <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-16 sm:py-24">
          <h1 className="heading-2 text-text-primary mb-4">API Reference</h1>
          <p className="body-text text-text-secondary mb-4">
            Programmatic access to Margin Invest&apos;s scoring engine, backtesting, and
            institutional data.
          </p>
          <p className="mb-12">
            <Link
              href="/account"
              className="text-sm text-accent hover:text-accent-hover transition-colors underline underline-offset-2"
            >
              Request an API key
            </Link>
          </p>

          <div className="space-y-12 text-text-secondary body-text">
            <section>
              <h2 className="heading-3 text-text-primary mb-4">Authentication</h2>
              <p className="mb-4">
                All API requests require an API key passed in the{" "}
                <code className="font-mono text-[13px] bg-bg-elevated px-1.5 py-0.5 rounded">X-API-Key</code>{" "}
                header. Generate and manage keys in your Account Settings.
              </p>
              <div className="terminal-card p-4 rounded-lg overflow-x-auto">
                <pre className="font-mono text-[13px] text-text-primary">
{`curl -H "X-API-Key: your_api_key" \\
  https://api.margin-invest.com/api/v1/scores/AAPL`}
                </pre>
              </div>
            </section>

            <section>
              <h2 className="heading-3 text-text-primary mb-4">Rate Limits</h2>
              <p className="mb-4">
                API requests are rate-limited per key. When you exceed the limit, responses
                return status 429 with a <code className="font-mono text-[13px] bg-bg-elevated px-1.5 py-0.5 rounded">Retry-After</code>{" "}
                header indicating when to retry.
              </p>
              <ul className="list-disc list-inside space-y-2 text-text-tertiary">
                <li>
                  Rate limit headers:{" "}
                  <code className="font-mono text-[13px]">X-RateLimit-Limit</code>,{" "}
                  <code className="font-mono text-[13px]">X-RateLimit-Remaining</code>,{" "}
                  <code className="font-mono text-[13px]">X-RateLimit-Reset</code>
                </li>
                <li>Limits vary by subscription plan</li>
                <li>Implement exponential backoff for 429 responses</li>
              </ul>
            </section>

            <section>
              <h2 className="heading-3 text-text-primary mb-4">Endpoints</h2>
              <div className="space-y-8">
                {endpoints.map((group) => (
                  <div key={group.group}>
                    <h3 className="text-[15px] font-semibold text-text-primary mb-3">
                      {group.group}
                    </h3>
                    <div className="border border-border-primary rounded-lg divide-y divide-border-subtle overflow-hidden">
                      {group.items.map((ep) => (
                        <div key={ep.path} className="px-4 py-3 flex flex-col sm:flex-row sm:items-start gap-1 sm:gap-3">
                          <span className="font-mono text-[12px] text-accent font-semibold shrink-0 w-12">
                            {ep.method}
                          </span>
                          <code className="font-mono text-[13px] text-text-primary break-all">
                            {ep.path}
                          </code>
                          <span className="text-[13px] text-text-tertiary sm:ml-auto sm:text-right shrink-0">
                            {ep.description}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </section>

            <section>
              <h2 className="heading-3 text-text-primary mb-4">Response Format &amp; Errors</h2>
              <p className="mb-4">All responses are JSON. Errors return a standard shape:</p>
              <div className="terminal-card p-4 rounded-lg mb-4 overflow-x-auto">
                <pre className="font-mono text-[13px] text-text-primary">
{`{
  "detail": "Ticker not found: XYZ"
}`}
                </pre>
              </div>
              <div className="border border-border-primary rounded-lg divide-y divide-border-subtle overflow-hidden">
                {errorCodes.map((err) => (
                  <div key={err.code} className="px-4 py-3 flex items-start gap-3">
                    <span className="font-mono text-[13px] text-accent font-semibold w-10 shrink-0">
                      {err.code}
                    </span>
                    <span className="text-[13px] text-text-tertiary">{err.meaning}</span>
                  </div>
                ))}
              </div>
            </section>

            <section>
              <h2 className="heading-3 text-text-primary mb-4">SDKs &amp; Support</h2>
              <p className="mb-4">
                The API is REST-only. Official client SDKs are not yet available.
              </p>
              <ul className="list-disc list-inside space-y-2 text-text-tertiary">
                <li>
                  For integration support, contact us at{" "}
                  <Link
                    href="/contact"
                    className="text-accent hover:text-accent-hover transition-colors underline underline-offset-2"
                  >
                    our contact page
                  </Link>
                </li>
                <li>
                  For data handling practices, see our{" "}
                  <Link
                    href="/security"
                    className="text-accent hover:text-accent-hover transition-colors underline underline-offset-2"
                  >
                    security page
                  </Link>
                </li>
              </ul>
            </section>
          </div>

          <div className="mt-16 pt-8 border-t border-border-subtle">
            <Link
              href="/"
              className="text-sm text-text-tertiary hover:text-text-secondary transition-colors"
            >
              &larr; Back to home
            </Link>
          </div>
        </div>
      </div>
    </main>
  )
}
```

**Step 4: Run test to verify it passes**

Run: `cd web && npx vitest run src/app/api-docs/__tests__/page.test.tsx`
Expected: PASS (7 tests)

**Step 5: Commit**

```bash
git add web/src/app/api-docs/
git commit -m "feat(web): add API docs page with endpoint reference and auth guide"
```

---

### Task 3: Contact Page

**Files:**
- Create: `web/src/app/contact/page.tsx`
- Create: `web/src/components/contact/contact-form.tsx`
- Create: `web/src/components/contact/index.ts`
- Test: `web/src/app/contact/__tests__/page.test.tsx`

**Step 1: Write the failing test**

Create `web/src/app/contact/__tests__/page.test.tsx`:

```tsx
import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import ContactPage from "../page"

describe("Contact Page", () => {
  it("renders the page heading", () => {
    render(<ContactPage />)
    expect(screen.getByRole("heading", { level: 1, name: /get in touch/i })).toBeInTheDocument()
  })

  it("renders all four contact channels", () => {
    render(<ContactPage />)
    expect(screen.getByText("General Support")).toBeInTheDocument()
    expect(screen.getByText("Security")).toBeInTheDocument()
    expect(screen.getByText("Legal & Privacy")).toBeInTheDocument()
    expect(screen.getByText("Business & Partnerships")).toBeInTheDocument()
  })

  it("renders mailto links for all channels", () => {
    render(<ContactPage />)
    expect(screen.getByRole("link", { name: "support@margin-invest.com" })).toHaveAttribute(
      "href",
      "mailto:support@margin-invest.com"
    )
    expect(screen.getByRole("link", { name: "security@margin-invest.com" })).toHaveAttribute(
      "href",
      "mailto:security@margin-invest.com"
    )
    expect(screen.getByRole("link", { name: "legal@margin-invest.com" })).toHaveAttribute(
      "href",
      "mailto:legal@margin-invest.com"
    )
    expect(screen.getByRole("link", { name: "partnerships@margin-invest.com" })).toHaveAttribute(
      "href",
      "mailto:partnerships@margin-invest.com"
    )
  })

  it("renders response time SLAs", () => {
    render(<ContactPage />)
    expect(screen.getByText(/within 24 hours/i)).toBeInTheDocument()
    expect(screen.getByText(/within 48 hours/i)).toBeInTheDocument()
    expect(screen.getByText(/within 5 business days/i)).toBeInTheDocument()
    expect(screen.getByText(/within 3 business days/i)).toBeInTheDocument()
  })

  it("renders the contact form fields", () => {
    render(<ContactPage />)
    expect(screen.getByLabelText(/name/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/subject/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/message/i)).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /send message/i })).toBeInTheDocument()
  })

  it("validates required fields on submit", async () => {
    const user = userEvent.setup()
    render(<ContactPage />)
    await user.click(screen.getByRole("button", { name: /send message/i }))
    // HTML5 validation prevents submission — form should still be visible
    expect(screen.getByRole("button", { name: /send message/i })).toBeInTheDocument()
  })

  it("renders office hours", () => {
    render(<ContactPage />)
    expect(screen.getByText(/monday.*friday.*9 am.*6 pm et/i)).toBeInTheDocument()
  })

  it("renders quick links to related pages", () => {
    render(<ContactPage />)
    expect(screen.getByRole("link", { name: /support/i })).toHaveAttribute("href", "/support")
    expect(screen.getByRole("link", { name: /security/i })).toHaveAttribute("href", "/security")
    expect(screen.getByRole("link", { name: /api/i })).toHaveAttribute("href", "/api-docs")
    expect(screen.getByRole("link", { name: /legal/i })).toHaveAttribute("href", "/legal")
  })

  it("renders the back to home link", () => {
    render(<ContactPage />)
    const backLink = screen.getByRole("link", { name: /back to home/i })
    expect(backLink).toHaveAttribute("href", "/")
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd web && npx vitest run src/app/contact/__tests__/page.test.tsx`
Expected: FAIL — module not found

**Step 3: Write the ContactForm component**

Create `web/src/components/contact/contact-form.tsx`:

```tsx
"use client"

import { useState } from "react"

const subjectOptions = [
  "General",
  "API Integration",
  "Security Report",
  "Business Inquiry",
  "Other",
]

export function ContactForm() {
  const [submitted, setSubmitted] = useState(false)

  function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const form = e.currentTarget
    const data = new FormData(form)
    const email = "support@margin-invest.com"
    const subject = data.get("subject") as string
    const body = `Name: ${data.get("name")}\n\n${data.get("message")}`
    window.location.href = `mailto:${email}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`
    setSubmitted(true)
  }

  if (submitted) {
    return (
      <div className="p-6 border border-border-primary rounded-lg bg-bg-elevated text-center">
        <p className="text-[15px] font-semibold text-text-primary mb-2">Message prepared</p>
        <p className="text-[13px] text-text-tertiary">
          Your email client should have opened with the message. If it didn&apos;t, email us
          directly at{" "}
          <a
            href="mailto:support@margin-invest.com"
            className="text-accent hover:text-accent-hover transition-colors underline underline-offset-2"
          >
            support@margin-invest.com
          </a>
          .
        </p>
      </div>
    )
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label htmlFor="contact-name" className="block text-[13px] font-medium text-text-primary mb-1">
          Name
        </label>
        <input
          id="contact-name"
          name="name"
          type="text"
          required
          className="w-full px-3 py-2 bg-bg-elevated border border-border-primary rounded-lg text-[14px] text-text-primary placeholder:text-text-tertiary focus:outline-none focus:border-accent transition-colors"
          placeholder="Your name"
        />
      </div>

      <div>
        <label htmlFor="contact-email" className="block text-[13px] font-medium text-text-primary mb-1">
          Email
        </label>
        <input
          id="contact-email"
          name="email"
          type="email"
          required
          className="w-full px-3 py-2 bg-bg-elevated border border-border-primary rounded-lg text-[14px] text-text-primary placeholder:text-text-tertiary focus:outline-none focus:border-accent transition-colors"
          placeholder="you@example.com"
        />
      </div>

      <div>
        <label htmlFor="contact-subject" className="block text-[13px] font-medium text-text-primary mb-1">
          Subject
        </label>
        <select
          id="contact-subject"
          name="subject"
          required
          className="w-full px-3 py-2 bg-bg-elevated border border-border-primary rounded-lg text-[14px] text-text-primary focus:outline-none focus:border-accent transition-colors"
        >
          <option value="">Select a topic...</option>
          {subjectOptions.map((opt) => (
            <option key={opt} value={opt}>
              {opt}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label htmlFor="contact-message" className="block text-[13px] font-medium text-text-primary mb-1">
          Message
        </label>
        <textarea
          id="contact-message"
          name="message"
          required
          rows={5}
          className="w-full px-3 py-2 bg-bg-elevated border border-border-primary rounded-lg text-[14px] text-text-primary placeholder:text-text-tertiary focus:outline-none focus:border-accent transition-colors resize-y"
          placeholder="How can we help?"
        />
      </div>

      <button
        type="submit"
        className="px-6 py-2.5 bg-accent hover:bg-accent-hover text-bg-primary text-[14px] font-medium rounded-lg transition-colors"
      >
        Send message
      </button>
    </form>
  )
}
```

Create `web/src/components/contact/index.ts`:

```ts
export { ContactForm } from "./contact-form"
```

**Step 4: Write the Contact page**

Create `web/src/app/contact/page.tsx`:

```tsx
import type { Metadata } from "next"
import Link from "next/link"
import { Navbar } from "@/components/nav/navbar"
import { ContactForm } from "@/components/contact"

export const metadata: Metadata = {
  title: "Contact | Margin Invest",
  description:
    "Get in touch with Margin Invest — support, security reports, legal inquiries, and business partnerships.",
  alternates: { canonical: "https://margin-invest.com/contact" },
}

const channels = [
  {
    title: "General Support",
    email: "support@margin-invest.com",
    description: "Platform questions, account help, billing issues",
    sla: "Within 24 hours",
  },
  {
    title: "Security",
    email: "security@margin-invest.com",
    description: "Vulnerability reports, suspicious activity",
    sla: "Within 48 hours",
  },
  {
    title: "Legal & Privacy",
    email: "legal@margin-invest.com",
    description: "Data deletion, compliance, legal notices",
    sla: "Within 5 business days",
  },
  {
    title: "Business & Partnerships",
    email: "partnerships@margin-invest.com",
    description: "Enterprise inquiries, API partnerships, data licensing",
    sla: "Within 3 business days",
  },
]

const quickLinks = [
  { label: "Looking for answers? Visit Support", href: "/support" },
  { label: "Security practices", href: "/security" },
  { label: "API documentation", href: "/api-docs" },
  { label: "Legal & terms", href: "/legal" },
]

export default function ContactPage() {
  return (
    <main className="relative bg-bg-primary min-h-screen">
      <div className="relative z-10">
        <Navbar />

        <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-16 sm:py-24">
          <h1 className="heading-2 text-text-primary mb-4">Get in Touch</h1>
          <p className="body-text text-text-secondary mb-12">
            Whether you&apos;re a developer, investor, or researcher — we&apos;ll route you to
            the right person.
          </p>

          <div className="space-y-12">
            <section>
              <h2 className="heading-3 text-text-primary mb-4">Contact Channels</h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {channels.map((ch) => (
                  <div
                    key={ch.email}
                    className="p-5 border border-border-primary rounded-lg bg-bg-elevated"
                  >
                    <h3 className="text-[15px] font-semibold text-text-primary mb-1">
                      {ch.title}
                    </h3>
                    <p className="text-[13px] text-text-tertiary mb-2">{ch.description}</p>
                    <a
                      href={`mailto:${ch.email}`}
                      className="text-[13px] text-accent hover:text-accent-hover transition-colors underline underline-offset-2"
                    >
                      {ch.email}
                    </a>
                    <p className="text-[12px] text-text-tertiary mt-2">{ch.sla}</p>
                  </div>
                ))}
              </div>
            </section>

            <section>
              <h2 className="heading-3 text-text-primary mb-4">Send a Message</h2>
              <ContactForm />
            </section>

            <section>
              <h2 className="heading-3 text-text-primary mb-4">Availability</h2>
              <ul className="list-disc list-inside space-y-2 text-[14px] text-text-tertiary">
                <li>Support hours: Monday–Friday, 9 AM – 6 PM ET</li>
                <li>Security reports: Monitored 7 days a week</li>
                <li>
                  System health:{" "}
                  <Link
                    href="/status"
                    className="text-accent hover:text-accent-hover transition-colors underline underline-offset-2"
                  >
                    check platform status
                  </Link>
                </li>
              </ul>
            </section>

            <section>
              <h2 className="heading-3 text-text-primary mb-4">Quick Links</h2>
              <ul className="space-y-2">
                {quickLinks.map((link) => (
                  <li key={link.href}>
                    <Link
                      href={link.href}
                      className="text-[14px] text-accent hover:text-accent-hover transition-colors underline underline-offset-2"
                    >
                      {link.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </section>
          </div>

          <div className="mt-16 pt-8 border-t border-border-subtle">
            <Link
              href="/"
              className="text-sm text-text-tertiary hover:text-text-secondary transition-colors"
            >
              &larr; Back to home
            </Link>
          </div>
        </div>
      </div>
    </main>
  )
}
```

**Step 5: Run test to verify it passes**

Run: `cd web && npx vitest run src/app/contact/__tests__/page.test.tsx`
Expected: PASS (9 tests)

**Step 6: Commit**

```bash
git add web/src/app/contact/ web/src/components/contact/
git commit -m "feat(web): add contact page with channels, form, and SLAs"
```

---

### Task 4: Footer Updates

**Files:**
- Modify: `web/src/components/landing/footer-section.tsx:10` (change `/api` to `/api-docs`)
- Modify: `web/src/components/layout/footer.tsx:3-7` (add three new links)
- Test: `web/src/components/landing/__tests__/footer-section.test.tsx`
- Test: `web/src/components/layout/__tests__/footer.test.tsx`

**Step 1: Write failing tests**

Create `web/src/components/landing/__tests__/footer-section.test.tsx`:

```tsx
import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { FooterSection } from "../footer-section"

describe("FooterSection (landing)", () => {
  it("renders all navigation links", () => {
    render(<FooterSection />)
    expect(screen.getByRole("link", { name: "Support" })).toHaveAttribute("href", "/support")
    expect(screen.getByRole("link", { name: "Methodology" })).toHaveAttribute("href", "/methodology")
    expect(screen.getByRole("link", { name: "Security" })).toHaveAttribute("href", "/security")
    expect(screen.getByRole("link", { name: "Legal" })).toHaveAttribute("href", "/legal")
    expect(screen.getByRole("link", { name: "Status" })).toHaveAttribute("href", "/status")
    expect(screen.getByRole("link", { name: "API" })).toHaveAttribute("href", "/api-docs")
    expect(screen.getByRole("link", { name: "Contact" })).toHaveAttribute("href", "/contact")
  })

  it("does not link to /api (reserved for API routes)", () => {
    render(<FooterSection />)
    const links = screen.getAllByRole("link")
    const apiLink = links.find((l) => l.getAttribute("href") === "/api")
    expect(apiLink).toBeUndefined()
  })
})
```

Create `web/src/components/layout/__tests__/footer.test.tsx`:

```tsx
import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { Footer } from "../footer"

describe("Footer (authenticated)", () => {
  it("renders all navigation links", () => {
    render(<Footer />)
    expect(screen.getByRole("link", { name: "Support" })).toHaveAttribute("href", "/support")
    expect(screen.getByRole("link", { name: "Methodology" })).toHaveAttribute("href", "/methodology")
    expect(screen.getByRole("link", { name: "Legal" })).toHaveAttribute("href", "/legal")
    expect(screen.getByRole("link", { name: "Security" })).toHaveAttribute("href", "/security")
    expect(screen.getByRole("link", { name: "API" })).toHaveAttribute("href", "/api-docs")
    expect(screen.getByRole("link", { name: "Contact" })).toHaveAttribute("href", "/contact")
  })
})
```

**Step 2: Run tests to verify they fail**

Run: `cd web && npx vitest run src/components/landing/__tests__/footer-section.test.tsx src/components/layout/__tests__/footer.test.tsx`
Expected: FAIL — `/api-docs` assertion fails (current value is `/api`), missing Security/API/Contact links in authenticated footer

**Step 3: Update the landing footer**

In `web/src/components/landing/footer-section.tsx`, change line 10:

```tsx
// Before:
  { label: "API", href: "/api" },

// After:
  { label: "API", href: "/api-docs" },
```

**Step 4: Update the authenticated footer**

In `web/src/components/layout/footer.tsx`, update the `footerLinks` array:

```tsx
// Before:
const footerLinks = [
  { href: "/support", label: "Support" },
  { href: "/methodology", label: "Methodology" },
  { href: "/legal", label: "Legal" },
]

// After:
const footerLinks = [
  { href: "/support", label: "Support" },
  { href: "/methodology", label: "Methodology" },
  { href: "/legal", label: "Legal" },
  { href: "/security", label: "Security" },
  { href: "/api-docs", label: "API" },
  { href: "/contact", label: "Contact" },
]
```

**Step 5: Run tests to verify they pass**

Run: `cd web && npx vitest run src/components/landing/__tests__/footer-section.test.tsx src/components/layout/__tests__/footer.test.tsx`
Expected: PASS (4 tests)

**Step 6: Commit**

```bash
git add web/src/components/landing/footer-section.tsx web/src/components/layout/footer.tsx web/src/components/landing/__tests__/ web/src/components/layout/__tests__/footer.test.tsx
git commit -m "fix(web): update footer links — /api to /api-docs, add security/contact to auth footer"
```

---

### Task 5: Sitemap and Robots

**Files:**
- Create: `web/src/app/sitemap.ts`
- Create: `web/src/app/robots.ts`
- Test: `web/src/app/__tests__/sitemap.test.ts`
- Test: `web/src/app/__tests__/robots.test.ts`

**Step 1: Write failing tests**

Create `web/src/app/__tests__/sitemap.test.ts`:

```ts
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
    expect(urls).toContain("https://margin-invest.com/")
    expect(urls).toContain("https://margin-invest.com/methodology")
    expect(urls).toContain("https://margin-invest.com/legal")
    expect(urls).toContain("https://margin-invest.com/support")
    expect(urls).toContain("https://margin-invest.com/status")
    expect(urls).toContain("https://margin-invest.com/guides")
    expect(urls).toContain("https://margin-invest.com/security")
    expect(urls).toContain("https://margin-invest.com/api-docs")
    expect(urls).toContain("https://margin-invest.com/contact")
  })

  it("excludes authenticated routes", () => {
    const entries = sitemap()
    const urls = entries.map((e) => e.url)
    expect(urls).not.toContain("https://margin-invest.com/dashboard")
    expect(urls).not.toContain("https://margin-invest.com/account")
    expect(urls).not.toContain("https://margin-invest.com/settings")
    expect(urls).not.toContain("https://margin-invest.com/login")
  })

  it("each entry has lastModified and changeFrequency", () => {
    const entries = sitemap()
    for (const entry of entries) {
      expect(entry.lastModified).toBeDefined()
      expect(entry.changeFrequency).toBeDefined()
    }
  })
})
```

Create `web/src/app/__tests__/robots.test.ts`:

```ts
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
    const disallowed = Array.isArray(wildcardRule!.disallow) ? wildcardRule!.disallow : [wildcardRule!.disallow]
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
```

**Step 2: Run tests to verify they fail**

Run: `cd web && npx vitest run src/app/__tests__/sitemap.test.ts src/app/__tests__/robots.test.ts`
Expected: FAIL — modules not found

**Step 3: Create sitemap.ts**

Create `web/src/app/sitemap.ts`:

```ts
import type { MetadataRoute } from "next"

const BASE_URL = "https://margin-invest.com"

export default function sitemap(): MetadataRoute.Sitemap {
  return [
    { url: `${BASE_URL}/`, lastModified: new Date("2026-02-27"), changeFrequency: "weekly", priority: 1.0 },
    { url: `${BASE_URL}/methodology`, lastModified: new Date("2026-02-27"), changeFrequency: "monthly", priority: 0.8 },
    { url: `${BASE_URL}/legal`, lastModified: new Date("2026-02-27"), changeFrequency: "monthly", priority: 0.3 },
    { url: `${BASE_URL}/support`, lastModified: new Date("2026-02-27"), changeFrequency: "monthly", priority: 0.6 },
    { url: `${BASE_URL}/status`, lastModified: new Date("2026-02-27"), changeFrequency: "daily", priority: 0.4 },
    { url: `${BASE_URL}/guides`, lastModified: new Date("2026-02-27"), changeFrequency: "weekly", priority: 0.7 },
    { url: `${BASE_URL}/security`, lastModified: new Date("2026-02-27"), changeFrequency: "monthly", priority: 0.6 },
    { url: `${BASE_URL}/api-docs`, lastModified: new Date("2026-02-27"), changeFrequency: "monthly", priority: 0.7 },
    { url: `${BASE_URL}/contact`, lastModified: new Date("2026-02-27"), changeFrequency: "monthly", priority: 0.5 },
  ]
}
```

**Step 4: Create robots.ts**

Create `web/src/app/robots.ts`:

```ts
import type { MetadataRoute } from "next"

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: "/",
      disallow: ["/dashboard", "/account", "/settings", "/admin/", "/api/v1/", "/login", "/register", "/reset-password", "/mfa/"],
    },
    sitemap: "https://margin-invest.com/sitemap.xml",
  }
}
```

**Step 5: Run tests to verify they pass**

Run: `cd web && npx vitest run src/app/__tests__/sitemap.test.ts src/app/__tests__/robots.test.ts`
Expected: PASS (8 tests)

**Step 6: Commit**

```bash
git add web/src/app/sitemap.ts web/src/app/robots.ts web/src/app/__tests__/
git commit -m "feat(web): add sitemap.ts and robots.ts for SEO"
```

---

### Task 6: Link Integrity Regression Test

**Files:**
- Create: `web/src/app/__tests__/link-integrity.test.ts`

**Purpose:** Prevent future 404s by asserting every footer link maps to an existing page route.

**Step 1: Write the test**

Create `web/src/app/__tests__/link-integrity.test.ts`:

```ts
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
  "/status",
  "/api-docs",
  "/contact",
]

// Authenticated footer links (keep in sync with layout/footer.tsx)
const authFooterLinks = [
  "/support",
  "/methodology",
  "/legal",
  "/security",
  "/api-docs",
  "/contact",
]

const APP_DIR = join(__dirname, "..")

function routeExists(route: string): boolean {
  // Strip leading slash, map to app directory
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
```

**Step 2: Run test to verify it passes**

Run: `cd web && npx vitest run src/app/__tests__/link-integrity.test.ts`
Expected: PASS (2 tests) — all pages now exist

**Step 3: Commit**

```bash
git add web/src/app/__tests__/link-integrity.test.ts
git commit -m "test(web): add link integrity regression test for footer links"
```

---

### Task 7: Full Test Suite Verification

**Files:** None (verification only)

**Step 1: Run all web tests**

Run: `cd web && npx vitest run`
Expected: All tests pass, including the new ones from Tasks 1-6

**Step 2: Verify no references to old `/api` footer link remain**

Run: `cd web && grep -rn 'href.*"/api"' src/components/landing/ src/components/layout/`
Expected: No matches (the only `/api` references should be in `src/app/api/` route handler directories, not in footer links)

**Step 3: Verify page count**

Run: `find web/src/app -name "page.tsx" -not -path "*/api/*" | wc -l`
Expected: Count should include the 3 new pages (security, api-docs, contact)
