import { redirect } from "next/navigation"
import { auth } from "@/lib/auth"
import { AppShell } from "@/components/layout"
import { PicksGrid, WatchlistPicksList, IngestionBanner, PortfolioConviction, MarketContextSidebar } from "@/components/dashboard"
import { DashboardGreeting } from "@/components/dashboard/dashboard-greeting"
import { ProposalBanner } from "@/components/dashboard/proposal-banner"
import { serverFetch } from "@/lib/api/server"
import type { DashboardResponse, PickSummary } from "@/lib/api/types"

function computePortfolioConviction(picks: PickSummary[]): { score: number; label: string } | null {
  if (picks.length === 0) return null
  const avg = picks.reduce((sum, p) => sum + (p.score ?? p.composite_percentile), 0) / picks.length
  const score = Math.round(avg)
  const label = score >= 60 ? "Strong" : score >= 30 ? "Moderate" : "Weak"
  return { score, label }
}

export default async function DashboardPage() {
  const session = await auth()
  if (!session) {
    redirect("/login")
  }

  let data: DashboardResponse | null = null
  let apiError: string | null = null

  try {
    data = await serverFetch<DashboardResponse>("/api/v1/dashboard")
  } catch (err) {
    apiError = err instanceof Error ? err.message : "Failed to load dashboard data"
  }

  return (
    <AppShell>
      <div className="mb-10 pt-12 flex items-start justify-between">
        <DashboardGreeting
          userName={session.user?.name?.split(" ")[0] ?? ""}
          changesCount={0}
          lastUpdated={data?.last_updated ?? new Date().toISOString()}
        />
        {data?.picks && (() => {
          const conviction = computePortfolioConviction(data.picks)
          return conviction ? (
            <PortfolioConviction score={conviction.score} label={conviction.label} />
          ) : null
        })()}
      </div>

      <div className="flex gap-8">
        <MarketContextSidebar
          pickCount={data?.picks?.length ?? 0}
          totalScored={data?.total_scored ?? null}
          universeSize={data?.universe?.size ?? null}
          engineVersion={data?.universe?.version}
          lastScoringRun={data?.universe?.last_scoring_run}
        />
        <div className="flex-1 min-w-0">
          <ProposalBanner />

          {apiError && (
            <div className="rounded-lg border border-warning/30 bg-warning/10 p-4 mb-8">
              <p className="text-sm text-warning">
                Unable to reach the API server. Start it with:{" "}
                <code className="bg-bg-subtle px-1.5 py-0.5 rounded text-xs">
                  uvicorn margin_api.app:create_app --factory
                </code>
              </p>
            </div>
          )}

          {data?.universe && !data.universe.is_complete && (
            <IngestionBanner universe={data.universe} warnings={data.warnings} />
          )}

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
            <PicksGrid
              picks={data?.picks ?? []}
              totalScored={data?.total_scored}
              universeSize={data?.universe?.size}
            />
          </section>

          {(data?.watchlist?.length ?? 0) > 0 && (
            <section>
              <h2 className="text-lg font-semibold text-text-primary mb-4">
                Watchlist Picks
              </h2>
              <WatchlistPicksList items={data!.watchlist} />
            </section>
          )}
        </div>
      </div>
    </AppShell>
  )
}
