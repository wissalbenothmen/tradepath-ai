import axios from 'axios'

const api = axios.create({ baseURL: '/api/v1' })

// Allow the QueryClient to be wired post-bootstrap so api.ts has no React import.
let _onAuthFailure: (() => void) | null = null
export const setOnAuthFailure = (fn: () => void) => { _onAuthFailure = fn }

/** Centralised logout: clears token + react-query cache. */
export const logout = () => {
  localStorage.removeItem('token')
  _onAuthFailure?.()
}

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token')
      if (_onAuthFailure) _onAuthFailure()
      // Hard nav: pull every in-memory route + cache down with us.
      if (window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
    }
    return Promise.reject(err)
  },
)

/** Centralised endpoint registry — single source of truth for route strings. */
export const endpoints = {
  auth: {
    login: '/auth/login',
    me: '/auth/me',
    register: '/auth/register',
  },
  shipments: {
    list: '/shipments',
    detail: (id: string) => `/shipments/${id}`,
    voiceRecords: (id: string) => `/shipments/${id}/voice-records`,
    crossValidate: (id: string) => `/shipments/${id}/amendment-cross-validate`,
    brief: (id: string) => `/shipments/${id}/amendment-brief.pdf`,
  },
  classification: {
    list: '/classification',
    create: '/classification',
    detail: (id: string) => `/classification/${id}`,
    confirm: (id: string) => `/classification/${id}/confirm`,
  },
  screening: {
    forShipment: (id: string) => `/screening/shipment/${id}`,
    create: '/screening',
  },
  declarations: {
    forShipment: (id: string) => `/declarations/shipment/${id}`,
    create: '/declarations',
  },
  coo: {
    forShipment: (id: string) => `/coo/shipment/${id}`,
    create: '/coo',
  },
  fta: {
    forShipment: (id: string) => `/fta/shipment/${id}`,
    create: '/fta',
  },
  documents: {
    forShipment: (id: string) => `/documents/shipment/${id}`,
    create: '/documents',
  },
  analytics: {
    dashboard: '/analytics/dashboard',
    trends: '/analytics/trends',
    byJurisdiction: '/analytics/by-jurisdiction',
    topFtas: '/analytics/top-ftas',
    actionQueue: '/analytics/action-queue',
    aiInsights: '/analytics/ai-insights',
  },
} as const

/** Typed query-key factory. */
export const qk = {
  dashboard: () => ['analytics', 'dashboard'] as const,
  trends: (months: number) => ['analytics', 'trends', months] as const,
  byJurisdiction: () => ['analytics', 'by-jurisdiction'] as const,
  topFtas: () => ['analytics', 'top-ftas'] as const,
  actionQueue: () => ['analytics', 'action-queue'] as const,
  aiInsights: () => ['analytics', 'ai-insights'] as const,
  shipments: () => ['shipments'] as const,
  shipment: (id: string) => ['shipment', id] as const,
  voiceRecords: (id: string) => ['shipment', id, 'voice-records'] as const,
  me: () => ['auth', 'me'] as const,
}

export default api
