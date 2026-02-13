export function SkeletonCard({ className = "" }: { className?: string }) {
  return (
    <div className={`bg-bg-secondary border border-border rounded-xl p-6 animate-pulse ${className}`}>
      <div className="flex items-center justify-between mb-4">
        <div className="h-6 w-16 bg-border rounded" />
        <div className="h-5 w-20 bg-border rounded-full" />
      </div>
      <div className="h-4 w-32 bg-border rounded mb-3" />
      <div className="space-y-2">
        <div className="h-2 bg-border rounded-full" />
        <div className="h-2 bg-border rounded-full w-4/5" />
        <div className="h-2 bg-border rounded-full w-3/5" />
      </div>
    </div>
  )
}
