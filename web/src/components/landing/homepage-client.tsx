"use client"

import { useState, useCallback } from "react"
import { HeroSection } from "./hero-section"
import { ProblemSection } from "./problem-section"
import { EliminationVignette } from "./elimination-vignette"
import { PipelineChips } from "./pipeline-chips"
import { EngineSection } from "./engine-section"
import { ProofSection } from "./proof-section"
import { PositioningSection } from "./positioning-section"
import { DifferentiatorSection } from "./differentiator-section"
import { PricingSection } from "./pricing-section"
import { FaqSection } from "./faq-section"
import { InfrastructureSection } from "./infrastructure-section"
import { FooterSection } from "./footer-section"
import { SectionIndicator } from "./section-indicator"
import { formatEliminationPct } from "@/lib/format-elimination-pct"
import type { HomepageData } from "./types"

interface HomepageClientProps {
  data: HomepageData | null
}

export function HomepageClient({ data }: HomepageClientProps) {
  const [activeStage, setActiveStage] = useState(0)
  const handleStageChange = useCallback((stage: number) => setActiveStage(stage), [])

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
      <PipelineChips activeStage={activeStage} />
      <EngineSection onStageChange={handleStageChange} />
      <PositioningSection />
      <DifferentiatorSection />
      <PricingSection />
      <FaqSection />
      <InfrastructureSection />
      <FooterSection />
      <SectionIndicator />
    </div>
  )
}
