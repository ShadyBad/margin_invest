"use client"

import dynamic from "next/dynamic"

const FluidShader = dynamic(
  () => import("@/components/landing/fluid-shader").then((m) => ({ default: m.FluidShader })),
  { ssr: false },
)

interface FluidShaderLoaderProps {
  baseColor?: string
  midColor?: string
  accentColor?: string
  tempo?: number
  density?: number
}

export function FluidShaderLoader(props: FluidShaderLoaderProps) {
  return <FluidShader {...props} />
}
