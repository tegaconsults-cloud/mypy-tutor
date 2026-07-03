"""
FastAPI application — MyPy Tutor (secured).
Security layer: rate limiting, input validation, security headers, sanitised errors.
"""

import datetime
import hashlib
import hmac
import logging
import re
import os as _os

from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi import Depends
from pydantic import BaseModel as _BM

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
    PasswordResetRequest, PasswordResetConfirm,
    AssignmentSubmit, AssignmentReview,
    CouponValidate, CouponCreate, ReferralUse,
    AccessCodeGenerate, EmailSignUpWithCode,
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
    verify_google_token, verify_google_token_strict, get_or_create_user,
    create_session_token, get_current_user, require_user,
)
from app.feedback import (
    record_message_feedback, record_survey,
    increment_interaction, get_summary,
)
from app.email_auth import (
    register_email, confirm_email_token,
    sign_in_email, hash_password, get_email_user_by_id,
    request_password_reset, confirm_password_reset,
)
from app.certificates import generate_certificate_html, get_cert_id, CERT_CONFIGS
from app.admin import (
    verify_admin_login, create_admin_token, verify_admin_token,
    add_payment, confirm_payment, get_payments, get_revenue_summary,
    invite_team_member, create_task, update_task_status, get_team, get_tasks,
    log_certificate, get_certificates, log_activity,
)
from app.db import (
    init_db, upgrade_tier_db, get_all_confirmed_emails,
    get_activity_log, get_certificates_db,
    # prompt history
    save_prompt_history, get_prompt_history,
    # quiz attempts
    save_quiz_attempt, get_quiz_attempts,
    # assignments
    create_assignment_db, submit_assignment_db,
    review_assignment_db, get_assignments_db, get_all_assignments_db,
    # referrals
    create_referral_code, get_referral_code, use_referral_code,
    get_referral_uses, get_learner_referral_code,
    # coupons
    create_coupon_db, validate_coupon_db, use_coupon_db, get_all_coupons_db,
    # invoices
    create_invoice_db, get_invoice_db, get_invoices_by_learner, get_all_invoices_db,
    # access codes
    create_access_code, validate_access_code, redeem_access_code, get_all_access_codes,
)
from app.supabase_client import (
    sb_upsert_profile, sb_get_or_create_conversation,
    sb_save_message, sb_load_messages, sb_load_all_conversations,
    sb_save_certificate, sb_save_payment, sb_update_tier, sb_enabled,
    sb_load_all_email_accounts,
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

from app.email_auth import _load_confirmed_from_db
init_db()
_load_confirmed_from_db()
logger.info("Database ready")

app = FastAPI(
    title="MyPy Tutor",
    version="2.0.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

_RENDER_URL = _os.getenv("RENDER_EXTERNAL_URL", "")
_allowed_origins = list(filter(None, [
    _RENDER_URL,
    "http://localhost:8000",
    "http://127.0.0.1:8000",
])) or ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_origin_regex=r"https://.*\.onrender\.com",
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
    allow_credentials=False,
)

app.add_middleware(SecurityMiddleware)

# ---------------------------------------------------------------------------
# /chat
# ---------------------------------------------------------------------------

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, req: Request,
               background_tasks: BackgroundTasks) -> ChatResponse:
    validate_chat_request(request.message, request.history, request.level, request.learner_id)

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
    topic  = _detect_topic(request.message)
    gaps   = get_knowledge_gaps(request.learner_id)
    is_gap = topic in gaps if topic else False

    system_prompt = build_system_prompt(intent, topic=topic, level=request.level, is_gap_topic=is_gap)

    # ── Resolve conversation_id ──────────────────────────────────────────
    conv_id = request.conversation_id or sb_get_or_create_conversation(request.learner_id)
    if not conv_id:
        conv_id = f"local_{request.learner_id}"

    # ── Build message list ───────────────────────────────────────────────
    # If client sends no history AND Supabase is up, load last 10 turns
    # so Sir. Tega continues exactly where the learner left off.
    history_messages = [{"role": m.role, "content": m.content} for m in request.history]
    if not history_messages and sb_enabled():
        sb_history = sb_load_messages(conv_id, limit=10)
        history_messages = [{"role": m["role"], "content": m["content"]} for m in sb_history]
    history_messages.append({"role": "user", "content": request.message})

    try:
        content = get_completion(system_prompt, history_messages)
    except Exception as exc:
        exc_type = type(exc).__name__.lower()
        if any(k in exc_type for k in ("ratelimit", "timeout", "serviceunavailable")):
            logger.warning("LLM unavailable: %s", exc)
            raise HTTPException(status_code=503, detail="LLM unavailable, please retry")
        logger.error("LLM error: %s", exc)
        raise HTTPException(status_code=502, detail="AI service error. Please try again.")

    response_dict  = format_response(content, intent)
    detected_topic = response_dict.get("topic") or topic
    xp, badge      = record_lesson(request.learner_id, detected_topic or "", intent)
    profile        = get_profile(request.learner_id)

    log_activity(request.learner_id, f"chat:{intent}",
                 f"topic={detected_topic or '—'} | msg={request.message[:80]}")

    # ── Persist: SQLite (sync, fast local) ────────────────────────────────
    save_prompt_history(request.learner_id, "user",      request.message, intent, detected_topic or "")
    save_prompt_history(request.learner_id, "assistant", content,         intent, detected_topic or "")

    # ── Supabase writes are background tasks — never block the response ────
    background_tasks.add_task(
        sb_save_message, conv_id, request.learner_id, "user",
        request.message, intent, detected_topic or ""
    )
    background_tasks.add_task(
        sb_save_message, conv_id, request.learner_id, "assistant",
        content, intent, detected_topic or ""
    )

    ask_survey = increment_interaction(request.learner_id)

    return ChatResponse(
        intent=response_dict["intent"],
        content=response_dict["content"],
        topic=response_dict["topic"],
        level=profile.level,
        xp_gained=xp,
        badge=badge,
        ask_survey=ask_survey,
        conversation_id=conv_id,
    )

# ---------------------------------------------------------------------------
# /topics  /health
# ---------------------------------------------------------------------------

@app.get("/topics")
async def topics() -> dict:
    return {"topics": get_topics()}


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Auth — Google OAuth
# ---------------------------------------------------------------------------

@app.get("/auth/config")
async def auth_config() -> dict:
    return {
        "google_client_id": _os.getenv("GOOGLE_CLIENT_ID", ""),
        "google_enabled":   bool(_os.getenv("GOOGLE_CLIENT_ID", "")),
    }


@app.get("/auth/google/login")
async def auth_google_login() -> JSONResponse:
    from fastapi.responses import RedirectResponse
    import urllib.parse

    client_id    = _os.getenv("GOOGLE_CLIENT_ID", "")
    app_url      = _os.getenv("APP_URL", "https://mypytutor.onrender.com")
    redirect_uri = f"{app_url}/auth/google/callback"

    if not client_id:
        return RedirectResponse(url="/?auth=error&msg=Google+Sign-In+not+configured")

    params = urllib.parse.urlencode({
        "client_id":     client_id,
        "redirect_uri":  redirect_uri,
        "response_type": "code",
        "scope":         "openid email profile",
        "access_type":   "online",
        "prompt":        "select_account",
    })
    return RedirectResponse(url=f"https://accounts.google.com/o/oauth2/v2/auth?{params}")


@app.get("/auth/google/callback")
async def auth_google_callback(code: str = None, error: str = None) -> JSONResponse:
    from fastapi.responses import RedirectResponse
    import urllib.parse, json

    app_url       = _os.getenv("APP_URL", "https://mypytutor.onrender.com")
    client_id     = _os.getenv("GOOGLE_CLIENT_ID", "")
    client_secret = _os.getenv("GOOGLE_CLIENT_SECRET", "")
    redirect_uri  = f"{app_url}/auth/google/callback"

    if error or not code:
        msg = urllib.parse.quote(error or "Google sign-in was cancelled")
        return RedirectResponse(url=f"/?auth=error&msg={msg}")

    try:
        import httpx as _httpx
        async with _httpx.AsyncClient(timeout=10) as hc:
            token_res = await hc.post("https://oauth2.googleapis.com/token", data={
                "code":          code,
                "client_id":     client_id,
                "client_secret": client_secret,
                "redirect_uri":  redirect_uri,
                "grant_type":    "authorization_code",
            })
            if token_res.status_code != 200:
                logger.error("Token exchange failed: %s", token_res.text)
                return RedirectResponse(url="/?auth=error&msg=Token+exchange+failed")

            tokens   = token_res.json()
            id_token = tokens.get("id_token", "")

        payload = verify_google_token(id_token)
        user    = get_or_create_user(payload)
        token   = create_session_token(user.learner_id)
        # Mirror to Supabase
        sb_upsert_profile(user.learner_id, user.email, user.name)

        import urllib.parse as _up
        user_data = _up.quote(json.dumps({
            "token":      token,
            "learner_id": user.learner_id,
            "name":       user.name,
            "email":      user.email,
            "picture":    user.picture,
        }))
        return RedirectResponse(url=f"/?auth=google_success&user={user_data}")

    except Exception as exc:
        logger.error("Google OAuth callback error: %s", exc)
        return RedirectResponse(url="/?auth=error&msg=Google+sign-in+failed")


