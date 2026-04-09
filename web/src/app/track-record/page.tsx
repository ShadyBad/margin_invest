import type { Metadata } from "next"
import { Navbar } from "@/components/nav/navbar"
import { PageHeader } from "@/components/shared/page-header"
import { TrackRecordTable } from "@/components/track-record/track-record-table"
import { TrackRecordStats } from "@/components/track-record/track-record-stats"

export const metadata: Metadata = {
  title: "Track Record | Margin Invest",
  description:
    "Public ledger of Margin Invest scoring cycles and results. View historical performance, filter statistics, and survivor counts for every analysis run.",
}

export default function TrackRecordPage() {
  return (
    <main className="relative bg-bg-primary min-h-screen">
      <div className="relative z-10">
        <Navbar />
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 pt-28">
          <PageHeader
            category="TRANSPARENCY"
            title="The public ledger. Every score, every outcome."
            description="We log what the system scored and what happened. No retroactive adjustments."
          />
        </div>
        <TrackRecordStats />
        <TrackRecordTable />
        {/* Disclaimer */}
        <section className="py-8 px-6 border-t border-border-subtle">
          <div className="max-w-6xl mx-auto">
            <p className="text-xs text-text-tertiary text-center leading-relaxed max-w-3xl mx-auto">
              Margin Invest is not a registered investment advisor or broker-dealer. Scores and rankings
              are the output of a deterministic quantitative model and do not constitute investment advice,
              a recommendation, or a solicitation to buy or sell any security. Past performance of the
              scoring system does not guarantee future results. Always conduct your own due diligence and
              consult a qualified financial advisor before making investment decisions.
            </p>
          </div>
        </section>
      </div>
    </main>
  )
}
