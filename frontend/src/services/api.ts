/**
 * API client service: fetch wrapper with JWT auth and token refresh.
 */

import { ref } from 'vue'

const API_BASE = '/api/v1'

export type StoredUser = {
  id: number
  phone: string
  family_id: number | null
  role: string | null
  name: string | null
}

function getToken(): string | null {
  return localStorage.getItem('fambank_token')
}

export function setToken(token: string): void {
  localStorage.setItem('fambank_token', token)
}

export function clearToken(): void {
  localStorage.removeItem('fambank_token')
}

function getRefreshTokenValue(): string | null {
  return localStorage.getItem('fambank_refresh_token')
}

export function setRefreshToken(token: string): void {
  localStorage.setItem('fambank_refresh_token', token)
}

export function clearRefreshToken(): void {
  localStorage.removeItem('fambank_refresh_token')
}

function loadStoredUser(): StoredUser | null {
  const raw = localStorage.getItem('fambank_user')
  if (!raw) return null
  try {
    return JSON.parse(raw)
  } catch {
    localStorage.removeItem('fambank_user')
    return null
  }
}

/** Reactive user state — use this in components instead of reading localStorage directly. */
export const currentUser = ref<StoredUser | null>(loadStoredUser())

// Sync logout across browser tabs
if (typeof window !== 'undefined') {
  window.addEventListener('storage', (e) => {
    if (e.key === 'fambank_token' && e.newValue === null) {
      currentUser.value = null
      window.location.href = '/login'
    }
  })
}

export function getStoredUser(): StoredUser | null {
  return currentUser.value
}

export function setStoredUser(user: StoredUser): void {
  localStorage.setItem('fambank_user', JSON.stringify(user))
  currentUser.value = user
}

export function clearStoredUser(): void {
  localStorage.removeItem('fambank_user')
  currentUser.value = null
}

export function logout(): void {
  clearToken()
  clearRefreshToken()
  clearStoredUser()
}

let isRefreshing = false
let refreshPromise: Promise<boolean> | null = null

async function tryRefreshToken(): Promise<boolean> {
  if (isRefreshing && refreshPromise) {
    return refreshPromise
  }
  isRefreshing = true
  refreshPromise = (async () => {
    const rt = getRefreshTokenValue()
    if (!rt) return false
    try {
      const response = await fetch(`${API_BASE}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: rt }),
      })
      if (!response.ok) return false
      const data = await response.json()
      setToken(data.access_token)
      setRefreshToken(data.refresh_token)
      return true
    } catch {
      return false
    } finally {
      isRefreshing = false
      refreshPromise = null
    }
  })()
  return refreshPromise
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

  let response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  })

  // On 401, attempt token refresh once
  if (response.status === 401 && token) {
    const refreshed = await tryRefreshToken()
    if (refreshed) {
      headers['Authorization'] = `Bearer ${getToken()}`
      response = await fetch(`${API_BASE}${path}`, {
        ...options,
        headers,
      })
    } else {
      // Refresh failed — clear session and redirect to login
      logout()
      window.location.href = '/login'
      throw new ApiError(401, '登录已过期，请重新登录')
    }
  }

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
  put: <T>(path: string, data?: unknown) =>
    request<T>(path, { method: 'PUT', body: data ? JSON.stringify(data) : undefined }),
  patch: <T>(path: string, data?: unknown) =>
    request<T>(path, { method: 'PATCH', body: data ? JSON.stringify(data) : undefined }),
  delete: <T>(path: string) => request<T>(path, { method: 'DELETE' }),
}

// ========== Auth API methods ==========

export async function sendCode(phone: string): Promise<{ message: string; expires_in: number }> {
  return api.post('/auth/send-code', { phone })
}

export async function verifyCode(
  phone: string,
  code: string
): Promise<{
  access_token: string
  refresh_token: string
  user: StoredUser
  is_new_user: boolean
}> {
  return api.post('/auth/verify-code', { phone, code })
}

export async function refreshToken(
  token: string
): Promise<{ access_token: string; refresh_token: string }> {
  return api.post('/auth/refresh', { refresh_token: token })
}
