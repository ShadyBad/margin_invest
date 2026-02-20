# Guides Feature Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a public-facing Guides section at `/guides` with MDX-powered content, card grid index, individual guide pages with sticky TOC, and 6 initial guides covering the V3 dual-track scoring engine.

**Architecture:** MDX files in `web/src/content/guides/` with YAML frontmatter. `next-mdx-remote` compiles MDX at render time in RSC pages. A utility module (`lib/guides.ts`) reads files, parses frontmatter, and extracts TOC headings. Index page renders a responsive card grid; guide pages render MDX with custom components and a sticky sidebar TOC with scroll-spy.

**Tech Stack:** Next.js 16 (app router, RSC), next-mdx-remote (RSC), Tailwind CSS v4, Framer Motion, Vitest + React Testing Library

**Design doc:** `docs/plans/2026-02-19-guides-feature-design.md`

---

## Task 1: Install next-mdx-remote

**Files:**
- Modify: `web/package.json`

**Step 1: Install the dependency**

Run from repo root:
```bash
cd web && npm install next-mdx-remote
```

**Step 2: Verify installation**

```bash
cd web && node -e "require('next-mdx-remote/rsc')" && echo "OK"
```
Expected: `OK` (no errors)

**Step 3: Commit**

```bash
git add web/package.json web/package-lock.json
git commit -m "chore: install next-mdx-remote for guides MDX rendering"
```

---

## Task 2: Guide loader utility (`lib/guides.ts`)

**Files:**
- Create: `web/src/lib/guides.ts`
- Create: `web/src/lib/__tests__/guides.test.ts`

**Step 1: Write the failing tests**

Create `web/src/lib/__tests__/guides.test.ts`:

```typescript
import { describe, it, expect, vi, beforeEach } from "vitest"

// We'll test the pure functions: parseFrontmatter, extractTocHeadings, getSlugFromFilename
// File I/O functions (getAllGuides, getGuideBySlug) are tested via integration

describe("extractTocHeadings", () => {
  it("extracts H2 and H3 headings from MDX source", async () => {
    const { extractTocHeadings } = await import("../guides")
    const source = `
# Title (ignored)

## Getting Started

Some text here.

### Prerequisites

More text.

### Installation

Even more text.

## Advanced Usage

Final text.
`
    const headings = extractTocHeadings(source)
    expect(headings).toEqual([
      { level: 2, text: "Getting Started", id: "getting-started" },
      { level: 3, text: "Prerequisites", id: "prerequisites" },
      { level: 3, text: "Installation", id: "installation" },
      { level: 2, text: "Advanced Usage", id: "advanced-usage" },
    ])
  })

  it("returns empty array for source with no headings", async () => {
    const { extractTocHeadings } = await import("../guides")
    expect(extractTocHeadings("Just some text.")).toEqual([])
  })

  it("generates unique IDs for duplicate headings", async () => {
    const { extractTocHeadings } = await import("../guides")
    const source = `
## Overview

## Overview
`
    const headings = extractTocHeadings(source)
    expect(headings[0].id).toBe("overview")
    expect(headings[1].id).toBe("overview-1")
  })
})

describe("slugify", () => {
  it("converts heading text to URL-safe slug", async () => {
    const { slugify } = await import("../guides")
    expect(slugify("Getting Started")).toBe("getting-started")
    expect(slugify("Metrics & Terminology")).toBe("metrics--terminology")
    expect(slugify("What is ROIC?")).toBe("what-is-roic")
  })
})
```

**Step 2: Run tests to verify they fail**

```bash
cd web && npx vitest run src/lib/__tests__/guides.test.ts
```
Expected: FAIL — module `../guides` does not export these functions.

**Step 3: Implement the guide loader**

Create `web/src/lib/guides.ts`:

