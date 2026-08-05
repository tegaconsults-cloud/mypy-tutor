import React, { useEffect, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { motion, AnimatePresence } from 'framer-motion'
import { Trophy, Zap, RefreshCw, ChevronRight, CheckCircle, XCircle, Brain } from 'lucide-react'
import { generateQuiz, submitQuizAnswer, getTopics } from '../api'
import { useAuth } from '../context/AuthContext'
import { useProgress } from '../context/ProgressContext'

// Group topics by category for a cleaner dropdown
const TOPIC_GROUPS: Record<string, string[]> = {
  'Python Basics':        ['Python Intro','Python Syntax','Python Variables','Python Data Types','Python Numbers','Python Strings','Python Booleans','Python Operators','String Methods','String Formatting','String Slicing'],
  'Collections':          ['Python Lists','List Methods','List Comprehension','Python Tuples','Python Sets','Python Dictionaries','Dictionary Methods'],
  'Control Flow':         ['If Else','While Loops','For Loops','Python Range','Break and Continue','Python Functions','Lambda Functions','Python Recursion','Python Decorators','Python Closures'],
  'OOP':                  ['Python OOP','Classes and Objects','Python Inheritance','Python Polymorphism','Python Encapsulation'],
  'Modules & Libraries':  ['Python Modules','Python JSON','Python RegEx','Python Math','File Handling','Try Except','Custom Exceptions','Async Await','Threading'],
  'NumPy':                ['NumPy Intro','NumPy Creating Arrays','NumPy Array Indexing','NumPy Array Slicing','NumPy Array Shape','NumPy Normal Distribution','NumPy ufunc Intro'],
  'Pandas':               ['Pandas Intro','Pandas DataFrames','Pandas Read CSV','Pandas Cleaning Data','Pandas Correlations','Pandas Plotting'],
  'DSA':                  ['DSA Intro','Stacks','Queues','Linked Lists','Hash Tables','Binary Trees','Graphs','Bubble Sort','Quick Sort','Merge Sort'],
  'Machine Learning':     ['Machine Learning Intro','Supervised Learning','Linear Regression','Logistic Regression','Decision Trees','Random Forest','K-Nearest Neighbours','Neural Networks','Deep Learning','Model Evaluation','scikit-learn','Natural Language Processing','Transfer Learning','Gradient Boosting'],
  'AI & Prompting':       ['Prompt Engineering','Zero-shot Prompting','Few-shot Prompting','Chain-of-thought Prompting','AI Integration','LangChain','Embeddings','AI Agents','RAG'],
  'Databases & APIs':     ['MySQL','MongoDB','Flask','FastAPI','REST APIs'],
}

export default function QuizPanel() {
  const { user }    = useAuth()
  const { refresh } = useProgress()
  const [serverTopics, setServerTopics] = useState<string[]>([])
  const [topic, setTopic]       = useState('')
  const [question, setQuestion] = useState('')
  const [options, setOptions]   = useState<string[]>([])
  const [result, setResult]     = useState<{ correct: boolean; explanation: string; xp_gained: number } | null>(null)
  const [selected, setSelected] = useState<string | null>(null)
  const [loading, setLoading]   = useState(false)
  const [streak, setStreak]     = useState(0)
  const [quizError, setQuizError] = useState('')

  const level     = localStorage.getItem('mypy_tutor_level') || 'beginner'
  const learnerId = user?.learner_id || 'default'

  useEffect(() => {
    getTopics().then(d => setServerTopics(d.topics || [])).catch(() => {})
  }, [])

  // Build merged topic groups: start with static groups, add any server topics not already grouped
  const groupedTopics = { ...TOPIC_GROUPS }
  const allGrouped = new Set(Object.values(TOPIC_GROUPS).flat())
  const ungrouped = serverTopics.filter(t => !allGrouped.has(t))
  if (ungrouped.length > 0) groupedTopics['Other Topics'] = ungrouped

  const generate = async () => {
    if (!topic) return
    setLoading(true); setResult(null); setSelected(null)
    setQuestion(''); setOptions([]); setQuizError('')
    try {
      const data = await generateQuiz(learnerId, topic, level)
      setQuestion(data.question); setOptions(data.options)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Could not load quiz'
      setQuizError(msg.toLowerCase().includes('503') || msg.toLowerCase().includes('warming')
        ? 'Sir. Tega is warming up — please try again in a moment.'
        : 'Could not generate quiz. Try again.')
    } finally { setLoading(false) }
  }

  const submit = async (answer: string) => {
    if (selected) return
    setSelected(answer)
    try {
      const data = await submitQuizAnswer(learnerId, topic, level, question, answer)
      setResult(data)
      if (data.correct) setStreak(s => s + 1)
      else setStreak(0)
      if (user) refresh(user.learner_id)
    } catch (_) {
      // Non-fatal — show optimistic result
    }
  }

  return (
    <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-4 touch-scroll scrollbar-thin">

      {/* Header */}
      <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }}
        className="rounded-2xl p-4 border"
        style={{ background: 'linear-gradient(135deg,rgba(13,71,161,0.15),rgba(6,13,28,0.9))', borderColor: 'rgba(13,71,161,0.4)' }}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl flex items-center justify-center"
              style={{ background: 'rgba(13,71,161,0.2)' }}>
              <Trophy size={20} style={{ color: '#E0A300' }} />
            </div>
            <div>
              <h2 className="font-bold text-sm text-white" style={{ fontFamily: 'Sora' }}>Test Your Knowledge</h2>
              <p className="text-xs" style={{ color: '#4d6080' }}>AI-generated · earn XP on correct answers</p>
            </div>
          </div>
          {streak > 0 && (
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full"
              style={{ background: 'rgba(224,163,0,0.15)', border: '1px solid rgba(224,163,0,0.3)' }}>
              <span className="text-base">🔥</span>
              <span className="text-xs font-bold" style={{ color: '#E0A300' }}>{streak} streak</span>
            </div>
          )}
        </div>
      </motion.div>

      {/* Topic selector */}
      <div className="flex gap-2">
        <select value={topic} onChange={e => setTopic(e.target.value)} className="flex-1 h-11">
          <option value="">— Pick a topic —</option>
          {Object.entries(groupedTopics).map(([group, topicList]) => (
            <optgroup key={group} label={group}>
              {topicList.map(t => <option key={t} value={t}>{t}</option>)}
            </optgroup>
          ))}
        </select>
        <button onClick={generate} disabled={loading || !topic} className="btn btn-primary px-5 h-11">
          {loading
            ? <div className="loading-dots scale-75"><span/><span/><span/></div>
            : <><Brain size={15} /> Generate</>}
        </button>
      </div>

      {/* Inline error (replaces alert()) */}
      {quizError && (
        <div className="rounded-xl px-4 py-3 flex items-center gap-3"
          style={{ background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.25)' }}>
          <span className="text-sm flex-1" style={{ color: '#fca5a5' }}>⚠️ {quizError}</span>
          <button onClick={() => setQuizError('')} className="text-xs" style={{ color: '#4d6080' }}>✕</button>
        </div>
      )}

      {/* Question */}
      <AnimatePresence mode="wait">
        {question && (
          <motion.div key={question} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }} className="card flex flex-col gap-3">

            <div className="flex items-start gap-2">
              <div className="w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold shrink-0 mt-0.5"
                style={{ background: 'rgba(13,71,161,0.2)', color: '#93c5fd' }}>Q</div>
              <p className="text-sm font-medium leading-relaxed text-white flex-1">{question}</p>
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
                      background: isCorrect ? 'rgba(34,197,94,0.1)' : isWrong ? 'rgba(239,68,68,0.1)' : 'rgba(6,13,28,0.6)',
                      borderColor: isCorrect ? '#22c55e' : isWrong ? '#ef4444' : 'rgba(13,71,161,0.2)',
                      color: isCorrect ? '#86efac' : isWrong ? '#fca5a5' : '#e2e8f0',
                      cursor: selected ? 'default' : 'pointer',
                    }}>
                    <span className="w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold shrink-0"
                      style={{ background: 'rgba(255,255,255,0.06)', color: '#94a3b8' }}>
                      {isCorrect ? <CheckCircle size={14} style={{ color: '#86efac' }} />
                       : isWrong  ? <XCircle size={14} style={{ color: '#fca5a5' }} />
                       : String.fromCharCode(65 + i)}
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
              {result.correct
                ? <><CheckCircle size={16} style={{ color: '#86efac' }} /><span className="font-bold text-sm" style={{ color: '#86efac' }}>Correct! 🎉</span></>
                : <><XCircle size={16} style={{ color: '#fca5a5' }} /><span className="font-bold text-sm" style={{ color: '#fca5a5' }}>Not quite</span></>}
              <span className="xp-pill ml-auto"><Zap size={9} />+{result.xp_gained} XP</span>
            </div>

            <div className="text-xs leading-relaxed prose prose-invert prose-xs max-w-none" style={{ color: '#94a3b8' }}>
              <ReactMarkdown>{result.explanation}</ReactMarkdown>
            </div>

            <div className="flex gap-2 mt-3">
              <button onClick={generate}
                className="btn btn-sm flex items-center gap-1.5"
                style={{ background: 'rgba(13,71,161,0.2)', color: '#93c5fd', border: '1px solid rgba(13,71,161,0.3)' }}>
                <RefreshCw size={12} /> Next Question
              </button>
              {!result.correct && (
                <button onClick={() => {
                  window.dispatchEvent(new CustomEvent('sidebar-ask', { detail: `I got a quiz on "${topic}" wrong. Explain this topic thoroughly.` }))
                  window.dispatchEvent(new CustomEvent('switch-panel', { detail: 'chat' }))
                }} className="btn btn-sm flex items-center gap-1.5"
                  style={{ background: 'rgba(224,163,0,0.12)', color: '#E0A300', border: '1px solid rgba(224,163,0,0.3)' }}>
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