@app.post("/auth/google", response_model=AuthResponse)
async def auth_google(request: GoogleAuthRequest) -> AuthResponse:
    """One-Tap / GSI token submitted directly from client — uses strict signature verification."""
    payload = await verify_google_token_strict(request.credential)
    user    = get_or_create_user(payload)
    token   = create_session_token(user.learner_id)
    # Mirror to Supabase
    sb_upsert_profile(user.learner_id, user.email, user.name)
    return AuthResponse(
        token=token, learner_id=user.learner_id,
        name=user.name, email=user.email, picture=user.picture,
    )

@app.get("/auth/me", response_model=AuthResponse)
async def auth_me(user=Depends(require_user)) -> AuthResponse:
    token = create_session_token(user.learner_id)
    return AuthResponse(
        token=token, learner_id=user.learner_id,
        name=user.name, email=user.email, picture=user.picture,
    )


# ---------------------------------------------------------------------------
# Email auth routes
# ---------------------------------------------------------------------------

@app.post("/auth/signup")
async def auth_signup(request: EmailSignUpWithCode) -> dict:
    """
    Register with email + password.
    Optional access_code: validated now, redeemed on email confirmation.
    Tier is NOT granted until the email is confirmed — prevents abuse.
    """
    pw_hash = hash_password(request.password)

    # Validate access code BEFORE registering (fail fast with clear message)
    access_code = request.access_code.strip().upper() if request.access_code else ""
    code_rec = None
    if access_code:
        code_rec = validate_access_code(access_code)
        if not code_rec:
            raise HTTPException(
                status_code=400,
                detail="Invalid or already-used access code. Please check and try again."
            )

    success, message = register_email(request.email, request.name, pw_hash)
    if not success:
        raise HTTPException(status_code=400, detail=message)

    from app.email_auth import _make_learner_id, _pending
    learner_id = _make_learner_id(request.email)

    # Store the access code in pending data — applied after email confirmation
    if access_code and code_rec:
        _pending[request.email.lower()]["access_code"] = access_code
        _pending[request.email.lower()]["access_tier"] = code_rec["tier"]

    # Mirror to Supabase (pre-confirm stub — real data added on confirm)
    import threading as _thr
    _thr.Thread(
        target=sb_upsert_profile,
        args=(learner_id, request.email, request.name),
        daemon=False,
    ).start()

    response = {"ok": True, "message": message}
    if code_rec:
        tier_labels = {"tier1": "Pro Learner", "tier2": "Career Builder", "tier3": "Elite"}
        response["code_accepted"] = True
        response["tier_on_confirm"] = tier_labels.get(code_rec["tier"], code_rec["tier"])
    return response


@app.post("/auth/signin", response_model=AuthResponse)
async def auth_signin(request: EmailSignInRequest) -> AuthResponse:
    success, user_data, message = sign_in_email(request.email, request.password)
    if not success or not user_data:
        raise HTTPException(status_code=401, detail=message)
    token = create_session_token(user_data["learner_id"])
    # Ensure Supabase profile row exists before any conversation inserts (Bug 4 fix)
    import threading as _thr
    _thr.Thread(
        target=sb_upsert_profile,
        args=(user_data["learner_id"], user_data["email"], user_data["name"]),
        daemon=False,
    ).start()
    return AuthResponse(
        token=token, learner_id=user_data["learner_id"],
        name=user_data["name"], email=user_data["email"], picture="",
    )


@app.get("/auth/confirm")
async def auth_confirm(token: str) -> JSONResponse:
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
    validate_learner_id(fb.learner_id)
    record_message_feedback(fb)
    return {"ok": True}


@app.post("/feedback/survey")
async def survey_feedback(fb: SurveyFeedback) -> dict:
    validate_learner_id(fb.learner_id)
    record_survey(fb)
    return {"ok": True, "message": "Thank you for your feedback! 🙏"}


@app.get("/feedback/summary", response_model=FeedbackSummary)
async def feedback_summary() -> FeedbackSummary:
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
    if level not in CERT_CONFIGS:
        raise HTTPException(status_code=400, detail="Invalid certificate level.")

    profile = get_profile(learner_id)
    CERT_TIER_REQUIRED = {
        "basic":     {"tier1", "tier2", "tier3"},
        "advanced":  {"tier2", "tier3"},
        "executive": {"tier3"},
    }
    allowed_tiers = CERT_TIER_REQUIRED.get(level, set())
    if profile.tier not in allowed_tiers:
        tier_names = {
            "basic":     "Pro Learner (Tier 1)",
            "advanced":  "Career Builder (Tier 2)",
            "executive": "Elite (Tier 3)",
        }
        return HTMLResponse(
            content=f"""<!DOCTYPE html><html><head><meta charset="UTF-8"/><title>Upgrade Required</title>
            <style>body{{font-family:sans-serif;background:#0f1117;color:#e2e8f0;display:flex;
            align-items:center;justify-content:center;height:100vh;text-align:center;padding:20px}}
            .box{{background:#1a202c;border:1px solid #2d3748;border-radius:14px;padding:40px;max-width:420px}}
            h2{{color:#f6ad55;margin-bottom:12px}}p{{color:#a0aec0;line-height:1.6;margin-bottom:20px}}
            a{{background:#3182ce;color:#fff;text-decoration:none;padding:12px 24px;border-radius:8px;
            font-weight:700}}</style></head>
            <body><div class="box"><h2>🔒 Upgrade Required</h2>
            <p>The <strong>{level.title()}</strong> Certificate requires
            <strong>{tier_names.get(level,'Premium')}</strong>.</p>
            <p>Upgrade to unlock certificates, unlimited prompts, and all courses.</p>
            <a href="https://paystack.shop/pay/vt_re4d3h52" target="_blank">💳 Upgrade Now</a>
            </div></body></html>""",
            status_code=402,
        )

    import re as _re
    clean_name = _re.sub(r'[<>&"\']', '', name).strip()[:80] or "Learner"
    cert_id    = get_cert_id(learner_id, level)
    log_certificate(cert_id, learner_id, clean_name, level)
    # Mirror certificate to Supabase
    sb_save_certificate(cert_id, learner_id, clean_name, level)
    html_doc   = generate_certificate_html(learner_name=clean_name, level=level, cert_id=cert_id)
    return HTMLResponse(content=html_doc)


# ---------------------------------------------------------------------------
# /progress  /prompts/count
# ---------------------------------------------------------------------------

@app.get("/progress/{learner_id}", response_model=ProgressResponse)
async def get_progress(learner_id: str) -> ProgressResponse:
    validate_learner_id(learner_id)
    profile = get_profile(learner_id)
    gaps    = get_knowledge_gaps(learner_id)
    return ProgressResponse(
        learner_id=profile.learner_id,
        level=profile.level,
        tier=profile.tier,
        xp=profile.xp,
        badges=profile.badges,
        topics_seen=profile.topics_seen,
        knowledge_gaps=gaps,
        current_course=profile.current_course,
        current_course_step=profile.current_course_step,
        completed_projects=profile.completed_projects,
        topic_progress=profile.topic_progress,
    )


@app.get("/prompts/count")
async def prompts_count(learner_id: str = "default", req: Request = None) -> dict:
    from app.security import FREE_DAILY_LIMIT
    validate_learner_id(learner_id)
    ip      = _get_ip(req) if req else "unknown"
    count   = get_free_prompt_count(learner_id, ip)
    profile = get_profile(learner_id)
    return {
        "used": count,
        "limit": FREE_DAILY_LIMIT,
        "tier": profile.tier,
        "is_limited": profile.tier == "free",
    }

# ---------------------------------------------------------------------------
# Courses
# ---------------------------------------------------------------------------

@app.get("/courses")
async def list_courses(level: str = "beginner") -> dict:
    validate_level(level)
    courses = get_courses_for_level(level)
    return {
        "level": level,
        "courses": [
            {"name": c.name, "description": c.description,
             "level": c.level, "total_steps": len(c.steps)}
            for c in courses
        ],
    }