```typescript
import fs from "fs"
import path from "path"

const GUIDES_DIR = path.join(process.cwd(), "src/content/guides")

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

export function slugify(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^\w\s-]/g, "")
    .replace(/\s+/g, "-")
    .replace(/-+/g, "-")
    .trim()
}

export function extractTocHeadings(source: string): TocHeading[] {
  const headingRegex = /^(#{2,3})\s+(.+)$/gm
  const headings: TocHeading[] = []
  const idCounts = new Map<string, number>()

  let match
  while ((match = headingRegex.exec(source)) !== null) {
    const level = match[1].length
    const text = match[2].trim()
    let id = slugify(text)

    const count = idCounts.get(id) || 0
    if (count > 0) {
      id = `${id}-${count}`
    }
    idCounts.set(slugify(text), count + 1)

    headings.push({ level, text, id })
  }

  return headings
}

function parseFrontmatter(fileContent: string): {
  frontmatter: GuideFrontmatter
  content: string
} {
  const frontmatterRegex = /^---\n([\s\S]*?)\n---\n([\s\S]*)$/
  const match = fileContent.match(frontmatterRegex)

  if (!match) {
    throw new Error("Invalid frontmatter format")
  }

  const rawFrontmatter = match[1]
  const content = match[2]

  const frontmatter: Record<string, string | number> = {}
  for (const line of rawFrontmatter.split("\n")) {
    const colonIndex = line.indexOf(":")
    if (colonIndex === -1) continue
    const key = line.slice(0, colonIndex).trim()
    let value: string | number = line.slice(colonIndex + 1).trim()
    // Strip surrounding quotes
    if (value.startsWith('"') && value.endsWith('"')) {
      value = value.slice(1, -1)
    }
    // Parse numbers
    if (key === "order" || key === "readingTime") {
      value = parseInt(value as string, 10)
    }
    frontmatter[key] = value
  }

  return { frontmatter: frontmatter as unknown as GuideFrontmatter, content }
}

export async function getAllGuides(): Promise<GuideMetadata[]> {
  if (!fs.existsSync(GUIDES_DIR)) return []

  const files = fs.readdirSync(GUIDES_DIR).filter((f) => f.endsWith(".mdx"))

  const guides: GuideMetadata[] = files.map((filename) => {
    const filePath = path.join(GUIDES_DIR, filename)
    const fileContent = fs.readFileSync(filePath, "utf-8")
    const { frontmatter } = parseFrontmatter(fileContent)
    const slug = filename.replace(/\.mdx$/, "")
    return { ...frontmatter, slug }
  })

  return guides.sort((a, b) => a.order - b.order)
}

export async function getGuideBySlug(
  slug: string
): Promise<{ frontmatter: GuideFrontmatter; source: string } | null> {
  const filePath = path.join(GUIDES_DIR, `${slug}.mdx`)

  if (!fs.existsSync(filePath)) return null

  const fileContent = fs.readFileSync(filePath, "utf-8")
  const { frontmatter, content } = parseFrontmatter(fileContent)

  return { frontmatter, source: content }
}

export async function getAllGuideSlugs(): Promise<string[]> {
  if (!fs.existsSync(GUIDES_DIR)) return []

  return fs
    .readdirSync(GUIDES_DIR)
    .filter((f) => f.endsWith(".mdx"))
    .map((f) => f.replace(/\.mdx$/, ""))
}
```

**Step 4: Run tests to verify they pass**

```bash
cd web && npx vitest run src/lib/__tests__/guides.test.ts
```
Expected: All 4 tests PASS.

**Step 5: Commit**

```bash
git add web/src/lib/guides.ts web/src/lib/__tests__/guides.test.ts
git commit -m "feat(guides): add guide loader utility with frontmatter parsing and TOC extraction"
```

---

## Task 3: Custom MDX components

**Files:**
- Create: `web/src/components/guides/mdx-components.tsx`
- Create: `web/src/components/guides/__tests__/mdx-components.test.tsx`

**Step 1: Write the failing tests**

Create `web/src/components/guides/__tests__/mdx-components.test.tsx`:

```tsx
import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { Callout, Formula, Example } from "../mdx-components"

describe("Callout", () => {
  it("renders info callout with content", () => {
    render(<Callout type="info">Important note here</Callout>)
    expect(screen.getByText("Important note here")).toBeInTheDocument()
  })

  it("renders warning callout", () => {
    render(<Callout type="warning">Watch out</Callout>)
    expect(screen.getByText("Watch out")).toBeInTheDocument()
  })

  it("renders tip callout", () => {
    render(<Callout type="tip">Pro tip</Callout>)
    expect(screen.getByText("Pro tip")).toBeInTheDocument()
  })
})

describe("Formula", () => {
  it("renders formula in monospace", () => {
    render(<Formula>ROIC = NOPAT / IC</Formula>)
    expect(screen.getByText("ROIC = NOPAT / IC")).toBeInTheDocument()
  })
})

describe("Example", () => {
  it("renders example block with title", () => {
    render(<Example title="Walkthrough">Step 1: Do this</Example>)
    expect(screen.getByText("Walkthrough")).toBeInTheDocument()
    expect(screen.getByText("Step 1: Do this")).toBeInTheDocument()
  })

  it("renders example block without title", () => {
    render(<Example>Just content</Example>)
    expect(screen.getByText("Just content")).toBeInTheDocument()
  })
})
```

**Step 2: Run tests to verify they fail**

```bash
cd web && npx vitest run src/components/guides/__tests__/mdx-components.test.tsx
```
Expected: FAIL — module not found.

**Step 3: Implement the MDX components**

Create `web/src/components/guides/mdx-components.tsx`:

