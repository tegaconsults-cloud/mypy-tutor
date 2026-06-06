"""
FastAPI application — MyPy Tutor (secured).
Security layer: rate limiting, input validation, security headers, sanitised errors.
"""

import logging
import re
import os as _os

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.classifier import classify_intent
from app.formatter import format_response
from app.llm_client import get_completion
from app.models import (
    ChatRequest, ChatResponse,
    QuizRequest, QuizResponse,
    QuizAnswerRequest, QuizAnswerResponse,
    ProgressResponse,
)
from app.prompts import build_system_prompt
from app.topics import get_topics
from app.progress import (
    get_profile, record_lesson, record_quiz,
    record_exercise, get_knowledge_gaps, advance_course,
)
from app.courses import get_all_courses, get_courses_for_level, get_course
from app.security import (
    SecurityMiddleware,
    validate_learner_id, validate_level,
    validate_course_name, validate_topic,
    validate_chat_request,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# App initialisation
# ---------------------------------------------------------------------------

try:
    import app.llm_client  # noqa: F401 — validates GROQ_API_KEY at startup
except ValueError as exc:
    logger.error("Startup error: %s", exc)
    raise

app = FastAPI(
    title="MyPy Tutor",
    version="2.0.0",
    # Disable docs in production to avoid leaking API schema
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

# ---------------------------------------------------------------------------
# Middleware — order matters: CORS first, then security
# ---------------------------------------------------------------------------

# The frontend and backend are served from the SAME Render service (same origin),
# so browser requests are never cross-origin. We allow the Render wildcard pattern
# plus localhost for dev. Using allow_origins=["*"] would be unsafe for a separate
# frontend, but here it's equivalent since our static files come from the same host.
_RENDER_URL = _os.getenv("RENDER_EXTERNAL_URL", "")  # auto-set by Render
_allowed_origins = list(filter(None, [
    _RENDER_URL,
    "http://localhost:8000",
    "http://127.0.0.1:8000",
])) or ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_origin_regex=r"https://.*\.onrender\.com",  # covers any Render subdomain
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
    allow_credentials=False,
)

# Rate limiting + security headers
app.add_middleware(SecurityMiddleware)

# ---------------------------------------------------------------------------
# /chat — original + secured
# ---------------------------------------------------------------------------

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    # Input validation (size, level, learner_id, history)
    validate_chat_request(request.message, request.history, request.level, request.learner_id)

    intent = classify_intent(request.message)

    from app.formatter import _detect_topic
    topic   = _detect_topic(request.message)
    gaps    = get_knowledge_gaps(request.learner_id)
    is_gap  = topic in gaps if topic else False

    system_prompt = build_system_prompt(
        intent, topic=topic, level=request.level, is_gap_topic=is_gap
    )

    messages = [{"role": m.role, "content": m.content} for m in request.history]
    messages.append({"role": "user", "content": request.message})

    try:
        content = get_completion(system_prompt, messages)
    except Exception as exc:
        exc_type = type(exc).__name__.lower()
        if any(k in exc_type for k in ("ratelimit", "timeout", "serviceunavailable")):
            logger.warning("LLM unavailable: %s", exc)
            raise HTTPException(status_code=503, detail="LLM unavailable, please retry")
        # Never leak raw exception details to the client
        logger.error("LLM error: %s", exc)
        raise HTTPException(status_code=502, detail="AI service error. Please try again.")

    response_dict   = format_response(content, intent)
    detected_topic  = response_dict.get("topic") or topic
    xp, badge       = record_lesson(request.learner_id, detected_topic or "", intent)
    profile         = get_profile(request.learner_id)

    return ChatResponse(
        intent=response_dict["intent"],
        content=response_dict["content"],
        topic=response_dict["topic"],
        level=profile.level,
        xp_gained=xp,
        badge=badge,
    )


# ---------------------------------------------------------------------------
# /topics — original, unchanged
# ---------------------------------------------------------------------------

@app.get("/topics")
async def topics() -> dict:
    return {"topics": get_topics()}


# ---------------------------------------------------------------------------
# /health — original, unchanged
# ---------------------------------------------------------------------------

@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# /progress/{learner_id}
# ---------------------------------------------------------------------------

@app.get("/progress/{learner_id}", response_model=ProgressResponse)
async def get_progress(learner_id: str) -> ProgressResponse:
    validate_learner_id(learner_id)
    profile = get_profile(learner_id)
    gaps    = get_knowledge_gaps(learner_id)
    return ProgressResponse(
        learner_id=profile.learner_id,
        level=profile.level,
        xp=profile.xp,
        badges=profile.badges,
        topics_seen=profile.topics_seen,
        knowledge_gaps=gaps,
        current_course=profile.current_course,
        current_course_step=profile.current_course_step,
        completed_projects=profile.completed_projects,
        topic_progress=profile.topic_progress,
    )


# ---------------------------------------------------------------------------
# /courses
# ---------------------------------------------------------------------------

@app.get("/courses")
async def list_courses(level: str = "beginner") -> dict:
    validate_level(level)
    courses = get_courses_for_level(level)
    return {
        "level": level,
        "courses": [
            {
                "name": c.name,
                "description": c.description,
                "level": c.level,
                "total_steps": len(c.steps),
            }
            for c in courses
        ],
    }


# ---------------------------------------------------------------------------
# /course/start
# ---------------------------------------------------------------------------

@app.post("/course/start")
async def start_course(learner_id: str, course_name: str) -> dict:
    validate_learner_id(learner_id)
    validate_course_name(course_name)

    course = get_course(course_name)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found.")

    profile = get_profile(learner_id)
    profile.current_course      = course_name
    profile.current_course_step = 1

    from app.progress import save_profile
    save_profile(profile)

    step = course.steps[0]
    system_prompt = build_system_prompt(step.intent, topic=step.title, level=profile.level)
    messages = [{"role": "user", "content": f"Teach me: {step.description}"}]

    try:
        content = get_completion(system_prompt, messages)
    except Exception as exc:
        logger.error("Course start LLM error: %s", exc)
        raise HTTPException(status_code=502, detail="AI service error. Please try again.")

    return {
        "course": course_name,
        "step": step.step,
        "title": step.title,
        "total_steps": len(course.steps),
        "content": content,
    }


# ---------------------------------------------------------------------------
# /course/next
# ---------------------------------------------------------------------------

@app.post("/course/next")
async def next_course_step(learner_id: str) -> dict:
    validate_learner_id(learner_id)

    profile = get_profile(learner_id)
    if not profile.current_course:
        raise HTTPException(status_code=400, detail="No active course. Start a course first.")

    course = get_course(profile.current_course)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found.")

    advance_course(learner_id)
    profile   = get_profile(learner_id)
    step_idx  = profile.current_course_step - 1

    if step_idx >= len(course.steps):
        from app.progress import _award_badge, save_profile, XP_PROJECT
        profile.completed_projects.append(profile.current_course)
        profile.xp += XP_PROJECT
        badge = _award_badge(profile, "course_complete")
        profile.current_course      = None
        profile.current_course_step = 0
        save_profile(profile)
        return {
            "completed": True,
            "course": course.name,
            "xp_gained": XP_PROJECT,
            "badge": badge,
            "content": f"🎉 Congratulations! You've completed **{course.name}**. You earned {XP_PROJECT} XP!",
        }

    step = course.steps[step_idx]
    system_prompt = build_system_prompt(step.intent, topic=step.title, level=profile.level)
    messages = [{"role": "user", "content": f"Teach me: {step.description}"}]

    try:
        content = get_completion(system_prompt, messages)
    except Exception as exc:
        logger.error("Course next LLM error: %s", exc)
        raise HTTPException(status_code=502, detail="AI service error. Please try again.")

    xp, badge = record_lesson(learner_id, step.title, step.intent)

    return {
        "completed": False,
        "course": course.name,
        "step": step.step,
        "title": step.title,
        "total_steps": len(course.steps),
        "content": content,
        "xp_gained": xp,
        "badge": badge,
    }


# ---------------------------------------------------------------------------
# /quiz/generate
# ---------------------------------------------------------------------------

@app.post("/quiz/generate", response_model=QuizResponse)
async def generate_quiz(request: QuizRequest) -> QuizResponse:
    # Pydantic already validated lengths; validate topic string safety
    validate_topic(request.topic)

    system_prompt = build_system_prompt("quiz", topic=request.topic, level=request.level)
    messages = [{"role": "user", "content": f"Generate a quiz question about: {request.topic}"}]

    try:
        content = get_completion(system_prompt, messages)
    except Exception as exc:
        logger.error("Quiz generate LLM error: %s", exc)
        raise HTTPException(status_code=502, detail="AI service error. Please try again.")

    question, options = _parse_quiz(content)
    return QuizResponse(question=question, options=options, topic=request.topic, level=request.level)


# ---------------------------------------------------------------------------
# /quiz/answer
# ---------------------------------------------------------------------------

@app.post("/quiz/answer", response_model=QuizAnswerResponse)
async def evaluate_quiz_answer(request: QuizAnswerRequest) -> QuizAnswerResponse:
    validate_topic(request.topic)

    system_prompt = build_system_prompt("quiz_eval", topic=request.topic, level=request.level)
    messages = [{
        "role": "user",
        "content": (
            f"Question: {request.question}\n"
            f"The learner answered: {request.answer}\n"
            "Evaluate this answer."
        ),
    }]

    try:
        content = get_completion(system_prompt, messages)
    except Exception as exc:
        logger.error("Quiz answer LLM error: %s", exc)
        raise HTTPException(status_code=502, detail="AI service error. Please try again.")

    correct  = "correct: true" in content.lower()
    score    = 100 if correct else 0
    xp, _    = record_quiz(request.learner_id, request.topic, score)

    return QuizAnswerResponse(correct=correct, explanation=content, score=score, xp_gained=xp)


# ---------------------------------------------------------------------------
# /exercise/generate
# ---------------------------------------------------------------------------

@app.post("/exercise/generate")
async def generate_exercise(learner_id: str, topic: str) -> dict:
    validate_learner_id(learner_id)
    validate_topic(topic)

    profile  = get_profile(learner_id)
    gaps     = get_knowledge_gaps(learner_id)
    is_gap   = topic in gaps

    system_prompt = build_system_prompt(
        "exercise", topic=topic, level=profile.level, is_gap_topic=is_gap
    )
    messages = [{"role": "user", "content": f"Give me a Python exercise on: {topic}"}]

    try:
        content = get_completion(system_prompt, messages)
    except Exception as exc:
        logger.error("Exercise LLM error: %s", exc)
        raise HTTPException(status_code=502, detail="AI service error. Please try again.")

    return {"topic": topic, "level": profile.level, "is_gap_topic": is_gap, "content": content}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_quiz(raw: str) -> tuple[str, list[str]]:
    question    = ""
    options     = []
    q_match     = re.search(r"\*\*Question:\*\*\s*(.+?)(?=\n[A-D]\))", raw, re.DOTALL)
    if q_match:
        question = q_match.group(1).strip()
    opt_matches = re.findall(r"^([A-D])\)\s*(.+)$", raw, re.MULTILINE)
    options     = [f"{letter}) {text}" for letter, text in opt_matches]
    if not question:
        question = raw.split("\n")[0].strip()
    if not options:
        options = ["A) See full response", "B) —", "C) —", "D) —"]
    return question, options


# ---------------------------------------------------------------------------
# Global error handlers — never expose internals
# ---------------------------------------------------------------------------

@app.exception_handler(RequestValidationError)
async def request_validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Catch Pydantic 422 errors and return a clean single-string message."""
    try:
        first = exc.errors()[0]
        field  = " → ".join(str(loc) for loc in first.get("loc", []) if loc != "body")
        msg    = first.get("msg", "Invalid value")
        detail = f"{field}: {msg}" if field else msg
    except Exception:
        detail = "Invalid request data"
    return JSONResponse(status_code=422, content={"error": detail})

@app.exception_handler(400)
async def bad_request_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=400, content={"error": "Bad request"})

@app.exception_handler(404)
async def not_found_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=404, content={"error": "Not found"})

@app.exception_handler(405)
async def method_not_allowed_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=405, content={"error": "Method not allowed"})

@app.exception_handler(422)
async def validation_error_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=422, content={"error": "Invalid request data"})

@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Unhandled error: %s", exc)
    return JSONResponse(status_code=500, content={"error": "Internal server error"})

@app.exception_handler(502)
async def bad_gateway_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=502, content={"error": "AI service error. Please try again."})

@app.exception_handler(503)
async def service_unavailable_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=503, content={"error": "LLM unavailable, please retry"})


# ---------------------------------------------------------------------------
# Static files — mounted LAST
# ---------------------------------------------------------------------------

app.mount("/", StaticFiles(directory="static", html=True), name="static")
