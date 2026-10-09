import type {
  AuthResponse, ChatRequest, ChatResponse, ProgressResponse,
  QuizResponse, QuizAnswerResponse, DashboardData, AdminUsersResponse,
  Payment, BankProof, CertRecord, Coupon, Announcement, TeamMember,
  Task, Invoice, WithdrawalRequest, Enquiry, ReferralStats,
  TTSPrepareResponse, TTSVoicesResponse, UserProfile, Level, Tier,
} from './types';

// ─── Base URL ─────────────────────────────────────────────────────────────────
export const API_BASE =
  import.meta.env.VITE_API_BASE ??
  (location.hostname === 'localhost' || location.hostname === '127.0.0.1'
    ? `http://${location.host}`
    : location.origin);

// ─── Core fetch helper ────────────────────────────────────────────────────────
async function req<T>(
  path: string,
  opts: RequestInit = {},
  token?: string,
): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(opts.headers as Record<string, string> ?? {}),
  };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  // 60-second timeout for chat/LLM calls — Groq responses can take 10-15s
  // on Render free tier; 30s was too tight for users on slow connections.
  const isLlmCall = path === '/chat' || path.startsWith('/quiz') || path.startsWith('/course') || path.startsWith('/exercise');
  const timeoutMs  = isLlmCall ? 60_000 : 30_000;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      ...opts,
      headers,
      signal: controller.signal,
    });
  } catch (err: unknown) {
    clearTimeout(timer);
    // Normalise ALL network/abort errors into a single detectable message
    const msg = (err instanceof Error ? err.message : String(err)).toLowerCase();
    const isAbort = msg.includes('abort') || msg.includes('cancel') || msg.includes('timed out');
    throw new Error(
      isAbort
        ? 'Request timed out — Sir. Tega is warming up. Please try again in a moment.'
        : `Sir. Tega is warming up. Please try again. (${msg})`
    );
  }
  clearTimeout(timer);

  if (!res.ok) {
    let msg = `HTTP ${res.status}`;
    try {
      const d = await res.json();
      msg = d.error ?? d.detail ?? msg;
    } catch { /* */ }
    // Map 502/503 explicitly to a warming-up message the UI can detect
    if (res.status === 503 || res.status === 502) {
      throw new Error(`Sir. Tega is warming up — ${msg}. Please try again in a moment.`);
    }
    throw new Error(msg);
  }
  return res.json() as Promise<T>;
}

function get<T>(path: string, token?: string) {
  return req<T>(path, { method: 'GET' }, token);
}
function post<T>(path: string, body?: unknown, token?: string) {
  return req<T>(path, { method: 'POST', body: body ? JSON.stringify(body) : undefined }, token);
}
function del<T>(path: string, token?: string) {
  return req<T>(path, { method: 'DELETE' }, token);
}
function put<T>(path: string, body?: unknown, token?: string) {
  return req<T>(path, { method: 'PUT', body: body ? JSON.stringify(body) : undefined }, token);
}

// ─── Auth ─────────────────────────────────────────────────────────────────────
export const authApi = {
  config:  () => get<{ google_client_id: string; google_enabled: boolean }>('/auth/config'),
  me:      (token: string) => get<AuthResponse>('/auth/me', token),
  signIn:  (email: string, password: string) =>
    post<AuthResponse>('/auth/signin', { email, password }),
  signUp:  (email: string, name: string, password: string, access_code?: string, terms_accepted?: boolean) =>
    post<{ ok: boolean; message: string }>('/auth/signup', { email, name, password, access_code: access_code ?? '', terms_accepted: terms_accepted ?? false }),
  confirm: (token: string) => get<{ ok: boolean; message: string }>(`/auth/confirm?token=${token}`),
  resendConfirmation: (email: string) =>
    post<{ ok: boolean }>('/auth/resend-confirmation', { email }),
  forgotPassword: (email: string) =>
    post<{ ok: boolean }>('/auth/forgot-password', { email }),
  resetPassword: (token: string, new_password: string) =>
    post<{ ok: boolean }>('/auth/reset-password', { token, new_password }),
  deleteAccount: (token: string) =>
    del<{ ok: boolean }>('/auth/account', token),
  googleLogin:  () => { window.location.href = `${API_BASE}/auth/google/login`; },
  githubLogin:  () => { window.location.href = `${API_BASE}/auth/github/login`; },
  validateCode: (code: string) =>
    post<{ valid: boolean; code_type?: string; tier?: string; message: string }>('/auth/validate-code', { code }),
};

// ─── Chat ─────────────────────────────────────────────────────────────────────
export const chatApi = {
  send: (body: ChatRequest, token?: string) =>
    post<ChatResponse>('/chat', body, token),
  /** Call on page mount — initialises the Groq client before first message */
  wake: () => fetch(`${API_BASE}/wake`).catch(() => null),
};

