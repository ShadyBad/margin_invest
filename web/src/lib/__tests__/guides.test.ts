import { describe, it, expect } from "vitest"

describe("slugify", () => {
  it("converts heading text to URL-safe slug", async () => {
    const { slugify } = await import("../guides")

    expect(slugify("Getting Started")).toBe("getting-started")
    expect(slugify("What is Margin?")).toBe("what-is-margin")
    expect(slugify("Step 1: Setup")).toBe("step-1-setup")
    expect(slugify("  Extra  Spaces  ")).toBe("extra-spaces")
    expect(slugify("ALL CAPS HEADING")).toBe("all-caps-heading")
    expect(slugify("hyphen-already")).toBe("hyphen-already")
    expect(slugify("special!@#chars")).toBe("specialchars")
  })
})

describe("extractTocHeadings", () => {
  it("extracts H2 and H3 headings from MDX source", async () => {
    const { extractTocHeadings } = await import("../guides")

    const source = [
      "# Title (H1 — should be ignored)",
      "",
      "Some intro text.",
      "",
      "## Getting Started",
      "",
      "Paragraph under H2.",
      "",
      "### Prerequisites",
      "",
      "More text.",
      "",
      "## Configuration",
      "",
      "### Advanced Options",
      "",
      "#### Too Deep (H4 — should be ignored)",
    ].join("\n")

    const headings = extractTocHeadings(source)

    expect(headings).toEqual([
      { level: 2, text: "Getting Started", id: "getting-started" },
      { level: 3, text: "Prerequisites", id: "prerequisites" },
      { level: 2, text: "Configuration", id: "configuration" },
      { level: 3, text: "Advanced Options", id: "advanced-options" },
    ])
  })

  it("returns empty array for source with no headings", async () => {
    const { extractTocHeadings } = await import("../guides")

    const source = "Just a plain paragraph.\n\nAnother paragraph."
    expect(extractTocHeadings(source)).toEqual([])
  })

  it("generates unique IDs for duplicate headings", async () => {
    const { extractTocHeadings } = await import("../guides")

    const source = [
      "## Overview",
      "",
      "## Overview",
      "",
      "### Details",
      "",
      "### Details",
      "",
      "### Details",
    ].join("\n")

    const headings = extractTocHeadings(source)

    expect(headings).toEqual([
      { level: 2, text: "Overview", id: "overview" },
      { level: 2, text: "Overview", id: "overview-1" },
      { level: 3, text: "Details", id: "details" },
      { level: 3, text: "Details", id: "details-1" },
      { level: 3, text: "Details", id: "details-2" },
    ])
  })
})

describe("groupGuidesByCategory", () => {
  it("groups guides into Concepts, Workflows, and Reference", async () => {
    const { groupGuidesByCategory } = await import("../guides")
    const guides = [
      { slug: "a", category: "Concepts", title: "A", description: "", order: 1, updatedAt: "", readingTime: 1 },
      { slug: "b", category: "Workflows", title: "B", description: "", order: 2, updatedAt: "", readingTime: 1 },
      { slug: "c", category: "Reference", title: "C", description: "", order: 3, updatedAt: "", readingTime: 1 },
      { slug: "d", category: "Concepts", title: "D", description: "", order: 4, updatedAt: "", readingTime: 1 },
    ]
    const grouped = groupGuidesByCategory(guides)
    expect(grouped.Concepts).toHaveLength(2)
    expect(grouped.Workflows).toHaveLength(1)
    expect(grouped.Reference).toHaveLength(1)
  })

  it("returns empty arrays for categories with no matching guides", async () => {
    const { groupGuidesByCategory } = await import("../guides")
    const guides = [
      { slug: "a", category: "Reference", title: "A", description: "", order: 1, updatedAt: "", readingTime: 1 },
    ]
    const grouped = groupGuidesByCategory(guides)
    expect(grouped.Concepts).toHaveLength(0)
    expect(grouped.Workflows).toHaveLength(0)
    expect(grouped.Reference).toHaveLength(1)
  })

  it("ignores guides with unrecognized categories", async () => {
    const { groupGuidesByCategory } = await import("../guides")
    const guides = [
      { slug: "a", category: "Core Concepts", title: "A", description: "", order: 1, updatedAt: "", readingTime: 1 },
      { slug: "b", category: "Unknown", title: "B", description: "", order: 2, updatedAt: "", readingTime: 1 },
    ]
    const grouped = groupGuidesByCategory(guides)
    expect(grouped.Concepts).toHaveLength(0)
    expect(grouped.Workflows).toHaveLength(0)
    expect(grouped.Reference).toHaveLength(0)
  })
})
