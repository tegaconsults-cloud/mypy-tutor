/**
 * AssignmentsPanel — surfacing the backend /assignments/* routes in the UI.
 * Lets users generate, submit, and get AI review on coding assignments.
 */
import React, { useEffect, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { motion, AnimatePresence } from 'framer-motion'
import {
  ClipboardList, Plus, Send, Star, RefreshCw,
  ChevronDown, ChevronUp, Clock, CheckCircle, Zap,
} from 'lucide-react'
import {
  generateAssignment, submitAssignment, reviewAssignment,
  getAssignments,
} from '../api'
import { useAuth } from '../context/AuthContext'

interface Assignment {
  id:          string
  title:       string
  description: string
  status:      'pending' | 'submitted' | 'reviewed'
  submission?: string
  feedback?:   string
  score?:      number
  created_at:  string
  submitted_at?: string
  reviewed_at?:  string
}

const TOPIC_SUGGESTIONS = [
  'Python Variables', 'Python Functions', 'Python OOP', 'Python Lists',
  'Python Decorators', 'Python Generators', 'Linear Regression', 'Decision Trees',
  'NumPy Arrays', 'Pandas DataFrames', 'REST APIs', 'DSA Intro',
]

const STATUS_COLORS: Record<string, { bg: string; text: string; label: string }> = {
  pending:  { bg: 'rgba(224,163,0,0.1)',    text: '#E0A300',  label: 'Pending' },
  submitted:{ bg: 'rgba(13,71,161,0.15)',   text: '#93c5fd',  label: 'Submitted' },
  reviewed: { bg: 'rgba(34,197,94,0.1)',    text: '#86efac',  label: 'Reviewed' },
}

export default function AssignmentsPanel() {
  const { user } = useAuth()
  const [assignments, setAssignments]       = useState<Assignment[]>([])
  const [loading, setLoading]               = useState(false)
  const [generating, setGenerating]         = useState(false)
  const [topic, setTopic]                   = useState('')
  const [error, setError]                   = useState('')
  const [expandedId, setExpandedId]         = useState<string | null>(null)
  const [submissionText, setSubmissionText] = useState<Record<string, string>>({})
  const [submitting, setSubmitting]         = useState<string | null>(null)
  const [reviewing, setReviewing]           = useState<string | null>(null)

  const learnerId = user?.learner_id || 'default'

  const loadAssignments = async () => {
    if (!user) return
    setLoading(true)
    try {
      const data = await getAssignments(learnerId)
      if (data?.assignments) setAssignments(data.assignments)
    } catch (_) {}
    finally { setLoading(false) }
  }

  useEffect(() => { loadAssignments() }, [user])

  const handleGenerate = async () => {
    if (!topic.trim() || !user) return
    setGenerating(true); setError('')
    try {
      const data = await generateAssignment(learnerId, topic.trim())
      // Prepend newly generated assignment
      setAssignments(prev => [{
        id:          data.assignment_id,
        title:       data.title,
        description: data.content,
        status:      'pending',
        created_at:  new Date().toISOString(),
      }, ...prev])
      setExpandedId(data.assignment_id)
      setTopic('')
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to generate'
      setError(msg.toLowerCase().includes('503') || msg.toLowerCase().includes('warming')
        ? 'Sir. Tega is warming up — please try again in a moment.'
        : 'Could not generate assignment. Try again.')
    } finally { setGenerating(false) }
  }

  const handleSubmit = async (assignmentId: string) => {
    const text = submissionText[assignmentId]?.trim()
    if (!text || !user) return
    setSubmitting(assignmentId)
    try {
      await submitAssignment(assignmentId, learnerId, text)
      setAssignments(prev => prev.map(a =>
        a.id === assignmentId ? { ...a, status: 'submitted', submission: text } : a
      ))
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Submission failed')
    } finally { setSubmitting(null) }
  }

  const handleReview = async (assignmentId: string) => {
    if (!user) return
    setReviewing(assignmentId)
    try {
      const data = await reviewAssignment(assignmentId, learnerId)
      setAssignments(prev => prev.map(a =>
        a.id === assignmentId ? { ...a, status: 'reviewed', feedback: data.feedback, score: data.score } : a
      ))
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Review failed')
    } finally { setReviewing(null) }
  }

  if (!user) return (
    <div className="flex-1 flex items-center justify-center p-8 text-center">
      <div>
        <ClipboardList size={40} className="mx-auto mb-3" style={{ color: '#4d6080' }} />
        <p className="text-sm" style={{ color: '#4d6080' }}>Sign in to access coding assignments.</p>
      </div>
    </div>
  )

  return (
    <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-4 touch-scroll scrollbar-thin">

      {/* Header */}
      <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }}
        className="rounded-2xl p-4 border"
        style={{ background: 'linear-gradient(135deg,rgba(139,92,246,0.12),rgba(6,13,28,0.9))', borderColor: 'rgba(139,92,246,0.4)' }}>
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-2xl flex items-center justify-center"
            style={{ background: 'rgba(139,92,246,0.2)' }}>
            <ClipboardList size={20} style={{ color: '#c4b5fd' }} />
          </div>
          <div>
            <h2 className="font-bold text-sm text-white" style={{ fontFamily: 'Sora' }}>Coding Assignments</h2>
            <p className="text-xs" style={{ color: '#4d6080' }}>AI-generated challenges · get expert feedback + score</p>
          </div>
          <button onClick={loadAssignments} disabled={loading}
            className="ml-auto btn btn-ghost btn-sm"
            style={{ color: '#4d6080' }}>
            <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
          </button>
        </div>
      </motion.div>

      {/* Generate new assignment */}
      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }}
        className="card flex flex-col gap-3">
        <div className="text-xs font-bold uppercase tracking-widest" style={{ color: '#4d6080' }}>
          Generate a new assignment
        </div>
        <div className="flex gap-2">
          <input value={topic} onChange={e => setTopic(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter') handleGenerate() }}
            placeholder="e.g. Python OOP, Linear Regression, NumPy Arrays…"
            className="flex-1 h-11"
            style={{ background: 'rgba(6,13,28,0.8)', borderColor: 'rgba(139,92,246,0.3)' }} />
          <button onClick={handleGenerate} disabled={generating || !topic.trim()}
            className="btn btn-primary h-11 px-4 flex items-center gap-1.5"
            style={{ background: 'linear-gradient(135deg,#6d28d9,#8b5cf6)' }}>
            {generating
              ? <div className="loading-dots scale-75"><span/><span/><span/></div>
              : <><Plus size={14} /> Generate</>}
          </button>
        </div>
        {/* Suggested topics */}
        <div className="flex flex-wrap gap-1.5">
          {TOPIC_SUGGESTIONS.map(t => (
            <button key={t} onClick={() => setTopic(t)}
              className="text-[10px] px-2.5 py-1 rounded-full transition-colors"
              style={{ background: 'rgba(139,92,246,0.08)', border: '1px solid rgba(139,92,246,0.2)', color: '#94a3b8' }}
              onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'rgba(139,92,246,0.18)'; (e.currentTarget as HTMLElement).style.color = '#c4b5fd' }}
              onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'rgba(139,92,246,0.08)'; (e.currentTarget as HTMLElement).style.color = '#94a3b8' }}>
              {t}
            </button>
          ))}
        </div>
      </motion.div>

      {/* Error */}
      {error && (
        <div className="rounded-xl px-4 py-3 flex items-center gap-3"
          style={{ background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.25)' }}>
          <span className="text-sm flex-1" style={{ color: '#fca5a5' }}>⚠️ {error}</span>
          <button onClick={() => setError('')} style={{ color: '#4d6080' }}>✕</button>
        </div>
      )}

      {/* Assignment list */}
      {loading && assignments.length === 0 && (
        <div className="flex flex-col gap-3">
          {[...Array(2)].map((_, i) => <div key={i} className="skeleton h-20 rounded-2xl" />)}
        </div>
      )}

      {!loading && assignments.length === 0 && (
        <div className="flex flex-col items-center justify-center py-16 gap-3">
          <ClipboardList size={40} style={{ color: '#1e3a5f' }} />
          <p className="text-sm" style={{ color: '#4d6080' }}>No assignments yet. Generate your first one above!</p>
        </div>
      )}

      <AnimatePresence initial={false}>
        {assignments.map((a, idx) => {
          const statusStyle = STATUS_COLORS[a.status] || STATUS_COLORS.pending
          const isExpanded  = expandedId === a.id

          return (
            <motion.div key={a.id} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
              transition={{ delay: idx * 0.04 }}
              className="card flex flex-col gap-0 overflow-hidden p-0"
              style={{ border: isExpanded ? '1px solid rgba(139,92,246,0.35)' : '1px solid rgba(13,71,161,0.2)' }}>

              {/* Assignment header row */}
              <button
                onClick={() => setExpandedId(isExpanded ? null : a.id)}
                className="flex items-center gap-3 p-4 text-left w-full"
                style={{ background: 'transparent' }}>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-sm font-semibold text-white truncate">{a.title}</span>
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded-full shrink-0"
                      style={{ background: statusStyle.bg, color: statusStyle.text }}>
                      {statusStyle.label}
                    </span>
                    {a.score != null && (
                      <span className="flex items-center gap-0.5 text-[10px] font-bold"
                        style={{ color: a.score >= 70 ? '#86efac' : a.score >= 50 ? '#E0A300' : '#fca5a5' }}>
                        <Star size={9} /> {a.score}/100
                      </span>
                    )}
                  </div>
                  <div className="text-[10px] mt-0.5 flex items-center gap-1" style={{ color: '#4d6080' }}>
                    <Clock size={9} />
                    {new Date(a.created_at).toLocaleDateString('en-NG', { day: 'numeric', month: 'short', year: 'numeric' })}
                  </div>
                </div>
                {isExpanded ? <ChevronUp size={14} style={{ color: '#4d6080', flexShrink: 0 }} /> : <ChevronDown size={14} style={{ color: '#4d6080', flexShrink: 0 }} />}
              </button>

              {/* Expanded content */}
              <AnimatePresence>
                {isExpanded && (
                  <motion.div key="body" initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }} transition={{ duration: 0.2 }}
                    className="px-4 pb-4 flex flex-col gap-3 overflow-hidden"
                    style={{ borderTop: '1px solid rgba(13,71,161,0.15)' }}>

                    {/* Assignment description */}
                    <div className="pt-3 text-xs leading-relaxed prose prose-invert prose-xs max-w-none"
                      style={{ color: '#94a3b8' }}>
                      <ReactMarkdown>{a.description}</ReactMarkdown>
                    </div>

                    {/* Submission area */}
                    {a.status === 'pending' && (
                      <div className="flex flex-col gap-2">
                        <label className="text-[10px] font-bold uppercase tracking-widest"
                          style={{ color: '#4d6080' }}>Your Solution</label>
                        <textarea
                          value={submissionText[a.id] || ''}
                          onChange={e => setSubmissionText(prev => ({ ...prev, [a.id]: e.target.value }))}
                          placeholder="# Write your Python solution here…"
                          rows={6}
                          className="w-full rounded-xl text-sm resize-y"
                          style={{
                            background: '#030810', fontFamily: 'JetBrains Mono, monospace',
                            fontSize: '0.82rem', padding: '10px 12px',
                            border: '1px solid rgba(139,92,246,0.3)', color: '#e2e8f0',
                            minHeight: 120, outline: 'none',
                          }} />
                        <button
                          onClick={() => handleSubmit(a.id)}
                          disabled={!submissionText[a.id]?.trim() || submitting === a.id}
                          className="btn btn-primary flex items-center justify-center gap-2 w-full"
                          style={{ background: 'linear-gradient(135deg,#6d28d9,#8b5cf6)' }}>
                          {submitting === a.id
                            ? <div className="loading-dots scale-75"><span/><span/><span/></div>
                            : <><Send size={13} /> Submit Solution</>}
                        </button>
                      </div>
                    )}

                    {/* Submitted — show submission + request review */}
                    {a.status === 'submitted' && (
                      <div className="flex flex-col gap-2">
                        <div className="text-[10px] font-bold uppercase tracking-widest" style={{ color: '#4d6080' }}>
                          Your Submission
                        </div>
                        <pre className="text-xs rounded-xl p-3 overflow-x-auto"
                          style={{ background: '#030810', border: '1px solid rgba(13,71,161,0.2)', color: '#93c5fd', fontFamily: 'JetBrains Mono,monospace', lineHeight: 1.6 }}>
                          {a.submission}
                        </pre>
                        <button onClick={() => handleReview(a.id)} disabled={reviewing === a.id}
                          className="btn btn-sm flex items-center justify-center gap-2 w-full"
                          style={{ background: 'rgba(139,92,246,0.15)', color: '#c4b5fd', border: '1px solid rgba(139,92,246,0.3)' }}>
                          {reviewing === a.id
                            ? <div className="loading-dots scale-75"><span/><span/><span/></div>
                            : <><Zap size={12} /> Get AI Review & Score</>}
                        </button>
                      </div>
                    )}

                    {/* Reviewed — show feedback + score */}
                    {a.status === 'reviewed' && a.feedback && (
                      <div className="flex flex-col gap-3">
                        <div className="flex items-center gap-2">
                          <CheckCircle size={14} style={{ color: '#86efac' }} />
                          <span className="text-xs font-bold" style={{ color: '#86efac' }}>AI Feedback</span>
                          {a.score != null && (
                            <span className="ml-auto text-sm font-bold"
                              style={{ color: a.score >= 70 ? '#86efac' : a.score >= 50 ? '#E0A300' : '#fca5a5' }}>
                              Score: {a.score}/100
                            </span>
                          )}
                        </div>
                        <div className="text-xs leading-relaxed prose prose-invert prose-xs max-w-none rounded-xl p-3"
                          style={{ background: 'rgba(34,197,94,0.05)', border: '1px solid rgba(34,197,94,0.15)', color: '#94a3b8' }}>
                          <ReactMarkdown>{a.feedback}</ReactMarkdown>
                        </div>
                        {/* Ask Sir. Tega for explanation */}
                        <button
                          onClick={() => {
                            window.dispatchEvent(new CustomEvent('sidebar-ask', {
                              detail: `I completed an assignment on "${a.title}" and got ${a.score}/100. Explain the key concepts and where I can improve.`
                            }))
                            window.dispatchEvent(new CustomEvent('switch-panel', { detail: 'chat' }))
                          }}
                          className="btn btn-sm flex items-center gap-1.5"
                          style={{ background: 'rgba(224,163,0,0.12)', color: '#E0A300', border: '1px solid rgba(224,163,0,0.3)' }}>
                          Ask Sir. Tega to explain →
                        </button>
                      </div>
                    )}
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>
          )
        })}
      </AnimatePresence>
    </div>
  )
}
