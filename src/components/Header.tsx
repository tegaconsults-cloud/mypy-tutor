import React, { useEffect, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Menu, MessageSquare, BookOpen, Trophy, BarChart2, Award,
  CreditCard, User, LogOut, Copy, Link2, Lock, TrendingUp,
  ChevronDown, X, Zap,
} from 'lucide-react'
import { useAuth } from '../context/AuthContext'
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
  { id: 'chat',         icon: <MessageSquare size={14} />, label: 'Chat' },
  { id: 'courses',      icon: <BookOpen size={14} />,      label: 'Courses' },
  { id: 'quiz',         icon: <Trophy size={14} />,        label: 'Quiz' },
  { id: 'progress',     icon: <BarChart2 size={14} />,     label: 'Progress' },
  { id: 'certificates', icon: <Award size={14} />,         label: 'Certs' },
  { id: 'pricing',      icon: <CreditCard size={14} />,    label: 'Plans' },
]

const LEVELS = [
  { value: 'beginner',     label: '🟢 Beginner' },
  { value: 'intermediate', label: '🟡 Mid' },
  { value: 'advanced',     label: '🔴 Advanced' },
]

export default function Header({ panel, onPanelChange, onMenuClick, onAuthClick, onReferralClick }: Props) {
  const { user, signOut } = useAuth()
  const [dropOpen, setDropOpen] = useState(false)
  const [level, setLevel] = useState(localStorage.getItem('mypy_tutor_level') || 'beginner')
  const [copyMsg, setCopyMsg] = useState('')
  const dropRef = useRef<HTMLDivElement>(null)

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
    setCopyMsg('Copied!')
    setTimeout(() => setCopyMsg(''), 2000)
  }

  const handleSignOut = () => {
    signOut(); setDropOpen(false)
    localStorage.removeItem('mypy_tutor_history_v2')
    localStorage.removeItem('mpt_conv_id')
    window.dispatchEvent(new Event('clear-chat'))
  }

  const initials = (user?.name || user?.email || 'U')
    .split(' ').map(w => w[0]).slice(0, 2).join('').toUpperCase()

  return (
    <header className="flex items-center justify-between px-4 py-2 gap-3 shrink-0 z-50"
      style={{ background: 'rgba(15,23,42,0.95)', borderBottom: '1px solid #1e293b', backdropFilter: 'blur(20px)' }}>

      {/* Left */}
      <div className="flex items-center gap-2 min-w-0">
        <button onClick={onMenuClick} className="btn btn-ghost btn-sm w-9 h-9 rounded-xl p-0" aria-label="Menu">
          <Menu size={18} />
        </button>

        <div className="flex items-center gap-2 shrink-0">
          <Logo size={32} shape="circle" style={{ border: '2px solid rgba(37,99,235,0.4)' }} />
          <span className="font-bold text-sm text-slate-100 hidden sm:block" style={{ fontFamily: 'Sora, sans-serif' }}>
            MyPy Tutor
          </span>
        </div>

        {/* Desktop tabs */}
        <nav className="desktop-nav gap-1 ml-2">
          {TABS.map(t => (
            <button key={t.id} onClick={() => onPanelChange(t.id)}
              className={`nav-tab flex items-center gap-1.5 ${panel === t.id ? 'active' : ''}`}>
              {t.icon}{t.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Right */}
      <div className="flex items-center gap-2 shrink-0">
        <select value={level} onChange={handleLevel}
          className="text-xs rounded-xl h-9 px-2 border-slate-600 bg-slate-800/60 text-slate-300 cursor-pointer"
          style={{ width: 'auto' }}>
          {LEVELS.map(l => <option key={l.value} value={l.value}>{l.label}</option>)}
        </select>

        {user ? (
          <div className="relative" ref={dropRef}>
            <button onClick={() => setDropOpen(d => !d)}
              className="flex items-center gap-2 px-3 py-1.5 rounded-full border border-slate-700 bg-slate-800/60 hover:border-slate-500 transition-all duration-200">
              {user.picture ? (
                <img src={user.picture} alt="" className="w-7 h-7 rounded-full object-cover" />
              ) : (
                <div className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold text-white"
                  style={{ background: 'linear-gradient(135deg,#2563eb,#7c3aed)' }}>{initials}</div>
              )}
              <span className="text-xs text-slate-200 font-medium max-w-[80px] truncate hidden sm:block">
                {user.name?.split(' ')[0] || 'Learner'}
              </span>
              <ChevronDown size={12} className="text-slate-500" />
            </button>

            <AnimatePresence>
              {dropOpen && (
                <motion.div
                  initial={{ opacity: 0, y: -8, scale: 0.96 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: -8, scale: 0.96 }}
                  transition={{ duration: 0.15 }}
                  className="absolute top-[calc(100%+8px)] right-0 w-60 z-50 py-1.5 rounded-2xl"
                  style={{ background: '#1e293b', border: '1px solid #334155', boxShadow: '0 20px 60px rgba(0,0,0,0.6)' }}>

                  {/* User info */}
                  <div className="px-4 py-3 border-b border-slate-700/60 mb-1">
                    <div className="font-semibold text-sm text-slate-100 truncate">{user.name}</div>
                    <div className="text-xs text-slate-500 mt-0.5 truncate">{user.email}</div>
                  </div>

                  {/* Navigation items */}
                  {[
                    { icon: <User size={14} />,      label: 'Edit Profile',      action: () => nav('profile') },
                    { icon: <TrendingUp size={14} />, label: 'Progress & Badges', action: () => nav('progress') },
                    { icon: <Zap size={14} />,        label: 'Upgrade Plan',      action: () => nav('pricing') },
                    { icon: <Award size={14} />,      label: 'My Certificates',   action: () => nav('certificates') },
                  ].map(item => (
                    <button key={item.label} onClick={item.action}
                      className="flex items-center gap-3 w-full px-4 py-2.5 text-sm text-slate-300 hover:bg-white/5 hover:text-slate-100 transition-colors duration-100">
                      <span className="text-slate-500">{item.icon}</span>{item.label}
                    </button>
                  ))}

                  <div className="divider mx-3" />

                  {/* Account actions */}
                  <button onClick={() => nav('profile')}
                    className="flex items-center gap-3 w-full px-4 py-2.5 text-sm text-slate-300 hover:bg-white/5 hover:text-slate-100 transition-colors duration-100">
                    <Lock size={14} className="text-slate-500" /> Change Password
                  </button>

                  <button onClick={copyId}
                    className="flex items-center gap-3 w-full px-4 py-2.5 text-sm text-slate-300 hover:bg-white/5 hover:text-slate-100 transition-colors duration-100">
                    <Copy size={14} className="text-slate-500" /> {copyMsg || 'Copy Learner ID'}
                  </button>

                  <button onClick={() => { onReferralClick(); setDropOpen(false) }}
                    className="flex items-center gap-3 w-full px-4 py-2.5 text-sm font-semibold text-emerald-400 hover:bg-emerald-500/5 transition-colors duration-100">
                    <Link2 size={14} /> Referral &amp; Bonus
                  </button>

                  <div className="divider mx-3" />

                  {/* Sign out — NO admin link here */}
                  <button onClick={handleSignOut}
                    className="flex items-center gap-3 w-full px-4 py-2.5 text-sm text-red-400 hover:bg-red-500/5 transition-colors duration-100">
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
