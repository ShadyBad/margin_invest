import { AppShell } from "@/components/layout"
import { SkeletonCard } from "@/components/ui"

function SkeletonSidebar() {
  return (
    <aside className="w-56 shrink-0 hidden lg:block">
      <div className="border border-border-subtle rounded-lg bg-bg-elevated p-4 animate-pulse">
        <div className="h-3 w-24 bg-border-primary rounded mb-4" />
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="flex justify-between">
              <div className="h-3 w-16 bg-border-primary rounded" />
              <div className="h-3 w-12 bg-border-primary rounded" />
            </div>
          ))}
        </div>
      </div>
    </aside>
  )
}

function SkeletonWatchlistRow() {
  return (
    <div className="flex items-center justify-between py-3 px-4 animate-pulse">
      <div className="flex items-center gap-3">
        <div className="h-2 w-2 bg-border-primary rounded-full" />
        <div className="h-4 w-14 bg-border-primary rounded" />
        <div className="h-4 w-32 bg-border-primary rounded" />
      </div>
      <div className="flex items-center gap-4">
        <div className="h-5 w-16 bg-border-primary rounded-full" />
        <div className="h-4 w-10 bg-border-primary rounded" />
      </div>
    </div>
  )
}

export default function DashboardLoading() {
  return (
    <AppShell>
      {/* Greeting skeleton */}
      <div className="mb-10 pt-12 flex items-start justify-between">
        <div className="animate-pulse">
          <div className="h-7 w-72 bg-border-primary rounded mb-2" />
          <div className="h-4 w-56 bg-border-primary rounded" />
        </div>
        <div className="h-16 w-16 bg-border-primary rounded-full animate-pulse" />
      </div>

      <div className="flex gap-8">
        <SkeletonSidebar />
        <div className="flex-1 min-w-0">
          {/* Picks grid skeleton */}
          <div className="mb-10">
            <div className="h-5 w-24 bg-border-primary rounded animate-pulse mb-4" />
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4" data-testid="loading-skeleton">
              {Array.from({ length: 6 }).map((_, i) => (
                <SkeletonCard key={i} />
              ))}
            </div>
          </div>
          {/* Watchlist skeleton */}
          <div>
            <div className="h-5 w-32 bg-border-primary rounded animate-pulse mb-4" />
            <div className="border border-border-subtle rounded-lg bg-bg-elevated divide-y divide-border-subtle">
              {Array.from({ length: 4 }).map((_, i) => (
                <SkeletonWatchlistRow key={i} />
              ))}
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  )
}
