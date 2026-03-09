"use client"

import { HeroSection } from "./hero-section"
import { AuthorityStrip } from "./authority-strip"
import { EvidenceSection } from "./evidence-section"
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
      <HeroSection
        data={data}
        totalUniverse={data?.total_universe ?? 3056}
        survivingCount={data?.surviving_count ?? 0}
      />
      <AuthorityStrip />
      <EvidenceSection candidates={data?.allPicks ?? []} />
      <PricingSection />
      <FaqSection />
      <FooterSection />
    </ScrollCanvas>
  )
}
