import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import Logo from './Logo'

interface Props { onDone: (firstMsg: string) => void }

const LEVELS = [
  { id: 'beginner',     icon: '🟢', label: 'Beginner',     sub: "I'm new to Python" },
  { id: 'intermediate', icon: '🟡', label: 'Intermediate', sub: 'I know the basics' },
  { id: 'advanced',     icon: '🔴', label: 'Advanced',     sub: 'I write Python regularly' },
]
const GOALS = [
  { id: 'career',  label: '💼', title: 'Tech Career',       sub: 'Get a job or freelance with Python' },
  { id: 'data',    label: '📊', title: 'Data Science',      sub: 'Learn data science and ML' },
  { id: 'build',   label: '🚀', title: 'Build Things',      sub: 'Build apps and automate tasks' },
  { id: 'general', label: '📚', title: 'General Knowledge', sub: 'Learn Python from scratch' },
]
const FIRST_MSGS: Record<string, string> = {
  career:  "I want to build a Python career. What should I learn first?",
  data:    "I want to learn data science and ML. Where do I start?",
  build:   "I want to build apps and automate tasks with Python. Where do I begin?",
  general: "I want to learn Python from scratch. Can you give me a roadmap?",
}

export default function OnboardingModal({ onDone }: Props) {
  const [step, setStep]               = useState(1)
  const [selectedLevel, setLevel]     = useState('')
  const [selectedGoal,  setGoal]      = useState('')

  const pickLevel = (id: string) => {
    setLevel(id)
    localStorage.setItem('mypy_tutor_level', id)
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
        style={{ background: '#1e293b', border: '1px solid #334155', boxShadow: '0 30px 80px rgba(0,0,0,.7)' }}>

        {/* Progress dots */}
        <div className="flex justify-center gap-2">
          {[1,2,3].map(i => (
            <motion.div key={i} animate={{ width: i === step ? 24 : 8, background: i <= step ? '#2563eb' : '#334155' }}
              className="h-2 rounded-full transition-all" />
          ))}
        </div>

        <AnimatePresence mode="wait">
          {/* Step 1 — Level */}
          {step === 1 && (
            <motion.div key="step1" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }}>
              <div className="text-center mb-5">
                <div className="flex justify-center mb-3">
                  <Logo size={72} shape="circle" style={{ border: '3px solid rgba(37,99,235,0.4)', boxShadow: '0 0 24px rgba(37,99,235,0.3)' }} />
                </div>
                <h2 className="font-bold text-xl text-slate-100 mb-1" style={{ fontFamily: 'Sora' }}>Welcome to MyPy Tutor!</h2>
                <p className="text-sm text-slate-400">Let's personalise your learning path.</p>
              </div>
              <p className="text-xs text-slate-500 font-semibold uppercase tracking-wide mb-3">What's your Python level?</p>
              <div className="flex flex-col gap-2">
                {LEVELS.map(l => (
                  <button key={l.id} onClick={() => pickLevel(l.id)}
                    className={`flex items-center gap-3 p-4 rounded-2xl border text-left transition-all duration-150 ${
                      selectedLevel === l.id ? 'border-blue-500 bg-blue-500/10' : 'border-slate-700 bg-slate-800/40 hover:border-slate-500'
                    }`}>
                    <span className="text-xl">{l.icon}</span>
                    <div>
                      <div className="font-semibold text-sm text-slate-100">{l.label}</div>
                      <div className="text-xs text-slate-500">{l.sub}</div>
                    </div>
                  </button>
                ))}
              </div>
            </motion.div>
          )}

          {/* Step 2 — Goal */}
          {step === 2 && (
            <motion.div key="step2" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }}>
              <div className="text-center mb-5">
                <div className="text-5xl mb-3">🎯</div>
                <h2 className="font-bold text-xl text-slate-100 mb-1" style={{ fontFamily: 'Sora' }}>What's your goal?</h2>
                <p className="text-sm text-slate-400">Sir. Tega will tailor his teaching to your ambitions.</p>
              </div>
              <div className="grid grid-cols-2 gap-2">
                {GOALS.map(g => (
                  <button key={g.id} onClick={() => pickGoal(g.id)}
                    className={`flex flex-col gap-2 p-4 rounded-2xl border text-left transition-all duration-150 ${
                      selectedGoal === g.id ? 'border-purple-500 bg-purple-500/10' : 'border-slate-700 bg-slate-800/40 hover:border-slate-500'
                    }`}>
                    <span className="text-2xl">{g.label}</span>
                    <div>
                      <div className="font-semibold text-xs text-slate-100">{g.title}</div>
                      <div className="text-[10px] text-slate-500 mt-0.5">{g.sub}</div>
                    </div>
                  </button>
                ))}
              </div>
            </motion.div>
          )}

          {/* Step 3 — Done */}
          {step === 3 && (
            <motion.div key="step3" initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}
              className="flex flex-col items-center gap-4 text-center">
              <div className="text-6xl">🎉</div>
              <div>
                <h2 className="font-bold text-xl text-slate-100 mb-2" style={{ fontFamily: 'Sora' }}>You're all set!</h2>
                <p className="text-sm text-slate-400 leading-relaxed">
                  Sir. Tega is ready. You have{' '}
                  <strong className="text-green-400">10 free AI prompts today</strong>{' '}
                  to ask anything about Python.
                </p>
              </div>
              <div className="w-full rounded-2xl p-4 text-left border border-slate-700/60" style={{ background: '#0f172a' }}>
                <p className="text-[10px] text-slate-600 uppercase tracking-widest mb-2">Quick Start</p>
                <div className="text-xs text-slate-300 space-y-1.5">
                  <p>💬 Type any Python question in chat</p>
                  <p>📚 Browse courses in the Courses tab</p>
                  <p>🏆 Test yourself in the Quiz tab</p>
                  <p>💎 View all plans in the Plans tab</p>
                </div>
              </div>
              <button onClick={finish} className="btn btn-primary w-full btn-lg">
                🚀 Start Learning Now
              </button>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    </div>
  )
}
