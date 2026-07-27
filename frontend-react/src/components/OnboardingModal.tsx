import React, { useState } from 'react'

interface Props { onDone: (firstMsg: string) => void }

const LEVELS = [
  { id: 'beginner', icon: '🟢', label: 'Beginner', sub: "I'm new to Python" },
  { id: 'intermediate', icon: '🟡', label: 'Intermediate', sub: 'I know the basics' },
  { id: 'advanced', icon: '🔴', label: 'Advanced', sub: 'I write Python regularly' },
]
const GOALS = [
  { id: 'career', label: '💼 Get a tech job or freelance career' },
  { id: 'data', label: '📊 Learn data science or machine learning' },
  { id: 'build', label: '🚀 Build apps and automate tasks' },
  { id: 'general', label: '📚 General Python knowledge' },
]
const FIRST_MSGS: Record<string, string> = {
  career: "I want to build a Python career. What should I learn first?",
  data: "I want to learn data science and machine learning. Where do I start?",
  build: "I want to build apps and automate tasks with Python. Where do I begin?",
  general: "I want to learn Python from scratch. Can you give me a learning roadmap?",
}

export default function OnboardingModal({ onDone }: Props) {
  const [step, setStep] = useState(1)
  const [selectedLevel, setSelectedLevel] = useState('')
  const [selectedGoal, setSelectedGoal] = useState('')

  const pickLevel = (id: string) => {
    setSelectedLevel(id)
    localStorage.setItem('mypy_tutor_level', id)
    window.dispatchEvent(new Event('level-changed'))
    setTimeout(() => setStep(2), 300)
  }

  const pickGoal = (id: string) => {
    setSelectedGoal(id)
    setTimeout(() => setStep(3), 300)
  }

  const finish = () => {
    localStorage.setItem('mpt_onboarded', '1')
    const msg = FIRST_MSGS[selectedGoal] || FIRST_MSGS.general
    onDone(msg)
  }

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.88)', backdropFilter: 'blur(12px)', zIndex: 2000, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 20 }}>
      <div className="slide-in" style={{ background: '#111827', border: '1px solid #1f2937', borderRadius: 24, padding: '32px 28px', width: '100%', maxWidth: 460, display: 'flex', flexDirection: 'column', gap: 20, position: 'relative', boxShadow: '0 30px 80px rgba(0,0,0,.7)' }}>

        {/* Progress dots */}
        <div style={{ display: 'flex', justifyContent: 'center', gap: 8 }}>
          {[1,2,3].map(i => <div key={i} style={{ width: 10, height: 10, borderRadius: '50%', background: i <= step ? '#3b82f6' : '#374151', transition: '.2s' }} />)}
        </div>

        {/* Step 1 — Level */}
        {step === 1 && (
          <div>
            <div style={{ textAlign: 'center', marginBottom: 16 }}>
              <div style={{ fontSize: '2.5rem', marginBottom: 8 }}>🐍</div>
              <h2 style={{ fontSize: '1.2rem', fontWeight: 800, color: '#f1f5f9', marginBottom: 6 }}>Welcome to MyPy Tutor!</h2>
              <p style={{ fontSize: '.84rem', color: '#94a3b8' }}>Let's personalise your learning. What's your Python level?</p>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {LEVELS.map(l => (
                <button key={l.id} onClick={() => pickLevel(l.id)} style={{ padding: 14, borderRadius: 12, border: `2px solid ${selectedLevel === l.id ? '#3b82f6' : '#374151'}`, background: '#1f2937', color: '#f1f5f9', fontSize: '.93rem', fontWeight: 600, cursor: 'pointer', textAlign: 'left', transition: 'all .15s' }}>
                  {l.icon} <strong>{l.label}</strong> — {l.sub}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Step 2 — Goal */}
        {step === 2 && (
          <div>
            <div style={{ textAlign: 'center', marginBottom: 16 }}>
              <div style={{ fontSize: '2.5rem', marginBottom: 8 }}>🎯</div>
              <h2 style={{ fontSize: '1.2rem', fontWeight: 800, color: '#f1f5f9', marginBottom: 6 }}>What's your goal?</h2>
              <p style={{ fontSize: '.84rem', color: '#94a3b8' }}>Sir. Tega will tailor his teaching to your ambitions.</p>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {GOALS.map(g => (
                <button key={g.id} onClick={() => pickGoal(g.id)} style={{ padding: 14, borderRadius: 12, border: `2px solid ${selectedGoal === g.id ? '#3b82f6' : '#374151'}`, background: '#1f2937', color: '#f1f5f9', fontSize: '.93rem', fontWeight: 600, cursor: 'pointer', textAlign: 'left', transition: 'all .15s' }}>
                  {g.label}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Step 3 — Start */}
        {step === 3 && (
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '3rem', marginBottom: 12 }}>🎉</div>
            <h2 style={{ fontSize: '1.2rem', fontWeight: 800, color: '#f1f5f9', marginBottom: 10 }}>You're all set!</h2>
            <p style={{ fontSize: '.86rem', color: '#94a3b8', lineHeight: 1.6, marginBottom: 16 }}>
              Sir. Tega is ready. You have <strong style={{ color: '#34d399' }}>10 free AI prompts today</strong> to ask anything about Python.
            </p>
            <div style={{ background: '#1f2937', borderRadius: 12, padding: 16, marginBottom: 16, textAlign: 'left' }}>
              <div style={{ fontSize: '.72rem', color: '#6b7280', textTransform: 'uppercase', letterSpacing: '.08em', marginBottom: 8 }}>Quick start</div>
              <div style={{ fontSize: '.84rem', color: '#e5e7eb', lineHeight: 1.8 }}>
                💬 Type any Python question in chat<br />
                📚 Browse courses in the Courses tab<br />
                🏆 Test yourself with the Quiz tab<br />
                💎 See all plans in the Plans tab
              </div>
            </div>
            <button onClick={finish} className="btn btn-primary" style={{ width: '100%', padding: 14, fontSize: '.95rem' }}>
              🚀 Start Learning Now
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