// ─── Progress ─────────────────────────────────────────────────────────────────
export const progressApi = {
  get:    (learner_id: string, token: string) =>
    get<ProgressResponse>(`/progress/${learner_id}`, token),
  promptCount: (learner_id: string, token?: string) =>
    get<{ learner_id: string; count: number; limit: number; date: string }>(
      `/prompts/count?learner_id=${learner_id}`, token
    ),
};

// ─── Courses ──────────────────────────────────────────────────────────────────
export const coursesApi = {
  list:     (token?: string) => get<{ courses: unknown[] }>('/courses', token),
  catalog:  ()               => get<Record<string, unknown>>('/courses/catalog'),
  start:    (learner_id: string, course_name: string, token: string) =>
    post<{ step: number; title: string; content: string; total_steps: number }>(
      '/course/start', { learner_id, course_name }, token
    ),
  next: (learner_id: string, token: string) =>
    post<{ completed: boolean; content: string; step?: number; title?: string; total_steps?: number }>(
      '/course/next', undefined, token
    ).then(d => d),
  learnerCourses: (learner_id: string, token: string) =>
    get<{ courses: unknown[]; total: number }>(`/learner/courses/${learner_id}`, token),
};

// ─── Quiz ─────────────────────────────────────────────────────────────────────
export const quizApi = {
  generate: (learner_id: string, topic: string, level: Level, token?: string) =>
    post<QuizResponse>('/quiz/generate', { learner_id, topic, level }, token),
  answer: (body: {
    learner_id: string; topic: string; level: Level;
    question: string; answer: string;
  }, token?: string) =>
    post<QuizAnswerResponse>('/quiz/answer', body, token),
};

// ─── TTS ──────────────────────────────────────────────────────────────────────
export const ttsApi = {
  prepare: (text: string) =>
    post<TTSPrepareResponse>('/tts/prepare', { text }),
  voices:  () => get<TTSVoicesResponse>('/tts/voices'),
};

// ─── Payments ─────────────────────────────────────────────────────────────────
export const paymentsApi = {
  bankDetails: () => get<{ bank_name: string; account_name: string; account_number: string; instructions: string[]; plans: unknown[] }>('/payments/bank-details'),

  /** Provision or retrieve a Paystack dedicated virtual account for the user */
  getDedicatedAccount: (learner_id: string, token: string) =>
    get<{
      ok: boolean;
      account_number: string;
      bank_name: string;
      account_name: string;
      customer_code: string;
      plans: { name: string; amount: number; tier: string }[];
      instructions: string[];
    }>(`/payments/dedicated-account/${learner_id}`, token),

  /** Force-provision a new DVA (called on payment panel open) */
  provisionDedicatedAccount: (token: string) =>
    post<{
      ok: boolean;
      account_number: string;
      bank_name: string;
      account_name: string;
      plans: { name: string; amount: number; tier: string }[];
    }>('/payments/dedicated-account', undefined, token),

  /** Dynamic Paystack checkout — returns authorization_url with amount+course+learner pre-loaded */
  initialize: (body: {
    learner_id: string;
    amount_ngn: number;
    plan: string;
    course_name?: string;
    coupon_code?: string;
  }, token: string) =>
    post<{ authorization_url: string; reference: string; amount_ngn: number; plan: string }>(
      '/payments/paystack/initialize', body, token
    ),

  /** Submit bank transfer proof — always sends JSON (image as base64 data URI) */
  submitProof: (body: {
    plan: string;
    amount: number;
    reference?: string;
    proof_image_base64?: string;
    proof_url?: string;
    notes?: string;
  }, token: string) =>
    post<{ ok: boolean; proof_id: string; status: string; message: string }>(
      '/payments/bank-transfer/submit', body, token
    ),

  proofStatus: (learner_id: string, token: string) =>
    get<{ proofs: unknown[]; total: number }>(`/payments/bank-transfer/status/${learner_id}`, token),

  metadata: (learner_id: string, token: string) =>
    get<{ metadata: unknown }>(`/payments/metadata/${learner_id}`, token),
};

// ─── Referrals ────────────────────────────────────────────────────────────────
export const referralApi = {
  get:    (learner_id: string, token: string) =>
    get<ReferralStats>(`/referral/${learner_id}`, token),
  balance: (learner_id: string, token: string) =>
    get<{ balance: number }>(`/referral/balance/${learner_id}`, token),
  withdraw: (body: unknown, token: string) =>
    post<{ ok: boolean }>('/referral/withdraw', body, token),
};

