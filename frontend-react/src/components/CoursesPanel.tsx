import React, { useEffect, useState } from 'react'
import { getCatalog, getLearnerCourses, startCourse } from '../api'
import { useAuth } from '../context/AuthContext'
import { useProgress } from '../context/ProgressContext'

const CAT_ORDER = ['Python Basics','Intermediate Python','Advanced Python','Data Science','Machine Learning','AI & Prompting']

export default function CoursesPanel() {
  const { user } = useAuth()
  const { progress } = useProgress()
  const [catalog, setCatalog] = useState<Record<string, unknown[]>>({})
  const [accessMap, setAccessMap] = useState<Record<string, { unlocked: boolean; via: string }>>({})
  const [loading, setLoading] = useState(true)
  const [starting, setStarting] = useState<string | null>(null)

  useEffect(() => {
    const load = async () => {
      const data = await getCatalog()
      if (!data) return
      const byCat: Record<string, unknown[]> = {}
      for (const c of data.courses || []) {
        const cat = (c as { category: string }).category
        if (!byCat[cat]) byCat[cat] = []
        byCat[cat].push(c)
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
    try {
      const data = await startCourse(user.learner_id, courseName)
      window.dispatchEvent(new CustomEvent('sidebar-ask', { detail: `### 📚 ${data.course} — Step ${data.step}/${data.total_steps}: ${data.title}\n\n${data.content}` }))
      window.dispatchEvent(new CustomEvent('switch-panel', { detail: 'chat' }))
    } catch (err: unknown) {
      if (err instanceof Error) alert(err.message)
    } finally { setStarting(null) }
  }

  const completed = new Set(progress?.completed_projects || [])

  if (loading) return (
    <div style={{ padding: 20, color: '#718096' }}>Loading courses…</div>
  )

  return (
    <div style={{ overflowY: 'auto', padding: 16, display: 'flex', flexDirection: 'column', gap: 14, WebkitOverflowScrolling: 'touch' }}>
      <h3 style={{ color: '#90cdf4', fontSize: '.97rem' }}>📚 Learning Paths</h3>

      {/* Active course bar */}
      {progress?.current_course && (
        <div style={{ background: '#1a365d', border: '1px solid #2c5282', borderRadius: 10, padding: '12px 14px', display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
          <span style={{ flex: 1, fontSize: '.86rem', color: '#90cdf4', fontWeight: 600 }}>
            {progress.current_course.replace(/-/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
          </span>
          <span style={{ fontSize: '.76rem', color: '#718096' }}>Step {progress.current_course_step}</span>
          <button onClick={() => handleStart(progress.current_course!)} className="btn btn-primary btn-sm">Continue →</button>
        </div>
      )}

      {CAT_ORDER.map(cat => {
        const items = catalog[cat]
        if (!items?.length) return null
        return (
          <div key={cat}>
            <div style={{ fontSize: '.65rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '.1em', color: '#4a5568', marginBottom: 6, paddingBottom: 4, borderBottom: '1px solid #2d3748' }}>{cat}</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginTop: 8 }}>
              {items.map((c: unknown) => {
                const course = c as { name: string; display_name: string; description: string; level: string; total_steps: number; badge: string; price_ngn: number; paystack_url: string }
                const access = accessMap[course.name]
                const isUnlocked = access?.unlocked
                const isDone = completed.has(course.name)
                const isActive = progress?.current_course === course.name
                const step = isActive ? (progress?.current_course_step || 0) : (isDone ? course.total_steps : 0)
                const pct = course.total_steps > 0 ? Math.round((step / course.total_steps) * 100) : 0
                const levelColors: Record<string, { bg: string; color: string }> = {
                  beginner: { bg: 'rgba(39,103,73,.15)', color: '#68d391' },
                  intermediate: { bg: 'rgba(116,66,16,.15)', color: '#f6ad55' },
                  advanced: { bg: 'rgba(116,42,42,.12)', color: '#fc8181' },
                }
                const lc = levelColors[course.level] || levelColors.beginner

                return (
                  <div key={course.name} style={{ background: '#1a202c', border: `1px solid ${isUnlocked ? '#276749' : '#2d3748'}`, borderRadius: 12, padding: 14, display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12, flexWrap: 'wrap' }}>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <h4 style={{ fontSize: '.9rem', color: '#e2e8f0', marginBottom: 4, display: 'flex', alignItems: 'center', gap: 7, flexWrap: 'wrap' }}>
                        <span>{course.badge}</span>
                        {course.display_name}
                        {isDone && <span style={{ background: '#276749', color: '#68d391', borderRadius: 999, padding: '2px 9px', fontSize: '.7rem', fontWeight: 700 }}>✅ Done</span>}
                        {isActive && !isDone && <span style={{ background: '#1a365d', color: '#90cdf4', borderRadius: 999, padding: '2px 9px', fontSize: '.7rem', fontWeight: 700 }}>▶ Active</span>}
                      </h4>
                      <p style={{ fontSize: '.78rem', color: '#718096', lineHeight: 1.4 }}>{course.description}</p>
                      <p style={{ marginTop: 3, fontSize: '.73rem', color: '#4a5568' }}>{course.total_steps} steps</p>
                      {(isActive || isDone) && (
                        <div style={{ marginTop: 6 }}>
                          <div style={{ height: 4, background: '#2d3748', borderRadius: 99, overflow: 'hidden' }}>
                            <div style={{ height: '100%', width: `${pct}%`, background: isDone ? '#68d391' : '#3182ce', borderRadius: 99, transition: 'width .4s' }} />
                          </div>
                          <div style={{ fontSize: '.68rem', color: '#4a5568', marginTop: 2 }}>Step {step}/{course.total_steps} · {pct}%</div>
                        </div>
                      )}
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 6, flexShrink: 0 }}>
                      <span style={{ fontSize: '.65rem', fontWeight: 700, textTransform: 'uppercase', padding: '2px 8px', borderRadius: 999, ...lc }}>{course.level}</span>
                      {isUnlocked ? (
                        <>
                          <span style={{ fontSize: '.7rem', fontWeight: 700, color: '#68d391' }}>{access.via === 'tier' ? '✅ Bundle' : '✅ Purchased'}</span>
                          <button onClick={() => handleStart(course.name)} disabled={starting === course.name} className="btn btn-sm" style={{ background: '#2c5282', color: '#90cdf4', border: '1px solid #4299e1' }}>
                            {starting === course.name ? '…' : isDone ? '🔄 Redo' : isActive ? '▶ Continue' : '▶ Start'}
                          </button>
                        </>
                      ) : (
                        <>
                          <span style={{ fontSize: '.75rem', fontWeight: 700, color: '#e2e8f0' }}>₦{course.price_ngn.toLocaleString()}</span>
                          <a href={course.paystack_url} target="_blank" rel="noopener" className="btn btn-sm btn-primary">💳 Buy</a>
                        </>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )
      })}
    </div>
  )
}
