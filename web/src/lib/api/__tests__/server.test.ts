import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"

// Mock auth before importing serverFetch
const mockAuth = vi.fn()
vi.mock("@/lib/auth", () => ({
  auth: () => mockAuth(),
}))

// Mock signServiceToken
const mockSignServiceToken = vi.fn()
vi.mock("../service-token", () => ({
  signServiceToken: (...args: unknown[]) => mockSignServiceToken(...args),
}))

// Mock global fetch
const mockFetch = vi.fn()
vi.stubGlobal("fetch", mockFetch)

// Import after mocks
const { serverFetch } = await import("../server")

describe("serverFetch", () => {
  beforeEach(() => {
    vi.stubEnv("API_URL", "http://localhost:8000")
    mockAuth.mockReset()
    mockFetch.mockReset()
    mockSignServiceToken.mockReset()
    mockSignServiceToken.mockResolvedValue("")
  })

  afterEach(() => {
    vi.unstubAllEnvs()
  })

  it("fetches from API_URL with the given path", async () => {
    mockAuth.mockResolvedValue(null)
    mockFetch.mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ status: "ok" }),
    })

    await serverFetch("/health")

    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8000/health",
      expect.objectContaining({
        headers: expect.objectContaining({
          "Content-Type": "application/json",
        }),
      }),
    )
  })

  it("returns parsed JSON on success", async () => {
    mockAuth.mockResolvedValue(null)
    mockFetch.mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ picks: [], watchlist: [] }),
    })

    const result = await serverFetch("/api/v1/dashboard")
    expect(result).toEqual({ picks: [], watchlist: [] })
  })

  it("throws ApiError on non-2xx response with structured body", async () => {
    mockAuth.mockResolvedValue(null)
    mockFetch.mockResolvedValue({
      ok: false,
      status: 500,
      statusText: "Internal Server Error",
      json: () => Promise.resolve({
        error_code: "INTERNAL_ERROR",
        message: "server error",
        request_id: "req-456",
        status_code: 500,
      }),
    })

    await expect(serverFetch("/api/v1/dashboard")).rejects.toThrow("server error")
  })

  it("falls back to statusText when error response is not JSON", async () => {
    mockAuth.mockResolvedValue(null)
    mockFetch.mockResolvedValue({
      ok: false,
      status: 502,
      statusText: "Bad Gateway",
      json: () => Promise.reject(new Error("not json")),
    })

    await expect(serverFetch("/api/v1/dashboard")).rejects.toThrow("Bad Gateway")
  })

  it("sends Authorization Bearer header when signServiceToken returns a JWT", async () => {
    mockAuth.mockResolvedValue({ userId: "user-123", user: { email: "test@test.com" } })
    mockSignServiceToken.mockResolvedValue("signed.jwt.token")
    mockFetch.mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve({}),
    })

    await serverFetch("/api/v1/dashboard")

    expect(mockSignServiceToken).toHaveBeenCalledWith("user-123", "test@test.com")
    expect(mockFetch).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({
        headers: expect.objectContaining({
          "Authorization": "Bearer signed.jwt.token",
        }),
      }),
    )
  })

  it("falls back to X-User-Id when signServiceToken returns empty string", async () => {
    mockAuth.mockResolvedValue({ userId: "user-123", user: { email: "test@test.com" } })
    mockSignServiceToken.mockResolvedValue("")
    mockFetch.mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve({}),
    })

    await serverFetch("/api/v1/dashboard")

    expect(mockFetch).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({
        headers: expect.objectContaining({
          "X-User-Id": "user-123",
        }),
      }),
    )
  })

  it("uses cache: no-store by default", async () => {
    mockAuth.mockResolvedValue(null)
    mockFetch.mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve({}),
    })

    await serverFetch("/api/v1/dashboard")

    expect(mockFetch).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({ cache: "no-store" }),
    )
  })

  it("returns undefined for 204 No Content", async () => {
    mockAuth.mockResolvedValue(null)
    mockFetch.mockResolvedValue({
      ok: true,
      status: 204,
    })

    const result = await serverFetch("/api/v1/something")
    expect(result).toBeUndefined()
  })

  it("throws SERVICE_UNAVAILABLE when fetch fails", async () => {
    mockAuth.mockResolvedValue(null)
    mockFetch.mockRejectedValue(new Error("network error"))

    await expect(serverFetch("/health")).rejects.toThrow("API server is not reachable")
  })
})
