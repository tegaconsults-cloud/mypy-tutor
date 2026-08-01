import React, { useState } from 'react'
import { motion } from 'framer-motion'
import { Check, Zap, Crown, Star, CreditCard, Building2, Copy } from 'lucide-react'
import CoursesPanel from './CoursesPanel'

const PAYSTACK = 'https://paystack.shop/pay/vt_re4d3h52'

const BUNDLES = [
  {
    tier: 'tier-1', badge: '🟢 Beginner Bundle', name: 'Python Foundation', price: '₦8,000',
    period: 'one-time', desc: 'All 4 beginner courses bundled.',
    features: ['43 structured lessons + exercises','Per-lesson quizzes & XP','Basic Certificate eligibility','Save ₦3,000 vs individual'],
    cta: 'Buy Beginner Bundle', link: `${PAYSTACK}?plan=beginner+bundle&tier=tier1&amount=8000`,
    gradient: 'linear-gradient(135deg,rgba(13,71,161,0.18),rgba(6,13,28,0.95))', border: 'rgba(13,71,161,0.45)', accent: '#93c5fd',
  },
  {
    tier: 'tier-2', badge: '⚡ Intermediate Bundle', name: '7 Courses', price: '₦15,000', popular: true,
    period: 'one-time', desc: 'Beginner + Functions, OOP, Standard Library.',
    features: ['86 structured lessons','OOP, decorators, generators','Advanced Certificate eligibility','Save ₦9,000 vs individual'],
    cta: 'Buy Intermediate Bundle', link: `${PAYSTACK}?plan=intermediate+bundle&tier=tier2&amount=15000`,
    gradient: 'linear-gradient(135deg,rgba(224,163,0,0.15),rgba(6,13,28,0.95))', border: 'rgba(224,163,0,0.4)', accent: '#E0A300',
  },
  {
    tier: 'tier-3', badge: '👑 Elite Bundle', name: 'ALL 16 Courses', price: '₦35,000',
    period: 'one-time', desc: 'Every course: ML, AI, DSA, Data Science.',
    features: ['Machine Learning (30 lessons)','AI & Prompt Engineering','NumPy, Pandas, Data Science','Executive Masters Certificate','Save ₦55,000 vs individual'],
    cta: 'Buy Elite Bundle', link: `${PAYSTACK}?plan=elite+bundle&tier=tier3&amount=35000`,
    gradient: 'linear-gradient(135deg,rgba(139,92,246,0.18),rgba(6,13,28,0.95))', border: 'rgba(139,92,246,0.4)', accent: '#c4b5fd',
  },
]

const PROMPTS = [
  { badge: 'Starter', name: '50 Prompts / Day', price: '₦2,000', period: '/month', desc: 'Perfect for regular learners.', link: `${PAYSTACK}?plan=prompt+starter&amount=2000`, accent: '#93c5fd', border: 'rgba(13,71,161,0.3)', bg: 'rgba(13,71,161,0.08)' },
  { badge: 'Pro', name: '200 Prompts / Day', price: '₦5,000', period: '/month', desc: 'For serious learners.', popular: true, link: `${PAYSTACK}?plan=prompt+pro&amount=5000`, accent: '#E0A300', border: 'rgba(224,163,0,0.35)', bg: 'rgba(224,163,0,0.08)' },
  { badge: 'Unlimited', name: 'No Daily Cap', price: '₦10,000', period: '/month', desc: '24/7 access, no restrictions.', link: `${PAYSTACK}?plan=prompt+unlimited&amount=10000`, accent: '#c4b5fd', border: 'rgba(139,92,246,0.35)', bg: 'rgba(139,92,246,0.08)' },
]

type Tab = 'catalog' | 'bundles' | 'prompts'

