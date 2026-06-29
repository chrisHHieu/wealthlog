export const API_URL = process.env.NEXT_PUBLIC_API_URL || ''

type QueryValue = string | number | boolean | null | undefined

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly details: unknown,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

function buildUrl(path: string, query?: Record<string, QueryValue>) {
  const url = `${API_URL}${path}`
  if (!query) return url

  const params = new URLSearchParams()
  Object.entries(query).forEach(([key, value]) => {
    if (value !== null && value !== undefined && value !== '') {
      params.set(key, String(value))
    }
  })
  const qs = params.toString()
  return qs ? `${url}?${qs}` : url
}

async function parseResponse<T>(response: Response): Promise<T> {
  const contentType = response.headers.get('content-type') || ''
  const body = contentType.includes('application/json')
    ? await response.json()
    : await response.text()

  if (!response.ok) {
    const message =
      typeof body === 'object' && body && 'detail' in body
        ? String((body as { detail: unknown }).detail)
        : response.statusText || 'Request failed'
    throw new ApiError(message, response.status, body)
  }

  return body as T
}

export async function apiGet<T>(path: string, query?: Record<string, QueryValue>) {
  const response = await fetch(buildUrl(path, query))
  return parseResponse<T>(response)
}

export async function apiJson<T>(
  path: string,
  options: Omit<RequestInit, 'body'> & { body?: unknown } = {},
) {
  const response = await fetch(buildUrl(path), {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
  })
  return parseResponse<T>(response)
}

export async function apiDelete<T = unknown>(path: string) {
  const response = await fetch(buildUrl(path), { method: 'DELETE' })
  return parseResponse<T>(response)
}

export const queryKeys = {
  accounts: ['accounts'] as const,
  budget: (month: string) => ['budgets', month] as const,
  budgetCheck: (categoryId: string, month: string) => ['budget-check', categoryId, month] as const,
  categories: (month?: string) => ['categories', month || 'all'] as const,
  dashboard: (period: string, month: string) => ['dashboard', period, month] as const,
  goals: ['goals'] as const,
  investments: ['investments'] as const,
  memoryFacts: ['memory-facts'] as const,
  reports: (mode: string, month: string, year: number) =>
    ['reports', mode, month, year] as const,
  recurring: ['recurring'] as const,
  settings: ['settings'] as const,
  transaction: (id?: string | null) => ['transaction', id || 'new'] as const,
  transactions: (
    type: string,
    accountId: string,
    categoryId: string,
    month: string,
    search: string,
    page: number,
  ) => ['transactions', type, accountId, categoryId, month, search, page] as const,
}
