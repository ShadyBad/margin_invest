interface MLAuditPanelProps {
  mlModelQualified: boolean | null
  mlModelRankIc: number | null
  mlModelTrainedAt: string | null
  mlAlpha: number | null
  mlConfidence: number | null
  mlOverride: string | null
  rulesTier: string | null
  compositeTier: string | null
}

const OVERRIDE_GATES = [
  "Rank IC above 0.15 qualification threshold",
  "ML confidence above override minimum",
  "Alpha signal directionally consistent",
  "No conflicting elimination filters",
]

function formatDate(iso: string): string {
  const d = new Date(iso)
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })
}

export function MLAuditPanel({
  mlModelQualified,
  mlModelRankIc,
  mlModelTrainedAt,
  mlAlpha,
  mlConfidence,
  mlOverride,
  rulesTier,
  compositeTier,
}: MLAuditPanelProps) {
  // Render nothing when no ML data at all (v2 fallback)
  if (mlModelQualified == null && mlModelRankIc == null) {
    return <div data-testid="ml-audit-panel" />
  }

  const isQualified = mlModelQualified === true
  const hasOverride = mlOverride === "promoted" || mlOverride === "demoted"
  const isPromoted = mlOverride === "promoted"

  return (
    <section data-testid="ml-audit-panel" className="space-y-4">
      {/* Section title */}
      <div className="flex items-center gap-3">
        <h2 className="text-lg font-semibold text-text-primary">Machine Learning Audit</h2>
        {hasOverride && (
          <span
            className={`text-xs font-semibold px-2 py-0.5 rounded uppercase tracking-wider ${
              isPromoted
                ? "bg-bullish/10 text-bullish"
                : "bg-bearish/10 text-bearish"
            }`}
          >
            {mlOverride.toUpperCase()}
          </span>
        )}
      </div>

      {/* Model status line */}
      <div className="terminal-card p-4 space-y-3">
        <div className="flex items-center gap-2">
          <span
            className={`inline-block w-2 h-2 rounded-full ${
              isQualified ? "bg-bullish" : "bg-text-tertiary"
            }`}
          />
          <span className={`text-sm font-medium ${isQualified ? "text-bullish" : "text-text-secondary"}`}>
            {isQualified ? "Qualified" : "No qualified model"}
          </span>
        </div>

        {/* Rank IC + training date */}
        <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-text-tertiary">
          {mlModelRankIc != null && (
            <span>
              Rank IC: <span className="font-mono text-text-secondary">{mlModelRankIc.toFixed(2)}</span>
            </span>
          )}
          {mlModelTrainedAt && (
            <span>
              Trained: <span className="text-text-secondary">{formatDate(mlModelTrainedAt)}</span>
            </span>
          )}
        </div>

        {/* Unqualified: explanation */}
        {!isQualified && (
          <p className="text-xs text-text-tertiary">
            ML models are training. Current rank IC ({mlModelRankIc != null ? mlModelRankIc.toFixed(2) : "N/A"}) is
            below the 0.15 qualification threshold. Scoring is rules-only.
          </p>
        )}
      </div>

      {/* Metric cards — only for qualified models */}
      {isQualified && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {/* ML Alpha */}
          <div className="terminal-card p-4 space-y-1">
            <span className="text-xs uppercase tracking-wider text-text-tertiary">ML Alpha</span>
            <span
              className={`text-2xl font-display block ${
                mlAlpha != null && mlAlpha > 0
                  ? "text-bullish"
                  : mlAlpha != null && mlAlpha < 0
                    ? "text-bearish"
                    : "text-text-primary"
              }`}
            >
              {mlAlpha != null ? `${mlAlpha > 0 ? "+" : ""}${mlAlpha.toFixed(1)}` : "N/A"}
            </span>
            <span className="text-xs text-text-tertiary">vs rules-only baseline</span>
          </div>

          {/* Confidence */}
          <div className="terminal-card p-4 space-y-1">
            <span className="text-xs uppercase tracking-wider text-text-tertiary">Confidence</span>
            <span className="text-2xl font-display text-text-primary block">
              {mlConfidence != null ? `${Math.round(mlConfidence * 100)}%` : "N/A"}
            </span>
            <span className="text-xs text-text-tertiary">model certainty</span>
          </div>

          {/* Override */}
          <div className="terminal-card p-4 space-y-1">
            <span className="text-xs uppercase tracking-wider text-text-tertiary">Override</span>
            {hasOverride ? (
              <>
                <span
                  className={`text-base font-semibold block ${
                    isPromoted ? "text-bullish" : "text-bearish"
                  }`}
                >
                  {isPromoted ? "Promoted" : "Demoted"}
                </span>
                {rulesTier && compositeTier && (
                  <span className="text-xs text-text-tertiary">
                    <span className="font-mono">{rulesTier}</span>
                    {" \u2192 "}
                    <span className="font-mono">{compositeTier}</span>
                  </span>
                )}
              </>
            ) : (
              <>
                <span className="text-base font-semibold text-text-primary block">None</span>
                <span className="text-xs text-text-tertiary">rules preserved</span>
              </>
            )}
          </div>
        </div>
      )}

      {/* Verdict */}
      {isQualified && (
        <div className="terminal-card p-4">
          <p className="text-xs text-text-secondary">
            {hasOverride
              ? isPromoted
                ? `ML model detected stronger upside potential than rules alone. Tier promoted from ${rulesTier ?? "unknown"} to ${compositeTier ?? "unknown"}.`
                : `ML model detected elevated risk not captured by rules. Tier demoted from ${rulesTier ?? "unknown"} to ${compositeTier ?? "unknown"}.`
              : "ML signal did not meet override thresholds. Rules-based tier preserved."}
          </p>
        </div>
      )}

      {/* Override gates checklist — only for overrides */}
      {isQualified && hasOverride && (
        <div className="terminal-card p-4 space-y-2">
          <span className="text-xs uppercase tracking-wider text-text-tertiary">
            Override Gates Passed
          </span>
          <div className="space-y-1">
            {OVERRIDE_GATES.map((gate) => (
              <div key={gate} className="flex items-center gap-2 text-xs text-text-secondary">
                <span className="text-bullish">&#10003;</span>
                <span>{gate}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </section>
  )
}
