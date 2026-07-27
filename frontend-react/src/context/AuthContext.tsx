import React, { createContext, useContext, useEffect, useState } from 'react'
import { getMe, ping, getConversations } from '../api'

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
const HISTORY_KEY = 'mypy_tutor_history_v2'
const AuthContext = createContext<AuthCtx>({} as AuthCtx)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUserState] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    ping() // warm up Render backend
    const token = localStorage.getItem(SESSION_KEY)
    if (!token) { setLoading(false); return }
    getMe(token)
      .then((data) => {
        const u = { ...data, token }
        setUserState(u)
        // Restore latest conversation from backend
        restoreConversation(u.learner_id)
      })
      .catch(() => localStorage.removeItem(SESSION_KEY))
      .finally(() => setLoading(false))
  }, [])

  /**
   * Try to restore the most recent conversation from Supabase.
   * Only fills local storage if there's no local history already.
   */
  const restoreConversation = async (learnerId: string) => {
    try {
      const existing = localStorage.getItem(HISTORY_KEY)
      if (existing) return // don't overwrite local history
      const data = await getConversations(learnerId)
      if (!data) return
      // getConversations returns { conversations: [{id, messages, ...}] }
      const convs: { id: string; messages?: { role: string; content: string }[] }[] =
        data.conversations || []
      if (convs.length === 0) return
      const latest = convs[0]
      if (latest.id) localStorage.setItem('mpt_conv_id', latest.id)
      if (latest.messages && latest.messages.length > 0) {
        // Store as our Message format (role + content)
        const msgs = latest.messages.map(m => ({ role: m.role, content: m.content }))
        localStorage.setItem(HISTORY_KEY, JSON.stringify(msgs))
        window.dispatchEvent(new Event('restore-chat'))
      }
    } catch (_) {}
  }

  const setUser = (u: User | null) => {
    if (u) {
      localStorage.setItem(SESSION_KEY, u.token)
      localStorage.setItem('mpt_learner_id', u.learner_id)
      localStorage.setItem('mpt_user_email', u.email)
      localStorage.setItem('mpt_user_name', u.name)
      localStorage.setItem('mpt_auth_type', u.learner_id.startsWith('g_') ? 'google' : 'email')
      // Restore conversation for fresh sign-in
      restoreConversation(u.learner_id)
    } else {
      ;[SESSION_KEY, 'mpt_learner_id', 'mpt_user_email', 'mpt_user_name',
        'mpt_auth_type', 'mpt_conv_id', HISTORY_KEY].forEach(
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
