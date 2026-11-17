import createClient, { type Middleware } from 'openapi-fetch'
import type { components, paths } from './schema'

export type Schemas = components['schemas']

export const API_URL: string = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

const TOKEN_KEY = 'backtester.token'

/** The bearer token survives reloads; storage can be unavailable (private mode), so never throw. */
export const tokenStore = {
  get(): string | null {
    try {
      return localStorage.getItem(TOKEN_KEY)
    } catch {
      return null
    }
  },
  set(token: string | null) {
    try {
      if (token) localStorage.setItem(TOKEN_KEY, token)
      else localStorage.removeItem(TOKEN_KEY)
    } catch {
      /* the session then lasts until the tab closes */
    }
  },
}

let memoryToken: string | null = tokenStore.get()
let onUnauthorized: (() => void) | null = null

export function setToken(token: string | null) {
  memoryToken = token
  tokenStore.set(token)
}

export function getToken() {
  return memoryToken
}

/** Called when a signed-in request comes back 401 (expired or revoked token). */
export function setUnauthorizedHandler(handler: (() => void) | null) {
  onUnauthorized = handler
}

const authMiddleware: Middleware = {
  onRequest({ request }) {
    if (memoryToken) request.headers.set('Authorization', `Bearer ${memoryToken}`)
    return request
  },
  onResponse({ response }) {
    if (response.status === 401 && memoryToken) onUnauthorized?.()
    return response
  },
}

export const api = createClient<paths>({ baseUrl: API_URL })
api.use(authMiddleware)

/** An HTTP error with FastAPI's `detail` turned into readable lines. */
export class ApiError extends Error {
  readonly status: number
  readonly messages: string[]
  readonly detail: unknown

  constructor(status: number, body: unknown) {
    const detail = (body as { detail?: unknown } | undefined)?.detail ?? body
    const messages = describeDetail(detail)
    super(messages[0] ?? `Request failed (${status})`)
    this.status = status
    this.detail = detail
    this.messages = messages.length ? messages : [`Request failed (${status})`]
  }
}

function describeDetail(detail: unknown): string[] {
  if (!detail) return []
  if (typeof detail === 'string') return [detail]
  if (Array.isArray(detail)) {
    // Pydantic validation errors: [{ loc: ['body', 'field'], msg }]
    return detail.map((item) => {
      const loc = (item?.loc ?? []).filter((part: unknown) => part !== 'body').join('.')
      const msg = String(item?.msg ?? item).replace(/^Value error, /, '')
      return loc ? `${loc}: ${msg}` : msg
    })
  }
  if (typeof detail === 'object') {
    // Strategy validation: { message, errors: [...] }
    const { message, errors } = detail as { message?: string; errors?: string[] }
    if (errors?.length) return errors
    if (message) return [message]
  }
  return [String(detail)]
}

/** Await an openapi-fetch call and return its data, or throw an ApiError. */
export async function unwrap<T>(
  call: Promise<{ data?: T; error?: unknown; response: Response }>,
): Promise<T> {
  let result
  try {
    result = await call
  } catch {
    throw new ApiError(0, { detail: `Cannot reach the API at ${API_URL}. Is the backend running?` })
  }
  const { data, error, response } = result
  if (!response.ok || error !== undefined) throw new ApiError(response.status, error)
  return data as T
}

/** Download an authenticated file (exports) by fetching it with the bearer token. */
export async function downloadFile(path: string, fallbackName: string) {
  const response = await fetch(`${API_URL}${path}`, {
    headers: memoryToken ? { Authorization: `Bearer ${memoryToken}` } : {},
  })
  if (!response.ok) throw new ApiError(response.status, await response.json().catch(() => undefined))
  const disposition = response.headers.get('content-disposition') ?? ''
  const name = /filename=([^;]+)/.exec(disposition)?.[1]?.trim() ?? fallbackName
  const url = URL.createObjectURL(await response.blob())
  const link = document.createElement('a')
  link.href = url
  link.download = name
  link.click()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
