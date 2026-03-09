export function SkeletonCard({ className = "" }: { className?: string }) {
  return (
    <div className={`bg-bg-elevated border border-border-primary rounded-lg p-6 animate-pulse ${className}`}>
      {/* Header: ticker + badge */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className="h-5 w-14 bg-border-primary rounded" />
          <div className="h-4 w-20 bg-border-primary rounded" />
        </div>
        <div className="h-6 w-20 bg-border-primary rounded-full" />
      </div>
      {/* Name */}
      <div className="h-4 w-40 bg-border-primary rounded mb-4" />
      {/* Score + action pill */}
      <div className="flex items-center justify-between mb-6">
        <div className="h-12 w-16 bg-border-primary rounded" />
        <div className="h-8 w-24 bg-border-primary rounded-full" />
      </div>
      {/* Price row */}
      <div className="flex items-center gap-4 mb-4">
        <div className="h-4 w-20 bg-border-primary rounded" />
        <div className="h-4 w-20 bg-border-primary rounded" />
        <div className="h-4 w-12 bg-border-primary rounded" />
      </div>
      {/* Percentile bars */}
      <div className="space-y-2">
        <div className="h-2.5 bg-border-primary rounded-full" />
        <div className="h-2.5 bg-border-primary rounded-full w-4/5" />
        <div className="h-2.5 bg-border-primary rounded-full w-3/5" />
      </div>
    </div>
  )
}
