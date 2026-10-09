import { useState, useEffect, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import useAuth from '@/hooks/useAuth';
import { COLORS } from '@/styles/shared';

const API = 'https://mypytutor.onrender.com';

interface PlanDef { name: string; amount: number; desc: string; }

const PLANS: Record<string, PlanDef> = {
  tier1:                   { name: 'Beginner Bundle',            amount: 30000,  desc: '4 courses · Lifetime access' },
  tier2:                   { name: 'Intermediate Bundle',        amount: 60000,  desc: '7 courses · Lifetime access' },
  tier3:                   { name: 'Advanced Bundle',            amount: 100000, desc: '14 courses · Lifetime access' },
  tier4:                   { name: 'Premium Bundle',             amount: 150000, desc: 'All 17 courses · Lifetime access' },
  'beginner-bundle':       { name: 'Beginner Bundle',            amount: 30000,  desc: '4 courses · Lifetime access' },
  'intermediate-bundle':   { name: 'Intermediate Bundle',        amount: 60000,  desc: '7 courses · Lifetime access' },
  'advanced-bundle':       { name: 'Advanced Bundle',            amount: 100000, desc: '14 courses · Lifetime access' },
  'premium-bundle':        { name: 'Premium Bundle',             amount: 150000, desc: 'All 17 courses · Lifetime access' },
  'basic-cert':            { name: 'Basic Certificate',          amount: 30000,  desc: 'Certificate fee' },
  'adv-cert':              { name: 'Advanced Certificate',       amount: 60000,  desc: 'Certificate fee' },
  'exec-cert':             { name: 'Executive Certificate',      amount: 100000, desc: 'Certificate fee' },
  'prompt-starter':        { name: 'Prompt Starter Plan',        amount: 2000,   desc: '50 prompts/day' },
  'prompt-pro':            { name: 'Prompt Pro Plan',            amount: 5000,   desc: '200 prompts/day' },
  'prompt-unlimited':      { name: 'Prompt Unlimited Plan',      amount: 10000,  desc: 'Unlimited prompts' },
  'python-fundamentals':   { name: 'Python Fundamentals',        amount: 5000,   desc: 'Beginner · Lifetime' },
  'python-strings':        { name: 'Python Strings',             amount: 5000,   desc: 'Beginner · Lifetime' },
  'python-collections':    { name: 'Python Collections',         amount: 5000,   desc: 'Beginner · Lifetime' },
  'python-control-flow':   { name: 'Python Control Flow',        amount: 5000,   desc: 'Beginner · Lifetime' },
  'python-functions-advanced': { name: 'Advanced Python Functions', amount: 15000, desc: 'Intermediate · Lifetime' },
  'python-oop':            { name: 'Object-Oriented Python',     amount: 15000,  desc: 'Intermediate · Lifetime' },
  'python-modules-stdlib': { name: 'Python Modules & Stdlib',    amount: 15000,  desc: 'Intermediate · Lifetime' },
  'python-dsa':            { name: 'Data Structures & Algorithms', amount: 30000, desc: 'Advanced · Lifetime' },
  'numpy-mastery':         { name: 'NumPy Mastery',              amount: 30000,  desc: 'Advanced · Lifetime' },
  'pandas-mastery':        { name: 'Pandas Mastery',             amount: 30000,  desc: 'Advanced · Lifetime' },
  'data-science-python':   { name: 'Data Science with Python',   amount: 30000,  desc: 'Advanced · Lifetime' },
  'python-databases':      { name: 'Python Databases',           amount: 30000,  desc: 'Advanced · Lifetime' },
  'web-apis':              { name: 'Web APIs with Python',       amount: 30000,  desc: 'Advanced · Lifetime' },
  'prompt-engineering':    { name: 'Prompt Engineering',         amount: 30000,  desc: 'Advanced · Lifetime' },
  'ai-prompt-engineering': { name: 'AI & Prompt Engineering',    amount: 50000,  desc: 'Premium · Lifetime' },
  'machine-learning':      { name: 'Machine Learning',           amount: 50000,  desc: 'Premium · Lifetime' },
  'ai-automation':         { name: 'AI Automation with Python',  amount: 50000,  desc: 'Premium · Lifetime' },
};

interface BankDetails { bank_name: string; account_name: string; account_number: string; }

export default function PaymentPage() {
  const [params] = useSearchParams();
  const { token, learnerId } = useAuth();

  const planKey   = params.get('plan') || params.get('tier') || params.get('course') || '';
  const urlName   = params.get('name') || '';
  const urlAmount = parseFloat(params.get('amount') || '0');
  const urlDesc   = params.get('desc') || '';
  const course    = params.get('course') || '';

  const planDef   = PLANS[planKey] ?? { name: urlName || 'Course Purchase', amount: urlAmount, desc: 'Lifetime access' };
  const planName  = urlName  || planDef.name;
  const planAmt   = urlAmount || planDef.amount;
  const planDesc  = urlDesc  || planDef.desc;

  const [tab,          setTab]          = useState<'paystack' | 'bank'>('paystack');
  const [couponCode,   setCouponCode]   = useState(params.get('coupon') || '');
  const [couponMsg,    setCouponMsg]    = useState('');
  const [couponOk,     setCouponOk]     = useState(false);
  const [couponApplied,setCouponApplied]= useState(false);
  const [accessGranted,setAccessGranted]= useState(false);
  const [discountedAmt,setDiscountedAmt]= useState(planAmt);
  const [applyBusy,    setApplyBusy]    = useState(false);

  const [payBusy,      setPayBusy]      = useState(false);
  const [payErr,       setPayErr]       = useState('');

  const [bankDetails,  setBankDetails]  = useState<BankDetails>({ bank_name: 'Zenith Bank Plc', account_name: 'Teamsamikoko Global Academy', account_number: '1228732577' });
  const [bankLoaded,   setBankLoaded]   = useState(false);

  const [btRef,        setBtRef]        = useState('');
  const [btNotes,      setBtNotes]      = useState('');
  const [btFileB64,    setBtFileB64]    = useState('');
  const [btFileName,   setBtFileName]   = useState('');
  const [btAlert,      setBtAlert]      = useState('');
  const [btAlertOk,    setBtAlertOk]    = useState(false);
  const [btBusy,       setBtBusy]       = useState(false);

  const fileRef = useRef<HTMLInputElement>(null);
  const payCtrl = useRef<AbortController | null>(null);
  const btCtrl  = useRef<AbortController | null>(null);

  // Payment success banner
  const isSuccess = params.get('payment') === 'success' || params.get('status') === 'success';
  const successRef = params.get('ref') || params.get('reference') || params.get('trxref') || '';

  // Update discounted amount when planAmt resolves
  useEffect(() => { setDiscountedAmt(planAmt); }, [planAmt]);

  // Load bank details when bank tab opens
  useEffect(() => {
    if (tab !== 'bank' || bankLoaded) return;
    fetch(`${API}/payments/bank-details`)
      .then(r => r.json())
      .then((d: Partial<BankDetails>) => {
        setBankDetails({
          bank_name:      d.bank_name      || 'Zenith Bank Plc',
          account_name:   d.account_name   || 'Teamsamikoko Global Academy',
          account_number: d.account_number || '1228732577',
        });
        setBankLoaded(true);
      })
      .catch(() => setBankLoaded(true));
  }, [tab, bankLoaded]);

  async function applyCoupon() {
    const code = couponCode.trim().toUpperCase();
    if (!code) return;
    if (!token) { setCouponMsg('Please sign in first.'); setCouponOk(false); return; }
    setApplyBusy(true); setCouponMsg('');
    try {
      const r = await fetch(`${API}/coupons/apply`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ code, plan: planKey || 'any', learner_id: learnerId, email: '' }),
      });
      const d = await r.json() as { ok?: boolean; message?: string; detail?: string; discount_pct?: number; discount_flat?: number; access_granted?: boolean };
      if (!r.ok) { setCouponMsg(d.detail || 'Coupon not found or expired.'); setCouponOk(false); return; }
      setCouponMsg(d.message || 'Coupon applied!');
      setCouponOk(true);
      setCouponApplied(true);
      if (d.access_granted) {
        setAccessGranted(true);
      } else {
        const pct  = d.discount_pct  || 0;
        const flat = d.discount_flat || 0;
        const disc = flat > 0 ? Math.max(0, planAmt - flat) : Math.round(planAmt * (1 - pct / 100));
        setDiscountedAmt(disc);
      }
    } catch { setCouponMsg('Network error. Try again.'); setCouponOk(false); }
    finally  { setApplyBusy(false); }
  }

  async function startPaystack() {
    if (!token) { setPayErr('Please sign in to MyPy Tutor first to start checkout.'); return; }
    if (!discountedAmt) { setPayErr('Could not determine plan price.'); return; }
    setPayBusy(true); setPayErr('');
    payCtrl.current?.abort();
    payCtrl.current = new AbortController();
    const timer = setTimeout(() => payCtrl.current?.abort(), 20000);
    try {
      const r = await fetch(`${API}/payments/paystack/initialize`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        signal: payCtrl.current.signal,
        body: JSON.stringify({ learner_id: learnerId, amount_ngn: discountedAmt, plan: planName, course_name: course, coupon_code: couponApplied ? couponCode : '' }),
      });
      clearTimeout(timer);
      const d = await r.json() as { authorization_url?: string; error?: string; detail?: string };
      if (!r.ok || !d.authorization_url) throw new Error(d.error || d.detail || 'Checkout failed.');
      window.location.href = d.authorization_url;
    } catch (e: unknown) {
      clearTimeout(timer);
      const msg = (e instanceof Error && e.name === 'AbortError') ? 'Request timed out. Try again or use bank transfer.' : (e instanceof Error ? e.message : 'Checkout failed.');
      setPayErr(msg);
      setPayBusy(false);
    }
  }

  function processFile(file: File) {
    if (file.size > 3.8 * 1024 * 1024) { setBtAlert('File too large. Max 3.5 MB.'); setBtAlertOk(false); return; }
    const reader = new FileReader();
    reader.onload = e => { setBtFileB64((e.target?.result as string) || ''); setBtFileName(file.name); };
    reader.readAsDataURL(file);
  }

  async function submitProof() {
    if (!btFileB64)  { setBtAlert('Please upload your receipt image.'); setBtAlertOk(false); return; }
    if (!token)      { setBtAlert('Please sign in first.'); setBtAlertOk(false); return; }
    if (!planName)   { setBtAlert('Plan name is missing.'); setBtAlertOk(false); return; }
    setBtBusy(true); setBtAlert('');
    btCtrl.current?.abort();
    btCtrl.current = new AbortController();
    const timer = setTimeout(() => btCtrl.current?.abort(), 25000);
    try {
      const r = await fetch(`${API}/payments/bank-transfer/submit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        signal: btCtrl.current.signal,
        body: JSON.stringify({ plan: planName, amount: discountedAmt || 0, reference: btRef, proof_image_base64: btFileB64, notes: btNotes }),
      });
      clearTimeout(timer);
      const d = await r.json() as { ok?: boolean; proof_id?: string; error?: string; detail?: string };
      if (!r.ok) throw new Error(d.error || d.detail || 'Submission failed.');
      setBtAlert(`✅ Receipt submitted! (Proof ID: ${d.proof_id ?? ''})\nYour account will be upgraded within 24 hours.`);
      setBtAlertOk(true);
    } catch (e: unknown) {
      clearTimeout(timer);
      const msg = (e instanceof Error && e.name === 'AbortError') ? 'Request timed out. Try again.' : (e instanceof Error ? e.message : 'Submission failed.');
      setBtAlert('❌ ' + msg); setBtAlertOk(false);
    } finally { setBtBusy(false); }
  }

  const tabStyle = (active: boolean): React.CSSProperties => ({ flex: 1, padding: 11, borderRadius: 10, border: `1px solid ${active ? 'rgba(59,130,246,.4)' : 'rgba(255,255,255,.1)'}`, background: active ? 'rgba(59,130,246,.18)' : 'rgba(255,255,255,.04)', color: active ? COLORS.blueText : COLORS.textMuted, cursor: 'pointer', fontSize: '.84rem', fontWeight: 700, textAlign: 'center' as const });

  const s: Record<string, React.CSSProperties> = {
    wrap:    { maxWidth: 520, margin: '0 auto', padding: '24px 16px 60px', position: 'relative', zIndex: 1 },
    header:  { textAlign: 'center', marginBottom: 28 },
    logo:    { display: 'inline-flex', alignItems: 'center', gap: 10, marginBottom: 16, textDecoration: 'none' },
    logoImg: { width: 40, height: 40, borderRadius: '50%', border: `2px solid rgba(245,158,11,.5)` },
    logoNm:  { fontSize: '1.2rem', fontWeight: 900, color: COLORS.gold, letterSpacing: '.04em' },
    badge:   { display: 'inline-block', background: 'rgba(59,130,246,.12)', border: '1px solid rgba(59,130,246,.3)', borderRadius: 99, padding: '3px 16px', fontSize: '.78rem', fontWeight: 700, color: COLORS.blueText, marginBottom: 10 },
    amtDisc: { fontSize: '2rem', fontWeight: 900, color: COLORS.gold, marginBottom: 4 },
    desc:    { fontSize: '.82rem', color: COLORS.textDisabled, lineHeight: 1.6 },
    tabs:    { display: 'flex', gap: 8, margin: '20px 0 16px' },
    field:   { width: '100%', background: 'rgba(255,255,255,.06)', border: '1px solid rgba(255,255,255,.12)', borderRadius: 8, padding: '9px 12px', color: COLORS.textPrimary, fontSize: '.88rem', fontFamily: 'inherit', outline: 'none' },
    cta:     { width: '100%', padding: 14, border: 'none', borderRadius: 12, background: 'linear-gradient(135deg,#d97706,#f59e0b)', color: '#07090f', fontSize: '.95rem', fontWeight: 800, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8, boxShadow: '0 4px 20px rgba(245,158,11,.35)' } as React.CSSProperties,
    submit:  { width: '100%', marginTop: 16, padding: 12, background: 'linear-gradient(135deg,#1d4ed8,#3b82f6)', color: '#fff', border: 'none', borderRadius: 10, fontSize: '.9rem', fontWeight: 700, cursor: 'pointer' } as React.CSSProperties,
    bankBox: { background: 'rgba(59,130,246,.07)', border: '1px solid rgba(59,130,246,.2)', borderRadius: 10, padding: '14px 16px', marginBottom: 14 },
    bankVal: { fontSize: '1rem', fontWeight: 700, color: COLORS.blueText, letterSpacing: '.04em' },
    bankLbl: { fontSize: '.72rem', color: COLORS.textDisabled, marginBottom: 2 },
    copyBtn: { display: 'inline-flex', alignItems: 'center', gap: 4, marginTop: 6, background: 'rgba(59,130,246,.15)', border: '1px solid rgba(59,130,246,.3)', color: COLORS.blueText, borderRadius: 6, padding: '3px 10px', fontSize: '.74rem', cursor: 'pointer' } as React.CSSProperties,
    upload:  { border: '2px dashed rgba(255,255,255,.12)', borderRadius: 10, padding: '18px 14px', textAlign: 'center', cursor: 'pointer', marginTop: 10 } as React.CSSProperties,
    errBox:  { background: 'rgba(239,68,68,.1)', border: '1px solid rgba(239,68,68,.3)', color: '#fca5a5', borderRadius: 8, padding: '10px 14px', fontSize: '.82rem', marginTop: 12 },
    okBox:   { background: 'rgba(16,185,129,.1)', border: '1px solid rgba(16,185,129,.3)', color: '#6ee7b7', borderRadius: 8, padding: '10px 14px', fontSize: '.82rem', marginTop: 12 },
  };

  return (
    <div style={{ minHeight: '100vh', background: COLORS.bg, paddingBottom: 60 }}>
      {isSuccess && (
        <div style={{ background: 'rgba(16,185,129,.15)', borderBottom: '1px solid rgba(16,185,129,.4)', padding: '14px 24px', textAlign: 'center', fontSize: '.9rem', color: '#6ee7b7' }}>
          ✅ <strong>Payment received!</strong> Your account will be updated automatically.
          {successRef && <> Reference: <code style={{ background: 'rgba(255,255,255,.08)', padding: '1px 6px', borderRadius: 4 }}>{successRef}</code></>}
          {' '}·{' '}<a href="https://mypytutor.com.ng" style={{ color: COLORS.blueText }}>Go to MyPy Tutor →</a>
        </div>
      )}
      <div style={s.wrap}>
        <div style={s.header}>
          <a href="https://mypytutor.com.ng" style={s.logo}>
            <img src={`${API}/static/icons/mypytutor_logo.jpg`} alt="MyPy Tutor" style={s.logoImg} />
            <span style={s.logoNm}>MYPY TUTOR</span>
          </a>
          <div style={s.badge}>{course ? 'Course Purchase' : 'Subscription Plan'}</div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 800, color: '#fff', marginBottom: 4 }}>{planName}</h1>
          <div style={s.amtDisc}>₦{discountedAmt.toLocaleString()}{discountedAmt !== planAmt && <span style={{ textDecoration: 'line-through', color: COLORS.textDisabled, fontSize: '1.2rem', marginLeft: 8 }}>₦{planAmt.toLocaleString()}</span>}</div>
          <p style={s.desc}>{planDesc}</p>
        </div>

        {/* Tabs */}
        <div style={s.tabs}>
          <button style={tabStyle(tab === 'paystack')} onClick={() => setTab('paystack')}>💳 Pay with Paystack</button>
          <button style={tabStyle(tab === 'bank')}     onClick={() => setTab('bank')}>🏦 Bank Transfer</button>
        </div>

        {/* ── Paystack panel ─────────────────────────────── */}
        {tab === 'paystack' && (
          <div>
            <p style={{ fontSize: '.82rem', color: COLORS.textDisabled, lineHeight: 1.6, marginBottom: 14 }}>
              Click below to open a secure Paystack checkout page.
            </p>

            {/* Coupon input */}
            {!accessGranted && (
              <div style={{ marginBottom: 14 }}>
                <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                  <input value={couponCode} onChange={e => setCouponCode(e.target.value.toUpperCase())}
                    onKeyDown={e => e.key === 'Enter' && applyCoupon()}
                    placeholder="Have a coupon code? Enter here"
                    style={{ ...s.field, flex: 1, textTransform: 'uppercase', letterSpacing: '.06em' }}
                    disabled={couponApplied} />
                  <button onClick={applyCoupon} disabled={applyBusy || couponApplied}
                    style={{ padding: '9px 16px', background: couponApplied ? 'rgba(16,185,129,.2)' : 'rgba(59,130,246,.18)', border: `1px solid ${couponApplied ? 'rgba(16,185,129,.4)' : 'rgba(59,130,246,.4)'}`, color: couponApplied ? '#6ee7b7' : COLORS.blueText, borderRadius: 8, fontSize: '.82rem', fontWeight: 700, cursor: couponApplied ? 'default' : 'pointer', whiteSpace: 'nowrap' }}>
                    {applyBusy ? '…' : couponApplied ? '✓ Applied' : 'Apply'}
                  </button>
                </div>
                {couponMsg && <div style={{ marginTop: 7, fontSize: '.8rem', padding: '7px 12px', borderRadius: 6, background: couponOk ? 'rgba(16,185,129,.1)' : 'rgba(239,68,68,.1)', border: `1px solid ${couponOk ? 'rgba(16,185,129,.3)' : 'rgba(239,68,68,.3)'}`, color: couponOk ? '#6ee7b7' : '#fca5a5' }}>{couponMsg}</div>}
              </div>
            )}

            {accessGranted ? (
              <div style={s.okBox}>🎉 <strong>Access granted!</strong> Your coupon has been applied and access is now active.<br /><a href="https://mypytutor.com.ng" style={{ color: COLORS.blueText }}>← Go to MyPy Tutor</a></div>
            ) : (
              <>
                <button onClick={startPaystack} disabled={payBusy}
                  style={{ ...s.cta, opacity: payBusy ? .55 : 1, cursor: payBusy ? 'wait' : 'pointer' }}>
                  {payBusy ? '⏳ Opening checkout…' : `🚀 Pay ₦${discountedAmt.toLocaleString()}`}
                </button>
                {payErr && (
                  <div style={s.errBox}>
                    {token ? payErr : <>Please <a href="https://mypytutor.com.ng" style={{ color: COLORS.blueText }}>sign in to MyPy Tutor</a> first to start checkout. If already signed in, reload this page.</>}
                  </div>
                )}
                <p style={{ fontSize: '.72rem', color: COLORS.textDisabled, marginTop: 10, textAlign: 'center' }}>Secured by Paystack · Card, bank transfer &amp; USSD accepted</p>
              </>
            )}
          </div>
        )}

        {/* ── Bank Transfer panel ─────────────────────────── */}
        {tab === 'bank' && (
          <div>
            <div style={s.bankBox}>
              <div style={s.bankLbl}>Bank</div><div style={s.bankVal}>{bankDetails.bank_name}</div>
              <div style={{ ...s.bankLbl, marginTop: 8 }}>Account Name</div><div style={s.bankVal}>{bankDetails.account_name}</div>
              <div style={{ ...s.bankLbl, marginTop: 8 }}>Account Number</div><div style={s.bankVal}>{bankDetails.account_number}</div>
              <button style={s.copyBtn} onClick={() => navigator.clipboard.writeText(bankDetails.account_number)}>📋 Copy number</button>
            </div>

            <p style={{ fontSize: '.82rem', color: COLORS.textMuted, lineHeight: 1.6, marginBottom: 10 }}>
              Transfer exactly <strong style={{ color: '#fcd34d' }}>₦{discountedAmt.toLocaleString()}</strong> and upload your receipt.
            </p>

            <label style={{ display: 'block', fontSize: '.78rem', fontWeight: 600, color: COLORS.textMuted, marginBottom: 5 }}>Payment Reference</label>
            <input value={btRef} onChange={e => setBtRef(e.target.value)} placeholder="e.g. your email address" style={s.field} />

            <label style={{ display: 'block', fontSize: '.78rem', fontWeight: 600, color: COLORS.textMuted, margin: '14px 0 5px' }}>Receipt Image *</label>
            <div style={s.upload} onClick={() => fileRef.current?.click()}
              onDragOver={e => { e.preventDefault(); (e.currentTarget as HTMLElement).style.borderColor = 'rgba(59,130,246,.5)'; }}
              onDragLeave={e => { (e.currentTarget as HTMLElement).style.borderColor = 'rgba(255,255,255,.12)'; }}
              onDrop={e => { e.preventDefault(); (e.currentTarget as HTMLElement).style.borderColor = 'rgba(255,255,255,.12)'; const f = e.dataTransfer.files[0]; if (f) processFile(f); }}>
              <div style={{ fontSize: '1.8rem', marginBottom: 6 }}>📎</div>
              <div style={{ fontSize: '.82rem', color: COLORS.textDisabled }}>{btFileName ? `✅ ${btFileName}` : 'Click or drag & drop your receipt here'}</div>
              <input ref={fileRef} type="file" accept="image/*" style={{ display: 'none' }} onChange={e => { const f = e.target.files?.[0]; if (f) processFile(f); }} />
            </div>

            <label style={{ display: 'block', fontSize: '.78rem', fontWeight: 600, color: COLORS.textMuted, margin: '14px 0 5px' }}>Notes (optional)</label>
            <textarea value={btNotes} onChange={e => setBtNotes(e.target.value)} rows={2} placeholder="Any additional info for the admin" style={{ ...s.field, resize: 'vertical' }} />

            <button onClick={submitProof} disabled={btBusy}
              style={{ ...s.submit, opacity: btBusy ? .5 : 1, cursor: btBusy ? 'wait' : 'pointer' }}>
              {btBusy ? '⏳ Submitting…' : '📤 Submit Payment Proof'}
            </button>
            {btAlert && <div style={btAlertOk ? s.okBox : s.errBox}>{btAlert}</div>}
          </div>
        )}

        <p style={{ display: 'block', marginTop: 20, fontSize: '.78rem', color: COLORS.textDisabled, textAlign: 'center' }}>
          <a href="https://mypytutor.com.ng" style={{ color: '#60a5fa', textDecoration: 'none' }}>← Back to MyPy Tutor</a>
        </p>
      </div>
    </div>
  );
}