@app.post("/course/start")
async def start_course(learner_id: str, course_name: str) -> dict:
    validate_learner_id(learner_id)
    validate_course_name(course_name)

    course  = get_course(course_name)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found.")

    profile = get_profile(learner_id)

    TIER1_COURSES = {
        "python-fundamentals", "python-strings",
        "python-collections", "python-control-flow",
    }
    TIER2_COURSES = TIER1_COURSES | {
        "python-functions-advanced", "python-oop", "python-modules-stdlib",
    }

    if profile.tier == "free":
        return JSONResponse(status_code=402, content={
            "error": "upgrade_required",
            "upgrade_url": "https://paystack.shop/pay/vt_re4d3h52",
            "message": "Courses require a Premium plan. Upgrade to Pro Learner or higher!",
        })
    if profile.tier == "tier1" and course_name not in TIER1_COURSES:
        return JSONResponse(status_code=402, content={
            "error": "upgrade_required",
            "upgrade_url": "https://paystack.shop/pay/vt_re4d3h52",
            "message": "This course requires Career Builder (Tier 2) or Elite (Tier 3). Upgrade to unlock!",
        })
    if profile.tier == "tier2" and course_name not in TIER2_COURSES:
        return JSONResponse(status_code=402, content={
            "error": "upgrade_required",
            "upgrade_url": "https://paystack.shop/pay/vt_re4d3h52",
            "message": "This course requires the Elite plan (Tier 3). Upgrade to unlock all advanced courses!",
        })

    profile.current_course      = course_name
    profile.current_course_step = 1

    from app.progress import save_profile
    save_profile(profile)

    step          = course.steps[0]
    system_prompt = build_system_prompt(step.intent, topic=step.title, level=profile.level)
    messages      = [{"role": "user", "content": f"Teach me: {step.description}"}]

    try:
        content = get_completion(system_prompt, messages)
    except Exception as exc:
        logger.error("Course start LLM error: %s", exc)
        raise HTTPException(status_code=502, detail="AI service error. Please try again.")

    return {
        "course": course_name, "step": step.step,
        "title": step.title, "total_steps": len(course.steps), "content": content,
    }


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
    profile  = get_profile(learner_id)
    step_idx = profile.current_course_step - 1

    if step_idx >= len(course.steps):
        from app.progress import _award_badge, save_profile, XP_PROJECT
        profile.completed_projects.append(profile.current_course)
        profile.xp += XP_PROJECT
        badge = _award_badge(profile, "course_complete")
        profile.current_course      = None
        profile.current_course_step = 0
        save_profile(profile)
        return {
            "completed": True, "course": course.name,
            "xp_gained": XP_PROJECT, "badge": badge,
            "content": f"🎉 Congratulations! You've completed **{course.name}**. You earned {XP_PROJECT} XP!",
        }

    step          = course.steps[step_idx]
    system_prompt = build_system_prompt(step.intent, topic=step.title, level=profile.level)
    messages      = [{"role": "user", "content": f"Teach me: {step.description}"}]

    try:
        content = get_completion(system_prompt, messages)
    except Exception as exc:
        logger.error("Course next LLM error: %s", exc)
        raise HTTPException(status_code=502, detail="AI service error. Please try again.")

    xp, badge = record_lesson(learner_id, step.title, step.intent)
    return {
        "completed": False, "course": course.name,
        "step": step.step, "title": step.title,
        "total_steps": len(course.steps), "content": content,
        "xp_gained": xp, "badge": badge,
    }

# ---------------------------------------------------------------------------
# Quiz & Exercise
# ---------------------------------------------------------------------------

@app.post("/quiz/generate", response_model=QuizResponse)
async def generate_quiz(request: QuizRequest) -> QuizResponse:
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
    correct = "correct: true" in content.lower()
    score   = 100 if correct else 0
    xp, _   = record_quiz(request.learner_id, request.topic, score)
    # Persist full quiz attempt record
    save_quiz_attempt(request.learner_id, request.topic,
                      request.question, request.answer, correct, score)
    return QuizAnswerResponse(correct=correct, explanation=content, score=score, xp_gained=xp)


@app.post("/exercise/generate")
async def generate_exercise(learner_id: str, topic: str) -> dict:
    validate_learner_id(learner_id)
    validate_topic(topic)
    profile  = get_profile(learner_id)
    gaps     = get_knowledge_gaps(learner_id)
    is_gap   = topic in gaps
    system_prompt = build_system_prompt("exercise", topic=topic, level=profile.level, is_gap_topic=is_gap)
    messages = [{"role": "user", "content": f"Give me a Python exercise on: {topic}"}]
    try:
        content = get_completion(system_prompt, messages)
    except Exception as exc:
        logger.error("Exercise LLM error: %s", exc)
        raise HTTPException(status_code=502, detail="AI service error. Please try again.")
    return {"topic": topic, "level": profile.level, "is_gap_topic": is_gap, "content": content}


# ---------------------------------------------------------------------------
# Helper
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
# ITEM 4 — Paystack webhook (auto-upgrade tier on charge.success)
# ---------------------------------------------------------------------------

# Tier map: Paystack plan name (lowercase) → internal tier
_PAYSTACK_PLAN_TIER: dict[str, str] = {
    "pro learner":   "tier1",
    "tier1":         "tier1",
    "tier 1":        "tier1",
    "career builder":"tier2",
    "tier2":         "tier2",
    "tier 2":        "tier2",
    "elite":         "tier3",
    "tier3":         "tier3",
    "tier 3":        "tier3",
    # subscription plan codes (set these in Paystack dashboard metadata)
    "plan_tier1":    "tier1",
    "plan_tier2":    "tier2",
    "plan_tier3":    "tier3",
}


@app.post("/webhooks/paystack")
async def paystack_webhook(request: Request) -> dict:
    """
    Paystack sends a POST with a JSON body and an X-Paystack-Signature header.
    We verify the HMAC-SHA512 signature using PAYSTACK_SECRET_KEY, then
    on charge.success we upgrade the user's tier automatically.
    """
    secret_key = _os.getenv("PAYSTACK_SECRET_KEY", "")
    body_bytes  = await request.body()

    # Verify signature
    if secret_key:
        sig_header = request.headers.get("x-paystack-signature", "")
        expected   = hmac.new(
            secret_key.encode(), body_bytes, hashlib.sha512
        ).hexdigest()
        if not hmac.compare_digest(sig_header, expected):
            logger.warning("Paystack webhook signature mismatch — ignored")
            raise HTTPException(status_code=400, detail="Invalid signature")

    import json as _json
    try:
        event = _json.loads(body_bytes)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    event_type = event.get("event", "")
    data       = event.get("data", {})

    if event_type == "charge.success":
        customer   = data.get("customer", {})
        email      = customer.get("email", "").lower()
        meta       = data.get("metadata", {}) or {}
        amount_kob = data.get("amount", 0)           # Paystack amounts are in kobo
        amount_ngn = amount_kob / 100

        # Determine tier from metadata or amount
        plan_meta = str(meta.get("plan", "") or meta.get("tier", "")).lower()
        tier      = _PAYSTACK_PLAN_TIER.get(plan_meta)

        if not tier:
            # Fall back: infer tier from amount
            if amount_ngn >= 18000:
                tier = "tier3"
            elif amount_ngn >= 8000:
                tier = "tier2"
            elif amount_ngn >= 4000:
                tier = "tier1"

        if tier and email:
            # Find learner_id from email account
            from app.db import load_email_account
            acct = load_email_account(email)
            learner_id = acct["learner_id"] if acct else email

            # Upgrade in SQLite (persistent) + memory cache
            upgrade_tier_db(learner_id, tier)
            from app.progress import get_profile as _gp, save_profile as _sp
            p      = _gp(learner_id)
            p.tier = tier
            _sp(p)

            # Record payment in admin
            plan_label = {
                "tier1": "Pro Learner (₦5,000/mo)",
                "tier2": "Career Builder (₦10,000/mo)",
                "tier3": "Elite (₦20,000/mo)",
            }.get(tier, tier)
            payment = add_payment(email, customer.get("name", email), amount_ngn, plan_label, "paystack")
            log_activity(learner_id, "payment:webhook",
                         f"Paystack charge.success | tier={tier} | ₦{amount_ngn:.0f}")

            # Auto-generate invoice
            import secrets as _sec
            invoice_id = f"INV-{_sec.token_hex(5).upper()}"
            create_invoice_db(invoice_id, payment.id, learner_id, email,
                              customer.get("name", email), plan_label, amount_ngn)
            # Mirror payment to Supabase
            sb_save_payment(payment.id, email, customer.get("name", email),
                            amount_ngn, plan_label, "paystack")
            # Sync updated tier to Supabase profile
            sb_update_tier(learner_id, tier)
            logger.info("Paystack webhook: upgraded %s → %s | invoice=%s", email, tier, invoice_id)

    return {"ok": True}

# ---------------------------------------------------------------------------
# Global error handlers
# ---------------------------------------------------------------------------

