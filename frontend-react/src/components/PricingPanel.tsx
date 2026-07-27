import React, { useState } from 'react'
import CoursesPanel from './CoursesPanel'

const PAYSTACK = 'https://paystack.shop/pay/vt_re4d3h52'

const BUNDLES = [
  { tier: 'tier-1', badge: 'Beginner Bundle', name: 'All 4 Python Foundation Courses', price: '₦8,000', period: 'one-time', desc: 'Fundamentals · Strings · Collections · Control Flow', features: ['43 structured lessons + exercises', 'Per-lesson quizzes & XP', 'Basic Certificate eligibility', 'Save ₦3,000 vs individual'], cta: '💳 Buy Beginner Bundle — ₦8,000', link: `${PAYSTACK}?plan=beginner+bundle&tier=tier1&amount=8000`, color: '#4299e1' },
  { tier: 'tier-2', badge: 'Intermediate Bundle', name: '7 Courses (Beginner + Intermediate)', price: '₦15,000', period: 'one-time', desc: 'All 4 beginner + Functions, OOP & Standard Library', features: ['86 structured lessons', 'OOP, decorators, generators', 'Advanced Certificate eligibility', 'Save ₦9,000 vs individual'], cta: '💳 Buy Intermediate Bundle — ₦15,000', link: `${PAYSTACK}?plan=intermediate+bundle&tier=tier2&amount=15000`, color: '#9f7aea', popular: true },
  { tier: 'tier-3', badge: 'Elite Bundle', name: 'ALL 16 Courses — Complete Library', price: '₦35,000', period: 'one-time', desc: 'Every course: ML, AI, DSA, Data Science, Web APIs', features: ['Machine Learning (30 lessons)', 'AI & Prompt Engineering', 'NumPy, Pandas, Data Science', 'Executive Masters Certificate', 'Save ₦55,000 vs individual'], cta: '💳 Buy Elite Bundle — ₦35,000', link: `${PAYSTACK}?plan=elite+bundle&tier=tier3&amount=35000`, color: '#f6ad55' },
]

const PROMPTS = [
  { badge: 'Prompt Starter', name: '50 Prompts / Day', price: '₦2,000', period: '/month', desc: 'Perfect for learners who chat regularly.', link: `${PAYSTACK}?plan=prompt+starter&amount=2000`, color: '#3182ce' },
  { badge: 'Prompt Pro', name: '200 Prompts / Day', price: '₦5,000', period: '/month', desc: 'For serious learners who want frequent help.', link: `${PAYSTACK}?plan=prompt+pro&amount=5000`, color: '#9f7aea', popular: true },
  { badge: 'Unlimited', name: 'Unlimited Prompts', price: '₦10,000', period: '/month', desc: 'No cap. 24/7 access to Sir. Tega.', link: `${PAYSTACK}?plan=prompt+unlimited&amount=10000`, color: '#f6ad55' },
]

type Tab = 'catalog' | 'bundles' | 'prompts'

