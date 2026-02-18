import type { Metadata } from "next"
import Link from "next/link"
import { Navbar } from "@/components/nav/navbar"

export const metadata: Metadata = {
  title: "Support | Margin Invest",
  description:
    "Get help with Margin Invest — how the platform works, conviction scores, account access, and contact information.",
}

export default function SupportPage() {
  return (
    <main className="relative bg-bg-primary min-h-screen">
      <div className="relative z-10">
        <Navbar />

        <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-16 sm:py-24">
          <h1 className="heading-2 text-text-primary mb-4">Support</h1>
          <p className="body-text text-text-secondary mb-12">
            Margin Invest is a quantitative scoring platform designed to bring structure and
            discipline to equity evaluation. Below you will find guidance on how the platform works
            and how to resolve common questions.
          </p>

          <div className="space-y-12 text-text-secondary body-text">
            <section>
              <h2 className="heading-3 text-text-primary mb-4">1. How Margin Invest Works</h2>
              <p className="mb-4">
                Margin Invest uses a deterministic scoring engine built around three primary pillars:
              </p>
              <ul className="list-disc list-inside mb-4 space-y-1 text-text-tertiary">
                <li>
                  <span className="text-text-secondary font-medium">Quality</span> &ndash;
                  Profitability, capital efficiency, balance sheet strength
                </li>
                <li>
                  <span className="text-text-secondary font-medium">Value</span> &ndash; Valuation
                  multiples, intrinsic value estimates, margin of safety
                </li>
                <li>
                  <span className="text-text-secondary font-medium">Momentum</span> &ndash; Price
                  strength and trend persistence
                </li>
              </ul>
              <p>
                Each company receives a composite conviction score derived from weighted factor
                models. Scores are calculated using standardized financial data and updated
                periodically.
              </p>
            </section>

            <section>
              <h2 className="heading-3 text-text-primary mb-4">
                2. Understanding Conviction Scores
              </h2>
              <p className="mb-4">
                Conviction scores reflect relative ranking within the investment universe. A higher
                score indicates stronger alignment across quality, value, and momentum metrics.
              </p>
              <p>
                Scores are not guarantees of performance and should be used as part of a broader
                investment process.
              </p>
            </section>

            <section>
              <h2 className="heading-3 text-text-primary mb-4">3. Portfolio Construction</h2>
              <p className="mb-4">
                The allocation model determines suggested portfolio weighting based on conviction
                strength and risk calibration.
              </p>
              <p>
                Allocation outputs are systematic and do not account for individual financial
                circumstances.
              </p>
            </section>

            <section>
              <h2 className="heading-3 text-text-primary mb-4">4. Frequently Asked Questions</h2>
              <div className="space-y-6">
                <div>
                  <h3 className="text-text-primary font-medium mb-1">
                    Is this financial advice?
                  </h3>
                  <p>
                    No. Margin Invest provides analytical tools, not personalized financial advice.
                  </p>
                </div>
                <div>
                  <h3 className="text-text-primary font-medium mb-1">
                    How often is data updated?
                  </h3>
                  <p>
                    Data is refreshed periodically depending on source availability and reporting
                    cycles.
                  </p>
                </div>
                <div>
                  <h3 className="text-text-primary font-medium mb-1">
                    Why are some metrics unavailable?
                  </h3>
                  <p>
                    Some securities may lack sufficient reporting data to compute certain metrics
                    reliably.
                  </p>
                </div>
              </div>
            </section>

            <section>
              <h2 className="heading-3 text-text-primary mb-4">5. Account &amp; Access Issues</h2>
              <p className="mb-4">
                If you experience login issues, authentication errors, or dashboard access problems:
              </p>
              <ul className="list-disc list-inside mb-4 space-y-1 text-text-tertiary">
                <li>Ensure cookies are enabled</li>
                <li>Confirm email verification (if applicable)</li>
                <li>Clear browser cache and retry</li>
              </ul>
              <p>If issues persist, contact support.</p>
            </section>

            <section>
              <h2 className="heading-3 text-text-primary mb-4">6. Contact Support</h2>
              <p>
                For technical assistance, platform questions, or general inquiries:{" "}
                <a
                  href="mailto:support@margin-invest.com"
                  className="text-accent hover:text-accent-hover transition-colors underline underline-offset-2"
                >
                  support@margin-invest.com
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
