import React, { useState } from 'react'
import { motion } from 'framer-motion'
import { Check, Zap, Crown, Star, CreditCard, Building2, Copy } from 'lucide-react'
import CoursesPanel from './CoursesPanel'

const PAYSTACK = 'https://paystack.shop/pay/vt_re4d3h52'

const BUNDLES = [
  {
    tier: 'tier-1', badge: '🟢 Beginner Bundle', name: 'Python Foundation', price: '₦8,000',
    period: 'one-time', desc: 'All 4 beginner courses bundled.',
    features: ['43 structured lessons + exercises', 'Per-lesson quizzes & XP', 'Basic Certificate eligibility', 'Save ₦3,000 vs individual'],
    cta: 'Buy Beginner Bundle', link: `${PAYSTACK}?plan=beginner+bundle&tier=tier1&amount=8000`,
    gradient: 'linear-gradient(135deg,rgba(37,99,235,0.15),rgba(30,41,59,0.95))', border: 'rgba(37,99,235,0.3)', accent: '#93c5fd', icon: 'logo',
  },
  {
    tier: 'tier-2', badge: '⚡ Intermediate Bundle', name: '7 Courses', price: '₦15,000',
    period: 'one-time', desc: 'Beginner + Functions, OOP, Standard Library.', popular: true,
    features: ['86 structured lessons', 'OOP, decorators, generators', 'Advanced Certificate eligibility', 'Save ₦9,000 vs individual'],
    cta: 'Buy Intermediate Bundle', link: `${PAYSTACK}?plan=intermediate+bundle&tier=tier2&amount=15000`,
    gradient: 'linear-gradient(135deg,rgba(124,58,237,0.18),rgba(30,41,59,0.95))', border: 'rgba(124,58,237,0.4)', accent: '#c4b5fd', icon: '⚡',
  },
  {
    tier: 'tier-3', badge: '👑 Elite Bundle', name: 'ALL 16 Courses', price: '₦35,000',
    period: 'one-time', desc: 'Every course: ML, AI, DSA, Data Science.',
    features: ['Machine Learning (30 lessons)', 'AI & Prompt Engineering', 'NumPy, Pandas, Data Science', 'Executive Masters Certificate', 'Save ₦55,000 vs individual'],
    cta: 'Buy Elite Bundle', link: `${PAYSTACK}?plan=elite+bundle&tier=tier3&amount=35000`,
    gradient: 'linear-gradient(135deg,rgba(245,158,11,0.15),rgba(30,41,59,0.95))', border: 'rgba(245,158,11,0.35)', accent: '#fcd34d', icon: '👑',
  },
]

const PROMPTS = [
  { badge: 'Starter', name: '50 Prompts / Day', price: '₦2,000', period: '/month', desc: 'Perfect for regular learners.', link: `${PAYSTACK}?plan=prompt+starter&amount=2000`, accent: '#93c5fd', border: 'rgba(37,99,235,0.3)', bg: 'rgba(37,99,235,0.1)' },
  { badge: 'Pro', name: '200 Prompts / Day', price: '₦5,000', period: '/month', desc: 'For serious learners.', popular: true, link: `${PAYSTACK}?plan=prompt+pro&amount=5000`, accent: '#c4b5fd', border: 'rgba(124,58,237,0.4)', bg: 'rgba(124,58,237,0.12)' },
  { badge: 'Unlimited', name: 'No Daily Cap', price: '₦10,000', period: '/month', desc: '24/7 access, no restrictions.', link: `${PAYSTACK}?plan=prompt+unlimited&amount=10000`, accent: '#fcd34d', border: 'rgba(245,158,11,0.35)', bg: 'rgba(245,158,11,0.1)' },
]

type Tab = 'catalog' | 'bundles' | 'prompts'

