import React, { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, Eye, EyeOff, Mail, Lock, User, KeyRound, ArrowLeft } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { signIn, signUp, forgotPassword, resendConfirmation, resetPassword, API_BASE } from '../api'
import Logo from './Logo'

interface Props { defaultTab?: 'signin' | 'signup'; onClose: () => void }

export default function AuthModal({ defaultTab = 'signin', onClose }: Props) {
  const { setUser, pendingAuthAction, clearPendingAuthAction } = useAuth()
  const [tab, setTab]         = useState<'signin' | 'signup' | 'forgot' | 'reset'>(defaultTab)
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState('')
  const [success, setSuccess] = useState('')

  const [siEmail, setSiEmail] = useState('')
  const [siPass,  setSiPass]  = useState('')
  const [siShow,  setSiShow]  = useState(false)

  const [suName,  setSuName]  = useState('')
  const [suEmail, setSuEmail] = useState('')
  const [suPass,  setSuPass]  = useState('')
  const [suCode,  setSuCode]  = useState('')
  const [suShow,  setSuShow]  = useState(false)

  const [fgEmail, setFgEmail] = useState('')

  // Reset password tab state
  const [rpPass,  setRpPass]  = useState('')
  const [rpShow,  setRpShow]  = useState(false)
  const [rpToken, setRpToken] = useState('')

  // Open forgot/reset tab when auth=reset deep-link is detected
  useEffect(() => {
    if (pendingAuthAction === 'reset') {
      const token = sessionStorage.getItem('mpt_reset_token') || ''
      if (token) {
        setRpToken(token)
        setTab('reset')
      } else {
        setTab('forgot')
      }
      clearPendingAuthAction()
    }
  }, [pendingAuthAction, clearPendingAuthAction])

  const handleSignIn = async (e: React.FormEvent) => {
    e.preventDefault(); setError(''); setLoading(true)
    try {
      const data = await signIn(siEmail, siPass)
      setUser(data); onClose()
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Sign in failed'
      setError(msg.toLowerCase().includes('confirm') ? msg + ' — check your email or resend below.' : msg)
    } finally { setLoading(false) }
  }

  const handleSignUp = async (e: React.FormEvent) => {
    e.preventDefault(); setError('')
    if (!suName)                { setError('Enter your full name.'); return }
    if (!suEmail.includes('@')) { setError('Enter a valid email.'); return }
    if (suPass.length < 8)      { setError('Password must be at least 8 characters.'); return }
    setLoading(true)
    try {
      const data = await signUp(suName, suEmail, suPass, suCode)
      const msg: string = data.message || ''
      const autoConfirmed = msg.toLowerCase().includes('welcome') || msg.toLowerCase().includes('confirmed')
      if (autoConfirmed) {
        // Use suPass (signup password) — not siPass which belongs to the sign-in tab
        const ld = await signIn(suEmail, suPass)
        setUser(ld); onClose()
      } else {
        setSuccess('✅ ' + msg + ' — check your email, then sign in.')
        setTimeout(() => setTab('signin'), 4000)
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Sign up failed')
    } finally { setLoading(false) }
  }

  const handleForgot = async (e: React.FormEvent) => {
    e.preventDefault(); setError(''); setLoading(true)
    try {
      const data = await forgotPassword(fgEmail)
      setSuccess(data.message || 'Reset link sent! Check your email.')
    } catch {
      setError('Network error. Please try again.')
    } finally { setLoading(false) }
  }

  const handleReset = async (e: React.FormEvent) => {
    e.preventDefault(); setError('')
    if (rpPass.length < 8) { setError('Password must be at least 8 characters.'); return }
    setLoading(true)
    try {
      await resetPassword(rpToken, rpPass)
      setSuccess('✅ Password updated! You can now sign in.')
      sessionStorage.removeItem('mpt_reset_token')
      setTimeout(() => setTab('signin'), 2500)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Reset failed. The link may have expired.')
    } finally { setLoading(false) }
  }

  const handleResend = async () => {
    // Use the email from whichever tab is active
    const email = tab === 'signin' ? siEmail : suEmail
    if (!email) { setError('Enter your email first.'); return }
    const data = await resendConfirmation(email)
    if (data.auto_confirmed) {
      try {
        // Use the correct password for the active tab
        const password = tab === 'signin' ? siPass : suPass
        if (!password) { setSuccess('✅ Confirmed! Please sign in.'); setTab('signin'); return }
        const ld = await signIn(email, password)
        setUser(ld); onClose()
      } catch {
        setSuccess('✅ Confirmed! Sign in below.'); setTab('signin')
      }
    } else {
      setSuccess(data.message || 'Resent!')
    }
  }

  const inputStyle = {
    background: 'rgba(6,13,28,0.8)',
    borderColor: 'rgba(13,71,161,0.35)',
  }

  const isAuthTab = tab === 'signin' || tab === 'signup'

  return (
    <AnimatePresence>
      <motion.div key="backdrop" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
        onClick={e => e.target === e.currentTarget && onClose()}
        className="glass-overlay flex items-center justify-center p-4">

        <motion.div key="modal"
          initial={{ opacity: 0, scale: 0.95, y: 16 }} animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 16 }} transition={{ type: 'spring', stiffness: 400, damping: 30 }}
          className="w-full max-w-sm relative rounded-3xl p-7 flex flex-col gap-5"
          style={{
            background: '#0f1a2e',
            border: '1px solid rgba(13,71,161,0.4)',
            boxShadow: '0 25px 80px rgba(0,0,0,0.8), 0 0 0 1px rgba(13,71,161,0.2)',
          }}>

          <button onClick={onClose} className="absolute top-4 right-4 btn btn-ghost btn-sm w-8 h-8 p-0 rounded-xl">
            <X size={15} />
          </button>

          {/* Logo + branding */}
          <div className="flex flex-col items-center gap-2">
            <div className="w-16 h-16 rounded-2xl overflow-hidden flex items-center justify-center"
              style={{ background: '#fff', border: '3px solid rgba(13,71,161,0.4)', boxShadow: '0 0 24px rgba(13,71,161,0.4)' }}>
              <img src="/icons/mypytutor_logo.jpg" alt="MyPy Tutor"
                style={{ width: '100%', height: '100%', objectFit: 'contain' }} />
            </div>
            <div className="text-center">
              <h2 className="font-sora font-bold text-white text-lg">
                {tab === 'forgot' ? 'Reset Password' : 'Welcome to MyPy Tutor'}
              </h2>
              <p className="text-xs mt-0.5" style={{ color: '#4d6080' }}>
                Africa's AI Python &amp; ML Tutor
              </p>
            </div>
          </div>

          {/* Tabs */}
          {isAuthTab && (
            <div className="flex rounded-2xl p-1 gap-1" style={{ background: 'rgba(6,13,28,0.8)' }}>
              {(['signin', 'signup'] as const).map(t => (
                <button key={t} onClick={() => { setTab(t); setError(''); setSuccess('') }}
                  className="flex-1 py-2 rounded-xl text-sm font-semibold transition-all duration-200"
                  style={tab === t
                    ? { background: 'linear-gradient(135deg,#0D47A1,#1565E8)', color: '#fff', boxShadow: '0 4px 12px rgba(13,71,161,0.4)' }
                    : { color: '#4d6080' }}>
                  {t === 'signin' ? 'Sign In' : 'Sign Up'}
                </button>
              ))}
            </div>
          )}

          {/* Alerts */}
          <AnimatePresence>
            {error && (
              <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }}
                className="rounded-xl px-4 py-3 text-sm border"
                style={{ background: 'rgba(239,68,68,0.08)', borderColor: 'rgba(239,68,68,0.3)', color: '#fca5a5' }}>
                {error}
                {error.toLowerCase().includes('confirm') && (
                  <button onClick={handleResend} className="block mt-1.5 text-xs underline" style={{ color: '#93c5fd' }}>
                    📧 Resend confirmation email
                  </button>
                )}
              </motion.div>
            )}
            {success && (
              <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }}
                className="rounded-xl px-4 py-3 text-sm border"
                style={{ background: 'rgba(34,197,94,0.08)', borderColor: 'rgba(34,197,94,0.3)', color: '#86efac' }}>
                {success}
              </motion.div>
            )}
          </AnimatePresence>

          {/* Sign In */}
          {tab === 'signin' && (
            <form onSubmit={handleSignIn} className="flex flex-col gap-3">
              <div className="relative">
                <Mail size={14} className="absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" style={{ color: '#4d6080' }} />
                <input type="email" placeholder="Email address" value={siEmail} onChange={e => setSiEmail(e.target.value)}
                  autoComplete="email" required className="pl-10 h-11" style={inputStyle} />
              </div>
              <div className="relative">
                <Lock size={14} className="absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" style={{ color: '#4d6080' }} />
                <input type={siShow ? 'text' : 'password'} placeholder="Password" value={siPass} onChange={e => setSiPass(e.target.value)}
                  autoComplete="current-password" required className="pl-10 pr-10 h-11" style={inputStyle} />
                <button type="button" onClick={() => setSiShow(s => !s)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 transition-colors" style={{ color: '#4d6080' }}>
                  {siShow ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </div>
              <button type="submit" disabled={loading} className="btn btn-primary w-full h-11">
                {loading ? <><div className="loading-dots scale-75"><span/><span/><span/></div> Signing in…</> : 'Sign In'}
              </button>
              <button type="button" onClick={() => { setTab('forgot'); setFgEmail(siEmail); setError(''); setSuccess('') }}
                className="text-xs text-center transition-colors" style={{ color: '#E0A300' }}>
                Forgot password?
              </button>
            </form>
          )}

          {/* Sign Up */}
          {tab === 'signup' && (
            <form onSubmit={handleSignUp} className="flex flex-col gap-3">
              <div className="relative">
                <User size={14} className="absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" style={{ color: '#4d6080' }} />
                <input type="text" placeholder="Full name" value={suName} onChange={e => setSuName(e.target.value)}
                  autoComplete="name" required className="pl-10 h-11" style={inputStyle} />
              </div>
              <div className="relative">
                <Mail size={14} className="absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" style={{ color: '#4d6080' }} />
                <input type="email" placeholder="Email address" value={suEmail} onChange={e => setSuEmail(e.target.value)}
                  autoComplete="email" required className="pl-10 h-11" style={inputStyle} />
              </div>
              <div className="relative">
                <Lock size={14} className="absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" style={{ color: '#4d6080' }} />
                <input type={suShow ? 'text' : 'password'} placeholder="Password (min 8 chars)" value={suPass} onChange={e => setSuPass(e.target.value)}
                  autoComplete="new-password" required className="pl-10 pr-10 h-11" style={inputStyle} />
                <button type="button" onClick={() => setSuShow(s => !s)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 transition-colors" style={{ color: '#4d6080' }}>
                  {suShow ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </div>
              <div className="relative">
                <KeyRound size={14} className="absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" style={{ color: '#4d6080' }} />
                <input type="text" placeholder="Referral / Access code (optional)" value={suCode}
                  onChange={e => setSuCode(e.target.value.toUpperCase())}
                  className="pl-10 h-11 uppercase tracking-widest" style={inputStyle} />
              </div>
              <button type="submit" disabled={loading} className="btn btn-primary w-full h-11">
                {loading ? <><div className="loading-dots scale-75"><span/><span/><span/></div> Creating…</> : 'Create Free Account'}
              </button>
            </form>
          )}

          {/* Forgot */}
          {tab === 'forgot' && (
            <form onSubmit={handleForgot} className="flex flex-col gap-3">
              <p className="text-xs text-center" style={{ color: '#4d6080' }}>Enter your email and we'll send a reset link.</p>
              <div className="relative">
                <Mail size={14} className="absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" style={{ color: '#4d6080' }} />
                <input type="email" placeholder="Email address" value={fgEmail} onChange={e => setFgEmail(e.target.value)} required className="pl-10 h-11" style={inputStyle} />
              </div>
              <button type="submit" disabled={loading} className="btn btn-primary w-full h-11">
                {loading ? 'Sending…' : 'Send Reset Link'}
              </button>
              <button type="button" onClick={() => { setTab('signin'); setError(''); setSuccess('') }}
                className="flex items-center justify-center gap-1.5 text-xs transition-colors" style={{ color: '#93c5fd' }}>
                <ArrowLeft size={12} /> Back to Sign In
              </button>
            </form>
          )}

          {/* Reset Password — opened from ?auth=reset deep-link */}
          {tab === 'reset' && (
            <form onSubmit={handleReset} className="flex flex-col gap-3">
              <p className="text-xs text-center" style={{ color: '#4d6080' }}>Enter your new password below.</p>
              <div className="relative">
                <Lock size={14} className="absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" style={{ color: '#4d6080' }} />
                <input type={rpShow ? 'text' : 'password'} placeholder="New password (min 8 chars)"
                  value={rpPass} onChange={e => setRpPass(e.target.value)}
                  autoComplete="new-password" required className="pl-10 pr-10 h-11" style={inputStyle} />
                <button type="button" onClick={() => setRpShow(s => !s)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 transition-colors" style={{ color: '#4d6080' }}>
                  {rpShow ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </div>
              <button type="submit" disabled={loading} className="btn btn-primary w-full h-11">
                {loading ? 'Updating…' : 'Set New Password'}
              </button>
              <button type="button" onClick={() => { setTab('signin'); setError(''); setSuccess('') }}
                className="flex items-center justify-center gap-1.5 text-xs transition-colors" style={{ color: '#93c5fd' }}>
                <ArrowLeft size={12} /> Back to Sign In
              </button>
            </form>
          )}

          {/* Divider */}
          <div className="flex items-center gap-3 text-xs" style={{ color: '#4d6080' }}>
            <div className="flex-1 h-px" style={{ background: 'rgba(13,71,161,0.2)' }} />
            or continue with
            <div className="flex-1 h-px" style={{ background: 'rgba(13,71,161,0.2)' }} />
          </div>

          {/* Google */}
          <a href={`${API_BASE}/auth/google/login`}
            className="flex items-center justify-center gap-3 w-full py-3 rounded-2xl border text-sm font-semibold transition-all duration-150 hover:opacity-90"
            style={{ background: '#fff', color: '#1a1a2e', borderColor: 'transparent' }}>
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
              <path d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844c-.209 1.125-.843 2.078-1.796 2.717v2.258h2.908C16.658 14.013 17.64 11.706 17.64 9.2z" fill="#4285F4"/>
              <path d="M9 18c2.43 0 4.467-.806 5.956-2.18l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 0 0 9 18z" fill="#34A853"/>
              <path d="M3.964 10.71A5.41 5.41 0 0 1 3.682 9c0-.593.102-1.17.282-1.71V4.958H.957A8.996 8.996 0 0 0 0 9c0 1.452.348 2.827.957 4.042l3.007-2.332z" fill="#FBBC05"/>
              <path d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 0 0 .957 4.958L3.964 7.29C4.672 5.163 6.656 3.58 9 3.58z" fill="#EA4335"/>
            </svg>
            Continue with Google
          </a>

          {/* GitHub */}
          <a href={`${API_BASE}/auth/github/login`}
            className="flex items-center justify-center gap-3 w-full py-3 rounded-2xl border text-sm font-semibold transition-all duration-150 hover:opacity-90"
            style={{ background: '#24292e', color: '#f0f6fc', borderColor: 'rgba(255,255,255,0.1)' }}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 0C5.374 0 0 5.373 0 12c0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23A11.509 11.509 0 0 1 12 5.803c1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576C20.566 21.797 24 17.3 24 12c0-6.627-5.373-12-12-12z"/>
            </svg>
            Continue with GitHub
          </a>

          <p className="text-[10px] text-center" style={{ color: '#4d6080' }}>
            By signing in you agree to our Terms of Service.
          </p>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  )
}
