import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react'
import { getCurrentUser, login as loginRequest } from '../api/auth'
import { setAuthToken } from '../api/client'
import type { CurrentUser } from '../api/types'

const TOKEN_STORAGE_KEY = 'salespilot-auth-token'

type AuthStatus = 'loading' | 'authenticated' | 'unauthenticated'

interface AuthContextValue {
  user: CurrentUser | null
  status: AuthStatus
  login: (email: string, password: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<CurrentUser | null>(null)
  const [status, setStatus] = useState<AuthStatus>('loading')

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_STORAGE_KEY)
    setAuthToken(null)
    setUser(null)
    setStatus('unauthenticated')
  }, [])

  // Rehydrate the session from a stored token on first load, and validate it
  // against the backend rather than trusting it blindly (an expired/revoked
  // token should immediately drop the user back to the login page, not
  // render the app with a token that will just 401 on the first request).
  useEffect(() => {
    const storedToken = localStorage.getItem(TOKEN_STORAGE_KEY)
    if (!storedToken) {
      setStatus('unauthenticated')
      return
    }
    setAuthToken(storedToken)
    getCurrentUser()
      .then((profile) => {
        setUser(profile)
        setStatus('authenticated')
      })
      .catch(() => logout())
  }, [logout])

  // The axios response interceptor (`api/client.ts`) fires this on any 401
  // — including a token that expires mid-session, not just a bad login.
  useEffect(() => {
    const handleUnauthorized = () => logout()
    window.addEventListener('auth:unauthorized', handleUnauthorized)
    return () => window.removeEventListener('auth:unauthorized', handleUnauthorized)
  }, [logout])

  const login = useCallback(async (email: string, password: string) => {
    const { access_token } = await loginRequest(email, password)
    localStorage.setItem(TOKEN_STORAGE_KEY, access_token)
    setAuthToken(access_token)
    const profile = await getCurrentUser()
    setUser(profile)
    setStatus('authenticated')
  }, [])

  return <AuthContext.Provider value={{ user, status, login, logout }}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
