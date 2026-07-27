import React from 'react'
import { Link } from 'react-router-dom'

const TOPICS = ['Variables','Loops','Functions','OOP','Decorators','Generators','List Comprehension','Exception Handling','File I/O','Regular Expressions','NumPy','Pandas','Data Structures','Algorithms','Sorting','Recursion','Machine Learning','Flask','FastAPI','REST APIs','Threading','Async/Await','Type Hints','Metaclasses']

export default function QuizzesPage() {
  return (
    <div style={{ fontFamily: 'Inter,sans-serif', background: '#0f1117', color: '#e2e8f0', minHeight: '100vh', padding: '60px 24px 40px', maxWidth: 720, margin: '0 auto' }}>
      <div style={{ display: 'inline-block', background: 'rgba(245,158,11,.12)', color: '#fcd34d', border: '1px solid rgba(245,158,11,.25)', borderRadius: 999, padding: '4px 14px', fontSize: '.8rem', fontWeight: 700, textTransform: 'uppercase', marginBottom: 20 }}>🏆 40+ Quiz Topics</div>
      <h1 style={{ fontSize: 'clamp(1.8rem,5vw,2.8rem)', fontWeight: 800, lineHeight: 1.2, marginBottom: 14 }}>Python <span style={{ background: 'linear-gradient(135deg,#fcd34d,#f97316)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>Quizzes</span></h1>
      <p style={{ fontSize: '1rem', color: '#94a3b8', lineHeight: 1.7, marginBottom: 28 }}>AI-generated questions tailored to your level. Get instant explanations after every answer.</p>
      <div style={{ marginBottom: 40 }}>
        <Link to="/?panel=quiz" style={{ background: 'linear-gradient(135deg,#b45309,#f59e0b)', color: '#fff', textDecoration: 'none', padding: '13px 30px', borderRadius: 12, fontWeight: 700, fontSize: '.95rem' }}>🏆 Start a Quiz Now</Link>
      </div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 32 }}>
        {TOPICS.map(t => (
          <span key={t} style={{ background: '#111827', border: '1px solid #1f2937', borderRadius: 999, padding: '7px 16px', fontSize: '.8rem', color: '#94a3b8' }}>{t}</span>
        ))}
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(180px,1fr))', gap: 12, marginBottom: 20 }}>
        {[['🎯','Pick a topic','Sir. Tega generates a fresh question each time.'],['✅','Submit your answer','Instant feedback — correct answer + explanation.'],['📊','Track gaps','Weak topics are flagged for targeted practice.'],['⚡','Earn XP','Every quiz earns XP toward levelling up.']].map(([icon,title,desc]) => (
          <div key={title} style={{ background: '#111827', border: '1px solid #1f2937', borderRadius: 12, padding: 16, textAlign: 'center' }}>
            <div style={{ fontSize: '1.6rem', marginBottom: 8 }}>{icon}</div>
            <p style={{ fontSize: '.77rem', color: '#64748b', lineHeight: 1.5 }}>{desc}</p>
          </div>
        ))}
      </div>
      <div style={{ textAlign: 'center', paddingTop: 20 }}><Link to="/" style={{ color: '#60a5fa', textDecoration: 'none', fontSize: '.88rem' }}>← Back to MyPy Tutor</Link></div>
    </div>
  )
}
