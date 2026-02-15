"use client"

import { useRef, useEffect, useMemo } from "react"
import { useFrame } from "@react-three/fiber"
import { useScroll } from "@react-three/drei"
import * as THREE from "three"

const CARD_COUNT = 4

// Staggered target positions matching the HTML staggered layout
const CARD_TARGETS: { pos: [number, number, number]; rot: [number, number, number] }[] = [
  { pos: [-3, 1.5, 0], rot: [0, 0.08, 0.03] },
  { pos: [3, 0.5, -0.3], rot: [0, -0.1, -0.02] },
  { pos: [-1, -0.8, -0.1], rot: [0, 0.05, 0.04] },
  { pos: [3.5, -2, -0.4], rot: [0, -0.07, -0.03] },
]

export function CapabilityCards3D() {
  const meshRef = useRef<THREE.InstancedMesh>(null)
  const scroll = useScroll()
  const tempObj = useMemo(() => new THREE.Object3D(), [])

  useEffect(() => {
    if (!meshRef.current) return
    for (let i = 0; i < CARD_COUNT; i++) {
      tempObj.position.set(0, -10, 0)
      tempObj.scale.setScalar(0.01)
      tempObj.updateMatrix()
      meshRef.current.setMatrixAt(i, tempObj.matrix)
    }
    meshRef.current.instanceMatrix.needsUpdate = true
  }, [tempObj])

  useFrame(() => {
    if (!meshRef.current) return

    const floatIn = scroll.range(0.6, 0.15)
    const settle = scroll.range(0.75, 0.15)

    for (let i = 0; i < CARD_COUNT; i++) {
      const target = CARD_TARGETS[i]
      const stagger = Math.max(0, Math.min(1, (floatIn * CARD_COUNT - i) * 1.5))

      tempObj.position.set(
        THREE.MathUtils.lerp(0, target.pos[0], stagger),
        THREE.MathUtils.lerp(-10 + i * -1, target.pos[1], stagger),
        THREE.MathUtils.lerp(-2, target.pos[2], stagger)
      )

      tempObj.rotation.set(
        THREE.MathUtils.lerp(0.2, target.rot[0], stagger),
        THREE.MathUtils.lerp(0.5, target.rot[1], stagger),
        THREE.MathUtils.lerp(0.1, target.rot[2], stagger)
      )

      const scale = THREE.MathUtils.lerp(0.01, 1, stagger) * (1 - settle * 0.3)
      tempObj.scale.set(2.5, 1.5, 0.02)
      tempObj.scale.multiplyScalar(scale)
      tempObj.updateMatrix()
      meshRef.current.setMatrixAt(i, tempObj.matrix)
    }

    meshRef.current.instanceMatrix.needsUpdate = true
  })

  return (
    <instancedMesh ref={meshRef} args={[undefined, undefined, CARD_COUNT]}>
      <planeGeometry args={[1, 1]} />
      <meshStandardMaterial
        color="#888888"
        transparent
        opacity={0.06}
        side={THREE.DoubleSide}
        roughness={0.9}
      />
    </instancedMesh>
  )
}
