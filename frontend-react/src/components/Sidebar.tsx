import React, { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, MessageSquare, BookOpen, Trophy, BarChart2, Award, CreditCard, User, Zap, Code, Layers, Shield, Database, Brain, MessageCircle } from 'lucide-react'
import { useProgress } from '../context/ProgressContext'
import { getTopics } from '../api'
import Logo from './Logo'

type Panel = 'chat' | 'courses' | 'quiz' | 'progress' | 'certificates' | 'pricing' | 'profile'

interface Props {
  open: boolean
  onClose: () => void
  onPanelChange: (p: Panel) => void
  onAuthClick: (tab?: 'signin' | 'signup') => void
}

const NAV_ITEMS: { id: Panel; icon: React.ReactNode; label: string }[] = [
  { id: 'chat',         icon: <MessageSquare size={16} />, label: 'AI Chat' },
  { id: 'courses',      icon: <BookOpen size={16} />,      label: 'Courses' },
  { id: 'quiz',         icon: <Trophy size={16} />,        label: 'Quiz' },
  { id: 'progress',     icon: <BarChart2 size={16} />,     label: 'Progress' },
  { id: 'certificates', icon: <Award size={16} />,         label: 'Certificates' },
  { id: 'pricing',      icon: <CreditCard size={16} />,    label: 'Plans' },
  { id: 'profile',      icon: <User size={16} />,          label: 'Profile' },
]

const QUICK_ASK = [
  { icon: <Code size={14} />,     label: 'Variables & Types',  ask: 'Explain Python variables and data types' },
  { icon: <Layers size={14} />,   label: 'Loops & Iteration',  ask: 'Explain loops in Python with examples' },
  { icon: <Zap size={14} />,      label: 'Functions',          ask: 'Explain functions in Python' },
  { icon: <Shield size={14} />,   label: 'OOP',                ask: 'Explain object-oriented programming in Python' },
  { icon: <Database size={14} />, label: 'Data Structures',    ask: 'Explain data structures in Python' },
  { icon: <Brain size={14} />,    label: 'ML Basics',          ask: 'What is machine learning? Explain with Python examples' },
]

export default function Sidebar({ open, onClose, onPanelChange, onAuthClick: _onAuthClick }: Props) {
  const { progress } = useProgress()
  const [, setTopics] = useState<string[]>([])

  useEffect(() => {
    getTopics().then(d => setTopics(d.topics || []))
  }, [])

  const sendAsk = (msg: string) => {
    window.dispatchEvent(new CustomEvent('sidebar-ask', { detail: msg }))
    onPanelChange('chat')
    onClose()
  }

  return (
    <AnimatePresence>
      {open && (
        <>
          {/* Backdrop */}
          <motion.div key="overlay" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }} onClick={onClose}
            className="fixed inset-0 z-40"
            style={{ background: 'rgba(0,0,0,0.65)', backdropFilter: 'blur(4px)' }} />

          {/* Drawer */}
          <motion.div key="drawer"
            initial={{ x: -280 }} animate={{ x: 0 }} exit={{ x: -280 }}
            transition={{ type: 'spring', stiffness: 350, damping: 35 }}
            className="fixed top-0 left-0 bottom-0 z-50 flex flex-col overflow-y-auto"
            style={{ width: 270, background: '#0f172a', borderRight: '1px solid #1e293b' }}>

            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800 shrink-0">
              <div className="flex items-center gap-2">
                <Logo size={32} shape="circle" style={{ border: '2px solid rgba(37,99,235,0.35)' }} />
                <span className="font-bold text-slate-100 text-sm" style={{ fontFamily: 'Sora' }}>MyPy Tutor</span>
              </div>
              <button onClick={onClose} className="btn btn-ghost btn-sm w-8 h-8 p-0 rounded-lg">
                <X size={16} />
              </button>
            </div>

            <div className="flex flex-col gap-1 px-3 py-3 flex-1 overflow-y-auto scrollbar-thin">
              {/* Navigation */}
              <div className="mb-2">
                <div className="text-[10px] font-bold uppercase tracking-widest text-slate-600 px-2 mb-1.5">Navigation</div>
                {NAV_ITEMS.map(item => (
                  <button key={item.id} onClick={() => { onPanelChange(item.id); onClose() }}
                    className="sidebar-item w-full">
                    <span className="text-slate-500">{item.icon}</span>
                    <span>{item.label}</span>
                  </button>
                ))}
              </div>

              <div className="divider" />

              {/* Quick Ask */}
              <div className="mb-2">
                <div className="text-[10px] font-bold uppercase tracking-widest text-slate-600 px-2 mb-1.5">Quick Ask Sir. Tega</div>
                {QUICK_ASK.map(q => (
                  <button key={q.label} onClick={() => sendAsk(q.ask)}
                    className="sidebar-item w-full text-left">
                    <span className="text-slate-600">{q.icon}</span>
                    <span className="text-sm">{q.label}</span>
                  </button>
                ))}
              </div>

              {/* Knowledge Gaps */}
              {progress && progress.knowledge_gaps.length > 0 && (
                <>
                  <div className="divider" />
                  <div>
                    <div className="text-[10px] font-bold uppercase tracking-widest text-slate-600 px-2 mb-2">Knowledge Gaps</div>
                    <div className="flex flex-wrap gap-1.5 px-2">
                      {progress.knowledge_gaps.map(g => (
                        <button key={g} onClick={() => sendAsk(`I need help understanding ${g}`)}
                          className="px-2.5 py-1 text-xs rounded-full border border-red-500/30 bg-red-500/10 text-red-400 hover:bg-red-500/20 transition-colors">
                          {g}
                        </button>
                      ))}
                    </div>
                  </div>
                </>
              )}

              {/* Recent Topics */}
              {progress && progress.topics_seen.length > 0 && (
                <>
                  <div className="divider" />
                  <div>
                    <div className="text-[10px] font-bold uppercase tracking-widest text-slate-600 px-2 mb-2">Recent Topics</div>
                    <div className="flex flex-wrap gap-1.5 px-2">
                      {progress.topics_seen.slice(-6).reverse().map(t => (
                        <button key={t} onClick={() => sendAsk(`Explain ${t} in Python`)}
                          className="px-2.5 py-1 text-xs rounded-full border border-slate-700 bg-slate-800/60 text-slate-400 hover:bg-slate-700 transition-colors">
                          {t}
                        </button>
                      ))}
                    </div>
                  </div>
                </>
              )}
            </div>

            {/* Footer */}
            <div className="px-3 py-3 border-t border-slate-800 shrink-0">
              <button onClick={() => window.dispatchEvent(new Event('open-feedback'))}
                className="flex items-center gap-2 w-full px-4 py-2.5 rounded-xl text-sm font-semibold text-white transition-all duration-200"
                style={{ background: 'linear-gradient(135deg,#7c3aed,#2563eb)' }}>
                <MessageCircle size={15} /> Send Feedback
              </button>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}
