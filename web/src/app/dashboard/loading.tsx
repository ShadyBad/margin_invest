import { AppShell } from "@/components/layout"

function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`animate-pulse bg-bg-subtle rounded-xl ${className}`} />
}

export default function DashboardLoading() {
  return (
    <AppShell>
      {/* Greeting bar + conviction badge */}
      <div className="mb-10 pt-12 flex items-start justify-between">
        <div className="space-y-2">
          <Skeleton className="h-8 w-56" />
          <Skeleton className="h-4 w-36" />
        </div>
        <Skeleton className="h-16 w-32" />
      </div>

      <div className="flex gap-8">
        {/* Sidebar — 3 blocks */}
        <aside className="w-56 shrink-0 hidden lg:block space-y-4">
          <Skeleton className="h-28" />
          <Skeleton className="h-28" />
          <Skeleton className="h-28" />
        </aside>

        {/* Main content */}
        <div className="flex-1 min-w-0">
          {/* Top Picks heading + 3 pick cards */}
          <section className="mb-10">
            <Skeleton className="h-6 w-28 mb-4" />
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4" data-testid="loading-skeleton">
              <Skeleton className="h-48" />
              <Skeleton className="h-48" />
              <Skeleton className="h-48" />
            </div>
          </section>

          {/* Recent Changes */}
          <section className="mb-10">
            <Skeleton className="h-6 w-40 mb-4" />
            <Skeleton className="h-32" />
          </section>
        </div>
      </div>
    </AppShell>
  )
}
