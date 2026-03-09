"use client"

import { HeroSection } from "./hero-section"
import { AuthorityStrip } from "./authority-strip"
import { EvidenceSection } from "./evidence-section"
import { HowItWorksSection } from "./how-it-works-section"
import { ResultsShowcaseSection } from "./results-showcase-section"
import { PillarsSection } from "./pillars-section"
import { PricingSection } from "./pricing-section"
import { FaqSection } from "./faq-section"
import { FooterSection } from "./footer-section"
import { ScrollCanvas } from "./scroll-canvas"
import type { HomepageData } from "./types"

interface HomepageClientProps {
  data: HomepageData | null
}

export function HomepageClient({ data }: HomepageClientProps) {
  return (
    <ScrollCanvas>
      <HeroSection data={data} />
      <AuthorityStrip />
      <EvidenceSection candidates={data?.allPicks ?? []} />
      <HowItWorksSection data={data} />
      <ResultsShowcaseSection data={data} />
      <PillarsSection data={data} />
      <PricingSection totalUniverse={data?.total_universe} />
      <FaqSection />
      <FooterSection />
    </ScrollCanvas>
  )
}
