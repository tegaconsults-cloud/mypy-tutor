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
  /** Set to 'reset' when ?auth=reset is detected — opens reset modal */
  pendingAuthAction: 'reset' | null
  clearPendingAuthAction: () => void
}

const SESSION_KEY = 'mypy_tutor_session'
const HISTORY_KEY = 'mypy_tutor_history_v2'
const AuthContext = createContext<AuthCtx>({} as AuthCtx)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUserState] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const [pendingAuthAction, setPendingAuthAction] = useState<'reset' | null>(null)

  useEffect(() => {
    ping() // warm up Render backend on initial load

    // ── Keepalive: ping every 8 minutes to prevent Render free-tier cold starts ──
    // Render free tier spins down after 15min idle. A periodic ping keeps the
    // server warm so users never experience 30-60s cold-start delays.
    const _keepalive = setInterval(() => {
      ping().catch(() => {}) // silent — non-fatal if it fails
    }, 8 * 60 * 1000) // 8 minutes

    // ── Handle OAuth/auth redirect params in the URL ──────────────────────
    const params = new URLSearchParams(window.location.search)
    const authType = params.get('auth')

    // ── Referral deep-link: ?ref=CODE ─────────────────────────────────────
    // When a new user lands via a referral link, persist the code so the
    // signup form can auto-fill it — even if they don't sign up immediately.
    const refCode = params.get('ref')
    if (refCode && refCode.length >= 4) {
      localStorage.setItem('mpt_referral_code', refCode.toUpperCase())
      // Clean the ?ref= param from the URL without a full reload
      const clean = new URLSearchParams(window.location.search)
      clean.delete('ref')
      const newSearch = clean.toString()
      window.history.replaceState(
        {},
        '',
        window.location.pathname + (newSearch ? `?${newSearch}` : '')
      )
    }

    if (authType === 'google_success' || authType === 'github_success') {
      // Both Google and GitHub OAuth redirects send user data the same way
      const raw = params.get('user')
      if (raw) {
        try {
          const userData = JSON.parse(decodeURIComponent(raw))
          if (userData.token && userData.learner_id) {
            const u: User = {
              token:      userData.token,
              learner_id: userData.learner_id,
              name:       userData.name    || '',
              email:      userData.email   || '',
              picture:    userData.picture || '',
            }
            setUser(u)
            // Clean the URL so reloads don't re-process the params
            const clean = window.location.pathname
            window.history.replaceState({}, '', clean)
            setLoading(false)
            return
          }
        } catch (_) { /* malformed — fall through */ }
      }
      window.history.replaceState({}, '', window.location.pathname)
    }

    if (authType === 'reset') {
      // Password reset deep-link: ?auth=reset&token=...
      // Store the reset token in sessionStorage so the AuthModal can use it
      const resetToken = params.get('token') || params.get('msg') || ''
      if (resetToken) sessionStorage.setItem('mpt_reset_token', resetToken)
      setPendingAuthAction('reset')
      window.history.replaceState({}, '', window.location.pathname)
      setLoading(false)
      return
    }

    if (authType === 'error') {
      // OAuth error — nothing to do, user stays logged out
      window.history.replaceState({}, '', window.location.pathname)
    }

    if (authType === 'confirmed') {
      // Email confirmed successfully — nothing extra needed, user can sign in
      window.history.replaceState({}, '', window.location.pathname)
    }

    // ── Restore existing session ──────────────────────────────────────────
    const token = localStorage.getItem(SESSION_KEY)
    if (!token) { setLoading(false); return }
    getMe(token)
      .then((data) => {
        const u = { ...data, token }
        setUserState(u)
        restoreConversation(u.learner_id)
      })
      .catch(() => localStorage.removeItem(SESSION_KEY))
      .finally(() => setLoading(false))

    return () => clearInterval(_keepalive) // cleanup keepalive on unmount
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

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
      const convs: { id: string; messages?: { role: string; content: string }[] }[] =
        data.conversations || []
      if (convs.length === 0) return
      const latest = convs[0]
      if (latest.id) localStorage.setItem('mpt_conv_id', latest.id)
      if (latest.messages && latest.messages.length > 0) {
        const msgs = latest.messages.map(m => ({ role: m.role, content: m.content }))
        localStorage.setItem(HISTORY_KEY, JSON.stringify(msgs))
        window.dispatchEvent(new Event('restore-chat'))
      }
    } catch (_) {
      // Non-fatal: conversation restore fails silently, user starts fresh
    }
  }

  const setUser = (u: User | null) => {
    if (u) {
      localStorage.setItem(SESSION_KEY, u.token)
      localStorage.setItem('mpt_learner_id', u.learner_id)
      localStorage.setItem('mpt_user_email', u.email)
      localStorage.setItem('mpt_user_name', u.name)
      localStorage.setItem('mpt_auth_type', u.learner_id.startsWith('g_') ? 'google' : u.learner_id.startsWith('gh_') ? 'github' : 'email')
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
  const clearPendingAuthAction = () => setPendingAuthAction(null)

  return (
    <AuthContext.Provider value={{ user, loading, setUser, signOut, pendingAuthAction, clearPendingAuthAction }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
