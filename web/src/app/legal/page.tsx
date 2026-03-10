import type { Metadata } from "next"
import Link from "next/link"
import { Navbar } from "@/components/nav/navbar"
import { PageHeader } from "@/components/shared/page-header"

export const metadata: Metadata = {
  title: "Legal | Margin Invest",
  description:
    "Terms of use, risk disclosure, investment disclaimer, and data privacy information for Margin Invest.",
}

const sections = [
  { id: "terms-of-use", label: "Terms of Use" },
  { id: "investment-disclaimer", label: "Disclaimer" },
  { id: "disclosure", label: "Disclosure" },
  { id: "data-privacy", label: "Data & Privacy" },
  { id: "liability", label: "Liability" },
  { id: "contact", label: "Contact" },
]

export default function LegalPage() {
  return (
    <main className="relative bg-bg-primary min-h-screen">
      <div className="relative z-10">
        <Navbar />

        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-16 sm:py-24">
          <PageHeader
            category="LEGAL"
            title="Legal Disclosures"
            description="Investment disclaimers and regulatory information."
          />

          <nav className="flex flex-wrap gap-4 mb-10 text-[13px]">
            <Link
              href="/terms"
              className="text-accent hover:text-accent-hover transition-colors underline underline-offset-2"
            >
              Terms of Service
            </Link>
            <Link
              href="/privacy"
              className="text-accent hover:text-accent-hover transition-colors underline underline-offset-2"
            >
              Privacy Policy
            </Link>
          </nav>

          <div className="grid grid-cols-1 lg:grid-cols-[1fr_200px] gap-8">
            <div className="space-y-8 text-text-secondary text-body">
              <section id="terms-of-use">
                <h2 className="text-title-1 text-text-primary mb-4">1. Terms of Use</h2>
              <p className="mb-4">
                By accessing or using Margin Invest (&ldquo;the Platform&rdquo;), you agree to be
                bound by these Terms of Use. If you do not agree to these terms, you must not use
                the Platform. See our full{" "}
                <Link
                  href="/terms"
                  className="text-accent hover:text-accent-hover transition-colors underline underline-offset-2"
                >
                  Terms of Service
                </Link>{" "}
                for complete details.
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

            <section id="investment-disclaimer">
              <h2 className="text-title-1 text-text-primary mb-4">2. Investment Disclaimer</h2>
              <p className="mb-4">
                Margin Invest does not provide personalized investment advice. All content, including
                composite scores, factor breakdowns, rankings, and portfolio insights, is provided
                for informational purposes only.
              </p>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 my-8">
                <div className="p-5 border border-border-primary rounded-lg bg-bg-elevated">
                  <h3 className="text-[14px] font-semibold text-text-primary mb-3 uppercase tracking-wide">
                    Margin Invest IS
                  </h3>
                  <ul className="space-y-2 text-[13px] text-text-secondary">
                    <li className="flex items-start gap-2">
                      <span className="text-bullish mt-0.5 flex-shrink-0">&bull;</span>
                      A quantitative analysis tool
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-bullish mt-0.5 flex-shrink-0">&bull;</span>
                      A software platform with automated scoring models
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-bullish mt-0.5 flex-shrink-0">&bull;</span>
                      An informational resource
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-bullish mt-0.5 flex-shrink-0">&bull;</span>
                      A backtested data provider
                    </li>
                  </ul>
                </div>
                <div className="p-5 border border-border-primary rounded-lg bg-bg-elevated">
                  <h3 className="text-[14px] font-semibold text-text-primary mb-3 uppercase tracking-wide">
                    Margin Invest IS NOT
                  </h3>
                  <ul className="space-y-2 text-[13px] text-text-secondary">
                    <li className="flex items-start gap-2">
                      <span className="text-bearish mt-0.5 flex-shrink-0">&bull;</span>
                      A financial adviser or investment adviser
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-bearish mt-0.5 flex-shrink-0">&bull;</span>
                      A broker-dealer
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-bearish mt-0.5 flex-shrink-0">&bull;</span>
                      A custodian of your assets
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-bearish mt-0.5 flex-shrink-0">&bull;</span>
                      A guarantee of investment returns
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-bearish mt-0.5 flex-shrink-0">&bull;</span>
                      A replacement for professional financial advice
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-bearish mt-0.5 flex-shrink-0">&bull;</span>
                      A financial product or security
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-bearish mt-0.5 flex-shrink-0">&bull;</span>
                      A margin or leverage provider
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-bearish mt-0.5 flex-shrink-0">&bull;</span>
                      A fiduciary
                    </li>
                  </ul>
                </div>
              </div>

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

            <section id="disclosure">
              <h2 className="text-title-1 text-text-primary mb-4">3. Risk Disclosure</h2>
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

            <section id="data-privacy">
              <h2 className="text-title-1 text-text-primary mb-4">4. Data Usage &amp; Privacy</h2>
              <p className="mb-4">
                Margin Invest may collect limited user data necessary for authentication, platform
                functionality, and performance optimization. See our full{" "}
                <Link
                  href="/privacy"
                  className="text-accent hover:text-accent-hover transition-colors underline underline-offset-2"
                >
                  Privacy Policy
                </Link>{" "}
                for complete details.
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

            <section id="liability">
              <h2 className="text-title-1 text-text-primary mb-4">5. Limitation of Liability</h2>
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

            <section id="contact">
              <h2 className="text-title-1 text-text-primary mb-4">6. Contact</h2>
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

            {/* Desktop TOC sidebar */}
            <aside className="hidden lg:block" aria-label="Table of contents">
              <nav className="sticky top-20">
                <p className="text-mono-label text-text-tertiary mb-4">On this page</p>
                <ul className="space-y-2">
                  {sections.map((s) => (
                    <li key={s.id}>
                      <a
                        href={`#${s.id}`}
                        className="text-xs text-text-tertiary hover:text-text-primary transition-colors"
                      >
                        {s.label}
                      </a>
                    </li>
                  ))}
                </ul>
              </nav>
            </aside>
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
