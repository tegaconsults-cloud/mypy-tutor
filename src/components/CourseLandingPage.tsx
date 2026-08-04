/**
 * CourseLandingPage — reusable landing page for any individual course.
 * Shows the full module/step list, pricing, and CTA.
 */
import React from 'react'
import { Link } from 'react-router-dom'
import SocialLinks from './SocialLinks'

export interface CourseModule {
  step: number
  title: string
  description: string
  type: 'concept' | 'exercise' | 'quiz' | 'codegen' | 'project'
}

export interface CourseLandingData {
  slug:        string
  title:       string
  tagline:     string
  description: string
  level:       'beginner' | 'intermediate' | 'advanced'
  badge:       string
  price_ngn:   number
  xp_total:    number
  modules:     CourseModule[]
  cert_level?: string  // "basic" | "advanced" | "executive"
  category:    string
}

const LEVEL_COLOR: Record<string, { bg: string; text: string; border: string }> = {
  beginner:     { bg: 'rgba(16,185,129,.12)',  text: '#6ee7b7', border: 'rgba(16,185,129,.3)' },
  intermediate: { bg: 'rgba(245,158,11,.12)',  text: '#fcd34d', border: 'rgba(245,158,11,.3)' },
  advanced:     { bg: 'rgba(239,68,68,.1)',    text: '#fca5a5', border: 'rgba(239,68,68,.3)'  },
}

const TYPE_ICON: Record<string, string> = {
  concept:  '📖',
  exercise: '✏️',
  quiz:     '🎯',
  codegen:  '💻',
  project:  '🚀',
}
const TYPE_LABEL: Record<string, string> = {
  concept:  'Lesson',
  exercise: 'Exercise',
  quiz:     'Quiz',
  codegen:  'Coding',
  project:  'Project',
}

const PAYSTACK = 'https://paystack.shop/pay/vt_re4d3h52'

interface Props { data: CourseLandingData }

