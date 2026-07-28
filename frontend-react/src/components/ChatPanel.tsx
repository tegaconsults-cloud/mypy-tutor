import React, { useCallback, useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism'
import { motion, AnimatePresence } from 'framer-motion'
import { Send, Code2, Copy, Check, RefreshCw, Sparkles, Zap, ArrowUpRight } from 'lucide-react'
import { sendChat } from '../api'
import { useAuth } from '../context/AuthContext'
import { useProgress } from '../context/ProgressContext'
import Logo from './Logo'

interface Message { role: 'user' | 'assistant' | 'error'; content: string; intent?: string; xp?: number }

const STORAGE_KEY = 'mypy_tutor_history_v2'
const FREE_LIMIT = 10

const SUGGESTED = [
  'Explain Python variables',
  'How do I use list comprehensions?',
  'What is a decorator?',
  'Debug my Python code',
]

interface Props { onAuthClick: (tab?: 'signin' | 'signup') => void }

export default function ChatPanel({ onAuthClick }: Props) {
  const { user } = useAuth()
  const { refresh } = useProgress()
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [code, setCode] = useState('')
  const [codeMode, setCodeMode] = useState(false)
  const [loading, setLoading] = useState(false)
  const [copiedIdx, setCopiedIdx] = useState<number | null>(null)
  const [copiedMsg, setCopiedMsg] = useState<number | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef  = useRef<HTMLTextAreaElement>(null)

  const learnerId = user?.learner_id || 'default'
  const level     = localStorage.getItem('mypy_tutor_level') || 'beginner'

  useEffect(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY)
      if (saved) setMessages(JSON.parse(saved))
    } catch {}
  }, [])

  useEffect(() => {
    const handler = (e: Event) => { setInput((e as CustomEvent<string>).detail); inputRef.current?.focus() }
    window.addEventListener('sidebar-ask', handler)
    return () => window.removeEventListener('sidebar-ask', handler)
  }, [])

  useEffect(() => {
    const handler = () => { setMessages([]); localStorage.removeItem(STORAGE_KEY); localStorage.removeItem('mpt_conv_id') }
    window.addEventListener('clear-chat', handler)
    return () => window.removeEventListener('clear-chat', handler)
  }, [])

  useEffect(() => {
    const handler = () => {
      try { const saved = localStorage.getItem(STORAGE_KEY); if (saved) setMessages(JSON.parse(saved)) } catch {}
    }
    window.addEventListener('restore-chat', handler)
    return () => window.removeEventListener('restore-chat', handler)
  }, [])

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages, loading])

  const saveHistory = useCallback((msgs: Message[]) => {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(msgs)) } catch {}
  }, [])

  const send = async (override?: string) => {
    let text = (override || input).trim()
    if (!text) return
    if (codeMode && code.trim()) text = `${text}\n\n\`\`\`python\n${code.trim()}\n\`\`\``

    const history = messages
      .filter(m => m.role !== 'error')
      .map(m => ({ role: m.role as 'user' | 'assistant', content: m.content.slice(0, 10000) }))

    const newMsgs: Message[] = [...messages, { role: 'user', content: text }]
    setMessages(newMsgs)
    setInput('')
    if (codeMode) { setCode(''); setCodeMode(false) }
    setLoading(true)

    try {
      const data = await sendChat({
        message: text,
        history: history.slice(-10),
        learner_id: learnerId,
        level,
        conversation_id: localStorage.getItem('mpt_conv_id') || null,
      })
      if (data.conversation_id) localStorage.setItem('mpt_conv_id', data.conversation_id)
      const reply: Message = { role: 'assistant', content: data.content, intent: data.intent, xp: data.xp_gained }
      const updated = [...newMsgs, reply]
      setMessages(updated)
      saveHistory(updated)
      window.dispatchEvent(new Event('prompt-used'))
      if (user) refresh(user.learner_id)
    } catch (err: unknown) {
      if (err instanceof Error) {
        const e = err as Error & { status?: number; data?: { limit?: number; error?: string } }
        if (e.status === 402 || e.data?.error === 'free_limit_reached') {
          const limit = e.data?.limit || FREE_LIMIT
          const limitMsg = `⏰ **You've used all ${limit} free prompts for today.**\n\nYour quota resets at **5:00 AM WAT** each morning.\n\n### Upgrade for more:\n| Plan | Prompts | Price |\n|------|---------|-------|\n| Starter | 50/day | ₦2,000/mo |\n| Pro | 200/day | ₦5,000/mo |\n| Unlimited | ∞ | ₦10,000/mo |\n\n[💳 Upgrade Now →](https://paystack.shop/pay/vt_re4d3h52)`
          setMessages(m => [...m.slice(0, -1), { role: 'assistant', content: limitMsg }])
        } else {
          setMessages(m => [...m, { role: 'error', content: e.message }])
        }
      }
    } finally {
      setLoading(false)
      inputRef.current?.focus()
    }
  }

  const copyMessage = (content: string, idx: number) => {
    navigator.clipboard.writeText(content)
    setCopiedMsg(idx)
    setTimeout(() => setCopiedMsg(null), 2000)
  }

  const INTENT_STYLE: Record<string, { bg: string; color: string; label: string }> = {
    concept:  { bg: 'rgba(37,99,235,0.15)',  color: '#93c5fd', label: 'Concept' },
    debug:    { bg: 'rgba(239,68,68,0.12)',  color: '#fca5a5', label: 'Debug' },
    codegen:  { bg: 'rgba(34,197,94,0.12)',  color: '#86efac', label: 'Code Gen' },
    exercise: { bg: 'rgba(124,58,237,0.15)', color: '#c4b5fd', label: 'Exercise' },
    quiz:     { bg: 'rgba(245,158,11,0.12)', color: '#fcd34d', label: 'Quiz' },
    course:   { bg: 'rgba(6,182,212,0.12)',  color: '#67e8f9', label: 'Course' },
    general:  { bg: 'rgba(100,116,139,0.15)', color: '#94a3b8', label: 'General' },
  }

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-4 flex flex-col gap-4 touch-scroll scrollbar-thin">

        {/* Welcome state */}
        {messages.length === 0 && (
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}
            className="flex flex-col items-center text-center py-10 px-4 gap-5">

            <div className="relative">
              <Logo size={80} shape="circle" style={{ border: '3px solid rgba(37,99,235,0.45)', boxShadow: '0 0 32px rgba(37,99,235,0.35)' }} />
              <div className="absolute -bottom-1 -right-1 w-6 h-6 rounded-full bg-green-500 border-2 border-slate-900 flex items-center justify-center">
                <Sparkles size={10} className="text-white" />
              </div>
            </div>

            <div>
              <h2 className="text-xl font-bold text-slate-100 mb-1" style={{ fontFamily: 'Sora' }}>
                Hi, I'm Sir. Tega 👋
              </h2>
              <p className="text-slate-400 text-sm leading-relaxed max-w-sm">
                Africa's most advanced <span className="text-white font-semibold">AI Python & ML Tutor</span>.
                Ask me anything about Python.
              </p>
              <div className="inline-flex items-center gap-1.5 mt-3 px-3 py-1.5 rounded-full text-xs font-bold"
                style={{ background: 'rgba(245,158,11,0.15)', color: '#fcd34d', border: '1px solid rgba(245,158,11,0.3)' }}>
                <Zap size={11} /> {FREE_LIMIT} Free Prompts / Day
              </div>
            </div>

            {!user && (
              <div className="flex gap-3 flex-wrap justify-center">
                <button onClick={() => onAuthClick('signup')} className="btn btn-primary">🚀 Start Free</button>
                <button onClick={() => onAuthClick('signin')} className="btn btn-secondary">Sign In</button>
              </div>
            )}

            {/* Suggested prompts */}
            <div className="w-full max-w-md">
              <p className="text-xs text-slate-600 mb-2 font-medium">Try asking:</p>
              <div className="grid grid-cols-2 gap-2">
                {SUGGESTED.map(s => (
                  <button key={s} onClick={() => send(s)}
                    className="text-left px-3 py-2.5 rounded-xl text-xs text-slate-400 border border-slate-700/60 hover:border-blue-500/40 hover:text-slate-200 hover:bg-blue-500/5 transition-all duration-150">
                    {s}
                  </button>
                ))}
              </div>
            </div>
          </motion.div>
        )}

        {/* Message list */}
        <AnimatePresence initial={false}>
          {messages.map((msg, i) => (
            <motion.div key={i}
              initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.25 }}
              className={`flex flex-col gap-1 max-w-[88%] ${msg.role === 'user' ? 'self-end items-end' : 'self-start items-start'}`}>

              <div className={`text-[10px] font-bold uppercase tracking-wider mb-0.5 ${
                msg.role === 'user' ? 'text-blue-400' : msg.role === 'error' ? 'text-red-400' : 'text-emerald-400'
              }`}>
                {msg.role === 'user' ? 'You' : msg.role === 'error' ? 'Error' : 'Sir. Tega'}
              </div>

              {msg.intent && (
                <span className="text-[10px] font-bold uppercase tracking-wide px-2 py-0.5 rounded-full mb-1 self-start"
                  style={{ background: INTENT_STYLE[msg.intent]?.bg || 'rgba(100,116,139,0.15)', color: INTENT_STYLE[msg.intent]?.color || '#94a3b8' }}>
                  {INTENT_STYLE[msg.intent]?.label || msg.intent}
                </span>
              )}

              <div className={`relative group rounded-2xl px-4 py-3 text-sm leading-relaxed break-words max-w-full ${
                msg.role === 'user'
                  ? 'text-white rounded-br-sm'
                  : msg.role === 'error'
                  ? 'text-red-300 border border-red-500/25 rounded-bl-sm'
                  : 'text-slate-200 border border-slate-700/50 rounded-bl-sm'
              }`} style={{
                background: msg.role === 'user'
                  ? 'linear-gradient(135deg,#1d4ed8,#2563eb)'
                  : msg.role === 'error'
                  ? 'rgba(239,68,68,0.08)'
                  : '#1e293b',
              }}>
                {msg.role === 'user' || msg.role === 'error' ? (
                  <span style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</span>
                ) : (
                  <div className="prose prose-invert prose-sm max-w-none">
                    <ReactMarkdown
                      components={{
                        code({ inline, className, children, ...props }: { inline?: boolean; className?: string; children?: React.ReactNode }) {
                          const match = /language-(\w+)/.exec(className || '')
                          const codeStr = String(children).replace(/\n$/, '')
                          if (!inline && match) {
                            return (
                              <div className="relative my-3 rounded-xl overflow-hidden border border-slate-700/50">
                                <div className="flex items-center justify-between px-4 py-2 text-xs text-slate-500 font-mono"
                                  style={{ background: '#0d1117', borderBottom: '1px solid #1e293b' }}>
                                  <span className="text-blue-400 font-semibold">{match[1]}</span>
                                  <button onClick={() => { navigator.clipboard.writeText(codeStr); setCopiedIdx(i); setTimeout(() => setCopiedIdx(null), 2000) }}
                                    className="flex items-center gap-1 hover:text-slate-300 transition-colors">
                                    {copiedIdx === i ? <Check size={12} className="text-green-400" /> : <Copy size={12} />}
                                    {copiedIdx === i ? 'Copied' : 'Copy'}
                                  </button>
                                </div>
                                <SyntaxHighlighter
                                  style={vscDarkPlus as Record<string, React.CSSProperties>}
                                  language={match[1]} PreTag="div"
                                  customStyle={{ margin: 0, background: '#0d1117', fontSize: '0.82rem', padding: '1rem' }}
                                  {...props}>{codeStr}</SyntaxHighlighter>
                              </div>
                            )
                          }
                          return (
                            <code className="px-1.5 py-0.5 rounded text-amber-300 text-[0.82em]"
                              style={{ background: 'rgba(245,158,11,0.1)', fontFamily: 'Consolas, monospace' }} {...props}>
                              {children}
                            </code>
                          )
                        },
                        a: ({ href, children }) => (
                          <a href={href} target="_blank" rel="noopener noreferrer"
                            className="inline-flex items-center gap-1 text-blue-400 hover:text-blue-300 underline-offset-2 hover:underline">
                            {children}<ArrowUpRight size={11} />
                          </a>
                        ),
                      }}>
                      {msg.content}
                    </ReactMarkdown>
                  </div>
                )}

                {/* Copy message button */}
                {msg.role === 'assistant' && (
                  <button onClick={() => copyMessage(msg.content, i)}
                    className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity p-1 rounded-lg hover:bg-white/10"
                    title="Copy response">
                    {copiedMsg === i ? <Check size={12} className="text-green-400" /> : <Copy size={12} className="text-slate-500" />}
                  </button>
                )}
              </div>

              {msg.xp != null && msg.xp > 0 && (
                <span className="xp-pill text-[10px]">
                  <Zap size={9} />+{msg.xp} XP
                </span>
              )}
            </motion.div>
          ))}
        </AnimatePresence>

        {/* Loading indicator */}
        {loading && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="self-start">
            <div className="text-[10px] font-bold uppercase tracking-wider text-emerald-400 mb-1">Sir. Tega</div>
            <div className="rounded-2xl rounded-bl-sm px-4 py-3 border border-slate-700/50" style={{ background: '#1e293b' }}>
              <div className="loading-dots">
                <span /><span /><span />
              </div>
            </div>
          </motion.div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input area */}
      <div className="shrink-0 px-4 pb-3 pt-2 border-t border-slate-800/60"
        style={{ background: 'rgba(15,23,42,0.95)', backdropFilter: 'blur(20px)' }}>

        {/* Code mode toggle */}
        <div className="flex items-center gap-2 mb-2">
          <button onClick={() => setCodeMode(c => !c)}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-semibold transition-all duration-150 ${
              codeMode ? 'bg-blue-500/20 text-blue-300 border border-blue-500/30' : 'text-slate-600 hover:text-slate-400'
            }`}>
            <Code2 size={12} /> Paste Code
          </button>
          {messages.length > 0 && !loading && (
            <button onClick={() => send(messages.filter(m=>m.role==='user').slice(-1)[0]?.content || '')}
              className="flex items-center gap-1 px-2 py-1 rounded-lg text-xs text-slate-600 hover:text-slate-400 transition-colors"
              title="Regenerate">
              <RefreshCw size={11} /> Regenerate
            </button>
          )}
        </div>

        {/* Code textarea */}
        {codeMode && (
          <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }} className="mb-2">
            <textarea value={code} onChange={e => setCode(e.target.value)}
              placeholder="# Paste your Python code here…" rows={4}
              className="w-full rounded-xl border border-slate-700 text-slate-200 text-sm resize-y outline-none"
              style={{ background: '#0d1117', fontFamily: 'Consolas, monospace', fontSize: '0.82rem', padding: '10px 12px', minHeight: 90, maxHeight: 200, tabSize: 4 }}
              onKeyDown={e => {
                if (e.key === 'Tab') {
                  e.preventDefault()
                  const s = e.currentTarget.selectionStart
                  const v = e.currentTarget.value
                  e.currentTarget.value = v.slice(0, s) + '    ' + v.slice(s)
                  e.currentTarget.selectionStart = e.currentTarget.selectionEnd = s + 4
                }
              }}
            />
          </motion.div>
        )}

        {/* Main input row */}
        <div className="flex gap-2 items-end">
          <div className="flex-1 relative">
            <textarea ref={inputRef} value={input}
              onChange={e => {
                setInput(e.target.value)
                e.target.style.height = 'auto'
                e.target.style.height = Math.min(e.target.scrollHeight, 140) + 'px'
              }}
              onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() } }}
              placeholder="Ask Sir Tega anything…"
              rows={1}
              className="w-full rounded-2xl border border-slate-700 bg-slate-800/60 text-slate-200 text-sm resize-none outline-none pr-4 transition-all duration-200 focus:border-blue-500/60"
              style={{ padding: '12px 16px', minHeight: 48, maxHeight: 140, lineHeight: 1.5 }}
            />
          </div>
          <button onClick={() => send()} disabled={loading || !input.trim()}
            className="btn btn-primary rounded-2xl w-12 h-12 p-0 shrink-0">
            <Send size={17} />
          </button>
        </div>
        <p className="text-[10px] text-slate-700 text-center mt-1.5">Enter to send · Shift+Enter for new line</p>
      </div>
    </div>
  )
}