```tsx
import type { ReactNode } from "react"

const calloutStyles = {
  info: {
    border: "border-l-accent",
    bg: "bg-accent-subtle",
    icon: "i",
    label: "Note",
  },
  warning: {
    border: "border-l-warning",
    bg: "bg-[rgba(184,134,11,0.08)]",
    icon: "!",
    label: "Warning",
  },
  tip: {
    border: "border-l-bullish",
    bg: "bg-[rgba(16,185,129,0.08)]",
    icon: "\u2713",
    label: "Tip",
  },
} as const

export function Callout({
  type = "info",
  children,
}: {
  type?: "info" | "warning" | "tip"
  children: ReactNode
}) {
  const style = calloutStyles[type]
  return (
    <div
      className={`${style.bg} ${style.border} border-l-4 rounded-r-lg px-4 py-3 my-6`}
    >
      <p className="text-[13px] font-semibold text-text-secondary mb-1 uppercase tracking-wider">
        {style.label}
      </p>
      <div className="text-text-secondary body-text">{children}</div>
    </div>
  )
}

export function Formula({ children }: { children: ReactNode }) {
  return (
    <div className="bg-bg-subtle rounded-lg px-4 py-3 my-6 font-mono text-[14px] text-text-primary overflow-x-auto">
      {children}
    </div>
  )
}

export function Example({
  title,
  children,
}: {
  title?: string
  children: ReactNode
}) {
  return (
    <div className="bg-bg-elevated border border-border-subtle rounded-lg px-5 py-4 my-6">
      {title && (
        <p className="text-[13px] font-semibold text-text-secondary mb-2 uppercase tracking-wider">
          {title}
        </p>
      )}
      <div className="text-text-secondary body-text">{children}</div>
    </div>
  )
}

// Heading components that add id attributes for TOC scroll-spy
function createHeading(level: 2 | 3) {
  const Tag = `h${level}` as const
  const className =
    level === 2
      ? "heading-3 text-text-primary mt-12 mb-4 scroll-mt-24"
      : "text-[18px] md:text-[20px] font-semibold text-text-primary mt-8 mb-3 scroll-mt-24"

  return function Heading({ children }: { children?: ReactNode }) {
    const text = typeof children === "string" ? children : ""
    const id = text
      .toLowerCase()
      .replace(/[^\w\s-]/g, "")
      .replace(/\s+/g, "-")
      .replace(/-+/g, "-")
      .trim()

    return (
      <Tag id={id} className={className}>
        {children}
      </Tag>
    )
  }
}

// Full component map for MDX rendering
export const mdxComponents = {
  h2: createHeading(2),
  h3: createHeading(3),
  p: ({ children }: { children?: ReactNode }) => (
    <p className="body-text text-text-secondary mb-4 leading-relaxed">{children}</p>
  ),
  ul: ({ children }: { children?: ReactNode }) => (
    <ul className="list-disc list-outside ml-5 mb-4 space-y-1 text-text-secondary body-text">
      {children}
    </ul>
  ),
  ol: ({ children }: { children?: ReactNode }) => (
    <ol className="list-decimal list-outside ml-5 mb-4 space-y-1 text-text-secondary body-text">
      {children}
    </ol>
  ),
  li: ({ children }: { children?: ReactNode }) => (
    <li className="text-text-secondary">{children}</li>
  ),
  strong: ({ children }: { children?: ReactNode }) => (
    <strong className="font-semibold text-text-primary">{children}</strong>
  ),
  a: ({ href, children }: { href?: string; children?: ReactNode }) => (
    <a
      href={href}
      className="text-accent hover:text-accent-hover underline underline-offset-2 transition-colors"
    >
      {children}
    </a>
  ),
  code: ({ children }: { children?: ReactNode }) => (
    <code className="bg-bg-subtle rounded px-1.5 py-0.5 text-[14px] font-mono text-text-primary">
      {children}
    </code>
  ),
  table: ({ children }: { children?: ReactNode }) => (
    <div className="overflow-x-auto my-6">
      <table className="w-full text-[14px] text-text-secondary">{children}</table>
    </div>
  ),
  th: ({ children }: { children?: ReactNode }) => (
    <th className="text-left text-text-primary font-semibold pb-2 pr-4 border-b border-border-primary">
      {children}
    </th>
  ),
  td: ({ children }: { children?: ReactNode }) => (
    <td className="py-2 pr-4 border-b border-border-subtle">{children}</td>
  ),
  hr: () => <hr className="border-border-subtle my-8" />,
  Callout,
  Formula,
  Example,
}
```

**Step 4: Run tests to verify they pass**

```bash
cd web && npx vitest run src/components/guides/__tests__/mdx-components.test.tsx
```
Expected: All 6 tests PASS.

**Step 5: Commit**

```bash
git add web/src/components/guides/mdx-components.tsx web/src/components/guides/__tests__/mdx-components.test.tsx
git commit -m "feat(guides): add custom MDX components (Callout, Formula, Example) with tests"
```

---

## Task 4: Table of Contents component with scroll-spy

**Files:**
- Create: `web/src/components/guides/table-of-contents.tsx`
- Create: `web/src/components/guides/__tests__/table-of-contents.test.tsx`

**Step 1: Write the failing tests**

Create `web/src/components/guides/__tests__/table-of-contents.test.tsx`:

