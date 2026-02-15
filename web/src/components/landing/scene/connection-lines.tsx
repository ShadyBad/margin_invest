"use client"

import { useRef } from "react"
import { useFrame } from "@react-three/fiber"
import { useScroll, Line } from "@react-three/drei"
import * as THREE from "three"

const NODE_POSITIONS: [number, number, number][] = [
  [-4.5, 0, 0],
  [-1.5, 0, 0],
  [1.5, 0, 0],
  [4.5, 0, 0],
]

export function ConnectionLines() {
  const scroll = useScroll()
  const groupRef = useRef<THREE.Group>(null)

  useFrame(() => {
    if (!groupRef.current) return
    const assembleProgress = scroll.range(0.3, 0.2)
    const recedeProgress = scroll.range(0.5, 0.1)
    groupRef.current.visible = assembleProgress > 0.1
    groupRef.current.position.z = -recedeProgress * 3
  })

  return (
    <group ref={groupRef}>
      {NODE_POSITIONS.slice(0, -1).map((start, i) => (
        <Line
          key={i}
          points={[start, NODE_POSITIONS[i + 1]]}
          color="#888888"
          lineWidth={1}
          transparent
          opacity={0.3}
        />
      ))}
    </group>
  )
}
