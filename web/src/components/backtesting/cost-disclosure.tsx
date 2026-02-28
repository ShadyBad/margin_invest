interface CostValidation {
  model_cost_bps: number
  benchmark_range_bps: number[]
  status: string
  source: string
}

interface CostDisclosureProps {
  costValidation?: CostValidation
}

function AcademicValidation({ costValidation }: { costValidation: CostValidation }) {
  const { model_cost_bps, benchmark_range_bps, status, source } = costValidation
  const [low, high] = benchmark_range_bps

  const isWithinRange = status === "within_range"
  const colorClass = isWithinRange ? "text-bullish" : "text-warning"

  let message: string
  if (status === "within_range") {
    message = `Our estimated round-trip cost of ${model_cost_bps} bps for large-cap equities is within the ${low}-${high} bps range reported by ${source}.`
  } else if (status === "below_benchmark") {
    message = `Our estimated cost of ${model_cost_bps} bps is below the ${low}-${high} bps range reported by ${source} \u2014 potentially optimistic.`
  } else {
    message = `Our estimated cost of ${model_cost_bps} bps exceeds the ${low}-${high} bps range reported by ${source} \u2014 conservative.`
  }

  return (
    <div className="mt-3">
      <h4 className="text-xs font-semibold tracking-widest text-text-secondary mb-1">
        ACADEMIC VALIDATION
      </h4>
      <p className={`text-xs ${colorClass}`}>{message}</p>
    </div>
  )
}

export function CostDisclosure({ costValidation }: CostDisclosureProps) {
  return (
    <div data-testid="cost-disclosure" className="terminal-card p-4">
      <h3
        data-testid="cost-disclosure-toggle"
        className="text-xs font-semibold tracking-widest text-text-secondary"
      >
        COST MODEL ASSUMPTIONS
      </h3>

      <div data-testid="cost-disclosure-content" className="mt-3">
        <div className="mt-3">
          <h4 className="text-xs font-semibold tracking-widest text-text-secondary mb-1">
            COMMISSION
          </h4>
          <p className="text-sm text-text-secondary">
            5 bps round-trip (conservative; many brokers now offer zero-commission trades)
          </p>
        </div>

        <div className="mt-3">
          <h4 className="text-xs font-semibold tracking-widest text-text-secondary mb-1">
            SPREAD
          </h4>
          <p className="text-sm text-text-secondary">
            Market-cap dependent: 3 + 50/sqrt(cap in $B). Mega-cap ~4 bps, mid-cap ~10 bps,
            small-cap ~18 bps
          </p>
        </div>

        <div className="mt-3">
          <h4 className="text-xs font-semibold tracking-widest text-text-secondary mb-1">
            MARKET IMPACT
          </h4>
          <p className="text-sm text-text-secondary">
            Square-root model: 0.1 &times; sqrt(trade_value / ADV) &times; 10,000. Cost grows
            sub-linearly with trade size.
          </p>
        </div>

        <div className="mt-3">
          <h4 className="text-xs font-semibold tracking-widest text-text-secondary mb-1">
            NOT MODELED
          </h4>
          <ul className="list-disc list-inside text-xs text-text-tertiary">
            <li>Short-selling costs / borrow fees</li>
            <li>Taxes (capital gains, wash sale rules)</li>
            <li>Management fees / fund expenses</li>
            <li>Opportunity cost of delayed execution</li>
          </ul>
        </div>

        {costValidation && <AcademicValidation costValidation={costValidation} />}
      </div>
    </div>
  )
}
