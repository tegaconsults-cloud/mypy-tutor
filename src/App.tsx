import React, { useEffect, useState } from 'react'
import { Routes, Route, useSearchParams } from 'react-router-dom'
import Header from './components/Header'
import Sidebar from './components/Sidebar'
import ChatPanel from './components/ChatPanel'
import CoursesPanel from './components/CoursesPanel'
import QuizPanel from './components/QuizPanel'
import ProgressPanel from './components/ProgressPanel'
import CertificatesPanel from './components/CertificatesPanel'
import PricingPanel from './components/PricingPanel'
import AuthModal from './components/AuthModal'
import BottomNav from './components/BottomNav'
import XPBar from './components/XPBar'
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
  const [searchParams] = useSearchParams()

  // Handle OAuth redirect params
  useEffect(() => {
    const auth = searchParams.get('auth')
    const msg = searchParams.get('msg')
    if (auth === 'google_success') {
      // handled in AuthModal via URL
    }
    if (auth === 'confirmed') {
      setAuthOpen(true)
      setAuthTab('signin')
    }
    const p = searchParams.get('panel') as Panel | null
    if (p) setPanel(p)
  }, [searchParams])

  // Refresh progress when user signs in
  useEffect(() => {
    if (user) refresh(user.learner_id)
  }, [user])

  const openAuth = (tab: 'signin' | 'signup' = 'signin') => {
    setAuthTab(tab)
    setAuthOpen(true)
  }

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh', background: '#0f1117' }}>
        <div className="loading-dots"><span/><span/><span/></div>
      </div>
    )
  }

  return (
    <Routes>
      {/* Landing pages */}
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
          />
          <XPBar />
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
            </div>
          </div>
          <BottomNav panel={panel} onPanelChange={setPanel} />
          {authOpen && (
            <AuthModal
              defaultTab={authTab}
              onClose={() => setAuthOpen(false)}
            />
          )}
        </>
      } />
    </Routes>
  )
}
