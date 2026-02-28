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
