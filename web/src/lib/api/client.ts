export class ApiError extends Error {
  constructor(
    public status: number,
    public errorCode: string,
    message?: string,
    public requestId?: string,
  ) {
    super(message || `API Error: ${status}`)
    this.name = 'ApiError'
  }
}

const BASE_URL = ''

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const url = `${BASE_URL}${path}`
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...((options.headers as Record<string, string>) || {}),
  }

  const response = await fetch(url, {
    ...options,
    headers,
  })

  if (!response.ok) {
    let errorCode = 'UNKNOWN'
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

  // 204 No Content
  if (response.status === 204) {
    return undefined as T
  }

  return response.json()
}
