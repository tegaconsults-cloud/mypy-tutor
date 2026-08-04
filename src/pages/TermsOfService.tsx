import React from 'react'
import { Link } from 'react-router-dom'
import SocialLinks from '../components/SocialLinks'

const LAST_UPDATED = 'August 4, 2026'

export default function TermsOfServicePage() {
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
        <h1 style={{ fontSize: 'clamp(1.6rem,4vw,2.2rem)', fontWeight: 900, marginBottom: 8, letterSpacing: '-0.01em' }}>Terms of Service</h1>
        <p style={{ color: '#64748b', fontSize: '0.85rem', marginBottom: 36 }}>Last updated: {LAST_UPDATED} · Effective immediately</p>

        {[
          ['1. Acceptance of Terms', `By accessing or using MyPy Tutor ("the Platform"), operated by TeamTega Technologies Limited and certified by Teamsamikoko Global Academy (Reg No: 3508656), you agree to be bound by these Terms of Service. If you do not agree, do not use the Platform.`],
          ['2. Description of Service', `MyPy Tutor is an AI-powered Python and Machine Learning learning platform. We provide structured courses, AI tutoring via "Sir. Tega", quizzes, progress tracking, and professional certificates. The free tier includes 10 AI prompts per day. Paid bundles and individual courses unlock additional content and unlimited AI access for enrolled courses.`],
          ['3. User Accounts', `You must provide accurate, current information when creating an account. You are responsible for maintaining the confidentiality of your password and for all activity under your account. You must be at least 13 years old to use the Platform. Notify us immediately at support@mypytutor.com.ng if you suspect unauthorised account access.`],
          ['4. Payments and Refunds', `All payments are processed securely via Paystack. Prices are in Nigerian Naira (NGN) unless otherwise stated. Course bundle purchases are one-time payments granting lifetime access to enrolled content. Due to the digital nature of the content, all sales are final and non-refundable except where required by applicable law. If you experience a technical issue preventing access to purchased content, contact support@mypytutor.com.ng within 7 days.`],
          ['5. Intellectual Property', `All course content, AI responses, certificates, and platform materials are the intellectual property of TeamTega Technologies Limited and Teamsamikoko Global Academy. You may use the content for personal learning purposes only. You may not redistribute, resell, or publicly display course materials without written permission.`],
          ['6. Certificates', `Certificates are issued by Teamsamikoko Global Academy (Reg No: 3508656) upon completing the required curriculum or purchasing the relevant bundle. Certificates are valid and verifiable at the URL provided in your certificate. We reserve the right to revoke certificates obtained through fraudulent means.`],
          ['7. Acceptable Use', `You agree not to: (a) use the Platform for any illegal purpose; (b) attempt to bypass rate limits, security controls, or access controls; (c) scrape, reverse-engineer, or copy the AI system; (d) submit harmful, abusive, or fraudulent content; (e) impersonate another user or entity; (f) share your account credentials with others.`],
          ['8. AI Service Limitations', `The AI tutor (Sir. Tega) is powered by large language models. Responses are generated automatically and may occasionally contain errors. Do not rely on AI-generated code for production systems without independent review. We are not liable for any losses resulting from acting on AI-generated content.`],
          ['9. Privacy', `Your use of the Platform is also governed by our Privacy Policy, available at /privacy. By using the Platform you consent to the data practices described therein.`],
          ['10. Service Availability', `We strive for high availability but do not guarantee uninterrupted service. The Platform may be unavailable for maintenance, updates, or due to factors beyond our control. We are not liable for any losses resulting from service interruptions.`],
          ['11. Limitation of Liability', `To the maximum extent permitted by law, TeamTega Technologies Limited shall not be liable for any indirect, incidental, special, or consequential damages arising from your use of the Platform. Our total liability shall not exceed the amount you paid us in the 3 months preceding the claim.`],
          ['12. Governing Law', `These Terms are governed by the laws of the Federal Republic of Nigeria. Any disputes shall be resolved in the competent courts of Nigeria. For disputes below ₦1,000,000, we encourage resolution through our support process before litigation.`],
          ['13. Changes to Terms', `We may update these Terms at any time. Continued use of the Platform after changes constitutes acceptance. We will notify registered users of material changes via email.`],
          ['14. Contact', `Questions about these Terms: support@mypytutor.com.ng\nTeamTega Technologies Limited / Teamsamikoko Global Academy\nReg No: 3508656 · Nigeria`],
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
            <Link to="/privacy" style={{ color: '#60a5fa' }}>Privacy Policy</Link> ·{' '}
            <a href="mailto:support@mypytutor.com.ng" style={{ color: '#60a5fa' }}>support@mypytutor.com.ng</a>
          </div>
        </div>
      </div>
    </div>
  )
}
