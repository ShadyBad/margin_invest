"use client"

export function DevAnnotations() {
  if (process.env.NODE_ENV !== "development") return null

  const notes = [
    "Render-on-demand WebGL (frameloop='demand')",
    "Quality tiers: high (DPR 1.5) / medium (DPR 1.0) / low (no WebGL)",
    "DPR cap: Math.min(devicePixelRatio, 1.5)",
    "No postprocessing (zero shader passes beyond default)",
    "InstancedMesh for diagram nodes and capability cards",
    "Progressive reveal scroll mapping via Drei ScrollControls",
  ]

  return (
    <div className="fixed bottom-4 right-4 z-[9999] max-w-sm p-4 bg-bg-elevated border border-border-primary rounded-[6px] text-[12px] font-mono text-text-secondary opacity-60 hover:opacity-100 transition-opacity">
      <div className="font-semibold text-text-primary mb-2 text-[13px]">
        WebGL Dev Notes
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
