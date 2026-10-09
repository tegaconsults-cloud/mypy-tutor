import { useState, useEffect } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import { COLORS } from '@/styles/shared';

const API = 'https://mypytutor.onrender.com';

interface CertData { cert_id: string; learner_name: string; level: string; programme?: string; issued_at?: number; cert_url?: string; }

export default function CertificateVerifiedPage() {
  const { certId } = useParams<{ certId: string }>();
  const [params]   = useSearchParams();

  const [cert, setCert]       = useState<CertData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState('');

  useEffect(() => {
    // Try URL params first (fast path — passed by backend verify page)
    const fromParams: Partial<CertData> = {
      cert_id:      certId || params.get('cert_id') || '',
      learner_name: params.get('learner_name') || params.get('name') || '',
      level:        params.get('level') || '',
      programme:    params.get('programme') || '',
      issued_at:    params.get('issued_at') ? Number(params.get('issued_at')) : undefined,
    };
    if (fromParams.cert_id && fromParams.learner_name) {
      setCert(fromParams as CertData); setLoading(false); return;
    }
    // Fetch from backend
    const id = certId || params.get('cert_id') || '';
    if (!id) { setError('No certificate ID provided.'); setLoading(false); return; }
    fetch(`${API}/verify/${id}`)
      .then(r => { if (!r.ok) throw new Error('Not found'); return r.text(); })
      .then(() => {
        // Backend returns HTML — extract params from URL if possible or show minimal info
        setCert({ cert_id: id, learner_name: '', level: '', programme: '' });
        setLoading(false);
      })
      .catch(() => { setError('Certificate not found.'); setLoading(false); });
  }, [certId, params]);

  const issuedStr = cert?.issued_at
    ? new Date(cert.issued_at * 1000).toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' })
    : '';

  const levelLabel = cert?.programme || (cert?.level ? cert.level.charAt(0).toUpperCase() + cert.level.slice(1) + ' Python Certificate' : 'Python Certificate');

  const certUrl = cert?.cert_url || (cert?.cert_id ? `${API}/certificate/${cert.level}?learner_id=&name=${encodeURIComponent(cert.learner_name || '')}&admin_view=false` : '');

  // Inline keyframes via a style tag
  useEffect(() => {
    const id = 'cert-verified-anim';
    if (document.getElementById(id)) return;
    const s = document.createElement('style'); s.id = id;
    s.textContent = `
      @keyframes cvSlideUp{from{opacity:0;transform:translateY(28px)}to{opacity:1;transform:translateY(0)}}
      @keyframes cvPopIn{0%{transform:scale(.3);opacity:0}65%{transform:scale(1.18)}100%{transform:scale(1);opacity:1}}
      @keyframes cvPulse{0%,100%{box-shadow:0 0 0 0 rgba(72,187,120,.45)}50%{box-shadow:0 0 0 16px rgba(72,187,120,0)}}
      @keyframes cvShimmer{from{background-position:-600px 0}to{background-position:600px 0}}
      @keyframes cvConfetti{0%{transform:translateY(-20px) rotate(0);opacity:1}100%{transform:translateY(60px) rotate(720deg);opacity:0}}
    `;
    document.head.appendChild(s);
  }, []);

  if (loading) return (
    <div style={{ minHeight: '100vh', background: COLORS.bg, display: 'flex', alignItems: 'center', justifyContent: 'center', color: COLORS.textMuted }}>Verifying certificate…</div>
  );

  if (error) return (
    <div style={{ minHeight: '100vh', background: COLORS.bg, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 20 }}>
      <div style={{ maxWidth: 460, background: 'rgba(26,32,44,.95)', border: '1px solid rgba(239,68,68,.25)', borderRadius: 20, padding: '44px 36px', textAlign: 'center' }}>
        <span style={{ fontSize: '3rem', display: 'block', marginBottom: 18 }}>❌</span>
        <h2 style={{ color: '#fc8181', fontSize: '1.35rem', fontWeight: 800, marginBottom: 14 }}>Certificate Not Found</h2>
        <p style={{ color: COLORS.textMuted }}>{error}</p>
        <a href="https://mypytutor.com.ng" style={{ display: 'inline-block', marginTop: 20, background: 'linear-gradient(135deg,#c53030,#e53e3e)', color: '#fff', textDecoration: 'none', padding: '12px 30px', borderRadius: 12, fontWeight: 700 }}>← Return to MyPy Tutor</a>
      </div>
    </div>
  );

  const confettiColors = ['#68d391','#f6ad55','#90cdf4','#fbd38d','#b794f4'];

  return (
    <div style={{ minHeight: '100vh', background: COLORS.bg, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24, fontFamily: "'Segoe UI', Arial, sans-serif", position: 'relative', overflow: 'hidden' }}>
      {/* Confetti */}
      <div style={{ position: 'fixed', top: 0, left: 0, width: '100%', pointerEvents: 'none', zIndex: 2 }}>
        {[10, 20, 35, 50, 62, 75, 85, 92].map((left, i) => (
          <div key={i} style={{ position: 'absolute', top: -10, left: `${left}%`, width: i % 2 === 0 ? 8 : 6, height: i % 2 === 0 ? 8 : 6, borderRadius: i % 3 === 0 ? '50%' : 2, background: confettiColors[i % confettiColors.length], animation: `cvConfetti ${2.0 + (i % 4) * 0.1}s ease forwards`, animationDelay: `${i * 0.07}s` }} />
        ))}
      </div>

      <div style={{ maxWidth: 540, width: '100%', background: 'rgba(22,37,30,.97)', border: '1px solid rgba(72,187,120,.3)', borderRadius: 22, padding: '44px 40px', textAlign: 'center', boxShadow: '0 28px 90px rgba(0,0,0,.65)', backdropFilter: 'blur(20px)', position: 'relative', zIndex: 3, animation: 'cvSlideUp .55s cubic-bezier(.22,.68,0,1.2) .1s both', overflow: 'hidden' }}>
        {/* Shimmer top bar */}
        <div style={{ position: 'absolute', top: 0, left: '8%', right: '8%', height: 2, background: 'linear-gradient(90deg,transparent,#48bb78,#68d391,#48bb78,transparent)', backgroundSize: '600px 2px', borderRadius: 1, animation: 'cvShimmer 2.5s linear infinite' }} />

        {/* Badge */}
        <div style={{ display: 'inline-block', marginBottom: 14, animation: 'cvPopIn .7s cubic-bezier(.22,.68,0,1.2) .3s both', position: 'relative' }}>
          <span style={{ fontSize: '3.8rem', display: 'block', filter: 'drop-shadow(0 0 18px rgba(72,187,120,.7))' }}>✅</span>
          <div style={{ position: 'absolute', inset: -8, borderRadius: '50%', border: '2px solid rgba(72,187,120,.35)', animation: 'cvPulse 2.2s ease 1s infinite' }} />
        </div>

        <h2 style={{ color: '#68d391', fontSize: '1.5rem', fontWeight: 900, marginBottom: 6, letterSpacing: '-.03em', animation: 'cvSlideUp .4s ease .5s both' }}>Certificate Verified</h2>
        <p style={{ color: COLORS.textMuted, fontSize: '.84rem', marginBottom: 28, animation: 'cvSlideUp .4s ease .55s both' }}>This certificate is authentic and issued by MyPy Tutor</p>

        {/* Data card */}
        <div style={{ background: 'rgba(45,55,72,.55)', border: '1px solid rgba(255,255,255,.08)', borderRadius: 14, padding: '22px 26px', textAlign: 'left', marginBottom: 26, position: 'relative', overflow: 'hidden' }}>
          <div style={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: 3, background: 'linear-gradient(180deg,#48bb78,#38a169)', borderRadius: '0 2px 2px 0' }} />
          {[
            ['Recipient', cert?.learner_name || '—'],
            ['Programme', levelLabel],
            ...(issuedStr ? [['Issued', issuedStr]] : []),
            ['Certificate ID', cert?.cert_id || '—'],
            ['Status', '● Genuine'],
          ].map(([label, value], i) => (
            <div key={label} style={{ display: 'flex', alignItems: 'flex-start', gap: 12, padding: '9px 0', borderBottom: i < 4 ? '1px solid rgba(255,255,255,.05)' : 'none', animation: `cvSlideUp .35s ease ${0.6 + i * 0.08}s both` }}>
              <span style={{ color: COLORS.textDisabled, fontSize: '.76rem', fontWeight: 600, textTransform: 'uppercase' as const, letterSpacing: '.07em', minWidth: 110, paddingTop: 3, flexShrink: 0 }}>{label}</span>
              <span style={{ color: label === 'Status' ? '#68d391' : COLORS.textPrimary, fontSize: label === 'Certificate ID' ? '.8rem' : '.9rem', fontWeight: 700, wordBreak: 'break-all' as const, fontFamily: label === 'Certificate ID' ? 'Courier New, monospace' : 'inherit' }}>{value}</span>
            </div>
          ))}
        </div>

        <p style={{ color: COLORS.textDisabled, fontSize: '.78rem', marginBottom: 26, lineHeight: 1.8, animation: 'cvSlideUp .4s ease 1s both' }}>
          Issued by <strong style={{ color: COLORS.textMuted }}>Teamsamikoko Global Academy</strong><br />
          Reg No: 3508656 · Powered by TeamTega Technologies Limited
        </p>

        <div style={{ display: 'flex', gap: 10, justifyContent: 'center', flexWrap: 'wrap', animation: 'cvSlideUp .4s ease 1.05s both' }}>
          {certUrl && (
            <a href={certUrl} style={{ display: 'inline-block', background: 'linear-gradient(135deg,#276749,#38a169)', color: '#fff', textDecoration: 'none', padding: '13px 24px', borderRadius: 12, fontWeight: 800, fontSize: '.9rem', boxShadow: '0 4px 20px rgba(72,187,120,.35)' }}>
              🎓 View Certificate
            </a>
          )}
          <a href="https://mypytutor.com.ng" style={{ display: 'inline-block', background: 'rgba(255,255,255,.07)', color: COLORS.textPrimary, textDecoration: 'none', padding: '13px 24px', borderRadius: 12, fontWeight: 700, fontSize: '.9rem', border: '1px solid rgba(255,255,255,.12)' }}>
            ← Visit MyPy Tutor
          </a>
        </div>
      </div>
    </div>
  );
}
