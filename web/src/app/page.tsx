import {
  HeroSection,
  FrictionSection,
  SystemDiagram,
  EngineProof,
  CapabilitiesSection,
  InvestorPositioning,
  FinalCTA,
} from "@/components/landing"

export default function Home() {
  return (
    <main className="bg-bg-primary min-h-screen">
      <HeroSection />
      <FrictionSection />
      <SystemDiagram />
      <EngineProof />
      <CapabilitiesSection />
      <InvestorPositioning />
      <FinalCTA />
    </main>
  )
}
