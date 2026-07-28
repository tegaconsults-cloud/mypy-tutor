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
      setDone(true)
      setTimeout(onClose, 3000)
    } catch { setErr('Something went wrong. Please try again.') }
    finally { setSending(false) }
  }

  const StarRow = ({ field, label }: { field: keyof typeof stars; label: string }) => (
    <div className="flex items-center justify-between">
      <span className="text-xs text-slate-400">{label}{field === 'overall' && <span className="text-red-400 ml-0.5">*</span>}</span>
      <div className="flex gap-1">
        {[1,2,3,4,5].map(v => (
          <button key={v} type="button" onClick={() => setStars(s => ({ ...s, [field]: v }))}
            className={`w-8 h-8 rounded-xl flex items-center justify-center transition-all duration-100 ${
              stars[field] >= v ? 'scale-110' : 'opacity-30 hover:opacity-70'
            }`}
            style={{ color: '#fbbf24' }}>
            <Star size={16} fill={stars[field] >= v ? '#fbbf24' : 'none'} />
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
          style={{ background: '#1e293b', border: '1px solid #334155', boxShadow: '0 25px 80px rgba(0,0,0,.7)' }}>

          <button onClick={onClose} className="absolute top-4 right-4 btn btn-ghost btn-sm w-8 h-8 p-0 rounded-xl">
            <X size={15} />
          </button>

          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl flex items-center justify-center"
              style={{ background: 'rgba(124,58,237,0.2)' }}>
              <Star size={18} className="text-purple-400" />
            </div>
            <div>
              <h3 className="font-bold text-sm text-slate-100" style={{ fontFamily: 'Sora' }}>Share Your Feedback</h3>
              <p className="text-xs text-slate-500">Help us improve MyPy Tutor. Takes 30 seconds.</p>
            </div>
          </div>

          {done ? (
            <motion.div initial={{ scale: 0.9 }} animate={{ scale: 1 }}
              className="flex flex-col items-center gap-3 py-6 text-center">
              <CheckCircle size={40} className="text-green-400" />
              <p className="font-semibold text-slate-100">Thank you! 🙏</p>
              <p className="text-xs text-slate-500">Your feedback has been sent to our team.</p>
            </motion.div>
          ) : (
            <>
              <div className="flex flex-col gap-3">
                <StarRow field="overall"     label="Overall experience" />
                <StarRow field="clarity"     label="Clarity of explanations" />
                <StarRow field="helpfulness" label="How helpful was Sir. Tega?" />
              </div>

              <div>
                <label className="text-xs text-slate-500 block mb-1.5">Suggestions or comments (optional)</label>
                <textarea value={suggestion} onChange={e => setSuggestion(e.target.value)}
                  placeholder="What can we improve? What do you love?" rows={3}
                  className="resize-y" />
              </div>

              <label className="flex items-center gap-3 cursor-pointer">
                <div className={`w-5 h-5 rounded-md border-2 flex items-center justify-center transition-all duration-150 shrink-0 ${
                  recommend ? 'bg-purple-600 border-purple-600' : 'border-slate-600'
                }`} onClick={() => setRecommend(r => !r)}>
                  {recommend && <CheckCircle size={13} className="text-white" />}
                </div>
                <input type="checkbox" checked={recommend} onChange={e => setRecommend(e.target.checked)} className="sr-only" />
                <span className="text-sm text-slate-400">I would recommend MyPy Tutor to others</span>
              </label>

              {err && <p className="text-xs text-red-400 text-center">{err}</p>}

              <button onClick={submit} disabled={sending} className="btn btn-primary w-full"
                style={{ background: 'linear-gradient(135deg,#7c3aed,#2563eb)' }}>
                {sending ? 'Sending…' : <><Send size={14} /> Send Feedback</>}
              </button>
            </>
          )}
        </motion.div>
      </motion.div>
    </AnimatePresence>
  )
}
