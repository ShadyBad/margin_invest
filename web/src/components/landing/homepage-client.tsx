"use client"

import { HeroSection } from "./hero-section"
import { AuthorityStrip } from "./authority-strip"
import { EvidenceSection } from "./evidence-section"
import { PricingSection } from "./pricing-section"
import { FaqSection } from "./faq-section"
import { FooterSection } from "./footer-section"
import type { HomepageData } from "./types"

interface HomepageClientProps {
  data: HomepageData | null
}

export function HomepageClient({ data }: HomepageClientProps) {
  return (
    <div className="relative z-10">
      <HeroSection data={data} />
      <AuthorityStrip />
      <EvidenceSection candidates={data?.allPicks ?? []} />
      <PricingSection />
      <FaqSection />
      <FooterSection />
    </div>
  )
}
