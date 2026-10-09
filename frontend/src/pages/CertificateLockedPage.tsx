import { useState, useEffect, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import useAuth from '@/hooks/useAuth';
import { COLORS } from '@/styles/shared';

const API = 'https://mypytutor.onrender.com';

const PLAN_AMOUNTS: Record<string, number> = {
  'Beginner Bundle': 30000, 'Intermediate Bundle': 60000,
  'Advanced Bundle': 100000, 'Premium Bundle': 150000,
};

export default function CertificateLockedPage() {
  const [params] = useSearchParams();
  const { token, learnerId } = useAuth();

  const planName  = params.get('plan')  || 'Beginner Bundle';
  const planAmt   = parseInt(params.get('amount') || '0', 10) || PLAN_AMOUNTS[planName] || 30000;
  const planDesc  = params.get('desc')  || planName;
  const levelTitle= params.get('level') || 'Basic';
  const frontendUrl = 'https://mypytutor.com.ng';

  const [tab,      setTab]      = useState<'paystack' | 'bank'>('paystack');
  const [bankDet,  setBankDet]  = useState({ bank_name: 'Zenith Bank Plc', account_name: 'Teamsamikoko Global Academy', account_number: '1228732577' });
  const [bankLoaded, setBankLoaded] = useState(false);

  const [payBusy,  setPayBusy]  = useState(false);
  const [payErr,   setPayErr]   = useState('');
  const [selPlan,  setSelPlan]  = useState(planName);
  const [selAmt,   setSelAmt]   = useState(String(planAmt));
  const [btRef,    setBtRef]    = useState('');
  const [btNotes,  setBtNotes]  = useState('');
  const [btFileB64,setBtFileB64]= useState('');
  const [btFilNm,  setBtFilNm]  = useState('');
  const [btAlert,  setBtAlert]  = useState('');
  const [btAlertOk,setBtAlertOk]= useState(false);
  const [btBusy,   setBtBusy]   = useState(false);

  const fileRef = useRef<HTMLInputElement>(null);
  const payCtrl = useRef<AbortController | null>(null);
  const btCtrl  = useRef<AbortController | null>(null);

  useEffect(() => {
    if (tab !== 'bank' || bankLoaded) return;
    fetch(`${API}/payments/bank-details`).then(r => r.json()).then((d: { bank_name?: string; account_name?: string; account_number?: string }) => {
      setBankDet({ bank_name: d.bank_name || 'Zenith Bank Plc', account_name: d.account_name || 'Teamsamikoko Global Academy', account_number: d.account_number || '1228732577' });
      setBankLoaded(true);
    }).catch(() => setBankLoaded(true));
  }, [tab, bankLoaded]);

  async function startPaystack() {
    if (!token) { setPayErr('Please sign in to MyPy Tutor first.'); return; }
    const amount = parseInt(selAmt, 10) || planAmt;
    setPayBusy(true); setPayErr('');
    payCtrl.current?.abort(); payCtrl.current = new AbortController();
    const timer = setTimeout(() => payCtrl.current?.abort(), 20000);
    try {
      const r = await fetch(`${API}/payments/paystack/initialize`, {
        method: 'POST', signal: payCtrl.current.signal,
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ learner_id: learnerId, amount_ngn: amount, plan: selPlan, course_name: '' }),
      });
      clearTimeout(timer);
      const d = await r.json() as { authorization_url?: string; error?: string; detail?: string };
      if (!r.ok || !d.authorization_url) throw new Error(d.error || d.detail || 'Checkout failed.');
      window.location.href = d.authorization_url;
    } catch (e: unknown) {
      clearTimeout(timer);
      setPayErr((e instanceof Error && e.name === 'AbortError') ? 'Request timed out.' : (e instanceof Error ? e.message : 'Failed.'));
      setPayBusy(false);
    }
  }

  function processFile(file: File) {
    if (file.size > 3.8 * 1024 * 1024) { setBtAlert('File too large. Max 3.5 MB.'); setBtAlertOk(false); return; }
    const r = new FileReader(); r.onload = e => { setBtFileB64((e.target?.result as string) || ''); setBtFilNm(file.name); }; r.readAsDataURL(file);
  }

  async function submitProof() {
    const amt = parseInt(selAmt, 10) || planAmt;
    if (!selPlan)  { setBtAlert('Select your plan.'); setBtAlertOk(false); return; }
    if (!btFileB64){ setBtAlert('Upload your receipt image.'); setBtAlertOk(false); return; }
    if (!token)    { setBtAlert('Please sign in first.'); setBtAlertOk(false); return; }
    setBtBusy(true); setBtAlert('');
    btCtrl.current?.abort(); btCtrl.current = new AbortController();
    const timer = setTimeout(() => btCtrl.current?.abort(), 25000);
    try {
      const r = await fetch(`${API}/payments/bank-transfer/submit`, {
        method: 'POST', signal: btCtrl.current.signal,
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ plan: selPlan, amount: amt, reference: btRef, proof_image_base64: btFileB64, notes: btNotes }),
      });
      clearTimeout(timer);
      const d = await r.json() as { proof_id?: string; error?: string; detail?: string };
      if (!r.ok) throw new Error(d.error || d.detail || 'Submission failed.');
      setBtAlert(`✅ Receipt submitted! (ID: ${d.proof_id ?? ''}). Upgrade within 24h.`); setBtAlertOk(true);
    } catch (e: unknown) {
      clearTimeout(timer);
      setBtAlert('❌ ' + ((e instanceof Error && e.name === 'AbortError') ? 'Timed out.' : (e instanceof Error ? e.message : 'Failed.'))); setBtAlertOk(false);
    } finally { setBtBusy(false); }
  }

  const field: React.CSSProperties = { width: '100%', background: 'rgba(255,255,255,.06)', border: '1px solid rgba(255,255,255,.12)', borderRadius: 8, padding: '9px 12px', color: COLORS.textPrimary, fontSize: '.88rem', fontFamily: 'inherit', outline: 'none' };

  return (
    <div style={{ minHeight: '100vh', background: COLORS.bg, display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '24px 16px' }}>
      <div style={{ maxWidth: 520, width: '100%', background: 'rgba(26,32,44,.97)', border: '1px solid rgba(245,158,11,.2)', borderRadius: 20, padding: '36px 32px', boxShadow: '0 24px 80px rgba(0,0,0,.55)', marginBottom: 20 }}>
        <div style={{ textAlign: 'center', marginBottom: 24 }}>
          <span style={{ fontSize: '3rem', display: 'block', marginBottom: 14, filter: 'drop-shadow(0 0 10px rgba(245,158,11,.5))' }}>🔒</span>
          <h2 style={{ color: '#fcd34d', fontSize: '1.35rem', fontWeight: 800, marginBottom: 12 }}>Certificate Locked</h2>
          <p style={{ color: COLORS.textMuted, lineHeight: 1.75, fontSize: '.88rem' }}>
            Unlock your <strong style={{ color: COLORS.textPrimary }}>{levelTitle} Certificate</strong> by purchasing{' '}
            <span style={{ color: COLORS.blueText, fontWeight: 700, background: 'rgba(59,130,246,.1)', borderRadius: 6, padding: '1px 10px', border: '1px solid rgba(59,130,246,.25)' }}>{planDesc}</span>.
          </p>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 7, margin: '0 0 20px' }}>
          {[['💳', 'Pay via Paystack card/transfer'], ['🏦', 'Bank transfer + upload receipt'], ['📚', 'Complete all required courses']].map(([icon, text]) => (
            <div key={text} style={{ display: 'flex', alignItems: 'center', gap: 12, background: 'rgba(255,255,255,.03)', border: '1px solid rgba(255,255,255,.06)', borderRadius: 10, padding: '9px 14px', fontSize: '.86rem', color: COLORS.textMuted }}>
              <span style={{ fontSize: '1.1rem' }}>{icon}</span><span>{text}</span>
            </div>
          ))}
        </div>

        <div style={{ display: 'flex', gap: 8, marginBottom: 20 }}>
          {(['paystack', 'bank'] as const).map(t => (
            <button key={t} onClick={() => setTab(t)} style={{ flex: 1, padding: 9, borderRadius: 10, border: `1px solid ${tab === t ? 'rgba(59,130,246,.4)' : 'rgba(255,255,255,.1)'}`, background: tab === t ? 'rgba(59,130,246,.18)' : 'rgba(255,255,255,.04)', color: tab === t ? COLORS.blueText : COLORS.textMuted, cursor: 'pointer', fontSize: '.82rem', fontWeight: 600 }}>
              {t === 'paystack' ? '💳 Pay with Paystack' : '🏦 Bank Transfer'}
            </button>
          ))}
        </div>

        {tab === 'paystack' && (
          <div>
            <p style={{ fontSize: '.82rem', color: COLORS.textDisabled, marginBottom: 14, lineHeight: 1.6 }}>
              Click below to open a secure Paystack checkout page.{' '}
              <a href={`/payment?plan=${encodeURIComponent(planName)}&amount=${planAmt}&name=${encodeURIComponent(planDesc)}&tier=${encodeURIComponent(levelTitle)}`} style={{ color: COLORS.blueText, fontSize: '.78rem' }}>Or open full payment page →</a>
            </p>
            <button onClick={startPaystack} disabled={payBusy} style={{ width: '100%', padding: 14, border: 'none', borderRadius: 12, background: 'linear-gradient(135deg,#d97706,#f59e0b)', color: '#07090f', fontSize: '.95rem', fontWeight: 800, cursor: payBusy ? 'wait' : 'pointer', opacity: payBusy ? .6 : 1 }}>
              {payBusy ? '⏳ Opening checkout…' : `🚀 Pay ₦${planAmt.toLocaleString()} — Unlock Certificate`}
            </button>
            {payErr && <div style={{ marginTop: 8, color: '#fca5a5', fontSize: '.82rem', background: 'rgba(239,68,68,.1)', border: '1px solid rgba(239,68,68,.3)', borderRadius: 8, padding: '8px 12px' }}>
              {!token ? <><a href="https://mypytutor.com.ng" style={{ color: COLORS.blueText }}>Sign in to MyPy Tutor</a> first to start checkout.</> : payErr}
            </div>}
          </div>
        )}

        {tab === 'bank' && (
          <div>
            <div style={{ background: 'rgba(59,130,246,.07)', border: '1px solid rgba(59,130,246,.2)', borderRadius: 10, padding: '14px 16px', marginBottom: 14 }}>
              {[['Bank', bankDet.bank_name], ['Account Name', bankDet.account_name], ['Account Number', bankDet.account_number]].map(([lbl, val]) => (
                <div key={lbl} style={{ marginTop: lbl === 'Bank' ? 0 : 8 }}>
                  <div style={{ fontSize: '.72rem', color: COLORS.textDisabled, marginBottom: 2 }}>{lbl}</div>
                  <div style={{ fontSize: '1rem', fontWeight: 700, color: COLORS.blueText, letterSpacing: '.04em' }}>{val}</div>
                </div>
              ))}
              <button onClick={() => navigator.clipboard.writeText(bankDet.account_number)} style={{ display: 'inline-flex', alignItems: 'center', gap: 4, marginTop: 6, background: 'rgba(59,130,246,.15)', border: '1px solid rgba(59,130,246,.3)', color: COLORS.blueText, borderRadius: 6, padding: '3px 10px', fontSize: '.74rem', cursor: 'pointer' }}>📋 Copy number</button>
            </div>

            <label style={{ display: 'block', fontSize: '.78rem', fontWeight: 600, color: COLORS.textMuted, marginBottom: 5 }}>Plan *</label>
            <select value={selPlan} onChange={e => { setSelPlan(e.target.value); setSelAmt(String(PLAN_AMOUNTS[e.target.value] || '')); }} style={{ ...field, marginBottom: 4 }}>
              <option value="">— Select your plan —</option>
              {Object.entries(PLAN_AMOUNTS).map(([name, amt]) => <option key={name} value={name}>{name} — ₦{amt.toLocaleString()}</option>)}
            </select>

            <label style={{ display: 'block', fontSize: '.78rem', fontWeight: 600, color: COLORS.textMuted, margin: '14px 0 5px' }}>Reference</label>
            <input value={btRef} onChange={e => setBtRef(e.target.value)} placeholder="e.g. your email" style={field} />

            <label style={{ display: 'block', fontSize: '.78rem', fontWeight: 600, color: COLORS.textMuted, margin: '14px 0 5px' }}>Receipt Image *</label>
            <div onClick={() => fileRef.current?.click()} style={{ border: '2px dashed rgba(255,255,255,.12)', borderRadius: 10, padding: '18px 14px', textAlign: 'center', cursor: 'pointer', marginTop: 10 }}>
              <div style={{ fontSize: '1.8rem', marginBottom: 6 }}>📎</div>
              <div style={{ fontSize: '.82rem', color: COLORS.textDisabled }}>{btFilNm ? `✅ ${btFilNm}` : 'Click or drag & drop receipt here'}</div>
              <input ref={fileRef} type="file" accept="image/*" style={{ display: 'none' }} onChange={e => { const f = e.target.files?.[0]; if (f) processFile(f); }} />
            </div>

            <label style={{ display: 'block', fontSize: '.78rem', fontWeight: 600, color: COLORS.textMuted, margin: '14px 0 5px' }}>Notes</label>
            <textarea value={btNotes} onChange={e => setBtNotes(e.target.value)} rows={2} style={{ ...field, resize: 'vertical' }} />

            <button onClick={submitProof} disabled={btBusy} style={{ width: '100%', marginTop: 16, padding: 12, background: 'linear-gradient(135deg,#1d4ed8,#3b82f6)', color: '#fff', border: 'none', borderRadius: 10, fontSize: '.9rem', fontWeight: 700, cursor: btBusy ? 'wait' : 'pointer', opacity: btBusy ? .5 : 1 }}>
              {btBusy ? '⏳ Submitting…' : '📤 Submit Payment Proof'}
            </button>
            {btAlert && <div style={{ marginTop: 12, padding: '10px 14px', borderRadius: 8, fontSize: '.82rem', background: btAlertOk ? 'rgba(16,185,129,.1)' : 'rgba(239,68,68,.1)', border: `1px solid ${btAlertOk ? 'rgba(16,185,129,.3)' : 'rgba(239,68,68,.3)'}`, color: btAlertOk ? '#6ee7b7' : '#fca5a5' }}>{btAlert}</div>}
          </div>
        )}

        <p style={{ marginTop: 16, fontSize: '.78rem', textAlign: 'center' }}>
          <a href={frontendUrl} style={{ color: '#60a5fa', textDecoration: 'none' }}>← Return to MyPy Tutor</a>
        </p>
      </div>
    </div>
  );
}
