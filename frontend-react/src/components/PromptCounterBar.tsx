import React, { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { Cpu, ArrowUpRight } from 'lucide-react'
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

  useEffect(() => {
    const handler = () => setUsed(u => Math.min(u + 1, limit))
    window.addEventListener('prompt-used', handler)
    return () => window.removeEventListener('prompt-used', handler)
  }, [limit])

  const pct = Math.min((used / limit) * 100, 100)
  const isNearLimit = pct >= 80
  const isAtLimit   = used >= limit

  const barColor = isAtLimit   ? '#ef4444' :
                   isNearLimit ? '#E0A300' : '#0D47A1'
  const textColor = isAtLimit   ? '#fca5a5' :
                    isNearLimit ? '#E0A300' : '#4d6080'

  return (
    <div className="flex items-center gap-3 px-4 py-1 shrink-0"
      style={{ background: 'rgba(6,13,28,0.85)', borderBottom: '1px solid rgba(13,71,161,0.1)' }}>

      <div className="flex items-center gap-1.5 shrink-0">
        <Cpu size={11} style={{ color: textColor }} />
        <span className="text-[10px] font-semibold" style={{ color: textColor }}>
          {used}/{limit} prompts
        </span>
      </div>

      <div className="flex-1 h-1 rounded-full overflow-hidden" style={{ background: 'rgba(13,71,161,0.15)' }}>
        <motion.div className="h-full rounded-full"
          style={{ background: barColor }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.4 }} />
      </div>

      {isAtLimit && (
        <a href="https://paystack.shop/pay/vt_re4d3h52" target="_blank" rel="noopener noreferrer"
          className="flex items-center gap-1 text-[10px] font-bold transition-colors shrink-0"
          style={{ color: '#E0A300' }}>
          Upgrade <ArrowUpRight size={10} />
        </a>
      )}
    </div>
  )
}
