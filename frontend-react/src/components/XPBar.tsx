import React from 'react'
import { motion } from 'framer-motion'
import { Zap, Star, Flame } from 'lucide-react'
import { useProgress } from '../context/ProgressContext'

const THRESHOLDS: Record<string, number> = { beginner: 200, intermediate: 500, advanced: 9999 }

export default function XPBar() {
  const { progress } = useProgress()

  if (!progress) return (
    <div className="h-8 shrink-0"
      style={{ background: 'rgba(6,13,28,0.9)', borderBottom: '1px solid rgba(13,71,161,0.15)' }} />
  )

  const { xp, level, badges } = progress
  const max = THRESHOLDS[level] || 200
  const pct = Math.min((xp / max) * 100, 100)
  const levelLabel = level.charAt(0).toUpperCase() + level.slice(1)

  return (
    <div className="flex items-center gap-3 px-4 py-1.5 shrink-0"
      style={{ background: 'rgba(6,13,28,0.9)', borderBottom: '1px solid rgba(13,71,161,0.15)' }}>

      {/* XP */}
      <div className="flex items-center gap-1.5 shrink-0">
        <Zap size={12} style={{ color: '#E0A300' }} />
        <span className="text-xs font-bold" style={{ color: '#E0A300' }}>
          {xp.toLocaleString()} XP
        </span>
        <span className="text-slate-600 text-xs">·</span>
        <span className="badge badge-blue text-[10px]">{levelLabel}</span>
      </div>

      {/* Progress bar */}
      <div className="flex-1 h-1.5 rounded-full overflow-hidden" style={{ background: 'rgba(13,71,161,0.2)' }}>
        <motion.div className="h-full rounded-full"
          style={{ background: 'linear-gradient(90deg,#0D47A1,#E0A300)' }}
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.8, ease: 'easeOut' }}
        />
      </div>

      <span className="text-[10px] shrink-0" style={{ color: '#4d6080' }}>{Math.round(pct)}%</span>

      {/* Badges */}
      {badges.length > 0 && (
        <div className="flex items-center gap-1 shrink-0">
          <Star size={11} style={{ color: '#E0A300' }} />
          <span className="text-[10px] max-w-[90px] truncate" style={{ color: '#4d6080' }}>
            {badges.slice(-3).join(' ')}
          </span>
        </div>
      )}
    </div>
  )
}
