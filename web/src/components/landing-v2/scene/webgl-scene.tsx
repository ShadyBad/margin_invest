"use client"

import dynamic from "next/dynamic"
import { useQualityTier } from "@/lib/hooks/use-quality-tier"

const SceneCanvas = dynamic(
  () => import("./scene-canvas").then((mod) => ({ default: mod.SceneCanvas })),
  { ssr: false }
)

interface WebGLSceneProps {
  pages: number
  children?: React.ReactNode
}

export function WebGLScene({ pages, children }: WebGLSceneProps) {
  const { tier, dpr, enableWebGL } = useQualityTier()

  if (!enableWebGL) return null

  return (
    <SceneCanvas tier={tier} dpr={dpr} pages={pages}>
      {children}
    </SceneCanvas>
  )
}
