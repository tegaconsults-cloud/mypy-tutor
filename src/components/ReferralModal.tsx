import React, { useEffect, useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { API_BASE } from '../api'

interface Props { onClose: () => void }

export default function ReferralModal({ onClose }: Props) {
  const { user } = useAuth()
  const [code, setCode] = useState('Loading…')
  const [uses, setUses] = useState(0)
  const [maxUses, setMaxUses] = useState(50)
  const [balance, setBalance] = useState(0)
  const [history, setHistory] = useState<{used_by_email:string;referrer_bonus:number;ts:string}[]>([])
  const [copied, setCopied] = useState(false)

  const lid = user?.learner_id || 'default'
  const appUrl = 'https://mypytutor.com.ng'

  useEffect(() => {
    if (!user) return
    fetch(`${API_BASE}/referral/${lid}`)
      .then(r => r.ok ? r.json() : null)
      .then(d => {
        if (!d) return
        setCode(d.code || '—')
        setUses(d.uses || 0)
        setMaxUses(d.max_uses || 50)
        setBalance(d.bonus_balance || 0)
        setHistory(d.recent_uses || [])
      }).catch(() => {})
  }, [user])

  const shareMsg = `Join MyPy Tutor, your best AI AND PYTHON TUTOR. Use code ${code} for 10% off your first subscription! ${appUrl}`

  const copyCode = () => {
    navigator.clipboard.writeText(shareMsg).then(() => { setCopied(true); setTimeout(() => setCopied(false), 3000) })
  }

  return (
    <div onClick={e => e.target === e.currentTarget && onClose()} style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.85)', backdropFilter: 'blur(10px)', zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 20 }}>
      <div className="slide-in" style={{ background: '#111827', border: '1px solid #1f2937', borderRadius: 24, padding: '28px 24px', width: '100%', maxWidth: 440, display: 'flex', flexDirection: 'column', gap: 16, position: 'relative', maxHeight: '90vh', overflowY: 'auto', boxShadow: '0 25px 60px rgba(0,0,0,.6)' }}>
        <button onClick={onClose} style={{ position: 'absolute', top: 14, right: 16, background: '#1f2937', border: '1px solid #374151', color: '#6b7280', borderRadius: 8, width: 30, height: 30, cursor: 'pointer', fontSize: '.9rem' }}>✕</button>

        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '2rem', marginBottom: 6 }}>🔗</div>
          <h2 style={{ fontSize: '1.1rem', fontWeight: 800, color: '#f1f5f9' }}>Your Referral Dashboard</h2>
          <p style={{ fontSize: '.82rem', color: '#94a3b8', marginTop: 6, lineHeight: 1.55 }}>
            Share your code. Referee gets <strong style={{ color: '#34d399' }}>15% off</strong> — you earn <strong style={{ color: '#60a5fa' }}>5% bonus</strong>.
          </p>
        </div>

        {/* Stats */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8 }}>
          {[['Referrals', uses, '#60a5fa'], ['Max Uses', maxUses, '#a78bfa'], ['Balance', `₦${balance.toFixed(0)}`, '#34d399']].map(([l, v, c]) => (
            <div key={String(l)} style={{ background: '#1f2937', border: '1px solid #374151', borderRadius: 10, padding: 12, textAlign: 'center' }}>
              <div style={{ fontSize: '1.4rem', fontWeight: 800, color: String(c) }}>{v}</div>
              <div style={{ fontSize: '.65rem', color: '#6b7280', marginTop: 2, textTransform: 'uppercase', letterSpacing: '.06em' }}>{l}</div>
            </div>
          ))}
        </div>

        {/* Code */}
        <div style={{ background: '#1f2937', border: '2px dashed #3b82f6', borderRadius: 14, padding: 18, textAlign: 'center' }}>
          <div style={{ fontSize: '.7rem', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '.1em', marginBottom: 8 }}>Your Unique Referral Code</div>
          <div style={{ fontFamily: 'monospace', fontSize: '1.8rem', fontWeight: 800, color: '#60a5fa', letterSpacing: '.2em' }}>{code}</div>
        </div>

        {/* How it works */}
        <div style={{ background: 'rgba(59,130,246,.07)', border: '1px solid rgba(59,130,246,.18)', borderRadius: 10, padding: 12, fontSize: '.79rem', color: '#94a3b8', lineHeight: 1.7 }}>
          <strong style={{ color: '#93c5fd' }}>How it works:</strong><br />
          • Friend enters your code at signup<br />
          • They get <strong style={{ color: '#34d399' }}>15% discount</strong> on first payment<br />
          • You earn <strong style={{ color: '#60a5fa' }}>5% bonus</strong>, credited automatically<br />
          • Bonus paid out upon request to admin
        </div>

        <button onClick={copyCode} className="btn btn-primary" style={{ width: '100%' }}>
          {copied ? '✅ Copied to clipboard!' : '📋 Copy Referral Message'}
        </button>

        {/* Share text */}
        <div style={{ background: '#0f172a', border: '1px solid #1f2937', borderRadius: 8, padding: 10, fontSize: '.76rem', color: '#94a3b8', lineHeight: 1.6, fontStyle: 'italic' }}>
          {shareMsg}
        </div>

        {/* History */}
        {history.length > 0 && (
          <div>
            <div style={{ fontSize: '.72rem', color: '#6b7280', textTransform: 'uppercase', letterSpacing: '.08em', marginBottom: 8 }}>Recent Referrals</div>
            {history.map((h, i) => (
              <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '7px 0', borderBottom: '1px solid #1f2937', fontSize: '.78rem' }}>
                <span style={{ color: '#94a3b8' }}>{h.used_by_email || 'user'}</span>
                <span style={{ color: '#34d399', fontWeight: 600 }}>+₦{(h.referrer_bonus || 0).toFixed(2)}</span>
                <span style={{ color: '#4b5563' }}>{h.ts || ''}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
