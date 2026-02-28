import { describe, it, expect, vi, beforeEach } from "vitest"

vi.mock("../client", () => ({
  apiFetch: vi.fn(),
}))

import { apiFetch } from "../client"
import {
  getLatestValidationReport,
  getValidationHistory,
  getValidationReport,
} from "../model-validation"

const mockedFetch = vi.mocked(apiFetch)

describe("model-validation API client", () => {
  beforeEach(() => {
    mockedFetch.mockReset()
  })

  it("getLatestValidationReport calls correct endpoint", async () => {
    const mockReport = { run_group_id: "test", gate_passed: true }
    mockedFetch.mockResolvedValueOnce(mockReport)
    const result = await getLatestValidationReport("admin-key")
    expect(mockedFetch).toHaveBeenCalledWith(
      "/api/v1/admin/model-validation/latest",
      expect.objectContaining({ headers: { "X-Admin-Key": "admin-key" } }),
    )
    expect(result).toEqual(mockReport)
  })

  it("getValidationHistory calls with pagination", async () => {
    mockedFetch.mockResolvedValueOnce({ reports: [], total: 0 })
    await getValidationHistory("admin-key", 10, 20)
    expect(mockedFetch).toHaveBeenCalledWith(
      "/api/v1/admin/model-validation/history?limit=10&offset=20",
      expect.objectContaining({ headers: { "X-Admin-Key": "admin-key" } }),
    )
  })

  it("getValidationHistory uses default pagination", async () => {
    mockedFetch.mockResolvedValueOnce({ reports: [], total: 0 })
    await getValidationHistory("admin-key")
    expect(mockedFetch).toHaveBeenCalledWith(
      "/api/v1/admin/model-validation/history?limit=20&offset=0",
      expect.objectContaining({ headers: { "X-Admin-Key": "admin-key" } }),
    )
  })

  it("getValidationReport calls with group id", async () => {
    mockedFetch.mockResolvedValueOnce({ run_group_id: "abc-123" })
    await getValidationReport("admin-key", "abc-123")
    expect(mockedFetch).toHaveBeenCalledWith(
      "/api/v1/admin/model-validation/abc-123",
      expect.objectContaining({ headers: { "X-Admin-Key": "admin-key" } }),
    )
  })
})
