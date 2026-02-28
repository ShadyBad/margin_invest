import { auth } from "@/lib/auth"
import { ApiError } from "./client"
import { signServiceToken } from "./service-token"

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

  // Inject signed auth token from session
  try {
    const session = await auth()
    if (session?.userId) {
      const token = await signServiceToken(
        session.userId as string,
        session.user?.email,
      )
      if (token) {
        headers["Authorization"] = `Bearer ${token}`
      } else {
        // Fallback: unsigned header for local dev without SERVICE_AUTH_SECRET
        headers["X-User-Id"] = session.userId as string
      }
    }
  } catch {
    // Auth not available — continue without user context
  }

  let response: Response
  try {
    response = await fetch(url, {
      ...options,
      headers,
      cache: options.cache ?? "no-store",
    })
  } catch {
    throw new ApiError(503, "SERVICE_UNAVAILABLE", "API server is not reachable")
  }

  if (!response.ok) {
    let errorCode = "UNKNOWN"
    let message = `API Error: ${response.status} ${response.statusText}`
    let requestId: string | undefined

    try {
      const body = await response.json()
      errorCode = body.error_code || errorCode
      message = body.message || message
      requestId = body.request_id
    } catch {
      message = response.statusText || message
    }

    throw new ApiError(response.status, errorCode, message, requestId)
  }

  if (response.status === 204) {
    return undefined as T
  }

  return response.json()
}
