import React, { useEffect, useRef, useState } from 'react'
import { Routes, Route, useSearchParams } from 'react-router-dom'
import Header from './components/Header'
import Sidebar from './components/Sidebar'
import ChatPanel from './components/ChatPanel'
import CoursesPanel from './components/CoursesPanel'
import QuizPanel from './components/QuizPanel'
import ProgressPanel from './components/ProgressPanel'
import CertificatesPanel from './components/CertificatesPanel'
import PricingPanel from './components/PricingPanel'
import ProfilePanel from './components/ProfilePanel'
import AuthModal from './components/AuthModal'
import BottomNav from './components/BottomNav'
import XPBar from './components/XPBar'
import PromptCounterBar from './components/PromptCounterBar'
import FeedbackModal from './components/FeedbackModal'
import ReferralModal from './components/ReferralModal'
import OnboardingModal from './components/OnboardingModal'
import { useAuth } from './context/AuthContext'
import { useProgress } from './context/ProgressContext'
import LearnPythonPage from './pages/LearnPython'
import PythonCoursePage from './pages/PythonCourse'
import BeginnerPage from './pages/PythonForBeginners'
import AiTutorPage from './pages/AiPythonTutor'
import CertificationPage from './pages/PythonCertification'
import InterviewPage from './pages/PythonInterviewQuestions'
import QuizzesPage from './pages/PythonQuizzes'

type Panel = 'chat' | 'courses' | 'quiz' | 'progress' | 'certificates' | 'pricing' | 'profile'

