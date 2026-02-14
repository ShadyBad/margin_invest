interface ConvictionBadgeProps {
  level: string
  className?: string
}

const badgeStyles: Record<string, string> = {
  exceptional: "bg-accent/20 text-accent border-accent/30",
  high: "bg-accent/10 text-accent-hover border-accent/20",
  watchlist: "bg-bg-elevated text-text-secondary border-border-primary",
  none: "bg-bg-primary text-text-secondary border-border-primary",
}

export function ConvictionBadge({ level, className = "" }: ConvictionBadgeProps) {
  const style = badgeStyles[level] || badgeStyles.none
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-sm text-xs font-medium border ${style} ${className}`}>
      {level}
    </span>
  )
}