// ─── Coupons ──────────────────────────────────────────────────────────────────
export const couponsApi = {
  validate: (code: string, plan?: string) =>
    post<{ valid: boolean; discount_pct?: number; discount_flat?: number; message: string }>(
      '/coupons/validate', { code, plan }
    ),
  apply: (body: { learner_id: string; email: string; code: string }, token: string) =>
    post<{ ok: boolean; savings: number }>('/coupons/apply', body, token),
};

// ─── Invoices ─────────────────────────────────────────────────────────────────
export const invoicesApi = {
  list: (learner_id: string, token: string) =>
    get<{ invoices: Invoice[]; total: number }>(`/invoices/${learner_id}`, token),
};

// ─── Conversations ────────────────────────────────────────────────────────────
export const conversationsApi = {
  list: (learner_id: string, token: string) =>
    get<{ conversations: unknown[] }>(`/conversations/${learner_id}`, token),
  messages: (learner_id: string, conv_id: string, token: string) =>
    get<{ messages: unknown[] }>(`/conversations/${learner_id}/${conv_id}`, token),
  newConversation: (learner_id: string, token: string) =>
    post<{ conversation_id: string }>(`/conversations/${learner_id}/new`, undefined, token),
};

// ─── Assignments ──────────────────────────────────────────────────────────────
export const assignmentsApi = {
  generate: (learner_id: string, topic: string, token: string) =>
    post<{ id: string; topic: string; question: string }>(
      '/assignments/generate', { learner_id, topic }, token
    ),
  list: (learner_id: string, token: string) =>
    get<{ assignments: unknown[] }>(`/assignments/${learner_id}`, token),
};

// ─── Feedback ─────────────────────────────────────────────────────────────────
export const feedbackApi = {
  message: (body: unknown, token?: string) =>
    post<{ ok: boolean }>('/feedback/message', body, token),
  survey:  (body: unknown, token?: string) =>
    post<{ ok: boolean }>('/feedback/survey', body, token),
};

// ─── Enquiry ──────────────────────────────────────────────────────────────────
export const enquiryApi = {
  submit: (body: { name: string; email: string; category: string; subject: string; message: string }) =>
    post<{ ok: boolean }>('/enquiry', body),
};

// ─── Profile ──────────────────────────────────────────────────────────────────
export const profileApi = {
  get:    (learner_id: string, token: string) =>
    get<Partial<UserProfile> & { photo_url?: string }>(`/auth/profile/${learner_id}`, token),
  update: (learner_id: string, body: unknown, token: string) =>
    post<{ ok: boolean }>(`/auth/profile/${learner_id}`, body, token),
};

// ─── Admin ────────────────────────────────────────────────────────────────────
function adminReq<T>(path: string, opts: RequestInit = {}, adminToken: string) {
  return req<T>(path, {
    ...opts,
    headers: { 'X-Admin-Token': adminToken, ...(opts.headers ?? {}) },
  });
}

