import { redirect } from "next/navigation"
import { auth } from "@/lib/auth"
import { serverFetch } from "@/lib/api/server"
import { AppShell } from "@/components/layout/app-shell"
import { AssetDetailView } from "@/components/asset-detail"
import type { ScoreResponse, ScoreHistoryResponse } from "@/lib/api/types"

interface AssetDetailPageProps {
  params: Promise<{ ticker: string }>
}

export default async function AssetDetailPage({ params }: AssetDetailPageProps) {
  const { ticker } = await params
  const session = await auth()
  if (!session) redirect("/login")

  const upperTicker = ticker.toUpperCase()

  let scoreData: ScoreResponse | null = null
  let historyData: ScoreHistoryResponse | null = null
  let apiError: string | null = null

  try {
    const [scoreResult, historyResult] = await Promise.allSettled([
      serverFetch<ScoreResponse>(
        `/api/v1/scores/${upperTicker}?include=price_history,signal_history`
      ),
      serverFetch<ScoreHistoryResponse>(
        `/api/v1/scores/${upperTicker}/history?limit=30`
      ),
    ])

    if (scoreResult.status === "fulfilled") scoreData = scoreResult.value
    else apiError = scoreResult.reason?.message ?? "Failed to load score"

    if (historyResult.status === "fulfilled") historyData = historyResult.value
  } catch (err) {
    apiError = err instanceof Error ? err.message : "Failed to load data"
  }

  return (
    <AppShell>
      <div className="max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8">
        <AssetDetailView
          ticker={upperTicker}
          scoreData={scoreData}
          historyData={historyData}
          apiError={apiError}
          totalScored={scoreData?.total_scored ?? undefined}
          filtersSurvivedCount={scoreData?.filters_survived_count ?? undefined}
          sectorSurvivorCount={scoreData?.sector_survivor_count ?? undefined}
          sectorName={scoreData?.sector ?? undefined}
        />
      </div>
    </AppShell>
  )
}
