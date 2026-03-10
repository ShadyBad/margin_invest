interface StalenessIndicatorProps {
  isFallback?: boolean
}

export function StalenessIndicator({ isFallback }: StalenessIndicatorProps) {
  if (!isFallback) return null

  return (
    <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-text-tertiary">
      Sample data from last scoring cycle &middot; Live data loads after engine
      run
    </p>
  )
}
