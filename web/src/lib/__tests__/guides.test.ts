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
