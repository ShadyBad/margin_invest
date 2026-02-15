"use client"

import { useRef, useMemo } from "react"
import { useFrame } from "@react-three/fiber"
import { useScroll } from "@react-three/drei"
import * as THREE from "three"
import type { QualityTier } from "@/lib/hooks/use-quality-tier"

interface AmbientGridProps {
  tier: QualityTier
}

export function AmbientGrid({ tier }: AmbientGridProps) {
  const groupRef = useRef<THREE.Group>(null)
  const scroll = useScroll()

  const gridSize = tier === "high" ? 40 : 20
  const divisions = tier === "high" ? 40 : 20

  const material = useMemo(
    () =>
      new THREE.LineBasicMaterial({
        color: new THREE.Color(0x888888),
        transparent: true,
        opacity: 0.04,
      }),
    []
  )

  useFrame(() => {
    if (!groupRef.current) return
    const offset = scroll.offset
    groupRef.current.position.y = offset * 2
    groupRef.current.rotation.x = -0.3 + offset * 0.1
  })

  return (
    <group ref={groupRef} position={[0, 0, -5]}>
      <gridHelper
        args={[gridSize, divisions, 0x888888, 0x888888]}
        material={material}
        rotation={[Math.PI / 2, 0, 0]}
      />
    </group>
  )
}
