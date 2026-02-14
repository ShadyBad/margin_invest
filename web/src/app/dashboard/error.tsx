"use client"

import { useRouter } from "next/navigation"
import { AppShell } from "@/components/layout"

export default function DashboardError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  const router = useRouter()

  return (
    <AppShell>
      <div className="flex flex-col items-center justify-center py-20">
        <div className="bg-bearish/10 border border-bearish/30 rounded-sm p-6 max-w-md text-center">
          <h2 className="text-lg font-semibold text-bearish mb-2">
            Failed to load dashboard
          </h2>
          <p className="text-sm text-text-secondary mb-4">
            {error.message || "An unexpected error occurred."}
          </p>
          <button
            onClick={() => {
              reset()
              router.refresh()
            }}
            className="px-4 py-2 bg-accent text-bg-primary rounded-sm text-sm font-medium hover:bg-accent/90 transition-colors"
          >
            Try again
          </button>
        </div>
      </div>
    </AppShell>
  )
}
