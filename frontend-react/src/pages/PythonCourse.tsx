import React from 'react'
import { Link } from 'react-router-dom'

const COURSES = [
  ['bg','Master Python from zero','beginner','14 lessons'],['bg','Master Python strings','beginner','8 lessons'],
  ['bg','Lists, Tuples, Sets & Dicts','beginner','11 lessons'],['bg','If/Else, While, For, Range','beginner','10 lessons'],
  ['int','Functions & Advanced Python','intermediate','12 lessons'],['int','OOP & Design Patterns','intermediate','14 lessons'],
  ['int','Modules & Standard Library','intermediate','10 lessons'],['adv','Data Structures & Algorithms','advanced','18 lessons'],
  ['adv','NumPy Mastery','advanced','16 lessons'],['adv','Pandas Mastery','advanced','14 lessons'],
  ['adv','Data Science with Python','advanced','20 lessons'],['adv','Machine Learning','advanced','30 lessons'],
  ['adv','Web APIs — FastAPI & Flask','advanced','12 lessons'],['adv','AI & Prompt Engineering','advanced','44 lessons'],
]
const LVL: Record<string, { bg: string; color: string }> = {
  bg: { bg: 'rgba(16,185,129,.12)', color: '#6ee7b7' },
  int: { bg: 'rgba(245,158,11,.12)', color: '#fcd34d' },
  adv: { bg: 'rgba(239,68,68,.1)', color: '#fca5a5' },
}

export default function PythonCoursePage() {
  return (
    <div style={{ fontFamily: 'Inter,sans-serif', background: '#0f1117', color: '#e2e8f0', minHeight: '100vh', padding: '60px 24px 40px', maxWidth: 860, margin: '0 auto' }}>
      <div style={{ display: 'inline-block', background: 'rgba(139,92,246,.15)', color: '#c4b5fd', border: '1px solid rgba(139,92,246,.3)', borderRadius: 999, padding: '4px 14px', fontSize: '.8rem', fontWeight: 700, textTransform: 'uppercase', marginBottom: 20 }}>📚 16 Courses Available</div>
      <h1 style={{ fontSize: 'clamp(1.8rem,5vw,2.8rem)', fontWeight: 800, lineHeight: 1.2, marginBottom: 14 }}>Python <span style={{ background: 'linear-gradient(135deg,#a78bfa,#60a5fa)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>Courses</span></h1>
      <p style={{ fontSize: '1rem', color: '#94a3b8', lineHeight: 1.7, marginBottom: 28 }}>Structured learning paths from beginner to AI engineer. All guided by Sir. Tega.</p>
      <div style={{ display: 'flex', gap: 12, justifyContent: 'center', marginBottom: 40 }}>
        <Link to="/" style={{ background: 'linear-gradient(135deg,#6d28d9,#8b5cf6)', color: '#fff', textDecoration: 'none', padding: '13px 30px', borderRadius: 12, fontWeight: 700, fontSize: '.95rem' }}>🚀 Start a Course Free</Link>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(230px,1fr))', gap: 12 }}>
        {COURSES.map(([level, name, , steps]) => (
          <div key={name} style={{ background: '#111827', border: '1px solid #1f2937', borderRadius: 14, padding: 18 }}>
            <span style={{ display: 'inline-block', fontSize: '.65rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '.07em', padding: '2px 8px', borderRadius: 999, marginBottom: 8, ...LVL[level] }}>
              {level === 'bg' ? 'Beginner' : level === 'int' ? 'Intermediate' : 'Advanced'}
            </span>
            <h3 style={{ fontSize: '.9rem', fontWeight: 700, color: '#f1f5f9', marginBottom: 5 }}>{name}</h3>
            <p style={{ fontSize: '.76rem', color: '#64748b' }}>{steps}</p>
          </div>
        ))}
      </div>
      <div style={{ textAlign: 'center', paddingTop: 40 }}><Link to="/" style={{ color: '#60a5fa', textDecoration: 'none', fontSize: '.88rem' }}>← Back to MyPy Tutor</Link></div>
    </div>
  )
}
