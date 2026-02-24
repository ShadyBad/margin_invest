interface FailurePeriod {
  startDate: string
  endDate: string
  returnPct: number
  benchmarkReturnPct: number
  regime: string
  maxDrawdown: number
  recoveryMonths: number | null
}

interface FailureAuditProps {
  periods: FailurePeriod[]
}

function formatPercent(value: number): string {
  return `${(value * 100).toFixed(2)}%`
}

export function FailureAudit({ periods }: FailureAuditProps) {
  const sorted = [...periods].sort((a, b) => a.returnPct - b.returnPct)

  return (
    <div className="terminal-card p-6" data-testid="failure-audit">
      <h3 className="text-xs font-semibold tracking-widest text-text-secondary mb-4">
        WORST PERIODS
      </h3>

      {sorted.length === 0 ? (
        <p className="text-text-secondary text-sm">No significant drawdowns</p>
      ) : (
        <div className="space-y-3">
          {sorted.map((period, i) => (
            <div
              key={`${period.startDate}-${period.endDate}`}
              data-testid={`failure-period-${i}`}
              className="bg-bg-primary border border-border-primary rounded-sm p-4"
            >
              <div className="flex items-start justify-between mb-2">
                <div>
                  <p className="text-sm text-text-primary">
                    {period.startDate} &mdash; {period.endDate}
                  </p>
                  <p className="text-xs text-text-tertiary mt-0.5">{period.regime}</p>
                </div>
                <span
                  data-testid={`failure-return-${i}`}
                  className="text-xl font-semibold font-[family-name:var(--font-mono)] text-bearish"
                >
                  {formatPercent(period.returnPct)}
                </span>
              </div>

              <div className="grid grid-cols-3 gap-4 mt-3">
                <div>
                  <p className="text-xs text-text-tertiary">Benchmark</p>
                  <p className="text-sm font-[family-name:var(--font-mono)] text-text-secondary">
                    {formatPercent(period.benchmarkReturnPct)}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-text-tertiary">Max Drawdown</p>
                  <p className="text-sm font-[family-name:var(--font-mono)] text-bearish">
                    {formatPercent(period.maxDrawdown)}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-text-tertiary">Recovery</p>
                  <p className="text-sm font-[family-name:var(--font-mono)] text-text-secondary">
                    {period.recoveryMonths === null
                      ? "Never recovered"
                      : `${period.recoveryMonths} months`}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
