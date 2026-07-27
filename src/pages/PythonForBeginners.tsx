import React from 'react'
import { Link } from 'react-router-dom'

export default function BeginnerPage() {
  return (
    <div style={{ fontFamily: 'Inter,sans-serif', background: '#0f1117', color: '#e2e8f0', minHeight: '100vh', padding: '60px 24px 40px', maxWidth: 640, margin: '0 auto' }}>
      <div style={{ display: 'inline-block', background: 'rgba(16,185,129,.12)', color: '#6ee7b7', border: '1px solid rgba(16,185,129,.25)', borderRadius: 999, padding: '4px 14px', fontSize: '.8rem', fontWeight: 700, textTransform: 'uppercase', marginBottom: 20 }}>🟢 Perfect for Beginners</div>
      <h1 style={{ fontSize: 'clamp(1.8rem,5vw,2.8rem)', fontWeight: 800, lineHeight: 1.2, marginBottom: 14 }}>Python for <span style={{ background: 'linear-gradient(135deg,#6ee7b7,#60a5fa)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>Beginners</span></h1>
      <p style={{ fontSize: '1rem', color: '#94a3b8', lineHeight: 1.7, marginBottom: 28 }}>No experience needed. Sir. Tega walks you through every concept step by step.</p>
      <div style={{ marginBottom: 40 }}>
        <Link to="/" style={{ background: 'linear-gradient(135deg,#059669,#10b981)', color: '#fff', textDecoration: 'none', padding: '13px 30px', borderRadius: 12, fontWeight: 700, fontSize: '.95rem' }}>🚀 Start Free — No Card Needed</Link>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        {[['1','Sign up — it\'s free','Create your account in 30 seconds. Get 10 AI questions per day, forever.'],['2','Tell Sir. Tega your goal','Career, data science, or building apps — he\'ll personalise your roadmap.'],['3','Work through the beginner path','Variables → loops → functions → data structures → exceptions. 43 lessons.'],['4','Ask anything, anytime','Stuck? Just ask. Sir. Tega explains it differently until it clicks.'],['5','Earn your Basic Certificate','Complete the curriculum and earn an accredited certificate.']].map(([n, title, desc]) => (
          <div key={n} style={{ background: '#111827', border: '1px solid #1f2937', borderRadius: 14, padding: 18, display: 'flex', gap: 16, alignItems: 'flex-start' }}>
            <div style={{ flexShrink: 0, width: 36, height: 36, background: 'rgba(16,185,129,.15)', border: '1px solid rgba(16,185,129,.3)', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800, fontSize: '.9rem', color: '#6ee7b7' }}>{n}</div>
            <div><h3 style={{ fontSize: '.92rem', fontWeight: 700, color: '#f1f5f9', marginBottom: 4 }}>{title}</h3><p style={{ fontSize: '.78rem', color: '#64748b', lineHeight: 1.5 }}>{desc}</p></div>
          </div>
        ))}
      </div>
      <div style={{ textAlign: 'center', paddingTop: 40 }}><Link to="/" style={{ color: '#60a5fa', textDecoration: 'none', fontSize: '.88rem' }}>← Back to MyPy Tutor</Link></div>
    </div>
  )
}
