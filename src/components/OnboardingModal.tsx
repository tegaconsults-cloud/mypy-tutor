import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

interface Props { onDone: (firstMsg: string) => void }

const LEVELS = [
  { id: 'beginner',     icon: '🟢', label: 'Beginner',     sub: "I'm new to Python" },
  { id: 'intermediate', icon: '🟡', label: 'Intermediate', sub: 'I know the basics' },
  { id: 'advanced',     icon: '🔴', label: 'Advanced',     sub: 'I write Python regularly' },
]
const GOALS = [
  { id: 'career',  icon: '💼', title: 'Tech Career',       sub: 'Get a job or freelance with Python' },
  { id: 'data',    icon: '📊', title: 'Data Science',      sub: 'Learn data science and ML' },
  { id: 'build',   icon: '🚀', title: 'Build Things',      sub: 'Build apps and automate tasks' },
  { id: 'general', icon: '📚', title: 'General Knowledge', sub: 'Learn Python from scratch' },
]
const FIRST_MSGS: Record<string, string> = {
  career:  "I want to build a Python career. What should I learn first?",
  data:    "I want to learn data science and ML. Where do I start?",
  build:   "I want to build apps and automate tasks. Where do I begin?",
  general: "I want to learn Python from scratch. Can you give me a roadmap?",
}

export default function OnboardingModal({ onDone }: Props) {
  const [step, setStep]         = useState(1)
  const [selectedLevel, setLevel] = useState('')
  const [selectedGoal, setGoal]   = useState('')

  const pickLevel = (id: string) => {
    setLevel(id); localStorage.setItem('mypy_tutor_level', id)
    window.dispatchEvent(new Event('level-changed'))
    setTimeout(() => setStep(2), 280)
  }

  const pickGoal = (id: string) => { setGoal(id); setTimeout(() => setStep(3), 280) }

  const finish = () => {
    localStorage.setItem('mpt_onboarded', '1')
    onDone(FIRST_MSGS[selectedGoal] || FIRST_MSGS.general)
  }

  return (
    <div className="glass-overlay flex items-center justify-center p-4" style={{ zIndex: 2000 }}>
      <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}
        className="w-full max-w-md rounded-3xl p-7 flex flex-col gap-5"
        style={{ background: '#0f1a2e', border: '1px solid rgba(13,71,161,0.4)', boxShadow: '0 30px 80px rgba(0,0,0,.8)' }}>

        {/* Progress */}
        <div className="flex justify-center gap-2">
          {[1,2,3].map(i => (
            <motion.div key={i}
              animate={{ width: i === step ? 24 : 8, background: i <= step ? '#E0A300' : 'rgba(13,71,161,0.3)' }}
              className="h-2 rounded-full transition-all" />
          ))}
        </div>

        <AnimatePresence mode="wait">
          {/* Step 1 — Level */}
          {step === 1 && (
            <motion.div key="s1" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }}>
              <div className="text-center mb-5">
                <div className="w-16 h-16 rounded-2xl overflow-hidden mx-auto mb-3"
                  style={{ background: '#fff', border: '3px solid rgba(224,163,0,0.4)', boxShadow: '0 0 24px rgba(224,163,0,0.3)' }}>
                  <img src="/icons/mypytutor_logo.jpg" alt="MyPy Tutor" style={{ width: '100%', height: '100%', objectFit: 'contain' }} />
                </div>
                <h2 className="font-bold text-xl text-white mb-1" style={{ fontFamily: 'Sora' }}>Welcome to MyPy Tutor!</h2>
                <p className="text-sm" style={{ color: '#94a3b8' }}>Let's personalise your learning path.</p>
              </div>
              <p className="text-xs font-bold uppercase tracking-widest px-1 mb-3" style={{ color: '#4d6080' }}>What's your Python level?</p>
              <div className="flex flex-col gap-2">
                {LEVELS.map(l => (
                  <button key={l.id} onClick={() => pickLevel(l.id)}
                    className="flex items-center gap-3 p-4 rounded-2xl border text-left transition-all duration-150"
                    style={{
                      borderColor: selectedLevel === l.id ? '#E0A300' : 'rgba(13,71,161,0.25)',
                      background: selectedLevel === l.id ? 'rgba(224,163,0,0.1)' : 'rgba(13,71,161,0.06)',
                    }}>
                    <span className="text-xl">{l.icon}</span>
                    <div>
                      <div className="font-semibold text-sm text-white">{l.label}</div>
                      <div className="text-xs" style={{ color: '#4d6080' }}>{l.sub}</div>
                    </div>
                  </button>
                ))}
              </div>
            </motion.div>
          )}

          {/* Step 2 — Goal */}
          {step === 2 && (
            <motion.div key="s2" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }}>
              <div className="text-center mb-5">
                <div className="text-5xl mb-3">🎯</div>
                <h2 className="font-bold text-xl text-white mb-1" style={{ fontFamily: 'Sora' }}>What's your goal?</h2>
                <p className="text-sm" style={{ color: '#94a3b8' }}>Sir. Tega will tailor teaching to your ambitions.</p>
              </div>
              <div className="grid grid-cols-2 gap-2">
                {GOALS.map(g => (
                  <button key={g.id} onClick={() => pickGoal(g.id)}
                    className="flex flex-col gap-2 p-4 rounded-2xl border text-left transition-all duration-150"
                    style={{
                      borderColor: selectedGoal === g.id ? '#E0A300' : 'rgba(13,71,161,0.25)',
                      background: selectedGoal === g.id ? 'rgba(224,163,0,0.1)' : 'rgba(13,71,161,0.06)',
                    }}>
                    <span className="text-2xl">{g.icon}</span>
                    <div>
                      <div className="font-semibold text-xs text-white">{g.title}</div>
                      <div className="text-[10px] mt-0.5" style={{ color: '#4d6080' }}>{g.sub}</div>
                    </div>
                  </button>
                ))}
              </div>
            </motion.div>
          )}

          {/* Step 3 — Done */}
          {step === 3 && (
            <motion.div key="s3" initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}
              className="flex flex-col items-center gap-4 text-center">
              <div className="text-6xl">🎉</div>
              <div>
                <h2 className="font-bold text-xl text-white mb-2" style={{ fontFamily: 'Sora' }}>You're all set!</h2>
                <p className="text-sm leading-relaxed" style={{ color: '#94a3b8' }}>
                  Sir. Tega is ready. You have{' '}
                  <strong style={{ color: '#E0A300' }}>10 free AI prompts today</strong>{' '}
                  to ask anything about Python.
                </p>
              </div>
              <div className="w-full rounded-2xl p-4 text-left border"
                style={{ background: '#030810', borderColor: 'rgba(13,71,161,0.2)' }}>
                <p className="text-[10px] uppercase tracking-widest mb-2" style={{ color: '#4d6080' }}>Quick Start</p>
                <div className="text-xs space-y-1.5" style={{ color: '#94a3b8' }}>
                  <p>💬 Type any Python question in chat</p>
                  <p>📚 Browse courses in the Courses tab</p>
                  <p>🏆 Test yourself in the Quiz tab</p>
                  <p>💎 View all plans in the Plans tab</p>
                </div>
              </div>
              <button onClick={finish} className="btn btn-primary w-full btn-lg"
                style={{ background: 'linear-gradient(135deg,#0D47A1,#E0A300)' }}>
                🚀 Start Learning Now
              </button>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    </div>
  )
}
