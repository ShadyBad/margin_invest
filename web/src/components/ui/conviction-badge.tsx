interface ConvictionBadgeProps {
  level: string
  className?: string
}

const badgeStyles: Record<string, string> = {
  exceptional: "bg-gold/20 text-gold border-gold/30",
  high: "bg-gold/10 text-gold-hover border-gold/20",
  watchlist: "bg-bg-secondary text-text-secondary border-border",
  none: "bg-bg-primary text-text-secondary border-border",
}

export function ConvictionBadge({ level, className = "" }: ConvictionBadgeProps) {
  const style = badgeStyles[level] || badgeStyles.none
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${style} ${className}`}>
      {level}
    </span>
  )
}
