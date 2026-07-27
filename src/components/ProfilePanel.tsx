import React, { useEffect, useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { getProfile, saveProfile, forgotPassword } from '../api'
import { API_BASE } from '../api'

export default function ProfilePanel() {
  const { user, signOut } = useAuth()
  const [name, setName] = useState('')
  const [bio, setBio] = useState('')
  const [location, setLocation] = useState('')
  const [website, setWebsite] = useState('')
  const [photoUrl, setPhotoUrl] = useState('')
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState('')
  const [pwMsg, setPwMsg] = useState('')
  const [invoices, setInvoices] = useState<{id:string;plan:string;amount:number}[]>([])

  const lid = user?.learner_id || 'default'
  const isGoogle = localStorage.getItem('mpt_auth_type') === 'google'

  useEffect(() => {
    if (!user) return
    // Fill from user immediately
    setName(user.name || '')
    setPhotoUrl(user.picture || '')
    // Load full profile
    getProfile(lid).then(d => {
      if (!d) return
      setName(d.display_name || user.name || '')
      setBio(d.bio || '')
      setLocation(d.location || '')
      setWebsite(d.website || '')
      setPhotoUrl(d.photo_url || user.picture || '')
    })
    // Load invoices
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
    const file = e.target.files?.[0]
    if (!file) return
    if (file.size > 2 * 1024 * 1024) { setMsg('Photo must be under 2 MB.'); return }
    const reader = new FileReader()
    reader.onload = ev => { setPhotoUrl(ev.target?.result as string) }
    reader.readAsDataURL(file)
  }

  const sendPasswordReset = async () => {
    if (isGoogle) { setPwMsg('Google accounts — change at myaccount.google.com'); return }
    const email = localStorage.getItem('mpt_user_email') || user?.email || ''
    if (!email) { setPwMsg('Could not find account email.'); return }
    try {
      await forgotPassword(email)
      setPwMsg(`✅ Reset link sent to ${email}`)
    } catch { setPwMsg('❌ Network error') }
  }

  if (!user) return (
    <div style={{ padding: 20, color: '#718096', textAlign: 'center' }}>Sign in to view your profile.</div>
  )

  return (
    <div style={{ overflowY: 'auto', padding: 16, display: 'flex', flexDirection: 'column', gap: 16, maxWidth: 560, margin: '0 auto', width: '100%' }}>

      {/* Avatar + name */}
      <div className="card" style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
        <label style={{ position: 'relative', flexShrink: 0, cursor: 'pointer' }}>
          <div style={{ width: 72, height: 72, borderRadius: '50%', overflow: 'hidden', background: 'linear-gradient(135deg,#3b82f6,#8b5cf6)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontWeight: 800, fontSize: '1.8rem' }}>
            {photoUrl ? <img src={photoUrl} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }} /> : (user.name || 'U').split(' ').map(w => w[0]).slice(0,2).join('').toUpperCase()}
          </div>
          <div style={{ position: 'absolute', bottom: 2, right: 2, background: '#3b82f6', borderRadius: '50%', width: 22, height: 22, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '.65rem' }}>📷</div>
          <input type="file" accept="image/*" onChange={handlePhotoUpload} style={{ display: 'none' }} />
        </label>
        <div style={{ flex: 1 }}>
          <div style={{ fontWeight: 800, color: '#f1f5f9', fontSize: '1.1rem' }}>{name || user.email.split('@')[0]}</div>
          <div style={{ fontSize: '.8rem', color: '#64748b' }}>{user.email}</div>
          <div style={{ display: 'inline-block', marginTop: 6, fontSize: '.62rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '.08em', padding: '2px 10px', borderRadius: 999, background: 'rgba(59,130,246,.15)', color: '#93c5fd', border: '1px solid rgba(59,130,246,.3)' }}>
            Free Plan
          </div>
        </div>
        <button onClick={() => { signOut() }} style={{ background: 'rgba(239,68,68,.1)', border: '1px solid rgba(239,68,68,.3)', color: '#fca5a5', borderRadius: 10, padding: '8px 12px', fontSize: '.8rem', fontWeight: 600, cursor: 'pointer' }}>🚪 Sign Out</button>
      </div>

      {/* Edit profile */}
      <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        <h3 style={{ color: '#f1f5f9', fontSize: '.97rem', fontWeight: 700 }}>✏️ Edit Profile</h3>
        <div>
          <label style={{ fontSize: '.72rem', color: '#718096', display: 'block', marginBottom: 4, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '.05em' }}>Display Name</label>
          <input value={name} onChange={e => setName(e.target.value)} placeholder="How should we call you?" maxLength={80} />
        </div>
        <div>
          <label style={{ fontSize: '.72rem', color: '#718096', display: 'block', marginBottom: 4, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '.05em' }}>Bio</label>
          <textarea value={bio} onChange={e => setBio(e.target.value)} placeholder="A short bio…" maxLength={500} rows={3} style={{ resize: 'vertical' }} />
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
          <div>
            <label style={{ fontSize: '.72rem', color: '#718096', display: 'block', marginBottom: 4, fontWeight: 600, textTransform: 'uppercase' }}>Location</label>
            <input value={location} onChange={e => setLocation(e.target.value)} placeholder="e.g. Lagos, Nigeria" maxLength={100} />
          </div>
          <div>
            <label style={{ fontSize: '.72rem', color: '#718096', display: 'block', marginBottom: 4, fontWeight: 600, textTransform: 'uppercase' }}>Website</label>
            <input value={website} onChange={e => setWebsite(e.target.value)} placeholder="https://yoursite.com" maxLength={200} type="url" />
          </div>
        </div>
        {msg && <div style={{ fontSize: '.82rem', textAlign: 'center', color: msg.startsWith('✅') ? '#68d391' : '#fc8181' }}>{msg}</div>}
        <button onClick={save} disabled={saving} className="btn btn-primary" style={{ width: '100%' }}>
          {saving ? 'Saving…' : 'Save Changes'}
        </button>
      </div>

      {/* Security */}
      <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        <h3 style={{ color: '#f1f5f9', fontSize: '.97rem', fontWeight: 700 }}>🔐 Security</h3>
        <p style={{ fontSize: '.82rem', color: '#64748b', lineHeight: 1.5 }}>To change your password, we'll send a secure reset link to your email.</p>
        <button onClick={sendPasswordReset} className="btn btn-secondary" style={{ width: '100%', borderColor: 'rgba(59,130,246,.4)', color: '#93c5fd' }}>
          📧 Send Password Reset Link
        </button>
        {pwMsg && <div style={{ fontSize: '.78rem', color: pwMsg.startsWith('✅') ? '#68d391' : '#f6ad55', textAlign: 'center' }}>{pwMsg}</div>}
      </div>

      {/* Invoices */}
      {invoices.length > 0 && (
        <div className="card">
          <h3 style={{ color: '#f1f5f9', fontSize: '.97rem', fontWeight: 700, marginBottom: 12 }}>🧾 Your Invoices</h3>
          {invoices.map(inv => (
            <div key={inv.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '7px 0', borderBottom: '1px solid #2d3748', fontSize: '.82rem' }}>
              <span style={{ color: '#94a3b8' }}>{inv.plan}</span>
              <span style={{ color: '#f1f5f9', fontWeight: 600 }}>₦{Number(inv.amount).toLocaleString()}</span>
              <a href={`${API_BASE}/invoice/${inv.id}`} target="_blank" rel="noopener" style={{ color: '#60a5fa', fontSize: '.75rem' }}>View</a>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
