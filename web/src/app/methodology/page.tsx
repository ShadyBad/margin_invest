import type { Metadata } from "next"
import { FloatingNav } from "@/components/nav/floating-nav"
import {
  MethodologyHero,
  PipelineSection,
  FactorSection,
  TransparencySection,
  MethodologyCTA,
} from "@/components/methodology"

export const metadata: Metadata = {
  title: "Methodology | Margin Invest",
  description:
    "How Margin scores equities — a deterministic pipeline from market data to composite conviction scores, using five orthogonal factors with sector-neutral percentile ranking.",
}

export default function MethodologyPage() {
  return (
    <main className="relative bg-bg-primary min-h-screen">
      <div className="relative z-10">
        <FloatingNav variant="public" />
        <MethodologyHero />
        <PipelineSection />
        <FactorSection />
        <TransparencySection />
        <MethodologyCTA />
      </div>
    </main>
  )
}
