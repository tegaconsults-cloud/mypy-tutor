import React from 'react'
import { Link } from 'react-router-dom'

const FAQS = [
  ['What is the difference between a list and a tuple?', 'Lists are mutable — you can change, add, or remove elements. Tuples are immutable. Tuples are faster and use less memory, ideal for fixed data.'],
  ['What are decorators in Python?', 'Decorators wrap another function to extend its behaviour without modifying its source code. They use the @decorator_name syntax.'],
  ['Explain deep copy vs shallow copy.', 'A shallow copy creates a new object but references the same nested objects. A deep copy (copy.deepcopy()) creates a fully independent clone.'],
  ['What is a generator and how does it differ from a list?', 'A generator uses yield to produce values lazily, one at a time, without storing them all in memory. Ideal for large datasets.'],
  ['What is the GIL?', 'The Global Interpreter Lock allows only one thread to execute Python bytecode at a time. Use multiprocessing for CPU-bound parallelism.'],
  ['Difference between __str__ and __repr__?', '__str__ is for human-readable output (used by print). __repr__ is for developers and should ideally be unambiguous.'],
]

export default function InterviewPage() {
  return (
    <div style={{ fontFamily: 'Inter,sans-serif', background: '#0f1117', color: '#e2e8f0', minHeight: '100vh', padding: '60px 24px 40px', maxWidth: 720, margin: '0 auto' }}>
      <div style={{ display: 'inline-block', background: 'rgba(239,68,68,.1)', color: '#fca5a5', border: '1px solid rgba(239,68,68,.25)', borderRadius: 999, padding: '4px 14px', fontSize: '.8rem', fontWeight: 700, textTransform: 'uppercase', marginBottom: 20 }}>💼 Interview Prep</div>
      <h1 style={{ fontSize: 'clamp(1.8rem,5vw,2.8rem)', fontWeight: 800, lineHeight: 1.2, marginBottom: 14 }}>Python <span style={{ background: 'linear-gradient(135deg,#fca5a5,#f97316)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>Interview Questions</span></h1>
      <p style={{ fontSize: '1rem', color: '#94a3b8', lineHeight: 1.7, marginBottom: 28 }}>Practice the questions that actually come up. Ask Sir. Tega to explain any concept in detail.</p>
      <div style={{ marginBottom: 40 }}>
        <Link to="/" style={{ background: 'linear-gradient(135deg,#dc2626,#ef4444)', color: '#fff', textDecoration: 'none', padding: '13px 30px', borderRadius: 12, fontWeight: 700, fontSize: '.95rem' }}>🎯 Practice with Sir. Tega</Link>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {FAQS.map(([q, a]) => (
          <div key={q} style={{ background: '#111827', border: '1px solid #1f2937', borderRadius: 14, padding: 20 }}>
            <h3 style={{ fontSize: '.9rem', fontWeight: 700, color: '#f1f5f9', marginBottom: 8 }}>{q}</h3>
            <p style={{ fontSize: '.8rem', color: '#94a3b8', lineHeight: 1.65 }}>{a}</p>
          </div>
        ))}
      </div>
      <div style={{ background: 'rgba(59,130,246,.06)', border: '1px solid rgba(59,130,246,.2)', borderRadius: 14, padding: 20, textAlign: 'center', marginTop: 20 }}>
        <p style={{ fontSize: '.88rem', color: '#94a3b8', lineHeight: 1.6, marginBottom: 14 }}>Want more? Ask Sir. Tega any interview question — instant explanations and quiz on the spot.</p>
        <Link to="/" style={{ background: 'linear-gradient(135deg,#3b82f6,#8b5cf6)', color: '#fff', textDecoration: 'none', padding: '11px 26px', borderRadius: 10, fontWeight: 700, fontSize: '.88rem' }}>💬 Ask Sir. Tega Now →</Link>
      </div>
      <div style={{ textAlign: 'center', paddingTop: 40 }}><Link to="/" style={{ color: '#60a5fa', textDecoration: 'none', fontSize: '.88rem' }}>← Back to MyPy Tutor</Link></div>
    </div>
  )
}
