"""
FastAPI application — MyPy Tutor (upgraded).
All original routes preserved. New routes added for progress, courses, quizzes.
"""

import logging
import re

from fastapi import FastAPI, HTTPException, Request
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

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# App initialisation
# ---------------------------------------------------------------------------

try:
    import app.llm_client  # noqa: F401 — validates GROQ_API_KEY at startup
except ValueError as exc:
    logger.error("Startup error: %s", exc)
    raise

app = FastAPI(title="MyPy Tutor", version="2.0.0")

# ---------------------------------------------------------------------------
# Original /chat route — upgraded with level-awareness & progress tracking
# ---------------------------------------------------------------------------

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Main chat endpoint. Classifies intent, builds a level-aware system prompt,
    calls the LLM, records progress, and returns a structured response.
    All original behaviour preserved — learner_id and level are optional extras.
    """
    if not request.message or not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    intent = classify_intent(request.message)

    # Detect topic from the user message for gap-awareness
    from app.formatter import _detect_topic  # reuse existing topic detection
    topic = _detect_topic(request.message)

    # Check if this is a known gap topic for this learner
    gaps = get_knowledge_gaps(request.learner_id)
    is_gap = topic in gaps if topic else False

    # Build level-aware, gap-aware system prompt
    system_prompt = build_system_prompt(
        intent,
        topic=topic,
        level=request.level,
        is_gap_topic=is_gap,
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
        logger.error("LLM error: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc))

    response_dict = format_response(content, intent)

    # Detect topic from response if not found in message
    detected_topic = response_dict.get("topic") or topic

    # Record progress
    xp, badge = record_lesson(request.learner_id, detected_topic or "", intent)

    profile = get_profile(request.learner_id)

    return ChatResponse(
        intent=response_dict["intent"],
        content=response_dict["content"],
        topic=response_dict["topic"],
        level=profile.level,
        xp_gained=xp,
        badge=badge,
    )


# ---------------------------------------------------------------------------
# Original /topics route — unchanged
# ---------------------------------------------------------------------------

@app.get("/topics")
async def topics() -> dict:
    """Return the list of supported Python topics."""
    return {"topics": get_topics()}


# ---------------------------------------------------------------------------
# Original /health route — unchanged
# ---------------------------------------------------------------------------

@app.get("/health")
async def health() -> dict:
    """Simple health-check endpoint."""
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# NEW: Progress & learner profile
# ---------------------------------------------------------------------------

@app.get("/progress/{learner_id}", response_model=ProgressResponse)
async def get_progress(learner_id: str) -> ProgressResponse:
    """Return full learner profile including XP, badges, gaps, and course status."""
    profile = get_profile(learner_id)
    gaps = get_knowledge_gaps(learner_id)
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
# NEW: Courses & learning paths
# ---------------------------------------------------------------------------

@app.get("/courses")
async def list_courses(level: str = "beginner") -> dict:
    """List all courses available for a given level."""
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


@app.post("/course/start")
async def start_course(learner_id: str, course_name: str) -> dict:
    """Enrol a learner in a course and return the first lesson."""
    course = get_course(course_name)
    if not course:
        raise HTTPException(status_code=404, detail=f"Course '{course_name}' not found")

    profile = get_profile(learner_id)
    profile.current_course = course_name
    profile.current_course_step = 1

    from app.progress import save_profile
    save_profile(profile)

    step = course.steps[0]
    system_prompt = build_system_prompt(
        step.intent, topic=step.title, level=profile.level
    )
    messages = [{"role": "user", "content": f"Teach me: {step.description}"}]

    try:
        content = get_completion(system_prompt, messages)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    return {
        "course": course_name,
        "step": step.step,
        "title": step.title,
        "total_steps": len(course.steps),
        "content": content,
    }


@app.post("/course/next")
async def next_course_step(learner_id: str) -> dict:
    """Advance to the next step in the learner's current course."""
    profile = get_profile(learner_id)
    if not profile.current_course:
        raise HTTPException(status_code=400, detail="No active course. Start a course first.")

    course = get_course(profile.current_course)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    advance_course(learner_id)
    profile = get_profile(learner_id)
    step_idx = profile.current_course_step - 1

    if step_idx >= len(course.steps):
        # Course complete
        from app.progress import _award_badge, save_profile, XP_PROJECT
        profile.completed_projects.append(profile.current_course)
        profile.xp += XP_PROJECT
        badge = _award_badge(profile, "course_complete")
        profile.current_course = None
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
    system_prompt = build_system_prompt(
        step.intent, topic=step.title, level=profile.level
    )
    messages = [{"role": "user", "content": f"Teach me: {step.description}"}]

    try:
        content = get_completion(system_prompt, messages)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))

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
# NEW: Quiz generation & evaluation
# ---------------------------------------------------------------------------

