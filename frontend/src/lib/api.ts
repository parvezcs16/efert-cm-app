import { employeeAuthStorage, guestAuthStorage } from '@/lib/auth-storage'

const API_V1_PREFIX = '/api/v1'

export class ApiError extends Error {
  status: number
  errorCode?: string
  details?: unknown

  constructor(message: string, status: number, errorCode?: string, details?: unknown) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.errorCode = errorCode
    this.details = details
  }
}

async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new ApiError(
      body.message ?? response.statusText,
      response.status,
      body.error_code,
      body.details,
    )
  }
  if (response.status === 204) {
    return undefined as T
  }
  return (await response.json()) as T
}

function buildInit(init: RequestInit | undefined, token: string | null): RequestInit {
  const headers = new Headers(init?.headers)
  // FormData needs the browser-generated multipart boundary header.
  if (init?.body !== undefined && !(init.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }
  if (token) {
    headers.set('Authorization', `Bearer ${token}`)
  }
  return { ...init, headers }
}

let refreshPromise: Promise<boolean> | null = null

/** Refreshes the employee access token exactly once even if several
 * requests hit a 401 concurrently -- callers share the same in-flight
 * refresh instead of each firing their own. */
async function refreshEmployeeToken(): Promise<boolean> {
  const refreshToken = employeeAuthStorage.getRefreshToken()
  if (!refreshToken) return false

  if (!refreshPromise) {
    refreshPromise = fetch(`${API_V1_PREFIX}/auth/token/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    })
      .then(async (res) => {
        if (!res.ok) return false
        const body = await res.json()
        employeeAuthStorage.setTokens(body.access_token, body.refresh_token)
        return true
      })
      .catch(() => false)
      .finally(() => {
        refreshPromise = null
      })
  }
  return refreshPromise
}

/** The default client: attaches the employee bearer token, and on a 401
 * transparently refreshes and retries the request once. */
export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const token = employeeAuthStorage.getAccessToken()
  const response = await fetch(`${API_V1_PREFIX}${path}`, buildInit(init, token))

  if (response.status === 401 && token) {
    const refreshed = await refreshEmployeeToken()
    if (refreshed) {
      const retryToken = employeeAuthStorage.getAccessToken()
      const retryResponse = await fetch(`${API_V1_PREFIX}${path}`, buildInit(init, retryToken))
      return parseResponse<T>(retryResponse)
    }
    employeeAuthStorage.clear()
  }

  return parseResponse<T>(response)
}

/** Turns a caught error (ApiError or otherwise) into a message safe to
 * show a user, including field-level detail from a 422 when present. */
export function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (Array.isArray(error.details) && error.details.length > 0) {
      const first = error.details[0] as { msg?: string }
      if (first?.msg) return first.msg
    }
    return error.message
  }
  if (error instanceof Error) return error.message
  return 'Something went wrong'
}

/** Guest-portal client: attaches the guest session's short-lived access
 * token instead. No refresh-on-401 -- a guest re-authenticates by
 * scanning the QR again, there's no refresh token to exchange. */
export async function guestApiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const token = guestAuthStorage.getAccessToken()
  const response = await fetch(`${API_V1_PREFIX}${path}`, buildInit(init, token))
  return parseResponse<T>(response)
}
