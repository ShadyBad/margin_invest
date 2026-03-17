import Link from "next/link"
import { HeroSearch } from "@/components/landing/hero-search"

export default function NotFound() {
  return (
    <div className="min-h-screen bg-bg-primary flex flex-col items-center justify-center px-6">
      <div className="max-w-md w-full text-center space-y-8">
        <div className="space-y-3">
          <p className="text-mono-label text-text-tertiary tracking-widest uppercase">
            404
          </p>
          <h1 className="text-[32px] font-bold text-text-primary tracking-tight">
            Page not found
          </h1>
          <p className="text-body text-text-secondary">
            This URL doesn&apos;t exist. Try searching for a ticker instead.
          </p>
        </div>

        <div className="max-w-sm mx-auto">
          <HeroSearch />
        </div>

        <Link
          href="/"
          className="inline-block text-sm text-text-secondary hover:text-accent transition-colors"
        >
          &larr; Back to home
        </Link>
      </div>
    </div>
  )
}
