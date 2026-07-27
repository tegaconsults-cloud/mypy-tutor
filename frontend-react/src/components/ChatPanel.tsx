import React, { useCallback, useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism'
import { sendChat } from '../api'
import { useAuth } from '../context/AuthContext'
import { useProgress } from '../context/ProgressContext'

interface Message { role: 'user' | 'assistant' | 'error'; content: string; intent?: string; xp?: number }

const STORAGE_KEY = 'mypy_tutor_history_v2'
const FREE_LIMIT = 10

interface Props { onAuthClick: (tab?: 'signin' | 'signup') => void }

export default function ChatPanel({ onAuthClick }: Props) {
  const { user } = useAuth()
  const { progress, refresh } = useProgress()
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [code, setCode] = useState('')
  const [codeMode, setCodeMode] = useState(false)
  const [loading, setLoading] = useState(false)
  const [copiedIdx, setCopiedIdx] = useState<number | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  const learnerId = user?.learner_id || 'default'
  const level = localStorage.getItem('mypy_tutor_level') || 'beginner'

  // Load history
  useEffect(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY)
      if (saved) setMessages(JSON.parse(saved))
    } catch {}
  }, [])

  // Sidebar ask event
  useEffect(() => {
    const handler = (e: Event) => {
      const msg = (e as CustomEvent<string>).detail
      setInput(msg)
      inputRef.current?.focus()
    }
    window.addEventListener('sidebar-ask', handler)
    return () => window.removeEventListener('sidebar-ask', handler)
  }, [])

  // Clear chat event
  useEffect(() => {
    const handler = () => {
      setMessages([])
      localStorage.removeItem(STORAGE_KEY)
      localStorage.removeItem('mpt_conv_id')
    }
    window.addEventListener('clear-chat', handler)
    return () => window.removeEventListener('clear-chat', handler)
  }, [])

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages, loading])

  const saveHistory = useCallback((msgs: Message[]) => {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(msgs)) } catch {}
  }, [])

  const send = async () => {
    let text = input.trim()
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
      if (user) refresh(user.learner_id)
    } catch (err: unknown) {
      if (err instanceof Error) {
        const e = err as Error & { status?: number; data?: { limit?: number; error?: string } }
        if (e.status === 402 || e.data?.error === 'free_limit_reached') {
          const limit = e.data?.limit || FREE_LIMIT
          const limitMsg = `⏰ **You've used all ${limit} free prompts for today.**\n\nYour quota resets at **5:00 AM WAT** every morning.\n\nOr upgrade to a **Prompt Plan**:\n- Starter (50/day) — ₦2,000/mo\n- Pro (200/day) — ₦5,000/mo\n- Unlimited — ₦10,000/mo\n\n[💳 Upgrade Now](https://paystack.shop/pay/vt_re4d3h52)`
          setMessages(m => [...m, { role: 'assistant', content: limitMsg }])
          setMessages(m => m.filter((_, i) => i !== m.length - 2)) // remove user msg
        } else {
          setMessages(m => [...m, { role: 'error', content: e.message }])
        }
      }
    } finally {
      setLoading(false)
      inputRef.current?.focus()
    }
  }

  const INTENT_COLORS: Record<string, string> = {
    concept: '#2c5282', debug: '#742a2a', codegen: '#276749',
    exercise: '#553c9a', quiz: '#744210', course: '#1a365d', general: '#4a5568',
  }
  const INTENT_TEXT: Record<string, string> = {
    concept: '#90cdf4', debug: '#fc8181', codegen: '#68d391',
    exercise: '#d6bcfa', quiz: '#f6ad55', course: '#63b3ed', general: '#e2e8f0',
  }

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      {/* Messages */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '12px 14px', display: 'flex', flexDirection: 'column', gap: 12, WebkitOverflowScrolling: 'touch' }}>
        {messages.length === 0 && (
          <div style={{ textAlign: 'center', padding: '32px 16px', color: '#718096' }}>
            <div style={{ marginBottom: 12 }}>
              <img src="/icons/logo-mpt.png" alt="MyPy Tutor" style={{ width: 64, height: 64, borderRadius: 18, objectFit: 'cover' }} />
            </div>
            <h2 style={{ fontSize: '1.05rem', color: '#a0aec0', marginBottom: 8 }}>Hi, I'm Sir. Tega 🐍</h2>
            <p style={{ fontSize: '.85rem', lineHeight: 1.7, maxWidth: 400, margin: '0 auto' }}>
              Africa's most advanced <strong style={{ color: '#e2e8f0' }}>AI Python &amp; ML Tutor</strong>.<br />
              <span style={{ background: '#744210', color: '#f6ad55', borderRadius: 8, padding: '3px 8px', fontSize: '.76rem', fontWeight: 600, margin: '0 3px' }}>⚡ {FREE_LIMIT} Free Prompts/Day</span>
            </p>
            {!user && (
              <div style={{ display: 'flex', gap: 10, justifyContent: 'center', marginTop: 16, flexWrap: 'wrap' }}>
                <button onClick={() => onAuthClick('signup')} className="btn btn-primary">🚀 Start Free</button>
                <button onClick={() => onAuthClick('signin')} className="btn btn-secondary">Sign In</button>
              </div>
            )}
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} style={{
            display: 'flex', flexDirection: 'column', maxWidth: '88%',
            alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
            alignItems: msg.role === 'user' ? 'flex-end' : 'flex-start',
          }}>
            <div style={{ fontSize: '.68rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '.05em', marginBottom: 3, color: msg.role === 'user' ? '#63b3ed' : msg.role === 'error' ? '#fc8181' : '#68d391' }}>
              {msg.role === 'user' ? 'You' : msg.role === 'error' ? 'Error' : 'Sir. Tega'}
            </div>
            {msg.intent && (
              <span style={{ display: 'inline-block', fontSize: '.65rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '.06em', padding: '2px 7px', borderRadius: 999, marginBottom: 4, background: INTENT_COLORS[msg.intent] || '#4a5568', color: INTENT_TEXT[msg.intent] || '#e2e8f0' }}>
                {msg.intent}
              </span>
            )}
            <div style={{
              padding: '10px 14px', borderRadius: 14, lineHeight: 1.65, fontSize: '.92rem', wordBreak: 'break-word',
              background: msg.role === 'user' ? '#2b4a7a' : msg.role === 'error' ? '#3b1a1a' : '#1a202c',
              border: msg.role === 'user' ? 'none' : `1px solid ${msg.role === 'error' ? '#742a2a' : '#2d3748'}`,
              color: msg.role === 'error' ? '#fc8181' : '#e2e8f0',
              borderBottomRightRadius: msg.role === 'user' ? 4 : 14,
              borderBottomLeftRadius: msg.role === 'user' ? 14 : 4,
              maxWidth: '100%',
            }}>
              {msg.role === 'user' || msg.role === 'error' ? (
                <span>{msg.content}</span>
              ) : (
                <ReactMarkdown
                  components={{
                    code({ inline, className, children, ...props }: { inline?: boolean; className?: string; children?: React.ReactNode }) {
                      const match = /language-(\w+)/.exec(className || '')
                      const codeStr = String(children).replace(/\n$/, '')
                      if (!inline && match) {
                        return (
                          <div style={{ position: 'relative', margin: '8px 0' }}>
                            <SyntaxHighlighter style={vscDarkPlus as Record<string, React.CSSProperties>} language={match[1]} PreTag="div" {...props}>
                              {codeStr}
                            </SyntaxHighlighter>
                            <button onClick={() => { navigator.clipboard.writeText(codeStr); setCopiedIdx(i); setTimeout(() => setCopiedIdx(null), 2000) }} style={{ position: 'absolute', top: 7, right: 7, background: '#2d3748', color: '#a0aec0', border: 'none', borderRadius: 5, padding: '4px 9px', fontSize: '.72rem', cursor: 'pointer' }}>
                              {copiedIdx === i ? 'Copied!' : 'Copy'}
                            </button>
                          </div>
                        )
                      }
                      return <code style={{ background: '#2d3748', color: '#f6ad55', padding: '2px 5px', borderRadius: 4, fontFamily: 'Consolas, monospace', fontSize: '.86em' }} {...props}>{children}</code>
                    },
                  }}
                >
                  {msg.content}
                </ReactMarkdown>
              )}
            </div>
            {msg.xp && msg.xp > 0 && (
              <span style={{ display: 'inline-block', background: '#276749', color: '#68d391', borderRadius: 999, padding: '2px 8px', fontSize: '.7rem', fontWeight: 600, marginTop: 4 }}>
                +{msg.xp} XP
              </span>
            )}
          </div>
        ))}

        {loading && (
          <div style={{ alignSelf: 'flex-start' }}>
            <div style={{ fontSize: '.68rem', color: '#68d391', marginBottom: 3, fontWeight: 600, textTransform: 'uppercase' }}>Sir. Tega</div>
            <div style={{ background: '#1a202c', border: '1px solid #2d3748', borderRadius: 14, borderBottomLeftRadius: 4, padding: '11px 14px' }}>
              <div className="loading-dots"><span /><span /><span /></div>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input area */}
      <div style={{ padding: '8px 12px 10px', borderTop: '1px solid #2d3748', display: 'flex', flexDirection: 'column', gap: 6, background: '#0f1117', flexShrink: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <input type="checkbox" id="code-mode" checked={codeMode} onChange={e => setCodeMode(e.target.checked)} style={{ width: 'auto', accentColor:'#3182ce' }} />
          <label htmlFor="code-mode" style={{ fontSize: '.78rem', color: '#718096', cursor: 'pointer', userSelect: 'none' }}>📝 Paste code</label>
        </div>
        {codeMode && (
          <textarea value={code} onChange={e => setCode(e.target.value)} placeholder="# Paste your Python code here…" rows={4}
            style={{ background: '#0d1117', border: '1px solid #2d3748', borderRadius: 8, color: '#e2e8f0', fontFamily: 'Consolas, monospace', fontSize: '.85rem', padding: '9px 12px', resize: 'vertical', minHeight: 90, maxHeight: 200, outline: 'none', tabSize: 4 }}
            onKeyDown={e => { if (e.key === 'Tab') { e.preventDefault(); const s = e.currentTarget.selectionStart; const v = e.currentTarget.value; e.currentTarget.value = v.slice(0, s) + '    ' + v.slice(s); e.currentTarget.selectionStart = e.currentTarget.selectionEnd = s + 4 } }}
          />
        )}
        <div style={{ display: 'flex', gap: 8, alignItems: 'flex-end' }}>
          <textarea ref={inputRef} value={input} onChange={e => { setInput(e.target.value); e.target.style.height = 'auto'; e.target.style.height = Math.min(e.target.scrollHeight, 140) + 'px' }}
            onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() } }}
            placeholder="Ask a Python question…" rows={1}
            style={{ flex: 1, background: '#1a202c', border: '1px solid #2d3748', borderRadius: 12, color: '#e2e8f0', fontSize: '1rem', padding: '10px 14px', resize: 'none', minHeight: 44, maxHeight: 140, lineHeight: 1.5, outline: 'none' }}
          />
          <button onClick={send} disabled={loading || !input.trim()} className="btn btn-primary" style={{ minWidth: 64, height: 44, borderRadius: 12 }}>
            Send
          </button>
        </div>
      </div>
    </div>
  )
}
