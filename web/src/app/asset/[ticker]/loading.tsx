export default function AssetDetailLoading() {
  return (
    <div className="min-h-screen bg-bg-primary">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 pt-24 pb-8">
        <div className="animate-pulse space-y-6">
          <div className="h-8 w-48 bg-bg-subtle rounded" />
          <div className="h-40 bg-bg-subtle rounded-xl" />
          <div className="h-64 bg-bg-subtle rounded-xl" />
        </div>
      </div>
    </div>
  )
}
