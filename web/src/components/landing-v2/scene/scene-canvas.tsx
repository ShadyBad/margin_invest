"use client"

import { Canvas } from "@react-three/fiber"
import { ScrollControls } from "@react-three/drei"
import { Suspense } from "react"
import { AmbientGrid } from "./ambient-grid"
import type { QualityTier } from "@/lib/hooks/use-quality-tier"

interface SceneCanvasProps {
  tier: QualityTier
  dpr: number
  pages: number
  children?: React.ReactNode
}

export function SceneCanvas({ tier, dpr, pages, children }: SceneCanvasProps) {
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
        <ScrollControls pages={pages} damping={0.15}>
          <AmbientGrid tier={tier} />
          {children}
        </ScrollControls>
      </Suspense>
    </Canvas>
  )
}
