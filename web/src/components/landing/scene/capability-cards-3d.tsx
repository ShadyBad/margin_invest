"use client"

import { useRef } from "react"
import { useFrame } from "@react-three/fiber"
import { useScroll, Edges } from "@react-three/drei"
import * as THREE from "three"

const CARD_COUNT = 4

const CARD_TARGETS: { pos: [number, number, number]; rot: [number, number, number] }[] = [
  { pos: [-3, 1.5, 0], rot: [0, 0.08, 0.03] },
  { pos: [3, 0.5, -0.3], rot: [0, -0.1, -0.02] },
  { pos: [-1, -0.8, -0.1], rot: [0, 0.05, 0.04] },
  { pos: [3.5, -2, -0.4], rot: [0, -0.07, -0.03] },
]

function CapabilityCard({ index }: { index: number }) {
  const ref = useRef<THREE.Mesh>(null)
  const scroll = useScroll()
  const target = CARD_TARGETS[index]

  useFrame(() => {
    if (!ref.current) return

    const floatIn = scroll.range(0.6, 0.15)
    const settle = scroll.range(0.75, 0.15)

    const stagger = Math.max(0, Math.min(1, (floatIn * CARD_COUNT - index) * 1.5))

    ref.current.position.set(
      THREE.MathUtils.lerp(0, target.pos[0], stagger),
      THREE.MathUtils.lerp(-10 + index * -1, target.pos[1], stagger),
      THREE.MathUtils.lerp(-2, target.pos[2], stagger)
    )

    ref.current.rotation.set(
      THREE.MathUtils.lerp(0.2, target.rot[0], stagger),
      THREE.MathUtils.lerp(0.5, target.rot[1], stagger),
      THREE.MathUtils.lerp(0.1, target.rot[2], stagger)
    )

    const scale = THREE.MathUtils.lerp(0.01, 1, stagger) * (1 - settle * 0.3)
    ref.current.scale.set(2.5 * scale, 1.5 * scale, 0.02)

    ref.current.visible = stagger > 0.01
  })

  return (
    <mesh ref={ref}>
      <planeGeometry args={[1, 1]} />
      <meshStandardMaterial
        color="#888888"
        transparent
        opacity={0.15}
        side={THREE.DoubleSide}
        roughness={0.9}
      />
      <Edges threshold={15} color="#1C7A5A" scale={1} lineWidth={0.5}>
        <lineBasicMaterial transparent opacity={0.2} />
      </Edges>
    </mesh>
  )
}

export function CapabilityCards3D() {
  return (
    <group>
      {Array.from({ length: CARD_COUNT }, (_, i) => (
        <CapabilityCard key={i} index={i} />
      ))}
    </group>
  )
}
