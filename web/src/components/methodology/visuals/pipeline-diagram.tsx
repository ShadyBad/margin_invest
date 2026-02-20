"use client"

const stages = [
  { num: "01", label: "Universe", desc: "Selection", metric: "~7,000 US equities" },
  { num: "02", label: "Data", desc: "Ingestion", metric: "Daily after close" },
  { num: "03", label: "Filters", desc: "Elimination", metric: "6 independent checks" },
  { num: "04", label: "Scoring", desc: "Multi-Factor", metric: "20+ quantitative factors" },
  { num: "05", label: "Conviction", desc: "Dual-Track", metric: "Compounder & Mispricing" },
  { num: "06", label: "Output", desc: "Decisions", metric: "Cards, targets, sizing" },
]

function PipelineArrow() {
  return (
    <svg
      width="20"
      height="12"
      viewBox="0 0 20 12"
      fill="none"
      className="text-border-primary flex-shrink-0 hidden sm:block"
    >
      <line x1="0" y1="6" x2="14" y2="6" stroke="currentColor" strokeWidth="1" />
      <path d="M12 2 L18 6 L12 10" stroke="currentColor" strokeWidth="1" fill="none" />
    </svg>
  )
}

export function PipelineDiagram() {
  return (
    <div className="p-6 border border-border-primary rounded-lg bg-bg-elevated overflow-x-auto">
      {/* Desktop: horizontal flow */}
      <div className="hidden sm:flex items-center justify-between gap-2">
        {stages.map((stage, i) => (
          <div key={stage.label} className="flex items-center gap-2">
            <div className="flex flex-col items-center text-center min-w-[90px]">
              <span className="text-[11px] font-mono font-bold text-accent">
                {stage.num}
              </span>
              <span className="text-[13px] font-semibold text-text-primary mt-1">
                {stage.label}
              </span>
              <span className="text-[11px] text-text-tertiary mt-0.5">
                {stage.desc}
              </span>
              <span className="text-[10px] font-mono text-text-tertiary mt-1">
                {stage.metric}
              </span>
            </div>
            {i < stages.length - 1 && <PipelineArrow />}
          </div>
        ))}
      </div>

      {/* Mobile: vertical flow */}
      <div className="flex flex-col gap-4 sm:hidden">
        {stages.map((stage) => (
          <div key={stage.label} className="flex items-start gap-3">
            <span className="text-[11px] font-mono font-bold text-accent w-5 flex-shrink-0 mt-0.5">
              {stage.num}
            </span>
            <div>
              <span className="text-[13px] font-semibold text-text-primary">
                {stage.label}
              </span>
              <span className="text-[11px] text-text-tertiary ml-2">
                {stage.desc}
              </span>
              <p className="text-[10px] font-mono text-text-tertiary mt-0.5">
                {stage.metric}
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
