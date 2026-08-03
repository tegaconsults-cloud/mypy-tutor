import React, { useEffect, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Menu, MessageSquare, BookOpen, Trophy, BarChart2, Award,
  CreditCard, User, LogOut, Copy, Link2, Lock, TrendingUp,
  ChevronDown, X, Zap,
} from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { useProgress } from '../context/ProgressContext'
import Logo from './Logo'

type Panel = 'chat' | 'courses' | 'quiz' | 'progress' | 'certificates' | 'pricing' | 'profile'

interface Props {
  panel: Panel
  onPanelChange: (p: Panel) => void
  onMenuClick: () => void
  onAuthClick: (tab?: 'signin' | 'signup') => void
  onReferralClick: () => void
}

const TABS: { id: Panel; icon: React.ReactNode; label: string }[] = [
  { id: 'chat',         icon: <MessageSquare size={13} />, label: 'AI Tutor' },
  { id: 'courses',      icon: <BookOpen size={13} />,      label: 'Courses' },
  { id: 'quiz',         icon: <Trophy size={13} />,        label: 'Quiz' },
  { id: 'progress',     icon: <BarChart2 size={13} />,     label: 'Progress' },
  { id: 'certificates', icon: <Award size={13} />,         label: 'Certs' },
  { id: 'pricing',      icon: <CreditCard size={13} />,    label: 'Plans' },
]

const LEVELS = [
  { value: 'beginner',     label: '🟢 Beginner' },
  { value: 'intermediate', label: '🟡 Intermediate' },
  { value: 'advanced',     label: '🔴 Advanced' },
]

/** Human-readable label + colour for each tier key. */
const TIER_META: Record<string, { label: string; color: string; bg: string; border: string }> = {
  free:  { label: 'Free',             color: '#E0A300', bg: 'rgba(224,163,0,0.15)',    border: 'rgba(224,163,0,0.3)' },
  tier1: { label: 'Beginner Bundle',  color: '#60a5fa', bg: 'rgba(13,71,161,0.2)',     border: 'rgba(13,71,161,0.4)' },
  tier2: { label: 'Career Builder',   color: '#a78bfa', bg: 'rgba(139,92,246,0.15)',   border: 'rgba(139,92,246,0.35)' },
  tier3: { label: 'Elite',            color: '#34d399', bg: 'rgba(16,185,129,0.15)',   border: 'rgba(16,185,129,0.35)' },
}

