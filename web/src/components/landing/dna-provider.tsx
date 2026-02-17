"use client"

import { useEffect, type ReactNode } from "react"

export interface DNAValues {
  base: string
  mid: string
  accent: string
  density: number
  tempo: number
}

interface DNAProviderProps {
  dna?: DNAValues | null
  children: ReactNode
}

export function DNAProvider({ dna, children }: DNAProviderProps) {
  useEffect(() => {
    if (!dna) return

    const root = document.documentElement
    root.style.setProperty("--dna-base", dna.base)
    root.style.setProperty("--dna-mid", dna.mid)
    root.style.setProperty("--dna-accent", dna.accent)
    root.style.setProperty("--dna-density", String(dna.density))
    root.style.setProperty("--dna-tempo", String(dna.tempo))

    return () => {
      root.style.removeProperty("--dna-base")
      root.style.removeProperty("--dna-mid")
      root.style.removeProperty("--dna-accent")
      root.style.removeProperty("--dna-density")
      root.style.removeProperty("--dna-tempo")
    }
  }, [dna])

  return <>{children}</>
}
