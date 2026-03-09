interface EngineCardProps {
  title: string
  subtitle: string
  description: string
}

export function EngineCard({ title, subtitle, description }: EngineCardProps) {
  return (
    <div className="w-[320px] flex-shrink-0 terminal-card p-6 md:p-8">
      <div className="text-xs uppercase tracking-[0.2em] text-text-tertiary mb-2">
        {subtitle}
      </div>
      <h3 className="font-display text-2xl md:text-3xl text-text-primary mb-3">
        {title}
      </h3>
      <p className="text-sm text-text-secondary leading-relaxed">
        {description}
      </p>
    </div>
  )
}