```tsx
import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { TableOfContents } from "../table-of-contents"

const headings = [
  { level: 2, text: "Getting Started", id: "getting-started" },
  { level: 3, text: "Prerequisites", id: "prerequisites" },
  { level: 3, text: "Installation", id: "installation" },
  { level: 2, text: "Advanced Usage", id: "advanced-usage" },
]

describe("TableOfContents", () => {
  it("renders all heading links", () => {
    render(<TableOfContents headings={headings} />)
    expect(screen.getByText("Getting Started")).toBeInTheDocument()
    expect(screen.getByText("Prerequisites")).toBeInTheDocument()
    expect(screen.getByText("Installation")).toBeInTheDocument()
    expect(screen.getByText("Advanced Usage")).toBeInTheDocument()
  })

  it("renders H3 items with indentation", () => {
    render(<TableOfContents headings={headings} />)
    const prereq = screen.getByText("Prerequisites").closest("a")
    expect(prereq?.className).toContain("pl-4")
  })

  it("links to correct heading IDs", () => {
    render(<TableOfContents headings={headings} />)
    const link = screen.getByText("Getting Started").closest("a")
    expect(link).toHaveAttribute("href", "#getting-started")
  })

  it("renders nothing when headings is empty", () => {
    const { container } = render(<TableOfContents headings={[]} />)
    expect(container.firstChild).toBeNull()
  })
})
```

**Step 2: Run tests to verify they fail**

```bash
cd web && npx vitest run src/components/guides/__tests__/table-of-contents.test.tsx
```
Expected: FAIL — module not found.

**Step 3: Implement the component**

Create `web/src/components/guides/table-of-contents.tsx`:

```tsx
"use client"

import { useEffect, useState } from "react"
import type { TocHeading } from "@/lib/guides"

interface TableOfContentsProps {
  headings: TocHeading[]
}

export function TableOfContents({ headings }: TableOfContentsProps) {
  const [activeId, setActiveId] = useState<string>("")

  useEffect(() => {
    if (headings.length === 0) return

    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            setActiveId(entry.target.id)
          }
        }
      },
      { rootMargin: "-96px 0px -80% 0px", threshold: 0 }
    )

    for (const heading of headings) {
      const el = document.getElementById(heading.id)
      if (el) observer.observe(el)
    }

    return () => observer.disconnect()
  }, [headings])

  if (headings.length === 0) return null

  return (
    <nav aria-label="Table of contents" className="text-[13px]">
      <p className="font-semibold text-text-primary mb-3 uppercase tracking-wider">
        On this page
      </p>
      <ul className="space-y-1">
        {headings.map((heading) => (
          <li key={heading.id}>
            <a
              href={`#${heading.id}`}
              className={`block py-1 transition-colors duration-200 ${
                heading.level === 3 ? "pl-4" : ""
              } ${
                activeId === heading.id
                  ? "text-accent font-medium"
                  : "text-text-tertiary hover:text-text-secondary"
              }`}
              onClick={(e) => {
                e.preventDefault()
                document.getElementById(heading.id)?.scrollIntoView({ behavior: "smooth" })
                setActiveId(heading.id)
              }}
            >
              {heading.text}
            </a>
          </li>
        ))}
      </ul>
    </nav>
  )
}
```

**Step 4: Run tests to verify they pass**

```bash
cd web && npx vitest run src/components/guides/__tests__/table-of-contents.test.tsx
```
Expected: All 4 tests PASS.

**Step 5: Commit**

```bash
git add web/src/components/guides/table-of-contents.tsx web/src/components/guides/__tests__/table-of-contents.test.tsx
git commit -m "feat(guides): add TableOfContents component with scroll-spy"
```

---

## Task 5: Guide card component

**Files:**
- Create: `web/src/components/guides/guide-card.tsx`
- Create: `web/src/components/guides/__tests__/guide-card.test.tsx`

**Step 1: Write the failing tests**

Create `web/src/components/guides/__tests__/guide-card.test.tsx`:

```tsx
import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { GuideCard } from "../guide-card"

const guide = {
  slug: "how-scoring-works",
  title: "How Scoring Works",
  description: "Understand the dual-track scoring engine.",
  order: 1,
  updatedAt: "2026-02-19",
  readingTime: 8,
  category: "Core Concepts",
}

describe("GuideCard", () => {
  it("renders title and description", () => {
    render(<GuideCard guide={guide} index={0} />)
    expect(screen.getByText("How Scoring Works")).toBeInTheDocument()
    expect(
      screen.getByText("Understand the dual-track scoring engine.")
    ).toBeInTheDocument()
  })

  it("renders reading time", () => {
    render(<GuideCard guide={guide} index={0} />)
    expect(screen.getByText("8 min read")).toBeInTheDocument()
  })

  it("links to the correct guide page", () => {
    render(<GuideCard guide={guide} index={0} />)
    const link = screen.getByRole("link")
    expect(link).toHaveAttribute("href", "/guides/how-scoring-works")
  })
})
```

**Step 2: Run tests to verify they fail**

```bash
cd web && npx vitest run src/components/guides/__tests__/guide-card.test.tsx
```
Expected: FAIL — module not found.

**Step 3: Implement the component**

Create `web/src/components/guides/guide-card.tsx`:

```tsx
"use client"

import Link from "next/link"
import { motion } from "framer-motion"
import type { GuideMetadata } from "@/lib/guides"

interface GuideCardProps {
  guide: GuideMetadata
  index: number
}

