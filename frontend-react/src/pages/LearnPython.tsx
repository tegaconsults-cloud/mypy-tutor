import React from 'react'
import { Link } from 'react-router-dom'

export default function LearnPythonPage() {
  return (
    <div style={{ fontFamily: 'Inter, sans-serif', background: '#0f1117', color: '#e2e8f0', minHeight: '100vh', padding: '60px 24px 40px', maxWidth: 800, margin: '0 auto' }}>
      <div style={{ display: 'inline-block', background: 'rgba(59,130,246,.15)', color: '#93c5fd', border: '1px solid rgba(59,130,246,.3)', borderRadius: 999, padding: '4px 14px', fontSize: '.8rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '.08em', marginBottom: 20 }}>🐍 AI-Powered Python Learning</div>
      <h1 style={{ fontSize: 'clamp(1.8rem,5vw,3rem)', fontWeight: 800, lineHeight: 1.2, marginBottom: 16 }}>Learn <span style={{ background: 'linear-gradient(135deg,#60a5fa,#a78bfa)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>Python</span> with Your AI Tutor</h1>
      <p style={{ fontSize: '1.05rem', color: '#94a3b8', lineHeight: 1.7, maxWidth: 600, marginBottom: 32 }}>MyPy Tutor teaches Python through real conversations, interactive exercises, and instant feedback — 24/7.</p>
      <div style={{ display: 'flex', gap: 12, justifyContent: 'center', flexWrap: 'wrap', marginBottom: 48 }}>
        <Link to="/" style={{ background: 'linear-gradient(135deg,#3b82f6,#8b5cf6)', color: '#fff', textDecoration: 'none', padding: '14px 32px', borderRadius: 12, fontWeight: 700, fontSize: '1rem' }}>🚀 Start Learning Free</Link>
        <Link to="/python-course" style={{ background: 'transparent', color: '#94a3b8', border: '1px solid #374151', textDecoration: 'none', padding: '14px 28px', borderRadius: 12, fontWeight: 600, fontSize: '.95rem' }}>Browse Courses →</Link>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(200px,1fr))', gap: 16 }}>
        {[['🤖','AI Tutor','Instant, personalised explanations adapted to your level.'],['📚','16 Courses','From Python basics to ML and AI Engineering.'],['🏆','Quizzes & XP','Test knowledge, earn XP, unlock badges.'],['🎓','Certificates','Accredited by Teamsamikoko Global Academy.'],['⚡','Free to Start','10 AI prompts/day, no credit card.'],['📱','Works Everywhere','PWA — install on any device.']].map(([icon,title,desc]) => (
          <div key={title} style={{ background: '#111827', border: '1px solid #1f2937', borderRadius: 14, padding: 20, textAlign: 'center' }}>
            <div style={{ fontSize: '2rem', marginBottom: 10 }}>{icon}</div>
            <h3 style={{ fontSize: '.92rem', fontWeight: 700, color: '#f1f5f9', marginBottom: 6 }}>{title}</h3>
            <p style={{ fontSize: '.78rem', color: '#64748b', lineHeight: 1.55 }}>{desc}</p>
          </div>
        ))}
      </div>
      <div style={{ textAlign: 'center', paddingTop: 40 }}><Link to="/" style={{ color: '#60a5fa', textDecoration: 'none', fontSize: '.88rem' }}>← Back to MyPy Tutor</Link></div>
    </div>
  )
}
