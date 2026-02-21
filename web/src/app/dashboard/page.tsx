import { redirect } from "next/navigation"
import { auth } from "@/lib/auth"
import { AppShell } from "@/components/layout"
import { PicksGrid, WatchlistPicksList, IngestionBanner, PortfolioConviction, CorrelationHeatmap } from "@/components/dashboard"
import { serverFetch } from "@/lib/api/server"
import type { DashboardResponse, PickSummary } from "@/lib/api/types"

function formatLastUpdated(isoString: string): string {
  const date = new Date(isoString)
  return date.toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  })
}

function computePortfolioConviction(picks: PickSummary[]): { score: number; label: string } | null {
  if (picks.length === 0) return null
  const avg = picks.reduce((sum, p) => sum + (p.score ?? p.composite_percentile), 0) / picks.length
  const score = Math.round(avg)
  const label = score >= 60 ? "Operating" : score >= 30 ? "Building" : "Reviewing"
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
        <div>
          <h1 className="text-2xl font-bold text-text-primary">Dashboard</h1>
          {data?.last_updated && (
            <p className="text-sm text-text-secondary mt-1">
              Last updated: {formatLastUpdated(data.last_updated)}
            </p>
          )}
        </div>
        {data?.picks && (() => {
          const conviction = computePortfolioConviction(data.picks)
          return conviction ? (
            <PortfolioConviction score={conviction.score} label={conviction.label} />
          ) : null
        })()}
      </div>

      {apiError && (
        <div className="rounded-lg border border-yellow-600/30 bg-yellow-950/20 p-4 mb-8">
          <p className="text-sm text-yellow-400">
            Unable to reach the API server. Start it with:{" "}
            <code className="bg-surface-secondary px-1.5 py-0.5 rounded text-xs">
              uvicorn margin_api.app:create_app --factory
            </code>
          </p>
        </div>
      )}

      {data?.universe && (
        <IngestionBanner universe={data.universe} warnings={data.warnings} />
      )}

      <section className="mb-10">
        <h2 className="text-lg font-semibold text-text-primary mb-4">
          Top Picks
        </h2>
        <PicksGrid picks={data?.picks ?? []} />
      </section>

      <section className="mb-10">
        <CorrelationHeatmap />
      </section>

      {(data?.watchlist?.length ?? 0) > 0 && (
        <section>
          <h2 className="text-lg font-semibold text-text-primary mb-4">
            Watchlist Picks
          </h2>
          <WatchlistPicksList items={data!.watchlist} />
        </section>
      )}
    </AppShell>
  )
}
