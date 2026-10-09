// ─── Auth ────────────────────────────────────────────────────────────────────
export interface AuthResponse {
  token:       string;
  learner_id:  string;
  name:        string;
  email:       string;
  picture:     string;
  greeting:    string;
  is_new_user: boolean;
}

export interface UserProfile {
  learner_id:     string;
  email:          string;
  name:           string;
  tier:           Tier;
  level:          Level;
  xp:             number;
  topics_seen:    number;
  courses_done:   number;
  badges:         number;
  current_course: string | null;
  joined_at:      string;
  joined_ts:      number;
  picture?:       string;
}

export type Tier  = 'free' | 'tier1' | 'tier2' | 'tier3' | 'tier4' | 'deleted';
export type Level = 'beginner' | 'intermediate' | 'advanced';

// ─── Chat ────────────────────────────────────────────────────────────────────
export interface Message {
  role:    'user' | 'assistant';
  content: string;
}

export interface ChatRequest {
  message:         string;
  history:         Message[];
  learner_id:      string;
  level:           Level;
  conversation_id?: string | null;
}

export interface ChatResponse {
  intent:          string;
  content:         string;
  topic:           string;
  level:           Level;
  xp_gained:       number;
  badge:           string | null;
  ask_survey:      boolean;
  conversation_id: string;
  new_conversation?: boolean;
}

// ─── Progress ────────────────────────────────────────────────────────────────
export interface TopicProgress {
  lessons:             number;
  exercises_attempted: number;
  exercises_passed:    number;
  weak:                boolean;
}

export interface ProgressResponse {
  learner_id:          string;
  level:               Level;
  tier:                Tier;
  xp:                  number;
  badges:              string[];
  topics_seen:         string[];
  knowledge_gaps:      string[];
  current_course:      string | null;
  current_course_step: number;
  completed_projects:  string[];
  topic_progress:      Record<string, TopicProgress>;
  updated_at:          number;
}

// ─── Quiz ────────────────────────────────────────────────────────────────────
export interface QuizResponse {
  question: string;
  options:  string[];
  topic:    string;
  level:    Level;
}

export interface QuizAnswerResponse {
  correct:     boolean;
  explanation: string;
  score:       number;
  xp_gained:   number;
}

// ─── Courses ─────────────────────────────────────────────────────────────────
export interface CourseStep {
  step:        number;
  title:       string;
  description: string;
  intent:      string;
}

export interface Course {
  name:        string;
  level:       string;
  description: string;
  steps:       CourseStep[];
}

// ─── Admin Dashboard ─────────────────────────────────────────────────────────
export interface DashboardData {
  users: {
    total:        number;
    active_today: number;
    new_24h:      number;
  };
  users_by_tier: Record<Tier, number>;
  revenue: {
    total_revenue:  number;
    today_revenue:  number;
    total_payments: number;
    confirmed:      number;
    pending:        number;
    by_plan:        Record<string, number>;
  };
  payments:            number;
  certificates:        number;
  tasks: {
    total:       number;
    open:        number;
    in_progress: number;
    done:        number;
  };
  feedback: {
    total_ratings:     number;
    satisfaction_pct:  number;
    avg_rating:        number;
  };
  team_size:           number;
  withdrawals_pending: number;
}

export interface AdminUsersResponse {
  learner_profiles: UserProfile[];
  email_accounts:   Array<{ email: string; name: string; learner_id: string; type: string }>;
  total:            number;
  email_signups:    number;
}

export interface Payment {
  id:          string;
  user_email:  string;
  user_name:   string;
  amount:      number;
  currency:    string;
  plan:        string;
  method:      string;
  status:      'pending' | 'confirmed' | 'refunded';
  notes:       string;
  created_at:  string;
}

export interface BankProof {
  id:           number;
  learner_id:   string;
  email:        string;
  plan:         string;
  amount:       number;
  proof_url:    string;
  status:       'pending' | 'approved' | 'rejected';
  submitted_at: number;
  submitted_at_fmt: string;
}

export interface CertRecord {
  cert_id:      string;
  learner_id:   string;
  learner_name: string;
  level:        string;
  issued_at:    number;
}

export interface Coupon {
  code:         string;
  discount_pct: number;
  discount_flat: number;
  plan:         string;
  max_uses:     number;
  uses:         number;
  active:       number;
  expires_at:   number;
}

export interface Announcement {
  id:         number;
  subject:    string;
  message:    string;
  target:     string;
  sent_to:    number;
  created_at: string;
}

export interface TeamMember {
  id:         number;
  email:      string;
  name:       string;
  role:       string;
  invited_at: string;
}

export interface Task {
  id:         number;
  title:      string;
  description: string;
  assigned_to: string;
  status:     'open' | 'in_progress' | 'done';
  created_at: string;
}

export interface Invoice {
  id:         string;
  payment_id: string;
  learner_id: string;
  email:      string;
  name:       string;
  plan:       string;
  amount:     number;
  currency:   string;
  issued_at:  number;
}

export interface WithdrawalRequest {
  id:           number;
  learner_id:   string;
  email:        string;
  amount:       number;
  bank_name:    string;
  account_name: string;
  account_no:   string;
  status:       'pending' | 'approved' | 'paid' | 'rejected';
  created_at:   string;
}

export interface Enquiry {
  id:         number;
  name:       string;
  email:      string;
  category:   string;
  subject:    string;
  message:    string;
  status:     'open' | 'resolved';
  created_at: string;
}

export interface ReferralStats {
  code:             string;
  uses:             number;
  max_uses:         number;
  bonus_balance:    number;
  paid_referrals:   number;
  unpaid_referrals: number;
  total_referrals:  number;
  recent_uses:      Array<{ email: string; ts: number }>;
}

// ─── Certificate verify ───────────────────────────────────────────────────────
export interface CertVerifyData {
  cert_id:      string;
  learner_name: string;
  level:        string;
  issued_at:    number;
}

// ─── TTS ─────────────────────────────────────────────────────────────────────
export interface TTSPrepareResponse {
  text:       string;
  char_count: number;
  truncated:  boolean;
}

export interface TTSVoicesResponse {
  preferred:         string[];
  language_priority: string[];
  fallback:          string;
}
