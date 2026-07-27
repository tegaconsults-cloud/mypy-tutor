import React, { useEffect, useState } from 'react'
import { submitFeedback } from '../api'
import { useAuth } from '../context/AuthContext'

interface Props { onClose: () => void }

export default function FeedbackModal({ onClose }: Props) {
  const { user } = useAuth()
  const [stars, setStars] = useState({ overall: 0, clarity: 0, helpfulness: 0 })
  const [suggestion, setSuggestion] = useState('')
  const [recommend, setRecommend] = useState(true)
  const [sending, setSending] = useState(false)
  const [done, setDone] = useState(false)
  const [err, setErr] = useState('')

  const submit = async () => {
    if (stars.overall === 0) { setErr('Please rate your overall experience.'); return }
    setSending(true); setErr('')
    try {
      await submitFeedback({
        learner_id: user?.learner_id || 'default',
        overall: stars.overall,
        clarity: stars.clarity || stars.overall,
        helpfulness: stars.helpfulness || stars.overall,
        suggestion,
        would_recommend: recommend,
      })
      setDone(true)
      setTimeout(onClose, 3000)
    } catch { setErr('Something went wrong. Please try again.') }
    finally { setSending(false) }
  }

  const StarRow = ({ field, label }: { field: keyof typeof stars; label: string }) => (
    <div>
      <div style={{ fontSize: '.8rem', color: '#718096', marginBottom: 4 }}>{label}{field === 'overall' && <span style={{ color: '#fc8181' }}> *</span>}</div>
      <div style={{ display: 'flex', gap: 6 }}>
        {[1,2,3,4,5].map(v => (
          <button key={v} onClick={() => setStars(s => ({ ...s, [field]: v }))} style={{ background: stars[field] >= v ? '#744210' : '#2d3748', border: 'none', color: stars[field] >= v ? '#f6ad55' : '#718096', fontSize: '1.4rem', cursor: 'pointer', borderRadius: 6, padding: '4px 8px', transition: 'all .12s' }}>⭐</button>
        ))}
      </div>
    </div>
  )

  return (
    <div onClick={e => e.target === e.currentTarget && onClose()} style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)', zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16 }}>
      <div className="slide-in" style={{ background: '#1a202c', border: '1px solid #2d3748', borderRadius: 18, padding: '28px 24px', width: '100%', maxWidth: 420, display: 'flex', flexDirection: 'column', gap: 14, position: 'relative', maxHeight: '90vh', overflowY: 'auto' }}>
        <button onClick={onClose} style={{ position: 'absolute', top: 14, right: 16, background: 'transparent', border: 'none', color: '#718096', fontSize: '1.2rem', cursor: 'pointer' }}>✕</button>
        <h3 style={{ color: '#90cdf4', fontSize: '1rem' }}>💬 Share Your Feedback</h3>
        <p style={{ fontSize: '.8rem', color: '#718096', marginTop: -6 }}>Help us improve MyPy Tutor. Takes 30 seconds.</p>

        {done ? (
          <div style={{ background: 'rgba(39,103,73,.15)', border: '1px solid rgba(39,103,73,.4)', color: '#68d391', borderRadius: 8, padding: '10px 14px', fontSize: '.84rem', textAlign: 'center' }}>
            🙏 Thank you! Your feedback has been sent to our team.
          </div>
        ) : (
          <>
            <StarRow field="overall" label="Overall experience" />
            <StarRow field="clarity" label="Clarity of explanations" />
            <StarRow field="helpfulness" label="How helpful was Sir. Tega?" />
            <div>
              <div style={{ fontSize: '.8rem', color: '#718096', marginBottom: 4 }}>Suggestions or comments (optional)</div>
              <textarea value={suggestion} onChange={e => setSuggestion(e.target.value)} placeholder="What can we improve? What do you love?" rows={3} style={{ resize: 'vertical', minHeight: 80 }} />
            </div>
            <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: '.84rem', color: '#a0aec0', cursor: 'pointer' }}>
              <input type="checkbox" checked={recommend} onChange={e => setRecommend(e.target.checked)} style={{ width: 16, height: 16, accentColor: '#9f7aea' }} />
              I would recommend MyPy Tutor to others
            </label>
            {err && <div style={{ color: '#fc8181', fontSize: '.82rem', textAlign: 'center' }}>{err}</div>}
            <button onClick={submit} disabled={sending} className="btn" style={{ width: '100%', background: '#9f7aea', color: '#fff', minHeight: 46, fontSize: '.93rem' }}>
              {sending ? 'Sending…' : 'Send Feedback'}
            </button>
          </>
        )}
      </div>
    </div>
  )
}