export default function PricingPanel() {
  const [tab, setTab] = useState<Tab>('bundles')
  const [copied, setCopied] = useState(false)

  const copyAcct = () => {
    navigator.clipboard.writeText('1228732577')
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="flex-1 overflow-y-auto flex flex-col touch-scroll scrollbar-thin">

      {/* Tab bar */}
      <div className="flex gap-1.5 p-3 border-b border-slate-800/60 sticky top-0 z-10"
        style={{ background: 'rgba(15,23,42,0.95)', backdropFilter: 'blur(20px)' }}>
        {([['catalog', '📚', 'Catalog'], ['bundles', '🎯', 'Bundles'], ['prompts', '🤖', 'AI Plans']] as [Tab, string, string][]).map(([t, icon, label]) => (
          <button key={t} onClick={() => setTab(t)}
            className={`flex-1 flex items-center justify-center gap-1.5 py-2 rounded-xl text-xs font-semibold transition-all duration-150 ${
              tab === t ? 'text-white' : 'text-slate-500 hover:text-slate-300'
            }`}
            style={tab === t ? { background: 'linear-gradient(135deg,#2563eb,#7c3aed)' } : { background: 'rgba(30,41,59,0.6)' }}>
            {icon} {label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="p-4 flex flex-col gap-4">

        {tab === 'catalog' && <CoursesPanel />}

        {tab === 'bundles' && (
          <>
            <div className="text-center">
              <h2 className="font-bold text-lg text-slate-100 mb-1" style={{ fontFamily: 'Sora' }}>Course Bundles</h2>
              <p className="text-xs text-slate-500">One payment. Lifetime access. No subscriptions.</p>
            </div>

            {BUNDLES.map((b, i) => (
              <motion.div key={b.tier} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.07 }}
                className="rounded-3xl p-5 border relative overflow-hidden"
                style={{ background: b.gradient, borderColor: b.border }}>

                {b.popular && (
                  <div className="absolute top-0 right-6 text-[10px] font-bold uppercase tracking-wide px-3 py-1 rounded-b-xl text-white"
                    style={{ background: 'linear-gradient(135deg,#7c3aed,#2563eb)' }}>Most Popular</div>
                )}

                <div className="absolute top-4 right-4 text-5xl opacity-10 pointer-events-none select-none">
                  {b.icon === 'logo'
                    ? <img src="/icons/mypytutor_logo.png" alt="" style={{ width: 48, height: 48, borderRadius: '50%', objectFit: 'cover' }} />
                    : b.icon}
                </div>

                <span className="badge text-[10px] mb-3" style={{ background: `${b.accent}20`, color: b.accent, border: `1px solid ${b.border}` }}>
                  {b.badge}
                </span>
                <div className="font-bold text-base text-slate-100 mb-1" style={{ fontFamily: 'Sora' }}>{b.name}</div>
                <div className="text-2xl font-bold mb-1" style={{ color: b.accent, fontFamily: 'Sora' }}>
                  {b.price} <span className="text-xs font-normal text-slate-500">{b.period}</span>
                </div>
                <p className="text-xs text-slate-500 mb-3">{b.desc}</p>
                <ul className="flex flex-col gap-1.5 mb-4">
                  {b.features.map(f => (
                    <li key={f} className="flex items-start gap-2 text-xs text-slate-400">
                      <Check size={12} className="text-green-400 shrink-0 mt-0.5" />{f}
                    </li>
                  ))}
                </ul>
                <a href={b.link} target="_blank" rel="noopener"
                  className="flex items-center justify-center gap-2 w-full py-3 rounded-2xl text-sm font-bold text-white transition-all duration-200 hover:opacity-90"
                  style={{ background: 'linear-gradient(135deg,#2563eb,#7c3aed)' }}>
                  <CreditCard size={14} /> {b.cta} — {b.price}
                </a>
              </motion.div>
            ))}
          </>
        )}

        {tab === 'prompts' && (
          <>
            <div className="text-center">
              <h2 className="font-bold text-lg text-slate-100 mb-1" style={{ fontFamily: 'Sora' }}>AI Chat Plans</h2>
              <p className="text-xs text-slate-500">Separate from course access. Upgrade your daily AI quota.</p>
            </div>

            <div className="rounded-2xl p-3 border border-green-500/25 flex items-center gap-2 text-xs text-green-400"
              style={{ background: 'rgba(34,197,94,0.08)' }}>
              <Zap size={13} />
              <span>Free plan includes <strong>10 AI prompts/day</strong> — resets at 5AM WAT.</span>
            </div>

            {PROMPTS.map((p, i) => (
              <motion.div key={p.badge} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.07 }}
                className="rounded-3xl p-5 border relative"
                style={{ background: p.bg, borderColor: p.border }}>
                {p.popular && (
                  <div className="absolute top-0 right-6 text-[10px] font-bold uppercase tracking-wide px-3 py-1 rounded-b-xl text-white"
                    style={{ background: 'linear-gradient(135deg,#7c3aed,#2563eb)' }}>Best Value</div>
                )}
                <span className="badge text-[10px] mb-3" style={{ background: `${p.accent}15`, color: p.accent, border: `1px solid ${p.border}` }}>
                  {p.badge === 'Unlimited' ? <><Crown size={10} /> {p.badge}</> : <><Star size={10} /> {p.badge}</>}
                </span>
                <div className="font-bold text-base text-slate-100 mb-1" style={{ fontFamily: 'Sora' }}>{p.name}</div>
                <div className="text-2xl font-bold mb-1" style={{ color: p.accent, fontFamily: 'Sora' }}>
                  {p.price}<span className="text-xs font-normal text-slate-500">{p.period}</span>
                </div>
                <p className="text-xs text-slate-500 mb-4">{p.desc}</p>
                <a href={p.link} target="_blank" rel="noopener"
                  className="flex items-center justify-center gap-2 w-full py-3 rounded-2xl text-sm font-bold text-white transition-all duration-200 hover:opacity-90"
                  style={{ background: 'linear-gradient(135deg,#2563eb,#7c3aed)' }}>
                  <CreditCard size={14} /> Subscribe — {p.price}{p.period}
                </a>
              </motion.div>
            ))}

            {/* Payment methods */}
            <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.25 }}
              className="card flex flex-col gap-4">
              <div className="flex items-center gap-2">
                <CreditCard size={16} className="text-blue-400" />
                <span className="font-bold text-sm text-slate-100" style={{ fontFamily: 'Sora' }}>Payment Methods</span>
              </div>

              {/* Bank transfer */}
              <div className="rounded-xl p-4 border border-slate-700/60" style={{ background: '#0f172a' }}>
                <div className="flex items-center gap-2 mb-2">
                  <Building2 size={14} className="text-blue-400" />
                  <span className="text-xs font-bold text-blue-400 uppercase tracking-wide">Bank Transfer</span>
                </div>
                <div className="text-sm text-slate-300 space-y-1">
                  <div><span className="text-slate-500">Bank: </span><strong>Zenith Bank Plc</strong></div>
                  <div><span className="text-slate-500">Name: </span><strong>Teamsamikoko Global Academy</strong></div>
                  <div className="flex items-center gap-2">
                    <span className="text-slate-500">Account: </span>
                    <strong className="text-blue-300 font-mono tracking-wider">1228732577</strong>
                    <button onClick={copyAcct} className="flex items-center gap-1 text-xs text-slate-500 hover:text-slate-300 transition-colors">
                      {copied ? <><Check size={10} className="text-green-400" /> Copied</> : <><Copy size={10} /> Copy</>}
                    </button>
                  </div>
                </div>
              </div>

              <a href={PAYSTACK} target="_blank" rel="noopener"
                className="flex items-center justify-center gap-2 w-full py-3 rounded-2xl text-sm font-bold text-white"
                style={{ background: 'linear-gradient(135deg,#06b6d4,#2563eb)' }}>
                ⚡ Pay Online via Paystack
              </a>
            </motion.div>
          </>
        )}
      </div>
    </div>
  )
}
