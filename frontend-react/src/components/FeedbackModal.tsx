import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, Star, Send, CheckCircle } from 'lucide-react'
import { submitFeedback } from '../api'
import { useAuth } from '../context/AuthContext'

interface Props { onClose: () => void }

export default function FeedbackModal({ onClose }: Props) {
  const { user } = useAuth()
  const [stars, setStars]   = useState({ overall: 0, clarity: 0, helpfulness: 0 })
  const [suggestion, setSuggestion] = useState('')
  const [recommend, setRecommend]   = useState(true)
  const [sending, setSending] = useState(false)
  const [done, setDone]       = useState(false)
  const [err, setErr]         = useState('')

  const submit = async () => {
    if (stars.overall === 0) { setErr('Please rate your overall experience.'); return }
    setSending(true); setErr('')
    try {
      await submitFeedback({
        learner_id: user?.learner_id || 'default',
        overall: stars.overall, clarity: stars.clarity || stars.overall,
        helpfulness: stars.helpfulness || stars.overall,
        suggestion, would_recommend: recommend,
      })
      setDone(true); setTimeout(onClose, 3000)
    } catch { setErr('Something went wrong. Please try again.') }
    finally { setSending(false) }
  }

  const StarRow = ({ field, label }: { field: keyof typeof stars; label: string }) => (
    <div className="flex items-center justify-between">
      <span className="text-xs" style={{ color: '#94a3b8' }}>{label}{field === 'overall' && <span style={{ color: '#fca5a5' }}> *</span>}</span>
      <div className="flex gap-1">
        {[1,2,3,4,5].map(v => (
          <button key={v} type="button" onClick={() => setStars(s => ({ ...s, [field]: v }))}
            className="w-8 h-8 rounded-xl flex items-center justify-center transition-all duration-100"
            style={{ color: '#E0A300', transform: stars[field] >= v ? 'scale(1.1)' : 'scale(1)', opacity: stars[field] >= v ? 1 : 0.3 }}>
            <Star size={16} fill={stars[field] >= v ? '#E0A300' : 'none'} />
          </button>
        ))}
      </div>
    </div>
  )

  return (
    <AnimatePresence>
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
        onClick={e => e.target === e.currentTarget && onClose()}
        className="glass-overlay flex items-center justify-center p-4">

        <motion.div initial={{ opacity: 0, scale: 0.95, y: 16 }} animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95 }} transition={{ type: 'spring', stiffness: 400, damping: 30 }}
          className="w-full max-w-md rounded-3xl p-6 relative flex flex-col gap-4"
          style={{ background: '#0f1a2e', border: '1px solid rgba(13,71,161,0.4)', boxShadow: '0 25px 80px rgba(0,0,0,.8)' }}>

          <button onClick={onClose} className="absolute top-4 right-4 btn btn-ghost btn-sm w-8 h-8 p-0 rounded-xl">
            <X size={15} />
          </button>

          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl flex items-center justify-center"
              style={{ background: 'rgba(13,71,161,0.2)' }}>
              <Star size={18} style={{ color: '#E0A300' }} />
            </div>
            <div>
              <h3 className="font-bold text-sm text-white" style={{ fontFamily: 'Sora' }}>Share Your Feedback</h3>
              <p className="text-xs" style={{ color: '#4d6080' }}>Help us improve MyPy Tutor. Takes 30 seconds.</p>
            </div>
          </div>

          {done ? (
            <motion.div initial={{ scale: 0.9 }} animate={{ scale: 1 }}
              className="flex flex-col items-center gap-3 py-6 text-center">
              <CheckCircle size={40} style={{ color: '#86efac' }} />
              <p className="font-semibold text-white">Thank you! 🙏</p>
              <p className="text-xs" style={{ color: '#4d6080' }}>Your feedback has been sent to our team.</p>
            </motion.div>
          ) : (
            <>
              <div className="flex flex-col gap-3">
                <StarRow field="overall"     label="Overall experience" />
                <StarRow field="clarity"     label="Clarity of explanations" />
                <StarRow field="helpfulness" label="How helpful was Sir. Tega?" />
              </div>
              <div>
                <label className="text-xs block mb-1.5" style={{ color: '#4d6080' }}>Suggestions or comments (optional)</label>
                <textarea value={suggestion} onChange={e => setSuggestion(e.target.value)}
                  placeholder="What can we improve? What do you love?" rows={3}
                  className="resize-y" style={{ background: 'rgba(6,13,28,0.8)', borderColor: 'rgba(13,71,161,0.3)' }} />
              </div>
              <label className="flex items-center gap-3 cursor-pointer">
                <div className="w-5 h-5 rounded-md border-2 flex items-center justify-center transition-all shrink-0"
                  style={{ background: recommend ? '#0D47A1' : 'transparent', borderColor: recommend ? '#0D47A1' : '#334155' }}
                  onClick={() => setRecommend(r => !r)}>
                  {recommend && <CheckCircle size={13} className="text-white" />}
                </div>
                <input type="checkbox" checked={recommend} onChange={e => setRecommend(e.target.checked)} className="sr-only" />
                <span className="text-sm" style={{ color: '#94a3b8' }}>I would recommend MyPy Tutor to others</span>
              </label>
              {err && <p className="text-xs text-center" style={{ color: '#fca5a5' }}>{err}</p>}
              <button onClick={submit} disabled={sending} className="btn btn-primary w-full"
                style={{ background: 'linear-gradient(135deg,#0D47A1,#E0A300)' }}>
                {sending ? 'Sending…' : <><Send size={14} /> Send Feedback</>}
              </button>
            </>
          )}
        </motion.div>
      </motion.div>
    </AnimatePresence>
  )
}
