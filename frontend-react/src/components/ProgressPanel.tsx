import React, { useEffect } from 'react'
import { motion } from 'framer-motion'
import { Zap, Award, TrendingUp, BookOpen, CheckCircle, AlertCircle, BarChart2 } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { useProgress } from '../context/ProgressContext'

export default function ProgressPanel() {
  const { user } = useAuth()
  const { progress, refresh } = useProgress()

  useEffect(() => { if (user) refresh(user.learner_id, true) }, [user])

  if (!progress) return (
    <div className="flex-1 flex items-center justify-center p-8 text-center">
      {user ? (
        <div className="flex flex-col items-center gap-3">
          <div className="skeleton w-12 h-12 rounded-full" />
          <div className="skeleton h-4 w-32" />
        </div>
      ) : (
        <div>
          <BarChart2 size={40} className="text-slate-700 mx-auto mb-3" />
          <p className="text-slate-500 text-sm">Sign in to track your progress.</p>
        </div>
      )}
    </div>
  )

  const { xp, level, badges, topics_seen, completed_projects, topic_progress, knowledge_gaps } = progress

  const STATS = [
    { icon: <Zap size={18} className="text-amber-400" />, value: xp.toLocaleString(), label: 'Total XP', gradient: 'rgba(245,158,11,0.12)', border: 'rgba(245,158,11,0.25)' },
    { icon: <TrendingUp size={18} className="text-blue-400" />, value: level.charAt(0).toUpperCase() + level.slice(1), label: 'Level', gradient: 'rgba(37,99,235,0.12)', border: 'rgba(37,99,235,0.25)' },
    { icon: <BookOpen size={18} className="text-purple-400" />, value: topics_seen.length, label: 'Topics', gradient: 'rgba(124,58,237,0.12)', border: 'rgba(124,58,237,0.25)' },
    { icon: <CheckCircle size={18} className="text-green-400" />, value: completed_projects.length, label: 'Courses Done', gradient: 'rgba(34,197,94,0.12)', border: 'rgba(34,197,94,0.25)' },
  ]

  return (
    <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-4 touch-scroll scrollbar-thin">

      {/* Stats grid */}
      <div className="grid grid-cols-2 gap-3">
        {STATS.map((s, i) => (
          <motion.div key={s.label} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.06 }}
            className="rounded-2xl p-4 border" style={{ background: s.gradient, borderColor: s.border }}>
            <div className="mb-2">{s.icon}</div>
            <div className="text-2xl font-bold text-slate-100" style={{ fontFamily: 'Sora' }}>{s.value}</div>
            <div className="text-xs text-slate-500 mt-0.5 font-medium">{s.label}</div>
          </motion.div>
        ))}
      </div>

      {/* Badges */}
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}
        className="card">
        <div className="flex items-center gap-2 mb-3">
          <Award size={16} className="text-amber-400" />
          <h3 className="font-bold text-sm text-slate-100" style={{ fontFamily: 'Sora' }}>Badges & Achievements</h3>
        </div>
        {badges.length > 0 ? (
          <div className="flex flex-wrap gap-2">
            {badges.map((b, i) => (
              <motion.span key={b} initial={{ scale: 0.8, opacity: 0 }} animate={{ scale: 1, opacity: 1 }}
                transition={{ delay: 0.15 + i * 0.04 }}
                className="badge badge-purple">{b}</motion.span>
            ))}
          </div>
        ) : (
          <div className="flex items-center gap-2 text-slate-600 text-sm">
            <Award size={14} />
            <span>Keep learning to earn your first badge!</span>
          </div>
        )}
      </motion.div>

      {/* Knowledge gaps */}
      {knowledge_gaps && knowledge_gaps.length > 0 && (
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}
          className="rounded-2xl p-4 border" style={{ background: 'rgba(239,68,68,0.06)', borderColor: 'rgba(239,68,68,0.2)' }}>
          <div className="flex items-center gap-2 mb-3">
            <AlertCircle size={16} className="text-red-400" />
            <h3 className="font-bold text-sm text-red-300" style={{ fontFamily: 'Sora' }}>Needs Review</h3>
          </div>
          <div className="flex flex-wrap gap-2">
            {knowledge_gaps.map(g => (
              <button key={g} onClick={() => window.dispatchEvent(new CustomEvent('sidebar-ask', { detail: `Help me understand ${g}` }))}
                className="badge badge-red cursor-pointer hover:opacity-80 transition-opacity">{g}</button>
            ))}
          </div>
        </motion.div>
      )}

      {/* Topic progress */}
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.25 }}
        className="card">
        <div className="flex items-center gap-2 mb-3">
          <TrendingUp size={16} className="text-blue-400" />
          <h3 className="font-bold text-sm text-slate-100" style={{ fontFamily: 'Sora' }}>Topic Progress</h3>
        </div>
        {Object.keys(topic_progress).length > 0 ? (
          <div className="flex flex-col gap-2">
            {Object.values(topic_progress).map((tp, i) => {
              const avg = tp.quiz_scores.length
                ? Math.round(tp.quiz_scores.reduce((a, b) => a + b, 0) / tp.quiz_scores.length) : null
              return (
                <motion.div key={tp.topic} initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.25 + i * 0.03 }}
                  className="flex items-center gap-3 py-2 border-b border-slate-800/60 last:border-0">
                  <div className={`w-2 h-2 rounded-full shrink-0 ${tp.weak ? 'bg-red-400' : 'bg-green-400'}`} />
                  <div className="flex-1 min-w-0">
                    <div className="text-sm text-slate-200 truncate">{tp.topic}</div>
                    <div className="text-xs text-slate-600">
                      {tp.lessons_completed} lessons · {tp.exercises_passed}/{tp.exercises_attempted} exercises
                      {avg !== null && ` · ${avg}% avg`}
                    </div>
                  </div>
                  {avg !== null && (
                    <div className="text-xs font-bold shrink-0"
                      style={{ color: avg >= 70 ? '#86efac' : avg >= 50 ? '#fcd34d' : '#fca5a5' }}>
                      {avg}%
                    </div>
                  )}
                </motion.div>
              )
            })}
          </div>
        ) : (
          <p className="text-sm text-slate-600">Start chatting to track your topics.</p>
        )}
      </motion.div>

      {/* Recent topics */}
      {topics_seen.length > 0 && (
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}
          className="card">
          <div className="flex items-center gap-2 mb-3">
            <BookOpen size={16} className="text-cyan-400" />
            <h3 className="font-bold text-sm text-slate-100" style={{ fontFamily: 'Sora' }}>Topics Covered</h3>
            <span className="badge badge-cyan ml-auto">{topics_seen.length}</span>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {topics_seen.slice(-20).reverse().map((t, i) => (
              <span key={t} className="px-2.5 py-1 text-xs rounded-full border border-slate-700/60 text-slate-400"
                style={{ background: '#1e293b' }}>
                {t}
              </span>
            ))}
          </div>
        </motion.div>
      )}
    </div>
  )
}
