import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, Send, Mail, User, MessageSquare, HelpCircle, ChevronDown } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { submitEnquiry } from '../api'

interface Props { onClose: () => void }

const CATEGORIES = [
  'Technical Issue',
  'Billing & Payments',
  'Course Access',
  'Certificate Request',
  'Account & Profile',
  'Referral & Bonus',
  'General Enquiry',
]

export default function EnquiryModal({ onClose }: Props) {
  const { user } = useAuth()
  const [name,     setName]     = useState(user?.name  || '')
  const [email,    setEmail]    = useState(user?.email || '')
  const [category, setCategory] = useState('')
  const [subject,  setSubject]  = useState('')
  const [message,  setMessage]  = useState('')
  const [loading,  setLoading]  = useState(false)
  const [success,  setSuccess]  = useState(false)
  const [error,    setError]    = useState('')

  const valid = name.trim() && email.includes('@') && category && subject.trim() && message.trim().length >= 10

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!valid) return
    setLoading(true); setError('')
    try {
      await submitEnquiry({
        name:       name.trim(),
        email:      email.trim(),
        category,
        subject:    subject.trim(),
        message:    message.trim(),
        learner_id: user?.learner_id || 'guest',
      })
      setSuccess(true)
      setTimeout(onClose, 3500)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send. Please email support@mypytutor.com.ng directly.')
    } finally {
      setLoading(false)
    }
  }

  const inputStyle: React.CSSProperties = {
    background: 'rgba(6,13,28,0.8)',
    border: '1px solid rgba(13,71,161,0.35)',
    borderRadius: 12,
    padding: '10px 14px',
    color: '#e2e8f0',
    fontSize: '0.88rem',
    width: '100%',
    outline: 'none',
    fontFamily: 'inherit',
  }

  return (
    <AnimatePresence>
      <motion.div
        key="backdrop"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
        onClick={e => e.target === e.currentTarget && onClose()}
        className="glass-overlay flex items-center justify-center p-4"
        style={{ zIndex: 60 }}>

        <motion.div
          key="modal"
          initial={{ opacity: 0, scale: 0.95, y: 16 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 16 }}
          transition={{ type: 'spring', stiffness: 400, damping: 30 }}
          className="w-full max-w-md relative rounded-3xl flex flex-col"
          style={{
            background: '#0f1a2e',
            border: '1px solid rgba(13,71,161,0.4)',
            boxShadow: '0 25px 80px rgba(0,0,0,0.8)',
            maxHeight: '90vh',
            overflow: 'hidden',
          }}>

          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4 shrink-0"
            style={{ borderBottom: '1px solid rgba(13,71,161,0.2)' }}>
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-full flex items-center justify-center shrink-0"
                style={{ background: 'rgba(13,71,161,0.2)', border: '1px solid rgba(13,71,161,0.4)' }}>
                <HelpCircle size={16} style={{ color: '#93c5fd' }} />
              </div>
              <div>
                <h2 className="font-bold text-sm text-white">Contact Support</h2>
                <p className="text-[10px]" style={{ color: '#4d6080' }}>support@mypytutor.com.ng</p>
              </div>
            </div>
            <button onClick={onClose}
              className="btn btn-ghost btn-sm w-8 h-8 p-0 rounded-xl">
              <X size={15} />
            </button>
          </div>

          {/* Body */}
          <div className="flex-1 overflow-y-auto px-6 py-5 scrollbar-thin">
            {success ? (
              <motion.div
                initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }}
                className="flex flex-col items-center text-center py-8 gap-4">
                <div className="w-16 h-16 rounded-full flex items-center justify-center text-3xl"
                  style={{ background: 'rgba(34,197,94,0.15)', border: '2px solid rgba(34,197,94,0.4)' }}>
                  ✅
                </div>
                <div>
                  <p className="font-bold text-white mb-1">Message Sent!</p>
                  <p className="text-sm" style={{ color: '#94a3b8' }}>
                    We'll respond to <strong style={{ color: '#93c5fd' }}>{email}</strong> within 24 hours.
                  </p>
                  <p className="text-xs mt-2" style={{ color: '#4d6080' }}>
                    For urgent issues: support@mypytutor.com.ng
                  </p>
                </div>
              </motion.div>
            ) : (
              <form onSubmit={handleSubmit} className="flex flex-col gap-3">
                {error && (
                  <div className="rounded-xl px-4 py-3 text-xs border"
                    style={{ background: 'rgba(239,68,68,0.08)', borderColor: 'rgba(239,68,68,0.3)', color: '#fca5a5' }}>
                    {error}
                  </div>
                )}

                <div className="grid grid-cols-2 gap-3">
                  {/* Name */}
                  <div className="relative">
                    <User size={13} className="absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none"
                      style={{ color: '#4d6080' }} />
                    <input
                      style={{ ...inputStyle, paddingLeft: 34 }}
                      placeholder="Full name"
                      value={name} onChange={e => setName(e.target.value)}
                      required
                    />
                  </div>
                  {/* Email */}
                  <div className="relative">
                    <Mail size={13} className="absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none"
                      style={{ color: '#4d6080' }} />
                    <input
                      type="email"
                      style={{ ...inputStyle, paddingLeft: 34 }}
                      placeholder="Email address"
                      value={email} onChange={e => setEmail(e.target.value)}
                      required
                    />
                  </div>
                </div>

                {/* Category */}
                <div className="relative">
                  <ChevronDown size={13} className="absolute right-3.5 top-1/2 -translate-y-1/2 pointer-events-none"
                    style={{ color: '#4d6080' }} />
                  <select
                    style={{ ...inputStyle, paddingRight: 34, appearance: 'none', height: 42 }}
                    value={category} onChange={e => setCategory(e.target.value)}
                    required>
                    <option value="">— Select category —</option>
                    {CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
                  </select>
                </div>

                {/* Subject */}
                <div className="relative">
                  <MessageSquare size={13} className="absolute left-3.5 top-3.5 pointer-events-none"
                    style={{ color: '#4d6080' }} />
                  <input
                    style={{ ...inputStyle, paddingLeft: 34 }}
                    placeholder="Subject — brief summary of your issue"
                    value={subject} onChange={e => setSubject(e.target.value)}
                    required
                  />
                </div>

                {/* Message */}
                <textarea
                  style={{ ...inputStyle, minHeight: 110, resize: 'vertical' }}
                  placeholder="Describe your issue or question in detail…"
                  value={message} onChange={e => setMessage(e.target.value)}
                  required
                />

                <div className="flex items-center justify-between gap-3 pt-1">
                  <p className="text-[10px]" style={{ color: '#4d6080' }}>
                    Response within 24 hrs · support@mypytutor.com.ng
                  </p>
                  <button
                    type="submit"
                    disabled={loading || !valid}
                    className="btn btn-primary flex items-center gap-2 shrink-0 rounded-xl"
                    style={{ height: 40, paddingLeft: 20, paddingRight: 20, fontSize: '0.85rem' }}>
                    {loading
                      ? <><div className="loading-dots scale-75"><span /><span /><span /></div> Sending…</>
                      : <><Send size={14} /> Send Message</>}
                  </button>
                </div>
              </form>
            )}
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  )
}
