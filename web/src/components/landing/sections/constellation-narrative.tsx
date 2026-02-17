"use client"

import { useRef } from "react"
import { motion, useScroll, useTransform, useReducedMotion, useTime, type MotionValue } from "framer-motion"
import {
  getConstellationData,
  type ConstellationNode,
  type ConstellationEdge,
} from "./constellation-data"

function getNodeProgress(progress: number, stagger: number): number {
  const adjusted = (progress - stagger * 0.3) / 0.7
  return Math.max(0, Math.min(1, adjusted))
}

function NodeCircle({
  node,
  progress,
}: {
  node: ConstellationNode
  progress: MotionValue<number>
}) {
  const prefersReducedMotion = useReducedMotion()
  const time = useTime()

  const cx = useTransform([progress, time] as MotionValue[], ([p, t]: number[]) => {
    const nodeP = getNodeProgress(p, node.stagger)
    const baseX = node.chaosPos.x + (node.structuredPos.x - node.chaosPos.x) * nodeP
    // Drift: dampens from ±2px to 0 as nodeProgress increases
    if (prefersReducedMotion || nodeP > 0.8) return baseX
    const amplitude = 2 * (1 - nodeP)
    return baseX + Math.sin((t / 1000) * node.driftFreq * Math.PI * 2) * amplitude
  })

  const cy = useTransform([progress, time] as MotionValue[], ([p, t]: number[]) => {
    const nodeP = getNodeProgress(p, node.stagger)
    const baseY = node.chaosPos.y + (node.structuredPos.y - node.chaosPos.y) * nodeP
    if (prefersReducedMotion || nodeP > 0.8) return baseY
    const amplitude = 1.5 * (1 - nodeP)
    // Phase offset by node.id for variety
    return baseY + Math.cos((t / 1000) * node.driftFreq * Math.PI * 2 + node.id) * amplitude
  })

  const r = useTransform(progress, (p: number) => {
    const t = getNodeProgress(p, node.stagger)
    return node.chaosRadius + (node.structuredRadius - node.chaosRadius) * t
  })

  const opacity = useTransform(progress, (p: number) => {
    const t = getNodeProgress(p, node.stagger)
    const chaosOpacity = 0.15 + node.id * 0.005
    return chaosOpacity + (node.structuredOpacity - chaosOpacity) * t
  })

  return (
    <motion.circle
      cx={cx}
      cy={cy}
      r={r}
      opacity={opacity}
      fill="currentColor"
      className={node.role === "hub" ? "text-accent" : "text-text-secondary"}
    />
  )
}

function EdgeLine({
  edge,
  progress,
  nodes,
}: {
  edge: ConstellationEdge
  progress: MotionValue<number>
  nodes: ConstellationNode[]
}) {
  const fromNode = nodes[edge.from]
  const toNode = nodes[edge.to]

  // Fallback node for hooks stability — ensures hooks are always called in the same order.
  // If an edge references an invalid index, we render nothing but still call all hooks.
  const safeFrom = fromNode ?? nodes[0]
  const safeTo = toNode ?? nodes[0]
  const valid = !!fromNode && !!toNode

  const x1 = useTransform(progress, (p: number) => {
    const t = getNodeProgress(p, safeFrom.stagger)
    return safeFrom.chaosPos.x + (safeFrom.structuredPos.x - safeFrom.chaosPos.x) * t
  })

  const y1 = useTransform(progress, (p: number) => {
    const t = getNodeProgress(p, safeFrom.stagger)
    return safeFrom.chaosPos.y + (safeFrom.structuredPos.y - safeFrom.chaosPos.y) * t
  })

  const x2 = useTransform(progress, (p: number) => {
    const t = getNodeProgress(p, safeTo.stagger)
    return safeTo.chaosPos.x + (safeTo.structuredPos.x - safeTo.chaosPos.x) * t
  })

  const y2 = useTransform(progress, (p: number) => {
    const t = getNodeProgress(p, safeTo.stagger)
    return safeTo.chaosPos.y + (safeTo.structuredPos.y - safeTo.chaosPos.y) * t
  })

  const opacity = useTransform(progress, (p: number) => {
    if (edge.type === "false") {
      // False edges: 0.12 -> 0 (fade out)
      return 0.12 * (1 - p)
    }
    // Real edges: 0.08 -> target opacity
    const target = edge.isHubEdge ? 0.4 : 0.2
    return 0.08 + (target - 0.08) * p
  })

  const strokeDasharray = useTransform(progress, (p: number) => {
    if (edge.type === "false") return "4 8"
    // Real edges: transition from broken to solid
    return p > 0.5 ? "none" : "4 8"
  })

  if (!valid) return null

  return (
    <motion.line
      x1={x1}
      y1={y1}
      x2={x2}
      y2={y2}
      opacity={opacity}
      strokeDasharray={strokeDasharray}
      stroke="currentColor"
      strokeWidth={edge.isHubEdge ? 1.5 : 0.8}
      className={edge.isHubEdge ? "text-accent" : "text-text-secondary"}
    />
  )
}

export function ConstellationNarrative() {
  const prefersReducedMotion = useReducedMotion()
  const containerRef = useRef<HTMLDivElement>(null)
  const { nodes, edges } = getConstellationData()

  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ["start end", "end start"],
  })

  // Map scroll to 0-1 animation progress
  const rawProgress = useTransform(scrollYProgress, [0.15, 0.55], [0, 1])
  // When reduced motion is preferred, pin progress to 1 (structured state)
  const progress = useTransform(rawProgress, (v: number) => prefersReducedMotion ? 1 : v)

  return (
    <div ref={containerRef} className="w-full h-full">
      <svg
        className="w-full h-full"
        viewBox="0 0 400 280"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        aria-hidden="true"
      >
        <g>
          {edges.map((edge, i) => (
            <EdgeLine key={`edge-${i}`} edge={edge} progress={progress} nodes={nodes} />
          ))}
        </g>
        <g>
          {nodes.map((node) => (
            <NodeCircle key={`node-${node.id}`} node={node} progress={progress} />
          ))}
        </g>
      </svg>
    </div>
  )
}
