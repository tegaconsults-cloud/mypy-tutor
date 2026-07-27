import React, { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  X, Link2, Copy, Check, Users, DollarSign, Clock,
  CreditCard, TrendingUp, Share2, ChevronDown, ChevronUp,
} from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { API_BASE } from '../api'

interface ReferralUse {
  used_by_email: string
  referrer_bonus: number
  referee_discount: number
  ts: string
}

interface ReferralData {
  code: string
  uses: number
  max_uses: number
  bonus_balance: number
  paid_referrals: number
  unpaid_referrals: number
  total_referrals: number
  recent_uses: ReferralUse[]
}

interface Props { onClose: () => void }

export default function ReferralModal({ onClose }: Props) {
  const { user }   = useAuth()
  const [data, setData] = useState<ReferralData | null>(null)
  const [copied, setCopied]     = useState(false)
  const [codeCopied, setCodeCopied] = useState(false)
  const [showHistory, setShowHistory] = useState(false)
  const [loading, setLoading]   = useState(true)

  const lid    = user?.learner_id || 'default'
  const appUrl = 'https://mypytutor.com.ng'

  useEffect(() => {
    if (!user) return
    setLoading(true)
    fetch(`${API_BASE}/referral/${lid}`)
      .then(r => r.ok ? r.json() : null)
      .then(d => { if (d) setData(d) })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [user])

  const code     = data?.code || '...'
  const shareMsg = `Join MyPy Tutor — Africa's best AI Python Tutor! 🐍\nUse my code ${code} at signup to get 5% off your first payment.\n👉 ${appUrl}`

  const copyMsg = () => {
    navigator.clipboard.writeText(shareMsg)
    setCopied(true)
    setTimeout(() => setCopied(false), 3000)
  }

  const copyCode = () => {
    navigator.clipboard.writeText(code)
    setCodeCopied(true)
    setTimeout(() => setCodeCopied(false), 2000)
  }

  const shareNative = async () => {
    if (navigator.share) {
      try {
        await navigator.share({ title: 'MyPy Tutor Referral', text: shareMsg, url: appUrl })
      } catch {}
    } else {
      copyMsg()
    }
  }

  const paidUses   = data?.paid_referrals   ?? 0
  const unpaidUses = data?.unpaid_referrals ?? 0
  const totalUses  = data?.total_referrals  ?? 0
  const balance    = data?.bonus_balance    ?? 0

  return (
    <AnimatePresence>
      <motion.div
        key="backdrop"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
        onClick={e => e.target === e.currentTarget && onClose()}
        className="glass-overlay flex items-end sm:items-center justify-center"
        style={{ padding: '0' }}>

        {/* Sheet slides up from bottom on mobile, centered on desktop */}
        <motion.div
          key="sheet"
          initial={{ opacity: 0, y: 60 }} animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 60 }}
          transition={{ type: 'spring', stiffness: 380, damping: 35 }}
          className="w-full relative flex flex-col overflow-y-auto scrollbar-none"
          style={{
            background: '#111827',
            border: '1px solid #1f2937',
            borderRadius: '24px 24px 0 0',
            maxHeight: '92dvh',
            maxWidth: 480,
            boxShadow: '0 -8px 48px rgba(0,0,0,.6)',
            // On sm+ center it as a dialog
            borderBottomLeftRadius: 'clamp(0px, (100vw - 480px) * 9999, 24px)',
            borderBottomRightRadius: 'clamp(0px, (100vw - 480px) * 9999, 24px)',
            margin: 'clamp(0px, (100vw - 480px) * 9999, auto)',
          }}>

          {/* Handle bar (mobile sheet indicator) */}
          <div className="flex justify-center pt-3 pb-1 shrink-0">
            <div className="w-10 h-1 rounded-full bg-slate-700" />
          </div>

          {/* Close button */}
          <button onClick={onClose}
            className="absolute top-4 right-4 btn btn-ghost btn-sm w-9 h-9 p-0 rounded-xl z-10">
            <X size={16} />
          </button>

          <div className="flex flex-col gap-4 px-5 pb-8 pt-2 overflow-y-auto scrollbar-none">

            {/* Header */}
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-2xl flex items-center justify-center shrink-0"
                style={{ background: 'linear-gradient(135deg,rgba(34,197,94,.2),rgba(37,99,235,.15))', border: '1px solid rgba(34,197,94,.3)' }}>
                <Link2 size={22} className="text-emerald-400" />
              </div>
              <div>
                <h2 className="font-bold text-base text-slate-100" style={{ fontFamily: 'Sora' }}>
                  Referral Dashboard
                </h2>
                <p className="text-xs text-slate-500">Share your code — earn 15% bonus per paid referral</p>
              </div>
            </div>

            {loading ? (
              <div className="flex flex-col gap-3">
                {[...Array(3)].map((_, i) => <div key={i} className="skeleton h-16 rounded-2xl" />)}
              </div>
            ) : (
              <>
                {/* Stats row */}
                <div className="grid grid-cols-3 gap-2">
                  {[
                    {
                      icon: <Users size={16} className="text-blue-400" />,
                      value: totalUses,
                      label: 'Total',
                      color: '#93c5fd',
                    },
                    {
                      icon: <CreditCard size={16} className="text-emerald-400" />,
                      value: paidUses,
                      label: 'Paid',
                      color: '#86efac',
                    },
                    {
                      icon: <Clock size={16} className="text-amber-400" />,
                      value: unpaidUses,
                      label: 'Pending',
                      color: '#fcd34d',
                    },
                  ].map(s => (
                    <div key={s.label}
                      className="flex flex-col items-center gap-1.5 rounded-2xl py-3 border border-slate-700/50"
                      style={{ background: '#1f2937' }}>
                      {s.icon}
                      <span className="text-xl font-bold" style={{ color: s.color, fontFamily: 'Sora' }}>
                        {s.value}
                      </span>
                      <span className="text-[10px] text-slate-600 uppercase tracking-wider font-semibold">
                        {s.label}
                      </span>
                    </div>
                  ))}
                </div>

                {/* Balance card */}
                <div className="rounded-2xl p-4 border"
                  style={{ background: 'linear-gradient(135deg,rgba(34,197,94,.08),rgba(37,99,235,.06))', borderColor: 'rgba(34,197,94,.25)' }}>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <DollarSign size={16} className="text-emerald-400" />
                      <span className="text-sm font-semibold text-slate-300">Bonus Balance</span>
                    </div>
                    <span className="text-2xl font-black text-emerald-400" style={{ fontFamily: 'Sora' }}>
                      ₦{balance.toLocaleString()}
                    </span>
                  </div>
                  <p className="text-xs text-slate-500 mt-1.5">
                    Earned from {paidUses} paid referral{paidUses !== 1 ? 's' : ''} · Paid out on request to admin
                  </p>
                </div>

                {/* Referral code */}
                <div className="rounded-2xl p-4 border-2 border-dashed text-center"
                  style={{ borderColor: 'rgba(37,99,235,.5)', background: 'rgba(37,99,235,.05)' }}>
                  <p className="text-[10px] text-slate-500 uppercase tracking-widest mb-2 font-semibold">
                    Your Unique Referral Code
                  </p>
                  <div className="flex items-center justify-center gap-3">
                    <span className="font-mono text-3xl font-black tracking-widest text-blue-300">
                      {code}
                    </span>
                    <button onClick={copyCode}
                      className="flex items-center gap-1 px-3 py-1.5 rounded-xl text-xs font-semibold transition-all duration-150"
                      style={{ background: codeCopied ? 'rgba(34,197,94,.15)' : 'rgba(37,99,235,.2)', color: codeCopied ? '#86efac' : '#93c5fd' }}>
                      {codeCopied ? <><Check size={12} /> Copied</> : <><Copy size={12} /> Copy</>}
                    </button>
                  </div>
                </div>

                {/* How it works */}
                <div className="rounded-2xl p-4 border border-slate-700/60 text-sm space-y-2.5"
                  style={{ background: '#0f172a' }}>
                  <p className="font-semibold text-slate-200 mb-1">How it works:</p>
                  {[
                    { dot: 'text-blue-400', text: 'Friend enters your code at signup' },
                    { dot: 'text-emerald-400', text: <>They get <strong className="text-emerald-400">5% discount</strong> on their first payment</> },
                    { dot: 'text-blue-400', text: <>You earn <strong className="text-blue-400">15% bonus</strong>, credited automatically</> },
                    { dot: 'text-amber-400', text: 'Bonus paid out on request to admin' },
                  ].map((item, i) => (
                    <div key={i} className="flex items-start gap-2.5 text-slate-400">
                      <span className={`w-1.5 h-1.5 rounded-full mt-1.5 shrink-0 ${item.dot} bg-current`} />
                      <span className="leading-relaxed">{item.text}</span>
                    </div>
                  ))}
                </div>

                {/* Action buttons */}
                <div className="flex flex-col gap-2.5">
                  {/* Native share (mobile) / copy message (desktop) */}
                  <button onClick={shareNative}
                    className="btn btn-primary w-full gap-2 py-3.5 text-sm font-bold">
                    {typeof navigator !== 'undefined' && 'share' in navigator
                      ? <><Share2 size={16} /> Share Referral Code</>
                      : copied
                        ? <><Check size={16} /> Copied to Clipboard!</>
                        : <><Copy size={16} /> Copy Referral Message</>}
                  </button>

                  {/* Always show copy message button as secondary */}
                  <button onClick={copyMsg}
                    className="btn btn-secondary w-full gap-2 py-3 text-sm">
                    {copied ? <><Check size={14} className="text-green-400" /> Message Copied!</> : <><Copy size={14} /> Copy Message Text</>}
                  </button>
                </div>

                {/* Preview message */}
                <div className="rounded-xl p-3 border border-slate-800 text-xs text-slate-500 leading-relaxed italic"
                  style={{ background: '#0a0f1a' }}>
                  {shareMsg}
                </div>

                {/* Referral history — collapsible */}
                {data && data.recent_uses.length > 0 && (
                  <div className="rounded-2xl overflow-hidden border border-slate-700/60">
                    <button onClick={() => setShowHistory(h => !h)}
                      className="w-full flex items-center justify-between px-4 py-3 text-sm font-semibold text-slate-300 hover:bg-white/5 transition-colors"
                      style={{ background: '#1f2937' }}>
                      <div className="flex items-center gap-2">
                        <TrendingUp size={14} className="text-blue-400" />
                        Referral History ({data.recent_uses.length})
                      </div>
                      {showHistory ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                    </button>

                    <AnimatePresence>
                      {showHistory && (
                        <motion.div
                          initial={{ height: 0 }} animate={{ height: 'auto' }} exit={{ height: 0 }}
                          style={{ overflow: 'hidden' }}>
                          <div className="divide-y divide-slate-800/60" style={{ background: '#111827' }}>
                            {data.recent_uses.map((h, i) => {
                              const isPaid = h.referrer_bonus > 0
                              return (
                                <div key={i} className="flex items-center gap-3 px-4 py-3">
                                  <div className={`w-7 h-7 rounded-full flex items-center justify-center shrink-0 text-xs ${isPaid ? 'bg-emerald-500/15 text-emerald-400' : 'bg-amber-500/10 text-amber-400'}`}>
                                    {isPaid ? <CreditCard size={13} /> : <Clock size={13} />}
                                  </div>
                                  <div className="flex-1 min-w-0">
                                    <div className="text-xs text-slate-300 truncate">
                                      {h.used_by_email || 'User'}
                                    </div>
                                    <div className="text-[10px] text-slate-600 mt-0.5">{h.ts}</div>
                                  </div>
                                  <div className="text-right shrink-0">
                                    {isPaid ? (
                                      <span className="text-xs font-bold text-emerald-400">
                                        +₦{h.referrer_bonus.toFixed(2)}
                                      </span>
                                    ) : (
                                      <span className="badge badge-yellow text-[9px]">Pending</span>
                                    )}
                                  </div>
                                </div>
                              )
                            })}
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                )}
              </>
            )}
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  )
}
