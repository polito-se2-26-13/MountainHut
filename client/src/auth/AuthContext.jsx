/* eslint-disable react-refresh/only-export-components */
import { createContext, useContext, useMemo, useState } from 'react'

const AuthContext = createContext(null)
const STORAGE_KEY = 'mountainhut.auth'

function readStoredSession() {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    return stored ? JSON.parse(stored) : null
  } catch {
    return null
  }
}

export function AuthProvider({ children }) {
  const [session, setSession] = useState(readStoredSession)

  function signIn(token, user) {
    const userProfile = {
      id: user.id,
      email: user.email,
      fullName: [user.firstName, user.lastName].filter(Boolean).join(' '),
      role: user.role,
    }
    const nextSession = { isAuthenticated: true, token, userProfile }
    localStorage.setItem(STORAGE_KEY, JSON.stringify(nextSession))
    setSession(nextSession)
    return nextSession
  }

  const value = useMemo(() => ({ session, signIn }), [session])
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used within AuthProvider')
  return context
}
