import React from 'react'
import { Link } from 'react-router-dom'

export default function AiTutorPage() {
  return (
    <div style={{ fontFamily: 'Inter,sans-serif', background: '#0f1117', color: '#e2e8f0', minHeight: '100vh', padding: '60px 24px 40px', maxWidth: 800, margin: '0 auto' }}>
      <div style={{ display: 'inline-block', background: 'rgba(6,182,212,.12)', color: '#67e8f9', border: '1px solid rgba(6,182,212,.25)', borderRadius: 999, padding: '4px 14px', fontSize: '.8rem', fontWeight: 700, textTransform: 'uppercase', marginBottom: 20 }}>🤖 Powered by Groq AI</div>
      <h1 style={{ fontSize: 'clamp(1.8rem,5vw,2.8rem)', fontWeight: 800, lineHeight: 1.2, marginBottom: 14 }}>Your Personal <span style={{ background: 'linear-gradient(135deg,#67e8f9,#a78bfa)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>AI Python Tutor</span></h1>
      <p style={{ fontSize: '1rem', color: '#94a3b8', lineHeight: 1.7, marginBottom: 28 }}>Sir. Tega adapts to your level, remembers your gaps, and explains things until they click.</p>
      <div style={{ marginBottom: 40 }}>
        <Link to="/" style={{ background: 'linear-gradient(135deg,#0891b2,#06b6d4)', color: '#fff', textDecoration: 'none', padding: '13px 30px', borderRadius: 12, fontWeight: 700, fontSize: '.95rem' }}>💬 Chat with Sir. Tega Free</Link>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(220px,1fr))', gap: 14 }}>
        {[['💡','Concept Explanations','Clear, level-appropriate explanations with real code examples.'],['🐛','Debug Your Code','Paste your code and Sir. Tega finds and explains the bug.'],['⚙️','Code Generation','Write functions, classes, or full scripts — production quality.'],['🏆','Quizzes on Demand','Ask for a quiz on any topic. Get instant feedback.'],['📊','Gap Detection','Sir. Tega tracks weak topics and offers targeted practice.'],['⚡','Always Available','24/7, on any device, 10 free questions per day.']].map(([icon,title,desc]) => (
          <div key={title} style={{ background: '#111827', border: '1px solid #1f2937', borderRadius: 14, padding: 20 }}>
            <div style={{ fontSize: '1.8rem', marginBottom: 10 }}>{icon}</div>
            <h3 style={{ fontSize: '.9rem', fontWeight: 700, color: '#f1f5f9', marginBottom: 6 }}>{title}</h3>
            <p style={{ fontSize: '.77rem', color: '#64748b', lineHeight: 1.55 }}>{desc}</p>
          </div>
        ))}
      </div>
      <div style={{ textAlign: 'center', paddingTop: 40 }}><Link to="/" style={{ color: '#60a5fa', textDecoration: 'none', fontSize: '.88rem' }}>← Back to MyPy Tutor</Link></div>
    </div>
  )
}