export default function App() {
  const { user, loading } = useAuth()
  const { refresh } = useProgress()
  const [panel, setPanel] = useState<Panel>('chat')
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [authOpen, setAuthOpen] = useState(false)
  const [authTab, setAuthTab] = useState<'signin' | 'signup'>('signin')
  const [feedbackOpen, setFeedbackOpen] = useState(false)
  const [referralOpen, setReferralOpen] = useState(false)
  const [onboardingOpen, setOnboardingOpen] = useState(false)
  const [nudgeVisible, setNudgeVisible] = useState(false)
  const nudgeTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const [searchParams] = useSearchParams()

  // Handle OAuth redirect params
  useEffect(() => {
    const auth = searchParams.get('auth')
    if (auth === 'confirmed') {
      setAuthOpen(true)
      setAuthTab('signin')
    }
    const p = searchParams.get('panel') as Panel | null
    if (p) setPanel(p)
  }, [searchParams])

  // Refresh progress when user signs in; show onboarding once
  useEffect(() => {
    if (user) {
      refresh(user.learner_id)
      if (!localStorage.getItem('mpt_onboarded')) {
        setTimeout(() => setOnboardingOpen(true), 400)
      }
    }
  }, [user])

  // Show sign-in nudge to unauthenticated users after 8 seconds
  useEffect(() => {
    if (!loading && !user) {
      nudgeTimerRef.current = setTimeout(() => {
        setNudgeVisible(true)
      }, 8000)
    }
    return () => {
      if (nudgeTimerRef.current) clearTimeout(nudgeTimerRef.current)
    }
  }, [loading, user])

  // Listen for feedback event dispatched from Sidebar
  useEffect(() => {
    const handler = () => setFeedbackOpen(true)
    window.addEventListener('open-feedback', handler)
    return () => window.removeEventListener('open-feedback', handler)
  }, [])

  const openAuth = (tab: 'signin' | 'signup' = 'signin') => {
    setAuthTab(tab)
    setAuthOpen(true)
    setNudgeVisible(false)
  }

  const handleOnboardingDone = (firstMsg: string) => {
    setOnboardingOpen(false)
    setPanel('chat')
    setTimeout(() => {
      window.dispatchEvent(new CustomEvent('sidebar-ask', { detail: firstMsg }))
    }, 300)
  }

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh', background: '#0f1117' }}>
        <div className="loading-dots"><span /><span /><span /></div>
      </div>
    )
  }

  return (
    <Routes>
      {/* SEO Landing pages */}
      <Route path="/learn-python" element={<LearnPythonPage />} />
      <Route path="/python-course" element={<PythonCoursePage />} />
      <Route path="/python-for-beginners" element={<BeginnerPage />} />
      <Route path="/ai-python-tutor" element={<AiTutorPage />} />
      <Route path="/python-certification" element={<CertificationPage />} />
      <Route path="/python-interview-questions" element={<InterviewPage />} />
      <Route path="/python-quizzes" element={<QuizzesPage />} />

      {/* Main app */}
      <Route path="*" element={
        <>
          <Header
            panel={panel}
            onPanelChange={setPanel}
            onMenuClick={() => setSidebarOpen(true)}
            onAuthClick={openAuth}
            onReferralClick={() => setReferralOpen(true)}
          />
          <XPBar />
          <PromptCounterBar />

          <div style={{ flex: 1, display: 'flex', overflow: 'hidden', position: 'relative' }}>
            <Sidebar
              open={sidebarOpen}
              onClose={() => setSidebarOpen(false)}
              onPanelChange={setPanel}
              onAuthClick={openAuth}
            />
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
              {panel === 'chat'         && <ChatPanel onAuthClick={openAuth} />}
              {panel === 'courses'      && <CoursesPanel />}
              {panel === 'quiz'         && <QuizPanel />}
              {panel === 'progress'     && <ProgressPanel />}
              {panel === 'certificates' && <CertificatesPanel />}
              {panel === 'pricing'      && <PricingPanel />}
              {panel === 'profile'      && <ProfilePanel />}
            </div>
          </div>

          <BottomNav panel={panel} onPanelChange={setPanel} />

          {/* Auth modal */}
          {authOpen && (
            <AuthModal
              defaultTab={authTab}
              onClose={() => setAuthOpen(false)}
            />
          )}

          {/* Feedback modal */}
          {feedbackOpen && (
            <FeedbackModal onClose={() => setFeedbackOpen(false)} />
          )}

          {/* Referral modal — only for signed-in users */}
          {referralOpen && user && (
            <ReferralModal onClose={() => setReferralOpen(false)} />
          )}

          {/* Onboarding — shown once after first login */}
          {onboardingOpen && (
            <OnboardingModal onDone={handleOnboardingDone} />
          )}

          {/* Auth nudge toast for unauthenticated visitors */}
          {nudgeVisible && !user && (
            <div style={{
              position: 'fixed', bottom: 70, left: '50%', transform: 'translateX(-50%)',
              background: '#1a202c', border: '1px solid #3182ce',
              borderRadius: 14, padding: '14px 20px', zIndex: 800,
              boxShadow: '0 8px 32px rgba(0,0,0,.6)', maxWidth: 360, width: 'calc(100% - 32px)',
              display: 'flex', flexDirection: 'column', gap: 10,
            }} className="slide-in">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                  <div style={{ fontWeight: 700, color: '#e2e8f0', fontSize: '.92rem' }}>🐍 Save your progress!</div>
                  <div style={{ fontSize: '.8rem', color: '#718096', marginTop: 4, lineHeight: 1.5 }}>
                    Sign in or create a free account to keep your chat history, earn XP, and unlock courses.
                  </div>
                </div>
                <button onClick={() => setNudgeVisible(false)} style={{ background: 'transparent', border: 'none', color: '#718096', cursor: 'pointer', fontSize: '1rem', marginLeft: 8, flexShrink: 0 }}>✕</button>
              </div>
              <div style={{ display: 'flex', gap: 8 }}>
                <button onClick={() => openAuth('signup')} className="btn btn-primary" style={{ flex: 1 }}>🚀 Sign Up Free</button>
                <button onClick={() => openAuth('signin')} className="btn btn-secondary" style={{ flex: 1 }}>Sign In</button>
              </div>
            </div>
          )}
        </>
      } />
    </Routes>
  )
}
