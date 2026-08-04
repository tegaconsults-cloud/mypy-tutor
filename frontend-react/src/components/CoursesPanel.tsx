import React, { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { BookOpen, Play, CheckCircle, Lock, Clock, Layers, ArrowRight, Zap, ExternalLink } from 'lucide-react'
import { getCatalog, getLearnerCourses, startCourse } from '../api'
import { useAuth } from '../context/AuthContext'
import { useProgress } from '../context/ProgressContext'

const CAT_ORDER = ['Python Basics','Intermediate Python','Advanced Python','Data Science','Machine Learning','AI & Prompting']
const CAT_ICONS: Record<string, string> = {
  'Python Basics':      '🐍', 'Intermediate Python': '⚡',
  'Advanced Python':    '🔥', 'Data Science':         '📊',
  'Machine Learning':   '🤖', 'AI & Prompting':       '✨',
}

// Map course names to their dedicated landing page routes
const COURSE_LANDING_PAGE: Record<string, string> = {
  'python-fundamentals':        '/courses/python-fundamentals',
  'python-strings':             '/courses/python-strings',
  'python-collections':         '/courses/python-collections',
  'python-control-flow':        '/courses/python-control-flow',
  'python-functions-advanced':  '/courses/python-functions-advanced',
  'python-oop':                 '/courses/python-oop',
  'python-modules-stdlib':      '/courses/python-modules-stdlib',
  'python-dsa':                 '/courses/python-dsa',
  'data-science-python':        '/courses/data-science-python',
  'python-databases':           '/courses/python-databases',
  'numpy-mastery':              '/courses/numpy-mastery',
  'pandas-mastery':             '/courses/pandas-mastery',
  'web-apis':                   '/courses/web-apis',
  'prompt-engineering':         '/courses/prompt-engineering',
  'ai-prompt-engineering':      '/courses/ai-prompt-engineering',
  'machine-learning':           '/courses/machine-learning',
}

interface Course {
  name: string; display_name: string; description: string
  level: string; total_steps: number; badge: string
  price_ngn: number; paystack_url: string
}

export default function CoursesPanel() {
  const { user } = useAuth()
  const { progress } = useProgress()
  const [catalog, setCatalog]   = useState<Record<string, Course[]>>({})
  const [accessMap, setAccessMap] = useState<Record<string, { unlocked: boolean; via: string }>>({})
  const [loading, setLoading]   = useState(true)
  const [starting, setStarting] = useState<string | null>(null)
  const [startError, setStartError] = useState<string>('')

  useEffect(() => {
    const load = async () => {
      const data = await getCatalog()
      if (!data) return
      const byCat: Record<string, Course[]> = {}
      for (const c of data.courses || []) {
        const cat = (c as Course & { category: string }).category
        if (!byCat[cat]) byCat[cat] = []
        byCat[cat].push(c as Course)
      }
      setCatalog(byCat)
      if (user) {
        const acc = await getLearnerCourses(user.learner_id)
        if (acc?.courses) {
          const map: Record<string, { unlocked: boolean; via: string }> = {}
          for (const c of acc.courses) map[(c as { name: string }).name] = c as { unlocked: boolean; via: string }
          setAccessMap(map)
        }
      }
      setLoading(false)
    }
    load()
  }, [user])

  const handleStart = async (courseName: string) => {
    if (!user) return
    setStarting(courseName)
    setStartError('')
    try {
      const data = await startCourse(user.learner_id, courseName)
      window.dispatchEvent(new CustomEvent('sidebar-ask', {
        detail: `### 📚 ${data.course} — Step ${data.step}/${data.total_steps}: ${data.title}\n\n${data.content}`
      }))
      window.dispatchEvent(new CustomEvent('switch-panel', { detail: 'chat' }))
    } catch (err: unknown) {
      if (err instanceof Error) {
        const msg = err.message || ''
        // Show user-friendly message — never expose internal server errors
        if (msg.toLowerCase().includes('upgrade') || msg.toLowerCase().includes('402')) {
          setStartError('Upgrade required to access this course.')
        } else if (msg.toLowerCase().includes('ai service') || msg.toLowerCase().includes('502') || msg.toLowerCase().includes('503')) {
          setStartError('Sir. Tega is warming up — please try again in a moment.')
        } else if (msg.toLowerCase().includes('sign in') || msg.toLowerCase().includes('401')) {
          setStartError('Please sign in to start this course.')
        } else {
          setStartError('Could not start course. Please try again.')
        }
        // Auto-clear error after 5 seconds
        setTimeout(() => setStartError(''), 5000)
      }
    } finally {
      setStarting(null)
    }
  }

  // Navigate to the course landing page in a new tab
  const handleLearnMore = (courseName: string) => {
    const page = COURSE_LANDING_PAGE[courseName]
    if (page) window.open(page, '_blank', 'noopener,noreferrer')
  }

  const completed = new Set(progress?.completed_projects || [])
  const LEVEL_BADGE: Record<string, { label: string; cls: string }> = {
    beginner:     { label: '🟢 Beginner',     cls: 'badge-green' },
    intermediate: { label: '🟡 Intermediate', cls: 'badge-gold' },
    advanced:     { label: '🔴 Advanced',     cls: 'badge-red' },
  }

  if (loading) return (
    <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-3">
      {[...Array(4)].map((_, i) => <div key={i} className="skeleton h-24 rounded-2xl" />)}
    </div>
  )

  return (
    <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-5 touch-scroll scrollbar-thin">

      {/* Inline error toast — replaces browser alert() */}
      {startError && (
        <div className="rounded-2xl px-4 py-3 flex items-center gap-3 shrink-0"
          style={{ background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.25)' }}>
          <span className="text-sm flex-1" style={{ color: '#fca5a5' }}>⚠️ {startError}</span>
          <button onClick={() => setStartError('')} className="text-sm shrink-0" style={{ color: '#4d6080' }}>✕</button>
        </div>
      )}
      {progress?.current_course && (
        <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }}
          className="rounded-2xl p-4 border"
          style={{ background: 'rgba(13,71,161,0.1)', borderColor: 'rgba(13,71,161,0.4)' }}>
          <div className="flex items-center justify-between gap-3 flex-wrap">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl flex items-center justify-center"
                style={{ background: 'rgba(13,71,161,0.2)' }}>
                <Play size={18} style={{ color: '#E0A300' }} />
              </div>
              <div>
                <div className="text-xs font-bold uppercase tracking-wide mb-0.5" style={{ color: '#E0A300' }}>Continue Learning</div>
                <div className="text-sm font-semibold text-white">
                  {progress.current_course.replace(/-/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                </div>
              </div>
            </div>
            <button onClick={() => handleStart(progress.current_course!)} className="btn btn-gold btn-sm">
              Continue <ArrowRight size={13} />
            </button>
          </div>
        </motion.div>
      )}

      {/* Category sections */}
      {CAT_ORDER.map((cat, ci) => {
        const items = catalog[cat]
        if (!items?.length) return null
        return (
          <motion.div key={cat} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: ci * 0.04 }}>
            <div className="flex items-center gap-2 mb-3">
              <span className="text-xl">{CAT_ICONS[cat] || '📚'}</span>
              <h3 className="font-bold text-sm text-white" style={{ fontFamily: 'Sora' }}>{cat}</h3>
              <div className="flex-1 h-px" style={{ background: 'rgba(13,71,161,0.2)' }} />
              <span className="badge badge-blue">{items.length}</span>
            </div>

            <div className="flex flex-col gap-3">
              {items.map((course, idx) => {
                const access     = accessMap[course.name]
                const isUnlocked = access?.unlocked
                const isDone     = completed.has(course.name)
                const isActive   = progress?.current_course === course.name
                const step       = isActive ? (progress?.current_course_step || 0) : (isDone ? course.total_steps : 0)
                const pct        = course.total_steps > 0 ? Math.round((step / course.total_steps) * 100) : 0
                const lb         = LEVEL_BADGE[course.level] || LEVEL_BADGE.beginner
                const hasPage    = Boolean(COURSE_LANDING_PAGE[course.name])

                return (
                  <motion.div key={course.name}
                    initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: ci * 0.04 + idx * 0.03 }}
                    className="card card-hover"
                    style={{ borderColor: isDone ? 'rgba(34,197,94,0.3)' : isActive ? 'rgba(13,71,161,0.5)' : undefined }}>
                    <div className="flex items-start gap-3">
                      {/* Course icon */}
                      <div className="w-11 h-11 rounded-2xl flex items-center justify-center text-xl shrink-0 mt-0.5"
                        style={{ background: isDone ? 'rgba(34,197,94,0.1)' : isUnlocked ? 'rgba(13,71,161,0.15)' : 'rgba(255,255,255,0.04)' }}>
                        {isDone ? '✅' : course.badge}
                      </div>

                      {/* Course info */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-start justify-between gap-2 flex-wrap">
                          <div>
                            <h4 className="font-semibold text-sm text-white flex items-center gap-2 flex-wrap">
                              {course.display_name}
                              {isActive && !isDone && <span className="badge badge-blue text-[9px]">▶ Active</span>}
                              {isDone && <span className="badge badge-green text-[9px]">Done</span>}
                            </h4>
                            <p className="text-xs mt-0.5 line-clamp-2" style={{ color: '#4d6080' }}>{course.description}</p>
                          </div>
                          <span className={`badge ${lb.cls} text-[9px] shrink-0`}>{lb.label}</span>
                        </div>

                        <div className="flex items-center gap-3 mt-2 text-xs" style={{ color: '#4d6080' }}>
                          <span className="flex items-center gap-1"><Layers size={10} />{course.total_steps} steps</span>
                          <span className="flex items-center gap-1"><Clock size={10} />{Math.ceil(course.total_steps * 5)} min</span>
                          <span className="flex items-center gap-1"><Zap size={10} style={{ color: '#E0A300' }} />{course.total_steps * 10} XP</span>
                        </div>

                        {/* Progress bar for active/done courses */}
                        {(isActive || isDone) && (
                          <div className="mt-2">
                            <div className="flex justify-between text-[10px] mb-1" style={{ color: '#4d6080' }}>
                              <span>Step {step}/{course.total_steps}</span>
                              <span>{pct}%</span>
                            </div>
                            <div className="h-1.5 rounded-full overflow-hidden" style={{ background: 'rgba(13,71,161,0.2)' }}>
                              <motion.div className="h-full rounded-full" initial={{ width: 0 }} animate={{ width: `${pct}%` }}
                                style={{ background: isDone ? '#22c55e' : 'linear-gradient(90deg,#0D47A1,#E0A300)' }} />
                            </div>
                          </div>
                        )}
                      </div>

                      {/* Action buttons */}
                      <div className="flex flex-col items-end gap-2 shrink-0 ml-1">
                        {isUnlocked ? (
                          <button onClick={() => handleStart(course.name)} disabled={starting === course.name}
                            className="btn btn-sm"
                            style={{ background: 'rgba(13,71,161,0.2)', color: '#93c5fd', border: '1px solid rgba(13,71,161,0.4)' }}>
                            {starting === course.name ? '…' : isDone ? '🔄 Redo' : isActive ? <><Play size={12} /> Continue</> : <><Play size={12} /> Start</>}
                          </button>
                        ) : (
                          <div className="flex flex-col items-end gap-1.5">
                            <div className="flex items-center gap-1" style={{ color: '#4d6080' }}>
                              <Lock size={11} />
                              <span className="text-xs font-bold text-white">₦{course.price_ngn.toLocaleString()}</span>
                            </div>
                            {/* Buy button → Paystack with course info */}
                            <a
                              href={`https://paystack.shop/pay/vt_re4d3h52?plan=${encodeURIComponent(course.name)}&amount=${course.price_ngn * 100}`}
                              target="_blank" rel="noopener noreferrer"
                              className="btn btn-gold btn-sm">
                              Buy
                            </a>
                            {/* Learn More → course landing page */}
                            {hasPage && (
                              <button
                                onClick={() => handleLearnMore(course.name)}
                                className="flex items-center gap-0.5 text-[10px] transition-colors"
                                style={{ color: '#4d6080' }}
                                onMouseEnter={e => (e.currentTarget.style.color = '#93c5fd')}
                                onMouseLeave={e => (e.currentTarget.style.color = '#4d6080')}>
                                Learn more <ExternalLink size={9} />
                              </button>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  </motion.div>
                )
              })}
            </div>
          </motion.div>
        )
      })}

      {/* No courses loaded */}
      {Object.keys(catalog).length === 0 && !loading && (
        <div className="flex-1 flex flex-col items-center justify-center py-16 gap-4">
          <BookOpen size={40} style={{ color: '#1e3a5f' }} />
          <p className="text-sm" style={{ color: '#4d6080' }}>Could not load course catalog. Please try refreshing.</p>
        </div>
      )}
    </div>
  )
}
