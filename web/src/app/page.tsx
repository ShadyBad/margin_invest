import dynamic from "next/dynamic"
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

const WebGLScene = dynamic(
  () => import("@/components/landing/scene/webgl-scene").then((mod) => ({ default: mod.WebGLScene })),
  { ssr: false }
)

const EngineNodes = dynamic(
  () => import("@/components/landing/scene/engine-nodes").then((mod) => ({ default: mod.EngineNodes })),
  { ssr: false }
)

const ConnectionLines = dynamic(
  () => import("@/components/landing/scene/connection-lines").then((mod) => ({ default: mod.ConnectionLines })),
  { ssr: false }
)

const CapabilityCards3D = dynamic(
  () => import("@/components/landing/scene/capability-cards-3d").then((mod) => ({ default: mod.CapabilityCards3D })),
  { ssr: false }
)

export default function Home() {
  return (
    <main className="relative bg-bg-primary min-h-screen">
      {/* WebGL canvas — fixed behind content */}
      <WebGLScene pages={7}>
        <EngineNodes tier="high" />
        <ConnectionLines />
        <CapabilityCards3D />
      </WebGLScene>

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
