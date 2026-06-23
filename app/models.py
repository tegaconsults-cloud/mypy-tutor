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
    message:    str          = Field(..., min_length=1, max_length=4_000)
    history:    list[Message]= Field(default=[], max_length=20)
    learner_id: str          = Field(default="default", min_length=1, max_length=64,
                                     pattern=r"^[a-zA-Z0-9_\-]+$")
    level:      Literal["beginner", "intermediate", "advanced"] = "beginner"


class ChatResponse(BaseModel):
    intent:     str
    content:    str
    topic:      str | None = None
    level:      str        = "beginner"
    xp_gained:  int        = 0
    badge:      str | None = None
    ask_survey: bool       = False   # True every 5 interactions → frontend shows survey


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
    xp:                   int
    badges:               list[str]
    topics_seen:          list[str]
    knowledge_gaps:       list[str]
    current_course:       str | None
    current_course_step:  int
    completed_projects:   list[str]
    topic_progress:       dict[str, TopicProgress]
