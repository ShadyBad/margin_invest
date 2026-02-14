import { auth } from "@/lib/auth"
import { ApiError } from "./client"

const API_URL = process.env.API_URL || "http://localhost:8000"

export async function serverFetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const url = `${API_URL}${path}`

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...((options.headers as Record<string, string>) || {}),
  }

  // Inject user ID from session if available
  try {
    const session = await auth()
    if (session?.userId) {
      headers["X-User-Id"] = session.userId as string
    }
  } catch {
    // Auth not available — continue without user context
  }

  const response = await fetch(url, {
    ...options,
    headers,
    cache: options.cache ?? "no-store",
  })

  if (!response.ok) {
    const message = await response.text().catch(() => undefined)
    throw new ApiError(response.status, response.statusText, message)
  }

  if (response.status === 204) {
    return undefined as T
  }

  return response.json()
}
