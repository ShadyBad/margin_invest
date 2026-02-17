interface ConvictionBadgeProps {
  level: string
  className?: string
}

const badgeStyles: Record<string, string> = {
  exceptional: "bg-accent text-white border-accent",
  high: "bg-accent/10 text-accent-hover border-accent/20",
  watchlist: "bg-bg-elevated text-text-secondary border-border-primary",
  none: "bg-bg-primary text-text-secondary border-border-primary",
}

export function ConvictionBadge({ level, className = "" }: ConvictionBadgeProps) {
  const style = badgeStyles[level] || badgeStyles.none
  const sizeClass = level === "exceptional" ? "px-3 py-1 text-sm" : "px-2.5 py-0.5 text-xs"
  return (
    <span className={`inline-flex items-center rounded-sm font-medium border ${sizeClass} ${style} ${className}`}>
      {level}
    </span>
  )
}