export function GuideCard({ guide, index }: GuideCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{
        duration: 0.4,
        delay: index * 0.08,
        ease: [0.22, 1, 0.36, 1],
      }}
    >
      <Link
        href={`/guides/${guide.slug}`}
        className="block bg-bg-elevated border border-border-subtle rounded-lg p-6 shadow-card hover:shadow-card-hover hover:-translate-y-0.5 transition-all duration-200"
      >
        <h2 className="text-[18px] font-semibold text-text-primary mb-2">
          {guide.title}
        </h2>
        <p className="text-[14px] text-text-secondary line-clamp-2 mb-4">
          {guide.description}
        </p>
        <div className="flex items-center gap-3 text-[12px] text-text-tertiary">
          <span>{guide.readingTime} min read</span>
          <span>&middot;</span>
          <span>Updated {guide.updatedAt}</span>
        </div>
      </Link>
    </motion.div>
  )
}
```

**Step 4: Run tests to verify they pass**

```bash
cd web && npx vitest run src/components/guides/__tests__/guide-card.test.tsx
```
Expected: All 3 tests PASS.

**Step 5: Commit**

```bash
git add web/src/components/guides/guide-card.tsx web/src/components/guides/__tests__/guide-card.test.tsx
git commit -m "feat(guides): add GuideCard component with staggered fade-in animation"
```

---

## Task 6: Guide layout wrapper

**Files:**
- Create: `web/src/components/guides/guide-layout.tsx`

This is a simple layout wrapper that composes the content area + TOC sidebar. No separate tests needed — it's a pure layout component tested via the page-level integration.

**Step 1: Implement the layout**

Create `web/src/components/guides/guide-layout.tsx`:

```tsx
import type { ReactNode } from "react"
import type { TocHeading } from "@/lib/guides"
import { TableOfContents } from "./table-of-contents"

interface GuideLayoutProps {
  children: ReactNode
  headings: TocHeading[]
}

export function GuideLayout({ children, headings }: GuideLayoutProps) {
  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
      <div className="lg:grid lg:grid-cols-[1fr_220px] lg:gap-12">
        <article className="min-w-0 max-w-prose">{children}</article>
        <aside className="hidden lg:block">
          <div className="sticky top-24">
            <TableOfContents headings={headings} />
          </div>
        </aside>
      </div>
    </div>
  )
}
```

**Step 2: Commit**

```bash
git add web/src/components/guides/guide-layout.tsx
git commit -m "feat(guides): add GuideLayout wrapper with sticky TOC sidebar"
```

---

## Task 7: Guides index page (`/guides`)

**Files:**
- Create: `web/src/app/guides/page.tsx`

**Step 1: Implement the index page**

Create `web/src/app/guides/page.tsx`:

```tsx
import type { Metadata } from "next"
import { Navbar } from "@/components/nav/navbar"
import { GuideCard } from "@/components/guides/guide-card"
import { getAllGuides } from "@/lib/guides"

export const metadata: Metadata = {
  title: "Guides | Margin Invest",
  description:
    "Learn how Margin Invest scores equities, interpret conviction ratings, and get the most from the platform.",
}

export default async function GuidesPage() {
  const guides = await getAllGuides()

  return (
    <main className="relative bg-bg-primary min-h-screen">
      <div className="relative z-10">
        <Navbar />

        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 pt-28 pb-16">
          <div className="max-w-2xl mb-12">
            <h1 className="heading-2 text-text-primary mb-4">Guides</h1>
            <p className="body-text text-text-secondary">
              Everything you need to understand how Margin Invest works and how
              to get the most from it.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {guides.map((guide, index) => (
              <GuideCard key={guide.slug} guide={guide} index={index} />
            ))}
          </div>
        </div>
      </div>
    </main>
  )
}
```

**Step 2: Commit**

```bash
git add web/src/app/guides/page.tsx
git commit -m "feat(guides): add /guides index page with card grid"
```

---

## Task 8: Individual guide page (`/guides/[slug]`)

**Files:**
- Create: `web/src/app/guides/[slug]/page.tsx`

**Step 1: Implement the guide detail page**

Create `web/src/app/guides/[slug]/page.tsx`:

```tsx
import type { Metadata } from "next"
import { notFound } from "next/navigation"
import Link from "next/link"
import { compileMDX } from "next-mdx-remote/rsc"
import { Navbar } from "@/components/nav/navbar"
import { GuideLayout } from "@/components/guides/guide-layout"
import { mdxComponents } from "@/components/guides/mdx-components"
import {
  getGuideBySlug,
  getAllGuideSlugs,
  extractTocHeadings,
  type GuideFrontmatter,
} from "@/lib/guides"

interface PageProps {
  params: Promise<{ slug: string }>
}

export async function generateStaticParams() {
  const slugs = await getAllGuideSlugs()
  return slugs.map((slug) => ({ slug }))
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { slug } = await params
  const guide = await getGuideBySlug(slug)
  if (!guide) return { title: "Guide Not Found | Margin Invest" }

  return {
    title: `${guide.frontmatter.title} | Margin Invest Guides`,
    description: guide.frontmatter.description,
  }
}

