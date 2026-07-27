import React, { createContext, useContext, useEffect, useState } from 'react'
import { getMe, ping } from '../api'

export interface User {
  token: string
  learner_id: string
  name: string
  email: string
  picture: string
}

interface AuthCtx {
  user: User | null
  loading: boolean
  setUser: (u: User | null) => void
  signOut: () => void
}

const SESSION_KEY = 'mypy_tutor_session'
const AuthContext = createContext<AuthCtx>({} as AuthCtx)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUserState] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    ping() // warm up Render backend
    const token = localStorage.getItem(SESSION_KEY)
    if (!token) { setLoading(false); return }
    getMe(token)
      .then((data) => setUserState({ ...data, token }))
      .catch(() => localStorage.removeItem(SESSION_KEY))
      .finally(() => setLoading(false))
  }, [])

  const setUser = (u: User | null) => {
    if (u) {
      localStorage.setItem(SESSION_KEY, u.token)
      localStorage.setItem('mpt_learner_id', u.learner_id)
      localStorage.setItem('mpt_user_email', u.email)
      localStorage.setItem('mpt_user_name', u.name)
      localStorage.setItem('mpt_auth_type', u.learner_id.startsWith('g_') ? 'google' : 'email')
    } else {
      ;[SESSION_KEY, 'mpt_learner_id', 'mpt_user_email', 'mpt_user_name', 'mpt_auth_type', 'mpt_conv_id'].forEach(
        (k) => localStorage.removeItem(k)
      )
    }
    setUserState(u)
  }

  const signOut = () => setUser(null)

  return (
    <AuthContext.Provider value={{ user, loading, setUser, signOut }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
