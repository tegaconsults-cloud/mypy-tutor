import React from 'react'
import { motion } from 'framer-motion'
import { Zap, Star } from 'lucide-react'
import { useProgress } from '../context/ProgressContext'

const THRESHOLDS: Record<string, number> = { beginner: 200, intermediate: 500, advanced: 9999 }

export default function XPBar() {
  const { progress } = useProgress()

  if (!progress) return (
    <div className="h-8 shrink-0" style={{ background: 'rgba(15,23,42,0.8)', borderBottom: '1px solid #1e293b' }} />
  )

  const { xp, level, badges } = progress
  const max = THRESHOLDS[level] || 200
  const pct = Math.min((xp / max) * 100, 100)
  const levelLabel = level.charAt(0).toUpperCase() + level.slice(1)

  return (
    <div className="flex items-center gap-3 px-4 py-1.5 shrink-0"
      style={{ background: 'rgba(15,23,42,0.8)', borderBottom: '1px solid #1e293b' }}>

      <div className="flex items-center gap-1.5 shrink-0">
        <Zap size={12} className="text-amber-400" />
        <span className="text-xs font-bold text-amber-400">{xp.toLocaleString()} XP</span>
        <span className="text-xs text-slate-600">·</span>
        <span className="badge badge-blue text-[10px]">{levelLabel}</span>
      </div>

      <div className="flex-1 h-1.5 rounded-full overflow-hidden" style={{ background: '#1e293b' }}>
        <motion.div
          className="h-full rounded-full"
          style={{ background: 'linear-gradient(90deg,#2563eb,#7c3aed)' }}
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.8, ease: 'easeOut' }}
        />
      </div>

      <span className="text-[10px] text-slate-600 shrink-0">{Math.round(pct)}%</span>

      {badges.length > 0 && (
        <div className="flex items-center gap-1 shrink-0">
          <Star size={11} className="text-amber-500" />
          <span className="text-[10px] text-slate-500 max-w-[100px] truncate">
            {badges.slice(-3).join(' ')}
          </span>
        </div>
      )}
    </div>
  )
}
