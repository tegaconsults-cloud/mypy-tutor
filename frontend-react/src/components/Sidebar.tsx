import React, { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  X, MessageSquare, BookOpen, Trophy, BarChart2, Award,
  CreditCard, User, Zap, Code, Layers, Shield, Database, Brain, MessageCircle, HelpCircle,
} from 'lucide-react'
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
  { id: 'chat',         icon: <MessageSquare size={16} />, label: 'AI Tutor' },
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
  { icon: <Shield size={14} />,   label: 'OOP Concepts',       ask: 'Explain object-oriented programming in Python' },
  { icon: <Database size={14} />, label: 'Data Structures',    ask: 'Explain data structures in Python' },
  { icon: <Brain size={14} />,    label: 'ML Basics',          ask: 'What is machine learning? Explain with Python examples' },
]

export default function Sidebar({ open, onClose, onPanelChange, onAuthClick: _onAuthClick }: Props) {
  const { progress } = useProgress()
  const [, setTopics] = useState<string[]>([])

  useEffect(() => {
    getTopics().then(d => setTopics((d && d.topics) ? d.topics : []))
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
          <motion.div key="overlay"
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }} onClick={onClose}
            className="fixed inset-0 z-40"
            style={{ background: 'rgba(3,8,16,0.75)', backdropFilter: 'blur(6px)' }} />

          {/* Drawer */}
          <motion.div key="drawer"
            initial={{ x: -290 }} animate={{ x: 0 }} exit={{ x: -290 }}
            transition={{ type: 'spring', stiffness: 380, damping: 38 }}
            className="fixed top-0 left-0 bottom-0 z-50 flex flex-col overflow-y-auto scrollbar-none"
            style={{
              width: 280,
              background: 'rgba(6,13,28,0.98)',
              borderRight: '1px solid rgba(13,71,161,0.3)',
              boxShadow: '4px 0 40px rgba(0,0,0,0.6)',
            }}>

            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 shrink-0"
              style={{ borderBottom: '1px solid rgba(13,71,161,0.2)' }}>
              <div className="flex items-center gap-2.5">
                <Logo size={36} shape="none" />
                <div className="flex flex-col leading-none">
                  <span className="font-league text-sm font-black" style={{ color: '#E0A300', letterSpacing: '0.04em' }}>MYPY</span>
                  <span className="font-league text-[10px] font-bold tracking-widest text-blue-300 uppercase">TUTOR</span>
                </div>
              </div>
              <button onClick={onClose} className="btn btn-ghost btn-sm w-8 h-8 p-0 rounded-lg">
                <X size={16} />
              </button>
            </div>

            <div className="flex flex-col flex-1 overflow-y-auto scrollbar-none px-3 py-3 gap-1">

              {/* Navigation */}
              <div className="mb-2">
                <div className="text-[10px] font-bold uppercase tracking-widest px-2 mb-1.5"
                  style={{ color: '#4d6080' }}>Navigation</div>
                {NAV_ITEMS.map(item => (
                  <button key={item.id}
                    onClick={() => { onPanelChange(item.id); onClose() }}
                    className="sidebar-item w-full">
                    <span style={{ color: '#4d6080' }}>{item.icon}</span>
                    <span>{item.label}</span>
                  </button>
                ))}
              </div>

              <div className="divider" />

              {/* Quick Ask */}
              <div className="mb-2">
                <div className="text-[10px] font-bold uppercase tracking-widest px-2 mb-1.5"
                  style={{ color: '#4d6080' }}>Ask Sir. Tega</div>
                {QUICK_ASK.map(q => (
                  <button key={q.label} onClick={() => sendAsk(q.ask)}
                    className="sidebar-item w-full text-left">
                    <span style={{ color: '#4d6080' }}>{q.icon}</span>
                    <span className="text-sm">{q.label}</span>
                  </button>
                ))}
              </div>

              {/* Knowledge Gaps */}
              {progress && progress.knowledge_gaps.length > 0 && (
                <>
                  <div className="divider" />
                  <div>
                    <div className="text-[10px] font-bold uppercase tracking-widest px-2 mb-2"
                      style={{ color: '#4d6080' }}>Knowledge Gaps</div>
                    <div className="flex flex-wrap gap-1.5 px-2">
                      {progress.knowledge_gaps.map(g => (
                        <button key={g} onClick={() => sendAsk(`I need help understanding ${g}`)}
                          className="px-2.5 py-1 text-xs rounded-full transition-colors"
                          style={{
                            background: 'rgba(239,68,68,0.1)',
                            border: '1px solid rgba(239,68,68,0.3)',
                            color: '#fca5a5',
                          }}>
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
                    <div className="text-[10px] font-bold uppercase tracking-widest px-2 mb-2"
                      style={{ color: '#4d6080' }}>Recent Topics</div>
                    <div className="flex flex-wrap gap-1.5 px-2">
                      {progress.topics_seen.slice(-6).reverse().map(t => (
                        <button key={t} onClick={() => sendAsk(`Explain ${t} in Python`)}
                          className="px-2.5 py-1 text-xs rounded-full transition-colors"
                          style={{
                            background: 'rgba(13,71,161,0.1)',
                            border: '1px solid rgba(13,71,161,0.25)',
                            color: '#93c5fd',
                          }}>
                          {t}
                        </button>
                      ))}
                    </div>
                  </div>
                </>
              )}
            </div>

            {/* Footer — Feedback + Support */}
            <div className="px-3 py-3 shrink-0 flex flex-col gap-2"
              style={{ borderTop: '1px solid rgba(13,71,161,0.2)' }}>
              <button
                onClick={() => window.dispatchEvent(new Event('open-feedback'))}
                className="flex items-center justify-center gap-2 w-full px-4 py-2.5 rounded-xl text-sm font-semibold text-white transition-all duration-200"
                style={{ background: 'linear-gradient(135deg,#0D47A1,#1565E8)', boxShadow: '0 4px 16px rgba(13,71,161,0.4)' }}>
                <MessageCircle size={15} /> Send Feedback
              </button>
              <button
                onClick={() => { window.dispatchEvent(new Event('open-enquiry')); onClose() }}
                className="flex items-center justify-center gap-2 w-full px-4 py-2.5 rounded-xl text-sm font-semibold transition-all duration-200"
                style={{
                  background: 'rgba(224,163,0,0.12)',
                  border: '1px solid rgba(224,163,0,0.3)',
                  color: '#E0A300',
                }}>
                <HelpCircle size={15} /> Contact Support
              </button>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}
