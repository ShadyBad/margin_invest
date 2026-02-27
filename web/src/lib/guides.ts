// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface GuideFrontmatter {
  title: string
  description: string
  order: number
  updatedAt: string
  readingTime: number
  category: string
}

export interface GuideMetadata extends GuideFrontmatter {
  slug: string
}

export interface TocHeading {
  level: number
  text: string
  id: string
}

// ---------------------------------------------------------------------------
// Category grouping
// ---------------------------------------------------------------------------

export const GUIDE_CATEGORIES = ["Concepts", "Workflows", "Reference"] as const
export type GuideCategory = (typeof GUIDE_CATEGORIES)[number]

export function groupGuidesByCategory(
  guides: GuideMetadata[],
): Record<GuideCategory, GuideMetadata[]> {
  const grouped: Record<GuideCategory, GuideMetadata[]> = {
    Concepts: [],
    Workflows: [],
    Reference: [],
  }
  for (const guide of guides) {
    const cat = guide.category as GuideCategory
    if (cat in grouped) {
      grouped[cat].push(guide)
    }
  }
  return grouped
}

// ---------------------------------------------------------------------------
// Pure helpers
// ---------------------------------------------------------------------------

/**
 * Convert text to a URL-safe slug.
 * Lowercase, spaces become hyphens, strip non-word chars except hyphens.
 */
export function slugify(text: string): string {
  return text
    .toLowerCase()
    .trim()
    .replace(/\s+/g, "-")
    .replace(/[^\w-]/g, "")
}

/**
 * Extract H2 and H3 headings from MDX source via regex.
 * Generates `id` from heading text via slugify.
 * Handles duplicate headings by appending `-1`, `-2` etc.
 */
export function extractTocHeadings(source: string): TocHeading[] {
  const regex = /^(#{2,3})\s+(.+)$/gm
  const headings: TocHeading[] = []
  const idCounts = new Map<string, number>()

  let match: RegExpExecArray | null
  while ((match = regex.exec(source)) !== null) {
    const level = match[1].length
    const text = match[2].trim()
    const baseId = slugify(text)

    const count = idCounts.get(baseId) ?? 0
    const id = count === 0 ? baseId : `${baseId}-${count}`
    idCounts.set(baseId, count + 1)

    headings.push({ level, text, id })
  }

  return headings
}
