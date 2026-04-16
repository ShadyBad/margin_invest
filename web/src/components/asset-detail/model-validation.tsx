/**
 * ModelValidation -- Merged ML audit + backtest teaser.
 *
 * Top section shows ML model qualification status with key metrics.
 * Bottom section shows backtest performance when data is available.
 */

export interface ModelValidationProps {
  mlModelQualified: boolean | null
  mlModelRankIc: number | null
  mlModelTrainedAt: string | null
  mlAlpha: number | null
  mlConfidence: number | null
  mlOverride: {
    applied: boolean
    direction: string | null
    rules_tier: string | null
    ml_tier: string | null
  } | null
  rulesTier: string | null
  compositeTier: string | null
  backtestData: {
    model_return: number
    benchmark_return: number
    max_drawdown: number
    benchmark_max_drawdown: number
    start_date: string
  } | null
}

function formatSignedPercent(value: number): string {
  const pct = (value * 100).toFixed(1)
  return value >= 0 ? `+${pct}%` : `${pct}%`
}

function formatDate(iso: string): string {
  const d = new Date(iso)
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })
}

function returnColor(value: number): string {
  return value >= 0 ? "var(--color-bullish)" : "var(--color-bearish)"
}

function MetricCell({
  label,
  value,
  color,
}: {
  label: string
  value: string
  color?: string
}) {
  return (
    <div>
      <div className="text-label-sm" style={{ color: "var(--color-on-surface-variant)" }}>
        {label}
      </div>
      <div
        className="text-mono-data mt-1"
        style={{ color: color ?? "var(--color-on-surface)" }}
      >
        {value}
      </div>
    </div>
  )
}

export function ModelValidation({
  mlModelQualified,
  mlModelRankIc,
  mlModelTrainedAt,
  mlAlpha,
  mlConfidence,
  mlOverride,
  rulesTier,
  compositeTier,
  backtestData,
}: ModelValidationProps) {
  const isQualified = mlModelQualified === true
  const hasOverride = mlOverride?.applied === true

  return (
    <section
      data-testid="model-validation"
      className="rounded-lg p-6"
      style={{
        background: "var(--color-surface-container-low)",
        border: "1px solid var(--color-ghost-border)",
      }}
    >
      {/* Header */}
      <span className="text-label-sm" style={{ color: "var(--color-on-surface-variant)" }}>
        MODEL VALIDATION
      </span>

      {/* ML Status */}
      <div className="mt-4">
        {isQualified ? (
          <>
            {/* Qualified badge */}
            <div className="flex items-center gap-2 mb-4">
              <span
                className="inline-block rounded-full"
                style={{ width: 8, height: 8, background: "var(--color-bullish)" }}
              />
              <span
                className="text-label-sm"
                style={{ color: "var(--color-bullish)" }}
              >
                QUALIFIED
              </span>
              {mlModelTrainedAt && (
                <span
                  className="text-label-sm ml-2"
                  style={{ color: "var(--color-text-tertiary)" }}
                >
                  {formatDate(mlModelTrainedAt)}
                </span>
              )}
            </div>

            {/* 3 ML metrics */}
            <div className="grid grid-cols-3 gap-4">
              <MetricCell
                label="RANK IC"
                value={mlModelRankIc != null ? mlModelRankIc.toFixed(2) : "\u2014"}
              />
              <MetricCell
                label="ALPHA"
                value={mlAlpha != null ? formatSignedPercent(mlAlpha) : "\u2014"}
                color={mlAlpha != null ? returnColor(mlAlpha) : undefined}
              />
              <MetricCell
                label="CONFIDENCE"
                value={mlConfidence != null ? `${Math.round(mlConfidence * 100)}%` : "\u2014"}
              />
            </div>

            {/* Override note */}
            {hasOverride && rulesTier && compositeTier && (
              <p
                className="text-label-sm mt-4"
                style={{ color: "var(--color-on-surface-variant)" }}
              >
                {mlOverride.direction === "promoted" ? "Promoted" : "Demoted"}{" "}
                <span style={{ fontFamily: "var(--font-data)" }}>
                  {rulesTier.toUpperCase()}
                </span>
                {" \u2192 "}
                <span style={{ fontFamily: "var(--font-data)" }}>
                  {compositeTier.toUpperCase()}
                </span>
              </p>
            )}
          </>
        ) : (
          <p
            className="text-body-md"
            style={{ color: "var(--color-text-tertiary)" }}
          >
            No qualified model &mdash; rules-only scoring
          </p>
        )}
      </div>

      {/* Backtest */}
      <div className="pt-6" data-testid="model-validation-backtest">
        {backtestData ? (
          <BacktestMetrics data={backtestData} />
        ) : (
          <p
            className="text-body-md"
            style={{ color: "var(--color-text-tertiary)" }}
          >
            Backtest data not yet available
          </p>
        )}
      </div>
    </section>
  )
}

function BacktestMetrics({
  data,
}: {
  data: NonNullable<ModelValidationProps["backtestData"]>
}) {
  const excess = data.model_return - data.benchmark_return
  const drawdownImprovement = data.benchmark_max_drawdown - data.max_drawdown

  return (
    <>
      {/* 3 return metrics */}
      <div className="grid grid-cols-3 gap-4">
        <MetricCell
          label="MODEL RETURN"
          value={formatSignedPercent(data.model_return)}
          color={returnColor(data.model_return)}
        />
        <MetricCell
          label="BENCHMARK"
          value={formatSignedPercent(data.benchmark_return)}
          color={returnColor(data.benchmark_return)}
        />
        <MetricCell
          label="EXCESS"
          value={formatSignedPercent(excess)}
          color={returnColor(excess)}
        />
      </div>

      {/* Drawdown improvement stat */}
      <p className="text-label-sm mt-4" style={{ color: "var(--color-on-surface-variant)" }}>
        DRAWDOWN IMPROVEMENT{" "}
        <span
          style={{
            fontFamily: "var(--font-data)",
            color: returnColor(drawdownImprovement),
          }}
        >
          {formatSignedPercent(drawdownImprovement)}
        </span>
      </p>
    </>
  )
}
