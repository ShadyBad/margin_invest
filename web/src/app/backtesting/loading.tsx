import { AppShell } from "@/components/layout"
import { SkeletonCard } from "@/components/ui"

export default function BacktestingLoading() {
  return (
    <AppShell>
      <div className="mb-8">
        <div className="h-8 w-48 bg-border-primary rounded animate-pulse" />
        <div className="h-4 w-64 bg-border-primary rounded animate-pulse mt-2" />
      </div>
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
        {Array.from({ length: 8 }).map((_, i) => (
          <SkeletonCard key={i} />
        ))}
      </div>
    </AppShell>
  )
}
