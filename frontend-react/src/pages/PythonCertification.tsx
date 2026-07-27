import React from 'react'
import { Link } from 'react-router-dom'

export default function CertificationPage() {
  return (
    <div style={{ fontFamily: 'Inter,sans-serif', background: '#0f1117', color: '#e2e8f0', minHeight: '100vh', padding: '60px 24px 40px', maxWidth: 800, margin: '0 auto' }}>
      <div style={{ display: 'inline-block', background: 'rgba(245,158,11,.12)', color: '#fcd34d', border: '1px solid rgba(245,158,11,.25)', borderRadius: 999, padding: '4px 14px', fontSize: '.8rem', fontWeight: 700, textTransform: 'uppercase', marginBottom: 20 }}>🎓 Accredited Certification</div>
      <h1 style={{ fontSize: 'clamp(1.8rem,5vw,2.8rem)', fontWeight: 800, lineHeight: 1.2, marginBottom: 14 }}>Earn a Python <span style={{ background: 'linear-gradient(135deg,#fcd34d,#f97316)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>Certificate</span></h1>
      <p style={{ fontSize: '1rem', color: '#94a3b8', lineHeight: 1.7, marginBottom: 8 }}>Earn a verifiable certificate from a registered educational institution.</p>
      <div style={{ display: 'inline-block', background: '#111827', border: '1px solid #1f2937', borderRadius: 10, padding: '10px 20px', fontSize: '.82rem', color: '#94a3b8', marginBottom: 28 }}>
        Issued by: <strong style={{ color: '#f1f5f9' }}>Teamsamikoko Global Academy</strong> · Reg No: <strong style={{ color: '#f1f5f9' }}>3508656</strong>
      </div>
      <div style={{ marginBottom: 40 }}>
        <Link to="/" style={{ background: 'linear-gradient(135deg,#b45309,#f59e0b)', color: '#fff', textDecoration: 'none', padding: '13px 30px', borderRadius: 12, fontWeight: 700, fontSize: '.95rem' }}>🎓 Start Your Certificate Path</Link>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(220px,1fr))', gap: 16 }}>
        {[
          { level: 'Basic', bg: 'linear-gradient(140deg,rgba(29,78,216,.15),#111827)', border: 'rgba(59,130,246,.3)', badge: { bg: 'rgba(59,130,246,.15)', color: '#93c5fd', border: 'rgba(59,130,246,.3)' }, desc: '4 beginner courses — fundamentals, strings, collections, control flow.', fee: '₦30,000' },
          { level: 'Advanced', bg: 'linear-gradient(140deg,rgba(109,40,217,.15),#111827)', border: 'rgba(139,92,246,.3)', badge: { bg: 'rgba(139,92,246,.15)', color: '#c4b5fd', border: 'rgba(139,92,246,.3)' }, desc: '7 courses including OOP, algorithms, and REST APIs.', fee: '₦60,000' },
          { level: 'Executive Masters', bg: 'linear-gradient(140deg,rgba(180,83,9,.15),#111827)', border: 'rgba(245,158,11,.3)', badge: { bg: 'rgba(245,158,11,.15)', color: '#fcd34d', border: 'rgba(245,158,11,.3)' }, desc: 'All 16 courses including Machine Learning and AI Engineering.', fee: '₦100,000' },
        ].map(c => (
          <div key={c.level} style={{ background: c.bg, border: `1px solid ${c.border}`, borderRadius: 16, padding: '22px 18px', display: 'flex', flexDirection: 'column', gap: 10 }}>
            <span style={{ display: 'inline-block', fontSize: '.62rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '.1em', padding: '3px 10px', borderRadius: 999, ...c.badge }}>{c.level}</span>
            <p style={{ fontSize: '.77rem', color: '#64748b', lineHeight: 1.55, flex: 1 }}>{c.desc}</p>
            <div style={{ fontSize: '.9rem', fontWeight: 700, color: '#f1f5f9' }}>{c.fee}</div>
          </div>
        ))}
      </div>
      <div style={{ textAlign: 'center', paddingTop: 40 }}><Link to="/" style={{ color: '#60a5fa', textDecoration: 'none', fontSize: '.88rem' }}>← Back to MyPy Tutor</Link></div>
    </div>
  )
}
