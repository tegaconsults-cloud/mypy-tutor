/**
 * CoursePlayer — dedicated, focused course study mode.
 *
 * Features:
 * - Full course step navigation with auto-advance
 * - Sir. Tega stays ON the current course topic even for off-topic questions
 * - Voice/Text-to-Speech audio lecture for each lesson
 * - Progress bar + step counter
 * - No distractions — full-panel takeover
 * - "Ask Sir. Tega" chat stays within course context
 */
import React, { useCallback, useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism'
import { motion, AnimatePresence } from 'framer-motion'
import {
  X, ChevronRight, ChevronLeft, Volume2, VolumeX, Send,
  CheckCircle, BookOpen, Zap, Trophy, RotateCcw, Loader2,
} from 'lucide-react'
// CoursePlayer uses direct fetch() calls to API_BASE for course steps
import { useAuth } from '../context/AuthContext'
import { useProgress } from '../context/ProgressContext'

interface CourseStep {
  step: number
  title: string
  content: string
  total_steps: number
  course: string
  completed?: boolean
  xp_gained?: number
  badge?: string
}

interface Props {
  courseName: string
  courseTitle: string
  totalSteps: number
  onClose: () => void
}

// Cache best voice — getVoices() is expensive, call once after voices load
let _cachedVoice: SpeechSynthesisVoice | null | undefined = undefined

function getBestVoice(): SpeechSynthesisVoice | null {
  if (_cachedVoice !== undefined) return _cachedVoice
  const voices = speechSynthesis.getVoices()
  if (!voices.length) { _cachedVoice = null; return null }
  const preferred = [
    voices.find(v => v.name.toLowerCase().includes('nigeria')),
    voices.find(v => v.lang === 'en-NG'),
    voices.find(v => v.lang === 'en-GB' && v.name.toLowerCase().includes('male')),
    voices.find(v => v.lang === 'en-GB'),
    voices.find(v => v.lang === 'en-US' && v.name.toLowerCase().includes('male')),
    voices.find(v => v.lang.startsWith('en')),
  ]
  _cachedVoice = preferred.find(Boolean) ?? null
  return _cachedVoice
}

// Invalidate cache when voices list changes (async load in some browsers)
if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
  speechSynthesis.onvoiceschanged = () => { _cachedVoice = undefined }
}

function speak(text: string, onEnd?: () => void) {
  if (!('speechSynthesis' in window)) return
  speechSynthesis.cancel()
  // Strip markdown for clean speech
  const clean = text
    .replace(/```[\s\S]*?```/g, 'Here is a code example.')
    .replace(/`[^`]+`/g, (m) => m.replace(/`/g, ''))
    .replace(/#{1,6}\s/g, '')
    .replace(/\*\*([^*]+)\*\*/g, '$1')
    .replace(/\*([^*]+)\*/g, '$1')
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
    .replace(/>\s/g, '')
    .replace(/[-•]\s/g, '')
    .slice(0, 2000)  // cap for performance

  const utter = new SpeechSynthesisUtterance(clean)
  utter.rate  = 0.92
  utter.pitch = 1.0
  utter.volume = 1.0
  const voice = getBestVoice()
  if (voice) utter.voice = voice
  if (onEnd) utter.onend = onEnd
  speechSynthesis.speak(utter)
}

function stopSpeech() {
  if ('speechSynthesis' in window) speechSynthesis.cancel()
}

// Chat message type for in-course Q&A
interface ChatMsg { role: 'user' | 'assistant'; content: string }

