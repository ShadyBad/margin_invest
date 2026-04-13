import type { Metadata } from "next"
import { Navbar } from "@/components/nav/navbar"
import { PageHeader } from "@/components/shared/page-header"
import { TrackRecordTable } from "@/components/track-record/track-record-table"
import type { CycleRecord } from "@/components/track-record/track-record-table"
import { TrackRecordStats } from "@/components/track-record/track-record-stats"
import { serverFetch } from "@/lib/api/server"
import type { DashboardResponse } from "@/lib/api/types"

export const metadata: Metadata = {
  title: "Track Record",
  description:
    "Public ledger of Margin Invest scoring cycles and results. View historical performance, filter statistics, and survivor counts for every analysis run.",
}

interface TrackRecordData {
  cycles: CycleRecord[]
  totalScored: number
  totalCycles: number
}

async function getTrackRecordData(): Promise<TrackRecordData | null> {
  try {
    const data = await serverFetch<DashboardResponse>("/api/v1/dashboard")
    if (!data.picks || data.picks.length === 0) return null

    // Build a single cycle record from the current dashboard data.
    // As the API grows to support historical cycle endpoints, this
    // will be replaced with a dedicated /api/v1/cycles fetch.
    const topPick = data.picks.reduce(
      (best, p) => (p.score > best.score ? p : best),
      data.picks[0],
    )

    const currentCycle: CycleRecord = {
      id: `cycle-${data.last_updated}`,
      date: data.last_updated
        ? new Date(data.last_updated).toISOString().split("T")[0]
        : new Date().toISOString().split("T")[0],
      survivors: data.picks.length,
      topScorer: topPick.ticker,
      topScore: Math.round(topPick.score),
      priceChange: null, // No historical price comparison yet
    }

    return {
      cycles: [currentCycle],
      totalScored: data.total_scored ?? data.picks.length,
      totalCycles: 1,
    }
  } catch {
    return null
  }
}

export default async function TrackRecordPage() {
  const data = await getTrackRecordData()

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
        <TrackRecordStats
          totalScored={data?.totalScored}
          totalCycles={data?.totalCycles}
        />
        <TrackRecordTable cycles={data?.cycles} />
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
