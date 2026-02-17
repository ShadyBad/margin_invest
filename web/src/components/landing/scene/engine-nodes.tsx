"use client"

import { useRef, useEffect, useMemo } from "react"
import { useFrame, useThree } from "@react-three/fiber"
import { useScroll } from "@react-three/drei"
import * as THREE from "three"
import { useNodePositions } from "@/lib/stores/node-positions"
import type { QualityTier } from "@/lib/hooks/use-quality-tier"

const NODE_COUNT = 4
const FORMATION_POSITIONS: [number, number, number][] = [
  [-6.3, 0, 0],
  [-2.1, 0, 0],
  [2.1, 0, 0],
  [6.3, 0, 0],
]

const ACCENT_COLOR = new THREE.Color("#0E4F3A")
const ACCENT_EMISSIVE = new THREE.Color("#1C7A5A")
const INACTIVE_COLOR = new THREE.Color("#888888")

interface EngineNodesProps {
  tier: QualityTier
}

export function EngineNodes({ tier }: EngineNodesProps) {
  const meshRef = useRef<THREE.InstancedMesh>(null)
  const scroll = useScroll()
  const { camera, size } = useThree()
  const tempObj = useMemo(() => new THREE.Object3D(), [])
  const tempColor = useMemo(() => new THREE.Color(), [])

  const geometry = useMemo(() => {
    return tier === "high"
      ? new THREE.OctahedronGeometry(0.5, 1)
      : new THREE.OctahedronGeometry(0.5, 0)
  }, [tier])

  useEffect(() => {
    if (!meshRef.current) return
    for (let i = 0; i < NODE_COUNT; i++) {
      tempObj.position.set(10 + i * 2, 0, 0)
      tempObj.scale.setScalar(0.01)
      tempObj.updateMatrix()
      meshRef.current.setMatrixAt(i, tempObj.matrix)
    }
    meshRef.current.instanceMatrix.needsUpdate = true
  }, [tempObj])

  useFrame(() => {
    if (!meshRef.current) return

    const positions = useNodePositions.getState().positions

    const morphProgress = scroll.range(0.32, 0.13)
    const recedeProgress = scroll.range(0.45, 0.1)

    const activeIndex = Math.min(
      Math.floor(morphProgress * NODE_COUNT),
      NODE_COUNT - 1
    )

    for (let i = 0; i < NODE_COUNT; i++) {
      const nodeProgress = Math.max(0, Math.min(1, (morphProgress * NODE_COUNT - i) * 1.5))
      const htmlRect = positions[`node-${i}`]
      const formationTarget = FORMATION_POSITIONS[i]

      let startX = 10 + i * 2
      let startY = 0

      if (htmlRect && morphProgress < 0.8) {
        const ndcX = (htmlRect.x / size.width) * 2 - 1
        const ndcY = -(htmlRect.y / size.height) * 2 + 1
        const worldPos = new THREE.Vector3(ndcX, ndcY, 0.5).unproject(camera)
        const dir = worldPos.sub(camera.position).normalize()
        const distance = -camera.position.z / dir.z
        const pos = camera.position.clone().add(dir.multiplyScalar(distance))
        startX = pos.x
        startY = pos.y
      }

      const x = THREE.MathUtils.lerp(startX, formationTarget[0], nodeProgress)
      const y = THREE.MathUtils.lerp(startY, formationTarget[1], nodeProgress)
      const z = THREE.MathUtils.lerp(0, formationTarget[2], nodeProgress) - recedeProgress * 3

      tempObj.position.set(x, y, z)
      // Breathing animation — each node oscillates at its own rate
      const time = performance.now() / 1000
      const breathPeriod = 3 + i * 0.8 // 3-6.2s per node
      const breathScale = 0.95 + 0.1 * (0.5 + 0.5 * Math.sin(time * (2 * Math.PI / breathPeriod)))
      const finalScale = THREE.MathUtils.lerp(0.01, 1, nodeProgress) * (1 - recedeProgress * 0.5) * breathScale
      tempObj.scale.setScalar(finalScale)
      tempObj.rotation.y += 0.002
      tempObj.updateMatrix()
      meshRef.current.setMatrixAt(i, tempObj.matrix)

      tempColor.copy(i <= activeIndex ? ACCENT_COLOR : INACTIVE_COLOR)
      meshRef.current.setColorAt(i, tempColor)
    }

    meshRef.current.instanceMatrix.needsUpdate = true
    if (meshRef.current.instanceColor) {
      meshRef.current.instanceColor.needsUpdate = true
    }
  })

  return (
    <instancedMesh ref={meshRef} args={[geometry, undefined, NODE_COUNT]}>
      <meshStandardMaterial
        transparent
        opacity={0.85}
        roughness={0.4}
        metalness={0.1}
        emissive={ACCENT_EMISSIVE}
        emissiveIntensity={0.3}
      />
    </instancedMesh>
  )
}
