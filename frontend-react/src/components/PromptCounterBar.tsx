import React, { useEffect, useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { getPromptCount } from '../api'

const FREE_LIMIT = 10

export default function PromptCounterBar() {
  const { user } = useAuth()
  const [used, setUsed] = useState(0)
  const [limit, setLimit] = useState(FREE_LIMIT)

  useEffect(() => {
    const lid = user?.learner_id || 'default'
    getPromptCount(lid).then(d => {
      if (!d) return
      setUsed(d.used ?? 0)
      setLimit(d.limit ?? FREE_LIMIT)
    }).catch(() => {})
  }, [user])

  // Also listen for chat responses that increment usage
  useEffect(() => {
    const handler = () => {
      setUsed(u => Math.min(u + 1, limit))
    }
    window.addEventListener('prompt-used', handler)
    return () => window.removeEventListener('prompt-used', handler)
  }, [limit])

  const pct = Math.min((used / limit) * 100, 100)
  const color = pct >= 90 ? '#fc8181' : pct >= 70 ? '#f6ad55' : '#68d391'

  return (
    <div style={{
      background: '#0f1117',
      borderBottom: '1px solid #1e2533',
      padding: '5px 16px',
      display: 'flex',
      alignItems: 'center',
      gap: 10,
      flexShrink: 0,
    }}>
      <span style={{ fontSize: '.7rem', color: '#718096', whiteSpace: 'nowrap', minWidth: 90 }}>
        ⚡ {used}/{limit} prompts
      </span>
      <div style={{ flex: 1, height: 4, background: '#2d3748', borderRadius: 999, overflow: 'hidden' }}>
        <div style={{ width: `${pct}%`, height: '100%', background: color, borderRadius: 999, transition: 'width .4s ease' }} />
      </div>
      {used >= limit && (
        <a href="https://paystack.shop/pay/vt_re4d3h52" target="_blank" rel="noopener noreferrer"
          style={{ fontSize: '.68rem', color: '#63b3ed', whiteSpace: 'nowrap', fontWeight: 600 }}>
          Upgrade ↗
        </a>
      )}
    </div>
  )
}
