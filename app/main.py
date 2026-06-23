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
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi import Depends

from app.classifier import classify_intent
from app.formatter import format_response
from app.llm_client import get_completion
from app.models import (
    ChatRequest, ChatResponse,
    QuizRequest, QuizResponse,
    QuizAnswerRequest, QuizAnswerResponse,
    ProgressResponse,
    GoogleAuthRequest, AuthResponse,
    EmailSignUpRequest, EmailSignInRequest,
    MessageFeedback, SurveyFeedback, FeedbackSummary,
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
    check_free_prompt_limit, increment_free_prompt_count, get_free_prompt_count,
    _get_ip,
)
from app.auth import (
    verify_google_token, get_or_create_user,
    create_session_token, get_current_user, require_user,
)
from app.feedback import (
    record_message_feedback, record_survey,
    increment_interaction, get_summary,
)
from app.email_auth import (
    register_email, confirm_email_token,
    sign_in_email, hash_password, get_email_user_by_id,
)
from app.certificates import generate_certificate_html, get_cert_id, CERT_CONFIGS

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
async def chat(request: ChatRequest, req: Request) -> ChatResponse:
    # Input validation (size, level, learner_id, history)
    validate_chat_request(request.message, request.history, request.level, request.learner_id)

    # Free-tier daily prompt limit check
    profile = get_profile(request.learner_id)
    if profile.tier == "free":
        ip = _get_ip(req)
        allowed, used = check_free_prompt_limit(request.learner_id, ip)
        if not allowed:
            return JSONResponse(
                status_code=402,
                content={
                    "error": "free_limit_reached",
                    "message": "You've used your 10 free daily prompts. Upgrade to Premium to continue learning!",
                    "used": used,
                    "limit": 10,
                },
            )
        increment_free_prompt_count(request.learner_id, ip)

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

    # Check if it's time to ask for a full survey
    ask_survey = increment_interaction(request.learner_id)

    return ChatResponse(
        intent=response_dict["intent"],
        content=response_dict["content"],
        topic=response_dict["topic"],
        level=profile.level,
        xp_gained=xp,
        badge=badge,
        ask_survey=ask_survey,
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
# Auth routes — Google OAuth
# ---------------------------------------------------------------------------


@app.post("/auth/google", response_model=AuthResponse)
async def auth_google(request: GoogleAuthRequest) -> AuthResponse:
    """Verify Google id_token, create/update user, return session token."""
    payload = verify_google_token(request.credential)
    user    = get_or_create_user(payload)
    token   = create_session_token(user.learner_id)
    return AuthResponse(
        token=token,
        learner_id=user.learner_id,
        name=user.name,
        email=user.email,
        picture=user.picture,
    )


@app.get("/auth/me", response_model=AuthResponse)
async def auth_me(user=Depends(require_user)) -> AuthResponse:
    """Return the currently authenticated user (validates session token)."""
    token = create_session_token(user.learner_id)   # refreshed token
    return AuthResponse(
        token=token,
        learner_id=user.learner_id,
        name=user.name,
        email=user.email,
        picture=user.picture,
    )


# ---------------------------------------------------------------------------
# Email auth routes
# ---------------------------------------------------------------------------

@app.post("/auth/signup")
async def auth_signup(request: EmailSignUpRequest) -> dict:
    """Register with email + password. Sends confirmation email."""
    pw_hash = hash_password(request.password)
    success, message = register_email(request.email, request.name, pw_hash)
    if not success:
        raise HTTPException(status_code=400, detail=message)
    return {"ok": True, "message": message}


@app.post("/auth/signin", response_model=AuthResponse)
async def auth_signin(request: EmailSignInRequest) -> AuthResponse:
    """Sign in with email + password."""
    success, user_data, message = sign_in_email(request.email, request.password)
    if not success or not user_data:
        raise HTTPException(status_code=401, detail=message)
    token = create_session_token(user_data["learner_id"])
    return AuthResponse(
        token=token,
        learner_id=user_data["learner_id"],
        name=user_data["name"],
        email=user_data["email"],
        picture="",
    )


@app.get("/auth/confirm")
async def auth_confirm(token: str) -> JSONResponse:
    """Handle email confirmation link click — redirects to frontend with result."""
    from fastapi.responses import RedirectResponse
    success, message = confirm_email_token(token)
    status = "confirmed" if success else "error"
    msg_encoded = message.replace(" ", "+")
    return RedirectResponse(url=f"/?auth={status}&msg={msg_encoded}", status_code=302)


# ---------------------------------------------------------------------------
# Feedback routes
# ---------------------------------------------------------------------------

@app.post("/feedback/message")
async def message_feedback(fb: MessageFeedback) -> dict:
    """Record a thumbs up/down on a single AI response."""
    validate_learner_id(fb.learner_id)
    record_message_feedback(fb)
    return {"ok": True}


@app.post("/feedback/survey")
async def survey_feedback(fb: SurveyFeedback) -> dict:
    """Record a full satisfaction survey response."""
    validate_learner_id(fb.learner_id)
    record_survey(fb)
    return {"ok": True, "message": "Thank you for your feedback! 🙏"}


@app.get("/feedback/summary", response_model=FeedbackSummary)
async def feedback_summary() -> FeedbackSummary:
    """Return aggregated feedback stats (admin use)."""
    return get_summary()


# ---------------------------------------------------------------------------
# Certificate routes
# ---------------------------------------------------------------------------


@app.get("/certificate/{level}", response_class=HTMLResponse)
async def get_certificate(
    level: str,
    name: str = "Learner",
    learner_id: str = "default",
) -> HTMLResponse:
    """
    Generate and return a printable HTML certificate.
    level: basic | advanced | executive
    """
    # Validate level
    if level not in CERT_CONFIGS:
        raise HTTPException(status_code=400, detail="Invalid certificate level. Use: basic, advanced, or executive")

    # Tier gate: check learner tier before issuing certificate
    profile = get_profile(learner_id)
    CERT_TIER_REQUIRED = {
        "basic":     {"tier1", "tier2", "tier3"},
        "advanced":  {"tier2", "tier3"},
        "executive": {"tier3"},
    }
    allowed_tiers = CERT_TIER_REQUIRED.get(level, set())
    if profile.tier not in allowed_tiers:
        tier_names = {"basic": "Pro Learner (Tier 1)", "advanced": "Career Builder (Tier 2)", "executive": "Elite (Tier 3)"}
        return HTMLResponse(
            content=f"""<!DOCTYPE html><html><head><meta charset="UTF-8"/><title>Upgrade Required</title>
            <style>body{{font-family:sans-serif;background:#0f1117;color:#e2e8f0;display:flex;align-items:center;justify-content:center;height:100vh;text-align:center;padding:20px}}
            .box{{background:#1a202c;border:1px solid #2d3748;border-radius:14px;padding:40px;max-width:420px}}
            h2{{color:#f6ad55;margin-bottom:12px}}p{{color:#a0aec0;line-height:1.6;margin-bottom:20px}}
            a{{background:#3182ce;color:#fff;text-decoration:none;padding:12px 24px;border-radius:8px;font-weight:700}}</style></head>
            <body><div class="box"><h2>🔒 Upgrade Required</h2>
            <p>The <strong>{level.title()}</strong> Certificate requires the <strong>{tier_names.get(level, 'Premium')}</strong> plan.</p>
            <p>Upgrade today to unlock certificates, unlimited prompts, and all courses.</p>
            <a href="https://paystack.shop/pay/vt_re4d3h52" target="_blank">💳 Upgrade Now</a></div></body></html>""",
            status_code=402,
        )

    # Sanitise name — max 80 chars, strip HTML
    import re as _re
    clean_name = _re.sub(r'[<>&"\']', '', name).strip()[:80] or "Learner"

    cert_id  = get_cert_id(learner_id, level)
    html_doc = generate_certificate_html(
        learner_name=clean_name,
        level=level,
        cert_id=cert_id,
    )
    return HTMLResponse(content=html_doc)


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
# /prompts/count — return daily free prompt usage
# ---------------------------------------------------------------------------

@app.get("/prompts/count")
async def prompts_count(learner_id: str = "default", req: Request = None) -> dict:
    validate_learner_id(learner_id)
    ip = _get_ip(req) if req else "unknown"
    count = get_free_prompt_count(learner_id, ip)
    profile = get_profile(learner_id)
    return {
        "used": count,
        "limit": 10,
        "tier": profile.tier,
        "is_limited": profile.tier == "free",
    }


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

    # Tier-gate: free users cannot start courses
    if profile.tier == "free":
        return JSONResponse(
            status_code=402,
            content={
                "error": "free_limit_reached",
                "message": "Courses require a Premium plan. Upgrade to Pro Learner or higher to access all courses!",
            },
        )

    # Tier 1 can only access beginner courses
    TIER1_COURSES = {
        "python-fundamentals", "python-strings",
        "python-collections", "python-control-flow",
    }
    TIER2_COURSES = TIER1_COURSES | {
        "python-functions-advanced", "python-oop", "python-modules-stdlib",
    }
    if profile.tier == "tier1" and course_name not in TIER1_COURSES:
        return JSONResponse(
            status_code=402,
            content={
                "error": "free_limit_reached",
                "message": "This course requires Career Builder (Tier 2) or Elite (Tier 3). Upgrade to unlock!",
            },
        )
    if profile.tier == "tier2" and course_name not in TIER2_COURSES:
        return JSONResponse(
            status_code=402,
            content={
                "error": "free_limit_reached",
                "message": "This course requires the Elite plan (Tier 3). Upgrade to unlock all advanced courses!",
            },
        )

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
