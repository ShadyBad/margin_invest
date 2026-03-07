"use client"

import { useCallback } from "react"
import { HeroSection } from "./hero-section"
import { ProblemSection } from "./problem-section"
import { EliminationVignette } from "./elimination-vignette"
import { EngineSection } from "./engine-section"
import { ProofSection } from "./proof-section"
import { PositioningSection } from "./positioning-section"
import { DifferentiatorSection } from "./differentiator-section"
import { PricingSection } from "./pricing-section"
import { FaqSection } from "./faq-section"
import { FooterSection } from "./footer-section"
import { SectionIndicator } from "./section-indicator"
import { formatEliminationPct } from "@/lib/format-elimination-pct"
import type { HomepageData } from "./types"

interface HomepageClientProps {
  data: HomepageData | null
}

export function HomepageClient({ data }: HomepageClientProps) {
  const handleStageChange = useCallback(function noop() {
    // Pipeline chip animation removed — engine section still expects this callback
  }, [])

  return (
    <div className="relative z-10">
      <HeroSection data={data} />
      <ProblemSection />
      <EliminationVignette
        eliminatedPct={
          data && data.total_scored > 0
            ? formatEliminationPct(data.total_scored - data.eligible_count, data.total_scored)
            : undefined
        }
      />
      <ProofSection candidates={data?.allPicks ?? []} />
      <EngineSection onStageChange={handleStageChange} />
      <PositioningSection />
      <DifferentiatorSection />
      <PricingSection />
      <FaqSection />
      <FooterSection />
      <SectionIndicator />
    </div>
  )
}
