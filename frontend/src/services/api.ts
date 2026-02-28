/**
 * API client service: fetch wrapper with session token and Decimal string handling.
 */

const API_BASE = '/api/v1'

function getToken(): string | null {
  return localStorage.getItem('fambank_token')
}

export function setToken(token: string): void {
  localStorage.setItem('fambank_token', token)
}

export function clearToken(): void {
  localStorage.removeItem('fambank_token')
}

export function getStoredUser(): { id: number; role: string; name: string } | null {
  const raw = localStorage.getItem('fambank_user')
  return raw ? JSON.parse(raw) : null
}

export function setStoredUser(user: { id: number; role: string; name: string }): void {
  localStorage.setItem('fambank_user', JSON.stringify(user))
}

export function clearStoredUser(): void {
  localStorage.removeItem('fambank_user')
}

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken()
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> || {}),
  }
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  })

  if (!response.ok) {
    const body = await response.json().catch(() => ({ error: response.statusText }))
    throw new ApiError(response.status, body.detail || body.error || response.statusText)
  }

  return response.json()
}

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, data?: unknown) =>
    request<T>(path, { method: 'POST', body: data ? JSON.stringify(data) : undefined }),
  patch: <T>(path: string, data?: unknown) =>
    request<T>(path, { method: 'PATCH', body: data ? JSON.stringify(data) : undefined }),
  delete: <T>(path: string) => request<T>(path, { method: 'DELETE' }),
}
