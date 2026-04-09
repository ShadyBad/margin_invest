"use client"

import Link from "next/link"

export function TransparencyStrip() {
  const launchDate = "2026"
  
  return (
    <section className="py-8 px-6 border-t border-border-subtle">
      <div className="max-w-5xl mx-auto flex items-center justify-center">
        <p className="text-sm text-text-secondary">
          <span className="font-medium">Live transparency</span> — Every score timestamped and publicly logged since {launchDate}.{" "}
          <Link
            href="/track-record"
            className="text-accent hover:text-accent-hover underline underline-offset-2 transition-colors"
          >
            View the ledger →
          </Link>
        </p>
      </div>
    </section>
  )
}
