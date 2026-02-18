import type { Metadata } from "next"
import Link from "next/link"
import { Navbar } from "@/components/nav/navbar"

export const metadata: Metadata = {
  title: "Legal | Margin Invest",
  description:
    "Terms of use, risk disclosure, investment disclaimer, and data privacy information for Margin Invest.",
}

export default function LegalPage() {
  return (
    <main className="relative bg-bg-primary min-h-screen">
      <div className="relative z-10">
        <Navbar />

        <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-16 sm:py-24">
          <h1 className="heading-2 text-text-primary mb-12">Legal</h1>

          <div className="space-y-12 text-text-secondary body-text">
            <section>
              <h2 className="heading-3 text-text-primary mb-4">1. Terms of Use</h2>
              <p className="mb-4">
                By accessing or using Margin Invest (&ldquo;the Platform&rdquo;), you agree to be
                bound by these Terms of Use. If you do not agree to these terms, you must not use
                the Platform.
              </p>
              <p className="mb-4">
                Margin Invest provides quantitative investment analysis tools and scoring frameworks
                for informational and educational purposes only. Use of the Platform does not create
                an advisory, fiduciary, or client relationship.
              </p>
              <p>
                We reserve the right to modify these terms at any time. Continued use of the
                Platform constitutes acceptance of any changes.
              </p>
            </section>

            <section>
              <h2 className="heading-3 text-text-primary mb-4">2. Investment Disclaimer</h2>
              <p className="mb-4">
                Margin Invest does not provide personalized investment advice. All content, including
                conviction scores, factor breakdowns, rankings, and portfolio insights, is provided
                for informational purposes only.
              </p>
              <p className="mb-4">Nothing on this Platform constitutes:</p>
              <ul className="list-disc list-inside mb-4 space-y-1 text-text-tertiary">
                <li>Investment advice</li>
                <li>A recommendation to buy or sell securities</li>
                <li>An offer or solicitation to transact</li>
                <li>Legal, tax, or financial advice</li>
              </ul>
              <p className="mb-4">
                All investments carry risk, including the possible loss of principal. Past
                performance does not guarantee future results.
              </p>
              <p>You are solely responsible for your investment decisions.</p>
            </section>

            <section>
              <h2 className="heading-3 text-text-primary mb-4">3. Risk Disclosure</h2>
              <p className="mb-4">
                Investing in equities, derivatives, or financial instruments involves substantial
                risk. Market volatility, liquidity constraints, macroeconomic changes, and
                company-specific events may materially impact asset prices.
              </p>
              <p className="mb-4">
                Margin Invest&apos;s scoring models rely on quantitative methodologies and
                historical data, which may not predict future performance. Model limitations, data
                inaccuracies, or unforeseen market events may result in losses.
              </p>
              <p>Users acknowledge and accept these risks when using the Platform.</p>
            </section>

            <section>
              <h2 className="heading-3 text-text-primary mb-4">4. Data Usage &amp; Privacy</h2>
              <p className="mb-4">
                Margin Invest may collect limited user data necessary for authentication, platform
                functionality, and performance optimization.
              </p>
              <p className="mb-4">We do not sell user data to third parties.</p>
              <p className="mb-4">
                Aggregated, anonymized data may be used for analytical and product improvement
                purposes.
              </p>
              <p>
                For privacy-related inquiries, contact:{" "}
                <a
                  href="mailto:legal@margin-invest.com"
                  className="text-accent hover:text-accent-hover transition-colors underline underline-offset-2"
                >
                  legal@margin-invest.com
                </a>
              </p>
            </section>

            <section>
              <h2 className="heading-3 text-text-primary mb-4">5. Limitation of Liability</h2>
              <p className="mb-4">
                To the fullest extent permitted by law, Margin Invest and its affiliates shall not
                be liable for any direct, indirect, incidental, consequential, or punitive damages
                arising from:
              </p>
              <ul className="list-disc list-inside mb-4 space-y-1 text-text-tertiary">
                <li>Use or inability to use the Platform</li>
                <li>Reliance on model outputs</li>
                <li>Data inaccuracies</li>
                <li>Market losses</li>
              </ul>
              <p>
                The Platform is provided &ldquo;as is&rdquo; without warranties of any kind.
              </p>
            </section>

            <section>
              <h2 className="heading-3 text-text-primary mb-4">6. Contact</h2>
              <p>
                For legal inquiries, compliance matters, or formal notices:{" "}
                <a
                  href="mailto:legal@margin-invest.com"
                  className="text-accent hover:text-accent-hover transition-colors underline underline-offset-2"
                >
                  legal@margin-invest.com
                </a>
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
