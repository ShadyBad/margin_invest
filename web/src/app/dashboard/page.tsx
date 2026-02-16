import { redirect } from "next/navigation"
import { auth } from "@/lib/auth"
import { AppShell } from "@/components/layout"
import { PicksGrid, WatchlistTable, IngestionBanner } from "@/components/dashboard"
import { serverFetch } from "@/lib/api/server"
import type { DashboardResponse } from "@/lib/api/types"

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

export default async function DashboardPage() {
  const session = await auth()
  if (!session) {
    redirect("/login")
  }

  const data = await serverFetch<DashboardResponse>("/api/v1/dashboard")

  return (
    <AppShell>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-text-primary">Dashboard</h1>
        {data.last_updated && (
          <p className="text-sm text-text-secondary mt-1">
            Last updated: {formatLastUpdated(data.last_updated)}
          </p>
        )}
      </div>

      {data.universe && (
        <IngestionBanner universe={data.universe} warnings={data.warnings} />
      )}

      <section className="mb-10">
        <h2 className="text-lg font-semibold text-text-primary mb-4">
          Top Picks
        </h2>
        <PicksGrid picks={data.picks} />
      </section>

      {data.watchlist.length > 0 && (
        <section>
          <h2 className="text-lg font-semibold text-text-primary mb-4">
            Watchlist
          </h2>
          <WatchlistTable items={data.watchlist} />
        </section>
      )}
    </AppShell>
  )
}
