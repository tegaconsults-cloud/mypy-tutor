"""
Pydantic models for MyPy Tutor — including learner profile and progress tracking.
"""

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Chat models
# ---------------------------------------------------------------------------

class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[Message] = []
    learner_id: str = "default"          # identifies the learner across sessions
    level: str = "beginner"              # beginner | intermediate | advanced


class ChatResponse(BaseModel):
    intent: str
    content: str
    topic: str | None = None
    level: str = "beginner"
    xp_gained: int = 0
    badge: str | None = None


# ---------------------------------------------------------------------------
# Progress & profile models
# ---------------------------------------------------------------------------

class TopicProgress(BaseModel):
    topic: str
    lessons_completed: int = 0
    exercises_attempted: int = 0
    exercises_passed: int = 0
    quiz_scores: list[int] = []          # 0-100 per quiz
    weak: bool = False                   # flagged as a knowledge gap


class LearnerProfile(BaseModel):
    learner_id: str
    level: str = "beginner"              # beginner | intermediate | advanced
    xp: int = 0
    badges: list[str] = []
    topics_seen: list[str] = []          # ordered — remembers lessons
    topic_progress: dict[str, TopicProgress] = {}
    current_course: str | None = None
    current_course_step: int = 0
    completed_projects: list[str] = []


# ---------------------------------------------------------------------------
# Course & quiz models
# ---------------------------------------------------------------------------

class CourseStep(BaseModel):
    step: int
    title: str
    description: str
    intent: str                          # concept | codegen | exercise | quiz


class Course(BaseModel):
    name: str
    level: str
    description: str
    steps: list[CourseStep]


class QuizRequest(BaseModel):
    learner_id: str = "default"
    topic: str
    level: str = "beginner"


class QuizResponse(BaseModel):
    question: str
    options: list[str]
    topic: str
    level: str


class QuizAnswerRequest(BaseModel):
    learner_id: str = "default"
    topic: str
    level: str = "beginner"
    question: str
    answer: str


class QuizAnswerResponse(BaseModel):
    correct: bool
    explanation: str
    score: int                           # 0 or 100
    xp_gained: int


# ---------------------------------------------------------------------------
# Progress API response
# ---------------------------------------------------------------------------

class ProgressResponse(BaseModel):
    learner_id: str
    level: str
    xp: int
    badges: list[str]
    topics_seen: list[str]
    knowledge_gaps: list[str]
    current_course: str | None
    current_course_step: int
    completed_projects: list[str]
    topic_progress: dict[str, TopicProgress]
