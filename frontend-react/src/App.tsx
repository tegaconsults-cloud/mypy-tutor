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

const PANEL_TITLES: Record<Panel, string> = {
  chat: 'AI Chat', courses: 'Courses', quiz: 'Quiz', progress: 'Progress',
  certificates: 'Certificates', pricing: 'Plans', profile: 'Profile',
}

export default function App() {
  const { user, loading, setUser } = useAuth()
  const { refresh }       = useProgress()
  const navigate          = useNavigate()
  const [panel, setPanel] = useState<Panel>('chat')
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [authOpen, setAuthOpen]       = useState(false)
  const [authTab, setAuthTab]         = useState<'signin' | 'signup'>('signin')
  const [feedbackOpen, setFeedbackOpen]   = useState(false)
  const [referralOpen, setReferralOpen]   = useState(false)
  const [onboardingOpen, setOnboardingOpen] = useState(false)
  const [nudgeVisible, setNudgeVisible]   = useState(false)
  const [oauthError, setOauthError]       = useState('')
  const nudgeTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const [searchParams] = useSearchParams()

  // Handle OAuth redirect — runs once on mount
  useEffect(() => {
    const auth = searchParams.get('auth')
    if (!auth) return

    if (auth === 'google_success') {
      // Backend URL-encoded JSON in the `user` param
      const userParam = searchParams.get('user')
      if (userParam) {
        try {
          const parsed = JSON.parse(decodeURIComponent(userParam))
          if (parsed.token && parsed.learner_id) {
            setUser(parsed)   // stores token, sets user state
            // Clean the URL so the params don't persist on refresh
            navigate('/', { replace: true })
            return
          }
        } catch (e) {
          console.error('Failed to parse Google OAuth user param', e)
        }
      }
      setOauthError('Google sign-in failed. Please try again.')
      navigate('/', { replace: true })
    } else if (auth === 'confirmed') {
      setAuthOpen(true)
      setAuthTab('signin')
      navigate('/', { replace: true })
    } else if (auth === 'error') {
      const msg = searchParams.get('msg') || 'Authentication failed.'
      setOauthError(decodeURIComponent(msg))
      navigate('/', { replace: true })
    }

    const p = searchParams.get('panel') as Panel | null
    if (p) setPanel(p)
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // On login: refresh XP, show onboarding once
  useEffect(() => {
    if (user) {
      refresh(user.learner_id)
      if (!localStorage.getItem('mpt_onboarded')) {
        setTimeout(() => setOnboardingOpen(true), 400)
      }
    }
  }, [user])

  // Switch panel via custom event (from CoursesPanel/QuizPanel)
  useEffect(() => {
    const handler = (e: Event) => setPanel((e as CustomEvent<Panel>).detail)
    window.addEventListener('switch-panel', handler)
    return () => window.removeEventListener('switch-panel', handler)
  }, [])

  // Auth nudge for guests after 8s
  useEffect(() => {
    if (!loading && !user) {
      nudgeTimer.current = setTimeout(() => setNudgeVisible(true), 8000)
    }
    return () => { if (nudgeTimer.current) clearTimeout(nudgeTimer.current) }
  }, [loading, user])

  // Feedback event from Sidebar
  useEffect(() => {
    const h = () => setFeedbackOpen(true)
    window.addEventListener('open-feedback', h)
    return () => window.removeEventListener('open-feedback', h)
  }, [])

  const openAuth = (tab: 'signin' | 'signup' = 'signin') => {
    setAuthTab(tab); setAuthOpen(true); setNudgeVisible(false); setOauthError('')
  }

  const handleOnboardingDone = (firstMsg: string) => {
    setOnboardingOpen(false); setPanel('chat')
    setTimeout(() => window.dispatchEvent(new CustomEvent('sidebar-ask', { detail: firstMsg })), 300)
  }

  if (loading) return (
    <div className="flex items-center justify-center h-full" style={{ background: '#0f172a' }}>
      <div className="flex flex-col items-center gap-4">
        <Logo size={64} shape="circle" style={{ border: '3px solid rgba(37,99,235,0.4)', boxShadow: '0 0 32px rgba(37,99,235,0.35)' }} />
        <div className="loading-dots"><span /><span /><span /></div>
      </div>
    </div>
  )

  return (
    <Routes>
      <Route path="/learn-python"             element={<LearnPythonPage />} />
      <Route path="/python-course"            element={<PythonCoursePage />} />
      <Route path="/python-for-beginners"     element={<BeginnerPage />} />
      <Route path="/ai-python-tutor"          element={<AiTutorPage />} />
      <Route path="/python-certification"     element={<CertificationPage />} />
      <Route path="/python-interview-questions" element={<InterviewPage />} />
      <Route path="/python-quizzes"           element={<QuizzesPage />} />

      <Route path="*" element={
        <div className="flex flex-col h-full overflow-hidden">
          <Header panel={panel} onPanelChange={setPanel} onMenuClick={() => setSidebarOpen(true)}
            onAuthClick={openAuth} onReferralClick={() => setReferralOpen(true)} />
          <XPBar />
          <PromptCounterBar />

          <div className="flex-1 flex overflow-hidden relative">
            <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)}
              onPanelChange={setPanel} onAuthClick={openAuth} />

            <AnimatePresence mode="wait">
              <motion.div key={panel} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                transition={{ duration: 0.15 }}
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

          <BottomNav panel={panel as 'chat' | 'courses' | 'quiz' | 'progress' | 'certificates' | 'pricing'} onPanelChange={p => setPanel(p)} />

          {/* Modals */}
          {authOpen && <AuthModal defaultTab={authTab} onClose={() => setAuthOpen(false)} />}
          {feedbackOpen && <FeedbackModal onClose={() => setFeedbackOpen(false)} />}
          {referralOpen && user && <ReferralModal onClose={() => setReferralOpen(false)} />}
          {onboardingOpen && <OnboardingModal onDone={handleOnboardingDone} />}

          {/* Auth nudge for guests */}
          <AnimatePresence>
            {nudgeVisible && !user && (
              <motion.div key="nudge"
                initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 20 }}
                className="fixed bottom-20 left-1/2 -translate-x-1/2 z-50 max-w-sm w-[calc(100%-32px)]"
                style={{ filter: 'drop-shadow(0 8px 32px rgba(0,0,0,.6))' }}>
                <div className="rounded-2xl p-4 border border-blue-500/30"
                  style={{ background: '#1e293b', boxShadow: '0 8px 40px rgba(0,0,0,.5)' }}>
                  <div className="flex items-start justify-between gap-3 mb-3">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <Logo size={24} shape="circle" />
                        <p className="font-bold text-sm text-slate-100">Save your progress!</p>
                      </div>
                      <p className="text-xs text-slate-400 leading-relaxed">
                        Sign in to keep chat history, earn XP, and unlock courses.
                      </p>
                    </div>
                    <button onClick={() => setNudgeVisible(false)} className="btn btn-ghost btn-sm w-7 h-7 p-0 shrink-0 rounded-xl">
                      ✕
                    </button>
                  </div>
                  <div className="flex gap-2">
                    <button onClick={() => openAuth('signup')} className="btn btn-primary flex-1 btn-sm">🚀 Sign Up Free</button>
                    <button onClick={() => openAuth('signin')} className="btn btn-secondary flex-1 btn-sm">Sign In</button>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* OAuth error toast */}
          <AnimatePresence>
            {oauthError && (
              <motion.div key="oauth-error"
                initial={{ opacity: 0, y: -16 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -16 }}
                className="fixed top-20 left-1/2 -translate-x-1/2 z-50 max-w-sm w-[calc(100%-32px)]">
                <div className="rounded-2xl px-4 py-3 border border-red-500/30 flex items-center gap-3"
                  style={{ background: 'rgba(239,68,68,0.12)', backdropFilter: 'blur(12px)', boxShadow: '0 8px 32px rgba(0,0,0,.5)' }}>
                  <span className="text-red-400 text-sm flex-1">⚠️ {oauthError}</span>
                  <button onClick={() => setOauthError('')} className="text-slate-500 hover:text-slate-300 transition-colors shrink-0 text-base">✕</button>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      } />
    </Routes>
  )
}
