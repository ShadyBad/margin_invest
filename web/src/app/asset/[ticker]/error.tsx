"use client"

export default function AssetDetailError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  return (
    <div className="min-h-screen bg-bg-primary flex items-center justify-center">
      <div className="text-center space-y-4">
        <h2 className="text-xl font-semibold text-text-primary">Something went wrong</h2>
        <p className="text-text-secondary text-sm">{error.message}</p>
        <button
          onClick={reset}
          className="px-4 py-2 bg-accent text-white rounded-lg text-sm hover:bg-accent-hover transition-colors"
        >
          Try again
        </button>
      </div>
    </div>
  )
}
