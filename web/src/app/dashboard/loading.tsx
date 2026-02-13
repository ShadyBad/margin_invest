import { AppShell } from "@/components/layout"
import { SkeletonCard } from "@/components/ui"

export default function DashboardLoading() {
  return (
    <AppShell>
      <div className="mb-8">
        <div className="h-8 w-40 bg-border rounded animate-pulse" />
        <div className="h-4 w-56 bg-border rounded animate-pulse mt-2" />
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {Array.from({ length: 6 }).map((_, i) => (
          <SkeletonCard key={i} />
        ))}
      </div>
    </AppShell>
  )
}
