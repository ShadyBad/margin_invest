import { getFactorInterpretation } from "../score-interpretation"

describe("getFactorInterpretation", () => {
  it("returns exceptional interpretation for 90+ quality", () => {
    const result = getFactorInterpretation("quality", 95, "Technology")
    expect(result).toContain("Top 5%")
  })

  it("returns strong interpretation for 70-89", () => {
    const result = getFactorInterpretation("value", 82, "Healthcare")
    expect(result).toContain("Top 18%")
  })

  it("returns average interpretation for 50-69", () => {
    const result = getFactorInterpretation("momentum", 55, "Energy")
    expect(result).toContain("Middle of")
  })

  it("returns below-average for 30-49", () => {
    const result = getFactorInterpretation("quality", 35, "Technology")
    expect(result).toContain("Below average")
  })

  it("returns weak interpretation for below 30", () => {
    const result = getFactorInterpretation("quality", 15, "Technology")
    expect(result).toContain("Bottom")
  })

  it("handles unknown factor names gracefully", () => {
    const result = getFactorInterpretation("unknown_factor", 95)
    expect(result).toContain("Top 5%")
  })
})
