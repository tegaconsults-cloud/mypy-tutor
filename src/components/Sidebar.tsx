import React, { useEffect, useState } from 'react'
import { useProgress } from '../context/ProgressContext'
import { getTopics } from '../api'

type Panel = 'chat' | 'courses' | 'quiz' | 'progress' | 'certificates' | 'pricing' | 'profile'

interface Props {
  open: boolean
  onClose: () => void
  onPanelChange: (p: Panel) => void
  onAuthClick: (tab?: 'signin' | 'signup') => void
}

const QUICK_ASK = [
  { label: '📦 Variables', ask: 'Explain Python variables for me' },
  { label: '🔄 Loops', ask: 'Explain loops in Python' },
  { label: '⚙️ Functions', ask: 'Explain functions in Python' },
  { label: '🏗️ OOP', ask: 'Explain OOP in Python' },
  { label: '🛡️ Exceptions', ask: 'Explain exception handling in Python' },
  { label: '📐 Data Structures', ask: 'Explain data structures in Python' },
]

export default function Sidebar({ open, onClose, onPanelChange, onAuthClick }: Props) {
  const { progress } = useProgress()
  const [topics, setTopics] = useState<string[]>([])

  useEffect(() => {
    getTopics().then(d => setTopics(d.topics || []))
  }, [])

  const sendAsk = (msg: string) => {
    window.dispatchEvent(new CustomEvent('sidebar-ask', { detail: msg }))
    onPanelChange('chat')
    onClose()
  }

  return (
    <>
      {/* Overlay */}
      {open && (
        <div onClick={onClose} style={{
          position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)',
          zIndex: 200,
        }} className="sidebar-overlay" />
      )}

      {/* Drawer */}
      <div style={{
        position: 'fixed', top: 0, left: 0, bottom: 0, width: 260,
        maxWidth: '80vw', background: '#0f1117', borderRight: '1px solid #2d3748',
        display: 'flex', flexDirection: 'column', overflowY: 'auto',
        padding: '16px 12px', gap: 16, zIndex: 300,
        transform: open ? 'translateX(0)' : 'translateX(-100%)',
        transition: 'transform .25s ease',
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingBottom: 12, borderBottom: '1px solid #2d3748' }}>
          <span style={{ fontWeight: 700, color: '#63b3ed' }}>🐍 MyPy Tutor</span>
          <button onClick={onClose} style={{ background: 'transparent', border: 'none', color: '#718096', fontSize: '1.2rem', cursor: 'pointer' }}>✕</button>
        </div>

        {/* Quick Ask */}
        <div>
          <h4 style={{ fontSize: '.7rem', textTransform: 'uppercase', letterSpacing: '.08em', color: '#4a5568', marginBottom: 8 }}>Quick Ask</h4>
          {QUICK_ASK.map(q => (
            <button key={q.label} onClick={() => sendAsk(q.ask)} style={{
              display: 'flex', alignItems: 'center', gap: 8, width: '100%',
              background: 'transparent', border: '1px solid #2d3748', color: '#a0aec0',
              borderRadius: 8, padding: '9px 12px', fontSize: '.84rem',
              cursor: 'pointer', textAlign: 'left', marginBottom: 4, minHeight: 44,
              transition: 'all .15s',
            }}>{q.label}</button>
          ))}
        </div>

        {/* Knowledge Gaps */}
        {progress && progress.knowledge_gaps.length > 0 && (
          <div>
            <h4 style={{ fontSize: '.7rem', textTransform: 'uppercase', letterSpacing: '.08em', color: '#4a5568', marginBottom: 8 }}>Knowledge Gaps</h4>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
              {progress.knowledge_gaps.map(g => (
                <span key={g} onClick={() => sendAsk(`I need help understanding ${g}`)} style={{
                  display: 'inline-block', background: '#3b1a1a', border: '1px solid #742a2a',
                  color: '#fc8181', borderRadius: 6, padding: '4px 10px', fontSize: '.78rem',
                  cursor: 'pointer',
                }}>{g}</span>
              ))}
            </div>
          </div>
        )}

        {/* Recent Topics */}
        {progress && progress.topics_seen.length > 0 && (
          <div>
            <h4 style={{ fontSize: '.7rem', textTransform: 'uppercase', letterSpacing: '.08em', color: '#4a5568', marginBottom: 8 }}>Recent Topics</h4>
            {progress.topics_seen.slice(-5).reverse().map(t => (
              <div key={t} onClick={() => sendAsk(`Explain ${t} in Python`)} style={{
                background: '#2d3748', borderRadius: 999, padding: '3px 10px',
                fontSize: '.76rem', margin: 3, cursor: 'pointer', display: 'inline-block',
              }}>{t}</div>
            ))}
          </div>
        )}

        {/* Feedback */}
        <div style={{ marginTop: 'auto', paddingTop: 8, borderTop: '1px solid #2d3748' }}>
          <button onClick={() => window.dispatchEvent(new Event('open-feedback'))} style={{
            display: 'flex', alignItems: 'center', gap: 8, width: '100%',
            background: '#9f7aea', color: '#fff', border: 'none',
            borderRadius: 10, padding: '11px 14px', fontSize: '.86rem',
            fontWeight: 700, cursor: 'pointer', minHeight: 44,
          }}>💬 Send Feedback</button>
        </div>
      </div>
    </>
  )
}
