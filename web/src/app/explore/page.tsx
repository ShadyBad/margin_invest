import type { Metadata } from "next"
import { serverFetch } from "@/lib/api/server"
import { ExploreClient } from "@/components/explore/explore-client"

export const metadata: Metadata = {
  title: "Explore Top Picks",
  description:
    "Browse the highest-scoring US equities from this scoring cycle. Every score is sector-neutral, deterministic, and auditable.",
}

interface ScoreListResponse {
  scores: Array<{
    ticker: string
    name: string
    sector?: string | null
    composite_percentile: number
    composite_tier: string
  }>
  total: number
  page: number
  page_size: number
}

async function getTopPicks(): Promise<ScoreListResponse> {
  try {
    return await serverFetch<ScoreListResponse>(
      "/api/v1/scores?page=1&page_size=20&min_percentile=70"
    )
  } catch {
    return { scores: [], total: 0, page: 1, page_size: 20 }
  }
}

export default async function ExplorePage() {
  const data = await getTopPicks()

  return (
    <div className="min-h-screen bg-bg-primary">
      <div className="max-w-4xl mx-auto px-6 py-16">
        <div className="text-center mb-12">
          <h1 className="text-[32px] md:text-[40px] font-bold text-text-primary tracking-tight mb-3">
            This Week&apos;s Top Picks
          </h1>
          <p className="text-body text-text-secondary max-w-lg mx-auto">
            The highest-scoring equities from our latest scoring cycle. Every score is
            sector-neutral, deterministic, and auditable to the formula.
          </p>
        </div>
        <ExploreClient initialData={data} />
      </div>
    </div>
  )
}
