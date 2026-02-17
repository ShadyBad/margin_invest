"use client"

import { EffectComposer, Bloom, Vignette, ChromaticAberration } from "@react-three/postprocessing"
import { BlendFunction } from "postprocessing"
import { Vector2 } from "three"
import type { QualityTier } from "@/lib/hooks/use-quality-tier"

const CHROMATIC_OFFSET = new Vector2(0.001, 0.001)

interface PostprocessingStackProps {
  tier: QualityTier
}

export function PostprocessingStack({ tier }: PostprocessingStackProps) {
  if (tier === "low") return null

  return (
    <EffectComposer>
      <Bloom
        luminanceThreshold={0.8}
        luminanceSmoothing={0.3}
        intensity={0.3}
        radius={0.6}
        blendFunction={BlendFunction.ADD}
      />
      <Vignette
        offset={0.3}
        darkness={0.5}
        blendFunction={BlendFunction.NORMAL}
      />
      {tier === "high" && (
        <ChromaticAberration
          offset={CHROMATIC_OFFSET}
          blendFunction={BlendFunction.NORMAL}
        />
      )}
    </EffectComposer>
  )
}
