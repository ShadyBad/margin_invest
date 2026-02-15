"use client"

import dynamic from "next/dynamic"

const WebGLScene = dynamic(
  () => import("./webgl-scene").then((mod) => ({ default: mod.WebGLScene })),
  { ssr: false }
)

interface LandingSceneProps {
  pages: number
}

export function LandingScene({ pages }: LandingSceneProps) {
  return <WebGLScene pages={pages} />
}
