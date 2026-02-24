import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { FILTER_METADATA } from "@/lib/filter-metadata"

describe("FILTER_METADATA", () => {
  it("every filter has an academic citation", () => {
    for (const [key, meta] of Object.entries(FILTER_METADATA)) {
      expect(meta.citation, `${key} missing citation`).toBeTruthy()
    }
  })
})