export default function PricingPanel() {
  const [tab, setTab]     = useState<Tab>('bundles')
  const [copied, setCopied] = useState(false)

  const copyAcct = () => {
    navigator.clipboard.writeText('1228732577')
    setCopied(true); setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="flex-1 overflow-y-auto flex flex-col touch-scroll scrollbar-thin">

      {/* Tab bar */}
      <div className="flex gap-1.5 p-3 sticky top-0 z-10"
        style={{ background: 'rgba(6,13,28,0.97)', borderBottom: '1px solid rgba(13,71,161,0.15)', backdropFilter: 'blur(20px)' }}>
        {([['catalog','📚','Catalog'],['bundles','🎯','Bundles'],['prompts','🤖','AI Plans']] as [Tab,string,string][]).map(([t, icon, label]) => (
          <button key={t} onClick={() => setTab(t)}
            className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-xl text-xs font-semibold transition-all duration-150"
            style={tab === t
              ? { background: 'linear-gradient(135deg,#0D47A1,#E0A300)', color: '#fff' }
              : { background: 'rgba(13,71,161,0.08)', color: '#4d6080' }}>
            {icon} {label}
          </button>
        ))}
      </div>

      <div className="p-4 flex flex-col gap-4">

        {tab === 'catalog' && <CoursesPanel />}

        {tab === 'bundles' && (
          <>
            <div className="text-center">
              <h2 className="font-bold text-lg text-white mb-1" style={{ fontFamily: 'Sora' }}>Course Bundles</h2>
              <p className="text-xs" style={{ color: '#4d6080' }}>One payment. Lifetime access. No subscriptions.</p>
            </div>

            {BUNDLES.map((b, i) => (
              <motion.div key={b.tier} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.07 }}
                className="rounded-3xl p-5 border relative overflow-hidden"
                style={{ background: b.gradient, borderColor: b.border }}>
                {b.popular && (
                  <div className="absolute top-0 right-6 text-[10px] font-bold uppercase tracking-wide px-3 py-1 rounded-b-xl text-white"
                    style={{ background: 'linear-gradient(135deg,#0D47A1,#E0A300)' }}>Most Popular</div>
                )}
                <span className="badge text-[10px] mb-3 inline-flex" style={{ background: `${b.accent}18`, color: b.accent, border: `1px solid ${b.border}` }}>
                  {b.badge}
                </span>
                <div className="font-bold text-base text-white mb-1" style={{ fontFamily: 'Sora' }}>{b.name}</div>
                <div className="text-2xl font-bold mb-1" style={{ color: b.accent, fontFamily: 'Sora' }}>
                  {b.price} <span className="text-xs font-normal" style={{ color: '#4d6080' }}>{b.period}</span>
                </div>
                <p className="text-xs mb-3" style={{ color: '#4d6080' }}>{b.desc}</p>
                <ul className="flex flex-col gap-1.5 mb-4">
                  {b.features.map(f => (
                    <li key={f} className="flex items-start gap-2 text-xs" style={{ color: '#94a3b8' }}>
                      <Check size={12} style={{ color: '#86efac', flexShrink: 0, marginTop: 2 }} />{f}
                    </li>
                  ))}
                </ul>
                <a href={b.link} target="_blank" rel="noopener"
                  className="flex items-center justify-center gap-2 w-full py-3 rounded-2xl text-sm font-bold text-white transition-all hover:opacity-90"
                  style={{ background: 'linear-gradient(135deg,#0D47A1,#1565E8)' }}>
                  <CreditCard size={14} /> {b.cta} — {b.price}
                </a>
              </motion.div>
            ))}
          </>
        )}

        {tab === 'prompts' && (
          <>
            <div className="text-center">
              <h2 className="font-bold text-lg text-white mb-1" style={{ fontFamily: 'Sora' }}>AI Chat Plans</h2>
              <p className="text-xs" style={{ color: '#4d6080' }}>Upgrade your daily AI quota. Separate from course access.</p>
            </div>

            <div className="rounded-2xl p-3 border flex items-center gap-2 text-xs"
              style={{ background: 'rgba(34,197,94,0.06)', borderColor: 'rgba(34,197,94,0.25)', color: '#86efac' }}>
              <Zap size={13} />
              <span>Free plan includes <strong>10 AI prompts/day</strong> — resets at 5AM WAT.</span>
            </div>

            {PROMPTS.map((p, i) => (
              <motion.div key={p.badge} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.07 }}
                className="rounded-3xl p-5 border relative"
                style={{ background: p.bg, borderColor: p.border }}>
                {p.popular && (
                  <div className="absolute top-0 right-6 text-[10px] font-bold uppercase tracking-wide px-3 py-1 rounded-b-xl text-white"
                    style={{ background: 'linear-gradient(135deg,#0D47A1,#E0A300)' }}>Best Value</div>
                )}
                <span className="badge text-[10px] mb-3 inline-flex" style={{ background: `${p.accent}15`, color: p.accent, border: `1px solid ${p.border}` }}>
                  {p.badge === 'Unlimited' ? <><Crown size={10} /> {p.badge}</> : <><Star size={10} /> {p.badge}</>}
                </span>
                <div className="font-bold text-base text-white mb-1" style={{ fontFamily: 'Sora' }}>{p.name}</div>
                <div className="text-2xl font-bold mb-1" style={{ color: p.accent, fontFamily: 'Sora' }}>
                  {p.price}<span className="text-xs font-normal" style={{ color: '#4d6080' }}>{p.period}</span>
                </div>
                <p className="text-xs mb-4" style={{ color: '#4d6080' }}>{p.desc}</p>
                <a href={p.link} target="_blank" rel="noopener"
                  className="flex items-center justify-center gap-2 w-full py-3 rounded-2xl text-sm font-bold text-white transition-all hover:opacity-90"
                  style={{ background: 'linear-gradient(135deg,#0D47A1,#1565E8)' }}>
                  <CreditCard size={14} /> Subscribe — {p.price}{p.period}
                </a>
              </motion.div>
            ))}

            {/* Bank transfer */}
            <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.25 }}
              className="card flex flex-col gap-4">
              <div className="flex items-center gap-2">
                <CreditCard size={16} style={{ color: '#93c5fd' }} />
                <span className="font-bold text-sm text-white" style={{ fontFamily: 'Sora' }}>Payment Methods</span>
              </div>
              <div className="rounded-xl p-4 border" style={{ background: '#030810', borderColor: 'rgba(13,71,161,0.2)' }}>
                <div className="flex items-center gap-2 mb-2">
                  <Building2 size={14} style={{ color: '#93c5fd' }} />
                  <span className="text-xs font-bold uppercase tracking-wide" style={{ color: '#93c5fd' }}>Bank Transfer</span>
                </div>
                <div className="text-sm space-y-1" style={{ color: '#94a3b8' }}>
                  <div><span style={{ color: '#4d6080' }}>Bank: </span><strong className="text-white">Zenith Bank Plc</strong></div>
                  <div><span style={{ color: '#4d6080' }}>Name: </span><strong className="text-white">Teamsamikoko Global Academy</strong></div>
                  <div className="flex items-center gap-2">
                    <span style={{ color: '#4d6080' }}>Account: </span>
                    <strong className="font-mono tracking-wider" style={{ color: '#E0A300' }}>1228732577</strong>
                    <button onClick={copyAcct} className="flex items-center gap-1 text-xs transition-colors" style={{ color: '#4d6080' }}>
                      {copied ? <><Check size={10} style={{ color: '#86efac' }} /> Copied</> : <><Copy size={10} /> Copy</>}
                    </button>
                  </div>
                </div>
              </div>
              <a href={PAYSTACK} target="_blank" rel="noopener"
                className="flex items-center justify-center gap-2 w-full py-3 rounded-2xl text-sm font-bold text-white"
                style={{ background: 'linear-gradient(135deg,#0D47A1,#E0A300)' }}>
                ⚡ Pay Online via Paystack
              </a>
            </motion.div>
          </>
        )}
      </div>
    </div>
  )
}