export default function PricingPanel() {
  const [tab, setTab] = useState<Tab>('catalog')

  return (
    <div style={{ overflowY: 'auto', padding: 16, display: 'flex', flexDirection: 'column', gap: 14, WebkitOverflowScrolling: 'touch' }}>
      {/* Tabs */}
      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
        {([['catalog', '📚 Course Catalog'], ['bundles', '🎯 Tier Bundles'], ['prompts', '🤖 AI Chat Plans']] as [Tab, string][]).map(([t, l]) => (
          <button key={t} onClick={() => setTab(t)} style={{
            flex: 1, minWidth: 120, background: tab === t ? '#2b6cb0' : '#1a202c', color: tab === t ? '#fff' : '#a0aec0',
            border: tab === t ? 'none' : '1px solid #2d3748', borderRadius: 8, padding: 10,
            fontSize: '.82rem', fontWeight: 700, cursor: 'pointer', transition: 'all .15s',
          }}>{l}</button>
        ))}
      </div>

      {tab === 'catalog' && <CoursesPanel />}

      {tab === 'bundles' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div style={{ textAlign: 'center' }}>
            <h2 style={{ fontSize: '1.2rem', color: '#e2e8f0', fontWeight: 700 }}>🎯 Course Bundles — Best Value</h2>
            <p style={{ fontSize: '.83rem', color: '#718096', marginTop: 4 }}>One payment unlocks an entire collection. No recurring fees.</p>
          </div>
          {BUNDLES.map(b => (
            <div key={b.tier} style={{ background: '#1a202c', border: `1px solid #2d3748`, borderTop: `3px solid ${b.color}`, borderRadius: 14, padding: '20px 16px', display: 'flex', flexDirection: 'column', gap: 14, position: 'relative' }}>
              {b.popular && <div style={{ position: 'absolute', top: -11, right: 14, background: '#9f7aea', color: '#fff', fontSize: '.65rem', fontWeight: 700, textTransform: 'uppercase', padding: '3px 10px', borderRadius: 999 }}>Most Popular</div>}
              <span style={{ display: 'inline-block', fontSize: '.62rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '.1em', padding: '3px 10px', borderRadius: 999, background: `${b.color}22`, color: b.color, border: `1px solid ${b.color}44` }}>{b.badge}</span>
              <div>
                <div style={{ fontSize: '1.05rem', fontWeight: 700, color: '#e2e8f0' }}>{b.name}</div>
                <div style={{ display: 'flex', alignItems: 'baseline', gap: 4, fontSize: '1.9rem', fontWeight: 800, color: '#e2e8f0', lineHeight: 1, margin: '6px 0 4px' }}>
                  {b.price}<span style={{ fontSize: '.76rem', fontWeight: 400, color: '#718096' }}> {b.period}</span>
                </div>
                <div style={{ fontSize: '.8rem', color: '#718096' }}>{b.desc}</div>
              </div>
              <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: 8, flex: 1 }}>
                {b.features.map(f => <li key={f} style={{ display: 'flex', alignItems: 'flex-start', gap: 8, fontSize: '.83rem', color: '#a0aec0' }}><span style={{ color: '#68d391', flexShrink: 0 }}>✓</span>{f}</li>)}
              </ul>
              <a href={b.link} target="_blank" rel="noopener" style={{ display: 'block', textAlign: 'center', background: b.color === '#4299e1' ? '#2b6cb0' : b.color === '#9f7aea' ? '#6b46c1' : '#c05621', color: '#fff', padding: 12, borderRadius: 10, fontSize: '.9rem', fontWeight: 700, minHeight: 44, lineHeight: '20px', textDecoration: 'none' }}>{b.cta}</a>
            </div>
          ))}
        </div>
      )}

      {tab === 'prompts' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div style={{ textAlign: 'center' }}>
            <h2 style={{ fontSize: '1.2rem', color: '#e2e8f0', fontWeight: 700 }}>🤖 AI Chat Plans</h2>
            <p style={{ fontSize: '.83rem', color: '#718096', marginTop: 4 }}>Buy more daily prompts. Separate from course access.</p>
          </div>
          <div style={{ background: '#1c2a1c', border: '1px solid #276749', borderRadius: 10, padding: '12px 16px', fontSize: '.82rem', color: '#68d391' }}>
            ✅ Free plan includes <strong>10 AI prompts/day</strong> — upgrade for more.
          </div>
          {PROMPTS.map(p => (
            <div key={p.badge} style={{ background: '#1a202c', border: `1px solid ${p.color}44`, borderRadius: 14, padding: '20px 16px', display: 'flex', flexDirection: 'column', gap: 12, position: 'relative' }}>
              {p.popular && <div style={{ position: 'absolute', top: -11, right: 14, background: 'linear-gradient(135deg,#9f7aea,#6d28d9)', color: '#fff', fontSize: '.62rem', fontWeight: 800, textTransform: 'uppercase', padding: '4px 12px', borderRadius: 999 }}>Best Value</div>}
              <span style={{ display: 'inline-block', fontSize: '.62rem', fontWeight: 800, textTransform: 'uppercase', padding: '3px 10px', borderRadius: 999, background: `${p.color}22`, color: p.color, border: `1px solid ${p.color}44` }}>{p.badge}</span>
              <div>
                <div style={{ fontSize: '1.05rem', fontWeight: 700, color: '#e2e8f0' }}>{p.name}</div>
                <div style={{ display: 'flex', alignItems: 'baseline', gap: 4, fontSize: '1.9rem', fontWeight: 800, color: '#e2e8f0', lineHeight: 1, margin: '4px 0' }}>
                  {p.price}<span style={{ fontSize: '.76rem', color: '#718096' }}>{p.period}</span>
                </div>
                <div style={{ fontSize: '.8rem', color: '#718096' }}>{p.desc}</div>
              </div>
              <a href={p.link} target="_blank" rel="noopener" style={{ display: 'block', textAlign: 'center', background: p.color === '#3182ce' ? '#2b6cb0' : p.color === '#9f7aea' ? '#6b46c1' : '#c05621', color: '#fff', padding: 12, borderRadius: 10, fontSize: '.9rem', fontWeight: 700, minHeight: 44, lineHeight: '20px', textDecoration: 'none' }}>
                💳 Subscribe — {p.price}{p.period}
              </a>
            </div>
          ))}

          {/* Payment methods */}
          <div style={{ background: '#1a202c', border: '1px solid #2d3748', borderRadius: 14, padding: 20, display: 'flex', flexDirection: 'column', gap: 14 }}>
            <div style={{ textAlign: 'center', fontWeight: 700, color: '#e2e8f0' }}>💳 Payment Methods</div>
            <div style={{ background: '#0f1117', border: '1px solid #2d3748', borderRadius: 10, padding: 14 }}>
              <div style={{ fontSize: '.78rem', fontWeight: 700, color: '#90cdf4', textTransform: 'uppercase', letterSpacing: '.08em', marginBottom: 8 }}>🏦 Bank Transfer</div>
              <div style={{ fontSize: '.86rem', color: '#e2e8f0', lineHeight: 1.8 }}>
                <span style={{ color: '#718096' }}>Bank:</span> <strong>Zenith Bank Plc</strong><br />
                <span style={{ color: '#718096' }}>Name:</span> <strong>Teamsamikoko Global Academy</strong><br />
                <span style={{ color: '#718096' }}>Account:</span> <strong style={{ color: '#63b3ed', letterSpacing: '.08em' }}>1228732577</strong>
                <button onClick={() => navigator.clipboard.writeText('1228732577')} style={{ marginLeft: 8, background: '#2d3748', color: '#a0aec0', border: 'none', borderRadius: 5, padding: '2px 8px', fontSize: '.72rem', cursor: 'pointer' }}>Copy</button>
              </div>
            </div>
            <div style={{ textAlign: 'center' }}>
              <a href={PAYSTACK} target="_blank" rel="noopener" style={{ display: 'inline-flex', alignItems: 'center', gap: 8, background: '#00c3f7', color: '#fff', textDecoration: 'none', fontWeight: 700, fontSize: '.9rem', padding: '12px 28px', borderRadius: 10 }}>
                ⚡ Pay Online via Paystack
              </a>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
