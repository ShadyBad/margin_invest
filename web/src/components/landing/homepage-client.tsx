"use client"

import { HeroSection } from "./sections/hero-section"
import { EvidenceSection } from "./sections/evidence-section"
import { ComparisonSection } from "./sections/comparison-section"
import { PricingSection } from "./sections/pricing-section"
import { FooterSection } from "./sections/footer-section"
import { ScrollCanvas } from "./shared/scroll-canvas"
import type { HomepageData } from "./shared/types"

interface HomepageClientProps {
  data: HomepageData | null
}

export function HomepageClient({ data }: HomepageClientProps) {
  return (
    <ScrollCanvas>
      <HeroSection data={data} />
      <EvidenceSection
        candidates={data?.allPicks ?? []}
        totalUniverse={data?.total_universe}
        eligibleCount={data?.eligible_count}
        totalScored={data?.total_scored}
        survivingCount={data?.surviving_count}
      />
      <ComparisonSection />
      <PricingSection totalUniverse={data?.total_universe} />
      <FooterSection />
    </ScrollCanvas>
  )
}
