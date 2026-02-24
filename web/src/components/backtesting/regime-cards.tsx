export interface RegimePerformance {
  regime: "bull" | "bear" | "sideways" | "crisis"
  label: string
  modelReturn: number
  benchmarkReturn: number
  months: number
  excessReturn: number
}

interface RegimeCardsProps {
  regimes: RegimePerformance[]
}

const regimeColors: Record<string, string> = {
  bull: "var(--color-bullish)",
  bear: "var(--color-bearish)",
  sideways: "var(--color-warning)",
  crisis: "var(--color-bearish)",
}

function formatReturn(value: number): string {
  const pct = (value * 100).toFixed(1)
  return value >= 0 ? `+${pct}%` : `${pct}%`
}

function excessColorClass(value: number): string {
  if (value > 0) return "text-bullish"
  if (value < 0) return "text-bearish"
  return "text-text-primary"
}

function RegimeCard({ perf }: { perf: RegimePerformance }) {
  return (
    <div
      className="terminal-card p-4"
      data-testid={`regime-card-${perf.regime}`}
    >
      <div className="flex items-center gap-2 mb-3">
        <span
          className="inline-block w-2 h-2 rounded-full"
          style={{ backgroundColor: regimeColors[perf.regime] }}
          aria-hidden="true"
        />
        <span className="text-xs uppercase tracking-wider text-text-secondary">
          {perf.label}
        </span>
      </div>

      <p className="text-2xl font-semibold font-[family-name:var(--font-mono)] text-text-primary mb-1">
        {formatReturn(perf.modelReturn)}
      </p>

      <p
        className="text-xs text-text-tertiary mb-2"
        data-testid={`regime-benchmark-${perf.regime}`}
      >
        Benchmark {formatReturn(perf.benchmarkReturn)}
      </p>

      <p
        className={`text-sm font-medium font-[family-name:var(--font-mono)] ${excessColorClass(perf.excessReturn)}`}
        data-testid={`regime-excess-${perf.regime}`}
      >
        {formatReturn(perf.excessReturn)} excess
      </p>

      <p className="text-xs text-text-tertiary mt-2">
        {perf.months} months
      </p>
    </div>
  )
}

export function RegimeCards({ regimes }: RegimeCardsProps) {
  if (regimes.length === 0) {
    return (
      <div data-testid="regime-cards-empty" className="text-text-secondary text-sm">
        No regime data available.
      </div>
    )
  }

  return (
    <div
      className="grid grid-cols-2 lg:grid-cols-4 gap-4"
      data-testid="regime-cards"
    >
      {regimes.map((perf) => (
        <RegimeCard key={perf.regime} perf={perf} />
      ))}
    </div>
  )
}
