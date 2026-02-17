"use client"

import { useState } from "react"

export function DevAnnotations() {
  const [open, setOpen] = useState(false)

  if (process.env.NODE_ENV !== "development") return null

  const notes = [
    "Continuous WebGL rendering (frameloop='always')",
    "Quality tiers: high (DPR 1.5) / medium (DPR 1.0) / low (no WebGL)",
    "DPR cap: Math.min(devicePixelRatio, 1.5)",
    "Postprocessing: Bloom + Vignette + ChromaticAberration (high tier)",
    "InstancedMesh for diagram nodes and capability cards",
    "Progressive reveal scroll mapping via Drei ScrollControls",
  ]

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="fixed bottom-4 right-4 z-[9999] w-8 h-8 bg-bg-elevated border border-border-primary rounded-[4px] text-[10px] font-mono text-text-secondary opacity-40 hover:opacity-100 transition-opacity flex items-center justify-center"
        aria-label="Show WebGL dev notes"
      >
        GL
      </button>
    )
  }

  return (
    <div className="fixed bottom-4 right-4 z-[9999] max-w-sm p-4 bg-bg-elevated border border-border-primary rounded-[6px] text-[12px] font-mono text-text-secondary opacity-80">
      <div className="flex items-center justify-between mb-2">
        <span className="font-semibold text-text-primary text-[13px]">
          WebGL Dev Notes
        </span>
        <button
          onClick={() => setOpen(false)}
          className="text-text-secondary hover:text-text-primary text-[14px] leading-none"
          aria-label="Close dev notes"
        >
          ×
        </button>
      </div>
      <ul className="space-y-1">
        {notes.map((note, i) => (
          <li key={i} className="flex gap-2">
            <span className="text-accent shrink-0">*</span>
            {note}
          </li>
        ))}
      </ul>
    </div>
  )
}
