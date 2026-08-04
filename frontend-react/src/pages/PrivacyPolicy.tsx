import React from 'react'
import { Link } from 'react-router-dom'
import SocialLinks from '../components/SocialLinks'

const LAST_UPDATED = 'August 4, 2026'

export default function PrivacyPolicyPage() {
  return (
    <div style={{ fontFamily: 'Inter,Segoe UI,sans-serif', background: '#0a0f1a', color: '#e2e8f0', minHeight: '100vh' }}>
      {/* Header */}
      <div style={{ background: 'rgba(6,13,28,0.97)', borderBottom: '1px solid rgba(13,71,161,0.25)', padding: '12px 20px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', position: 'sticky', top: 0, zIndex: 50, backdropFilter: 'blur(20px)' }}>
        <Link to="/" style={{ display: 'flex', alignItems: 'center', gap: 10, textDecoration: 'none' }}>
          <div style={{ width: 36, height: 36, borderRadius: '50%', overflow: 'hidden', background: '#fff', border: '2px solid rgba(224,163,0,0.5)', flexShrink: 0 }}>
            <img src="/icons/mypytutor_logo.jpg" alt="MyPy Tutor" style={{ width: '100%', height: '100%', objectFit: 'contain' }} />
          </div>
          <div style={{ lineHeight: 1.1 }}>
            <div style={{ fontWeight: 900, fontSize: '0.9rem', color: '#E0A300', letterSpacing: '0.04em' }}>MYPY</div>
            <div style={{ fontWeight: 700, fontSize: '0.65rem', letterSpacing: '0.12em', color: '#60a5fa', textTransform: 'uppercase' }}>TUTOR</div>
          </div>
        </Link>
        <Link to="/" style={{ color: '#93c5fd', textDecoration: 'none', fontSize: '0.85rem' }}>← Back to App</Link>
      </div>

      <div style={{ maxWidth: 760, margin: '0 auto', padding: 'clamp(32px,5vw,56px) clamp(16px,4vw,40px) 60px' }}>
        <h1 style={{ fontSize: 'clamp(1.6rem,4vw,2.2rem)', fontWeight: 900, marginBottom: 8, letterSpacing: '-0.01em' }}>Privacy Policy</h1>
        <p style={{ color: '#64748b', fontSize: '0.85rem', marginBottom: 36 }}>Last updated: {LAST_UPDATED} · Compliant with Nigeria Data Protection Regulation (NDPR) 2019</p>

        {[
          ['1. Who We Are', `MyPy Tutor is operated by TeamTega Technologies Limited and certified by Teamsamikoko Global Academy (Reg No: 3508656), Nigeria. We are the data controller for personal information collected through this Platform. Contact: support@mypytutor.com.ng`],
          ['2. Information We Collect', `We collect:\n• Account information: name, email address, and password hash when you register\n• Learning data: courses started, quiz answers, XP earned, topics studied\n• Usage data: chat messages sent to the AI tutor, lesson progress\n• Payment data: payment reference, amount, plan purchased (we do NOT store card numbers — Paystack handles card processing)\n• Device data: browser type, IP address (for rate limiting and security)\n• OAuth data: Google/GitHub profile picture, name, and email when you sign in via OAuth`],
          ['3. How We Use Your Information', `We use your data to:\n• Provide and personalise the learning experience\n• Track your progress, award XP, and issue certificates\n• Process payments and send receipts\n• Send important account communications (confirmation, password reset)\n• Send optional learning reminders and announcements (you can opt out)\n• Detect fraud and abuse (rate limiting, security monitoring)\n• Improve the Platform`],
          ['4. Legal Basis (NDPR / GDPR)', `We process your data based on:\n• Contract performance: to provide the service you signed up for\n• Legitimate interests: security, fraud prevention, service improvement\n• Consent: marketing emails (you may withdraw consent at any time)\n• Legal obligation: compliance with Nigerian law`],
          ['5. Data Storage and Security', `Your data is stored in:\n• SQLite database on Render (ephemeral, resets on restart)\n• Supabase PostgreSQL cloud database (persistent, encrypted at rest)\n• All data is transmitted over HTTPS/TLS\n• Passwords are hashed using bcrypt (cost factor 12)\n• Session tokens are signed HMAC tokens, not stored server-side`],
          ['6. Data Sharing', `We do not sell your personal data. We share data only with:\n• Supabase (cloud database) — data processor\n• Groq (AI inference) — chat messages are sent for processing; Groq does not train on API data per their policy\n• Paystack (payment processing) — payment data only\n• Resend/Gmail (email delivery) — email address and name only\n• We may disclose data if required by Nigerian law enforcement`],
          ['7. Your Rights (NDPR)', `Under the Nigeria Data Protection Regulation you have the right to:\n• Access your personal data\n• Correct inaccurate data\n• Request deletion of your account and data\n• Object to processing for marketing\n• Data portability (receive your data in a machine-readable format)\n\nTo exercise any of these rights, go to Profile → Delete Account, or contact support@mypytutor.com.ng. We will respond within 30 days.`],
          ['8. Account Deletion', `You can delete your account from the Profile panel in the app. On deletion we will:\n• Remove your email, name, and password hash immediately\n• Anonymise your learning data (retained in aggregate, non-identifiable form)\n• Remove your data from Supabase within 30 days\n• Retain payment records for 7 years as required by Nigerian tax law`],
          ['9. Cookies and Local Storage', `We use browser localStorage (not cookies) to store your session token and chat history locally on your device. This data never leaves your browser except when making API calls. You can clear this at any time by signing out.`],
          ['10. Children', `Our Platform is not directed at children under 13. If you are under 13, do not use this service. If we discover we have collected data from a child under 13, we will delete it immediately.`],
          ['11. International Transfers', `Your data may be processed by Supabase (US), Groq (US), Paystack (Nigeria/US), and Resend (US). These providers maintain adequate data protection standards. We rely on contractual safeguards for international transfers.`],
          ['12. Retention', `We retain your data for as long as your account is active plus 2 years. You may request deletion at any time. Payment records are retained for 7 years per Nigerian law.`],
          ['13. Changes', `We will notify you of material changes to this Policy by email and by updating the "Last updated" date above. Continued use after changes constitutes acceptance.`],
          ['14. Contact & Complaints', `Data Protection contact: support@mypytutor.com.ng\nIf you believe your NDPR rights have been violated, you may lodge a complaint with the National Information Technology Development Agency (NITDA) at nitda.gov.ng`],
        ].map(([heading, body]) => (
          <section key={heading as string} style={{ marginBottom: 32 }}>
            <h2 style={{ fontSize: '1rem', fontWeight: 700, color: '#E0A300', marginBottom: 10, paddingBottom: 6, borderBottom: '1px solid rgba(13,71,161,0.2)' }}>{heading}</h2>
            <p style={{ color: '#94a3b8', lineHeight: 1.8, fontSize: '0.88rem', whiteSpace: 'pre-line' }}>{body}</p>
          </section>
        ))}

        <div style={{ marginTop: 48, paddingTop: 24, borderTop: '1px solid rgba(13,71,161,0.15)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 16 }}>
          <SocialLinks compact />
          <div style={{ fontSize: '0.75rem', color: '#4d6080', textAlign: 'right' }}>
            <strong style={{ color: '#94a3b8' }}>MyPy Tutor</strong> · Africa's Best AI, Python &amp; ML Tutor<br />
            TeamTega Technologies Limited · Teamsamikoko Global Academy · Reg No: 3508656<br />
            <Link to="/terms" style={{ color: '#60a5fa' }}>Terms of Service</Link> ·{' '}
            <a href="mailto:support@mypytutor.com.ng" style={{ color: '#60a5fa' }}>support@mypytutor.com.ng</a>
          </div>
        </div>
      </div>
    </div>
  )
}
