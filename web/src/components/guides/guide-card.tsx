"use client"

import Link from "next/link"
import { motion } from "framer-motion"
import type { GuideMetadata } from "@/lib/guides"

const CATEGORY_COLORS: Record<string, string> = {
  Concepts: "var(--color-accent)",
  Workflows: "var(--color-accent-warm)",
  Reference: "var(--color-text-tertiary)",
}

const CATEGORY_BG: Record<string, string> = {
  Concepts: "bg-accent/10",
  Workflows: "bg-[var(--color-accent-warm)]/10",
  Reference: "bg-text-tertiary/10",
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
  const bgClass = CATEGORY_BG[guide.category] ?? "bg-accent/10"

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: index * 0.08, ease: [0.22, 1, 0.36, 1] }}
    >
      <Link
        href={`/guides/${guide.slug}`}
        className="group/card block bg-bg-elevated border border-border-subtle rounded-lg p-5 hover:bg-bg-elevated/80 hover:-translate-y-0.5 transition-all duration-200 relative overflow-hidden border-l-2"
        style={{ borderLeftColor: accentColor }}
      >
        <div className="flex items-start justify-between gap-3 mb-3">
          <h3 className="text-[16px] font-semibold text-text-primary flex-1">{guide.title}</h3>
          <span className={`text-xs font-medium text-text-tertiary ${bgClass} px-2 py-1 rounded shrink-0`}>
            {guide.category}
          </span>
        </div>
        <p className="text-[14px] text-text-secondary line-clamp-2 mb-4">{guide.description}</p>
        <div className="flex items-center justify-between text-[12px] text-text-tertiary">
          <div className="flex items-center gap-3">
            <span>{guide.readingTime} min read</span>
            <span>&middot;</span>
            <span>Updated {formatDate(guide.updatedAt)}</span>
          </div>
          <span className="opacity-0 group-hover/card:opacity-100 transition-opacity text-accent" aria-hidden="true">→</span>
        </div>
      </Link>
    </motion.div>
  )
}
