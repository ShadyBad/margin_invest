import type { Metadata } from "next"
import Link from "next/link"

export const metadata: Metadata = {
  title: "About",
  description:
    "Why we built a deterministic investment analysis system. Our mission, methodology, and the team behind it.",
}

export default function AboutPage() {
  return (
    <div className="min-h-screen bg-bg-primary">
      <div className="max-w-2xl mx-auto px-6 py-16 space-y-16">
        <section className="space-y-4">
          <h1 className="text-[32px] md:text-[40px] font-bold text-text-primary tracking-tight">
            Why This Exists
          </h1>
          <div className="space-y-4 text-body text-text-secondary leading-relaxed">
            <p>
              Most investment analysis is narrative-driven. An analyst reads a 10-K,
              forms an opinion, and publishes a rating that reflects their confidence,
              biases, and incentives — not the data.
            </p>
            <p>
              Margin Invest replaces that process with deterministic scoring. Five
              quantitative factors. Six forensic filters. Every formula documented.
              Every score reproducible with a spreadsheet.
            </p>
            <p>
              The system doesn&apos;t have opinions. It doesn&apos;t override its own
              output. It scores 3,000+ US equities daily with zero human discretion.
            </p>
          </div>
        </section>

        <section className="space-y-4">
          <h2 className="text-[24px] font-bold text-text-primary tracking-tight">
            How It Works
          </h2>
          <p className="text-body text-text-secondary leading-relaxed">
            Every equity is scored across quality, value, momentum, sentiment, and
            growth — ranked within its GICS sector to eliminate cross-sector bias.
            Before scoring, six forensic filters (including Beneish M-Score and
            Altman Z-Score) eliminate candidates with accounting red flags.
          </p>
          <Link
            href="/methodology"
            className="inline-block text-sm text-accent hover:underline underline-offset-2"
          >
            Read the full methodology &rarr;
          </Link>
        </section>

        <section className="space-y-4">
          <h2 className="text-[24px] font-bold text-text-primary tracking-tight">
            Who Built It
          </h2>
          <p className="text-body text-text-secondary leading-relaxed">
            Built by an engineer who got tired of paying for black-box ratings.
          </p>
        </section>

        <section className="space-y-4">
          <h2 className="text-[24px] font-bold text-text-primary tracking-tight">
            Contact
          </h2>
          <p className="text-body text-text-secondary">
            Questions, feedback, or partnership inquiries —{" "}
            <Link
              href="/contact"
              className="text-accent hover:underline underline-offset-2"
            >
              get in touch
            </Link>
            .
          </p>
        </section>
      </div>
    </div>
  )
}
