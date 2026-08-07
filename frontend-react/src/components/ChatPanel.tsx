import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism'
import { motion, AnimatePresence } from 'framer-motion'
import { Send, Code2, Copy, Check, RefreshCw, Sparkles, Zap, ArrowUpRight } from 'lucide-react'
import { sendChat, getPromptCount } from '../api'
import { useAuth } from '../context/AuthContext'
import { useProgress } from '../context/ProgressContext'

interface Message { role: 'user' | 'assistant' | 'error'; content: string; intent?: string; xp?: number }

const STORAGE_KEY = 'mypy_tutor_history_v2'
// Server-side default — overwritten by /prompts/count response on mount
const DEFAULT_FREE_LIMIT = 10

const SUGGESTED = [
  'Explain Python variables and types',
  'How do list comprehensions work?',
  'What is a decorator in Python?',
  'Help me debug this Python code',
]

interface Props { onAuthClick: (tab?: 'signin' | 'signup') => void }

export default function ChatPanel({ onAuthClick }: Props) {
  const { user } = useAuth()
  const { refresh } = useProgress()
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput]       = useState('')
  const [code, setCode]         = useState('')
  const [codeMode, setCodeMode] = useState(false)
  const [loading, setLoading]   = useState(false)
  const [copiedIdx, setCopiedIdx]   = useState<number | null>(null)
  const [copiedMsg, setCopiedMsg]   = useState<number | null>(null)
  // Daily limit fetched live from server so it stays in sync with backend config
  const [freeLimit, setFreeLimit] = useState(DEFAULT_FREE_LIMIT)
  const [limitReached, setLimitReached] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef  = useRef<HTMLTextAreaElement>(null)

  const learnerId = user?.learner_id || 'default'
  const level     = localStorage.getItem('mypy_tutor_level') || 'beginner'

  // Fetch the real daily limit and current usage from the server
  useEffect(() => {
    getPromptCount(learnerId).then(data => {
      if (!data) return
      if (data.limit && typeof data.limit === 'number') setFreeLimit(data.limit)
      // If user is already at limit on load, show the gate immediately
      if (data.is_limited && data.used >= data.limit) setLimitReached(true)
    }).catch(() => { /* non-fatal — keep defaults */ })
  }, [learnerId])

  useEffect(() => {
    try { const s = localStorage.getItem(STORAGE_KEY); if (s) setMessages(JSON.parse(s)) } catch {}
  }, [])

  useEffect(() => {
    const h = (e: Event) => { setInput((e as CustomEvent<string>).detail); inputRef.current?.focus() }
    window.addEventListener('sidebar-ask', h)
    return () => window.removeEventListener('sidebar-ask', h)
  }, [])

  useEffect(() => {
    const h = () => { setMessages([]); localStorage.removeItem(STORAGE_KEY); localStorage.removeItem('mpt_conv_id') }
    window.addEventListener('clear-chat', h)
    return () => window.removeEventListener('clear-chat', h)
  }, [])

  useEffect(() => {
    const h = () => { try { const s = localStorage.getItem(STORAGE_KEY); if (s) setMessages(JSON.parse(s)) } catch {} }
    window.addEventListener('restore-chat', h)
    return () => window.removeEventListener('restore-chat', h)
  }, [])

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages, loading])

  const saveHistory = useCallback((msgs: Message[]) => {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(msgs)) } catch {}
  }, [])

  const send = async (override?: string) => {
    let text = (override || input).trim()
    if (!text) return
    if (limitReached) return  // hard gate — don't attempt API call
    if (codeMode && code.trim()) text = `${text}\n\n\`\`\`python\n${code.trim()}\n\`\`\``

    const history = messages.filter(m => m.role !== 'error')
      .map(m => ({ role: m.role as 'user' | 'assistant', content: m.content.slice(0, 10000) }))

    const newMsgs: Message[] = [...messages, { role: 'user', content: text }]
    setMessages(newMsgs); setInput('')
    if (codeMode) { setCode(''); setCodeMode(false) }
    setLoading(true)

    try {
      const data = await sendChat({
        message: text,
        // Send up to 20 messages — matches backend MAX_HISTORY_ITEMS
        history: history.slice(-20),
        learner_id: learnerId, level,
        conversation_id: localStorage.getItem('mpt_conv_id') || null,
      })
      if (data.conversation_id) localStorage.setItem('mpt_conv_id', data.conversation_id)
      const reply: Message = { role: 'assistant', content: data.content, intent: data.intent, xp: data.xp_gained }
      const updated = [...newMsgs, reply]
      setMessages(updated); saveHistory(updated)
      window.dispatchEvent(new Event('prompt-used'))
      // force=true so XP bar and tier badge update immediately after each message
      if (user) refresh(user.learner_id, true)
    } catch (err: unknown) {
      if (err instanceof Error) {
        const e = err as Error & { status?: number; data?: { limit?: number; error?: string } }
        if (e.status === 402 || e.data?.error === 'free_limit_reached') {
          const limit = e.data?.limit ?? freeLimit
          setLimitReached(true)
          // Remove the user message we added optimistically, show upgrade card instead
          const upgradeMsg = [
            `⏰ **You've used all ${limit} free prompts for today.**`,
            '',
            `Your quota resets at **5:00 AM WAT** each morning.`,
            '',
            `### Upgrade to keep learning:`,
            `| Bundle | Courses | Price |`,
            `|--------|---------|-------|`,
            `| 🟢 Beginner Bundle | 4 courses | ₦30,000 one-time |`,
            `| ⚡ Intermediate Bundle | 7 courses | ₦60,000 one-time |`,
            `| 🚀 Advanced Bundle | 14 courses | ₦100,000 one-time |`,
            `| 👑 Premium Bundle | ALL 16 courses | ₦100,000 one-time |`,
            '',
            `All bundles include **unlimited AI prompts** for enrolled courses.`,
            '',
            `[💳 Upgrade Now → paystack.shop/pay/vt_re4d3h52](https://paystack.shop/pay/vt_re4d3h52)`,
          ].join('\n')
          setMessages(m => [...m.slice(0, -1), { role: 'assistant', content: upgradeMsg }])
        } else {
          setMessages(m => [...m, { role: 'error', content: e.message }])
        }
      }
    } finally { setLoading(false); inputRef.current?.focus() }
  }

  const copyMessage = (content: string, idx: number) => {
    navigator.clipboard.writeText(content); setCopiedMsg(idx); setTimeout(() => setCopiedMsg(null), 2000)
  }

  const INTENT_STYLE: Record<string, { bg: string; color: string; label: string }> = {
    concept:  { bg: 'rgba(13,71,161,0.2)',  color: '#93c5fd', label: 'Concept' },
    debug:    { bg: 'rgba(239,68,68,0.15)', color: '#fca5a5', label: 'Debug' },
    codegen:  { bg: 'rgba(34,197,94,0.15)', color: '#86efac', label: 'Code Gen' },
    exercise: { bg: 'rgba(139,92,246,0.15)',color: '#c4b5fd', label: 'Exercise' },
    quiz:     { bg: 'rgba(224,163,0,0.15)', color: '#fcd34d', label: 'Quiz' },
    course:   { bg: 'rgba(21,101,232,0.15)',color: '#60a5fa', label: 'Course' },
    general:  { bg: 'rgba(30,41,59,0.6)',   color: '#94a3b8', label: 'General' },
  }

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-4 flex flex-col gap-4 touch-scroll scrollbar-thin">

        {/* Welcome */}
        {messages.length === 0 && (
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
            className="flex flex-col items-center text-center px-4 gap-4"
            style={{ paddingTop: 'max(24px, env(safe-area-inset-top, 16px))', paddingBottom: 16 }}>

            {/* Sir. Tega avatar */}
            <div className="relative">
              <div className="w-20 h-20 rounded-3xl flex items-center justify-center overflow-hidden"
                style={{ background: '#fff', border: '3px solid rgba(13,71,161,0.5)', boxShadow: '0 0 40px rgba(13,71,161,0.4)' }}>
                <img src="/icons/mypytutor_logo.jpg" alt="MyPy Tutor"
                  style={{ width: '100%', height: '100%', objectFit: 'contain' }} />
              </div>
              <div className="absolute -bottom-1 -right-1 w-6 h-6 rounded-full border-2 flex items-center justify-center"
                style={{ background: '#0D47A1', borderColor: '#060d1c' }}>
                <Sparkles size={10} className="text-white" />
              </div>
            </div>

            <div>
              <h2 className="text-xl font-bold text-white mb-1" style={{ fontFamily: 'Sora' }}>
                Hi, I'm Sir. Tega 👋
              </h2>
              <p className="text-sm leading-relaxed max-w-sm" style={{ color: '#94a3b8' }}>
                Africa's Best <strong className="text-white">AI, Python &amp; Machine Learning Tutor</strong>.<br />
                Ask me anything about Python, ML or AI.
              </p>
              <div className="inline-flex items-center gap-1.5 mt-3 px-3 py-1.5 rounded-full text-xs font-bold"
                style={{ background: 'rgba(224,163,0,0.15)', color: '#E0A300', border: '1px solid rgba(224,163,0,0.3)' }}>
                <Zap size={11} /> {freeLimit} Free Prompts / Day
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
              <p className="text-xs mb-2 font-medium" style={{ color: '#4d6080' }}>Try asking:</p>
              <div className="grid grid-cols-2 gap-2">
                {SUGGESTED.map(s => (
                  <button key={s} onClick={() => send(s)}
                    className="text-left px-3 py-2.5 rounded-xl text-xs transition-all duration-150"
                    style={{
                      background: 'rgba(13,71,161,0.08)',
                      border: '1px solid rgba(13,71,161,0.2)',
                      color: '#94a3b8',
                    }}
                    onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'rgba(13,71,161,0.18)'; (e.currentTarget as HTMLElement).style.color = '#bfdbfe' }}
                    onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'rgba(13,71,161,0.08)'; (e.currentTarget as HTMLElement).style.color = '#94a3b8' }}>
                    {s}
                  </button>
                ))}
              </div>
            </div>
          </motion.div>
        )}

        {/* Message list — initial={false} prevents re-animation of existing messages */}
        <AnimatePresence initial={false}>
          {messages.map((msg, i) => (
            <motion.div key={i}
              initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.25 }}
              className={`flex flex-col gap-1 max-w-[88%] ${msg.role === 'user' ? 'self-end items-end' : 'self-start items-start'}`}>

              <div className="text-[10px] font-bold uppercase tracking-wider mb-0.5"
                style={{ color: msg.role === 'user' ? '#E0A300' : msg.role === 'error' ? '#fca5a5' : '#93c5fd' }}>
                {msg.role === 'user' ? 'You' : msg.role === 'error' ? 'Error' : 'Sir. Tega'}
              </div>

              {msg.intent && (
                <span className="text-[10px] font-bold uppercase tracking-wide px-2 py-0.5 rounded-full mb-1 self-start"
                  style={{ background: INTENT_STYLE[msg.intent]?.bg || 'rgba(30,41,59,0.6)', color: INTENT_STYLE[msg.intent]?.color || '#94a3b8' }}>
                  {INTENT_STYLE[msg.intent]?.label || msg.intent}
                </span>
              )}

              <div className={`relative group rounded-2xl px-4 py-3 text-sm leading-relaxed break-words max-w-full ${
                msg.role === 'user' ? 'rounded-br-sm' : msg.role === 'error' ? 'rounded-bl-sm' : 'rounded-bl-sm'
              }`} style={{
                background: msg.role === 'user'
                  ? 'linear-gradient(135deg,#082B6B,#0D47A1)'
                  : msg.role === 'error'
                  ? 'rgba(239,68,68,0.08)'
                  : '#0f1a2e',
                border: msg.role === 'user' ? 'none' : `1px solid ${msg.role === 'error' ? 'rgba(239,68,68,0.25)' : 'rgba(13,71,161,0.25)'}`,
                color: msg.role === 'error' ? '#fca5a5' : '#e2e8f0',
                boxShadow: msg.role === 'user' ? '0 4px 16px rgba(13,71,161,0.3)' : undefined,
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
                              <div className="relative my-3 rounded-xl overflow-hidden"
                                style={{ border: '1px solid rgba(13,71,161,0.3)' }}>
                                <div className="flex items-center justify-between px-4 py-2 text-xs font-mono"
                                  style={{ background: '#030810', borderBottom: '1px solid rgba(13,71,161,0.2)', color: '#4d6080' }}>
                                  <span style={{ color: '#E0A300', fontWeight: 600 }}>{match[1]}</span>
                                  <button onClick={() => { navigator.clipboard.writeText(codeStr); setCopiedIdx(i); setTimeout(() => setCopiedIdx(null), 2000) }}
                                    className="flex items-center gap-1 transition-colors"
                                    style={{ color: copiedIdx === i ? '#86efac' : '#4d6080' }}>
                                    {copiedIdx === i ? <Check size={12} /> : <Copy size={12} />}
                                    {copiedIdx === i ? 'Copied' : 'Copy'}
                                  </button>
                                </div>
                                <SyntaxHighlighter style={vscDarkPlus as Record<string, React.CSSProperties>}
                                  language={match[1]} PreTag="div"
                                  customStyle={{ margin: 0, background: '#030810', fontSize: '0.82rem', padding: '1rem' }}
                                  {...props}>{codeStr}</SyntaxHighlighter>
                              </div>
                            )
                          }
                          return (
                            <code className="px-1.5 py-0.5 rounded text-[0.82em]"
                              style={{ background: 'rgba(13,71,161,0.2)', color: '#E0A300', fontFamily: 'JetBrains Mono, monospace' }} {...props}>
                              {children}
                            </code>
                          )
                        },
                        a: ({ href, children }) => (
                          <a href={href} target="_blank" rel="noopener noreferrer"
                            className="inline-flex items-center gap-1 underline-offset-2 hover:underline"
                            style={{ color: '#E0A300' }}>
                            {children}<ArrowUpRight size={11} />
                          </a>
                        ),
                      }}>
                      {msg.content}
                    </ReactMarkdown>
                  </div>
                )}
                {msg.role === 'assistant' && (
                  <button onClick={() => copyMessage(msg.content, i)}
                    className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity p-1 rounded-lg"
                    style={{ background: 'rgba(255,255,255,0.05)' }}>
                    {copiedMsg === i ? <Check size={12} style={{ color: '#86efac' }} /> : <Copy size={12} style={{ color: '#4d6080' }} />}
                  </button>
                )}
              </div>

              {msg.xp != null && msg.xp > 0 && (
                <span className="xp-pill text-[10px]"><Zap size={9} />+{msg.xp} XP</span>
              )}
            </motion.div>
          ))}
        </AnimatePresence>

        {/* Typing indicator */}
        {loading && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="self-start">
            <div className="text-[10px] font-bold uppercase tracking-wider mb-1" style={{ color: '#93c5fd' }}>Sir. Tega</div>
            <div className="rounded-2xl rounded-bl-sm px-4 py-3"
              style={{ background: '#0f1a2e', border: '1px solid rgba(13,71,161,0.25)' }}>
              <div className="loading-dots"><span /><span /><span /></div>
            </div>
          </motion.div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input area */}
      <div className="shrink-0 px-4 pb-3 pt-2"
        style={{ background: 'rgba(6,13,28,0.97)', borderTop: '1px solid rgba(13,71,161,0.2)', backdropFilter: 'blur(20px)' }}>

        {/* Hard gate when daily limit reached */}
        {limitReached && (
          <div className="mb-2 rounded-2xl px-4 py-3 flex items-center justify-between gap-3"
            style={{ background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.25)' }}>
            <p className="text-xs font-semibold" style={{ color: '#fca5a5' }}>
              ⏰ Daily limit reached — resets at 5AM WAT
            </p>
            <a href="https://paystack.shop/pay/vt_re4d3h52" target="_blank" rel="noopener noreferrer"
              className="btn btn-sm flex items-center gap-1 shrink-0 font-bold"
              style={{ background: 'linear-gradient(135deg,#0D47A1,#E0A300)', color: '#fff', fontSize: '0.7rem' }}>
              💳 Upgrade
            </a>
          </div>
        )}

        <div className="flex items-center gap-2 mb-2">
          <button onClick={() => setCodeMode(c => !c)}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-semibold transition-all duration-150"
            style={codeMode
              ? { background: 'rgba(13,71,161,0.25)', color: '#93c5fd', border: '1px solid rgba(13,71,161,0.4)' }
              : { color: '#4d6080' }}>
            <Code2 size={12} /> Paste Code
          </button>
          {messages.length > 0 && !loading && (
            <button onClick={() => send(messages.filter(m => m.role === 'user').slice(-1)[0]?.content || '')}
              className="flex items-center gap-1 px-2 py-1 rounded-lg text-xs transition-colors"
              style={{ color: '#4d6080' }}>
              <RefreshCw size={11} /> Regenerate
            </button>
          )}
        </div>

        {codeMode && (
          <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} className="mb-2">
            <textarea value={code} onChange={e => setCode(e.target.value)}
              placeholder="# Paste your Python code here…" rows={4}
              className="w-full rounded-xl border text-slate-200 text-sm resize-y outline-none"
              style={{
                background: '#030810', fontFamily: 'JetBrains Mono, monospace', fontSize: '0.82rem',
                padding: '10px 12px', minHeight: 90, maxHeight: 200, tabSize: 4,
                borderColor: 'rgba(13,71,161,0.3)',
              }} />
          </motion.div>
        )}

        <div className="flex gap-2 items-end">
          <textarea ref={inputRef} value={input}
            onChange={e => {
              setInput(e.target.value)
              e.target.style.height = 'auto'
              e.target.style.height = Math.min(e.target.scrollHeight, 140) + 'px'
            }}
            onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() } }}
            placeholder="Ask Sir Tega anything about Python…" rows={1}
            className="flex-1 rounded-2xl text-slate-200 text-sm resize-none outline-none pr-4 transition-all duration-200"
            style={{
              background: '#0f1a2e',
              border: '1px solid rgba(13,71,161,0.35)',
              padding: '12px 16px', minHeight: 48, maxHeight: 140, lineHeight: 1.5,
            }}
            onFocus={e => (e.currentTarget.style.borderColor = '#1565E8')}
            onBlur={e => (e.currentTarget.style.borderColor = 'rgba(13,71,161,0.35)')}
          />
          <button onClick={() => send()} disabled={loading || !input.trim() || limitReached}
            className="btn btn-primary rounded-2xl w-12 h-12 p-0 shrink-0"
            style={{ background: limitReached ? 'rgba(13,71,161,0.3)' : 'linear-gradient(135deg,#0D47A1,#1565E8)' }}>
            <Send size={17} />
          </button>
        </div>
        <p className="text-[10px] text-center mt-1.5" style={{ color: '#4d6080' }}>Enter to send · Shift+Enter for new line</p>
      </div>
    </div>
  )
}
