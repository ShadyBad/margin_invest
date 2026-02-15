import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"

const mockAuth = vi.fn()
vi.mock("@/lib/auth", () => ({
  auth: () => mockAuth(),
}))

const mockFetch = vi.fn()
vi.stubGlobal("fetch", mockFetch)

const { GET } = await import("../route")

function mockNextRequest(url: string) {
  return new Request(url)
}

describe("GET /api/v1/backtest/results/[id]", () => {
  beforeEach(() => {
    vi.stubEnv("API_URL", "http://localhost:8000")
    mockAuth.mockReset()
    mockFetch.mockReset()
  })

  afterEach(() => {
    vi.unstubAllEnvs()
  })

  it("returns 401 when not authenticated", async () => {
    mockAuth.mockResolvedValue(null)

    const response = await GET(
      mockNextRequest("http://localhost:3000/api/v1/backtest/results/abc-123"),
      { params: Promise.resolve({ id: "abc-123" }) },
    )

    expect(response.status).toBe(401)
    const body = await response.json()
    expect(body.error).toBe("Unauthorized")
  })

  it("proxies request to FastAPI when authenticated", async () => {
    mockAuth.mockResolvedValue({ userId: "user-123" })
    mockFetch.mockResolvedValue(
      new Response(JSON.stringify({ id: "abc-123", status: "completed" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    )

    const response = await GET(
      mockNextRequest("http://localhost:3000/api/v1/backtest/results/abc-123"),
      { params: Promise.resolve({ id: "abc-123" }) },
    )

    expect(response.status).toBe(200)
    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/backtest/results/abc-123",
      expect.objectContaining({
        headers: expect.objectContaining({
          "Content-Type": "application/json",
          "X-User-Id": "user-123",
        }),
      }),
    )
  })

  it("forwards upstream error status", async () => {
    mockAuth.mockResolvedValue({ userId: "user-123" })
    mockFetch.mockResolvedValue(
      new Response("Not Found", { status: 404 }),
    )

    const response = await GET(
      mockNextRequest("http://localhost:3000/api/v1/backtest/results/bad-id"),
      { params: Promise.resolve({ id: "bad-id" }) },
    )

    expect(response.status).toBe(404)
  })

  it("returns 502 when upstream fails", async () => {
    mockAuth.mockResolvedValue({ userId: "user-123" })
    mockFetch.mockRejectedValue(new Error("Connection refused"))

    const response = await GET(
      mockNextRequest("http://localhost:3000/api/v1/backtest/results/abc-123"),
      { params: Promise.resolve({ id: "abc-123" }) },
    )

    expect(response.status).toBe(502)
  })
})