export default function CourseLandingPage({ data }: Props) {
  const lc   = LEVEL_COLOR[data.level]
  const href = `${PAYSTACK}?plan=${encodeURIComponent(data.slug)}&amount=${data.price_ngn * 100}`

  return (
    <div style={{
      fontFamily: 'Inter,Segoe UI,sans-serif',
      background: '#0a0f1a',
      color: '#e2e8f0',
      minHeight: '100vh',
    }}>

      {/* Header */}
      <div style={{ background: 'rgba(6,13,28,0.95)', borderBottom: '1px solid rgba(13,71,161,0.25)', padding: '12px 20px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 10, position: 'sticky', top: 0, zIndex: 50, backdropFilter: 'blur(20px)' }}>
        <Link to="/" style={{ display: 'flex', alignItems: 'center', gap: 10, textDecoration: 'none' }}>
          <div style={{ width: 36, height: 36, borderRadius: '50%', overflow: 'hidden', background: '#fff', border: '2px solid rgba(224,163,0,0.5)', flexShrink: 0 }}>
            <img src="/icons/mypytutor_logo.jpg" alt="MyPy Tutor" style={{ width: '100%', height: '100%', objectFit: 'contain' }} />
          </div>
          <div style={{ lineHeight: 1.1 }}>
            <div style={{ fontWeight: 900, fontSize: '0.9rem', color: '#E0A300', letterSpacing: '0.04em' }}>MYPY</div>
            <div style={{ fontWeight: 700, fontSize: '0.65rem', letterSpacing: '0.12em', color: '#60a5fa', textTransform: 'uppercase' }}>TUTOR</div>
          </div>
        </Link>
        <a href={href} target="_blank" rel="noopener noreferrer"
          style={{ background: 'linear-gradient(135deg,#0D47A1,#E0A300)', color: '#fff', textDecoration: 'none', padding: '8px 20px', borderRadius: 10, fontWeight: 700, fontSize: '0.82rem', whiteSpace: 'nowrap' }}>
          Buy Course — ₦{data.price_ngn.toLocaleString()}
        </a>
      </div>

      {/* Hero */}
      <div style={{ padding: 'clamp(32px,5vw,64px) clamp(16px,4vw,40px) 32px', maxWidth: 760, margin: '0 auto' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16, flexWrap: 'wrap' }}>
          <span style={{ background: lc.bg, color: lc.text, border: `1px solid ${lc.border}`, borderRadius: 999, padding: '3px 12px', fontSize: '0.72rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
            {data.level.charAt(0).toUpperCase() + data.level.slice(1)}
          </span>
          <span style={{ background: 'rgba(13,71,161,0.15)', color: '#93c5fd', border: '1px solid rgba(13,71,161,0.3)', borderRadius: 999, padding: '3px 12px', fontSize: '0.72rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
            {data.category}
          </span>
          <span style={{ background: 'rgba(224,163,0,0.12)', color: '#E0A300', border: '1px solid rgba(224,163,0,0.3)', borderRadius: 999, padding: '3px 12px', fontSize: '0.72rem', fontWeight: 700 }}>
            ⚡ {data.xp_total} XP
          </span>
        </div>

        <h1 style={{ fontSize: 'clamp(1.6rem,5vw,2.6rem)', fontWeight: 900, lineHeight: 1.15, marginBottom: 12, letterSpacing: '-0.01em' }}>
          {data.badge} {data.title}
        </h1>
        <p style={{ fontSize: '1rem', color: '#94a3b8', lineHeight: 1.7, marginBottom: 24, maxWidth: 600 }}>
          {data.description}
        </p>

        {/* Stats row */}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 20, marginBottom: 28 }}>
          {[
            ['📚', `${data.modules.length} lessons`],
            ['✏️', `${data.modules.filter(m => m.type === 'exercise').length} exercises`],
            ['🎯', `${data.modules.filter(m => m.type === 'quiz').length} quizzes`],
            ['⏱️', `~${Math.ceil(data.modules.length * 8)} min`],
            ['⚡', `${data.xp_total} XP`],
          ].map(([icon, label]) => (
            <div key={label as string} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.85rem', color: '#64748b' }}>
              <span style={{ fontSize: '1rem' }}>{icon}</span>
              <span>{label}</span>
            </div>
          ))}
        </div>

        {/* CTA */}
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 40 }}>
          <a href={href} target="_blank" rel="noopener noreferrer"
            style={{ background: 'linear-gradient(135deg,#0D47A1,#1565E8)', color: '#fff', textDecoration: 'none', padding: '14px 32px', borderRadius: 12, fontWeight: 700, fontSize: '0.95rem', boxShadow: '0 4px 20px rgba(13,71,161,0.4)', display: 'inline-block' }}>
            💳 Buy — ₦{data.price_ngn.toLocaleString()}
          </a>
          <Link to="/"
            style={{ background: 'rgba(13,71,161,0.12)', color: '#93c5fd', textDecoration: 'none', padding: '14px 28px', borderRadius: 12, fontWeight: 700, fontSize: '0.95rem', border: '1px solid rgba(13,71,161,0.3)', display: 'inline-block' }}>
            🤖 Try Free with Sir. Tega
          </Link>
        </div>

        {data.cert_level && (
          <div style={{ background: 'rgba(16,185,129,.07)', border: '1px solid rgba(16,185,129,.25)', borderRadius: 12, padding: '12px 18px', marginBottom: 32, fontSize: '0.85rem', color: '#6ee7b7' }}>
            🏆 Completing this course counts toward your <strong style={{ color: '#6ee7b7' }}>{data.cert_level.charAt(0).toUpperCase() + data.cert_level.slice(1)} Certificate</strong> from Teamsamikoko Global Academy (Reg No: 3508656)
          </div>
        )}
      </div>

      {/* Module list */}
      <div style={{ maxWidth: 760, margin: '0 auto', padding: '0 clamp(16px,4vw,40px) 60px' }}>
        <h2 style={{ fontSize: '1.1rem', fontWeight: 800, marginBottom: 16, color: '#f1f5f9', letterSpacing: '-0.01em' }}>
          Course Curriculum
        </h2>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {data.modules.map((mod) => (
            <div key={mod.step} style={{
              background: '#0f1a2e',
              border: '1px solid rgba(13,71,161,0.2)',
              borderRadius: 12,
              padding: '14px 18px',
              display: 'flex',
              alignItems: 'flex-start',
              gap: 14,
            }}>
              {/* Step number */}
              <div style={{ flexShrink: 0, width: 32, height: 32, borderRadius: '50%', background: 'rgba(13,71,161,0.2)', border: '1px solid rgba(13,71,161,0.35)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.72rem', fontWeight: 800, color: '#93c5fd', marginTop: 1 }}>
                {mod.step}
              </div>

              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                  <span style={{ fontSize: '0.85rem', fontWeight: 700, color: '#e2e8f0' }}>
                    {mod.title}
                  </span>
                  <span style={{ fontSize: '0.65rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', padding: '1px 7px', borderRadius: 999, background: mod.type === 'exercise' ? 'rgba(139,92,246,.15)' : mod.type === 'quiz' ? 'rgba(224,163,0,.12)' : mod.type === 'codegen' ? 'rgba(34,197,94,.1)' : 'rgba(13,71,161,.15)', color: mod.type === 'exercise' ? '#c4b5fd' : mod.type === 'quiz' ? '#E0A300' : mod.type === 'codegen' ? '#86efac' : '#93c5fd' }}>
                    {TYPE_ICON[mod.type]} {TYPE_LABEL[mod.type]}
                  </span>
                </div>
                <p style={{ fontSize: '0.78rem', color: '#4d6080', marginTop: 3, lineHeight: 1.5 }}>
                  {mod.description}
                </p>
              </div>
            </div>
          ))}
        </div>

        {/* Bottom CTA */}
        <div style={{ marginTop: 40, padding: '28px 24px', background: 'linear-gradient(135deg,rgba(13,71,161,0.15),rgba(6,13,28,0.9))', border: '1px solid rgba(13,71,161,0.35)', borderRadius: 16, textAlign: 'center' }}>
          <h3 style={{ fontSize: '1.2rem', fontWeight: 800, marginBottom: 8, color: '#f1f5f9' }}>
            Ready to start?
          </h3>
          <p style={{ fontSize: '0.85rem', color: '#94a3b8', marginBottom: 20, lineHeight: 1.6 }}>
            Get lifetime access to this course — guided step by step by <strong style={{ color: '#E0A300' }}>Sir. Tega, AI Tutor</strong>.
          </p>
          <div style={{ display: 'flex', gap: 12, justifyContent: 'center', flexWrap: 'wrap' }}>
            <a href={href} target="_blank" rel="noopener noreferrer"
              style={{ background: 'linear-gradient(135deg,#0D47A1,#E0A300)', color: '#fff', textDecoration: 'none', padding: '13px 30px', borderRadius: 12, fontWeight: 700, fontSize: '0.95rem', display: 'inline-block' }}>
              💳 Buy Now — ₦{data.price_ngn.toLocaleString()}
            </a>
            <Link to="/"
              style={{ background: 'rgba(255,255,255,0.06)', color: '#93c5fd', textDecoration: 'none', padding: '13px 24px', borderRadius: 12, fontWeight: 600, fontSize: '0.9rem', border: '1px solid rgba(13,71,161,0.3)', display: 'inline-block' }}>
              ← Back to App
            </Link>
          </div>
        </div>

        {/* Social + Footer */}
        <div style={{ marginTop: 40, paddingTop: 24, borderTop: '1px solid rgba(13,71,161,0.15)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 16 }}>
          <div>
            <SocialLinks />
          </div>
          <div style={{ fontSize: '0.75rem', color: '#4d6080', lineHeight: 1.6, textAlign: 'right' }}>
            <strong style={{ color: '#94a3b8' }}>MyPy Tutor</strong> · Africa's Best AI, Python &amp; ML Tutor<br />
            Powered by TeamTega Technologies Limited<br />
            Certified by Teamsamikoko Global Academy · Reg No: 3508656
          </div>
        </div>
      </div>
    </div>
  )
}