export default function Header({ panel, onPanelChange, onMenuClick, onAuthClick, onReferralClick }: Props) {
  const { user, signOut } = useAuth()
  const { progress, refresh } = useProgress()
  const [dropOpen, setDropOpen] = useState(false)
  const [level, setLevel] = useState(localStorage.getItem('mypy_tutor_level') || 'beginner')
  const [copyMsg, setCopyMsg] = useState('')
  const dropRef = useRef<HTMLDivElement>(null)

  // Fetch progress whenever the user is available so the tier badge is live
  useEffect(() => {
    if (user) refresh(user.learner_id)
  }, [user]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (dropRef.current && !dropRef.current.contains(e.target as Node)) setDropOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const handleLevel = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setLevel(e.target.value)
    localStorage.setItem('mypy_tutor_level', e.target.value)
    window.dispatchEvent(new Event('level-changed'))
  }

  const nav = (p: Panel) => { onPanelChange(p); setDropOpen(false) }

  const copyId = () => {
    navigator.clipboard.writeText(user?.learner_id || '')
    setCopyMsg('Copied!'); setTimeout(() => setCopyMsg(''), 2000)
  }

  const handleSignOut = () => {
    signOut(); setDropOpen(false)
    localStorage.removeItem('mypy_tutor_history_v2')
    localStorage.removeItem('mpt_conv_id')
    window.dispatchEvent(new Event('clear-chat'))
  }

  const initials = (user?.name || user?.email || 'U')
    .split(' ').map(w => w[0]).slice(0, 2).join('').toUpperCase()

  // Resolve the current tier from progress (live) or fall back to 'free'
  const currentTier = progress?.tier ?? 'free'
  const tierMeta = TIER_META[currentTier] ?? TIER_META.free

  return (
    <header
      className="flex items-center justify-between px-4 py-2 gap-3 shrink-0 z-50"
      style={{
        background: 'rgba(6,13,28,0.97)',
        borderBottom: '1px solid rgba(13,71,161,0.3)',
        backdropFilter: 'blur(24px)',
        boxShadow: '0 1px 0 rgba(13,71,161,0.15)',
      }}>

      {/* Left — Logo + brand + nav */}
      <div className="flex items-center gap-3 min-w-0">
        <button onClick={onMenuClick}
          className="btn btn-ghost btn-sm w-9 h-9 rounded-xl p-0 shrink-0"
          aria-label="Menu">
          <Menu size={18} />
        </button>

        {/* Brand */}
        <div className="flex items-center gap-2.5 shrink-0">
          <Logo size={34} shape="none" />
          <div className="hidden sm:flex flex-col leading-none">
            <span className="font-league text-sm font-black tracking-wide"
              style={{ color: '#E0A300', letterSpacing: '0.04em' }}>MYPY</span>
            <span className="font-league text-[10px] font-bold tracking-widest text-blue-300 uppercase">TUTOR</span>
          </div>
        </div>

        {/* Desktop nav tabs */}
        <nav className="desktop-nav gap-0.5 ml-1">
          {TABS.map(t => (
            <button key={t.id} onClick={() => onPanelChange(t.id)}
              className={`nav-tab flex items-center gap-1.5 ${panel === t.id ? 'active' : ''}`}
              style={{ fontSize: '0.75rem' }}>
              {t.icon}{t.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Right */}
      <div className="flex items-center gap-2 shrink-0">
        {/* Level selector */}
        <select value={level} onChange={handleLevel}
          className="text-xs rounded-xl h-9 px-2 cursor-pointer"
          style={{
            width: 'auto',
            background: 'rgba(13,71,161,0.12)',
            border: '1px solid rgba(13,71,161,0.3)',
            color: '#93c5fd',
          }}>
          {LEVELS.map(l => <option key={l.value} value={l.value}>{l.label}</option>)}
        </select>

        {user ? (
          <div className="relative" ref={dropRef}>
            <button onClick={() => setDropOpen(d => !d)}
              className="flex items-center gap-2 px-3 py-1.5 rounded-full transition-all duration-200"
              style={{
                border: '1px solid rgba(13,71,161,0.4)',
                background: 'rgba(13,71,161,0.1)',
              }}>
              {user.picture ? (
                <img src={user.picture} alt="" className="w-7 h-7 rounded-full object-cover" />
              ) : (
                <div className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold text-white"
                  style={{ background: 'linear-gradient(135deg,#0D47A1,#1565E8)' }}>{initials}</div>
              )}
              <span className="text-xs font-semibold max-w-[72px] truncate hidden sm:block" style={{ color: '#bfdbfe' }}>
                {user.name?.split(' ')[0] || 'Learner'}
              </span>
              <ChevronDown size={11} className="text-blue-400" />
            </button>

            <AnimatePresence>
              {dropOpen && (
                <motion.div
                  initial={{ opacity: 0, y: -8, scale: 0.96 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: -8, scale: 0.96 }}
                  transition={{ duration: 0.15 }}
                  className="absolute top-[calc(100%+8px)] right-0 w-64 z-50 py-2 rounded-2xl"
                  style={{
                    background: '#0f1a2e',
                    border: '1px solid rgba(13,71,161,0.35)',
                    boxShadow: '0 20px 60px rgba(0,0,0,0.7), 0 0 0 1px rgba(13,71,161,0.2)',
                  }}>

                  {/* User info */}
                  <div className="px-4 py-3 mb-1"
                    style={{ borderBottom: '1px solid rgba(13,71,161,0.2)' }}>
                    <div className="font-semibold text-sm text-white truncate">{user.name}</div>
                    <div className="text-xs mt-0.5 truncate" style={{ color: '#4d6080' }}>{user.email}</div>
                    {/* Live tier badge — reads from progress context */}
                    <div className="mt-2 inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold uppercase"
                      style={{ background: tierMeta.bg, color: tierMeta.color, border: `1px solid ${tierMeta.border}` }}>
                      <Zap size={9} /> {tierMeta.label}
                    </div>
                  </div>

                  {/* Menu items */}
                  {[
                    { icon: <User size={14} />,      label: 'Edit Profile',      action: () => nav('profile') },
                    { icon: <TrendingUp size={14} />, label: 'Progress & Badges', action: () => nav('progress') },
                    { icon: <Zap size={14} />,        label: 'Upgrade Plan',      action: () => nav('pricing') },
                    { icon: <Award size={14} />,      label: 'My Certificates',   action: () => nav('certificates') },
                  ].map(item => (
                    <button key={item.label} onClick={item.action}
                      className="flex items-center gap-3 w-full px-4 py-2.5 text-sm transition-colors duration-100"
                      style={{ color: '#94a3b8' }}
                      onMouseEnter={e => (e.currentTarget.style.background = 'rgba(13,71,161,0.12)', e.currentTarget.style.color = '#bfdbfe')}
                      onMouseLeave={e => (e.currentTarget.style.background = 'transparent', e.currentTarget.style.color = '#94a3b8')}>
                      <span style={{ color: '#4d6080' }}>{item.icon}</span>{item.label}
                    </button>
                  ))}

                  <div className="divider mx-3" />

                  <button onClick={() => nav('profile')}
                    className="flex items-center gap-3 w-full px-4 py-2.5 text-sm transition-colors duration-100"
                    style={{ color: '#94a3b8' }}
                    onMouseEnter={e => (e.currentTarget.style.background = 'rgba(13,71,161,0.12)', e.currentTarget.style.color = '#bfdbfe')}
                    onMouseLeave={e => (e.currentTarget.style.background = 'transparent', e.currentTarget.style.color = '#94a3b8')}>
                    <Lock size={14} style={{ color: '#4d6080' }} /> Change Password
                  </button>

                  <button onClick={copyId}
                    className="flex items-center gap-3 w-full px-4 py-2.5 text-sm transition-colors duration-100"
                    style={{ color: '#94a3b8' }}
                    onMouseEnter={e => (e.currentTarget.style.background = 'rgba(13,71,161,0.12)', e.currentTarget.style.color = '#bfdbfe')}
                    onMouseLeave={e => (e.currentTarget.style.background = 'transparent', e.currentTarget.style.color = '#94a3b8')}>
                    <Copy size={14} style={{ color: '#4d6080' }} /> {copyMsg || 'Copy Learner ID'}
                  </button>

                  <button onClick={() => { onReferralClick(); setDropOpen(false) }}
                    className="flex items-center gap-3 w-full px-4 py-2.5 text-sm font-semibold transition-colors duration-100"
                    style={{ color: '#E0A300' }}
                    onMouseEnter={e => (e.currentTarget.style.background = 'rgba(224,163,0,0.08)')}
                    onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}>
                    <Link2 size={14} /> Referral &amp; Bonus
                  </button>

                  <div className="divider mx-3" />

                  {/* Sign out — NO admin link for users */}
                  <button onClick={handleSignOut}
                    className="flex items-center gap-3 w-full px-4 py-2.5 text-sm transition-colors duration-100"
                    style={{ color: '#fca5a5' }}
                    onMouseEnter={e => (e.currentTarget.style.background = 'rgba(239,68,68,0.08)')}
                    onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}>
                    <LogOut size={14} /> Sign Out
                  </button>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        ) : (
          <button onClick={() => onAuthClick('signin')} className="btn btn-primary btn-sm">
            Sign In
          </button>
        )}

        <button onClick={() => {
          if (!confirm('Clear chat history?')) return
          localStorage.removeItem('mypy_tutor_history_v2')
          localStorage.removeItem('mpt_conv_id')
          window.dispatchEvent(new Event('clear-chat'))
        }} className="btn btn-ghost btn-sm px-2.5 h-9 rounded-xl" title="Clear chat">
          <X size={16} />
        </button>
      </div>
    </header>
  )
}
