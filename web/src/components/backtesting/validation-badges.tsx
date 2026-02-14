import type { BacktestValidation } from "@/lib/api/types"

interface ValidationBadgesProps {
  validation: BacktestValidation
}

export function ValidationBadges({ validation }: ValidationBadgesProps) {
  const { overall_pass, passed_count, total_checks, checks } = validation

  return (
    <div data-testid="validation-badges">
      {/* Overall verdict banner */}
      <div
        className={`rounded-sm p-4 mb-4 border ${
          overall_pass
            ? "bg-bullish/10 border-bullish/30 text-bullish"
            : passed_count > 0
              ? "bg-accent/10 border-accent/30 text-accent"
              : "bg-bearish/10 border-bearish/30 text-bearish"
        }`}
        data-testid="validation-verdict"
      >
        <p className="font-semibold text-sm">
          {overall_pass
            ? "ALL CHECKS PASSED"
            : `${passed_count}/${total_checks} CHECKS PASSED`}
        </p>
      </div>

      {/* Individual checks */}
      <div className="space-y-2">
        {checks.map((check) => (
          <div
            key={check.name}
            className="flex items-center justify-between bg-bg-elevated border border-border-primary rounded-sm px-4 py-3"
            data-testid={`check-${check.name}`}
          >
            <div className="flex items-center gap-3">
              {check.passed ? (
                <svg
                  className="w-5 h-5 text-bullish flex-shrink-0"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  aria-hidden="true"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M5 13l4 4L19 7"
                  />
                </svg>
              ) : (
                <svg
                  className="w-5 h-5 text-bearish flex-shrink-0"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  aria-hidden="true"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              )}
              <span className="text-sm text-text-primary">{check.name}</span>
            </div>
            <div className="flex items-center gap-3">
              <span className="text-xs text-text-secondary">
                {check.actual.toFixed(2)} / {check.threshold.toFixed(2)}
              </span>
              <span
                className={`text-xs font-semibold px-2 py-0.5 rounded ${
                  check.passed
                    ? "bg-bullish/10 text-bullish"
                    : "bg-bearish/10 text-bearish"
                }`}
              >
                {check.passed ? "PASS" : "FAIL"}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
