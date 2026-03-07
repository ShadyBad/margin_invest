import { InsightCard } from "./insight-card"

interface InsightPanelProps {
  strengths: string[]
  risks: string[]
  commentary: string
  confidence: number
}

export function InsightPanel({ strengths, risks, commentary, confidence }: InsightPanelProps) {
  return (
    <div className="space-y-3" data-testid="insight-panel">
      <InsightCard variant="strengths" title="Strengths" items={strengths} />
      <InsightCard variant="risks" title="Risk Flags" items={risks} />
      <InsightCard variant="commentary" title="Analysis" text={commentary} />

      <div className="flex items-center gap-3 pt-1">
        <span className="text-[11px] text-text-tertiary">AI Confidence</span>
        <div className="flex-1 h-[3px] rounded-full bg-border-subtle">
          <div
            className="h-full rounded-full bg-accent transition-all duration-700 ease-out"
            style={{ width: `${confidence}%` }}
          />
        </div>
        <span className="text-[13px] font-mono text-accent">{confidence}%</span>
      </div>
    </div>
  )
}