@app.post("/quiz/generate", response_model=QuizResponse)
async def generate_quiz(request: QuizRequest) -> QuizResponse:
    """Generate a multiple-choice quiz question for a topic and level."""
    system_prompt = build_system_prompt("quiz", topic=request.topic, level=request.level)
    messages = [{"role": "user", "content": f"Generate a quiz question about: {request.topic}"}]

    try:
        content = get_completion(system_prompt, messages)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    # Parse the structured quiz response
    question, options = _parse_quiz(content)

    return QuizResponse(
        question=question,
        options=options,
        topic=request.topic,
        level=request.level,
    )


@app.post("/quiz/answer", response_model=QuizAnswerResponse)
async def evaluate_quiz_answer(request: QuizAnswerRequest) -> QuizAnswerResponse:
    """Evaluate a learner's quiz answer and record the result."""
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
        raise HTTPException(status_code=502, detail=str(exc))

    correct = "correct: true" in content.lower()
    score = 100 if correct else 0
    xp, badge = record_quiz(request.learner_id, request.topic, score)

    return QuizAnswerResponse(
        correct=correct,
        explanation=content,
        score=score,
        xp_gained=xp,
    )


# ---------------------------------------------------------------------------
# NEW: Personalised exercise generation
# ---------------------------------------------------------------------------

@app.post("/exercise/generate")
async def generate_exercise(learner_id: str, topic: str) -> dict:
    """Generate a personalised exercise based on learner level and known gaps."""
    profile = get_profile(learner_id)
    gaps = get_knowledge_gaps(learner_id)
    is_gap = topic in gaps

    system_prompt = build_system_prompt(
        "exercise", topic=topic, level=profile.level, is_gap_topic=is_gap
    )
    messages = [{"role": "user", "content": f"Give me a Python exercise on: {topic}"}]

    try:
        content = get_completion(system_prompt, messages)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    return {
        "topic": topic,
        "level": profile.level,
        "is_gap_topic": is_gap,
        "content": content,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_quiz(raw: str) -> tuple[str, list[str]]:
    """Extract question text and A/B/C/D options from raw LLM output."""
    question = ""
    options = []

    q_match = re.search(r"\*\*Question:\*\*\s*(.+?)(?=\n[A-D]\))", raw, re.DOTALL)
    if q_match:
        question = q_match.group(1).strip()

    opt_matches = re.findall(r"^([A-D])\)\s*(.+)$", raw, re.MULTILINE)
    options = [f"{letter}) {text}" for letter, text in opt_matches]

    if not question:
        question = raw.split("\n")[0].strip()
    if not options:
        options = ["A) See full response", "B) —", "C) —", "D) —"]

    return question, options


# ---------------------------------------------------------------------------
# Original error handlers — unchanged
# ---------------------------------------------------------------------------

@app.exception_handler(400)
async def bad_request_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=400, content={"error": "Bad request"})


@app.exception_handler(502)
async def bad_gateway_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=502, content={"error": "Bad gateway"})


@app.exception_handler(503)
async def service_unavailable_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=503, content={"error": "LLM unavailable, please retry"})


# ---------------------------------------------------------------------------
# Static files — must be mounted LAST
# ---------------------------------------------------------------------------

app.mount("/", StaticFiles(directory="static", html=True), name="static")
