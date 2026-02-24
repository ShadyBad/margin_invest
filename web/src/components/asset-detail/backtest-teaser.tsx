import Link from "next/link"

interface BacktestTeaserProps {
  modelReturn: number
  benchmarkReturn: number
  maxDrawdown: number
  benchmarkMaxDrawdown: number
  startDate: string
}

export function BacktestTeaser({
  modelReturn,
  benchmarkReturn,
  maxDrawdown,
  benchmarkMaxDrawdown,
  startDate,
}: BacktestTeaserProps) {
  const startYear = parseInt(startDate.slice(0, 4), 10)
  const excessReturn = modelReturn - benchmarkReturn
  const drawdownImprovement = benchmarkMaxDrawdown - maxDrawdown

  return (
    <div data-testid="backtest-teaser" className="terminal-card p-6">
      <h3 className="font-display text-lg mb-4">Backtest Preview</h3>
      <p className="text-sm text-text-secondary mb-4">
        Simulated performance since {startYear} using the scoring model.
      </p>

      <div className="grid grid-cols-3 gap-4 mb-4">
        <div className="text-center">
          <p className="text-xs text-text-secondary uppercase tracking-wider mb-1">
            Model Return
          </p>
          <p
            className={`font-mono text-xl font-bold ${
              modelReturn >= 0 ? "text-[var(--color-bullish)]" : "text-[var(--color-bearish)]"
            }`}
          >
            {modelReturn >= 0 ? "+" : ""}
            {(modelReturn * 100).toFixed(0)}%
          </p>
        </div>

        <div className="text-center">
          <p className="text-xs text-text-secondary uppercase tracking-wider mb-1">
            Benchmark Return
          </p>
          <p
            className={`font-mono text-xl font-bold ${
              benchmarkReturn >= 0 ? "text-[var(--color-bullish)]" : "text-[var(--color-bearish)]"
            }`}
          >
            {benchmarkReturn >= 0 ? "+" : ""}
            {(benchmarkReturn * 100).toFixed(0)}%
          </p>
        </div>

        <div className="text-center">
          <p className="text-xs text-text-secondary uppercase tracking-wider mb-1">
            Max Drawdown
          </p>
          <p className="font-mono text-xl font-bold text-[var(--color-bearish)]">
            -{(maxDrawdown * 100).toFixed(0)}%
          </p>
        </div>
      </div>

      <div className="flex items-center justify-between text-sm border-t border-border pt-3">
        <div className="space-x-4 text-text-secondary">
          <span>
            Excess return:{" "}
            <span
              className={`font-mono ${
                excessReturn >= 0 ? "text-[var(--color-bullish)]" : "text-[var(--color-bearish)]"
              }`}
            >
              {excessReturn >= 0 ? "+" : ""}
              {(excessReturn * 100).toFixed(0)}%
            </span>
          </span>
          <span>
            Drawdown improvement:{" "}
            <span
              className={`font-mono ${
                drawdownImprovement >= 0
                  ? "text-[var(--color-bullish)]"
                  : "text-[var(--color-bearish)]"
              }`}
            >
              {drawdownImprovement >= 0 ? "+" : ""}
              {(drawdownImprovement * 100).toFixed(0)}%
            </span>
          </span>
        </div>
        <Link href="/backtest" className="text-accent hover:text-accent-hover">
          Full backtest &rarr;
        </Link>
      </div>
    </div>
  )
}
