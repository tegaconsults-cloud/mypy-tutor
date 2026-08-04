import React, { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { Zap, ArrowUpRight } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { getPromptCount } from '../api'

const DEFAULT_LIMIT = 10

export default function PromptCounterBar() {
  const { user } = useAuth()
  const [used,   setUsed]   = useState(0)
  const [limit,  setLimit]  = useState(DEFAULT_LIMIT)
  const [isPaid, setIsPaid] = useState(false)
  const [loaded, setLoaded] = useState(false)

  // Fetch real count from server on mount and whenever user changes
  useEffect(() => {
    setLoaded(false)
    const lid = user?.learner_id || 'default'
    getPromptCount(lid)
      .then(d => {
        if (!d) return
        setUsed(d.used   ?? 0)
        setLimit(d.limit ?? DEFAULT_LIMIT)
        // is_limited = true means free tier (has a cap)
        // is_limited = false means paid tier (no cap) — hide the bar
        setIsPaid(d.is_limited === false)
      })
      .catch(() => {
        // Non-fatal — show bar with defaults so user sees their quota
      })
      .finally(() => setLoaded(true))
  }, [user?.learner_id])

  // Increment locally on each chat message so it updates without a roundtrip
  useEffect(() => {
    const handler = () => {
      setUsed(u => {
        const next = u + 1
        // If we just hit the limit, dispatch an event so ChatPanel can gate immediately
        if (next >= limit) window.dispatchEvent(new Event('prompt-limit-reached'))
        return next
      })
    }
    window.addEventListener('prompt-used', handler)
    return () => window.removeEventListener('prompt-used', handler)
  }, [limit])

  // Don't render until we have data (avoids flash before fetch completes)
  if (!loaded) return null
  // Hide bar for paid users — they have no daily cap
  if (isPaid) return null

  const pct         = Math.min((used / limit) * 100, 100)
  const isNearLimit = pct >= 70
  const isAtLimit   = used >= limit

  const accent    = isAtLimit ? '#ef4444' : isNearLimit ? '#E0A300' : '#3b82f6'
  const textColor = isAtLimit ? '#fca5a5' : isNearLimit ? '#fcd34d' : '#94a3b8'
  // Always show a minimum visible bar width so users can see it even at 0 prompts used
  const barWidth  = used === 0 ? '2px' : `${pct}%`

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="shrink-0 px-4 py-1.5 flex items-center gap-3"
      style={{
        background: isAtLimit ? 'rgba(239,68,68,0.06)' : 'rgba(6,13,28,0.92)',
        borderBottom: `1px solid ${isAtLimit ? 'rgba(239,68,68,0.2)' : 'rgba(13,71,161,0.15)'}`,
        minHeight: 32,
      }}>

      {/* Icon + count */}
      <div className="flex items-center gap-1.5 shrink-0">
        <Zap size={11} style={{ color: accent }} />
        <span className="text-[10px] font-bold" style={{ color: textColor }}>
          {used}/{limit}
          <span className="font-normal ml-1" style={{ color: '#4d6080' }}>free prompts today</span>
        </span>
      </div>

      {/* Progress bar */}
      <div className="flex-1 h-1.5 rounded-full overflow-hidden" style={{ background: 'rgba(255,255,255,0.06)', minWidth: 40 }}>
        <motion.div
          className="h-full rounded-full"
          style={{ background: accent, minWidth: 3 }}
          animate={{ width: barWidth }}
          transition={{ duration: 0.5, ease: 'easeOut' }}
        />
      </div>

      {/* Upgrade CTA when at/near limit */}
      {isNearLimit && (
        <a
          href="https://paystack.shop/pay/vt_re4d3h52"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-0.5 text-[10px] font-bold shrink-0 transition-opacity hover:opacity-80"
          style={{ color: accent }}>
          {isAtLimit ? 'Upgrade' : 'Upgrade'} <ArrowUpRight size={9} />
        </a>
      )}

      {/* Resets note when at limit */}
      {isAtLimit && (
        <span className="text-[9px] shrink-0" style={{ color: '#4d6080' }}>
          resets 5AM WAT
        </span>
      )}
    </motion.div>
  )
}
