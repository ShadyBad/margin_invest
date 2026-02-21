import { describe, it, expect, vi, beforeEach } from 'vitest'
import { apiFetch, ApiError, MfaRequiredError } from '../client'

describe('apiFetch', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('fetches data successfully', async () => {
    const mockData = { status: 'ok' }
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve(mockData),
    })

    const result = await apiFetch('/health')
    expect(result).toEqual(mockData)
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('/health'),
      expect.objectContaining({
        headers: expect.objectContaining({
          'Content-Type': 'application/json',
        }),
      }),
    )
  })

  it('throws ApiError on non-2xx response with structured body', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      statusText: 'Not Found',
      json: () => Promise.resolve({
        error_code: 'NOT_FOUND',
        message: 'Score not found',
        request_id: 'req-123',
        status_code: 404,
      }),
    })

    await expect(apiFetch('/api/v1/scores/INVALID')).rejects.toThrow(ApiError)
    await expect(apiFetch('/api/v1/scores/INVALID')).rejects.toMatchObject({
      status: 404,
      errorCode: 'NOT_FOUND',
      message: 'Score not found',
      requestId: 'req-123',
    })
  })

  it('falls back to statusText when response is not JSON', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 502,
      statusText: 'Bad Gateway',
      json: () => Promise.reject(new Error('not json')),
    })

    await expect(apiFetch('/api/v1/scores/INVALID')).rejects.toThrow(ApiError)
    await expect(apiFetch('/api/v1/scores/INVALID')).rejects.toMatchObject({
      status: 502,
      errorCode: 'UNKNOWN',
      message: 'Bad Gateway',
    })
  })

  it('handles 204 No Content', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 204,
    })

    const result = await apiFetch('/api/v1/scores/AAPL')
    expect(result).toBeUndefined()
  })

  describe('MFA-required interceptor', () => {
    it('throws MfaRequiredError on 403 with error=mfa_required', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 403,
        statusText: 'Forbidden',
        json: () => Promise.resolve({
          error: 'mfa_required',
          message: 'Multi-factor authentication is required',
        }),
      })

      await expect(apiFetch('/api/v1/scores/AAPL')).rejects.toThrow(MfaRequiredError)
      await expect(apiFetch('/api/v1/scores/AAPL')).rejects.toMatchObject({
        status: 403,
        errorCode: 'mfa_required',
        message: 'Multi-factor authentication is required',
      })
    })

    it('dispatches mfa-required custom event on window', async () => {
      const handler = vi.fn()
      window.addEventListener('mfa-required', handler)

      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 403,
        statusText: 'Forbidden',
        json: () => Promise.resolve({
          error: 'mfa_required',
          message: 'MFA required',
        }),
      })

      await expect(apiFetch('/api/v1/scores/AAPL')).rejects.toThrow(MfaRequiredError)
      expect(handler).toHaveBeenCalledTimes(1)

      window.removeEventListener('mfa-required', handler)
    })

    it('does not dispatch event for non-MFA 403 errors', async () => {
      const handler = vi.fn()
      window.addEventListener('mfa-required', handler)

      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 403,
        statusText: 'Forbidden',
        json: () => Promise.resolve({
          error_code: 'FORBIDDEN',
          message: 'Access denied',
        }),
      })

      await expect(apiFetch('/api/v1/scores/AAPL')).rejects.toThrow(ApiError)
      await expect(apiFetch('/api/v1/scores/AAPL')).rejects.not.toThrow(MfaRequiredError)
      expect(handler).not.toHaveBeenCalled()

      window.removeEventListener('mfa-required', handler)
    })

    it('handles error_code=mfa_required variant', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 403,
        statusText: 'Forbidden',
        json: () => Promise.resolve({
          error_code: 'mfa_required',
          message: 'MFA required',
        }),
      })

      await expect(apiFetch('/api/v1/scores/AAPL')).rejects.toThrow(MfaRequiredError)
    })
  })
})
