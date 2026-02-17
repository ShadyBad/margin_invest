"use client"

import { ProGate } from "./pro-gate"

interface AiSummaryProps {
  summary: string
  confidence: number
  className?: string
}

export function AiSummary({ summary, confidence, className = "" }: AiSummaryProps) {
  return (
    <ProGate className={className}>
      <div
        className="bg-bg-subtle/50 border border-border-primary/30 rounded-sm p-5"
        data-testid="ai-summary"
      >
        <div className="text-xs font-semibold tracking-wide uppercase text-text-tertiary mb-3">
          AI ANALYSIS
        </div>
        <p className="text-sm text-text-secondary leading-relaxed mb-4">
          {summary}
        </p>
        <div className="flex items-center gap-3">
          <span className="text-xs text-text-tertiary uppercase tracking-wide">Confidence</span>
          <div className="flex-1 h-2 bg-bg-primary rounded-full overflow-hidden">
            <div
              data-testid="confidence-bar-fill"
              className="h-full bg-accent rounded-full transition-[width] duration-[600ms] ease-[cubic-bezier(0.22,1,0.36,1)]"
              style={{ width: `${Math.max(0, Math.min(100, confidence))}%` }}
            />
          </div>
          <span className="text-xs font-mono text-text-primary w-8 text-right">
            {Math.round(confidence)}
          </span>
        </div>
      </div>
    </ProGate>
  )
}
