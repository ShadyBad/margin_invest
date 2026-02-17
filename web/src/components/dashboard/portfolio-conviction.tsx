interface PortfolioConvictionProps {
  score: number | null
  label: string | null
  className?: string
}

export function PortfolioConviction({ score, label, className = "" }: PortfolioConvictionProps) {
  if (score == null) return null

  return (
    <div className={`flex flex-col items-end ${className}`} data-testid="portfolio-conviction">
      <span className="text-[11px] font-medium text-text-secondary tracking-[0.2px] uppercase mb-1">
        Portfolio Conviction
      </span>
      <div className="flex items-baseline gap-2">
        <span className="text-[40px] font-bold font-mono text-accent leading-none tracking-[-1px]">
          {score.toFixed(0)}
        </span>
        <span className="text-[13px] text-text-secondary font-mono">/100</span>
      </div>
      {label && (
        <span className="text-[13px] text-accent font-medium mt-1">
          {label}
        </span>
      )}
    </div>
  )
}
