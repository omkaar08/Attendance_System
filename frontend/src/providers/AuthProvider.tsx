import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'

import { authApi, setAuthToken } from '../lib/api'
import type { AppRole, CurrentUserResponse, LoginRequest, LoginUser } from '../lib/types'

const STORAGE_KEY = 'visionattend.session'

type SessionUser = LoginUser & {
  full_name?: string | null
  email?: string
  faculty_profile_id?: string | null
}

interface AuthSession {
  access_token: string
  refresh_token: string
  expires_in: number
  user: SessionUser
}

interface AuthContextValue {
  session: AuthSession | null
  user: SessionUser | null
  role: AppRole | null
  isAuthenticated: boolean
  isBootstrapping: boolean
  login: (payload: LoginRequest) => Promise<void>
  logout: () => void
  refreshUser: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

const parseStoredSession = (): AuthSession | null => {
  const raw = localStorage.getItem(STORAGE_KEY)
  if (!raw) {
    return null
  }

  try {
    return JSON.parse(raw) as AuthSession
  } catch {
    localStorage.removeItem(STORAGE_KEY)
    return null
  }
}

const mergeProfile = (session: AuthSession, profile: CurrentUserResponse): AuthSession => ({
  ...session,
  user: {
    ...session.user,
    id: profile.id,
    role: profile.role,
    department_id: profile.department_id,
    full_name: profile.full_name,
    email: profile.email,
    faculty_profile_id: profile.faculty_profile_id,
  },
})

export const AuthProvider = ({ children }: { children: React.ReactNode }) => {
  const [session, setSession] = useState<AuthSession | null>(() => parseStoredSession())
  const isBootstrapping = false

  useEffect(() => {
    setAuthToken(session?.access_token ?? null)

    if (session) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(session))
    } else {
      localStorage.removeItem(STORAGE_KEY)
    }
  }, [session])

  const logout = useCallback(() => {
    setSession(null)
  }, [])

  const refreshUser = useCallback(async () => {
    if (!session) {
      return
    }

    try {
      const profile = await authApi.me()
      setSession((prev) => (prev ? mergeProfile(prev, profile) : prev))
    } catch {
      logout()
    }
  }, [logout, session])

  const login = useCallback(async (payload: LoginRequest) => {
    const response = await authApi.login(payload)

    const initialSession: AuthSession = {
      access_token: response.access_token,
      refresh_token: response.refresh_token,
      expires_in: response.expires_in,
      user: response.user,
    }

    setSession(initialSession)
    setAuthToken(response.access_token)

    try {
      const profile = await authApi.me()
      setSession(mergeProfile(initialSession, profile))
    } catch {
      setSession(initialSession)
    }
  }, [])

  const value = useMemo<AuthContextValue>(
    () => ({
      session,
      user: session?.user ?? null,
      role: session?.user.role ?? null,
      isAuthenticated: Boolean(session?.access_token),
      isBootstrapping,
      login,
      logout,
      refreshUser,
    }),
    [isBootstrapping, login, logout, refreshUser, session],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

// eslint-disable-next-line react-refresh/only-export-components
export const useAuth = (): AuthContextValue => {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used inside AuthProvider.')
  }
  return context
}
