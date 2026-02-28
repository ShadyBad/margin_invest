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
      {
        method: "GET",
        path: "/api/v1/scores/{ticker}",
        description: "Composite score, factor breakdown, composite percentile",
      },
      {
        method: "GET",
        path: "/api/v1/scores/{ticker}/history",
        description: "Historical score snapshots over time",
      },
      {
        method: "GET",
        path: "/api/v1/scores/{ticker}/valuation-audit",
        description: "Intrinsic value calculation audit trail",
      },
      {
        method: "GET",
        path: "/api/v1/scores",
        description: "List all scored assets with current scores",
      },
    ],
  },
  {
    group: "Backtesting",
    items: [
      {
        method: "GET",
        path: "/api/v1/backtest/default",
        description: "Default backtest with current scoring parameters",
      },
      {
        method: "POST",
        path: "/api/v1/backtest/replay",
        description: "Run custom backtest replay with parameter overrides",
      },
      {
        method: "GET",
        path: "/api/v1/backtest/shadow-portfolio",
        description: "Shadow portfolio tracking real-time picks",
      },
      {
        method: "GET",
        path: "/api/v1/backtest/teaser/{ticker}",
        description: "Single-asset backtest teaser",
      },
      {
        method: "GET",
        path: "/api/v1/backtest/portfolio-teaser",
        description: "Portfolio equity curve teaser (public)",
      },
    ],
  },
  {
    group: "Institutional (13F)",
    items: [
      {
        method: "GET",
        path: "/api/v1/13f/holdings/{ticker}",
        description: "Institutional holders for a ticker from SEC 13F filings",
      },
      {
        method: "GET",
        path: "/api/v1/13f/holdings/{ticker}/history",
        description: "Historical institutional holding changes",
      },
      {
        method: "GET",
        path: "/api/v1/13f/managers",
        description: "List tracked institutional managers",
      },
      {
        method: "GET",
        path: "/api/v1/13f/managers/{manager_id}/portfolio",
        description: "Full portfolio for a specific manager",
      },
    ],
  },
  {
    group: "Universe & Transparency",
    items: [
      {
        method: "GET",
        path: "/api/v1/universe/funnel",
        description: "Selectivity funnel — how many assets pass each filter stage",
      },
      {
        method: "GET",
        path: "/api/v1/correlations/showcase",
        description: "Factor correlation matrix for scored universe",
      },
      {
        method: "GET",
        path: "/api/v1/governance/transparency",
        description: "Oversight classification and pipeline health",
      },
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
                <code className="font-mono text-[13px] bg-bg-elevated px-1.5 py-0.5 rounded">
                  X-API-Key
                </code>{" "}
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
                API requests are rate-limited per key. When you exceed the limit, responses return
                status 429 with a{" "}
                <code className="font-mono text-[13px] bg-bg-elevated px-1.5 py-0.5 rounded">
                  Retry-After
                </code>{" "}
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
                        <div
                          key={ep.path}
                          className="px-4 py-3 flex flex-col sm:flex-row sm:items-start gap-1 sm:gap-3"
                        >
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
