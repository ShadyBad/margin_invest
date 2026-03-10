"use client"

import Link from "next/link"
import { motion } from "framer-motion"
import type { GuideMetadata } from "@/lib/guides"

const CATEGORY_COLORS: Record<string, string> = {
  Concepts: "var(--color-accent)",
  Workflows: "var(--color-accent-warm)",
  Reference: "var(--color-text-tertiary)",
}

function formatDate(iso: string): string {
  const date = new Date(iso)
  if (isNaN(date.getTime())) return iso
  return date.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })
}

interface GuideCardProps {
  guide: GuideMetadata
  index: number
}

export function GuideCard({ guide, index }: GuideCardProps) {
  const accentColor = CATEGORY_COLORS[guide.category] ?? "var(--color-accent)"

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: index * 0.08, ease: [0.22, 1, 0.36, 1] }}
    >
      <Link
        href={`/guides/${guide.slug}`}
        className="block bg-bg-elevated border border-border-subtle rounded-lg p-6 shadow-card hover:shadow-card-hover hover:-translate-y-0.5 transition-all duration-200 relative overflow-hidden border-l-2"
        style={{ borderLeftColor: accentColor }}
      >
        <h3 className="text-[18px] font-semibold text-text-primary mb-2">{guide.title}</h3>
        <p className="text-[14px] text-text-secondary line-clamp-2 mb-4">{guide.description}</p>
        <div className="flex items-center gap-3 text-[12px] text-text-tertiary">
          <span>{guide.readingTime} min read</span>
          <span>&middot;</span>
          <span>Updated {formatDate(guide.updatedAt)}</span>
        </div>
      </Link>
    </motion.div>
  )
}
