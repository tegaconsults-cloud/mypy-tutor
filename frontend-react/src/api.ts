// ── API client for MyPy Tutor backend ────────────────────────────────────
// All fetch calls go through here. API_BASE points to the Render backend.
// Last updated: 2026-08-03

export const API_BASE = 'https://mypytutor.onrender.com'

function url(path: string) {
  return API_BASE + path
}

// ── Auth ──────────────────────────────────────────────────────────────────

export async function getAuthConfig() {
  const r = await fetch(url('/auth/config'))
  return r.json()
}

export async function signIn(email: string, password: string) {
  const r = await fetch(url('/auth/signin'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  })
  const data = await r.json()
  if (!r.ok) throw new Error(data.detail || data.error || 'Sign in failed')
  return data as { token: string; learner_id: string; name: string; email: string; picture: string }
}

export async function signUp(name: string, email: string, password: string, access_code = '') {
  const r = await fetch(url('/auth/signup'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, email, password, access_code }),
  })
  const data = await r.json()
  if (!r.ok) throw new Error(data.detail || data.error || 'Sign up failed')
  return data
}

export async function getMe(token: string) {
  const r = await fetch(url('/auth/me'), {
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!r.ok) throw new Error('Session expired')
  return r.json()
}

export async function forgotPassword(email: string) {
  const r = await fetch(url('/auth/forgot-password'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email }),
  })
  return r.json()
}

export async function resetPassword(token: string, new_password: string) {
  const r = await fetch(url('/auth/reset-password'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ token, new_password }),
  })
  const data = await r.json()
  if (!r.ok) throw new Error(data.detail || data.error || 'Reset failed')
  return data
}

export async function resendConfirmation(email: string) {
  const r = await fetch(url('/auth/resend-confirmation'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email }),
  })
  return r.json()
}

export async function getProfile(learnerId: string) {
  const r = await fetch(url(`/auth/profile/${learnerId}`))
  if (!r.ok) return null
  return r.json()
}

export async function saveProfile(learnerId: string, body: Record<string, string>) {
  const r = await fetch(url(`/auth/profile/${learnerId}`), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  return r.json()
}

export async function requestReferralWithdrawal(payload: {
  learner_id: string
  email: string
  amount: number
  bank_name: string
  account_name: string
  account_num: string
}) {
  const r = await fetch(url('/referral/withdraw'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  const data = await r.json()
  if (!r.ok) throw new Error(data.error || data.detail || data.message || 'Withdrawal request failed')
  return data
}

export async function getReferralWithdrawals(learnerId: string) {
  const r = await fetch(url(`/referral/withdrawals/${learnerId}`))
  if (!r.ok) return null
  return r.json()
}

// ── Chat ──────────────────────────────────────────────────────────────────

export async function sendChat(payload: {
  message: string
  history: { role: string; content: string }[]
  learner_id: string
  level: string
  conversation_id?: string | null
}) {
  const r = await fetch(url('/chat'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  const data = await r.json()
  if (!r.ok) {
    const err = data as { error?: string; detail?: string; limit?: number; message?: string }
    throw Object.assign(new Error(err.message || err.error || err.detail || `Error ${r.status}`), { data, status: r.status })
  }
  return data
}

// ── Progress ──────────────────────────────────────────────────────────────

export async function getProgress(learnerId: string) {
  const r = await fetch(url(`/progress/${learnerId}`))
  if (!r.ok) return null
  return r.json()
}

export async function getPromptCount(learnerId: string) {
  const r = await fetch(url(`/prompts/count?learner_id=${learnerId}`))
  if (!r.ok) return null
  return r.json()
}

// ── Courses ───────────────────────────────────────────────────────────────

export async function getCatalog() {
  const r = await fetch(url('/courses/catalog'))
  if (!r.ok) return null
  return r.json()
}

export async function getLearnerCourses(learnerId: string) {
  const r = await fetch(url(`/learner/courses/${learnerId}`))
  if (!r.ok) return null
  return r.json()
}

export async function startCourse(learnerId: string, courseName: string) {
  const r = await fetch(url(`/course/start?learner_id=${learnerId}&course_name=${encodeURIComponent(courseName)}`), {
    method: 'POST',
  })
  const data = await r.json()
  if (!r.ok) throw Object.assign(new Error(data.error || data.detail || 'Failed'), { data, status: r.status })
  return data
}

export async function nextCourseStep(learnerId: string) {
  const r = await fetch(url(`/course/next?learner_id=${learnerId}`), { method: 'POST' })
  const data = await r.json()
  if (!r.ok) throw new Error(data.error || 'Failed')
  return data
}

// ── Quiz ──────────────────────────────────────────────────────────────────

export async function generateQuiz(learnerId: string, topic: string, level: string) {
  const r = await fetch(url('/quiz/generate'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ learner_id: learnerId, topic, level }),
  })
  const data = await r.json()
  if (!r.ok) throw new Error(data.detail || 'Failed')
  return data
}

export async function submitQuizAnswer(learnerId: string, topic: string, level: string, question: string, answer: string) {
  const r = await fetch(url('/quiz/answer'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ learner_id: learnerId, topic, level, question, answer }),
  })
  return r.json()
}

// ── Topics ────────────────────────────────────────────────────────────────

export async function getTopics() {
  const r = await fetch(url('/topics'))
  if (!r.ok) return { topics: [] }
  return r.json()
}

// ── Feedback ──────────────────────────────────────────────────────────────

export async function submitFeedback(payload: {
  learner_id: string; overall: number; clarity: number
  helpfulness: number; suggestion: string; would_recommend: boolean
}) {
  const r = await fetch(url('/feedback/survey'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  return r.json()
}

// ── Conversations ─────────────────────────────────────────────────────────

export async function getConversations(learnerId: string) {
  const r = await fetch(url(`/conversations/${learnerId}`))
  if (!r.ok) return null
  return r.json()
}

export async function newConversation(learnerId: string) {
  const r = await fetch(url(`/conversations/${learnerId}/new`), { method: 'POST' })
  if (!r.ok) return null
  return r.json()
}

// ── Health (backend warmup) ───────────────────────────────────────────────

export async function ping() {
  try { await fetch(url('/health')) } catch (_) {}
}