@app.exception_handler(RequestValidationError)
async def request_validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    try:
        first  = exc.errors()[0]
        field  = " → ".join(str(loc) for loc in first.get("loc", []) if loc != "body")
        msg    = first.get("msg", "Invalid value")
        detail = f"{field}: {msg}" if field else msg
    except Exception:
        detail = "Invalid request data"
    return JSONResponse(status_code=422, content={"error": detail})


@app.exception_handler(400)
async def bad_request_handler(request: Request, exc: Exception) -> JSONResponse:
    detail = getattr(exc, "detail", None)
    if isinstance(detail, str):
        return JSONResponse(status_code=400, content={"error": detail})
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
# Admin Pydantic models
# ---------------------------------------------------------------------------

class _AdminLogin(_BM):
    email:    str
    password: str


class _PaymentAdd(_BM):
    user_email: str
    user_name:  str
    amount:     float
    plan:       str
    method:     str = "bank"
    notes:      str = ""


class _TaskCreate(_BM):
    title:       str
    description: str
    assigned_to: str
    priority:    str = "medium"
    due_date:    str = ""


class _TeamInvite(_BM):
    email: str
    name:  str
    role:  str = "team"


def _require_admin(request: Request) -> str:
    token = request.headers.get("X-Admin-Token", "") or request.cookies.get("admin_token", "")
    if not token or not verify_admin_token(token):
        raise HTTPException(status_code=403, detail="Admin authentication required.")
    return token


# ---------------------------------------------------------------------------
# Admin routes
# ---------------------------------------------------------------------------

@app.post("/admin/login")
async def admin_login(body: _AdminLogin) -> dict:
    if not verify_admin_login(body.email, body.password):
        raise HTTPException(status_code=401, detail="Invalid admin credentials.")
    token = create_admin_token()
    return {"ok": True, "token": token}


@app.get("/admin/dashboard")
async def admin_dashboard(request: Request) -> dict:
    _require_admin(request)
    from app.progress import _store as learner_store
    from app.security import _daily_prompt_store

    today        = datetime.date.today().isoformat()
    active_today = sum(1 for k, (d, c) in _daily_prompt_store.items() if d == today and c > 0)

    # Merge memory store with SQLite confirmed emails for accurate user count
    try:
        db_emails = get_all_confirmed_emails()
        email_count = len(db_emails)
    except Exception:
        email_count = 0

    total_users = max(len(learner_store), email_count)

    return {
        "users": {"total": total_users, "active_today": active_today},
        "users_by_tier": {
            t: sum(1 for p in learner_store.values() if p.tier == t)
            for t in ["free", "tier1", "tier2", "tier3"]
        },
        "revenue":      get_revenue_summary(),
        "payments":     len(get_payments()),
        "certificates": len(get_certificates()),
        "tasks": {
            "total":       len(get_tasks()),
            "open":        sum(1 for t in get_tasks() if t.status == "open"),
            "in_progress": sum(1 for t in get_tasks() if t.status == "in_progress"),
            "done":        sum(1 for t in get_tasks() if t.status == "done"),
        },
        "feedback":  get_summary().model_dump(),
        "team_size": len(get_team()),
    }

@app.get("/admin/users")
async def admin_list_users(request: Request) -> dict:
    _require_admin(request)
    from app.progress import _store as ls

    # Pull all confirmed email accounts from SQLite (persistent across restarts)
    try:
        db_emails = get_all_confirmed_emails()
    except Exception:
        from app.email_auth import _confirmed
        db_emails = [
            {"email": e, "name": u["name"], "learner_id": u["learner_id"]}
            for e, u in _confirmed.items()
        ]

    # Build a learner_id → email/name lookup for enriching profiles
    id_to_email = {r["learner_id"]: r for r in db_emails}

    users = []
    for lid, profile in ls.items():
        info = id_to_email.get(lid, {})
        users.append({
            "learner_id":    lid,
            "email":         info.get("email", profile.email or ""),
            "name":          info.get("name", profile.display_name or ""),
            "tier":          profile.tier,
            "level":         profile.level,
            "xp":            profile.xp,
            "topics_seen":   len(profile.topics_seen),
            "courses_done":  len(profile.completed_projects),
            "badges":        len(profile.badges),
            "current_course": profile.current_course,
        })

    # Include email accounts not yet in memory (signed up but not chatted)
    seen_ids = {u["learner_id"] for u in users}
    for r in db_emails:
        if r["learner_id"] not in seen_ids:
            users.append({
                "learner_id": r["learner_id"],
                "email":      r["email"],
                "name":       r["name"],
                "tier":       "free",
                "level":      "beginner",
                "xp":         0,
                "topics_seen": 0,
                "courses_done": 0,
                "badges":      0,
                "current_course": None,
            })

    return {
        "learner_profiles": users,
        "email_accounts":   [{"email": r["email"], "name": r["name"],
                               "learner_id": r["learner_id"], "type": "email"}
                              for r in db_emails],
        "total":        len(users),
        "email_signups": len(db_emails),
    }


@app.get("/admin/users/{learner_id}")
async def admin_user_detail(learner_id: str, request: Request) -> dict:
    _require_admin(request)
    validate_learner_id(learner_id)
    from app.progress import _store as ls
    from app.security import _daily_prompt_store

    p = ls.get(learner_id)
    if not p:
        # Try loading from SQLite
        from app.db import load_profile
        row = load_profile(learner_id)
        if not row:
            raise HTTPException(status_code=404, detail="User not found.")
        p = get_profile(learner_id)

    today         = datetime.date.today().isoformat()
    entry         = _daily_prompt_store.get(learner_id)
    prompts_today = entry[1] if entry and entry[0] == today else 0

    return {
        "learner_id":     learner_id,
        "email":          p.email,
        "name":           p.display_name,
        "tier":           p.tier,
        "level":          p.level,
        "xp":             p.xp,
        "badges":         p.badges,
        "topics_seen":    p.topics_seen,
        "prompts_today":  prompts_today,
        "current_course": p.current_course,
        "course_step":    p.current_course_step,
        "courses_done":   p.completed_projects,
        "topic_progress": {
            k: {"lessons": v.lessons_completed,
                "exercises_passed": v.exercises_passed,
                "exercises_attempted": v.exercises_attempted,
                "weak": v.weak}
            for k, v in p.topic_progress.items()
        },
    }

# ITEM 1 — set-tier now writes to both memory AND SQLite via upgrade_tier_db
@app.post("/admin/users/{learner_id}/set-tier")
async def admin_set_tier(learner_id: str, request: Request) -> dict:
    _require_admin(request)
    validate_learner_id(learner_id)
    body = await request.json()
    tier = body.get("tier", "free")
    if tier not in ("free", "tier1", "tier2", "tier3"):
        raise HTTPException(status_code=400, detail="Invalid tier.")

    from app.progress import _store as ls, save_profile as _sp
    # Ensure profile is in memory
    p      = get_profile(learner_id)   # loads from SQLite if not in cache
    p.tier = tier
    _sp(p)                             # saves to memory + SQLite
    upgrade_tier_db(learner_id, tier)  # belt-and-suspenders: direct SQL UPDATE
    log_activity(learner_id, "admin:set-tier", f"tier set to {tier}")
    return {"ok": True, "learner_id": learner_id, "tier": tier}


@app.post("/admin/users/{learner_id}/terminate")
async def admin_terminate_user(learner_id: str, request: Request) -> dict:
    _require_admin(request)
    validate_learner_id(learner_id)
    from app.progress import save_profile as _sp
    p = get_profile(learner_id)
    p.tier               = "free"
    p.current_course     = None
    p.current_course_step= 0
    _sp(p)
    upgrade_tier_db(learner_id, "free")
    log_activity(learner_id, "admin:terminate", "subscription terminated by admin")
    return {"ok": True, "message": f"Subscription terminated for {learner_id}"}


@app.get("/admin/payments")
async def admin_payments(request: Request) -> dict:
    _require_admin(request)
    payments = get_payments()
    return {
        "payments": [
            {"id": p.id, "user_email": p.user_email, "user_name": p.user_name,
             "amount": p.amount, "currency": p.currency, "plan": p.plan,
             "method": p.method, "status": p.status, "notes": p.notes,
             "created_at": datetime.datetime.fromtimestamp(p.created_at).isoformat()}
            for p in payments
        ],
        "summary": get_revenue_summary(),
    }


@app.post("/admin/payments/add")
async def admin_add_payment(body: _PaymentAdd, request: Request) -> dict:
    _require_admin(request)
    p = add_payment(body.user_email, body.user_name, body.amount,
                    body.plan, body.method, body.notes)
    return {"ok": True, "payment_id": p.id}


