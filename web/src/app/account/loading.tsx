import { AppShell } from "@/components/layout"

export default function AccountLoading() {
  return (
    <AppShell>
      <div className="h-10 w-32 bg-border-primary rounded animate-pulse mb-2" />
      <div className="h-4 w-64 bg-border-primary rounded animate-pulse mb-8" />

      <div className="md:grid md:grid-cols-[160px_1fr] md:gap-8">
        <div className="hidden md:block">
          <div className="space-y-2">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="h-8 w-full bg-border-primary rounded-lg animate-pulse" />
            ))}
          </div>
        </div>

        <div className="space-y-8">
          {Array.from({ length: 3 }).map((_, i) => (
            <div
              key={i}
              className="terminal-card p-6 md:p-8 animate-pulse"
            >
              <div className="h-3 w-16 bg-border-primary rounded mb-6" />
              <div className="h-5 w-1/3 bg-border-primary rounded mb-3" />
              <div className="h-4 w-1/2 bg-border-primary rounded" />
            </div>
          ))}
        </div>
      </div>
    </AppShell>
  )
}
