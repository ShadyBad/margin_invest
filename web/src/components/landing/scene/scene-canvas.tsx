"use client"

import { Canvas } from "@react-three/fiber"
import { ScrollControls } from "@react-three/drei"
import { Suspense } from "react"
import { AmbientGrid } from "./ambient-grid"
import { EngineNodes } from "./engine-nodes"
import { ConnectionLines } from "./connection-lines"
import { CapabilityCards3D } from "./capability-cards-3d"
import type { QualityTier } from "@/lib/hooks/use-quality-tier"

interface SceneCanvasProps {
  tier: QualityTier
  dpr: number
  pages: number
}

export function SceneCanvas({ tier, dpr, pages }: SceneCanvasProps) {
  return (
    <Canvas
      dpr={[1, dpr]}
      frameloop="demand"
      gl={{ antialias: tier === "high", alpha: true, powerPreference: "high-performance" }}
      camera={{ position: [0, 0, 10], fov: 50 }}
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        width: "100vw",
        height: "100vh",
        zIndex: 0,
        pointerEvents: "none",
      }}
    >
      <Suspense fallback={null}>
        <ambientLight intensity={0.5} />
        <pointLight position={[5, 5, 5]} intensity={0.3} />
        <ScrollControls pages={pages} damping={0.15}>
          <AmbientGrid tier={tier} />
          <EngineNodes tier={tier} />
          <ConnectionLines />
          <CapabilityCards3D />
        </ScrollControls>
      </Suspense>
    </Canvas>
  )
}
