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

function DrawLine({ start, end, index }: {
  start: [number, number, number]
  end: [number, number, number]
  index: number
}) {
  const groupRef = useRef<THREE.Group>(null)
  const scroll = useScroll()

  useFrame(() => {
    if (!groupRef.current) return

    const assembleProgress = scroll.range(0.32, 0.13)
    const recedeProgress = scroll.range(0.45, 0.1)

    // Each line draws after its preceding node arrives
    const lineDelay = (index + 0.5) / NODE_POSITIONS.length
    const drawProgress = Math.max(0, Math.min(1, (assembleProgress - lineDelay) * NODE_POSITIONS.length * 1.5))

    groupRef.current.visible = drawProgress > 0.01
    groupRef.current.position.z = -recedeProgress * 3

    // Animate via scale on x-axis to simulate draw effect
    groupRef.current.scale.x = drawProgress

    // Fade opacity with draw progress
    groupRef.current.traverse((child) => {
      if ((child as THREE.Line).material) {
        const mat = (child as THREE.Line).material as THREE.LineBasicMaterial
        if (mat.opacity !== undefined) {
          mat.opacity = drawProgress * 0.3
          mat.needsUpdate = true
        }
      }
    })
  })

  return (
    <group ref={groupRef}>
      <Line
        points={[start, end]}
        color="#888888"
        lineWidth={1}
        transparent
        opacity={0.3}
      />
    </group>
  )
}

export function ConnectionLines() {
  return (
    <group>
      {NODE_POSITIONS.slice(0, -1).map((start, i) => (
        <DrawLine
          key={i}
          start={start}
          end={NODE_POSITIONS[i + 1]}
          index={i}
        />
      ))}
    </group>
  )
}