@app.post("/admin/payments/confirm/{payment_id}")
async def admin_confirm_payment(payment_id: str, request: Request) -> dict:
    _require_admin(request)
    ok = confirm_payment(payment_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Payment not found.")
    return {"ok": True}


@app.get("/admin/certificates")
async def admin_certificates(request: Request) -> dict:
    _require_admin(request)
    # Prefer SQLite persistent store; fall back to in-memory
    try:
        certs_raw = get_certificates_db()
        return {"certificates": certs_raw, "total": len(certs_raw)}
    except Exception:
        pass
    certs = get_certificates()
    return {
        "certificates": [
            {"cert_id": c.cert_id, "learner_id": c.learner_id,
             "learner_name": c.learner_name, "level": c.level,
             "issued_at": datetime.datetime.fromtimestamp(c.issued_at).isoformat()}
            for c in certs
        ],
        "total": len(certs),
    }

@app.get("/admin/team")
async def admin_team(request: Request) -> dict:
    _require_admin(request)
    return {
        "members": [{"email": m.email, "name": m.name, "role": m.role, "status": m.status}
                    for m in get_team()],
        "tasks":   [{"id": t.id, "title": t.title, "assigned_to": t.assigned_to,
                     "priority": t.priority, "status": t.status,
                     "due_date": t.due_date, "description": t.description}
                    for t in get_tasks()],
    }


@app.post("/admin/team/invite")
async def admin_invite_team(body: _TeamInvite, request: Request) -> dict:
    _require_admin(request)
    m = invite_team_member(body.email, body.name, body.role)
    try:
        from app.email_auth import _send_email_async
        _app_url = _os.getenv("APP_URL", "https://mypytutor.onrender.com")
        html = f"""<div style="font-family:Arial;background:#0f1117;color:#e2e8f0;padding:32px;">
        <h2 style="color:#63b3ed;">🐍 MyPy Tutor — Team Invitation</h2>
        <p>Hi {body.name},</p>
        <p>You've been invited to join the MyPy Tutor team as <strong>{body.role}</strong>.</p>
        <a href="{_app_url}" style="background:#3182ce;color:#fff;padding:12px 24px;border-radius:8px;
        text-decoration:none;font-weight:bold;">Access Platform</a>
        <p style="color:#4a5568;margin-top:20px;font-size:0.8rem;">MyPy Tutor · Teamsamikoko Global Academy</p>
        </div>"""
        _send_email_async(body.email, "You're invited to join the MyPy Tutor team!", html,
                          f"Hi {body.name}, you've been invited to the MyPy Tutor team as {body.role}.")
    except Exception as e:
        logger.warning("Team invite email failed: %s", e)
    return {"ok": True, "member": {"email": m.email, "name": m.name, "role": m.role}}


@app.post("/admin/tasks/create")
async def admin_create_task(body: _TaskCreate, request: Request) -> dict:
    _require_admin(request)
    t = create_task(body.title, body.description, body.assigned_to, body.priority, body.due_date)
    try:
        from app.email_auth import _send_email_async
        _app_url = _os.getenv("APP_URL", "https://mypytutor.onrender.com")
        html = f"""<div style="font-family:Arial;background:#0f1117;color:#e2e8f0;padding:32px;">
        <h2 style="color:#f6ad55;">📋 New Task Assigned</h2>
        <p><strong>{body.title}</strong></p>
        <p style="color:#a0aec0;">{body.description}</p>
        <p>Priority: <strong style="color:{'#fc8181' if body.priority=='urgent' else '#f6ad55'}">
        {body.priority.upper()}</strong></p>
        {"<p>Due: " + body.due_date + "</p>" if body.due_date else ""}
        <a href="{_app_url}" style="background:#3182ce;color:#fff;padding:12px 24px;border-radius:8px;
        text-decoration:none;font-weight:bold;">View Task</a>
        <p style="color:#4a5568;margin-top:20px;font-size:0.8rem;">MyPy Tutor · Teamsamikoko Global Academy</p>
        </div>"""
        _send_email_async(body.assigned_to, f"Task assigned: {body.title}", html,
                          f"New task: {body.title}\n{body.description}\nPriority: {body.priority}")
    except Exception as e:
        logger.warning("Task email failed: %s", e)
    return {"ok": True, "task_id": t.id}


@app.post("/admin/tasks/{task_id}/status")
async def admin_update_task(task_id: str, status: str, request: Request) -> dict:
    _require_admin(request)
    if status not in ("open", "in_progress", "done"):
        raise HTTPException(status_code=400, detail="Invalid status.")
    ok = update_task_status(task_id, status)
    if not ok:
        raise HTTPException(status_code=404, detail="Task not found.")
    return {"ok": True}


@app.get("/admin/feedback")
async def admin_feedback_data(request: Request) -> dict:
    _require_admin(request)
    from app.feedback import _ratings, _surveys, get_summary as _gs
    return {
        "summary": _gs().model_dump(),
        "recent_ratings": [
            {"learner_id": r.learner_id, "rating": r.rating,
             "topic": r.topic, "comment": r.comment, "intent": r.intent}
            for r in list(reversed(_ratings))[:20]
        ],
        "recent_surveys": [
            {"learner_id": s.learner_id, "overall": s.overall,
             "clarity": s.clarity, "helpfulness": s.helpfulness,
             "suggestion": s.suggestion, "would_recommend": s.would_recommend}
            for s in list(reversed(_surveys))[:20]
        ],
    }


@app.get("/admin/activity")
async def admin_activity(request: Request) -> dict:
    _require_admin(request)
    try:
        activity = get_activity_log(200)
    except Exception:
        from app.admin import _activity_log
        activity = list(reversed(_activity_log[-200:]))
    return {"activity": activity}


@app.post("/admin/announce")
async def admin_announce(request: Request) -> dict:
    _require_admin(request)
    body    = await request.json()
    target  = body.get("target", "all")
    subject = body.get("subject", "")
    message = body.get("message", "")
    if not subject or not message:
        raise HTTPException(status_code=400, detail="Subject and message required.")
    from app.admin import send_announcement
    sent = await send_announcement(target, subject, message)
    return {"ok": True, "sent_to": sent, "message": f"Announcement sent to {sent} users"}


@app.get("/admin/files")
async def admin_files_list(request: Request) -> dict:
    _require_admin(request)
    import os as _os2
    files = []
    for root, dirs, fnames in _os2.walk("."):
        dirs[:] = [d for d in dirs if d not in ['.venv', '__pycache__', '.git', '.hypothesis']]
        for f in fnames:
            path = _os2.path.join(root, f).replace("\\", "/").lstrip("./")
            if any(path.startswith(p) for p in ['app/', 'static/', 'requirements']):
                size = _os2.path.getsize(_os2.path.join(root, f))
                files.append({"path": path, "size": size})
    files.sort(key=lambda x: x["path"])
    return {"files": files, "total": len(files)}


@app.post("/admin/email/test")
async def admin_test_email(request: Request) -> dict:
    """
    Send a test email to verify SMTP configuration is working.
    POST body: { "to": "recipient@email.com" }
    """
    _require_admin(request)
    body = await request.json()
    to   = body.get("to", "").strip()
    if not to or "@" not in to:
        raise HTTPException(status_code=400, detail="Provide a valid 'to' email address.")

    # Show current SMTP config (values only, no secrets)
    email_user = _os.getenv("EMAIL_USER", "")
    email_pass = _os.getenv("EMAIL_PASS", "")
    email_host = _os.getenv("EMAIL_HOST", "smtp.gmail.com")
    email_port = _os.getenv("EMAIL_PORT", "587")

    config_status = {
        "EMAIL_HOST":  email_host,
        "EMAIL_PORT":  email_port,
        "EMAIL_USER":  email_user if email_user else "❌ NOT SET",
        "EMAIL_PASS":  "✅ set" if email_pass else "❌ NOT SET",
        "EMAIL_FROM":  _os.getenv("EMAIL_FROM", "not set"),
        "APP_URL":     _os.getenv("APP_URL", "not set"),
    }

    if not email_user or not email_pass:
        return {
            "ok": False,
            "sent": False,
            "config": config_status,
            "error": "EMAIL_USER or EMAIL_PASS not set in Render environment variables.",
        }

    from app.email_auth import _send_email
    import threading, queue

    result_q: queue.Queue = queue.Queue()

    def _try_send():
        html = f"""<div style="font-family:Arial;background:#0f1117;color:#e2e8f0;padding:32px;max-width:500px;border-radius:12px;">
        <h2 style="color:#63b3ed;">🐍 MyPy Tutor — Email Test</h2>
        <p>✅ This is a test email from your MyPy Tutor admin panel.</p>
        <p style="color:#68d391;font-weight:700;">Email delivery is working correctly!</p>
        <hr style="border:none;border-top:1px solid #2d3748;margin:16px 0"/>
        <p style="font-size:.78rem;color:#4a5568;">Sent from: {email_user}<br/>
        Host: {email_host}:{email_port}</p>
        </div>"""
        text = f"MyPy Tutor email test.\nIf you see this, email delivery is working.\nFrom: {email_user}"
        ok = _send_email(to, "MyPy Tutor — Email Test ✅", html, text)
        result_q.put(ok)

    t = threading.Thread(target=_try_send, daemon=True)
    t.start()
    t.join(timeout=25)   # wait up to 25s for the result

    if not result_q.empty():
        ok = result_q.get()
        if ok:
            return {"ok": True, "sent": True, "to": to, "config": config_status}
        else:
            return {
                "ok": False, "sent": False, "to": to, "config": config_status,
                "error": "SMTP send failed — check Render logs for the exact error. "
                         "Common causes: wrong Gmail App Password, 2FA not enabled on Gmail, "
                         "or EMAIL_USER is not a Gmail address.",
            }
    return {
        "ok": False, "sent": False, "to": to, "config": config_status,
        "error": "Email send timed out after 25 seconds. Check your SMTP settings.",
    }


# ---------------------------------------------------------------------------
# PASSWORD RESET routes
# ---------------------------------------------------------------------------

@app.post("/auth/forgot-password")
async def forgot_password(body: PasswordResetRequest) -> dict:
    """Send a password-reset email. Always returns 200 to prevent enumeration."""
    ok, message = request_password_reset(body.email)
    return {"ok": True, "message": message}


@app.post("/auth/reset-password")
async def reset_password_route(body: PasswordResetConfirm) -> dict:
    """Validate token and set new password."""
    ok, message = confirm_password_reset(body.token, body.new_password)
    if not ok:
        raise HTTPException(status_code=400, detail=message)
    return {"ok": True, "message": message}


# ---------------------------------------------------------------------------
# PROMPT HISTORY routes
# ---------------------------------------------------------------------------

@app.get("/history/{learner_id}")
async def prompt_history(learner_id: str, limit: int = 20) -> dict:
    validate_learner_id(learner_id)
    limit   = max(1, min(limit, 50))
    history = get_prompt_history(learner_id, limit)
    return {"learner_id": learner_id, "history": history, "count": len(history)}


@app.get("/history/{learner_id}/quiz")
async def quiz_history(learner_id: str, limit: int = 50) -> dict:
    validate_learner_id(learner_id)
    attempts = get_quiz_attempts(learner_id, min(limit, 100))
    total    = len(attempts)
    correct  = sum(1 for a in attempts if a.get("correct"))
    return {
        "learner_id": learner_id,
        "attempts":   attempts,
        "total":      total,
        "correct":    correct,
        "accuracy":   round(correct / total * 100, 1) if total else 0.0,
    }


# ---------------------------------------------------------------------------
# ASSIGNMENTS routes
# ---------------------------------------------------------------------------

@app.post("/assignments/generate")
async def generate_assignment(learner_id: str, topic: str) -> dict:
    validate_learner_id(learner_id)
    validate_topic(topic)
    import secrets as _sec
    profile = get_profile(learner_id)

    system_prompt = build_system_prompt("exercise", topic=topic, level=profile.level)
    messages = [{"role": "user", "content": (
        f"Create a detailed coding assignment on '{topic}'. "
        f"Include: title, clear description, requirements (3-5 bullet points), "
        f"expected output, and evaluation criteria. Format it clearly."
    )}]
    try:
        content = get_completion(system_prompt, messages)
    except Exception as exc:
        logger.error("Assignment gen error: %s", exc)
        raise HTTPException(status_code=502, detail="AI service error. Please try again.")

    assignment_id = _sec.token_hex(8).upper()
    title = f"{topic} — Coding Assignment"
    create_assignment_db(assignment_id, learner_id, title, content)
    log_activity(learner_id, "assignment:generated", f"topic={topic}")
    return {"assignment_id": assignment_id, "learner_id": learner_id,
            "topic": topic, "title": title, "content": content}


@app.post("/assignments/{assignment_id}/submit")
async def submit_assignment(assignment_id: str, body: AssignmentSubmit) -> dict:
    validate_learner_id(body.learner_id)
    ok = submit_assignment_db(assignment_id, body.learner_id, body.submission)
    if not ok:
        raise HTTPException(status_code=404, detail="Assignment not found.")
    log_activity(body.learner_id, "assignment:submitted", f"id={assignment_id}")
    return {"ok": True, "message": "Assignment submitted successfully."}


@app.post("/assignments/{assignment_id}/review")
async def ai_review_assignment(assignment_id: str, learner_id: str) -> dict:
    validate_learner_id(learner_id)
    assignments = get_assignments_db(learner_id)
    assignment  = next((a for a in assignments if a["id"] == assignment_id), None)
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found.")
    if not assignment.get("submission"):
        raise HTTPException(status_code=400, detail="No submission to review yet.")

    system_prompt = build_system_prompt("debug", topic=assignment["title"])
    messages = [{"role": "user", "content": (
        f"Review this Python assignment submission and provide:\n"
        f"1. A score out of 100\n"
        f"2. Detailed feedback (strengths, weaknesses, corrections)\n"
        f"3. Specific improvement suggestions with code examples\n\n"
        f"Assignment: {assignment['description'][:500]}\n\n"
        f"Submission:\n{assignment['submission'][:3000]}\n\n"
        f"End your response with exactly: SCORE: <number>"
    )}]
    try:
        content = get_completion(system_prompt, messages)
    except Exception as exc:
        logger.error("Assignment review error: %s", exc)
        raise HTTPException(status_code=502, detail="AI service error. Please try again.")

    score_match = re.search(r"SCORE:\s*(\d+)", content)
    score       = int(score_match.group(1)) if score_match else 70
    score       = max(0, min(100, score))

    review_assignment_db(assignment_id, content, score)
    log_activity(learner_id, "assignment:reviewed", f"id={assignment_id} score={score}")
    return {"ok": True, "feedback": content, "score": score}


@app.get("/assignments/{learner_id}")
async def list_assignments(learner_id: str) -> dict:
    validate_learner_id(learner_id)
    assignments = get_assignments_db(learner_id)
    return {"learner_id": learner_id, "assignments": assignments, "total": len(assignments)}


# ---------------------------------------------------------------------------
# LESSON RESOURCES
# ---------------------------------------------------------------------------

_LESSON_RESOURCES: dict[str, list[dict]] = {
    "Python Intro & Get Started":    [{"type":"docs",    "label":"Python.org Official Docs",         "url":"https://docs.python.org/3/tutorial/"},
                                      {"type":"video",   "label":"Python in 100 Seconds (Fireship)", "url":"https://www.youtube.com/watch?v=x7X9w_GIm1s"}],
    "Python Syntax":                 [{"type":"docs",    "label":"W3Schools Python Syntax",           "url":"https://www.w3schools.com/python/python_syntax.asp"}],
    "Python Variables":              [{"type":"docs",    "label":"W3Schools Variables",               "url":"https://www.w3schools.com/python/python_variables.asp"},
                                      {"type":"article", "label":"Real Python — Variables",           "url":"https://realpython.com/python-variables/"}],
    "Python Data Types":             [{"type":"docs",    "label":"W3Schools Data Types",              "url":"https://www.w3schools.com/python/python_datatypes.asp"}],
    "Python Strings":                [{"type":"docs",    "label":"W3Schools Strings",                 "url":"https://www.w3schools.com/python/python_strings.asp"},
                                      {"type":"article", "label":"Real Python — Strings",             "url":"https://realpython.com/python-strings/"}],
    "Python Lists":                  [{"type":"docs",    "label":"W3Schools Lists",                   "url":"https://www.w3schools.com/python/python_lists.asp"}],
    "Python Dictionaries":           [{"type":"docs",    "label":"W3Schools Dictionaries",            "url":"https://www.w3schools.com/python/python_dictionaries.asp"}],
    "Python Functions":              [{"type":"docs",    "label":"W3Schools Functions",               "url":"https://www.w3schools.com/python/python_functions.asp"},
                                      {"type":"article", "label":"Real Python — Functions",           "url":"https://realpython.com/defining-your-own-python-function/"}],
    "Classes and Objects":           [{"type":"docs",    "label":"W3Schools OOP",                     "url":"https://www.w3schools.com/python/python_classes.asp"},
                                      {"type":"article", "label":"Real Python — OOP",                 "url":"https://realpython.com/python3-object-oriented-programming/"}],
    "Python Inheritance":            [{"type":"docs",    "label":"W3Schools Inheritance",             "url":"https://www.w3schools.com/python/python_inheritance.asp"}],
    "Python RegEx":                  [{"type":"docs",    "label":"W3Schools RegEx",                   "url":"https://www.w3schools.com/python/python_regex.asp"},
                                      {"type":"tool",    "label":"Regex101 — Live tester",            "url":"https://regex101.com/"}],
    "File Handling":                 [{"type":"docs",    "label":"W3Schools File Handling",           "url":"https://www.w3schools.com/python/python_file_handling.asp"}],
    "Python JSON":                   [{"type":"docs",    "label":"W3Schools JSON",                    "url":"https://www.w3schools.com/python/python_json.asp"}],
    "NumPy Intro & Getting Started": [{"type":"docs",    "label":"NumPy Official Docs",               "url":"https://numpy.org/doc/stable/"},
                                      {"type":"docs",    "label":"W3Schools NumPy",                   "url":"https://www.w3schools.com/python/numpy/default.asp"}],
    "Pandas Intro & Getting Started":[{"type":"docs",    "label":"Pandas Official Docs",              "url":"https://pandas.pydata.org/docs/"},
                                      {"type":"docs",    "label":"W3Schools Pandas",                  "url":"https://www.w3schools.com/python/pandas/default.asp"}],
    "DSA Intro":                     [{"type":"docs",    "label":"W3Schools DSA",                     "url":"https://www.w3schools.com/dsa/"},
                                      {"type":"article", "label":"Big-O Cheat Sheet",                 "url":"https://www.bigocheatsheet.com/"}],
}
_DEFAULT_RESOURCES = [
    {"type":"docs",  "label":"Python Official Documentation", "url":"https://docs.python.org/3/"},
    {"type":"docs",  "label":"W3Schools Python Tutorial",     "url":"https://www.w3schools.com/python/"},
    {"type":"tool",  "label":"Python Tutor — Visualiser",     "url":"https://pythontutor.com/"},
]


@app.get("/lessons/resources")
async def lesson_resources(topic: str = "") -> dict:
    resources = _LESSON_RESOURCES.get(topic, _DEFAULT_RESOURCES)
    return {"topic": topic, "resources": resources, "count": len(resources)}


# ---------------------------------------------------------------------------
# COUPON routes
# ---------------------------------------------------------------------------

@app.post("/coupons/validate")
async def validate_coupon(body: CouponValidate) -> dict:
    coupon = validate_coupon_db(body.code, body.plan)
    if not coupon:
        raise HTTPException(status_code=404, detail="Coupon is invalid, expired, or not applicable.")
    return {
        "valid":         True,
        "code":          coupon["code"],
        "discount_pct":  coupon["discount_pct"],
        "discount_flat": coupon["discount_flat"],
        "plan":          coupon["plan"],
        "uses_left":     coupon["max_uses"] - coupon["uses"],
    }


@app.post("/coupons/apply")
async def apply_coupon(body: CouponValidate) -> dict:
    if not body.learner_id or not body.email:
        raise HTTPException(status_code=400, detail="learner_id and email required.")
    coupon = validate_coupon_db(body.code, body.plan)
    if not coupon:
        raise HTTPException(status_code=404, detail="Coupon is invalid or exhausted.")
    savings = coupon["discount_flat"] if coupon["discount_flat"] else 0.0
    use_coupon_db(body.code, body.learner_id, body.email, savings)
    log_activity(body.learner_id, "coupon:applied", f"code={body.code}")
    return {"ok": True, "discount_pct": coupon["discount_pct"],
            "discount_flat": coupon["discount_flat"], "message": "Coupon applied!"}


# ---------------------------------------------------------------------------
# REFERRAL routes
# ---------------------------------------------------------------------------

@app.get("/referral/{learner_id}")
async def get_my_referral(learner_id: str) -> dict:
    validate_learner_id(learner_id)
    existing = get_learner_referral_code(learner_id)
    if existing:
        uses = get_referral_uses(existing["code"])
        return {"code": existing["code"], "uses": existing["uses"],
                "max_uses": existing["max_uses"], "recent_uses": uses[:10]}
    import secrets as _sec
    code    = _sec.token_hex(4).upper()
    profile = get_profile(learner_id)
    email   = profile.email or learner_id
    create_referral_code(code, learner_id, email)
    return {"code": code, "uses": 0, "max_uses": 50, "recent_uses": []}


@app.post("/referral/use")
async def use_referral(body: ReferralUse) -> dict:
    ref = get_referral_code(body.code)
    if not ref or ref["uses"] >= ref["max_uses"]:
        raise HTTPException(status_code=404, detail="Referral code is invalid or exhausted.")
    ok = use_referral_code(body.code, body.email, body.learner_id, discount_pct=20)
    if not ok:
        raise HTTPException(status_code=400, detail="Could not apply referral code.")
    log_activity(body.learner_id, "referral:used", f"code={body.code}")
    return {"ok": True, "discount_pct": 20,
            "message": "Referral applied! You get 20% off your first subscription."}


# ---------------------------------------------------------------------------
# INVOICE routes
# ---------------------------------------------------------------------------

@app.get("/invoice/{invoice_id}", response_class=HTMLResponse)
async def get_invoice(invoice_id: str) -> HTMLResponse:
    inv = get_invoice_db(invoice_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found.")
    return HTMLResponse(content=_render_invoice(inv))


@app.get("/invoices/{learner_id}")
async def list_invoices(learner_id: str) -> dict:
    validate_learner_id(learner_id)
    invoices = get_invoices_by_learner(learner_id)
    return {"learner_id": learner_id, "invoices": invoices, "total": len(invoices)}


def _render_invoice(inv: dict) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <title>Invoice #{inv['id']} — MyPy Tutor</title>
  <style>
    @media print{{.no-print{{display:none}}body{{padding:0}}}}
    *{{box-sizing:border-box;margin:0;padding:0}}
    body{{font-family:Arial,Helvetica,sans-serif;background:#f9fafb;color:#1a202c;padding:40px 20px}}
    .invoice{{max-width:700px;margin:0 auto;background:#fff;border-radius:12px;
              box-shadow:0 4px 20px rgba(0,0,0,.08);overflow:hidden}}
    .hdr{{background:linear-gradient(135deg,#0d2b6e,#1a3f9a);color:#fff;
          padding:32px 40px;display:flex;justify-content:space-between;align-items:flex-start}}
    .hdr h1{{font-size:1.5rem;margin-bottom:4px}}
    .hdr p{{font-size:0.75rem;opacity:.75;margin-top:3px}}
    .badge{{background:rgba(255,255,255,.2);padding:6px 14px;border-radius:20px;
            font-size:0.78rem;font-weight:700;letter-spacing:.06em}}
    .body{{padding:36px 40px}}
    .meta{{display:flex;justify-content:space-between;margin-bottom:24px}}
    .status{{display:inline-block;background:#c6f6d5;color:#276749;padding:3px 12px;
             border-radius:20px;font-size:0.78rem;font-weight:700}}
    hr{{border:none;border-top:1px solid #e2e8f0;margin:20px 0}}
    .line{{display:flex;justify-content:space-between;font-size:0.9rem;padding:8px 0}}
    .total{{display:flex;justify-content:space-between;font-size:1.1rem;
            font-weight:700;color:#0d2b6e}}
    .ftr{{background:#f7fafc;border-top:1px solid #e2e8f0;padding:20px 40px;
          text-align:center;font-size:0.75rem;color:#718096}}
    .pbtn{{display:block;margin:20px auto;padding:10px 28px;background:#0d2b6e;
           color:#fff;border:none;border-radius:8px;font-size:0.9rem;cursor:pointer}}
  </style>
</head>
<body>
<div class="invoice">
  <div class="hdr">
    <div>
      <div style="font-size:1.8rem;margin-bottom:6px">🐍</div>
      <h1>MyPy Tutor</h1>
      <p>Powered by TeamTega Technologies Limited</p>
      <p>Certified by Teamsamikoko Global Academy · Reg No: 3508656</p>
    </div>
    <div style="text-align:right">
      <div class="badge">INVOICE</div>
      <p style="margin-top:10px;font-size:0.85rem;opacity:.9">#{inv['id']}</p>
      <p style="font-size:0.75rem;opacity:.75">{inv.get('issued_at_fmt','')}</p>
    </div>
  </div>
  <div class="body">
    <div class="meta">
      <div>
        <p style="font-size:.72rem;color:#718096;text-transform:uppercase;
                  letter-spacing:.08em;margin-bottom:6px">Bill To</p>
        <p style="font-weight:700;font-size:.95rem">{inv['name']}</p>
        <p style="color:#718096;font-size:.85rem">{inv['email']}</p>
      </div>
      <div style="text-align:right">
        <span class="status">✅ PAID</span>
        <p style="margin-top:8px;font-size:.78rem;color:#718096">
          Payment ID: {inv['payment_id']}</p>
      </div>
    </div>
    <hr/>
    <div style="font-size:.75rem;color:#718096;text-transform:uppercase;
                letter-spacing:.06em;padding-bottom:8px;border-bottom:1px solid #e2e8f0;
                margin-bottom:12px;display:flex;justify-content:space-between">
      <span>Description</span><span>Amount</span>
    </div>
    <div class="line">
      <span>{inv['plan']}</span>
      <span style="font-weight:700">₦{inv['amount']:,.0f}</span>
    </div>
    <hr/>
    <div class="total">
      <span>Total Paid</span>
      <span>₦{inv['amount']:,.0f} {inv['currency']}</span>
    </div>
    <p style="margin-top:24px;font-size:.8rem;color:#718096;line-height:1.6">
      Thank you for investing in your Python education. This invoice is proof of
      payment for the MyPy Tutor subscription/certification listed above.
    </p>
  </div>
  <div class="ftr">
    <p>MyPy Tutor · mypytutor.onrender.com</p>
    <p style="margin-top:4px">TeamTega Technologies Limited · Teamsamikoko Global Academy</p>
    <p style="margin-top:4px;font-style:italic">"Learn Smarter. Code Better. Build the Future."</p>
  </div>
</div>
<button class="pbtn no-print" onclick="window.print()">🖨️ Print / Save as PDF</button>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Admin routes for new features
# ---------------------------------------------------------------------------

@app.get("/admin/assignments")
async def admin_all_assignments(request: Request) -> dict:
    _require_admin(request)
    assignments = get_all_assignments_db()
    return {
        "assignments": assignments,
        "total":       len(assignments),
        "pending":     sum(1 for a in assignments if a["status"] == "pending"),
        "submitted":   sum(1 for a in assignments if a["status"] == "submitted"),
        "reviewed":    sum(1 for a in assignments if a["status"] == "reviewed"),
    }


@app.post("/admin/assignments/{assignment_id}/review")
async def admin_review_assignment(assignment_id: str,
                                   body: AssignmentReview,
                                   request: Request) -> dict:
    _require_admin(request)
    ok = review_assignment_db(assignment_id, body.feedback, body.score)
    if not ok:
        raise HTTPException(status_code=404, detail="Assignment not found.")
    return {"ok": True, "message": f"Assignment reviewed. Score: {body.score}/100"}


@app.get("/admin/coupons")
async def admin_coupons(request: Request) -> dict:
    _require_admin(request)
    return {"coupons": get_all_coupons_db()}


@app.post("/admin/coupons/create")
async def admin_create_coupon(body: CouponCreate, request: Request) -> dict:
    _require_admin(request)
    import time as _t
    expires_at = _t.time() + body.expires_days * 86400 if body.expires_days else 0
    create_coupon_db(body.code, body.discount_pct, body.discount_flat,
                     body.plan, body.max_uses, expires_at)
    return {"ok": True, "code": body.code.upper(),
            "discount_pct": body.discount_pct,
            "message": f"Coupon {body.code.upper()} created."}


@app.get("/admin/invoices")
async def admin_invoices(request: Request) -> dict:
    _require_admin(request)
    invoices      = get_all_invoices_db()
    total_revenue = sum(i["amount"] for i in invoices)
    return {"invoices": invoices, "total": len(invoices), "total_revenue": total_revenue}


@app.get("/admin/history/{learner_id}")
async def admin_learner_history(learner_id: str, request: Request) -> dict:
    _require_admin(request)
    validate_learner_id(learner_id)
    history  = get_prompt_history(learner_id, 50)
    attempts = get_quiz_attempts(learner_id, 50)
    # Also pull from Supabase if available
    sb_msgs = sb_load_messages(f"local_{learner_id}", limit=50) if sb_enabled() else []
    return {"learner_id": learner_id,
            "prompt_history": history,
            "supabase_messages": sb_msgs,
            "quiz_attempts": attempts}


# ---------------------------------------------------------------------------
# SUPABASE — Conversation & history routes
# ---------------------------------------------------------------------------

@app.get("/conversations/{learner_id}")
async def list_conversations(learner_id: str) -> dict:
    """
    Return all conversation sessions for a learner.
    Pulls from Supabase when configured; falls back to SQLite prompt_history.
    """
    validate_learner_id(learner_id)
    if sb_enabled():
        convs = sb_load_all_conversations(learner_id)
        return {"learner_id": learner_id, "conversations": convs,
                "source": "supabase", "total": len(convs)}
    # Fallback: group SQLite history by day
    history = get_prompt_history(learner_id, 50)
    return {"learner_id": learner_id,
            "conversations": [{"id": f"local_{learner_id}", "messages": history}],
            "source": "sqlite", "total": len(history)}


@app.get("/conversations/{learner_id}/{conversation_id}")
async def get_conversation(learner_id: str, conversation_id: str,
                            limit: int = 50) -> dict:
    """
    Load all messages from a specific conversation.
    Sir. Tega uses this to resume context on re-login.
    """
    validate_learner_id(learner_id)
    if sb_enabled():
        messages = sb_load_messages(conversation_id, limit=min(limit, 100))
        return {"conversation_id": conversation_id,
                "learner_id": learner_id,
                "messages": messages,
                "count": len(messages),
                "source": "supabase"}
    # Fallback to SQLite
    history = get_prompt_history(learner_id, limit=min(limit, 50))
    return {"conversation_id": conversation_id,
            "learner_id": learner_id,
            "messages": history,
            "count": len(history),
            "source": "sqlite"}


@app.post("/conversations/{learner_id}/new")
async def new_conversation(learner_id: str) -> dict:
    """Start a fresh conversation (clears context window for Sir. Tega)."""
    validate_learner_id(learner_id)
    if sb_enabled():
        import secrets as _sec
        conv_id = _sec.token_hex(16)
        from app.supabase_client import get_supabase
        sb = get_supabase()
        if sb:
            try:
                sb.table("conversations").insert({
                    "id": conv_id, "learner_id": learner_id,
                    "title": "New Conversation"
                }).execute()
            except Exception as exc:
                logger.warning("New conversation insert failed: %s", exc)
                conv_id = f"local_{_sec.token_hex(8)}"
        return {"conversation_id": conv_id, "learner_id": learner_id}
    import secrets as _sec
    return {"conversation_id": f"local_{_sec.token_hex(8)}", "learner_id": learner_id}


# ---------------------------------------------------------------------------
# SUPABASE — Status & health check
# ---------------------------------------------------------------------------

@app.get("/supabase/status")
async def supabase_status() -> dict:
    """Check whether Supabase is configured and reachable."""
    if not sb_enabled():
        return {"enabled": False,
                "message": "Supabase not configured. Add SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in Render env vars."}
    try:
        from app.supabase_client import get_supabase
        sb = get_supabase()
        # Simple ping — list 1 row from profiles
        sb.table("profiles").select("id").limit(1).execute()
        return {"enabled": True, "status": "connected",
                "url": _os.getenv("SUPABASE_URL", "")[:40] + "…"}
    except Exception as exc:
        return {"enabled": True, "status": "error", "detail": str(exc)[:120]}


# ---------------------------------------------------------------------------
# STARTUP — Supabase data recovery on Render restart
# ---------------------------------------------------------------------------

def _recover_from_supabase() -> None:
    """
    On startup: if SQLite is empty (Render ephemeral restart), pull both
    learner progress AND email accounts from Supabase so the app has full
    data immediately — users can log in and resume learning without delay.

    Email account recovery is handled inside _load_confirmed_from_db()
    (called just before this). This function handles learner progress only.
    """
    if not sb_enabled():
        return
    from app.supabase_client import get_supabase
    from app.db import get_all_learners, save_profile_db
    import json
    try:
        sb = get_supabase()
        if get_all_learners():
            logger.info("SQLite learner_profiles intact — skipping Supabase progress recovery")
            return
        logger.info("Recovering learner progress from Supabase…")
        res = sb.table("learner_progress").select("*").limit(500).execute()
        recovered = 0
        for row in (res.data or []):
            lid = row.get("learner_id", "")
            if not lid:
                continue
            save_profile_db(lid, {
                "tier":               row.get("tier", "free"),
                "level":              row.get("level", "beginner"),
                "xp":                 row.get("xp", 0),
                "badges":             json.loads(row.get("badges") or "[]"),
                "topics_seen":        json.loads(row.get("topics_seen") or "[]"),
                "topic_progress":     {},
                "current_course":     row.get("current_course"),
                "current_course_step":row.get("current_course_step", 0),
                "completed_projects": json.loads(row.get("completed_projects") or "[]"),
                "daily_prompts_used": 0,
                "last_prompt_date":   "",
            })
            recovered += 1
        logger.info("Recovered %d learner progress records from Supabase", recovered)
    except Exception as exc:
        logger.warning("Supabase progress recovery failed (non-fatal): %s", exc)


# Run recovery at startup (after DB is initialised)
_recover_from_supabase()


# ---------------------------------------------------------------------------
# Static files — mounted LAST so API routes take priority
# ---------------------------------------------------------------------------

app.mount("/", StaticFiles(directory="static", html=True), name="static")
