import { LandingScene } from "@/components/landing/scene/landing-scene"
import { NavMinimal } from "@/components/landing/nav-minimal"
import { DevAnnotations } from "@/components/landing/dev-annotations"
import {
  HeroSection,
  FrictionSection,
  EngineDiagram,
  EngineProof,
  CapabilitiesSection,
  InvestorPositioning,
  FinalCTA,
} from "@/components/landing/sections"

export default function Home() {
  return (
    <main className="relative bg-bg-primary min-h-screen">
      {/* WebGL canvas — fixed behind content */}
      <LandingScene pages={7} />

      {/* HTML overlay — scrollable content */}
      <div className="relative z-10">
        <NavMinimal />
        <HeroSection />
        <FrictionSection />
        <EngineDiagram />
        <EngineProof />
        <CapabilitiesSection />
        <InvestorPositioning />
        <FinalCTA />
        <DevAnnotations />
      </div>
    </main>
  )
}
