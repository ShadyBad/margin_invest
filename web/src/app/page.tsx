import { Navbar } from "@/components/nav/navbar"
import { serverFetch } from "@/lib/api/server"
import { HomepageClient } from "@/components/landing/homepage-client"
import type { DashboardResponse } from "@/lib/api/types"
import type { HomepageData, CandidateCard } from "@/components/landing/types"

function toCandidateCard(pick: DashboardResponse["picks"][0]): CandidateCard {
  return {
    ticker: pick.ticker,
    name: pick.name,
    sector: pick.sector ?? "Unknown",
    actual_price: pick.actual_price ?? 0,
    buy_price: pick.buy_price ?? 0,
    margin_of_safety: pick.margin_of_safety ?? 0,
    composite_percentile: pick.composite_percentile,
    conviction_level: pick.conviction_level,
    quality_percentile: pick.quality_percentile,
    value_percentile: pick.value_percentile,
    momentum_percentile: pick.momentum_percentile,
    sentiment_percentile: pick.sentiment_percentile ?? 0,
    growth_percentile: pick.growth_percentile ?? 0,
    scored_at: pick.scored_at ?? new Date().toISOString(),
    filters_passed: 8,
    filters_total: 8,
  }
}

async function getHomepageData(): Promise<HomepageData | null> {
  try {
    const data = await serverFetch<DashboardResponse>("/api/v1/dashboard")
    if (!data.picks || data.picks.length === 0) return null
    const allCards = data.picks.map(toCandidateCard)
    return {
      candidates: allCards.slice(0, 5),
      allPicks: allCards,
      last_updated: data.last_updated,
      universe_size: data.universe?.size ?? 0,
      eligible_count: data.total_scored,
      total_scored: data.total_scored,
    }
  } catch {
    return null
  }
}

export default async function Home() {
  const data = await getHomepageData()

  return (
    <main>
      <Navbar />
      <HomepageClient data={data} />
    </main>
  )
}
