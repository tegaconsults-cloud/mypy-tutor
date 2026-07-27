import React, { useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { signIn, signUp, forgotPassword, resendConfirmation } from '../api'
import { API_BASE } from '../api'

interface Props {
  defaultTab?: 'signin' | 'signup'
  onClose: () => void
}

export default function AuthModal({ defaultTab = 'signin', onClose }: Props) {
  const { setUser } = useAuth()
  const [tab, setTab] = useState<'signin' | 'signup' | 'forgot'>(defaultTab)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  // Sign In
  const [siEmail, setSiEmail] = useState('')
  const [siPass, setSiPass] = useState('')
  const [siShowPw, setSiShowPw] = useState(false)

  // Sign Up
  const [suName, setSuName] = useState('')
  const [suEmail, setSuEmail] = useState('')
  const [suPass, setSuPass] = useState('')
  const [suCode, setSuCode] = useState('')
  const [suShowPw, setSuShowPw] = useState(false)

  // Forgot
  const [fgEmail, setFgEmail] = useState('')

  const handleSignIn = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(''); setLoading(true)
    try {
      const data = await signIn(siEmail, siPass)
      setUser(data)
      onClose()
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Sign in failed'
      if (msg.toLowerCase().includes('confirm')) {
        setError(msg + ' — check your email or resend below.')
      } else {
        setError(msg)
      }
    } finally { setLoading(false) }
  }

  const handleSignUp = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    if (!suName) { setError('Enter your full name.'); return }
    if (!suEmail.includes('@')) { setError('Enter a valid email.'); return }
    if (suPass.length < 8) { setError('Password must be at least 8 characters.'); return }
    setLoading(true)
    try {
      const data = await signUp(suName, suEmail, suPass, suCode)
      const msg: string = data.message || 'Account created!'
      const autoConfirmed = msg.toLowerCase().includes('welcome') || msg.toLowerCase().includes('confirmed')
      if (autoConfirmed) {
        const loginData = await signIn(suEmail, suPass)
        setUser(loginData)
        onClose()
      } else {
        setSuccess('✅ ' + msg + ' — check your email to confirm, then sign in.')
        setTimeout(() => setTab('signin'), 4000)
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Sign up failed')
    } finally { setLoading(false) }
  }

  const handleForgot = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(''); setLoading(true)
    try {
      const data = await forgotPassword(fgEmail)
      setSuccess(data.message || 'Reset link sent! Check your inbox.')
    } catch { setError('Network error. Please try again.') }
    finally { setLoading(false) }
  }

  const handleResend = async () => {
    const email = tab === 'signin' ? siEmail : suEmail
    if (!email) { setError('Enter your email first.'); return }
    const data = await resendConfirmation(email)
    if (data.auto_confirmed) {
      try {
        const loginData = await signIn(email, siPass)
        setUser(loginData); onClose()
      } catch { setSuccess('✅ Confirmed! Sign in below.'); setTab('signin') }
    } else {
      setSuccess(data.message || 'Resent!')
    }
  }

  return (
    <div onClick={(e) => e.target === e.currentTarget && onClose()} style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)',
      zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 20,
    }}>
      <div className="slide-in" style={{
        background: '#1a202c', border: '1px solid #2d3748', borderRadius: 18,
        padding: '32px 28px', width: '100%', maxWidth: 380,
        display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 20,
        position: 'relative',
      }}>
        <button onClick={onClose} style={{
          position: 'absolute', top: 14, right: 16, background: 'transparent',
          border: 'none', color: '#718096', fontSize: '1.2rem', cursor: 'pointer',
        }}>✕</button>

        <div style={{ fontSize: '2.2rem' }}>🐍</div>
        <div style={{ fontSize: '1.1rem', fontWeight: 700, textAlign: 'center' }}>Welcome to MyPy Tutor</div>

        {/* Tabs */}
        {tab !== 'forgot' && (
          <div style={{ display: 'flex', gap: 0, borderRadius: 8, overflow: 'hidden', border: '1px solid #2d3748', width: '100%' }}>
            {(['signin', 'signup'] as const).map(t => (
              <button key={t} onClick={() => { setTab(t); setError(''); setSuccess('') }} style={{
                flex: 1, background: tab === t ? '#2c5282' : 'transparent',
                border: 'none', color: tab === t ? '#90cdf4' : '#718096',
                padding: 9, fontSize: '.84rem', fontWeight: 600, cursor: 'pointer',
                borderRight: t === 'signin' ? '1px solid #2d3748' : 'none',
              }}>{t === 'signin' ? 'Sign In' : 'Sign Up'}</button>
            ))}
          </div>
        )}

        {error && <div style={{ background: 'rgba(116,42,42,.2)', border: '1px solid rgba(116,42,42,.4)', color: '#fc8181', borderRadius: 8, padding: '10px 14px', fontSize: '.82rem', width: '100%', textAlign: 'center' }}>
          {error}
          {error.toLowerCase().includes('confirm') && (
            <button onClick={handleResend} style={{ display: 'block', margin: '6px auto 0', color: '#60a5fa', background: 'transparent', border: 'none', fontSize: '.8rem', cursor: 'pointer', textDecoration: 'underline' }}>
              📧 Resend confirmation email
            </button>
          )}
        </div>}

        {success && <div style={{ background: 'rgba(39,103,73,.15)', border: '1px solid rgba(39,103,73,.4)', color: '#68d391', borderRadius: 8, padding: '10px 14px', fontSize: '.83rem', width: '100%', textAlign: 'center' }}>{success}</div>}

        {/* Sign In */}
        {tab === 'signin' && (
          <form onSubmit={handleSignIn} style={{ display: 'flex', flexDirection: 'column', gap: 10, width: '100%' }}>
            <input type="email" placeholder="Email address" value={siEmail} onChange={e => setSiEmail(e.target.value)} autoComplete="email" required />
            <div style={{ position: 'relative' }}>
              <input type={siShowPw ? 'text' : 'password'} placeholder="Password" value={siPass} onChange={e => setSiPass(e.target.value)} autoComplete="current-password" style={{ paddingRight: 42 }} required />
              <button type="button" onClick={() => setSiShowPw(s => !s)} style={{ position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)', background: 'transparent', border: 'none', color: '#64748b', cursor: 'pointer', fontSize: '1rem' }}>
                {siShowPw ? '🙈' : '👁'}
              </button>
            </div>
            <button type="submit" disabled={loading} className="btn btn-primary" style={{ width: '100%' }}>
              {loading ? 'Signing in…' : 'Sign In'}
            </button>
            <button type="button" onClick={() => { setTab('forgot'); setFgEmail(siEmail); setError(''); setSuccess('') }} style={{ background: 'transparent', border: 'none', color: '#60a5fa', fontSize: '.82rem', cursor: 'pointer', textAlign: 'center' }}>
              Forgot password?
            </button>
          </form>
        )}

        {/* Sign Up */}
        {tab === 'signup' && (
          <form onSubmit={handleSignUp} style={{ display: 'flex', flexDirection: 'column', gap: 10, width: '100%' }}>
            <input type="text" placeholder="Full name" value={suName} onChange={e => setSuName(e.target.value)} autoComplete="name" required />
            <input type="email" placeholder="Email address" value={suEmail} onChange={e => setSuEmail(e.target.value)} autoComplete="email" required />
            <div style={{ position: 'relative' }}>
              <input type={suShowPw ? 'text' : 'password'} placeholder="Password (min 8 chars)" value={suPass} onChange={e => setSuPass(e.target.value)} autoComplete="new-password" style={{ paddingRight: 42 }} required />
              <button type="button" onClick={() => setSuShowPw(s => !s)} style={{ position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)', background: 'transparent', border: 'none', color: '#64748b', cursor: 'pointer', fontSize: '1rem' }}>
                {suShowPw ? '🙈' : '👁'}
              </button>
            </div>
            <input type="text" placeholder="Referral / Access code (optional)" value={suCode} onChange={e => setSuCode(e.target.value.toUpperCase())} style={{ textTransform: 'uppercase', letterSpacing: '.08em' }} />
            <button type="submit" disabled={loading} className="btn btn-primary" style={{ width: '100%' }}>
              {loading ? 'Creating…' : 'Create Account'}
            </button>
          </form>
        )}

        {/* Forgot */}
        {tab === 'forgot' && (
          <form onSubmit={handleForgot} style={{ display: 'flex', flexDirection: 'column', gap: 10, width: '100%' }}>
            <p style={{ color: '#a0aec0', fontSize: '.85rem', textAlign: 'center' }}>Enter your email and we'll send a reset link.</p>
            <input type="email" placeholder="Email address" value={fgEmail} onChange={e => setFgEmail(e.target.value)} required />
            <button type="submit" disabled={loading} className="btn btn-primary" style={{ width: '100%' }}>
              {loading ? 'Sending…' : 'Send Reset Link'}
            </button>
            <button type="button" onClick={() => { setTab('signin'); setError(''); setSuccess('') }} style={{ background: 'transparent', border: 'none', color: '#63b3ed', fontSize: '.82rem', cursor: 'pointer', textAlign: 'center' }}>
              ← Back to Sign In
            </button>
          </form>
        )}

        {/* Divider */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#4a5568', fontSize: '.78rem', width: '100%' }}>
          <div style={{ flex: 1, height: 1, background: '#2d3748' }} />
          or continue with
          <div style={{ flex: 1, height: 1, background: '#2d3748' }} />
        </div>

        {/* Google */}
        <a href={`${API_BASE}/auth/google/login`} style={{
          display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10,
          width: '100%', background: '#fff', color: '#1a202c',
          borderRadius: 10, padding: '13px 20px', fontSize: '.95rem', fontWeight: 600,
          minHeight: 48, transition: 'opacity .15s',
        }} onMouseOver={e => (e.currentTarget.style.opacity = '.88')} onMouseOut={e => (e.currentTarget.style.opacity = '1')}>
          <svg width="20" height="20" viewBox="0 0 18 18" fill="none">
            <path d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844c-.209 1.125-.843 2.078-1.796 2.717v2.258h2.908C16.658 14.013 17.64 11.706 17.64 9.2z" fill="#4285F4"/>
            <path d="M9 18c2.43 0 4.467-.806 5.956-2.18l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 0 0 9 18z" fill="#34A853"/>
            <path d="M3.964 10.71A5.41 5.41 0 0 1 3.682 9c0-.593.102-1.17.282-1.71V4.958H.957A8.996 8.996 0 0 0 0 9c0 1.452.348 2.827.957 4.042l3.007-2.332z" fill="#FBBC05"/>
            <path d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 0 0 .957 4.958L3.964 7.29C4.672 5.163 6.656 3.58 9 3.58z" fill="#EA4335"/>
          </svg>
          Continue with Google
        </a>

        <p style={{ fontSize: '.73rem', color: '#4a5568', textAlign: 'center', lineHeight: 1.5 }}>
          By signing in you agree to our Terms of Service.
        </p>
      </div>
    </div>
  )
}
