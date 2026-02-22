import { describe, it, expect, vi, beforeEach } from "vitest"

// Mock the incidents JSON import
vi.mock("@/data/incidents.json", () => ({
  default: [
    {
      id: "test-incident",
      title: "Test incident",
      status: "investigating",
      severity: "minor",
      createdAt: "2026-02-22T10:00:00Z",
      resolvedAt: null,
      updates: [{ message: "Investigating the issue.", timestamp: "2026-02-22T10:00:00Z" }],
    },
  ],
}))

// Must import after mock
import { GET } from "../route"

describe("GET /api/v1/status", () => {
  beforeEach(() => {
    vi.stubEnv("API_URL", "http://localhost:8000")
    vi.restoreAllMocks()
  })

  it("returns operational status when backend is healthy", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ version: "0.1.0", database: "ok", redis: "ok", status: "ok" }),
      })
    )

    const response = await GET()
    const data = await response.json()

    expect(data.services.api).toBe("operational")
    expect(data.services.database).toBe("operational")
    expect(data.services.scoring).toBe("operational")
    expect(data.version).toBe("0.1.0")
  })

  it("returns degraded when backend reports degraded", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({ version: "0.1.0", database: "ok", redis: "error", status: "degraded" }),
      })
    )

    const response = await GET()
    const data = await response.json()

    expect(data.services.scoring).toBe("outage")
    expect(data.status).toBe("outage")
  })

  it("returns unknown when backend is unreachable", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("Connection refused")))

    const response = await GET()
    const data = await response.json()

    expect(data.services.api).toBe("unknown")
    expect(data.services.database).toBe("unknown")
    expect(data.services.scoring).toBe("unknown")
    expect(data.status).toBe("degraded")
  })

  it("includes incidents from the JSON file", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ version: "0.1.0", database: "ok", redis: "ok", status: "ok" }),
      })
    )

    const response = await GET()
    const data = await response.json()

    expect(data.incidents).toHaveLength(1)
    expect(data.incidents[0].id).toBe("test-incident")
  })

  it("factors active incidents into overall status", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ version: "0.1.0", database: "ok", redis: "ok", status: "ok" }),
      })
    )

    const response = await GET()
    const data = await response.json()

    // Active minor incident should make overall status degraded even if services are ok
    expect(data.status).toBe("degraded")
  })
})
