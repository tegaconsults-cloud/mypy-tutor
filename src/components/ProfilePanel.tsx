import React, { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { User, MapPin, Globe, Lock, Camera, LogOut, ExternalLink, Mail } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { getProfile, saveProfile, forgotPassword, API_BASE } from '../api'

export default function ProfilePanel() {
  const { user, signOut } = useAuth()
  const [name,     setName]     = useState('')
  const [bio,      setBio]      = useState('')
  const [location, setLocation] = useState('')
  const [website,  setWebsite]  = useState('')
  const [photoUrl, setPhotoUrl] = useState('')
  const [saving,   setSaving]   = useState(false)
  const [msg,      setMsg]      = useState('')
  const [pwMsg,    setPwMsg]    = useState('')
  const [invoices, setInvoices] = useState<{id:string;plan:string;amount:number}[]>([])

  const lid      = user?.learner_id || 'default'
  const isGoogle = localStorage.getItem('mpt_auth_type') === 'google'

  useEffect(() => {
    if (!user) return
    setName(user.name || ''); setPhotoUrl(user.picture || '')
    getProfile(lid).then(d => {
      if (!d) return
      setName(d.display_name || user.name || '')
      setBio(d.bio || ''); setLocation(d.location || '')
      setWebsite(d.website || '')
      setPhotoUrl(d.photo_url || user.picture || '')
    })
    fetch(`${API_BASE}/invoices/${lid}`).then(r => r.ok ? r.json() : null).then(d => {
      if (d?.invoices) setInvoices(d.invoices)
    }).catch(() => {})
  }, [user])

  const save = async () => {
    setSaving(true); setMsg('')
    const ws = website && !website.startsWith('http') ? 'https://' + website : website
    try {
      await saveProfile(lid, { display_name: name, bio, location, website: ws, photo_url: photoUrl })
      setMsg('✅ Profile saved!')
    } catch { setMsg('❌ Save failed.') }
    finally { setSaving(false) }
  }

  const handlePhotoUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]; if (!file) return
    if (file.size > 2 * 1024 * 1024) { setMsg('Photo must be under 2 MB.'); return }
    const reader = new FileReader()
    reader.onload = ev => setPhotoUrl(ev.target?.result as string)
    reader.readAsDataURL(file)
  }

  const sendPasswordReset = async () => {
    if (isGoogle) { setPwMsg('Google accounts — change at myaccount.google.com'); return }
    const email = localStorage.getItem('mpt_user_email') || user?.email || ''
    if (!email) { setPwMsg('Could not find account email.'); return }
    try { await forgotPassword(email); setPwMsg(`✅ Reset link sent to ${email}`) }
    catch { setPwMsg('❌ Network error') }
  }

  if (!user) return (
    <div className="flex-1 flex items-center justify-center p-8 text-center">
      <div>
        <User size={40} className="mx-auto mb-3" style={{ color: '#4d6080' }} />
        <p className="text-sm" style={{ color: '#4d6080' }}>Sign in to view your profile.</p>
      </div>
    </div>
  )

  const initials = (user.name || 'U').split(' ').map(w => w[0]).slice(0, 2).join('').toUpperCase()
  const inputStyle = { background: 'rgba(6,13,28,0.8)', borderColor: 'rgba(13,71,161,0.3)' }

  return (
    <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-4 touch-scroll scrollbar-thin max-w-xl mx-auto w-full">

      {/* Avatar */}
      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="card">
        <div className="flex items-center gap-4">
          <label className="relative cursor-pointer shrink-0 group">
            <div className="w-16 h-16 rounded-2xl overflow-hidden flex items-center justify-center font-bold text-xl text-white"
              style={{ background: 'linear-gradient(135deg,#0D47A1,#E0A300)' }}>
              {photoUrl ? <img src={photoUrl} alt="" className="w-full h-full object-cover" /> : initials}
            </div>
            <div className="absolute inset-0 bg-black/50 rounded-2xl flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
              <Camera size={16} className="text-white" />
            </div>
            <input type="file" accept="image/*" onChange={handlePhotoUpload} className="sr-only" />
          </label>
          <div className="flex-1 min-w-0">
            <div className="font-bold text-base text-white truncate">{name || user.email.split('@')[0]}</div>
            <div className="text-xs truncate" style={{ color: '#4d6080' }}>{user.email}</div>
            <span className="badge badge-navy text-[10px] mt-1.5">Free Plan</span>
          </div>
          <button onClick={signOut} className="btn btn-danger btn-sm shrink-0">
            <LogOut size={13} /> Sign Out
          </button>
        </div>
      </motion.div>

      {/* Edit Profile */}
      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }}
        className="card flex flex-col gap-4">
        <div className="flex items-center gap-2">
          <User size={15} style={{ color: '#93c5fd' }} />
          <h3 className="font-bold text-sm text-white" style={{ fontFamily: 'Sora' }}>Edit Profile</h3>
        </div>
        <div>
          <label className="text-[10px] font-bold uppercase tracking-widest block mb-1.5" style={{ color: '#4d6080' }}>Display Name</label>
          <input value={name} onChange={e => setName(e.target.value)} placeholder="How should we call you?" maxLength={80} className="h-11" style={inputStyle} />
        </div>
        <div>
          <label className="text-[10px] font-bold uppercase tracking-widest block mb-1.5" style={{ color: '#4d6080' }}>Bio</label>
          <textarea value={bio} onChange={e => setBio(e.target.value)} placeholder="A short bio…" maxLength={500} rows={3}
            className="resize-y" style={{ ...inputStyle, lineHeight: 1.6 }} />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-[10px] font-bold uppercase tracking-widest block mb-1.5" style={{ color: '#4d6080' }}>Location</label>
            <div className="relative">
              <MapPin size={13} className="absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" style={{ color: '#4d6080' }} />
              <input value={location} onChange={e => setLocation(e.target.value)} placeholder="Lagos, Nigeria" maxLength={100} className="pl-8 h-11" style={inputStyle} />
            </div>
          </div>
          <div>
            <label className="text-[10px] font-bold uppercase tracking-widest block mb-1.5" style={{ color: '#4d6080' }}>Website</label>
            <div className="relative">
              <Globe size={13} className="absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" style={{ color: '#4d6080' }} />
              <input value={website} onChange={e => setWebsite(e.target.value)} placeholder="https://…" maxLength={200} type="url" className="pl-8 h-11" style={inputStyle} />
            </div>
          </div>
        </div>
        {msg && (
          <div className="text-xs text-center py-2 px-3 rounded-xl"
            style={{ background: msg.startsWith('✅') ? 'rgba(34,197,94,0.1)' : 'rgba(239,68,68,0.1)', color: msg.startsWith('✅') ? '#86efac' : '#fca5a5' }}>
            {msg}
          </div>
        )}
        <button onClick={save} disabled={saving} className="btn btn-primary w-full">
          {saving ? 'Saving…' : 'Save Changes'}
        </button>
      </motion.div>

      {/* Security */}
      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
        className="card flex flex-col gap-3">
        <div className="flex items-center gap-2">
          <Lock size={15} style={{ color: '#c4b5fd' }} />
          <h3 className="font-bold text-sm text-white" style={{ fontFamily: 'Sora' }}>Security</h3>
        </div>
        <p className="text-xs leading-relaxed" style={{ color: '#4d6080' }}>
          To change your password, we'll send a secure reset link to your email address.
        </p>
        <button onClick={sendPasswordReset}
          className="btn btn-secondary flex items-center justify-center gap-2 w-full">
          <Mail size={14} /> Send Password Reset Link
        </button>
        {pwMsg && (
          <div className="text-xs text-center" style={{ color: pwMsg.startsWith('✅') ? '#86efac' : '#E0A300' }}>{pwMsg}</div>
        )}
      </motion.div>

      {/* Learner ID */}
      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }} className="card">
        <div className="text-[10px] font-bold uppercase tracking-widest mb-2" style={{ color: '#4d6080' }}>Learner ID</div>
        <div className="font-mono text-xs px-3 py-2 rounded-xl break-all"
          style={{ background: '#030810', border: '1px solid rgba(13,71,161,0.2)', color: '#93c5fd' }}>
          {user.learner_id}
        </div>
      </motion.div>

      {/* Invoices */}
      {invoices.length > 0 && (
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }} className="card">
          <div className="font-bold text-sm text-white mb-3" style={{ fontFamily: 'Sora' }}>🧾 Your Invoices</div>
          <div className="flex flex-col gap-2">
            {invoices.map(inv => (
              <div key={inv.id} className="flex items-center justify-between py-2 border-b last:border-0 text-sm"
                style={{ borderColor: 'rgba(13,71,161,0.15)' }}>
                <span style={{ color: '#94a3b8' }}>{inv.plan}</span>
                <span className="font-semibold text-white">₦{Number(inv.amount).toLocaleString()}</span>
                <a href={`${API_BASE}/invoice/${inv.id}`} target="_blank" rel="noopener"
                  className="flex items-center gap-1 text-xs transition-colors" style={{ color: '#E0A300' }}>
                  View <ExternalLink size={10} />
                </a>
              </div>
            ))}
          </div>
        </motion.div>
      )}
    </div>
  )
}