export default async function GuidePage({ params }: PageProps) {
  const { slug } = await params
  const guide = await getGuideBySlug(slug)

  if (!guide) notFound()

  const headings = extractTocHeadings(guide.source)

  const { content } = await compileMDX<GuideFrontmatter>({
    source: guide.source,
    components: mdxComponents,
    options: { parseFrontmatter: false },
  })

  return (
    <main className="relative bg-bg-primary min-h-screen">
      <div className="relative z-10">
        <Navbar />

        <div className="pt-28 pb-16">
          <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 mb-8">
            <Link
              href="/guides"
              className="text-[13px] text-text-tertiary hover:text-text-secondary transition-colors"
            >
              &larr; All Guides
            </Link>
          </div>

          <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 mb-10">
            <h1 className="heading-2 text-text-primary mb-3">
              {guide.frontmatter.title}
            </h1>
            <div className="flex items-center gap-3 text-[13px] text-text-tertiary">
              <span>{guide.frontmatter.readingTime} min read</span>
              <span>&middot;</span>
              <span>Updated {guide.frontmatter.updatedAt}</span>
            </div>
          </div>

          <GuideLayout headings={headings}>{content}</GuideLayout>
        </div>
      </div>
    </main>
  )
}
```

**Step 2: Commit**

```bash
git add web/src/app/guides/\[slug\]/page.tsx
git commit -m "feat(guides): add /guides/[slug] detail page with MDX rendering and TOC"
```

---

## Task 9: Navigation — add Guides to PUBLIC_LINKS

**Files:**
- Modify: `web/src/hooks/use-navigation.ts` (line 40)
- Modify: `web/src/hooks/__tests__/use-navigation.test.ts`

**Step 1: Read the existing nav test to understand current assertions**

File: `web/src/hooks/__tests__/use-navigation.test.ts`
Check what assertions exist for `PUBLIC_LINKS` and update accordingly.

**Step 2: Update the nav hook**

In `web/src/hooks/use-navigation.ts`, change line 40 from:

```typescript
const PUBLIC_LINKS: { href: string; label: string }[] = []
```

to:

```typescript
const PUBLIC_LINKS: { href: string; label: string }[] = [
  { href: "/guides", label: "Guides" },
]
```

**Step 3: Update nav tests**

Add/update test assertions to verify unauthenticated users see the Guides link. The existing navbar test at `web/src/components/nav/__tests__/navbar.test.tsx` already has `mockIsAuthenticated` logic — ensure the unauthenticated case includes the Guides link.

**Step 4: Run nav tests**

```bash
cd web && npx vitest run src/hooks/__tests__/use-navigation.test.ts src/components/nav/__tests__/navbar.test.tsx
```
Expected: All PASS.

**Step 5: Commit**

```bash
git add web/src/hooks/use-navigation.ts web/src/hooks/__tests__/use-navigation.test.ts web/src/components/nav/__tests__/navbar.test.tsx
git commit -m "feat(guides): add Guides link to public navigation"
```

---

## Task 10: Write guide content — How Scoring Works

**Files:**
- Create: `web/src/content/guides/how-scoring-works.mdx`

**Step 1: Write the guide content**

Create `web/src/content/guides/how-scoring-works.mdx` with the following content. This must reflect the real V3 dual-track engine from the codebase.

Frontmatter:
```yaml
---
title: "How Scoring Works"
description: "Understand the dual-track scoring engine that evaluates every candidate through Compounder and Mispricing lenses."
order: 1
updatedAt: "2026-02-19"
readingTime: 10
category: "Core Concepts"
---
```

Sections to cover (using real engine logic from `engine/src/margin_engine/scoring/`):
- **Overview**: 4-stage pipeline — elimination filters, dual-track scoring, conviction determination, position sizing
- **Stage 1: Elimination Filters**: Brief mention, link to the dedicated filters guide
- **Stage 2: Dual-Track Scoring**: Explain that every stock is independently evaluated on two tracks
- **Track A — Compounder**: 4 gates (Moat Evidence, Reinvestment Engine, Capital Allocation, Valuation). Explain each gate's purpose and what it measures. Use `<Formula>` for key formulas like `Compounding Power = Incremental ROIC x Reinvestment Rate x (1 - ROIC CV)`.
- **Track B — Mispricing**: 4 gates (Ensemble Valuation, Downside Protection, Catalyst, Quality Floor). Explain the 4-method valuation consensus, asymmetry ratio.
- **Multiplicative Scoring**: Explain why scores multiply rather than add — a zero in any factor yields zero. Use `<Formula>` blocks.
- **Conviction Levels**: EXCEPTIONAL, HIGH, WATCHLIST, NONE with the gate/threshold requirements for each
- **Worked Example**: A fictional company "TechCo" showing how it flows through both tracks. Use `<Example>` blocks.
- **Common Pitfalls**: Use `<Callout type="warning">` blocks. Cover: confusing track scores with composite score, assuming WATCHLIST means "buy soon", ignoring which track qualified.

Content guardrails: Educational only. Include a `<Callout type="info">` at the top noting this is for educational purposes and is not investment advice. Use fictional company names/numbers in examples.

**Step 2: Commit**

```bash
git add web/src/content/guides/how-scoring-works.mdx
git commit -m "content(guides): add How Scoring Works guide"
```

---

## Task 11: Write guide content — Elimination Filters Explained

**Files:**
- Create: `web/src/content/guides/elimination-filters.mdx`

**Step 1: Write the guide content**

Frontmatter:
```yaml
---
title: "Elimination Filters Explained"
description: "Learn about the binary pass/fail checks that screen out risky stocks before scoring begins."
order: 2
updatedAt: "2026-02-19"
readingTime: 7
category: "Core Concepts"
---
```

Sections to cover (real thresholds from `engine/src/margin_engine/scoring/filters/filter_config.py`):
- **Why Filters Exist**: Fail-fast principle — remove clearly distressed/manipulated companies before expensive scoring
- **The 6 Elimination Filters**: Each filter gets its own H2 section with:
  - What it measures (plain English)
  - Default threshold
  - Sector-specific adjustments (e.g., Utilities Altman exemption, Tech higher interest coverage)
  - Use `<Formula>` for formulas, tables for thresholds
- **Beneish M-Score**: Score > -1.78 flags manipulation risk
- **Altman Z-Score**: Score < 1.1 indicates distress (Utilities exempt)
- **Current Ratio**: Sector-adjusted (Tech 0.8, Utilities 0.6, default 0.8)
- **Interest Coverage**: 3-year median, sector-adjusted (Tech 5.0x, Utilities 1.2x, default 1.5x)
- **FCF Distress**: 3+ positive years in last 5, min margin -5%
- **Liquidity**: Market cap ($300M+ default) and dollar volume (tiered by cap size)
- **How Filters Run**: All 6 run regardless of earlier failures (complete diagnostics). Must pass ALL to proceed.
- **Common Pitfalls**: "Why was my stock eliminated?" — how to check which filter failed. `<Callout type="tip">` about sector adjustments.

**Step 2: Commit**

```bash
git add web/src/content/guides/elimination-filters.mdx
git commit -m "content(guides): add Elimination Filters guide"
```

---

## Task 12: Write guide content — Using Margin Invest Effectively

**Files:**
- Create: `web/src/content/guides/using-margin-invest.mdx`

**Step 1: Write the guide content**

Frontmatter:
```yaml
---
title: "Using Margin Invest Effectively"
description: "Practical workflows, decision checklists, and tips for getting the most value from the platform."
order: 3
updatedAt: "2026-02-19"
readingTime: 6
category: "Getting Started"
---
```

Sections:
- **Typical Workflow**: Weekly review cadence — check new candidates, review conviction changes, review eliminated stocks
- **Reading the Dashboard**: What each card shows — ticker, conviction badge, opportunity type (Compounder/Mispricing/Both), sector color bar
- **Interpreting Conviction Levels**: EXCEPTIONAL (top tier, rare), HIGH (strong, actionable), WATCHLIST (monitor, not actionable), NONE (below threshold)
- **Expanding a Candidate**: What the detail panel shows — factor breakdown, gate results, position sizing
- **Decision Checklist**: Bulleted list of questions to ask before acting on a candidate
- **Common Pitfalls**: Acting on WATCHLIST candidates, ignoring opportunity type context, assuming scores are static (they update as new data arrives)

**Step 2: Commit**

```bash
git add web/src/content/guides/using-margin-invest.mdx
git commit -m "content(guides): add Using Margin Invest Effectively guide"
```

---

## Task 13: Write guide content — Metrics & Terminology

**Files:**
- Create: `web/src/content/guides/metrics-and-terminology.mdx`

**Step 1: Write the guide content**

Frontmatter:
```yaml
---
title: "Metrics & Terminology"
description: "Definitions of every key term, metric, and score you will encounter in the Margin Invest UI."
order: 4
updatedAt: "2026-02-19"
readingTime: 8
category: "Reference"
---
```

Sections — each metric gets a brief definition, what it measures, and why it matters:
- **Conviction Levels**: EXCEPTIONAL, HIGH, WATCHLIST, NONE
- **Opportunity Types**: Compounder, Mispricing, Both, Neither
- **Growth Stages**: High Growth, Steady Growth, Mature, Cyclical, Turnaround — with the classification criteria
- **Track A Metrics**: Moat Durability Score (0-4), Compounding Power, Capital Allocation Composite, Growth Gap (Reverse DCF)
- **Track B Metrics**: Asymmetry Ratio, Catalyst Strength, Quality Floor Factor, Valuation Convergence
- **Financial Fundamentals**: ROIC, NOPAT, Invested Capital, FCF Yield, Revenue CAGR, Gross Profitability, Shareholder Yield
- **Filter Metrics**: Beneish M-Score, Altman Z-Score, Current Ratio, Interest Coverage

Use tables for groups of related terms. Use `<Formula>` for key formulas.

**Step 2: Commit**

```bash
git add web/src/content/guides/metrics-and-terminology.mdx
git commit -m "content(guides): add Metrics & Terminology reference guide"
```

---

## Task 14: Write guide content — Position Sizing

**Files:**
- Create: `web/src/content/guides/position-sizing.mdx`

**Step 1: Write the guide content**

Frontmatter:
```yaml
---
title: "Position Sizing & Portfolio Construction"
description: "How the engine determines suggested allocation sizes based on conviction and opportunity type."
order: 5
updatedAt: "2026-02-19"
readingTime: 5
category: "Core Concepts"
---
```

Sections (real values from engine code):
- **Maximum Positions**: 10 stocks max in the model portfolio
- **Sizing by Opportunity Type**: Table showing Compounder, Mispricing, Both allocations at each conviction level (EXCEPTIONAL: 15%/12%/20%, HIGH: 8%/6%/10%, WATCHLIST: 0%)
- **Why "Both" Gets the Largest Allocation**: Stocks qualifying on both tracks have the strongest combined signal
- **Risk Management Principles**: Diversification by sector, avoiding over-concentration
- **Common Pitfalls**: Over-concentrating in one sector, treating suggested sizes as exact targets, ignoring position sizing entirely

**Step 2: Commit**

```bash
git add web/src/content/guides/position-sizing.mdx
git commit -m "content(guides): add Position Sizing guide"
```

---

## Task 15: Write guide content — Data Sources & Freshness

**Files:**
- Create: `web/src/content/guides/data-freshness.mdx`

**Step 1: Write the guide content**

Frontmatter:
```yaml
---
title: "Data Sources & Freshness"
description: "Where data comes from, when it updates, and what to do when values look off."
order: 6
updatedAt: "2026-02-19"
readingTime: 5
category: "Reference"
---
```

Sections (real provider info from engine):
- **Data Provider Chains**: Table showing data type → primary provider → fallback(s). Fundamentals: FMP → yfinance → SEC EDGAR. Price: Polygon → yfinance. Insider: SEC EDGAR Form 4 → Finnhub. Institutional: SEC EDGAR 13F → Finnhub. Macro: FRED. News/Earnings: Finnhub → FMP.
- **Update Cadences**: Quarterly financials ~45 days after quarter end, price data daily, insider filings within 2 business days
- **Data Windows**: Up to 5 years historical, 60-day volume averaging
- **Troubleshooting Stale Data**: What to check, why some securities lack data, what "inconclusive" means on a filter
- **Known Limitations**: Some companies don't report all metrics, sector classification depends on GICS data availability, newly IPO'd companies may have incomplete histories

**Step 2: Commit**

```bash
git add web/src/content/guides/data-freshness.mdx
git commit -m "content(guides): add Data Sources & Freshness guide"
```

---

## Task 16: Smoke test — build and verify

**Files:** None (verification only)

**Step 1: Run all guide-related tests**

```bash
cd web && npx vitest run src/lib/__tests__/guides.test.ts src/components/guides/__tests__/
```
Expected: All tests PASS.

**Step 2: Run full test suite**

```bash
cd web && npx vitest run
```
Expected: All existing tests still pass + new tests pass.

**Step 3: Verify dev build renders correctly**

```bash
cd web && npm run build
```
Expected: Build succeeds. No TypeScript errors, no missing module errors.

**Step 4: Manual verification checklist**

Start dev server (`npm run dev`) and verify:
- [ ] `/guides` renders card grid with 6 guides
- [ ] Clicking a card navigates to `/guides/[slug]`
- [ ] MDX content renders (headings, lists, tables, Callout/Formula/Example components)
- [ ] TOC sidebar appears on desktop, hidden on mobile
- [ ] Scroll-spy highlights correct TOC item
- [ ] "← All Guides" link works
- [ ] Dark mode: all elements use correct theme tokens
- [ ] Unauthenticated users see Guides in nav
- [ ] Authenticated users see Guides in nav
- [ ] Deep link `/guides/how-scoring-works` works directly

**Step 5: Final commit (if any fixes needed)**

```bash
git add -A && git commit -m "fix(guides): address smoke test issues"
```

---

## Summary

| Task | Description | Files | Tests |
|------|-------------|-------|-------|
| 1 | Install next-mdx-remote | package.json | - |
| 2 | Guide loader utility | lib/guides.ts | 4 tests |
| 3 | Custom MDX components | components/guides/mdx-components.tsx | 6 tests |
| 4 | Table of Contents | components/guides/table-of-contents.tsx | 4 tests |
| 5 | Guide card | components/guides/guide-card.tsx | 3 tests |
| 6 | Guide layout | components/guides/guide-layout.tsx | - |
| 7 | Index page | app/guides/page.tsx | - |
| 8 | Detail page | app/guides/[slug]/page.tsx | - |
| 9 | Nav update | hooks/use-navigation.ts | update existing |
| 10 | Guide: How Scoring Works | content/guides/how-scoring-works.mdx | - |
| 11 | Guide: Elimination Filters | content/guides/elimination-filters.mdx | - |
| 12 | Guide: Using Effectively | content/guides/using-margin-invest.mdx | - |
| 13 | Guide: Metrics & Terminology | content/guides/metrics-and-terminology.mdx | - |
| 14 | Guide: Position Sizing | content/guides/position-sizing.mdx | - |
| 15 | Guide: Data Freshness | content/guides/data-freshness.mdx | - |
| 16 | Smoke test | - | build + manual |
