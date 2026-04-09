"use client"

import { useState, useMemo } from "react"
import Link from "next/link"
import { motion } from "framer-motion"
import { GUIDE_CATEGORIES, type GuideCategory, type GuideMetadata } from "@/lib/guides"
import { GuideCard } from "./guide-card"

interface GuidesContentProps {
  grouped: Record<GuideCategory, GuideMetadata[]>
  allGuides: GuideMetadata[]
}

function formatDate(iso: string): string {
  const date = new Date(iso)
  if (isNaN(date.getTime())) return iso
  return date.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })
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

  // Find featured guide (Elimination Filters)
  const featuredGuide = allGuides.find((g) => g.slug === "elimination-filters")

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
        /* Category tabs and featured card */
        <div>
          {/* Pill-style tab filters */}
          <div role="tablist" className="flex flex-wrap gap-2 mb-8">
            {GUIDE_CATEGORIES.map((cat) => (
              <button
                key={cat}
                role="tab"
                aria-selected={active === cat}
                onClick={() => setActive(cat)}
                className={`px-4 py-2 rounded-full text-sm font-medium transition-all ${
                  active === cat
                    ? "bg-accent text-bg-primary"
                    : "bg-bg-elevated border border-border-subtle text-text-tertiary hover:text-text-secondary hover:bg-bg-primary"
                }`}
              >
                {cat} ({grouped[cat].length})
              </button>
            ))}
          </div>

          {/* Featured guide */}
          {featuredGuide && (
            <div className="mb-8">
              <p className="text-caption text-text-tertiary mb-3">Featured</p>
              <motion.div
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
              >
                <Link
                  href={`/guides/${featuredGuide.slug}`}
                  className="block bg-bg-elevated border border-accent/40 rounded-lg p-5 hover:bg-bg-elevated/80 hover:-translate-y-0.5 transition-all duration-200 relative overflow-hidden border-l-2"
                  style={{ borderLeftColor: "var(--color-accent)" }}
                >
                  <div className="flex items-start justify-between gap-4 mb-3">
                    <h3 className="text-[18px] font-semibold text-accent flex-1">
                      {featuredGuide.title}
                    </h3>
                    <span className="text-xs font-medium text-accent bg-accent/10 px-2 py-1 rounded shrink-0">
                      {featuredGuide.category}
                    </span>
                  </div>
                  <p className="text-[14px] text-text-secondary line-clamp-2 mb-3">
                    {featuredGuide.description}
                  </p>
                  <div className="flex items-center gap-3 text-[12px] text-text-tertiary">
                    <span>{featuredGuide.readingTime} min read</span>
                    <span>&middot;</span>
                    <span>Updated {formatDate(featuredGuide.updatedAt)}</span>
                  </div>
                </Link>
              </motion.div>
            </div>
          )}

          {/* Category grid */}
          <div role="tabpanel" className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {grouped[active]
              .filter((g) => g.slug !== "elimination-filters") // Don't show featured guide in grid
              .map((guide, index) => (
                <GuideCard key={guide.slug} guide={guide} index={index} />
              ))}
          </div>
        </div>
      )}
    </div>
  )
}
