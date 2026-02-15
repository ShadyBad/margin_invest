import type { SignalTransition } from "@/lib/api/types"

interface SignalTimelineProps {
  transitions: SignalTransition[] | null | undefined
  className?: string
}

const signalColor: Record<string, string> = {
  buy: "text-bullish",
  hold: "text-accent",
  sell: "text-warning",
  urgent_sell: "text-bearish",
  watch: "text-text-secondary",
  no_action: "text-text-tertiary",
}

export function SignalTimeline({
  transitions,
  className = "",
}: SignalTimelineProps) {
  if (!transitions || transitions.length === 0) {
    return (
      <div className={className} data-testid="signal-timeline-empty">
        <h4 className="text-sm font-semibold text-text-primary mb-3">Signal History</h4>
        <p className="text-sm text-text-tertiary">No transitions recorded</p>
      </div>
    )
  }

  return (
    <div className={className} data-testid="signal-timeline">
      <h4 className="text-sm font-semibold text-text-primary mb-3">Signal History</h4>
      <div className="space-y-3">
        {transitions.map((t, i) => {
          const date = new Date(t.transitioned_at).toLocaleDateString("en-US", {
            month: "short",
            day: "numeric",
          })
          return (
            <div key={i} className="flex items-center gap-3 text-sm">
              <span className="text-text-tertiary w-14 shrink-0">{date}</span>
              <span className={`uppercase text-xs font-medium ${signalColor[t.previous_signal] ?? ""}`}>
                {t.previous_signal.replace("_", " ")}
              </span>
              <span className="text-text-tertiary">&rarr;</span>
              <span className={`uppercase text-xs font-medium ${signalColor[t.new_signal] ?? ""}`}>
                {t.new_signal.replace("_", " ")}
              </span>
              {t.actual_price_at_transition != null && (
                <span className="text-text-secondary ml-auto">
                  @${t.actual_price_at_transition.toFixed(2)}
                </span>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