export const adminApi = {
  login: (email: string, password: string) =>
    post<{ token: string }>('/admin/login', { email, password }),

  dashboard: (t: string) => adminReq<DashboardData>('/admin/dashboard', {}, t),
  users:     (t: string) => adminReq<AdminUsersResponse>('/admin/users', {}, t),
  userDetail:(lid: string, t: string) =>
    adminReq<UserProfile & { topic_progress: unknown; prompts_today: number; badges: string[] }>(
      `/admin/users/${lid}`, {}, t
    ),
  setTier:   (lid: string, tier: Tier, t: string) =>
    adminReq<{ ok: boolean }>(`/admin/users/${lid}/set-tier`,
      { method: 'POST', body: JSON.stringify({ tier }) }, t),
  terminate: (lid: string, t: string) =>
    adminReq<{ ok: boolean }>(`/admin/users/${lid}/terminate`, { method: 'POST' }, t),
  deleteUser:(lid: string, t: string) =>
    adminReq<{ ok: boolean }>(`/admin/users/${lid}`, { method: 'DELETE' }, t),
  confirmEmail:(email: string, t: string) =>
    adminReq<{ ok: boolean; message: string }>('/admin/users/confirm-email',
      { method: 'POST', body: JSON.stringify({ email }) }, t),

  payments:       (t: string) => adminReq<{ payments: Payment[]; bank_transfer_proofs: BankProof[]; summary: unknown }>('/admin/payments', {}, t),
  addPayment:     (body: unknown, t: string) =>
    adminReq<{ ok: boolean }>('/admin/payments/add', { method: 'POST', body: JSON.stringify(body) }, t),
  confirmPayment: (id: string, t: string) =>
    adminReq<{ ok: boolean }>(`/admin/payments/confirm/${id}`, { method: 'POST' }, t),
  approveProof:   (id: number, tier: Tier, t: string) =>
    adminReq<{ ok: boolean }>(`/admin/payments/bank-transfer/${id}/approve`,
      { method: 'POST', body: JSON.stringify({ tier }) }, t),
  rejectProof:    (id: number, reason: string, t: string) =>
    adminReq<{ ok: boolean }>(`/admin/payments/bank-transfer/${id}/reject`,
      { method: 'POST', body: JSON.stringify({ reason }) }, t),

  certificates: (t: string) => adminReq<{ certificates: CertRecord[] }>('/admin/certificates', {}, t),
  activity:     (t: string) => adminReq<{ activity: unknown[] }>('/admin/activity', {}, t),
  feedback:     (t: string) => adminReq<{ ratings: unknown[]; surveys: unknown[] }>('/admin/feedback', {}, t),

  announcements: (t: string) => adminReq<{ announcements: Announcement[] }>('/admin/announce/history', {}, t),
  announce:      (body: unknown, t: string) =>
    adminReq<{ ok: boolean; sent_to: number }>('/admin/announce',
      { method: 'POST', body: JSON.stringify(body) }, t),

  team:       (t: string) => adminReq<{ members: TeamMember[] }>('/admin/team', {}, t),
  inviteTeam: (body: unknown, t: string) =>
    adminReq<{ ok: boolean }>('/admin/team/invite', { method: 'POST', body: JSON.stringify(body) }, t),

  tasks:      (t: string) => adminReq<{ tasks: Task[] }>('/admin/tasks/list', {}, t),
  createTask: (body: unknown, t: string) =>
    adminReq<{ ok: boolean }>('/admin/tasks/create', { method: 'POST', body: JSON.stringify(body) }, t),
  updateTask: (id: number, status: string, t: string) =>
    adminReq<{ ok: boolean }>(`/admin/tasks/${id}/status`,
      { method: 'POST', body: JSON.stringify({ status }) }, t),

  referrals:   (t: string) => adminReq<{ referrals: unknown[] }>('/admin/referrals', {}, t),
  withdrawals: (t: string) => adminReq<{ withdrawals: WithdrawalRequest[]; total: number; pending: number }>('/admin/withdrawals', {}, t),
  updateWithdrawal: (id: number, status: string, t: string) =>
    adminReq<{ ok: boolean }>(`/admin/withdrawals/${id}/status`,
      { method: 'POST', body: JSON.stringify({ status }) }, t),

  coupons:      (t: string) => adminReq<{ coupons: Coupon[] }>('/admin/coupons', {}, t),
  createCoupon: (body: unknown, t: string) =>
    adminReq<{ ok: boolean }>('/admin/coupons/create', { method: 'POST', body: JSON.stringify(body) }, t),
  deleteCoupon: (code: string, t: string) =>
    adminReq<{ ok: boolean }>(`/admin/coupons/${code}`, { method: 'DELETE' }, t),
  deactivateCoupon: (code: string, t: string) =>
    adminReq<{ ok: boolean }>(`/admin/coupons/${code}/deactivate`, { method: 'PUT' }, t),
  activateCoupon:   (code: string, t: string) =>
    adminReq<{ ok: boolean }>(`/admin/coupons/${code}/activate`, { method: 'PUT' }, t),

  invoices:  (t: string) => adminReq<{ invoices: Invoice[]; total_revenue: number }>('/admin/invoices', {}, t),
  enquiries: (t: string) => adminReq<{ enquiries: Enquiry[] }>('/admin/enquiries', {}, t),
  resolveEnquiry: (id: number, t: string) =>
    adminReq<{ ok: boolean }>(`/admin/enquiries/${id}/resolve`, { method: 'POST' }, t),
  history:   (lid: string, t: string) =>
    adminReq<{ history: unknown[] }>(`/admin/history/${lid}`, {}, t),
  assignments: (t: string) => adminReq<{ assignments: unknown[] }>('/admin/assignments', {}, t),
  files:       (t: string) => adminReq<{ files: unknown[] }>('/admin/files', {}, t),

  testEmail: (to: string, t: string) =>
    adminReq<{ ok: boolean; results: unknown }>('/admin/email/test',
      { method: 'POST', body: JSON.stringify({ to }) }, t),

  triggerReengagement:         (t: string) => adminReq<{ sent: number }>('/admin/reengagement/trigger', { method: 'POST' }, t),
  triggerCourseReminder:       (t: string) => adminReq<{ sent: number }>('/admin/email/course-reminder/trigger', { method: 'POST' }, t),
  triggerAssignmentReminder:   (t: string) => adminReq<{ sent: number }>('/admin/email/assignment-reminder/trigger', { method: 'POST' }, t),
  triggerWeekend:              (t: string) => adminReq<{ sent: number }>('/admin/email/weekend/trigger', { method: 'POST' }, t),
  triggerNewMonth:             (t: string) => adminReq<{ sent: number }>('/admin/email/new-month/trigger', { method: 'POST' }, t),
};
