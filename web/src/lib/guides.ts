import fs from "fs/promises"
import path from "path"

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
// Constants
// ---------------------------------------------------------------------------

const GUIDES_DIR = path.join(process.cwd(), "src/content/guides")

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

// ---------------------------------------------------------------------------
// Frontmatter parsing (simple line-by-line, no external YAML library)
// ---------------------------------------------------------------------------

function parseFrontmatter(raw: string): {
  frontmatter: GuideFrontmatter
  content: string
} {
  const lines = raw.split("\n")

  // Expect first line to be "---"
  if (lines[0].trim() !== "---") {
    throw new Error("Missing opening frontmatter delimiter")
  }

  let closingIndex = -1
  for (let i = 1; i < lines.length; i++) {
    if (lines[i].trim() === "---") {
      closingIndex = i
      break
    }
  }

  if (closingIndex === -1) {
    throw new Error("Missing closing frontmatter delimiter")
  }

  const fmLines = lines.slice(1, closingIndex)
  const data: Record<string, string | number> = {}

  for (const line of fmLines) {
    const colonIndex = line.indexOf(":")
    if (colonIndex === -1) continue

    const key = line.slice(0, colonIndex).trim()
    let value: string | number = line.slice(colonIndex + 1).trim()

    // Strip surrounding quotes
    if (
      (value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"))
    ) {
      value = value.slice(1, -1)
    }

    // Parse numeric values for known numeric fields
    if (key === "order" || key === "readingTime") {
      const num = Number(value)
      if (!Number.isNaN(num)) {
        value = num
      }
    }

    data[key] = value
  }

  const content = lines.slice(closingIndex + 1).join("\n").replace(/^\n+/, "")

  return {
    frontmatter: {
      title: String(data.title ?? ""),
      description: String(data.description ?? ""),
      order: Number(data.order ?? 0),
      updatedAt: String(data.updatedAt ?? ""),
      readingTime: Number(data.readingTime ?? 0),
      category: String(data.category ?? ""),
    },
    content,
  }
}

// ---------------------------------------------------------------------------
// File I/O functions (server-side only)
// ---------------------------------------------------------------------------

/**
 * Read all `.mdx` files from the guides content directory,
 * parse frontmatter from each, and return sorted by `order`.
 * Returns empty array if directory doesn't exist.
 */
export async function getAllGuides(): Promise<GuideMetadata[]> {
  try {
    const entries = await fs.readdir(GUIDES_DIR)
    const mdxFiles = entries.filter((f) => f.endsWith(".mdx"))

    const guides: GuideMetadata[] = []

    for (const file of mdxFiles) {
      const filePath = path.join(GUIDES_DIR, file)
      const raw = await fs.readFile(filePath, "utf-8")
      const { frontmatter } = parseFrontmatter(raw)
      const slug = file.replace(/\.mdx$/, "")
      guides.push({ ...frontmatter, slug })
    }

    return guides.sort((a, b) => a.order - b.order)
  } catch {
    return []
  }
}

/**
 * Read a single `.mdx` file by slug (filename without extension).
 * Return null if not found.
 * Returns frontmatter + content (everything after the `---` frontmatter block).
 */
export async function getGuideBySlug(
  slug: string,
): Promise<{ frontmatter: GuideFrontmatter; source: string } | null> {
  try {
    const filePath = path.join(GUIDES_DIR, `${slug}.mdx`)
    const raw = await fs.readFile(filePath, "utf-8")
    const { frontmatter, content } = parseFrontmatter(raw)
    return { frontmatter, source: content }
  } catch {
    return null
  }
}

/**
 * Return array of all guide slugs (filenames without `.mdx`).
 * Returns empty array if directory doesn't exist.
 */
export async function getAllGuideSlugs(): Promise<string[]> {
  try {
    const entries = await fs.readdir(GUIDES_DIR)
    return entries.filter((f) => f.endsWith(".mdx")).map((f) => f.replace(/\.mdx$/, ""))
  } catch {
    return []
  }
}
