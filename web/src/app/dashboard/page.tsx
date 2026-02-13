"use client"

import { useEffect, useState } from "react"
import { AppShell } from "@/components/layout"
import { PicksGrid, WatchlistTable } from "@/components/dashboard"
import { SkeletonCard } from "@/components/ui"
import { getDashboard } from "@/lib/api/dashboard"
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

export default function DashboardPage() {
  const [data, setData] = useState<DashboardResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    async function fetchData() {
      try {
        setLoading(true)
        setError(null)
        const response = await getDashboard()
        if (!cancelled) {
          setData(response)
        }
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof Error ? err.message : "Failed to load dashboard",
          )
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }

    fetchData()
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <AppShell>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-text-primary">Dashboard</h1>
        {data?.last_updated && (
          <p className="text-sm text-text-secondary mt-1">
            Last updated: {formatLastUpdated(data.last_updated)}
          </p>
        )}
      </div>

      {loading && (
        <div
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
          data-testid="loading-skeleton"
        >
          {Array.from({ length: 6 }).map((_, i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
      )}

      {error && (
        <div className="bg-bearish/10 border border-bearish/30 rounded-xl p-4 text-bearish">
          {error}
        </div>
      )}

      {!loading && !error && data && (
        <>
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
        </>
      )}
    </AppShell>
  )
}
