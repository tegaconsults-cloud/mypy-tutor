import React, { memo, useEffect, useRef, useState } from 'react'
import { Zap, ArrowUpRight } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { getPromptCount } from '../api'

const DEFAULT_LIMIT = 10

// Memoised — avoids re-renders from parent unless user changes
const PromptCounterBar = memo(function PromptCounterBar() {
  const { user } = useAuth()
  const [used,   setUsed]   = useState(0)
  const [limit,  setLimit]  = useState(DEFAULT_LIMIT)
  const [isPaid, setIsPaid] = useState(false)
  const [loaded, setLoaded] = useState(false)
  // Track last fetched learner_id to avoid duplicate fetches
  const fetchedId = useRef<string>('')

  useEffect(() => {
    const lid = user?.learner_id || 'default'
    // Skip re-fetch if same learner (e.g. parent re-renders)
    if (lid === fetchedId.current && loaded) return
    fetchedId.current = lid
    setLoaded(false)

    getPromptCount(lid)
      .then(d => {
        if (!d) return
        setUsed(d.used   ?? 0)
        setLimit(d.limit ?? DEFAULT_LIMIT)
        setIsPaid(d.is_limited === false)
      })
      .catch(() => {})
      .finally(() => setLoaded(true))
  }, [user?.learner_id]) // only re-fetch when learner changes

  // Increment locally on each chat message
  useEffect(() => {
    const handler = () => {
      setUsed(u => {
        const next = u + 1
        if (next >= limit) window.dispatchEvent(new Event('prompt-limit-reached'))
        return next
      })
    }
    window.addEventListener('prompt-used', handler)
    return () => window.removeEventListener('prompt-used', handler)
  }, [limit])

  if (!loaded || isPaid) return null

  const pct         = Math.min((used / limit) * 100, 100)
  const isNearLimit = pct >= 70
  const isAtLimit   = used >= limit

  const accent    = isAtLimit ? '#ef4444' : isNearLimit ? '#E0A300' : '#3b82f6'
  const textColor = isAtLimit ? '#fca5a5' : isNearLimit ? '#fcd34d' : '#94a3b8'
  const barWidth  = used === 0 ? '2px' : `${pct}%`

  return (
    <div
      className="shrink-0 px-4 py-1.5 flex items-center gap-3"
      style={{
        background: isAtLimit ? 'rgba(239,68,68,0.06)' : 'rgba(6,13,28,0.92)',
        borderBottom: `1px solid ${isAtLimit ? 'rgba(239,68,68,0.2)' : 'rgba(13,71,161,0.15)'}`,
        minHeight: 32,
      }}>

      <div className="flex items-center gap-1.5 shrink-0">
        <Zap size={11} style={{ color: accent }} />
        <span className="text-[10px] font-bold" style={{ color: textColor }}>
          {used}/{limit}
          <span className="font-normal ml-1" style={{ color: '#4d6080' }}>free prompts today</span>
        </span>
      </div>

      {/* CSS transition — no framer-motion for a simple bar */}
      <div className="flex-1 h-1.5 rounded-full overflow-hidden"
        style={{ background: 'rgba(255,255,255,0.06)', minWidth: 40 }}>
        <div
          className="h-full rounded-full"
          style={{
            background: accent,
            width: barWidth,
            minWidth: 3,
            transition: 'width 0.4s ease-out',
          }} />
      </div>

      {isNearLimit && (
        <a
          href="https://paystack.shop/pay/vt_re4d3h52"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-0.5 text-[10px] font-bold shrink-0 transition-opacity hover:opacity-80"
          style={{ color: accent }}>
          Upgrade <ArrowUpRight size={9} />
        </a>
      )}

      {isAtLimit && (
        <span className="text-[9px] shrink-0" style={{ color: '#4d6080' }}>
          resets 5AM WAT
        </span>
      )}
    </div>
  )
})

export default PromptCounterBar
