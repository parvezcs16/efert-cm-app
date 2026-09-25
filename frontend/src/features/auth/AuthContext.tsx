import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import type { ReactNode } from 'react'

import { apiFetch } from '@/lib/api'
import { employeeAuthStorage } from '@/lib/auth-storage'
import type { Employee } from '@/lib/types'

interface LoginResult {
  mustChangePassword: boolean
}

interface AuthContextValue {
  employee: Employee | null
  status: 'loading' | 'authenticated' | 'unauthenticated'
  login: (pNo: string, password: string) => Promise<LoginResult>
  logout: () => Promise<void>
  refreshProfile: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

interface TokenResponse {
  access_token: string
  refresh_token: string
  must_change_password: boolean
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [employee, setEmployee] = useState<Employee | null>(null)
  const [status, setStatus] = useState<AuthContextValue['status']>('loading')

  const loadProfile = useCallback(async () => {
    try {
      const profile = await apiFetch<Employee>('/employees/me')
      setEmployee(profile)
      setStatus('authenticated')
    } catch {
      employeeAuthStorage.clear()
      setEmployee(null)
      setStatus('unauthenticated')
    }
  }, [])

  useEffect(() => {
    if (employeeAuthStorage.getAccessToken()) {
      void loadProfile()
    } else {
      setStatus('unauthenticated')
    }
  }, [loadProfile])

  const login = useCallback(
    async (pNo: string, password: string): Promise<LoginResult> => {
      const tokens = await apiFetch<TokenResponse>('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ p_no: pNo, password }),
      })
      employeeAuthStorage.setTokens(tokens.access_token, tokens.refresh_token)
      if (!tokens.must_change_password) {
        await loadProfile()
      }
      return { mustChangePassword: tokens.must_change_password }
    },
    [loadProfile],
  )

  const logout = useCallback(async () => {
    const refreshToken = employeeAuthStorage.getRefreshToken()
    if (refreshToken) {
      await apiFetch('/auth/logout', {
        method: 'POST',
        body: JSON.stringify({ refresh_token: refreshToken }),
      }).catch(() => {
        // Best-effort: the client-side sign-out below still happens.
      })
    }
    employeeAuthStorage.clear()
    setEmployee(null)
    setStatus('unauthenticated')
  }, [])

  return (
    <AuthContext.Provider value={{ employee, status, login, logout, refreshProfile: loadProfile }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider')
  return ctx
}
