import React, { useEffect, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { generateQuiz, submitQuizAnswer, getTopics } from '../api'
import { useAuth } from '../context/AuthContext'
import { useProgress } from '../context/ProgressContext'

export default function QuizPanel() {
  const { user } = useAuth()
  const { refresh } = useProgress()
  const [topics, setTopics] = useState<string[]>([])
  const [topic, setTopic] = useState('')
  const [question, setQuestion] = useState('')
  const [options, setOptions] = useState<string[]>([])
  const [result, setResult] = useState<{ correct: boolean; explanation: string; xp_gained: number } | null>(null)
  const [selected, setSelected] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const level = localStorage.getItem('mypy_tutor_level') || 'beginner'
  const learnerId = user?.learner_id || 'default'

  useEffect(() => {
    getTopics().then(d => setTopics(d.topics || []))
  }, [])

  const generate = async () => {
    if (!topic) { alert('Pick a topic first.'); return }
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
    if (user) refresh(user.learner_id)
  }

  return (
    <div style={{ overflowY: 'auto', padding: 16, display: 'flex', flexDirection: 'column', gap: 14, WebkitOverflowScrolling: 'touch' }}>
      <h3 style={{ color: '#90cdf4', fontSize: '.97rem' }}>🏆 Test Your Knowledge</h3>
      <p style={{ fontSize: '.82rem', color: '#718096' }}>Pick a topic and take a quiz. Scores track your knowledge gaps.</p>

      <select value={topic} onChange={e => setTopic(e.target.value)} style={{ height: 44 }}>
        <option value="">— Pick a topic —</option>
        {topics.map(t => <option key={t} value={t}>{t}</option>)}
      </select>

      <button onClick={generate} disabled={loading || !topic} className="btn btn-primary">
        {loading ? 'Loading…' : 'Generate Question'}
      </button>

      {question && (
        <div style={{ background: '#1a202c', border: '1px solid #2d3748', borderRadius: 12, padding: 16, display: 'flex', flexDirection: 'column', gap: 10 }}>
          <div style={{ fontSize: '.93rem', lineHeight: 1.6, color: '#e2e8f0', fontWeight: 500 }}>{question}</div>
          {options.map(opt => {
            const isSelected = selected === opt
            const isCorrect = result?.correct && isSelected
            const isWrong = !result?.correct && isSelected
            return (
              <button key={opt} onClick={() => submit(opt)} disabled={!!selected} style={{
                background: isCorrect ? '#1a3a26' : isWrong ? '#3b1a1a' : '#0f1117',
                border: `1px solid ${isCorrect ? '#68d391' : isWrong ? '#fc8181' : '#2d3748'}`,
                color: isCorrect ? '#68d391' : isWrong ? '#fc8181' : '#e2e8f0',
                borderRadius: 10, padding: '12px 14px', fontSize: '.88rem', cursor: selected ? 'default' : 'pointer',
                textAlign: 'left', width: '100%', minHeight: 44, transition: 'all .15s',
              }}>{opt}</button>
            )
          })}
        </div>
      )}

      {result && (
        <div style={{ background: '#1a202c', border: '1px solid #2d3748', borderRadius: 12, padding: 14, fontSize: '.88rem', lineHeight: 1.65 }}>
          <ReactMarkdown>{result.explanation}</ReactMarkdown>
          <div style={{ display: 'inline-block', background: '#276749', color: '#68d391', borderRadius: 999, padding: '2px 8px', fontSize: '.7rem', fontWeight: 600, marginTop: 8 }}>
            +{result.xp_gained} XP
          </div>
          {!result.correct && (
            <button onClick={() => {
              window.dispatchEvent(new CustomEvent('sidebar-ask', { detail: `I got a quiz question on "${topic}" wrong. Explain it thoroughly with examples.` }))
              window.dispatchEvent(new CustomEvent('switch-panel', { detail: 'chat' }))
            }} className="btn btn-sm" style={{ display: 'block', marginTop: 10, background: '#2b6cb0', color: '#fff', border: 'none' }}>
              📚 Review "{topic}" with Sir. Tega
            </button>
          )}
          {result.correct && (
            <button onClick={generate} className="btn btn-sm btn-success" style={{ display: 'inline-block', marginTop: 10 }}>
              ✅ Next Question →
            </button>
          )}
        </div>
      )}
    </div>
  )
}
