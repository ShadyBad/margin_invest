import fs from "fs/promises"
import path from "path"

import type { GuideFrontmatter, GuideMetadata } from "./guides"

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const GUIDES_DIR = path.join(process.cwd(), "src/content/guides")

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
