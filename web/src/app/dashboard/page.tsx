import { redirect } from "next/navigation"
import { auth } from "@/lib/auth"
import { AppShell } from "@/components/layout"
import { PicksGrid, WatchlistPicksList, IngestionBanner, RecentChanges } from "@/components/dashboard"
import { DashboardGreeting } from "@/components/dashboard/dashboard-greeting"
import { PortfolioConviction } from "@/components/dashboard/portfolio-conviction"
import { ProposalBanner } from "@/components/dashboard/proposal-banner"
import { SystemStatusStrip } from "@/components/dashboard/system-status-strip"
import { MarketContextPanel } from "@/components/dashboard/market-context-panel"
import { SkeletonCard } from "@/components/ui"
import { serverFetch } from "@/lib/api/server"
import type { DashboardResponse, PickSummary } from "@/lib/api/types"
import fallbackSnapshot from "@/data/fallback-scoring-snapshot.json"

function computePortfolioConviction(picks: PickSummary[]): { score: number; label: string } | null {
  if (picks.length === 0) return null
  const avg = picks.reduce((sum, p) => sum + (p.score ?? p.composite_percentile), 0) / picks.length
  const score = Math.round(avg)
  const label = score >= 60 ? "Strong" : score >= 30 ? "Moderate" : "Weak"
  return { score, label }
}

/** Build a DashboardResponse from the static fallback snapshot for offline use */
function buildFallbackData(): DashboardResponse {
  const snapshot = fallbackSnapshot as {
    allPicks: Array<{
      ticker: string
      name: string
      score: number
      composite_percentile: number
      composite_tier: string
      quality_percentile: number
      value_percentile: number
      momentum_percentile: number
      sentiment_percentile?: number
      growth_percentile?: number
      actual_price: number | null
      buy_price: number | null
      margin_of_safety?: number
      scored_at?: string
      sector?: string
    }>
    last_updated: string
    universe_size: number
    total_scored: number
    surviving_count: number
  }

  const picks: PickSummary[] = snapshot.allPicks.map((c, i) => ({
    score_id: i + 1,
    ticker: c.ticker,
    name: c.name,
    score: c.score,
    universe_percentile: c.composite_percentile,
    composite_percentile: c.composite_percentile,
    composite_tier: c.composite_tier,
    signal: c.composite_tier === "strong" ? "strong" : "stable",
    quality_percentile: c.quality_percentile,
    value_percentile: c.value_percentile,
    momentum_percentile: c.momentum_percentile,
    sentiment_percentile: c.sentiment_percentile ?? null,
    growth_percentile: c.growth_percentile ?? null,
    actual_price: c.actual_price,
    buy_price: c.buy_price,
    sell_price: null,
    price_upside: null,
    scored_at: c.scored_at,
    sector: c.sector ?? null,
  }))

  return {
    picks,
    watchlist: [],
    last_updated: snapshot.last_updated,
    total_scored: snapshot.total_scored,
    universe: {
      version: "v4",
      size: snapshot.universe_size,
      scoring_coverage: 1,
      is_complete: true,
      last_scoring_run: snapshot.last_updated,
    },
  }
}

export default async function DashboardPage() {
  const session = await auth()
  if (!session) {
    redirect("/login")
  }

  let data: DashboardResponse | null = null
  let usingFallback = false

  try {
    data = await serverFetch<DashboardResponse>("/api/v1/dashboard")
  } catch {
    // API unreachable — use fallback data
    data = buildFallbackData()
    usingFallback = true
  }

  const conviction = data?.picks ? computePortfolioConviction(data.picks) : null

  return (
    <AppShell>
      {/* Greeting + Portfolio Score */}
      <div className="mb-6 pt-12 flex items-start justify-between">
        <DashboardGreeting
          userName={session.user?.name?.split(" ")[0] ?? ""}
          changesCount={0}
          lastUpdated={data?.last_updated ?? new Date().toISOString()}
        />
        {conviction && (
          <PortfolioConviction score={conviction.score} label={conviction.label} />
        )}
      </div>

      {/* Zone 1: System Status Strip */}
      <SystemStatusStrip data={usingFallback ? null : data} />

      {/* Fallback notice */}
      {usingFallback && (
        <div
          className="mt-4 rounded-lg border border-border-subtle bg-bg-elevated p-3 flex items-center gap-3"
          data-testid="fallback-notice"
        >
          <svg className="w-5 h-5 text-text-tertiary flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <p className="text-xs text-text-secondary">
            Showing cached data. Scores will update when the engine reconnects.
          </p>
        </div>
      )}

      {/* Zone 2: Main Content + Side Panel */}
      <div className="flex gap-8 mt-6">
        {/* Left: Main content */}
        <div className="flex-1 min-w-0">
          <ProposalBanner />

          {data?.universe && !data.universe.is_complete && (
            <IngestionBanner universe={data.universe} warnings={data.warnings} />
          )}

          {/* Top Picks section */}
          <section className="mb-10">
            <h2 className="text-lg font-semibold text-text-primary mb-4">
              Top Picks
            </h2>
            {(data?.picks?.length ?? 0) > 0 && (data?.picks?.length ?? 0) <= 5 && data?.total_scored && (
              <p className="text-xs text-text-tertiary mb-4">
                Only {data.picks.length} stock{data.picks.length !== 1 ? "s" : ""} survived
                all filters and scored above the conviction threshold.{" "}
                {data.total_scored} stocks were evaluated.
              </p>
            )}
            {data ? (
              <PicksGrid
                picks={data.picks ?? []}
                totalScored={data.total_scored}
                universeSize={data.universe?.size}
              />
            ) : (
              <DashboardLoadingSkeleton />
            )}
          </section>

          {/* Recent Changes section */}
          <section className="mb-10">
            <h2 className="text-lg font-semibold text-text-primary mb-4">
              Recent Changes
            </h2>
            <div className="border border-border-subtle rounded-lg bg-bg-elevated p-4">
              <RecentChanges changes={[]} />
            </div>
          </section>

          {/* Watchlist section */}
          {(data?.watchlist?.length ?? 0) > 0 && (
            <section>
              <h2 className="text-lg font-semibold text-text-primary mb-4">
                Watchlist Picks
              </h2>
              <WatchlistPicksList items={data!.watchlist} />
            </section>
          )}
        </div>

        {/* Right: Market Context Panel */}
        <MarketContextPanel data={data} />
      </div>
    </AppShell>
  )
}

/** Loading skeleton for the picks grid */
function DashboardLoadingSkeleton() {
  return (
    <div
      className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4"
      data-testid="dashboard-loading-skeleton"
    >
      {Array.from({ length: 6 }).map((_, i) => (
        <SkeletonCard key={i} />
      ))}
    </div>
  )
}
