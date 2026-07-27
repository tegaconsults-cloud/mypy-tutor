import React from 'react'

type Panel = 'chat' | 'courses' | 'quiz' | 'progress' | 'certificates' | 'pricing'

const TABS: { id: Panel; icon: string; label: string }[] = [
  { id: 'chat', icon: '💬', label: 'Chat' },
  { id: 'courses', icon: '📚', label: 'Courses' },
  { id: 'quiz', icon: '🏆', label: 'Quiz' },
  { id: 'progress', icon: '📊', label: 'Progress' },
  { id: 'certificates', icon: '🎓', label: 'Certs' },
  { id: 'pricing', icon: '💎', label: 'Plans' },
]

interface Props { panel: Panel; onPanelChange: (p: Panel) => void }

export default function BottomNav({ panel, onPanelChange }: Props) {
  return (
    <nav style={{
      display: 'flex', justifyContent: 'space-around', padding: '4px 0',
      background: '#0f1117', borderTop: '1px solid #2d3748',
      flexShrink: 0, paddingBottom: 'env(safe-area-inset-bottom)',
    }} className="bottom-nav">
      {TABS.map(t => (
        <button key={t.id} onClick={() => onPanelChange(t.id)} style={{
          display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2,
          background: 'transparent', border: 'none',
          color: panel === t.id ? '#63b3ed' : '#4a5568',
          fontSize: '0.6rem', cursor: 'pointer', padding: '6px 10px',
          borderRadius: 8, minWidth: 48, transition: 'color .15s',
        }}>
          <span style={{ fontSize: '1.3rem', lineHeight: 1 }}>{t.icon}</span>
          {t.label}
        </button>
      ))}
    </nav>
  )
}
