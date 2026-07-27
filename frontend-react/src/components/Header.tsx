import React, { useEffect, useRef, useState } from 'react'
import { useAuth } from '../context/AuthContext'

type Panel = 'chat' | 'courses' | 'quiz' | 'progress' | 'certificates' | 'pricing' | 'profile'

interface Props {
  panel: Panel
  onPanelChange: (p: Panel) => void
  onMenuClick: () => void
  onAuthClick: (tab?: 'signin' | 'signup') => void
  onReferralClick: () => void
}

const TABS: { id: Panel; label: string }[] = [
  { id: 'chat',         label: '💬 Chat' },
  { id: 'courses',      label: '📚 Courses' },
  { id: 'quiz',         label: '🏆 Quiz' },
  { id: 'progress',     label: '📊 Progress' },
  { id: 'certificates', label: '🎓 Certs' },
  { id: 'pricing',      label: '💎 Plans' },
]

export default function Header({ panel, onPanelChange, onMenuClick, onAuthClick, onReferralClick }: Props) {
  const { user, signOut } = useAuth()
  const [dropdownOpen, setDropdownOpen] = useState(false)
  const [level, setLevel] = useState(localStorage.getItem('mypy_tutor_level') || 'beginner')
  const [copyMsg, setCopyMsg] = useState('')
  const dropRef = useRef<HTMLDivElement>(null)

  // Close dropdown on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (dropRef.current && !dropRef.current.contains(e.target as Node)) {
        setDropdownOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const handleLevel = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setLevel(e.target.value)
    localStorage.setItem('mypy_tutor_level', e.target.value)
    window.dispatchEvent(new Event('level-changed'))
  }

  const navigate = (p: Panel) => {
    onPanelChange(p)
    setDropdownOpen(false)
  }

  const copyLearnerId = () => {
    const lid = user?.learner_id || ''
    navigator.clipboard.writeText(lid).then(() => {
      setCopyMsg('Copied!')
      setTimeout(() => setCopyMsg(''), 2000)
    })
  }

  const handleSignOut = () => {
    signOut()
    setDropdownOpen(false)
    localStorage.removeItem('mypy_tutor_history_v2')
    localStorage.removeItem('mpt_conv_id')
    window.dispatchEvent(new Event('clear-chat'))
  }

  const initials = (user?.name || user?.email || 'U')
    .split(' ')
    .map(w => w[0])
    .slice(0, 2)
    .join('')
    .toUpperCase()

  return (
    <header style={{
      background: '#0f1117', borderBottom: '1px solid #2d3748',
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      padding: '10px 16px', gap: 10, flexShrink: 0, zIndex: 100,
    }}>
      {/* Left */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, minWidth: 0 }}>
        <button onClick={onMenuClick} style={{
          background: 'transparent', border: '1px solid #2d3748', color: '#718096',
          borderRadius: 8, width: 36, height: 36, fontSize: '1.1rem', cursor: 'pointer',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }} aria-label="Menu">☰</button>

        <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#63b3ed', whiteSpace: 'nowrap' }}>
          🐍 MyPy Tutor
        </div>

        {/* Desktop nav */}
        <nav style={{ display: 'flex', gap: 4 }} className="desktop-nav">
          {TABS.map(t => (
            <button key={t.id} onClick={() => onPanelChange(t.id)} style={{
              background: panel === t.id ? '#2c5282' : 'transparent',
              border: `1px solid ${panel === t.id ? '#4299e1' : '#2d3748'}`,
              color: panel === t.id ? '#90cdf4' : '#718096',
              borderRadius: 8, padding: '5px 12px', fontSize: '0.8rem',
              cursor: 'pointer', whiteSpace: 'nowrap', height: 34, transition: 'all .15s',
            }}>{t.label}</button>
          ))}
        </nav>
      </div>

      {/* Right */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexShrink: 0 }}>
        <select value={level} onChange={handleLevel} style={{
          background: '#1a202c', border: '1px solid #2d3748', color: '#e2e8f0',
          borderRadius: 8, padding: '6px 8px', fontSize: '0.8rem', height: 36, cursor: 'pointer',
        }}>
          <option value="beginner">🟢 Beginner</option>
          <option value="intermediate">🟡 Mid</option>
          <option value="advanced">🔴 Advanced</option>
        </select>

        {user ? (
          <div style={{ position: 'relative' }} ref={dropRef}>
            <button onClick={() => setDropdownOpen(d => !d)} style={{
              display: 'flex', alignItems: 'center', gap: 7,
              background: '#1a202c', border: '1px solid #2d3748',
              borderRadius: 999, padding: '3px 12px 3px 4px',
              cursor: 'pointer', color: '#e2e8f0',
            }}>
              {user.picture ? (
                <img src={user.picture} alt="" style={{ width: 28, height: 28, borderRadius: '50%', objectFit: 'cover' }} />
              ) : (
                <div style={{
                  width: 28, height: 28, borderRadius: '50%',
                  background: 'linear-gradient(135deg,#2b6cb0,#553c9a)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  color: '#fff', fontSize: '0.72rem', fontWeight: 700,
                }}>
                  {initials}
                </div>
              )}
              <span style={{ fontSize: '0.78rem', maxWidth: 100, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {user.name?.split(' ')[0] || 'Learner'}
              </span>
              <span style={{ fontSize: '0.6rem', color: '#718096' }}>▾</span>
            </button>

            {dropdownOpen && (
              <div style={{
                position: 'absolute', top: 'calc(100% + 8px)', right: 0,
                background: '#1a202c', border: '1px solid #2d3748', borderRadius: 12,
                minWidth: 220, padding: 6, zIndex: 500,
                boxShadow: '0 12px 32px rgba(0,0,0,.55)',
              }} className="slide-in">
                {/* User info header */}
                <div style={{ padding: '10px 14px 8px', borderBottom: '1px solid #2d3748', marginBottom: 4 }}>
                  <div style={{ fontWeight: 700, fontSize: '.88rem', color: '#f1f5f9' }}>{user.name}</div>
                  <div style={{ fontSize: '.72rem', color: '#718096', marginTop: 2 }}>{user.email}</div>
                </div>

                {/* Menu items */}
                {[
                  { icon: '👤', label: 'Edit Profile',      action: () => navigate('profile') },
                  { icon: '📊', label: 'Progress & Badges', action: () => navigate('progress') },
                  { icon: '💎', label: 'Upgrade Plan',       action: () => navigate('pricing') },
                  { icon: '🎓', label: 'My Certificates',    action: () => navigate('certificates') },
                ].map(item => (
                  <button key={item.label} onClick={item.action} style={{
                    display: 'flex', alignItems: 'center', gap: 9, padding: '9px 12px',
                    borderRadius: 7, width: '100%', background: 'transparent', border: 'none',
                    color: '#e2e8f0', cursor: 'pointer', fontSize: '.84rem', textAlign: 'left',
                    transition: 'background .12s',
                  }}
                    onMouseEnter={e => (e.currentTarget.style.background = '#2d3748')}
                    onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
                  >
                    {item.icon} {item.label}
                  </button>
                ))}

                <div style={{ borderTop: '1px solid #2d3748', margin: '4px 0' }} />

                {/* Change password */}
                <button onClick={() => { navigate('profile') }} style={{
                  display: 'flex', alignItems: 'center', gap: 9, padding: '9px 12px',
                  borderRadius: 7, width: '100%', background: 'transparent', border: 'none',
                  color: '#e2e8f0', cursor: 'pointer', fontSize: '.84rem', textAlign: 'left',
                }}
                  onMouseEnter={e => (e.currentTarget.style.background = '#2d3748')}
                  onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
                >
                  🔐 Change Password
                </button>

                {/* Copy Learner ID */}
                <button onClick={copyLearnerId} style={{
                  display: 'flex', alignItems: 'center', gap: 9, padding: '9px 12px',
                  borderRadius: 7, width: '100%', background: 'transparent', border: 'none',
                  color: '#e2e8f0', cursor: 'pointer', fontSize: '.84rem', textAlign: 'left',
                }}
                  onMouseEnter={e => (e.currentTarget.style.background = '#2d3748')}
                  onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
                >
                  🪪 {copyMsg || 'Copy Learner ID'}
                </button>

                {/* Referral & Bonus */}
                <button onClick={() => { onReferralClick(); setDropdownOpen(false) }} style={{
                  display: 'flex', alignItems: 'center', gap: 9, padding: '9px 12px',
                  borderRadius: 7, width: '100%', background: 'transparent', border: 'none',
                  color: '#34d399', cursor: 'pointer', fontSize: '.84rem', fontWeight: 600, textAlign: 'left',
                }}
                  onMouseEnter={e => (e.currentTarget.style.background = '#2d3748')}
                  onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
                >
                  🔗 Referral &amp; Bonus
                </button>

                <div style={{ borderTop: '1px solid #2d3748', margin: '4px 0' }} />

                {/* Sign out */}
                <button onClick={handleSignOut} style={{
                  display: 'flex', alignItems: 'center', gap: 9, padding: '9px 12px',
                  borderRadius: 7, width: '100%', background: 'transparent', border: 'none',
                  color: '#fc8181', cursor: 'pointer', fontSize: '.84rem', textAlign: 'left',
                }}
                  onMouseEnter={e => (e.currentTarget.style.background = 'rgba(252,129,129,.08)')}
                  onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
                >
                  🚪 Sign Out
                </button>
              </div>
            )}
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
        }} style={{
          background: 'transparent', border: '1px solid #2d3748', color: '#718096',
          borderRadius: 8, padding: '0 10px', fontSize: '0.8rem', height: 36, cursor: 'pointer',
        }}>✕ Clear</button>
      </div>
    </header>
  )
}
