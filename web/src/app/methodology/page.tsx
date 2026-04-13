import type { Metadata } from "next"
import { Navbar } from "@/components/nav/navbar"
import { PageHeader } from "@/components/shared/page-header"
import { MethodologyProgressDots } from "@/components/methodology/progress-dots"
import {
  PipelineSection,
  UniverseSection,
  FiltersSection,
  ScoringSection,
  ConvictionSection,
  MLRefinementSection,
  SmartMoneySection,
  OutputsSection,
  UsageSection,
  TransparencySection,
  CTASection,
} from "@/components/methodology"

export const metadata: Metadata = {
  title: "How It Works",
  description:
    "How Margin Invest scores every US-listed equity — a deterministic pipeline of elimination filters, multi-factor scoring across Quality, Value, and Momentum, and dual-track composite scoring.",
}

export default function MethodologyPage() {
  return (
    <main className="relative bg-bg-primary min-h-screen">
      <div className="relative z-10">
        <Navbar />
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 pt-28">
          <PageHeader
            category="METHODOLOGY"
            title="From 7,000+ stocks to the ones worth your attention."
            description="Follow one stock through our entire pipeline — every filter, every factor, every decision — to see exactly how composite scores are built."
          />
        </div>
        <MethodologyProgressDots />
        <div data-methodology-section="pipeline">
          <PipelineSection />
        </div>
        <div data-methodology-section="universe">
          <UniverseSection />
        </div>
        <div data-methodology-section="filters">
          <FiltersSection />
        </div>
        <div data-methodology-section="scoring">
          <ScoringSection />
        </div>
        <div data-methodology-section="conviction">
          <ConvictionSection />
        </div>
        <div data-methodology-section="ml">
          <MLRefinementSection />
        </div>
        <div data-methodology-section="output">
          <SmartMoneySection />
        </div>
        <OutputsSection />
        <UsageSection />
        <TransparencySection />
        <CTASection />
      </div>
    </main>
  )
}
