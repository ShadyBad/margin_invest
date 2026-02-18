import type { Metadata } from "next"
import { Navbar } from "@/components/nav/navbar"
import {
  ProblemSection,
  ApproachSection,
  EngineSection,
  OutputsSection,
  WhySection,
  TrustSection,
  MethodologyCTA,
} from "@/components/methodology"

export const metadata: Metadata = {
  title: "Methodology | Margin Invest",
  description:
    "How Margin scores equities — a deterministic pipeline from market data to composite conviction scores, using quality, value, and momentum factors with sector-neutral percentile ranking.",
}

export default function MethodologyPage() {
  return (
    <main className="relative bg-bg-primary min-h-screen">
      <div className="relative z-10">
        <Navbar />
        <ProblemSection />
        <ApproachSection />
        <EngineSection />
        <OutputsSection />
        <WhySection />
        <TrustSection />
        <MethodologyCTA />
      </div>
    </main>
  )
}
