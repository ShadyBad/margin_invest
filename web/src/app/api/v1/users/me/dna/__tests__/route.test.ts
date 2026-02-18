import { describe, it, expect, vi, beforeEach } from "vitest"

vi.mock("@/lib/auth", () => ({
  auth: vi.fn(),
}))

const mockFetch = vi.fn()
global.fetch = mockFetch

import { GET } from "../route"
import { auth } from "@/lib/auth"

describe("GET /api/v1/users/me/dna", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("returns 401 when not authenticated", async () => {
    vi.mocked(auth).mockResolvedValue(null)
    const response = await GET()
    expect(response.status).toBe(401)
  })

  it("proxies DNA data from upstream API", async () => {
    vi.mocked(auth).mockResolvedValue({
      userId: "1",
      user: { email: "test@test.com" },
    } as any)
    mockFetch.mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          base: "#1A3A5C",
          mid: "#0E4F4F",
          accent: "#1A7A5A",
          density: 0.6,
          tempo: 0.85,
        }),
    })
    const response = await GET()
    expect(response.status).toBe(200)
    const data = await response.json()
    expect(data.base).toBe("#1A3A5C")
    expect(data.density).toBe(0.6)
  })
})
