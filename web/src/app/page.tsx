import type { Metadata } from "next"
import { Navbar } from "@/components/nav/navbar"
import { serverFetch } from "@/lib/api/server"
import { HomepageClient } from "@/components/landing/homepage-client"
import type { DashboardResponse } from "@/lib/api/types"
import type { HomepageData, CandidateCard } from "@/components/landing/shared/types"
import fallbackSnapshot from "@/data/fallback-scoring-snapshot.json"

export const metadata: Metadata = {
  title: "Margin Invest — Discipline. Engineered.",
  description:
    "3,000+ US equities filtered to the ones worth your capital. Six forensic elimination filters, five-factor scoring, every formula auditable. No opinions, no overrides.",
  alternates: {
    canonical: "https://www.margin-invest.com",
  },
}

function toCandidateCard(pick: DashboardResponse["picks"][0]): CandidateCard {
  return {
    ticker: pick.ticker,
    name: pick.name,
    sector: pick.sector ?? "Unknown",
    actual_price: pick.actual_price ?? 0,
    buy_price: pick.buy_price ?? 0,
    margin_of_safety: pick.margin_of_safety ?? 0,
    score: pick.score,
    composite_percentile: pick.composite_percentile,
    composite_tier: pick.composite_tier,
    quality_percentile: pick.quality_percentile,
    value_percentile: pick.value_percentile,
    momentum_percentile: pick.momentum_percentile,
    sentiment_percentile: pick.sentiment_percentile ?? null,
    growth_percentile: pick.growth_percentile ?? null,
    scored_at: pick.scored_at ?? new Date().toISOString(),
    filters_passed: 8,
    filters_total: 8,
  }
}


async function getHomepageData(): Promise<HomepageData | null> {
  try {
    const data = await serverFetch<DashboardResponse>("/api/v1/dashboard")
    if (!data.picks || data.picks.length === 0) return null
    const pickCards = data.picks.map(toCandidateCard)
    return {
      candidates: pickCards.slice(0, 5),
      allPicks: pickCards,
      last_updated: data.last_updated,
      universe_size: data.universe?.size ?? 0,
      eligible_count: data.picks.length,
      total_scored: data.total_scored,
      total_universe: data.universe?.size ?? 3056,
      surviving_count:
        (data.universe && "surviving" in data.universe)
          ? Number((data.universe as unknown as Record<string, unknown>).surviving)
          : data.picks.length,
    }
  } catch {
    return {
      ...(fallbackSnapshot as unknown as HomepageData),
      isFallback: true,
    }
  }
}

export default async function Home() {
  const data = await getHomepageData()

  const jsonLd = {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "Organization",
        name: "Margin Invest",
        url: "https://www.margin-invest.com",
        logo: "https://www.margin-invest.com/icon.svg",
        description:
          "Deterministic investment analysis platform scoring 3,000+ US equities using forensic elimination filters and multi-factor analysis.",
        sameAs: [],
      },
      {
        "@type": "WebApplication",
        name: "Margin Invest",
        url: "https://www.margin-invest.com",
        applicationCategory: "FinanceApplication",
        operatingSystem: "Web",
        offers: [
          {
            "@type": "Offer",
            name: "Scout",
            price: "0",
            priceCurrency: "USD",
            description: "Free tier with composite scores and 1 forensic report per month",
          },
          {
            "@type": "Offer",
            name: "Analyst",
            price: "19",
            priceCurrency: "USD",
            priceSpecification: { "@type": "UnitPriceSpecification", billingDuration: "P1M" },
            description:
              "Unlimited forensic reports, 90-day history, score alerts, sector comparison",
          },
          {
            "@type": "Offer",
            name: "Portfolio",
            price: "49",
            priceCurrency: "USD",
            priceSpecification: { "@type": "UnitPriceSpecification", billingDuration: "P1M" },
            description:
              "Full history, correlation analysis, 13F tracking, API access, priority support",
          },
        ],
      },
    ],
  }

  return (
    <main>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
      <Navbar />
      <HomepageClient data={data} />
    </main>
  )
}
