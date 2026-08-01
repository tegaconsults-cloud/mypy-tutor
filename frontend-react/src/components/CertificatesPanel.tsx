import React, { useState } from 'react'
import { motion } from 'framer-motion'
import { Award, CheckCircle, Lock, ExternalLink } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { useProgress } from '../context/ProgressContext'
import { API_BASE } from '../api'

const CERT_TRACKS = {
  basic: {
    courses: ['python-fundamentals','python-strings','python-collections','python-control-flow'],
    label: 'Basic Certificate', fee: '₦30,000', icon: '🎓',
    desc: 'Foundational Python — syntax, variables, data structures, loops, functions.',
    gradient: 'linear-gradient(135deg,rgba(13,71,161,0.2),rgba(6,13,28,0.9))',
    border: 'rgba(13,71,161,0.5)', accent: '#93c5fd', badgeBg: 'rgba(13,71,161,0.2)',
  },
  advanced: {
    courses: ['python-fundamentals','python-strings','python-collections','python-control-flow','python-functions-advanced','python-oop','python-modules-stdlib'],
    label: 'Advanced Certificate', fee: '₦60,000', icon: '🏆',
    desc: 'OOP, algorithms, REST APIs, design patterns, real projects.',
    gradient: 'linear-gradient(135deg,rgba(139,92,246,0.18),rgba(6,13,28,0.9))',
    border: 'rgba(139,92,246,0.5)', accent: '#c4b5fd', badgeBg: 'rgba(139,92,246,0.2)',
  },
  executive: {
    courses: ['python-fundamentals','python-strings','python-collections','python-control-flow','python-functions-advanced','python-oop','python-modules-stdlib','python-dsa','numpy-mastery','pandas-mastery','data-science-python','machine-learning'],
    label: 'Executive Masters', fee: '₦100,000', icon: '👑',
    desc: 'ML, AI engineering, data science, NumPy, Pandas, prompt engineering.',
    gradient: 'linear-gradient(135deg,rgba(224,163,0,0.2),rgba(6,13,28,0.9))',
    border: 'rgba(224,163,0,0.5)', accent: '#E0A300', badgeBg: 'rgba(224,163,0,0.15)',
  },
}

export default function CertificatesPanel() {
  const { user } = useAuth()
  const { progress } = useProgress()
  const [name, setName] = useState(user?.name || '')

  const completed = new Set(progress?.completed_projects || [])
  const learnerId = user?.learner_id || 'default'

  const preview = (level: string) => {
    const certName = name.trim() || 'Learner'
    const url = `${API_BASE}/certificate/${level}?name=${encodeURIComponent(certName)}&learner_id=${encodeURIComponent(learnerId)}`
    window.open(url, '_blank', 'width=1000,height=720,noopener,noreferrer')
  }

  return (
    <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-5 touch-scroll scrollbar-thin">

      {/* Issuer info */}
      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
        className="rounded-2xl p-4 border"
        style={{ background: 'rgba(13,71,161,0.08)', borderColor: 'rgba(13,71,161,0.25)' }}>
        <div className="flex items-start gap-3">
          <div className="w-10 h-10 rounded-xl flex items-center justify-center text-xl shrink-0"
            style={{ background: 'rgba(13,71,161,0.2)' }}>🏛️</div>
          <div>
            <div className="text-sm font-semibold text-white mb-0.5">Teamsamikoko Global Academy</div>
            <div className="text-xs" style={{ color: '#4d6080' }}>Reg No: 3508656 · Est. 2021</div>
            <div className="text-xs mt-1" style={{ color: '#94a3b8' }}>
              Certificates are industry-recognised with QR verification and a unique Certificate ID.
            </div>
          </div>
        </div>
      </motion.div>

      {/* Name input */}
      <div>
        <label className="text-xs font-bold uppercase tracking-widest block mb-2" style={{ color: '#4d6080' }}>
          Your full name for the certificate
        </label>
        <input value={name} onChange={e => setName(e.target.value)}
          placeholder="e.g. Adaora Chukwuemeka" maxLength={80} className="h-11" />
      </div>

      {/* Certificate cards */}
      <div className="grid gap-4">
        {(Object.entries(CERT_TRACKS) as [keyof typeof CERT_TRACKS, typeof CERT_TRACKS['basic']][]).map(([level, track], i) => {
          const done   = track.courses.filter(c => completed.has(c)).length
          const total  = track.courses.length
          const pct    = Math.round((done / total) * 100)
          const isReady= done === total

          return (
            <motion.div key={level} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.08 }}
              className="rounded-3xl p-5 border relative overflow-hidden"
              style={{ background: track.gradient, borderColor: track.border }}>

              {/* Background decoration */}
              <div className="absolute top-0 right-0 text-8xl opacity-5 pointer-events-none select-none -mt-2 -mr-2">
                {track.icon}
              </div>

              <div className="flex items-center justify-between mb-3">
                <span className="text-[10px] font-bold px-2.5 py-1 rounded-full"
                  style={{ background: track.badgeBg, color: track.accent, border: `1px solid ${track.border}` }}>
                  {track.icon} {track.label}
                </span>
                {isReady && (
                  <span className="badge badge-green flex items-center gap-1">
                    <CheckCircle size={10} /> Ready
                  </span>
                )}
              </div>

              <div className="text-sm mb-3" style={{ color: '#94a3b8', lineHeight: 1.6 }}>{track.desc}</div>

              <div className="text-xl font-bold mb-3" style={{ color: track.accent, fontFamily: 'Sora' }}>
                {track.fee}
              </div>

              {/* Progress */}
              <div className="mb-4">
                <div className="flex justify-between text-xs mb-1.5"
                  style={{ color: isReady ? '#86efac' : '#94a3b8' }}>
                  <span className="flex items-center gap-1">
                    {isReady ? <CheckCircle size={11} /> : <Lock size={11} />}
                    {isReady ? 'All courses completed!' : `${done}/${total} courses (${pct}%)`}
                  </span>
                  <span>{pct}%</span>
                </div>
                <div className="h-2 rounded-full overflow-hidden" style={{ background: 'rgba(6,13,28,0.5)' }}>
                  <motion.div className="h-full rounded-full" initial={{ width: 0 }} animate={{ width: `${pct}%` }}
                    transition={{ duration: 0.8, delay: 0.3 + i * 0.08 }}
                    style={{ background: isReady ? '#22c55e' : track.accent }} />
                </div>
              </div>

              {/* Actions */}
              <div className="flex gap-2">
                <button onClick={() => preview(level)}
                  className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl text-sm font-semibold transition-all duration-200 hover:opacity-90"
                  style={{ background: track.badgeBg, color: track.accent, border: `1px solid ${track.border}` }}>
                  <ExternalLink size={14} /> Preview Certificate
                </button>
                {isReady && (
                  <button onClick={() => preview(level)}
                    className="flex items-center gap-1.5 px-4 py-2.5 rounded-xl text-sm font-semibold text-white transition-all hover:opacity-90"
                    style={{ background: 'linear-gradient(135deg,#0D47A1,#E0A300)' }}>
                    Download
                  </button>
                )}
              </div>
            </motion.div>
          )
        })}
      </div>

      <div className="rounded-xl p-3 border text-xs flex items-start gap-2"
        style={{ background: '#0f1a2e', borderColor: 'rgba(13,71,161,0.2)', color: '#4d6080' }}>
        <span>💡</span>
        <span>Certificates open in a new tab. Use <strong className="text-slate-400">Print → Save as PDF</strong> to download.</span>
      </div>
    </div>
  )
}
