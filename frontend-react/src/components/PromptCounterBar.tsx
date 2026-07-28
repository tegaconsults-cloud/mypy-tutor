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

  return (
    <div className="flex items-center gap-3 px-4 py-1 shrink-0"
      style={{ background: 'rgba(15,23,42,0.7)', borderBottom: '1px solid #1e293b' }}>

      <div className="flex items-center gap-1.5 shrink-0">
        <Cpu size={11} className={isAtLimit ? 'text-red-400' : isNearLimit ? 'text-amber-400' : 'text-slate-500'} />
        <span className={`text-[10px] font-semibold ${isAtLimit ? 'text-red-400' : isNearLimit ? 'text-amber-400' : 'text-slate-500'}`}>
          {used}/{limit} prompts
        </span>
      </div>

      <div className="flex-1 h-1 rounded-full overflow-hidden" style={{ background: '#1e293b' }}>
        <motion.div
          className="h-full rounded-full"
          style={{ background: isAtLimit ? '#ef4444' : isNearLimit ? '#f59e0b' : '#22c55e' }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.4 }}
        />
      </div>

      {isAtLimit && (
        <a href="https://paystack.shop/pay/vt_re4d3h52" target="_blank" rel="noopener noreferrer"
          className="flex items-center gap-1 text-[10px] font-bold text-blue-400 hover:text-blue-300 shrink-0 transition-colors">
          Upgrade <ArrowUpRight size={10} />
        </a>
      )}
    </div>
  )
}
