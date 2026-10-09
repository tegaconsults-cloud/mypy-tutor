import { useParams, useSearchParams } from 'react-router-dom';
import { COLORS } from '@/styles/shared';

export default function CertificateNotFoundPage() {
  const { certId: paramId } = useParams<{ certId?: string }>();
  const [params] = useSearchParams();
  const certId = paramId || params.get('cert_id') || params.get('id') || '';

  return (
    <div style={{ minHeight: '100vh', background: COLORS.bg, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 20, fontFamily: "'Segoe UI', Arial, sans-serif" }}>
      <div style={{ maxWidth: 460, width: '100%', background: 'rgba(26,32,44,.95)', border: '1px solid rgba(239,68,68,.25)', borderRadius: 20, padding: '44px 36px', textAlign: 'center', boxShadow: '0 24px 80px rgba(0,0,0,.6)', backdropFilter: 'blur(16px)', position: 'relative', overflow: 'hidden' }}>
        {/* Red top border */}
        <div style={{ position: 'absolute', top: 0, left: '10%', right: '10%', height: 2, background: 'linear-gradient(90deg,transparent,#ef4444,#f87171,#ef4444,transparent)', borderRadius: 1 }} />

        <span style={{ fontSize: '3.2rem', display: 'block', marginBottom: 18, filter: 'drop-shadow(0 0 14px rgba(239,68,68,.45))' }}>❌</span>
        <h2 style={{ color: '#fc8181', fontSize: '1.35rem', fontWeight: 800, marginBottom: 14, letterSpacing: '-.02em' }}>Certificate Not Found</h2>
        {certId && (
          <p style={{ color: COLORS.textMuted, lineHeight: 1.75, marginBottom: 12, fontSize: '.9rem' }}>
            No certificate with ID{' '}
            <code style={{ background: 'rgba(45,55,72,.8)', border: '1px solid rgba(255,255,255,.1)', padding: '3px 10px', borderRadius: 6, color: '#fcd34d', fontFamily: 'Courier New, monospace' }}>{certId}</code>{' '}
            was found in our records.
          </p>
        )}
        <p style={{ color: COLORS.textMuted, lineHeight: 1.75, marginBottom: 20, fontSize: '.9rem' }}>
          If you believe this is an error, please contact our support team at{' '}
          <a href="mailto:tega.com.ng@gmail.com" style={{ color: '#63b3ed', fontWeight: 600, textDecoration: 'none' }}>tega.com.ng@gmail.com</a>.
        </p>
        <a href="https://mypytutor.com.ng" style={{ display: 'inline-block', background: 'linear-gradient(135deg,#c53030,#e53e3e)', color: '#fff', textDecoration: 'none', padding: '12px 30px', borderRadius: 12, fontWeight: 700, fontSize: '.93rem', boxShadow: '0 4px 18px rgba(239,68,68,.35)' }}>
          ← Return to MyPy Tutor
        </a>
      </div>
    </div>
  );
}
