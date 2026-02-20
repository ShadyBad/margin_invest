import type { Metadata } from "next"
import { Navbar } from "@/components/nav/navbar"
import {
  HeroSection,
  PipelineSection,
  UniverseSection,
  FiltersSection,
  ScoringSection,
  ConvictionSection,
  OutputsSection,
  UsageSection,
  TransparencySection,
  CTASection,
} from "@/components/methodology"

export const metadata: Metadata = {
  title: "How It Works | Margin Invest",
  description:
    "How Margin Invest scores every US-listed equity — a deterministic pipeline of elimination filters, multi-factor scoring across Quality, Value, and Momentum, and dual-track conviction ranking.",
}

export default function MethodologyPage() {
  return (
    <main className="relative bg-bg-primary min-h-screen">
      <div className="relative z-10">
        <Navbar />
        <HeroSection />
        <PipelineSection />
        <UniverseSection />
        <FiltersSection />
        <ScoringSection />
        <ConvictionSection />
        <OutputsSection />
        <UsageSection />
        <TransparencySection />
        <CTASection />
      </div>
    </main>
  )
}
