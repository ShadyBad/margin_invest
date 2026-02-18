import { Navbar } from "@/components/nav/navbar"
import { HeroSection } from "@/components/landing/hero-section"
import { ProblemSection } from "@/components/landing/problem-section"
import { EngineSection } from "@/components/landing/engine-section"
import { ProofSection } from "@/components/landing/proof-section"
import { PositioningSection } from "@/components/landing/positioning-section"
import { PricingSection } from "@/components/landing/pricing-section"
import { LegitimacyStrip } from "@/components/landing/legitimacy-strip"
import { FooterInstitutional } from "@/components/landing/footer-institutional"
import { SectionIndicator } from "@/components/landing/section-indicator"
import { serverFetch } from "@/lib/api/server"

interface PickSummary {
  ticker: string
  name: string
  actual_price: number | null
  buy_price: number | null
  margin_of_safety: number | null
  composite_percentile: number
  quality_percentile: number
  value_percentile: number
  momentum_percentile: number
  scored_at: string | null
  sector: string | null
}

interface DashboardResponse {
  picks: PickSummary[]
}

async function getTopPick(): Promise<PickSummary | null> {
  try {
    const data = await serverFetch<DashboardResponse>("/api/v1/dashboard")
    return data.picks[0] ?? null
  } catch {
    return null
  }
}

export default async function Home() {
  const topPick = await getTopPick()

  return (
    <main>
      <Navbar />
      <div className="relative z-10">
        <HeroSection pick={topPick} />
        <ProblemSection />
        <EngineSection />
        <ProofSection pick={topPick} />
        <PositioningSection />
        <PricingSection />
        <LegitimacyStrip />
        <FooterInstitutional />
      </div>
      <SectionIndicator />
    </main>
  )
}
