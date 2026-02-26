import { auth } from "@/lib/auth"
import { ApiError } from "./client"
import { createHmac } from "crypto"

const API_URL = process.env.API_URL || "http://localhost:8000"
const SERVICE_AUTH_SECRET = process.env.SERVICE_AUTH_SECRET || ""

function signRequest(userId: string): Record<string, string> {
  if (!SERVICE_AUTH_SECRET) {
    // Fallback: unsigned (for local dev without secret configured)
    return { "X-User-Id": userId }
  }
  const timestamp = Math.floor(Date.now() / 1000).toString()
  const payload = `${userId}:${timestamp}`
  const signature = createHmac("sha256", SERVICE_AUTH_SECRET)
    .update(payload)
    .digest("hex")
  return {
    "X-User-Id": userId,
    "X-Auth-Timestamp": timestamp,
    "X-Auth-Signature": signature,
  }
}

export async function serverFetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const url = `${API_URL}${path}`

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...((options.headers as Record<string, string>) || {}),
  }

  // Inject signed auth headers from session
  try {
    const session = await auth()
    if (session?.userId) {
      Object.assign(headers, signRequest(session.userId as string))
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
  } catch (err) {
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
      // Non-JSON error response — use status text
      message = response.statusText || message
    }

    throw new ApiError(response.status, errorCode, message, requestId)
  }

  if (response.status === 204) {
    return undefined as T
  }

  return response.json()
}
