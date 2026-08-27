import { apiClient } from './client'
import type { CurrentUser, LoginResponse } from './types'

// The backend's login endpoint is a standard OAuth2 password grant (form
// fields `username`/`password`, `username` holding the email) — that exact
// shape is what makes FastAPI's `/docs` "Authorize" button work too.
export const login = (email: string, password: string) => {
  const body = new URLSearchParams()
  body.set('username', email)
  body.set('password', password)
  return apiClient
    .post<LoginResponse>('/auth/login', body, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    })
    .then((res) => res.data)
}

export const getCurrentUser = () => apiClient.get<CurrentUser>('/auth/me').then((res) => res.data)
