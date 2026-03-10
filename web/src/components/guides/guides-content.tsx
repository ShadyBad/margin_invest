"use client"

import { useState, useMemo } from "react"
import { GUIDE_CATEGORIES, type GuideCategory, type GuideMetadata } from "@/lib/guides"
import { GuideCard } from "./guide-card"

interface GuidesContentProps {
  grouped: Record<GuideCategory, GuideMetadata[]>
  allGuides: GuideMetadata[]
}

export function GuidesContent({ grouped, allGuides }: GuidesContentProps) {
  const [active, setActive] = useState<GuideCategory>("Concepts")
  const [query, setQuery] = useState("")

  const filteredGuides = useMemo(() => {
    const term = query.trim().toLowerCase()
    if (!term) return null
    return allGuides.filter(
      (g) =>
        g.title.toLowerCase().includes(term) ||
        g.description.toLowerCase().includes(term)
    )
  }, [query, allGuides])

  const isSearching = filteredGuides !== null

  return (
    <div>
      {/* Search bar */}
      <div className="relative mb-8">
        <svg
          className="absolute left-3 top-1/2 -translate-y-1/2 text-text-tertiary pointer-events-none"
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <circle cx="11" cy="11" r="8" />
          <path d="m21 21-4.3-4.3" />
        </svg>
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search guides by title or description..."
          className="w-full h-10 pl-10 pr-4 rounded-lg bg-bg-elevated border border-border-subtle text-[14px] text-text-primary placeholder-text-tertiary focus:border-accent focus:ring-1 focus:ring-accent/30 focus:outline-none transition-colors"
          aria-label="Search guides"
        />
      </div>

      {isSearching ? (
        /* Search results */
        <div>
          <p className="text-caption text-text-tertiary mb-4">
            {filteredGuides.length} {filteredGuides.length === 1 ? "result" : "results"} for &ldquo;{query.trim()}&rdquo;
          </p>
          {filteredGuides.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {filteredGuides.map((guide, index) => (
                <GuideCard key={guide.slug} guide={guide} index={index} />
              ))}
            </div>
          ) : (
            <p className="text-body text-text-secondary py-8 text-center">
              No guides match your search. Try different keywords.
            </p>
          )}
        </div>
      ) : (
        /* Category tabs */
        <div>
          <div role="tablist" className="flex gap-4 border-b border-border-subtle mb-8">
            {GUIDE_CATEGORIES.map((cat) => (
              <button
                key={cat}
                role="tab"
                aria-selected={active === cat}
                onClick={() => setActive(cat)}
                className={`pb-3 px-1 text-sm font-medium border-b-2 transition-colors ${
                  active === cat
                    ? "border-accent text-accent"
                    : "border-transparent text-text-tertiary hover:text-text-secondary"
                }`}
              >
                {cat} ({grouped[cat].length})
              </button>
            ))}
          </div>

          <div role="tabpanel" className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {grouped[active].map((guide, index) => (
              <GuideCard key={guide.slug} guide={guide} index={index} />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
