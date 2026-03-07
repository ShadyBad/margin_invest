interface InsightCardProps {
  variant: "strengths" | "risks" | "commentary"
  title: string
  items?: string[]
  text?: string
}

const VARIANT_STYLES = {
  strengths: {
    border: "border-l-bullish",
    bg: "bg-bullish/[0.04]",
    title: "text-bullish",
    icon: "M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z",
  },
  risks: {
    border: "border-l-bearish",
    bg: "bg-bearish/[0.04]",
    title: "text-bearish",
    icon: "M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z",
  },
  commentary: {
    border: "border-l-border-primary",
    bg: "bg-surface-overlay",
    title: "text-text-secondary",
    icon: "M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09Z",
  },
}

export function InsightCard({ variant, title, items, text }: InsightCardProps) {
  const styles = VARIANT_STYLES[variant]

  return (
    <div
      className={`border-l-4 ${styles.border} ${styles.bg} rounded-r-lg p-4 hover:border-l-[6px] transition-all duration-200`}
      data-testid={`insight-card-${variant}`}
    >
      <div className={`flex items-center gap-2 mb-2 ${styles.title}`}>
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d={styles.icon} />
        </svg>
        <span className="text-[13px] font-medium">{title}</span>
      </div>
      {items && items.length > 0 && (
        <ul className="space-y-1">
          {items.map((item, i) => (
            <li key={i} className="text-[13px] text-text-secondary leading-relaxed flex gap-2">
              <span className="text-text-tertiary shrink-0">&bull;</span>
              {item}
            </li>
          ))}
        </ul>
      )}
      {text && (
        <p className="text-[13px] text-text-secondary leading-relaxed">{text}</p>
      )}
    </div>
  )
}
