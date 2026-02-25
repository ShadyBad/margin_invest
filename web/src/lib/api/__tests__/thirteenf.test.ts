import { describe, it, expect, vi, beforeEach } from "vitest"
import {
  getHoldings,
  getHoldingsHistory,
  getManagers,
  getManagerPortfolio,
  getOverlap,
  getNewPositions,
  getClonePortfolio,
} from "../thirteenf"

// Mock the client module
vi.mock("../client", () => ({
  apiFetch: vi.fn(),
}))

import { apiFetch } from "../client"
const mockApiFetch = vi.mocked(apiFetch)

describe("13F API helpers", () => {
  beforeEach(() => {
    mockApiFetch.mockReset()
  })

  it("getHoldings calls correct URL", async () => {
    mockApiFetch.mockResolvedValueOnce({
      ticker: "AAPL",
      curated_holders: [],
      other_holders: [],
      summary: {},
    })
    await getHoldings("AAPL")
    expect(mockApiFetch).toHaveBeenCalledWith("/api/v1/13f/holdings/AAPL")
  })

  it("getHoldings uppercases ticker", async () => {
    mockApiFetch.mockResolvedValueOnce({
      ticker: "AAPL",
      curated_holders: [],
      other_holders: [],
      summary: {},
    })
    await getHoldings("aapl")
    expect(mockApiFetch).toHaveBeenCalledWith("/api/v1/13f/holdings/AAPL")
  })

  it("getHoldingsHistory calls correct URL with limit", async () => {
    mockApiFetch.mockResolvedValueOnce({ ticker: "AAPL", quarters: [] })
    await getHoldingsHistory("AAPL", 20)
    expect(mockApiFetch).toHaveBeenCalledWith("/api/v1/13f/holdings/AAPL/history?limit=20")
  })

  it("getHoldingsHistory uses default limit", async () => {
    mockApiFetch.mockResolvedValueOnce({ ticker: "AAPL", quarters: [] })
    await getHoldingsHistory("AAPL")
    expect(mockApiFetch).toHaveBeenCalledWith("/api/v1/13f/holdings/AAPL/history?limit=10")
  })

  it("getManagers calls correct URL", async () => {
    mockApiFetch.mockResolvedValueOnce([])
    await getManagers()
    expect(mockApiFetch).toHaveBeenCalledWith("/api/v1/13f/managers")
  })

  it("getManagers with tier filter", async () => {
    mockApiFetch.mockResolvedValueOnce([])
    await getManagers("curated")
    expect(mockApiFetch).toHaveBeenCalledWith("/api/v1/13f/managers?tier=curated")
  })

  it("getManagerPortfolio calls correct URL", async () => {
    mockApiFetch.mockResolvedValueOnce({ manager: "Berkshire", holdings: [] })
    await getManagerPortfolio(1)
    expect(mockApiFetch).toHaveBeenCalledWith("/api/v1/13f/managers/1/portfolio")
  })

  it("getManagerPortfolio with period", async () => {
    mockApiFetch.mockResolvedValueOnce({ manager: "Berkshire", holdings: [] })
    await getManagerPortfolio(1, "2025-12-31")
    expect(mockApiFetch).toHaveBeenCalledWith("/api/v1/13f/managers/1/portfolio?period=2025-12-31")
  })

  it("getOverlap calls correct URL", async () => {
    mockApiFetch.mockResolvedValueOnce({ most_held: [], crowded_trades: [] })
    await getOverlap()
    expect(mockApiFetch).toHaveBeenCalledWith("/api/v1/13f/analytics/overlap")
  })

  it("getNewPositions calls correct URL", async () => {
    mockApiFetch.mockResolvedValueOnce({ new_positions: [] })
    await getNewPositions()
    expect(mockApiFetch).toHaveBeenCalledWith("/api/v1/13f/analytics/new-positions")
  })

  it("getClonePortfolio calls correct URL", async () => {
    mockApiFetch.mockResolvedValueOnce({ positions: [] })
    await getClonePortfolio(1)
    expect(mockApiFetch).toHaveBeenCalledWith(
      "/api/v1/13f/analytics/clone/1?strategy=equal_weight_top_20",
    )
  })

  it("getClonePortfolio with custom strategy", async () => {
    mockApiFetch.mockResolvedValueOnce({ positions: [] })
    await getClonePortfolio(1, "value_weight_top_10")
    expect(mockApiFetch).toHaveBeenCalledWith(
      "/api/v1/13f/analytics/clone/1?strategy=value_weight_top_10",
    )
  })
})
