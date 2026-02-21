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

export class MfaRequiredError extends ApiError {
  constructor(message: string) {
    super(403, 'mfa_required', message)
    this.name = 'MfaRequiredError'
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
      errorCode = body.error_code || body.error || errorCode
      message = body.message || message
      requestId = body.request_id

      // Intercept MFA-required 403 responses
      if (response.status === 403 && (body.error === 'mfa_required' || body.error_code === 'mfa_required')) {
        if (typeof window !== 'undefined') {
          window.dispatchEvent(new CustomEvent('mfa-required', { detail: body }))
        }
        throw new MfaRequiredError(message)
      }
    } catch (err) {
      // Re-throw MfaRequiredError
      if (err instanceof MfaRequiredError) throw err
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
