import { Navbar } from "@/components/nav/navbar"

export default function GuidesLoading() {
  return (
    <main className="relative bg-bg-primary min-h-screen">
      <div className="relative z-10">
        <Navbar />

        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 pt-28 pb-16">
          <div className="max-w-2xl mb-12">
            <div className="h-8 w-32 bg-border-primary rounded animate-pulse" />
            <div className="h-4 w-72 bg-border-primary rounded animate-pulse mt-4" />
          </div>

          {/* Tab skeleton */}
          <div className="flex gap-2 mb-8">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="h-8 w-24 bg-border-primary rounded-full animate-pulse" />
            ))}
          </div>

          {/* Card skeletons */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {Array.from({ length: 6 }).map((_, i) => (
              <div
                key={i}
                className="bg-bg-elevated border border-border-subtle rounded-lg p-6 animate-pulse"
              >
                <div className="h-5 w-3/4 bg-border-primary rounded mb-3" />
                <div className="h-4 w-full bg-border-primary rounded mb-2" />
                <div className="h-4 w-2/3 bg-border-primary rounded mb-4" />
                <div className="h-3 w-1/3 bg-border-primary rounded" />
              </div>
            ))}
          </div>
        </div>
      </div>
    </main>
  )
}
