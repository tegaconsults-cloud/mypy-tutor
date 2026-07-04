"""
Pydantic models for MyPy Tutor.
Field-level validation enforced here — lengths, allowed values, patterns.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Literal


# ---------------------------------------------------------------------------
# Auth / user models
# ---------------------------------------------------------------------------

class UserAccount(BaseModel):
    learner_id: str
    email:      str
    name:       str
    picture:    str = ""
    google_sub: str


class GoogleAuthRequest(BaseModel):
    credential: str = Field(..., min_length=10, max_length=4096)


class AuthResponse(BaseModel):
    token:      str
    learner_id: str
    name:       str
    email:      str
    picture:    str


class EmailSignUpRequest(BaseModel):
    name:     str   = Field(..., min_length=1, max_length=80)
    email:    str   = Field(..., min_length=5, max_length=254,
                            pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str   = Field(..., min_length=8, max_length=128)


class EmailSignInRequest(BaseModel):
    email:    str   = Field(..., min_length=5, max_length=254)
    password: str   = Field(..., min_length=1, max_length=128)


# ---------------------------------------------------------------------------
# Feedback models
# ---------------------------------------------------------------------------

class MessageFeedback(BaseModel):
    """Quick thumbs up/down on a single AI response."""
    learner_id:  str   = Field(default="default", min_length=1, max_length=64,
                               pattern=r"^[a-zA-Z0-9_\-]+$")
    rating:      Literal["up", "down"]
    intent:      str   = Field(default="", max_length=50)
    topic:       str   = Field(default="", max_length=100)
    comment:     str   = Field(default="", max_length=500)   # optional quick note


class SurveyFeedback(BaseModel):
    """Periodic full satisfaction survey."""
    learner_id:      str  = Field(default="default", min_length=1, max_length=64,
                                  pattern=r"^[a-zA-Z0-9_\-]+$")
    overall:         int  = Field(..., ge=1, le=5)          # 1–5 star rating
    clarity:         int  = Field(..., ge=1, le=5)          # how clear are explanations?
    helpfulness:     int  = Field(..., ge=1, le=5)          # how helpful overall?
    suggestion:      str  = Field(default="", max_length=1000)  # free text
    would_recommend: bool = True


class FeedbackSummary(BaseModel):
    total_ratings:    int
    thumbs_up:        int
    thumbs_down:      int
    satisfaction_pct: float          # % positive
    avg_overall:      float          # avg survey overall score
    avg_clarity:      float
    avg_helpfulness:  float
    total_surveys:    int
    recent_suggestions: list[str]


# ---------------------------------------------------------------------------
# Chat models
# ---------------------------------------------------------------------------

class Message(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str = Field(..., min_length=1, max_length=12_000)  # AI responses can be long


class ChatRequest(BaseModel):
    message:         str          = Field(..., min_length=1, max_length=4_000)
    history:         list[Message]= Field(default=[], max_length=20)
    learner_id:      str          = Field(default="default", min_length=1, max_length=64,
                                          pattern=r"^[a-zA-Z0-9_\-]+$")
    level:           Literal["beginner", "intermediate", "advanced"] = "beginner"
    conversation_id: str | None   = None   # Supabase conversation UUID; None = auto-resolve


class ChatResponse(BaseModel):
    intent:          str
    content:         str
    topic:           str | None  = None
    level:           str         = "beginner"
    xp_gained:       int         = 0
    badge:           str | None  = None
    ask_survey:      bool        = False
    conversation_id: str | None  = None   # echoed back so frontend can persist it


# ---------------------------------------------------------------------------
# Progress & profile models
# ---------------------------------------------------------------------------

class TopicProgress(BaseModel):
    topic:               str
    lessons_completed:   int       = 0
    exercises_attempted: int       = 0
    exercises_passed:    int       = 0
    quiz_scores:         list[int] = []
    weak:                bool      = False


class LearnerProfile(BaseModel):
    learner_id:           str
    tier:                 str       = "free"     # "free" | "tier1" | "tier2" | "tier3"
    level:                str       = "beginner"
    xp:                   int       = 0
    badges:               list[str] = []
    topics_seen:          list[str] = []
    topic_progress:       dict[str, TopicProgress] = {}
    current_course:       str | None = None
    current_course_step:  int        = 0
    completed_projects:   list[str]  = []
    daily_prompts_used:   int        = 0
    last_prompt_date:     str        = ""
    email:                str        = ""   # real email — stored from auth for admin
    display_name:         str        = ""   # user's real name from auth


# ---------------------------------------------------------------------------
# Course & quiz models
# ---------------------------------------------------------------------------

class CourseStep(BaseModel):
    step:        int
    title:       str
    description: str
    intent:      str


class Course(BaseModel):
    name:        str
    level:       str
    description: str
    steps:       list[CourseStep]


class QuizRequest(BaseModel):
    learner_id: str = Field(default="default", min_length=1, max_length=64,
                            pattern=r"^[a-zA-Z0-9_\-]+$")
    topic:      str = Field(..., min_length=1, max_length=100)
    level:      Literal["beginner", "intermediate", "advanced"] = "beginner"


class QuizResponse(BaseModel):
    question: str
    options:  list[str]
    topic:    str
    level:    str


class QuizAnswerRequest(BaseModel):
    learner_id: str      = Field(default="default", min_length=1, max_length=64,
                                 pattern=r"^[a-zA-Z0-9_\-]+$")
    topic:      str      = Field(..., min_length=1, max_length=100)
    level:      Literal["beginner", "intermediate", "advanced"] = "beginner"
    question:   str      = Field(..., min_length=1, max_length=1_000)
    answer:     str      = Field(..., min_length=1, max_length=500)


class QuizAnswerResponse(BaseModel):
    correct:     bool
    explanation: str
    score:       int
    xp_gained:   int


# ---------------------------------------------------------------------------
# Progress API response
# ---------------------------------------------------------------------------

class ProgressResponse(BaseModel):
    learner_id:           str
    level:                str
    tier:                 str       = "free"   # included so frontend can show plan badge
    xp:                   int
    badges:               list[str]
    topics_seen:          list[str]
    knowledge_gaps:       list[str]
    current_course:       str | None
    current_course_step:  int
    completed_projects:   list[str]
    topic_progress:       dict[str, TopicProgress]


# ---------------------------------------------------------------------------
# Password reset models
# ---------------------------------------------------------------------------

class PasswordResetRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=254,
                       pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class PasswordResetConfirm(BaseModel):
    token:        str = Field(..., min_length=10, max_length=512)
    new_password: str = Field(..., min_length=8, max_length=128)


# ---------------------------------------------------------------------------
# Assignment models
# ---------------------------------------------------------------------------

class AssignmentSubmit(BaseModel):
    learner_id: str = Field(..., min_length=1, max_length=64,
                            pattern=r"^[a-zA-Z0-9_\-]+$")
    submission: str = Field(..., min_length=1, max_length=8000)


class AssignmentReview(BaseModel):
    feedback: str = Field(..., min_length=1, max_length=2000)
    score:    int = Field(..., ge=0, le=100)


# ---------------------------------------------------------------------------
# Coupon / referral models
# ---------------------------------------------------------------------------

class CouponValidate(BaseModel):
    code:       str = Field(..., min_length=1, max_length=32)
    plan:       str = Field(default="any", max_length=20)
    learner_id: str = Field(default="default", max_length=64)
    email:      str = Field(default="", max_length=254)


class ReferralUse(BaseModel):
    code:       str = Field(..., min_length=1, max_length=32)
    learner_id: str = Field(..., min_length=1, max_length=64,
                            pattern=r"^[a-zA-Z0-9_\-]+$")
    email:      str = Field(..., min_length=5, max_length=254)


# ---------------------------------------------------------------------------
# Admin coupon creation model
# ---------------------------------------------------------------------------

class CouponCreate(BaseModel):
    code:          str   = Field(..., min_length=2, max_length=32)
    discount_pct:  int   = Field(..., ge=0, le=100)
    discount_flat: float = Field(default=0.0, ge=0)
    plan:          str   = Field(default="any", max_length=20)
    max_uses:      int   = Field(default=100, ge=1)
    expires_days:  int   = Field(default=0, ge=0)   # 0 = never expires


# ---------------------------------------------------------------------------
# Access code models
# ---------------------------------------------------------------------------

class AccessCodeGenerate(BaseModel):
    tier:          Literal["tier1", "tier2", "tier3"]
    sent_to_email: str  = Field(default="", max_length=254)
    expires_days:  int  = Field(default=30, ge=1, le=365)


class EmailSignUpWithCode(BaseModel):
    """Extended signup that accepts an optional access code."""
    name:        str = Field(..., min_length=1, max_length=80)
    email:       str = Field(..., min_length=5, max_length=254,
                              pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password:    str = Field(..., min_length=8, max_length=128)
    access_code: str = Field(default="", max_length=32)

# ---------------------------------------------------------------------------
# Editable user profile model
# ---------------------------------------------------------------------------

class UserProfileUpdate(BaseModel):
    """Fields a user can edit about themselves."""
    display_name: str = Field(default="", max_length=80)
    bio:          str = Field(default="", max_length=500)
    location:     str = Field(default="", max_length=100)
    website:      str = Field(default="", max_length=200)
    photo_url:    str = Field(default="", max_length=500_000)  # base64 data URL


# ---------------------------------------------------------------------------
# GitHub OAuth model
# ---------------------------------------------------------------------------

class GitHubAuthCallback(BaseModel):
    code:  str = Field(..., min_length=1, max_length=256)
    state: str = Field(default="", max_length=256)

