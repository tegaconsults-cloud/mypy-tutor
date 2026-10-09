import { COLORS } from '@/styles/shared';

const API = 'https://mypytutor.onrender.com';

function Logo() {
  return (
    <a href="https://mypytutor.com.ng" style={{ display: 'inline-flex', alignItems: 'center', gap: 12, marginBottom: 20, textDecoration: 'none' }}>
      <img src={`${API}/static/icons/mypytutor_logo.jpg`} alt="MyPy Tutor" style={{ width: 44, height: 44, borderRadius: '50%', border: '2px solid rgba(224,163,0,.5)' }} />
      <span style={{ fontSize: '1.35rem', fontWeight: 900, color: COLORS.gold, letterSpacing: '.04em' }}>MYPY TUTOR</span>
    </a>
  );
}

const h2: React.CSSProperties = { fontSize: '1.1rem', fontWeight: 700, color: '#60a5fa', marginBottom: 12, paddingBottom: 6, borderBottom: '1px solid rgba(59,130,246,.2)' };
const h3: React.CSSProperties = { fontSize: '.95rem', fontWeight: 700, color: '#fcd34d', margin: '16px 0 6px' };
const p:  React.CSSProperties = { color: '#cbd5e1', marginBottom: 12, fontSize: '.92rem', lineHeight: 1.8 };
const li: React.CSSProperties = { color: '#cbd5e1', fontSize: '.92rem', marginBottom: 6, lineHeight: 1.8 };
const box = (variant: 'blue' | 'warn' | 'green'): React.CSSProperties => ({
  background: variant === 'blue' ? 'rgba(59,130,246,.07)' : variant === 'warn' ? 'rgba(245,158,11,.07)' : 'rgba(16,185,129,.07)',
  border: `1px solid ${variant === 'blue' ? 'rgba(59,130,246,.22)' : variant === 'warn' ? 'rgba(245,158,11,.25)' : 'rgba(16,185,129,.22)'}`,
  borderRadius: 10, padding: '16px 20px', margin: '14px 0',
});

