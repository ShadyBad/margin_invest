import { LandingScene } from "@/components/landing/scene/landing-scene"
import { Navbar } from "@/components/nav/navbar"
import { DevAnnotations } from "@/components/landing/dev-annotations"
import {
  HeroSection,
  FrictionSection,
  EngineDiagram,
  EngineProof,
  CapabilitiesSection,
  PricingSection,
  InvestorPositioning,
  MetricsStrip,
  FinalCTA,
} from "@/components/landing/sections"

export default function Home() {
  return (
    <main className="relative bg-bg-primary min-h-screen">
      {/* WebGL canvas — fixed behind content */}
      <LandingScene pages={8} />

      {/* HTML overlay — scrollable content */}
      <div className="relative z-10">
        <Navbar />
        <HeroSection />
        <MetricsStrip />
        <EngineDiagram />
        <FrictionSection />
        <EngineProof />
        <CapabilitiesSection />
        <PricingSection />
        <InvestorPositioning />
        <FinalCTA />
        <DevAnnotations />
      </div>
    </main>
  )
}
