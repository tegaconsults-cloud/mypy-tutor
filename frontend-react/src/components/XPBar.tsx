import React from 'react'
import { useProgress } from '../context/ProgressContext'

const THRESHOLDS: Record<string, number> = { beginner: 200, intermediate: 500, advanced: 9999 }

export default function XPBar() {
  const { progress } = useProgress()
  if (!progress) return (
    <div style={{ height: 22, background: '#0f1117', borderBottom: '1px solid #1a202c' }} />
  )

  const { xp, level, badges } = progress
  const max = THRESHOLDS[level] || 200
  const pct = Math.min((xp / max) * 100, 100)

  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 8,
      padding: '4px 16px', background: '#0f1117',
      borderBottom: '1px solid #1a202c', flexShrink: 0,
    }}>
      <span style={{ fontSize: '.72rem', color: '#718096', whiteSpace: 'nowrap', minWidth: 100 }}>
        XP: {xp} · {level.charAt(0).toUpperCase() + level.slice(1)}
      </span>
      <div style={{ flex: 1, height: 5, background: '#2d3748', borderRadius: 99, overflow: 'hidden' }}>
        <div style={{
          height: '100%', width: `${pct}%`,
          background: 'linear-gradient(90deg, #3182ce, #63b3ed)',
          borderRadius: 99, transition: 'width .6s ease',
        }} />
      </div>
      {badges.length > 0 && (
        <span style={{ fontSize: '.8rem', whiteSpace: 'nowrap', maxWidth: 140, overflow: 'hidden', textOverflow: 'ellipsis' }}>
          {badges.slice(-3).join(' ')}
        </span>
      )}
    </div>
  )
}
