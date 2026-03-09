"use client"

import { useCallback } from "react"
import { HeroSection } from "./hero-section"
import { ProblemSection } from "./problem-section"
import { EliminationVignette } from "./elimination-vignette"
import { EngineSection } from "./engine-section"
import { ProofSection } from "./proof-section"
import { PositioningSection } from "./positioning-section"
import { PricingSection } from "./pricing-section"
import { FaqSection } from "./faq-section"
import { FooterSection } from "./footer-section"
import { SectionIndicator } from "./section-indicator"
import { formatEliminationPct } from "@/lib/format-elimination-pct"
import type { HomepageData } from "./types"

function SectionGlow() {
  return (
    <div
      className="relative h-px w-full overflow-visible"
      style={{
        background: "linear-gradient(90deg, transparent, var(--color-accent), transparent)",
        opacity: 0.15,
      }}
    >
      <div
        className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 pointer-events-none"
        style={{
          width: "60%",
          height: "80px",
          background: "radial-gradient(ellipse, rgba(26,122,90,0.06) 0%, transparent 70%)",
        }}
      />
    </div>
  )
}

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
      <SectionGlow />
      <ProofSection candidates={data?.allPicks ?? []} />
      <EngineSection onStageChange={handleStageChange} />
      <PositioningSection />
      <SectionGlow />
      <PricingSection />
      <FaqSection />
      <FooterSection />
      <SectionIndicator />
    </div>
  )
}