export default function TermsPage() {
  return (
    <div style={{ background: COLORS.bg, color: COLORS.textPrimary, minHeight: '100vh', padding: '40px 16px 60px', lineHeight: 1.8, fontFamily: "'Segoe UI', Arial, sans-serif" }}>
      <div style={{ maxWidth: 820, margin: '0 auto' }}>
        <div style={{ textAlign: 'center', marginBottom: 48 }}>
          <Logo />
          <h1 style={{ fontSize: '1.9rem', fontWeight: 800, color: '#fff', marginBottom: 8 }}>Terms of Service</h1>
          <p style={{ ...p, color: COLORS.textDisabled }}>Effective Date: 1 October 2025 &nbsp;·&nbsp; Last Updated: 1 October 2026</p>
          <p style={{ ...p, color: COLORS.textDisabled }}>Teamsamikoko Global Academy (Reg No: 3508656) &nbsp;·&nbsp; Powered by TeamTega Technologies Limited</p>
        </div>

        {[
          { title: '1. Acceptance of Terms', content: <><p style={p}>By signing up for, accessing, or using the MyPy Tutor platform at <strong>mypytutor.com.ng</strong> (the "Platform"), you agree to be bound by these Terms of Service ("Terms"), our Privacy Policy, and all applicable laws of the Federal Republic of Nigeria.</p><p style={p}>These Terms constitute a legally binding agreement between you ("User", "Learner") and Teamsamikoko Global Academy ("Academy", "we", "us"), incorporated under the laws of Nigeria (Reg No: 3508656).</p></> },
          { title: '2. Platform Description', content: <p style={p}>MyPy Tutor is an AI-powered Python, Machine Learning, and Data Science learning platform. It offers structured courses, an AI tutoring agent ("Sir. Tega"), quizzes, assignments, certifications, and a referral programme.</p> },
          { title: '3. Eligibility and Account', content: <ul style={{ paddingLeft: 20, marginBottom: 12 }}>{['You must be at least 13 years old to use the Platform.','You are responsible for maintaining the confidentiality of your account credentials.','You agree to provide accurate, current, and complete information during registration.','You may not create multiple accounts to circumvent free-tier limits or referral restrictions.'].map(t => <li key={t} style={li}>{t}</li>)}</ul> },
          { title: '4. Payments and Pricing', content: <><p style={p}>All prices are in <strong>Nigerian Naira (₦)</strong>. All course and bundle purchases grant <strong>lifetime access</strong> with a one-time payment.</p><ul style={{ paddingLeft: 20, marginBottom: 12 }}>{['Beginner Bundle — ₦30,000 (4 courses)','Intermediate Bundle — ₦60,000 (7 courses)','Advanced Bundle — ₦100,000 (14 courses)','Premium Bundle — ₦150,000 (all 17 courses)'].map(t => <li key={t} style={li}>{t}</li>)}</ul><p style={p}>Payments are processed via <strong>Paystack</strong> or manual bank transfer to Zenith Bank · Teamsamikoko Global Academy · 1228732577.</p><p style={p}><strong>Refund Policy:</strong> Due to the digital nature of our content, all sales are final. Refunds are only considered in cases of verified technical failure on our part, submitted within 7 days of purchase.</p></> },
          { title: '5. Free Tier', content: <p style={p}>Free accounts receive <strong>10 AI prompts per day</strong>, resetting at 5:00 AM WAT. Upgrading to a paid plan removes this restriction.</p> },
          { title: '6. Certificates', content: <p style={p}>Certificates are issued by <strong>Teamsamikoko Global Academy (Reg No: 3508656)</strong>. A certificate is earned by completing all required courses in a track. Certificates are verifiable online. The Academy reserves the right to revoke certificates if fraud is proven.</p> },
        ].map(({ title, content }) => (
          <div key={title} style={{ marginBottom: 36 }}>
            <h2 style={h2}>{title}</h2>
            {content}
          </div>
        ))}

        {/* Referral Programme */}
        <div style={{ marginBottom: 36 }}>
          <h2 style={h2}>7. Referral Programme Terms</h2>
          <div style={box('green')}><p style={{ ...p, margin: 0, fontSize: '.88rem' }}><strong>Summary:</strong> Every user who joins via a referral link receives a ₦5,000 welcome bonus. Referrers earn 15% of every payment their referees make.</p></div>
          <h3 style={h3}>7.1 Welcome Bonus</h3>
          <p style={p}>When a new user registers using a valid referral code, they receive a <strong>₦5,000 welcome bonus</strong> credited instantly.</p>
          <h3 style={h3}>7.2 Referrer Earnings</h3>
          <p style={p}>For every payment made by a referee, you earn a <strong>15% bonus</strong> of the payment amount. Example: referee pays ₦30,000 → you earn ₦4,500.</p>
          <h3 style={h3}>7.3 Referee Discount</h3>
          <p style={p}>Users who sign up using a valid referral code receive a <strong>5% discount</strong> on their first payment.</p>
          <h3 style={h3}>7.4 Share Message</h3>
          <div style={box('blue')}><p style={{ ...p, margin: 0, fontSize: '.88rem' }}><em>"Join MyPy Tutor — Africa's Best AI, Python and Machine Learning Tutor! Use my referral link to get instant ₦5,000 welcome bonus, 5% off your first payment, 15% bonus per new user you refer."</em></p></div>
          <h3 style={h3}>7.5 Referral Code Rules</h3>
          <ul style={{ paddingLeft: 20, marginBottom: 12 }}>
            {['Each user has one unique referral code, valid for up to 50 uses.','Self-referrals are strictly prohibited and will result in account suspension.','Referral codes cannot be transferred, sold, or bartered.'].map(t => <li key={t} style={li}>{t}</li>)}
          </ul>
        </div>

        {/* Withdrawal Terms */}
        <div style={{ marginBottom: 36 }}>
          <h2 style={h2}>8. Referral Balance & Withdrawal Terms</h2>
          <div style={box('warn')}><p style={{ ...p, margin: 0, fontSize: '.88rem' }}><strong>Important:</strong> Your referral balance is locked until you have completed <strong>10 successful paid referrals</strong>.</p></div>
          <h3 style={h3}>8.1 Balance Accrual</h3>
          <p style={p}>Your referral balance accumulates from: (a) the ₦5,000 one-time welcome bonus, and (b) 15% of each confirmed payment made by your referees.</p>
          <h3 style={h3}>8.2 Withdrawal Lock</h3>
          <p style={p}>Withdrawals are locked until you have achieved 10 successful paid referrals — meaning 10 unique users who signed up via your code and subsequently made at least one confirmed payment.</p>
          <h3 style={h3}>8.3 Withdrawal Process</h3>
          <ul style={{ paddingLeft: 20, marginBottom: 12 }}>
            {['You may withdraw your entire balance at any time through the Referral Dashboard.','You must provide valid Nigerian bank account details.','Withdrawals are processed within 24 to 72 hours.','Minimum withdrawal amount: ₦1,000.'].map(t => <li key={t} style={li}>{t}</li>)}
          </ul>
          <h3 style={h3}>8.4 Balance as Course Credit</h3>
          <p style={p}>Alternatively, after achieving 10 successful paid referrals, you may apply your referral balance toward the purchase of any course instead of a cash withdrawal.</p>
        </div>

        {[
          { title: '9. Intellectual Property', content: <p style={p}>All content on the Platform is the exclusive property of Teamsamikoko Global Academy and TeamTega Technologies Limited. Personal use for study and reference is permitted.</p> },
          { title: '10. Prohibited Conduct', content: <ul style={{ paddingLeft: 20, marginBottom: 12 }}>{['Using automated tools or bots to access the Platform.','Sharing account credentials or selling access to your account.','Attempting to reverse-engineer, scrape, or copy course content.','Any activity that violates Nigerian law.'].map(t => <li key={t} style={li}>{t}</li>)}</ul> },
          { title: '11. Disclaimers', content: <p style={p}>The Platform is provided "as is." The AI tutor may occasionally produce incorrect information. Always validate code with authoritative documentation. The Academy makes no guarantee of employment or income outcomes.</p> },
          { title: '12. Governing Law', content: <p style={p}>These Terms are governed by the laws of the Federal Republic of Nigeria. Disputes shall be subject to the jurisdiction of the courts of Lagos State, Nigeria.</p> },
          { title: '13. Contact', content: <p style={p}>Questions? Use the Support/Enquiry form at <a href="https://mypytutor.com.ng" style={{ color: '#60a5fa' }}>mypytutor.com.ng</a> or via our <a href="https://whatsapp.com/channel/0029Vb6IDBz8V0tmPLtYwq2v" style={{ color: '#25D366' }}>WhatsApp Channel</a>.</p> },
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
