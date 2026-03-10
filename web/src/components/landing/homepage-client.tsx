"use client"

import { HeroSection } from "./sections/hero-section"
import { AuthorityStrip } from "./sections/authority-strip"
import { EvidenceSection } from "./sections/evidence-section"
import { HowItWorksSection } from "./sections/how-it-works-section"
import { ResultsShowcaseSection } from "./sections/results-showcase-section"
import { PillarsSection } from "./sections/pillars-section"
import { PricingSection } from "./sections/pricing-section"
import { FaqSection } from "./sections/faq-section"
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
      <AuthorityStrip data={data} />
      <EvidenceSection
        candidates={data?.allPicks ?? []}
        totalUniverse={data?.total_universe}
        eligibleCount={data?.eligible_count}
        totalScored={data?.total_scored}
        survivingCount={data?.surviving_count}
      />
      <HowItWorksSection data={data} />
      <ResultsShowcaseSection data={data} />
      <PillarsSection data={data} />
      <PricingSection totalUniverse={data?.total_universe} />
      <FaqSection />
      <FooterSection />
    </ScrollCanvas>
  )
}
