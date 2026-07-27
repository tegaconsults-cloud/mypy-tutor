import React, { useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { useProgress } from '../context/ProgressContext'
import { API_BASE } from '../api'

const CERT_TRACKS = {
  basic:     { courses: ['python-fundamentals','python-strings','python-collections','python-control-flow'], label: 'Basic Certificate', fee: '₦30,000' },
  advanced:  { courses: ['python-fundamentals','python-strings','python-collections','python-control-flow','python-functions-advanced','python-oop','python-modules-stdlib'], label: 'Advanced Certificate', fee: '₦60,000' },
  executive: { courses: ['python-fundamentals','python-strings','python-collections','python-control-flow','python-functions-advanced','python-oop','python-modules-stdlib','python-dsa','numpy-mastery','pandas-mastery','data-science-python','machine-learning'], label: 'Executive Masters', fee: '₦100,000' },
}

const CERT_STYLES = {
  basic:     { bg: 'linear-gradient(135deg,#1a2a5e,#1a202c)', border: '#3182ce', badge: { bg: '#1a365d', color: '#63b3ed' }, btn: '#63b3ed' },
  advanced:  { bg: 'linear-gradient(135deg,#2d1a5e,#1a202c)', border: '#9f7aea', badge: { bg: '#322659', color: '#b794f4' }, btn: '#b794f4' },
  executive: { bg: 'linear-gradient(135deg,#5e3a00,#1a202c)', border: '#f6ad55', badge: { bg: '#7b3a00', color: '#f6ad55' }, btn: '#f6ad55' },
}

export default function CertificatesPanel() {
  const { user } = useAuth()
  const { progress } = useProgress()
  const [name, setName] = useState(user?.name || '')

  const completed = new Set(progress?.completed_projects || [])
  const learnerId = user?.learner_id || 'default'

  const preview = (level: string) => {
    const certName = name.trim() || 'Learner'
    const url = `${API_BASE}/certificate/${level}?name=${encodeURIComponent(certName)}&learner_id=${encodeURIComponent(learnerId)}`
    window.open(url, '_blank', 'width=1000,height=720,noopener,noreferrer')
  }

  return (
    <div style={{ overflowY: 'auto', padding: 20, display: 'flex', flexDirection: 'column', gap: 18, WebkitOverflowScrolling: 'touch' }}>
      <h3 style={{ color: '#90cdf4', fontSize: '.97rem' }}>🎓 Your Certificates</h3>

      <div style={{ background: '#1a202c', border: '1px solid #2d3748', borderRadius: 10, padding: 14, fontSize: '.82rem', color: '#a0aec0', lineHeight: 1.6 }}>
        <strong style={{ color: '#e2e8f0' }}>Issued by:</strong> Teamsamikoko Global Academy &nbsp;·&nbsp;
        <strong style={{ color: '#e2e8f0' }}>Reg No:</strong> 3508656 &nbsp;·&nbsp;
        <strong style={{ color: '#e2e8f0' }}>Est:</strong> 2021
        <br />Enter your full name for the certificate, then click Preview.
      </div>

      <div>
        <label style={{ fontSize: '.8rem', color: '#718096', display: 'block', marginBottom: 6 }}>Your full name for the certificate:</label>
        <input value={name} onChange={e => setName(e.target.value)} placeholder="e.g. Adaora Chukwuemeka" maxLength={80} style={{ height: 42 }} />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 16 }}>
        {(Object.entries(CERT_TRACKS) as [keyof typeof CERT_TRACKS, typeof CERT_TRACKS['basic']][]).map(([level, track]) => {
          const done = track.courses.filter(c => completed.has(c)).length
          const total = track.courses.length
          const pct = Math.round((done / total) * 100)
          const isReady = done === total
          const styles = CERT_STYLES[level]

          return (
            <div key={level} style={{ background: styles.bg, border: `2px solid ${styles.border}`, borderRadius: 14, padding: '22px 18px', display: 'flex', flexDirection: 'column', gap: 12 }}>
              <span style={{ display: 'inline-block', fontSize: '.65rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '.14em', padding: '3px 12px', borderRadius: 999, background: styles.badge.bg, color: styles.badge.color }}>{level === 'executive' ? 'Executive Masters' : level.charAt(0).toUpperCase() + level.slice(1)}</span>

              <div style={{ fontSize: '1.05rem', fontWeight: 700, color: '#e2e8f0' }}>
                {level === 'basic' ? 'Certificate of Completion' : level === 'advanced' ? 'Certificate of Achievement' : 'Executive Masters Certificate'}
              </div>

              <div style={{ fontSize: '.78rem', color: '#a0aec0', lineHeight: 1.5, flex: 1 }}>
                {level === 'basic' ? 'Foundational Python — syntax, data structures, loops, functions.' : level === 'advanced' ? 'OOP, algorithms, REST APIs, design patterns.' : 'ML, AI engineering, data science, prompt engineering.'}
              </div>

              <div style={{ fontSize: '.9rem', fontWeight: 700, color: '#e2e8f0' }}>{track.fee}</div>

              {/* Progress */}
              <div>
                <div style={{ fontSize: '.75rem', color: isReady ? '#68d391' : '#94a3b8', marginBottom: 4, fontWeight: 600 }}>
                  {isReady ? '✅ Ready to claim!' : `📚 ${done}/${total} courses (${pct}%)`}
                </div>
                <div style={{ height: 5, background: '#1f2937', borderRadius: 99, overflow: 'hidden' }}>
                  <div style={{ height: '100%', width: `${pct}%`, background: isReady ? '#34d399' : styles.border, borderRadius: 99, transition: 'width .5s' }} />
                </div>
              </div>

              <button onClick={() => preview(level)} style={{ background: 'transparent', border: `1px solid ${styles.btn}`, color: styles.btn, borderRadius: 8, padding: '9px 14px', fontSize: '.84rem', fontWeight: 600, cursor: 'pointer', minHeight: 40, width: '100%', transition: 'opacity .15s' }} onMouseOver={e => (e.currentTarget.style.opacity = '.8')} onMouseOut={e => (e.currentTarget.style.opacity = '1')}>
                🎓 Preview {level === 'executive' ? 'Executive' : level.charAt(0).toUpperCase() + level.slice(1)} Certificate
              </button>
            </div>
          )
        })}
      </div>

      <div style={{ background: '#1a202c', border: '1px solid #2d3748', borderRadius: 10, padding: 14, fontSize: '.75rem', color: '#4a5568' }}>
        💡 Certificates open in a new tab. Use <strong style={{ color: '#718096' }}>Print → Save as PDF</strong> to download.
      </div>
    </div>
  )
}
