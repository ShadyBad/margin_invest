"use client"

import { HeroSection } from "./hero-section"
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
      <PricingSection />
      <FaqSection />
      <FooterSection />
    </div>
  )
}
