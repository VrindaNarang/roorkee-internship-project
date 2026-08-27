import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1'

// Single axios instance so base URL / interceptors are configured once.
export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10_000,
})

// The backend's plot images (SHAP waterfall/force/summary/bar/dependence
// PNGs) are served at the app root (`/plots/...`), not under `/api/v1` —
// derive the bare origin once so callers can build full <img> URLs.
export const API_ORIGIN = API_BASE_URL.replace(/\/api\/v1\/?$/, '')

// The bearer token lives here, not directly in `AuthContext`'s React state,
// so this plain axios module never needs to import React — `AuthContext`
// calls `setAuthToken` whenever it logs in/out/rehydrates from storage.
let currentToken: string | null = null

export const setAuthToken = (token: string | null) => {
  currentToken = token
}

apiClient.interceptors.request.use((config) => {
  if (currentToken) {
    config.headers.Authorization = `Bearer ${currentToken}`
  }
  return config
})

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    // Centralized log point for now; a toast/notification system can hook in later.
    console.error('[API error]', error?.response?.status, error?.response?.data ?? error.message)
    if (error?.response?.status === 401) {
      // Event-based (not a direct import) so this module stays framework-agnostic —
      // `AuthContext` is the one listener that clears session state and redirects to /login.
      window.dispatchEvent(new CustomEvent('auth:unauthorized'))
    }
    return Promise.reject(error)
  },
)