export default function CoursePlayer({ courseName, courseTitle, totalSteps, onClose }: Props) {
  const { user } = useAuth()
  const { refresh } = useProgress()
  const learnerId = user?.learner_id || 'default'

  // Course step state
  const [currentStep, setCurrentStep] = useState<CourseStep | null>(null)
  const [stepLoading, setStepLoading]  = useState(true)
  const [stepError,   setStepError]    = useState('')
  const [completed,   setCompleted]    = useState(false)
  const [finalXP,     setFinalXP]      = useState(0)

  // Audio state
  const [audioOn,    setAudioOn]    = useState(false)
  const [isSpeaking, setIsSpeaking] = useState(false)

  // In-course Q&A chat
  const [chatMsgs,  setChatMsgs]  = useState<ChatMsg[]>([])
  const [chatInput, setChatInput] = useState('')
  const [chatLoading, setChatLoading] = useState(false)
  const [showChat,  setShowChat]  = useState(false)

  const API_BASE = 'https://mypytutor.onrender.com'
  const chatEndRef = useRef<HTMLDivElement>(null)
  const inputRef   = useRef<HTMLTextAreaElement>(null)

  // ── Load first step on mount ──────────────────────────────────────────
  useEffect(() => {
    loadStep('start')
    return () => stopSpeech()
  }, [])  // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chatMsgs])

  const loadStep = async (mode: 'start' | 'next') => {
    setStepLoading(true); setStepError('')
    try {
      const token = localStorage.getItem('mypy_tutor_session') || ''
      const headers: Record<string, string> = { 'Content-Type': 'application/json' }
      if (token) headers['Authorization'] = `Bearer ${token}`

      let data: CourseStep
      if (mode === 'start') {
        const r = await fetch(
          `${API_BASE}/course/start?learner_id=${learnerId}&course_name=${encodeURIComponent(courseName)}`,
          { method: 'POST', headers },
        )
        data = await r.json()
        if (!r.ok) throw new Error(data as unknown as string)
      } else {
        const r = await fetch(
          `${API_BASE}/course/next?learner_id=${learnerId}`,
          { method: 'POST', headers },
        )
        data = await r.json()
        if (!r.ok) throw new Error(data as unknown as string)
      }

      if (data.completed) {
        setCompleted(true)
        setFinalXP(data.xp_gained || 0)
        if (user) refresh(user.learner_id, true)
        return
      }

      setCurrentStep(data)
      setChatMsgs([])  // Clear chat on new step

      // Auto-speak if audio is on
      if (audioOn && data.content) {
        setIsSpeaking(true)
        speak(data.content, () => setIsSpeaking(false))
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed'
      setStepError(msg.toLowerCase().includes('warming')
        ? 'Sir. Tega is warming up — please try again in a moment.'
        : 'Could not load lesson. Please try again.')
    } finally {
      setStepLoading(false)
    }
  }

  const handleNext = () => loadStep('next')

  const toggleAudio = () => {
    if (isSpeaking) {
      stopSpeech()
      setIsSpeaking(false)
      setAudioOn(false)
    } else {
      setAudioOn(true)
      if (currentStep?.content) {
        setIsSpeaking(true)
        speak(currentStep.content, () => setIsSpeaking(false))
      }
    }
  }

  // ── Course-focused Q&A chat ──────────────────────────────────────────
  // Sir. Tega always brings off-topic questions back to the current course
  const sendCourseChat = useCallback(async () => {
    const text = chatInput.trim()
    if (!text || chatLoading) return
    setChatInput('')
    setChatLoading(true)

    const userMsg: ChatMsg = { role: 'user', content: text }
    setChatMsgs(prev => [...prev, userMsg])

    try {
      const token = localStorage.getItem('mypy_tutor_session') || ''
      const headers: Record<string, string> = { 'Content-Type': 'application/json' }
      if (token) headers['Authorization'] = `Bearer ${token}`

      // Build a course-focused message: wrap user question with course context
      // so Sir. Tega stays on-topic. If truly off-topic, he redirects politely.
      const courseContext = currentStep
        ? `[COURSE CONTEXT: The learner is currently studying "${courseTitle}" — specifically Step ${currentStep.step}/${currentStep.total_steps}: "${currentStep.title}". Keep your answer relevant to this course and lesson. If the question is unrelated, give a brief answer then redirect back to the lesson.]`
        : `[COURSE CONTEXT: The learner is studying "${courseTitle}". Stay focused on this course.]`

      const contextualMessage = `${courseContext}\n\nLearner asks: ${text}`

      const r = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          message: contextualMessage,
          history: chatMsgs.slice(-6).map(m => ({ role: m.role, content: m.content })),
          learner_id: learnerId,
          level: localStorage.getItem('mypy_tutor_level') || 'beginner',
        }),
      })
      const data = await r.json()
      const reply = data.content || 'I could not process that. Please try again.'
      setChatMsgs(prev => [...prev, { role: 'assistant', content: reply }])

      // Speak the reply if audio is on
      if (audioOn) {
        setIsSpeaking(true)
        speak(reply, () => setIsSpeaking(false))
      }
    } catch (_) {
      setChatMsgs(prev => [...prev, { role: 'assistant', content: 'Connection error. Please try again.' }])
    } finally {
      setChatLoading(false)
    }
  }, [chatInput, chatLoading, chatMsgs, currentStep, courseTitle, learnerId, audioOn])

  const pct = currentStep
    ? Math.round(((currentStep.step - 1) / currentStep.total_steps) * 100)
    : 0

  // ── Completion screen ────────────────────────────────────────────────
  if (completed) return (
    <div className="flex-1 flex flex-col items-center justify-center p-8 text-center gap-6"
      style={{ background: '#060d1c' }}>
      <motion.div initial={{ scale: 0.5, opacity: 0 }} animate={{ scale: 1, opacity: 1 }}
        transition={{ type: 'spring', stiffness: 300, damping: 20 }}>
        <div className="text-6xl mb-4">🎉</div>
        <h2 className="text-2xl font-bold text-white mb-2" style={{ fontFamily: 'Sora' }}>
          Course Complete!
        </h2>
        <p className="text-base mb-1" style={{ color: '#94a3b8' }}>
          You've completed <strong className="text-white">{courseTitle}</strong>
        </p>
        {finalXP > 0 && (
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full mt-2"
            style={{ background: 'rgba(224,163,0,0.15)', border: '1px solid rgba(224,163,0,0.3)', color: '#E0A300' }}>
            <Zap size={14} /> +{finalXP} XP earned
          </div>
        )}
      </motion.div>
      <div className="flex gap-3 flex-wrap justify-center">
        <button onClick={onClose}
          className="btn btn-primary"
          style={{ background: 'linear-gradient(135deg,#0D47A1,#E0A300)' }}>
          <Trophy size={14} /> View Certificates
        </button>
        <button onClick={() => { setCompleted(false); loadStep('start') }}
          className="btn btn-secondary flex items-center gap-2">
          <RotateCcw size={13} /> Restart Course
        </button>
        <button onClick={onClose} className="btn btn-ghost">Back to Courses</button>
      </div>
    </div>
  )

  return (
    <div className="flex-1 flex flex-col overflow-hidden" style={{ background: '#060d1c' }}>

      {/* ── Course header bar ─────────────────────────────────────── */}
      <div className="shrink-0 px-4 py-3 flex items-center gap-3"
        style={{ background: 'rgba(6,13,28,0.97)', borderBottom: '1px solid rgba(13,71,161,0.25)', backdropFilter: 'blur(20px)' }}>

        {/* Close */}
        <button onClick={() => { stopSpeech(); onClose() }}
          className="btn btn-ghost btn-sm w-8 h-8 p-0 rounded-xl shrink-0">
          <X size={15} />
        </button>

        {/* Course title + step */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <BookOpen size={12} style={{ color: '#E0A300' }} />
            <span className="text-xs font-bold" style={{ color: '#E0A300' }}>{courseTitle}</span>
            {currentStep && (
              <span className="text-[10px] font-medium" style={{ color: '#4d6080' }}>
                Step {currentStep.step} of {currentStep.total_steps}
              </span>
            )}
          </div>
          {/* Progress bar */}
          <div className="mt-1.5 h-1 rounded-full overflow-hidden" style={{ background: 'rgba(13,71,161,0.2)' }}>
            <motion.div className="h-full rounded-full"
              style={{ background: 'linear-gradient(90deg,#0D47A1,#E0A300)' }}
              animate={{ width: `${pct}%` }}
              transition={{ duration: 0.5 }} />
          </div>
        </div>

        {/* Audio toggle */}
        <button onClick={toggleAudio}
          className="btn btn-ghost btn-sm w-8 h-8 p-0 rounded-xl shrink-0"
          title={isSpeaking ? 'Stop audio' : 'Read lesson aloud'}
          style={{ color: isSpeaking ? '#E0A300' : '#4d6080' }}>
          {isSpeaking ? <Volume2 size={15} /> : <VolumeX size={15} />}
        </button>

        {/* Ask question toggle */}
        <button onClick={() => setShowChat(c => !c)}
          className="btn btn-sm shrink-0"
          style={{
            background: showChat ? 'rgba(13,71,161,0.25)' : 'rgba(13,71,161,0.1)',
            color: '#93c5fd', border: '1px solid rgba(13,71,161,0.3)',
            fontSize: '0.7rem', padding: '4px 10px',
          }}>
          Ask
        </button>
      </div>

      {/* ── Main content area ─────────────────────────────────────── */}
      <div className="flex-1 overflow-hidden flex flex-col">

        {/* Lesson content */}
        <div className="flex-1 overflow-y-auto px-4 py-4 touch-scroll scrollbar-thin">
          {stepLoading && (
            <div className="flex items-center justify-center py-16 gap-3">
              <Loader2 size={20} className="animate-spin" style={{ color: '#E0A300' }} />
              <span className="text-sm" style={{ color: '#4d6080' }}>Loading lesson…</span>
            </div>
          )}

          {stepError && !stepLoading && (
            <div className="rounded-2xl px-4 py-4 text-center"
              style={{ background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.25)' }}>
              <p className="text-sm mb-3" style={{ color: '#fca5a5' }}>⚠️ {stepError}</p>
              <button onClick={() => loadStep(currentStep ? 'next' : 'start')}
                className="btn btn-sm" style={{ background: 'rgba(239,68,68,0.15)', color: '#fca5a5' }}>
                Try Again
              </button>
            </div>
          )}

          {currentStep && !stepLoading && (
            <motion.div key={currentStep.step} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
              {/* Step title */}
              <div className="mb-4">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wide"
                    style={{ background: 'rgba(13,71,161,0.2)', color: '#93c5fd', border: '1px solid rgba(13,71,161,0.3)' }}>
                    Step {currentStep.step}
                  </span>
                </div>
                <h2 className="text-lg font-bold text-white" style={{ fontFamily: 'Sora' }}>
                  {currentStep.title}
                </h2>
              </div>

              {/* Lesson content with full markdown */}
              <div className="prose prose-invert prose-sm max-w-none">
                <ReactMarkdown
                  components={{
                    code({ inline, className, children, ...props }: { inline?: boolean; className?: string; children?: React.ReactNode }) {
                      const match = /language-(\w+)/.exec(className || '')
                      const codeStr = String(children).replace(/\n$/, '')
                      if (!inline && match) {
                        return (
                          <div className="relative my-3 rounded-xl overflow-hidden"
                            style={{ border: '1px solid rgba(13,71,161,0.3)' }}>
                            <div className="flex items-center justify-between px-4 py-2 text-xs"
                              style={{ background: '#030810', borderBottom: '1px solid rgba(13,71,161,0.2)', color: '#4d6080' }}>
                              <span style={{ color: '#E0A300', fontWeight: 600 }}>{match[1]}</span>
                            </div>
                            <SyntaxHighlighter
                              style={vscDarkPlus as Record<string, React.CSSProperties>}
                              language={match[1]} PreTag="div"
                              customStyle={{ margin: 0, background: '#030810', fontSize: '0.82rem', padding: '1rem' }}
                              {...props}>{codeStr}</SyntaxHighlighter>
                          </div>
                        )
                      }
                      return (
                        <code className="px-1.5 py-0.5 rounded text-[0.82em]"
                          style={{ background: 'rgba(13,71,161,0.2)', color: '#E0A300', fontFamily: 'JetBrains Mono, monospace' }}
                          {...props}>{children}</code>
                      )
                    },
                  }}>
                  {currentStep.content}
                </ReactMarkdown>
              </div>
            </motion.div>
          )}
        </div>

        {/* ── In-course Q&A chat (slide-up) ─────────────────────── */}
        <AnimatePresence>
          {showChat && (
            <motion.div key="chat"
              initial={{ height: 0, opacity: 0 }} animate={{ height: 280, opacity: 1 }}
              exit={{ height: 0, opacity: 0 }} transition={{ duration: 0.2 }}
              className="shrink-0 flex flex-col overflow-hidden"
              style={{ borderTop: '1px solid rgba(13,71,161,0.25)', background: 'rgba(9,18,35,0.98)' }}>

              <div className="px-3 pt-2 pb-1 text-[10px] font-bold uppercase tracking-widest"
                style={{ color: '#4d6080' }}>
                Ask Sir. Tega about this lesson
              </div>

              {/* Messages */}
              <div className="flex-1 overflow-y-auto px-3 py-1 flex flex-col gap-2 touch-scroll scrollbar-thin">
                {chatMsgs.length === 0 && (
                  <p className="text-[11px] text-center py-3" style={{ color: '#4d6080' }}>
                    Ask anything about <strong style={{ color: '#93c5fd' }}>{currentStep?.title || courseTitle}</strong>
                  </p>
                )}
                {chatMsgs.map((m, i) => (
                  <div key={i} className={`text-xs leading-relaxed rounded-xl px-3 py-2 max-w-[90%] ${m.role === 'user' ? 'self-end' : 'self-start'}`}
                    style={{
                      background: m.role === 'user' ? 'linear-gradient(135deg,#082B6B,#0D47A1)' : '#0f1a2e',
                      border: m.role === 'user' ? 'none' : '1px solid rgba(13,71,161,0.2)',
                      color: '#e2e8f0',
                    }}>
                    {m.role === 'assistant'
                      ? <div className="prose prose-invert prose-xs max-w-none"><ReactMarkdown>{m.content}</ReactMarkdown></div>
                      : m.content}
                  </div>
                ))}
                <div ref={chatEndRef} />
              </div>

              {/* Chat input */}
              <div className="px-3 pb-3 pt-1 flex gap-2">
                <textarea ref={inputRef} value={chatInput}
                  onChange={e => setChatInput(e.target.value)}
                  onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendCourseChat() } }}
                  placeholder="Ask about this lesson…" rows={1}
                  className="flex-1 rounded-xl text-slate-200 text-xs resize-none outline-none"
                  style={{ background: '#0f1a2e', border: '1px solid rgba(13,71,161,0.3)', padding: '8px 12px', minHeight: 36, maxHeight: 72, lineHeight: 1.5 }} />
                <button onClick={sendCourseChat} disabled={chatLoading || !chatInput.trim()}
                  className="btn btn-primary rounded-xl w-9 h-9 p-0 shrink-0"
                  style={{ background: 'linear-gradient(135deg,#0D47A1,#1565E8)', minWidth: 36 }}>
                  {chatLoading ? <Loader2 size={13} className="animate-spin" /> : <Send size={13} />}
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* ── Navigation footer ──────────────────────────────────── */}
        {currentStep && !stepLoading && !stepError && (
          <div className="shrink-0 px-4 py-3 flex items-center justify-between gap-3"
            style={{ borderTop: '1px solid rgba(13,71,161,0.2)', background: 'rgba(6,13,28,0.97)' }}>

            <div className="text-xs" style={{ color: '#4d6080' }}>
              {currentStep.step}/{currentStep.total_steps} lessons
            </div>

            <button onClick={handleNext}
              className="btn btn-primary flex items-center gap-2"
              style={{ background: 'linear-gradient(135deg,#0D47A1,#E0A300)' }}>
              {currentStep.step < currentStep.total_steps ? (
                <><ChevronRight size={15} /> Next Lesson</>
              ) : (
                <><CheckCircle size={15} /> Complete Course</>
              )}
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
