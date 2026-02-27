"use client"

import { useState } from "react"
import { GUIDE_CATEGORIES, type GuideCategory, type GuideMetadata } from "@/lib/guides"
import { GuideCard } from "./guide-card"

interface GuideCategoryTabsProps {
  grouped: Record<GuideCategory, GuideMetadata[]>
}

export function GuideCategoryTabs({ grouped }: GuideCategoryTabsProps) {
  const [active, setActive] = useState<GuideCategory>("Concepts")

  return (
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
  )
}
