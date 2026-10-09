import { COLORS } from '@/styles/shared';

const API = 'https://mypytutor.onrender.com';

const h2: React.CSSProperties = { fontSize: '1.1rem', fontWeight: 700, color: '#60a5fa', marginBottom: 12, paddingBottom: 6, borderBottom: '1px solid rgba(59,130,246,.2)' };
const p:  React.CSSProperties = { color: '#cbd5e1', marginBottom: 12, fontSize: '.92rem', lineHeight: 1.8 };
const li: React.CSSProperties = { color: '#cbd5e1', fontSize: '.92rem', marginBottom: 6, lineHeight: 1.8 };

export default function PrivacyPage() {
  return (
    <div style={{ background: COLORS.bg, color: COLORS.textPrimary, minHeight: '100vh', padding: '40px 16px 60px', lineHeight: 1.8, fontFamily: "'Segoe UI', Arial, sans-serif" }}>
      <div style={{ maxWidth: 820, margin: '0 auto' }}>
        <div style={{ textAlign: 'center', marginBottom: 48 }}>
          <a href="https://mypytutor.com.ng" style={{ display: 'inline-flex', alignItems: 'center', gap: 12, marginBottom: 20, textDecoration: 'none' }}>
            <img src={`${API}/static/icons/mypytutor_logo.jpg`} alt="MyPy Tutor" style={{ width: 44, height: 44, borderRadius: '50%', border: '2px solid rgba(224,163,0,.5)' }} />
            <span style={{ fontSize: '1.35rem', fontWeight: 900, color: COLORS.gold, letterSpacing: '.04em' }}>MYPY TUTOR</span>
          </a>
          <h1 style={{ fontSize: '1.9rem', fontWeight: 800, color: '#fff', marginBottom: 8 }}>Privacy Policy</h1>
          <p style={{ ...p, color: COLORS.textDisabled }}>Effective Date: 1 October 2025 &nbsp;·&nbsp; Last Updated: 1 October 2026</p>
          <p style={{ ...p, color: COLORS.textDisabled }}>Teamsamikoko Global Academy (Reg No: 3508656)</p>
        </div>

        {[
          {
            title: '1. Data We Collect',
            content: (
              <ul style={{ paddingLeft: 20, marginBottom: 12 }}>
                {[
                  <><strong>Account data:</strong> name, email address, hashed password.</>,
                  <><strong>Learning data:</strong> topics studied, XP earned, quiz results, course progress, assignments.</>,
                  <><strong>Payment data:</strong> amount paid, plan purchased, Paystack transaction reference. We never store card numbers or CVVs.</>,
                  <><strong>Referral data:</strong> referral codes used, referral earnings, withdrawal requests.</>,
                  <><strong>Technical data:</strong> IP address (for rate-limiting), browser type, device type.</>,
                ].map((t, i) => <li key={i} style={li}>{t}</li>)}
              </ul>
            ),
          },
          {
            title: '2. How We Use Your Data',
            content: (
              <ul style={{ paddingLeft: 20, marginBottom: 12 }}>
                {['Deliver personalised AI tutoring and track your learning progress.','Process payments and issue receipts and certificates.','Administer the referral programme and process withdrawal requests.','Send transactional emails (confirmations, receipts, re-engagement reminders).','Improve the Platform through aggregated, anonymised analytics.'].map(t => <li key={t} style={li}>{t}</li>)}
              </ul>
            ),
          },
          {
            title: '3. Data Sharing',
            content: (
              <>
                <p style={p}>We do not sell your personal data. We share data only with:</p>
                <ul style={{ paddingLeft: 20, marginBottom: 12 }}>
                  {[
                    <><strong>Paystack</strong> — payment processing.</>,
                    <><strong>Supabase</strong> — cloud database hosting (EU-West region).</>,
                    <><strong>Resend / SMTP</strong> — transactional email delivery.</>,
                    <><strong>Groq / Google</strong> — AI inference (your messages are processed to generate tutor responses).</>,
                    <>Law enforcement or regulatory bodies, when required by Nigerian law.</>,
                  ].map((t, i) => <li key={i} style={li}>{t}</li>)}
                </ul>
              </>
            ),
          },
          {
            title: '4. Data Retention',
            content: <p style={p}>We retain your account and learning data for as long as your account is active. If you request account deletion, all personal data is permanently removed within 30 days, except data we are legally required to retain (e.g. payment records for 7 years under Nigerian FIRS requirements).</p>,
          },
          {
            title: '5. Your Rights (NDPR)',
            content: (
              <>
                <p style={p}>Under the Nigeria Data Protection Regulation (NDPR) 2019, you have the right to:</p>
                <ul style={{ paddingLeft: 20, marginBottom: 12 }}>
                  {['Access the personal data we hold about you.','Correct inaccurate data.','Request deletion of your data (right to erasure).','Withdraw consent for marketing communications at any time.'].map(t => <li key={t} style={li}>{t}</li>)}
                </ul>
                <p style={p}>To exercise any of these rights, use the Support/Enquiry form on the Platform.</p>
              </>
            ),
          },
          {
            title: '6. Security',
            content: <p style={p}>Passwords are hashed with bcrypt. All data is transmitted over HTTPS/TLS. Database access is restricted to the application server. We conduct regular security reviews. We will notify affected users within 72 hours of discovering a material data breach.</p>,
          },
          {
            title: '7. Cookies',
            content: <p style={p}>The Platform uses only functional cookies (session management, authentication tokens stored in localStorage). We do not use advertising or tracking cookies.</p>,
          },
          {
            title: '8. Changes to This Policy',
            content: <p style={p}>We may update this Privacy Policy from time to time. The latest version is always at <a href="/privacy" style={{ color: '#60a5fa' }}>mypytutor.com.ng/privacy</a>. Material changes will be communicated by email.</p>,
          },
          {
            title: '9. Contact',
            content: <p style={p}>Privacy questions: Support/Enquiry form at <a href="https://mypytutor.com.ng" style={{ color: '#60a5fa' }}>mypytutor.com.ng</a>. Data Protection Officer: Amb. Samuel Atulegwu Nwosu (Sir. Tega) — Teamsamikoko Global Academy.</p>,
          },
        ].map(({ title, content }) => (
          <div key={title} style={{ marginBottom: 36 }}>
            <h2 style={h2}>{title}</h2>
            {content}
          </div>
        ))}

        <div style={{ textAlign: 'center', marginTop: 56, paddingTop: 24, borderTop: '1px solid rgba(255,255,255,.07)', fontSize: '.78rem', color: COLORS.textDisabled }}>
          <p><a href="https://mypytutor.com.ng" style={{ color: '#60a5fa', textDecoration: 'none' }}>mypytutor.com.ng</a> &nbsp;·&nbsp; <a href="/terms" style={{ color: '#60a5fa', textDecoration: 'none' }}>Terms</a> &nbsp;·&nbsp; <a href="/privacy" style={{ color: '#60a5fa', textDecoration: 'none' }}>Privacy</a></p>
          <p style={{ marginTop: 8 }}>© 2025–2026 Teamsamikoko Global Academy. All rights reserved.</p>
        </div>
      </div>
    </div>
  );
}
