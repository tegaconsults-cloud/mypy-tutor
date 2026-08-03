import React, { useEffect, useRef, useState } from 'react'
import { Routes, Route, useSearchParams, useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
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
import EnquiryModal from './components/EnquiryModal'
import Logo from './components/Logo'
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
  const { user, loading, setUser, pendingAuthAction } = useAuth()
  const { refresh }       = useProgress()
  const navigate          = useNavigate()
  const [panel, setPanel] = useState<Panel>('chat')
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [authOpen, setAuthOpen]       = useState(false)
  const [authTab, setAuthTab]         = useState<'signin' | 'signup'>('signin')
  const [feedbackOpen, setFeedbackOpen]     = useState(false)
  const [referralOpen, setReferralOpen]     = useState(false)
  const [enquiryOpen,  setEnquiryOpen]      = useState(false)
  const [onboardingOpen, setOnboardingOpen] = useState(false)
  const [nudgeVisible, setNudgeVisible]     = useState(false)
  const [oauthError, setOauthError]         = useState('')
  const nudgeTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const [searchParams] = useSearchParams()

  // Open AuthModal automatically when password reset deep-link is detected
  useEffect(() => {
    if (pendingAuthAction === 'reset') {
      setAuthOpen(true)
      // Tab switching handled inside AuthModal via pendingAuthAction
    }
  }, [pendingAuthAction])

  useEffect(() => {
    const auth = searchParams.get('auth')
    if (!auth) return
    if (auth === 'google_success' || auth === 'github_success') {
      // Handled by AuthContext — setUser already called there
      navigate('/', { replace: true })
    } else if (auth === 'confirmed') {
      setAuthOpen(true); setAuthTab('signin'); navigate('/', { replace: true })
    } else if (auth === 'reset') {
      // Handled by AuthContext — pendingAuthAction set there, picked up above
      navigate('/', { replace: true })
    } else if (auth === 'error') {
      setOauthError(decodeURIComponent(searchParams.get('msg') || 'Authentication failed.')); navigate('/', { replace: true })
    }
    const p = searchParams.get('panel') as Panel | null
    if (p) setPanel(p)
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (user) {
      refresh(user.learner_id)
      if (!localStorage.getItem('mpt_onboarded')) setTimeout(() => setOnboardingOpen(true), 400)
    }
  }, [user])

  useEffect(() => {
    const handler = (e: Event) => setPanel((e as CustomEvent<Panel>).detail)
    window.addEventListener('switch-panel', handler)
    return () => window.removeEventListener('switch-panel', handler)
  }, [])

  useEffect(() => {
    if (!loading && !user) {
      nudgeTimer.current = setTimeout(() => setNudgeVisible(true), 8000)
    }
    return () => { if (nudgeTimer.current) clearTimeout(nudgeTimer.current) }
  }, [loading, user])

  useEffect(() => {
    const h = () => setFeedbackOpen(true)
    window.addEventListener('open-feedback', h)
    return () => window.removeEventListener('open-feedback', h)
  }, [])

  useEffect(() => {
    const h = () => setEnquiryOpen(true)
    window.addEventListener('open-enquiry', h)
    return () => window.removeEventListener('open-enquiry', h)
  }, [])

  const openAuth = (tab: 'signin' | 'signup' = 'signin') => {
    setAuthTab(tab); setAuthOpen(true); setNudgeVisible(false); setOauthError('')
  }

  const handleOnboardingDone = (firstMsg: string) => {
    setOnboardingOpen(false); setPanel('chat')
    setTimeout(() => window.dispatchEvent(new CustomEvent('sidebar-ask', { detail: firstMsg })), 300)
  }

  if (loading) return (
    <div className="flex items-center justify-center h-full" style={{ background: '#060d1c' }}>
      <div className="flex flex-col items-center gap-4">
        <div className="w-16 h-16 rounded-2xl overflow-hidden"
          style={{ background: '#fff', border: '3px solid rgba(224,163,0,0.5)', boxShadow: '0 0 40px rgba(13,71,161,0.5)' }}>
          <img src="/icons/mypytutor_logo.jpg" alt="MyPy Tutor" style={{ width: '100%', height: '100%', objectFit: 'contain' }} />
        </div>
        <div className="loading-dots"><span /><span /><span /></div>
      </div>
    </div>
  )

  return (
    <Routes>
      <Route path="/learn-python"              element={<LearnPythonPage />} />
      <Route path="/python-course"             element={<PythonCoursePage />} />
      <Route path="/python-for-beginners"      element={<BeginnerPage />} />
      <Route path="/ai-python-tutor"           element={<AiTutorPage />} />
      <Route path="/python-certification"      element={<CertificationPage />} />
      <Route path="/python-interview-questions"element={<InterviewPage />} />
      <Route path="/python-quizzes"            element={<QuizzesPage />} />

      <Route path="*" element={
        <div className="flex flex-col h-full overflow-hidden" style={{ background: '#060d1c' }}>
          <Header panel={panel} onPanelChange={setPanel} onMenuClick={() => setSidebarOpen(true)}
            onAuthClick={openAuth} onReferralClick={() => setReferralOpen(true)} />
          <XPBar />
          <PromptCounterBar />

          <div className="flex-1 flex overflow-hidden relative">
            <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)}
              onPanelChange={setPanel} onAuthClick={openAuth} />

            <AnimatePresence mode="wait">
              <motion.div key={panel} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                transition={{ duration: 0.12 }}
                className="flex-1 flex flex-col overflow-hidden">
                {panel === 'chat'         && <ChatPanel onAuthClick={openAuth} />}
                {panel === 'courses'      && <CoursesPanel />}
                {panel === 'quiz'         && <QuizPanel />}
                {panel === 'progress'     && <ProgressPanel />}
                {panel === 'certificates' && <CertificatesPanel />}
                {panel === 'pricing'      && <PricingPanel />}
                {panel === 'profile'      && <ProfilePanel />}
              </motion.div>
            </AnimatePresence>
          </div>

          <BottomNav panel={panel as 'chat'|'courses'|'quiz'|'progress'|'certificates'|'pricing'}
            onPanelChange={p => setPanel(p)} />

          {/* Modals */}
          {authOpen      && <AuthModal defaultTab={authTab} onClose={() => setAuthOpen(false)} />}
          {feedbackOpen  && <FeedbackModal onClose={() => setFeedbackOpen(false)} />}
          {enquiryOpen   && <EnquiryModal onClose={() => setEnquiryOpen(false)} />}
          {referralOpen && user && <ReferralModal onClose={() => setReferralOpen(false)} />}
          {onboardingOpen && <OnboardingModal onDone={handleOnboardingDone} />}

          {/* Auth nudge */}
          <AnimatePresence>
            {nudgeVisible && !user && (
              <motion.div key="nudge"
                initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 20 }}
                className="fixed bottom-20 left-1/2 -translate-x-1/2 z-50 max-w-sm w-[calc(100%-32px)]"
                style={{ filter: 'drop-shadow(0 8px 32px rgba(0,0,0,.7))' }}>
                <div className="rounded-2xl p-4 border"
                  style={{ background: '#0f1a2e', border: '1px solid rgba(13,71,161,0.4)', boxShadow: '0 8px 40px rgba(0,0,0,.6)' }}>
                  <div className="flex items-start justify-between gap-3 mb-3">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <div className="w-6 h-6 rounded-full overflow-hidden shrink-0"
                          style={{ background: '#fff' }}>
                          <img src="/icons/mypytutor_logo.jpg" alt="" style={{ width: '100%', height: '100%', objectFit: 'contain' }} />
                        </div>
                        <p className="font-bold text-sm text-white">Save your progress!</p>
                      </div>
                      <p className="text-xs leading-relaxed" style={{ color: '#94a3b8' }}>
                        Sign in to keep chat history, earn XP, and unlock courses.
                      </p>
                    </div>
                    <button onClick={() => setNudgeVisible(false)} className="btn btn-ghost btn-sm w-7 h-7 p-0 shrink-0 rounded-xl">✕</button>
                  </div>
                  <div className="flex gap-2">
                    <button onClick={() => openAuth('signup')} className="btn btn-primary flex-1 btn-sm"
                      style={{ background: 'linear-gradient(135deg,#0D47A1,#E0A300)' }}>
                      🚀 Sign Up Free
                    </button>
                    <button onClick={() => openAuth('signin')} className="btn btn-secondary flex-1 btn-sm">
                      Sign In
                    </button>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* OAuth error */}
          <AnimatePresence>
            {oauthError && (
              <motion.div key="oauth-err"
                initial={{ opacity: 0, y: -16 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -16 }}
                className="fixed top-20 left-1/2 -translate-x-1/2 z-50 max-w-sm w-[calc(100%-32px)]">
                <div className="rounded-2xl px-4 py-3 border flex items-center gap-3"
                  style={{ background: 'rgba(239,68,68,0.12)', backdropFilter: 'blur(12px)', borderColor: 'rgba(239,68,68,0.3)' }}>
                  <span className="text-sm flex-1" style={{ color: '#fca5a5' }}>⚠️ {oauthError}</span>
                  <button onClick={() => setOauthError('')} className="text-base" style={{ color: '#4d6080' }}>✕</button>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      } />
    </Routes>
  )
}
