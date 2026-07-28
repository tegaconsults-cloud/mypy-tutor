import React, { useEffect, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { motion, AnimatePresence } from 'framer-motion'
import { Trophy, Zap, RefreshCw, ChevronRight, CheckCircle, XCircle, Brain } from 'lucide-react'
import { generateQuiz, submitQuizAnswer, getTopics } from '../api'
import { useAuth } from '../context/AuthContext'
import { useProgress } from '../context/ProgressContext'

export default function QuizPanel() {
  const { user }  = useAuth()
  const { refresh } = useProgress()
  const [topics, setTopics]   = useState<string[]>([])
  const [topic, setTopic]     = useState('')
  const [question, setQuestion] = useState('')
  const [options, setOptions] = useState<string[]>([])
  const [result, setResult]   = useState<{ correct: boolean; explanation: string; xp_gained: number } | null>(null)
  const [selected, setSelected] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [streak, setStreak]   = useState(0)
  const level = localStorage.getItem('mypy_tutor_level') || 'beginner'
  const learnerId = user?.learner_id || 'default'

  useEffect(() => {
    getTopics().then(d => setTopics(d.topics || []))
  }, [])

  const generate = async () => {
    if (!topic) return
    setLoading(true); setResult(null); setSelected(null); setQuestion(''); setOptions([])
    try {
      const data = await generateQuiz(learnerId, topic, level)
      setQuestion(data.question)
      setOptions(data.options)
    } catch { alert('Could not load quiz. Try again.') }
    finally { setLoading(false) }
  }

  const submit = async (answer: string) => {
    if (selected) return
    setSelected(answer)
    const data = await submitQuizAnswer(learnerId, topic, level, question, answer)
    setResult(data)
    if (data.correct) setStreak(s => s + 1)
    else setStreak(0)
    if (user) refresh(user.learner_id)
  }

  return (
    <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-4 touch-scroll scrollbar-thin">

      {/* Header */}
      <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }}
        className="card" style={{ background: 'linear-gradient(135deg,rgba(124,58,237,0.15),rgba(30,41,59,0.9))', borderColor: 'rgba(124,58,237,0.3)' }}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl flex items-center justify-center"
              style={{ background: 'rgba(124,58,237,0.2)' }}>
              <Trophy size={20} className="text-purple-400" />
            </div>
            <div>
              <h2 className="font-bold text-slate-100 text-sm" style={{ fontFamily: 'Sora' }}>Test Your Knowledge</h2>
              <p className="text-xs text-slate-500">AI-generated quiz · earn XP on each correct answer</p>
            </div>
          </div>
          {streak > 0 && (
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full"
              style={{ background: 'rgba(245,158,11,0.15)', border: '1px solid rgba(245,158,11,0.3)' }}>
              <span className="text-base">🔥</span>
              <span className="text-xs font-bold text-amber-400">{streak} streak</span>
            </div>
          )}
        </div>
      </motion.div>

      {/* Topic selector */}
      <div className="flex gap-2">
        <select value={topic} onChange={e => setTopic(e.target.value)} className="flex-1 h-11">
          <option value="">— Pick a topic —</option>
          {topics.map(t => <option key={t} value={t}>{t}</option>)}
        </select>
        <button onClick={generate} disabled={loading || !topic} className="btn btn-primary px-5 h-11">
          {loading ? <div className="loading-dots scale-75"><span/><span/><span/></div> : <><Brain size={15} /> Generate</>}
        </button>
      </div>

      {/* Question */}
      <AnimatePresence mode="wait">
        {question && (
          <motion.div key={question} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }} className="card flex flex-col gap-3">

            <div className="flex items-start gap-2">
              <div className="w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold shrink-0 mt-0.5"
                style={{ background: 'rgba(124,58,237,0.2)', color: '#c4b5fd' }}>Q</div>
              <p className="text-sm text-slate-200 leading-relaxed font-medium flex-1">{question}</p>
            </div>

            <div className="flex flex-col gap-2 mt-1">
              {options.map((opt, i) => {
                const isSelected = selected === opt
                const isCorrect  = result?.correct && isSelected
                const isWrong    = !result?.correct && isSelected

                return (
                  <motion.button key={opt} whileTap={{ scale: 0.98 }} onClick={() => submit(opt)}
                    disabled={!!selected}
                    className="flex items-center gap-3 p-3.5 rounded-xl text-sm text-left transition-all duration-200 border"
                    style={{
                      background: isCorrect ? 'rgba(34,197,94,0.1)' : isWrong ? 'rgba(239,68,68,0.1)' : 'rgba(15,23,42,0.6)',
                      borderColor: isCorrect ? '#22c55e' : isWrong ? '#ef4444' : '#334155',
                      color: isCorrect ? '#86efac' : isWrong ? '#fca5a5' : '#e2e8f0',
                      cursor: selected ? 'default' : 'pointer',
                    }}>
                    <span className="w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold shrink-0"
                      style={{ background: 'rgba(100,116,139,0.2)', color: '#94a3b8' }}>
                      {isCorrect ? <CheckCircle size={14} className="text-green-400" /> :
                       isWrong   ? <XCircle size={14} className="text-red-400" /> :
                       String.fromCharCode(65 + i)}
                    </span>
                    {opt}
                  </motion.button>
                )
              })}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Result */}
      <AnimatePresence>
        {result && (
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
            className="rounded-2xl p-4 border"
            style={{
              background: result.correct ? 'rgba(34,197,94,0.08)' : 'rgba(239,68,68,0.08)',
              borderColor: result.correct ? 'rgba(34,197,94,0.3)' : 'rgba(239,68,68,0.25)',
            }}>

            <div className="flex items-center gap-2 mb-2">
              {result.correct ? (
                <><CheckCircle size={16} className="text-green-400" /><span className="font-bold text-sm text-green-400">Correct! 🎉</span></>
              ) : (
                <><XCircle size={16} className="text-red-400" /><span className="font-bold text-sm text-red-400">Not quite</span></>
              )}
              <span className="xp-pill ml-auto"><Zap size={9} />+{result.xp_gained} XP</span>
            </div>

            <div className="text-xs text-slate-400 leading-relaxed prose prose-invert prose-xs max-w-none">
              <ReactMarkdown>{result.explanation}</ReactMarkdown>
            </div>

            <div className="flex gap-2 mt-3">
              <button onClick={generate} className="btn btn-sm flex items-center gap-1.5"
                style={{ background: 'rgba(37,99,235,0.2)', color: '#93c5fd', border: '1px solid rgba(37,99,235,0.3)' }}>
                <RefreshCw size={12} /> Next Question
              </button>
              {!result.correct && (
                <button onClick={() => {
                  window.dispatchEvent(new CustomEvent('sidebar-ask', { detail: `I got a quiz on "${topic}" wrong. Explain this topic thoroughly with examples.` }))
                  window.dispatchEvent(new CustomEvent('switch-panel', { detail: 'chat' }))
                }} className="btn btn-sm flex items-center gap-1.5"
                  style={{ background: 'rgba(124,58,237,0.15)', color: '#c4b5fd', border: '1px solid rgba(124,58,237,0.3)' }}>
                  <ChevronRight size={12} /> Ask Sir. Tega
                </button>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
