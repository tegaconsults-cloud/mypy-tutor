"""
FastAPI application � MyPy Tutor (secured).
Security layer: rate limiting, input validation, security headers, sanitised errors.
"""

import asyncio
import datetime
import hashlib
import hmac
import json
import logging
import re
import secrets
import threading
import time
import os as _os

import psycopg2
import psycopg2.extras as _pge

from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi import Depends
from fastapi.security import HTTPBearer as _HTTPBearer
from pydantic import BaseModel as _BM, Field as _Field

# Optional bearer dependency � declared here (module top) so it is available
# to ALL route handlers regardless of definition order.
# Routes use Depends(_bearer_optional) to read the token when present without
# requiring authentication (auto_error=False means missing token ? None, not 401).
_bearer_optional = _HTTPBearer(auto_error=False)

from app.classifier import classify_intent
from app.formatter import format_response
from app.llm_client import get_completion
from app.models import (
    ChatRequest, ChatResponse,
    QuizRequest, QuizResponse,
    QuizAnswerRequest, QuizAnswerResponse,
    ProgressResponse,
    GoogleAuthRequest, AuthResponse,
    EmailSignInRequest,
    MessageFeedback, SurveyFeedback, FeedbackSummary,
    PasswordResetRequest, PasswordResetConfirm,
    AssignmentSubmit, AssignmentReview,
    CouponValidate, CouponCreate, ReferralUse,
    AccessCodeGenerate, EmailSignUpWithCode,
    UserProfileUpdate,
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
    invite_team_member, create_task, update_task_status,
    log_certificate, get_certificates, log_activity, get_announcements,
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
    create_access_code, validate_access_code, redeem_access_code,
    # user profiles
    update_user_profile_db, get_user_profile_db,
    # referral balance
    get_referral_bonus_balance,
    # referral withdrawals
    create_withdrawal_request, get_withdrawals_for_learner,
    # course purchases
    record_course_purchase, has_course_purchase, get_learner_courses,
    get_course_purchases_for_learner,
)
from app.supabase_client import (
    sb_upsert_profile, sb_get_or_create_conversation,
    sb_save_message, sb_load_messages, sb_load_all_conversations,
    sb_save_certificate, sb_save_payment, sb_update_tier, sb_enabled,
    sb_load_all_email_accounts,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# WAT greeting helper — called on every sign-in / sign-up to personalise
# the response with the user's first name and Nigerian time of day.
# WAT = UTC+1. Nigeria does not observe DST so this is always UTC+1.
# ---------------------------------------------------------------------------

def _wat_greeting(name: str, is_new: bool = False) -> str:
    """Return a personalised WAT-aware greeting string.

    Examples:
      "Good morning, Chidi! ☀️ Ready to learn some Python today?"
      "Good evening, Amara! 🌙 Welcome back to MyPy Tutor."
      "Welcome, Daniel! 🎉 Sir. Tega is excited to start your Python journey!"
    """
    import datetime as _dtt
    first = (name.split()[0] if name else "Learner").strip()

    wat_now = _dtt.datetime.utcnow() + _dtt.timedelta(hours=1)  # WAT = UTC+1
    hour    = wat_now.hour

    if hour < 5:
        time_str, emoji = "Good night",    "🌙"
    elif hour < 12:
        time_str, emoji = "Good morning",  "☀️"
    elif hour < 17:
        time_str, emoji = "Good afternoon","👋"
    elif hour < 21:
        time_str, emoji = "Good evening",  "🌆"
    else:
        time_str, emoji = "Good night",    "🌙"

    if is_new:
        return (
            f"Welcome, {first}! 🎉 Sir. Tega is excited to start your Python "
            f"journey with you. Let's dive in!"
        )
    return f"{time_str}, {first}! {emoji} Welcome back to MyPy Tutor."

# ---------------------------------------------------------------------------
# Sentry error tracking � initialised early so all errors are captured.
# Set SENTRY_DSN in Render dashboard ? Environment to enable.
# Free tier: 5,000 errors/month. No-op when SENTRY_DSN is unset.
# ---------------------------------------------------------------------------
_sentry_dsn = _os.getenv("SENTRY_DSN", "")
if _sentry_dsn:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration
        sentry_sdk.init(
            dsn=_sentry_dsn,
            integrations=[
                StarletteIntegration(transaction_style="endpoint"),
                FastApiIntegration(transaction_style="endpoint"),
            ],
            # Capture 10% of transactions for performance monitoring
            # (free tier has limits � keep this low)
            traces_sample_rate=0.1,
            # Don't send PII (emails, IPs) to Sentry
            send_default_pii=False,
            # Release tag helps correlate errors to deploys
            release=_os.getenv("RENDER_GIT_COMMIT", "unknown"),
            environment=_os.getenv("RENDER_SERVICE_NAME", "development"),
        )
        logger.info("Sentry initialised (dsn configured)")
    except ImportError:
        logger.warning("sentry-sdk not installed � run: pip install sentry-sdk[fastapi]")
    except Exception as _sentry_exc:
        logger.warning("Sentry init failed (non-fatal): %s", _sentry_exc)

# ---------------------------------------------------------------------------
# App initialisation
# ---------------------------------------------------------------------------

try:
    import app.llm_client  # noqa: F401 � validates GROQ_API_KEY at startup
except ValueError as exc:
    logger.error("Startup error: %s", exc)
    raise

from app.email_auth import _load_confirmed_from_db
try:
    init_db()
    _load_confirmed_from_db()
    logger.info("Database ready")
except Exception as _db_exc:
    logger.warning(
        "Database not available at startup: %s � "
        "set DATABASE_URL in Render ? mypy-tutor ? Environment. "
        "App will start but DB-dependent features will error until it is set.",
        _db_exc
    )
# Purge expired/used password reset tokens so the table doesn't grow unbounded
try:
    from app.db import purge_expired_reset_tokens
    purge_expired_reset_tokens()
except Exception:
    pass

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

_RENDER_URL   = _os.getenv("RENDER_EXTERNAL_URL", "")
_FRONTEND_URL = _os.getenv("FRONTEND_URL", "")   # Vercel frontend URL once deployed
_allowed_origins = list(filter(None, [
    _RENDER_URL,
    _FRONTEND_URL,
    "https://mypytutor.com.ng",
    "https://www.mypytutor.com.ng",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
])) or ["*"]

app.add_middleware(SecurityMiddleware)

# GZip all responses =1KB � reduces bandwidth ~70% on Render's metered egress
from starlette.middleware.gzip import GZipMiddleware
app.add_middleware(GZipMiddleware, minimum_size=1024)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_origin_regex=r"https://(.*\.)?(onrender\.com|vercel\.app|mypytutor\.com\.ng)",
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With", "Accept"],
    expose_headers=["Content-Type"],
    allow_credentials=False,
    max_age=86400,
)

# ---------------------------------------------------------------------------
# /chat
# ---------------------------------------------------------------------------

@app.post("/chat")
async def chat(request: ChatRequest, req: Request,
               background_tasks: BackgroundTasks,
               user=Depends(get_current_user)) -> JSONResponse:
    validate_chat_request(request.message, request.history, request.level, request.learner_id)

    # When authenticated, enforce learner_id matches token so XP/activity
    # is never credited to a different user's profile.
    # Anonymous users (no token) pass freely � they use the free-tier quota.
    if user is not None and user.learner_id != request.learner_id:
        raise HTTPException(
            status_code=403,
            detail="learner_id in request does not match your session."
        )

    profile = get_profile(request.learner_id)
    if profile.tier == "free":
        ip = _get_ip(req)
        allowed, used = check_free_prompt_limit(request.learner_id, ip)
        if not allowed:
            from app.security import FREE_DAILY_LIMIT
            return JSONResponse(
                status_code=402,
                content={
                    "error": "free_limit_reached",
                    "message": f"You've used your {FREE_DAILY_LIMIT} free daily prompts. Upgrade to Premium to continue learning!",
                    "used": used,
                    "limit": FREE_DAILY_LIMIT,
                },
            )
        increment_free_prompt_count(request.learner_id, ip)

    intent = classify_intent(request.message)

    from app.formatter import _detect_topic
    topic  = _detect_topic(request.message)
    gaps   = get_knowledge_gaps(request.learner_id)
    is_gap = topic in gaps if topic else False

    system_prompt = build_system_prompt(intent, topic=topic, level=request.level, is_gap_topic=is_gap)

    # -- Resolve conversation_id ------------------------------------------
    # Use client-provided conv_id if present; otherwise fall back to a
    # local synthetic ID. Do NOT call sb_get_or_create_conversation here �
    # it makes a synchronous network call to Supabase which blocks the
    # event loop and adds 200-400ms latency to every message.
    conv_id = request.conversation_id or f"local_{request.learner_id}"

    # -- Build message list -----------------------------------------------
    # If client sends no history AND Supabase is up AND we have a real conv_id
    # (not the synthetic local_ one), load last 6 turns so Sir. Tega has context.
    history_messages = [{"role": m.role, "content": m.content} for m in request.history]
    if not history_messages and sb_enabled() and request.conversation_id and not request.conversation_id.startswith("local_"):
        try:
            # Run in thread executor � sb_load_messages is synchronous (httpx/supabase-py)
            # Running it directly would block the uvicorn event loop.
            loop = asyncio.get_running_loop()
            sb_history = await loop.run_in_executor(
                None, lambda: sb_load_messages(request.conversation_id, limit=6)
            )
            history_messages = [{"role": m["role"], "content": m["content"]} for m in sb_history]
        except Exception:
            pass  # non-fatal � continue without history
    history_messages.append({"role": "user", "content": request.message})

    # -- LLM call with context-window overflow recovery -------------------
    # If Groq returns a context_length_exceeded / 413 error, trim the oldest
    # turns from history by half and retry ONCE with the shortened context.
    # If the retry also fails, return a structured new_conversation signal so
    # the frontend can open a fresh chat instead of showing a generic 502.
    def _is_context_overflow(exc: Exception) -> bool:
        msg = str(exc).lower()
        return any(k in msg for k in (
            "context_length_exceeded", "context length", "413",
            "max_tokens", "too long", "token limit", "reduce"
        ))

    content = None
    last_exc: Exception | None = None
    for _attempt in range(2):
        try:
            msgs_to_send = history_messages if _attempt == 0 else history_messages[-4:]
            content = get_completion(system_prompt, msgs_to_send, intent=intent)
            break
        except Exception as exc:
            last_exc = exc
            exc_type = str(type(exc).__name__).lower()
            exc_msg  = str(exc).lower()

            if _is_context_overflow(exc) and _attempt == 0:
                # Context too long — trim to last 4 messages and retry
                logger.info(
                    "Context overflow for %s — trimming history from %d to 4 msgs and retrying",
                    request.learner_id, len(history_messages)
                )
                continue

            if any(k in exc_type for k in ("ratelimit", "timeout", "serviceunavailable")):
                logger.warning("LLM unavailable: %s", exc)
                raise HTTPException(status_code=503, detail="Sir. Tega is momentarily busy. Please retry.")

            # Any other error after both attempts
            break

    if content is None:
        # If it was a context overflow even after trimming, tell frontend to open a new chat
        if last_exc and _is_context_overflow(last_exc):
            new_conv_id = f"local_{request.learner_id}_{secrets.token_hex(4)}"
            logger.info("Context overflow unrecoverable for %s — signalling new_conversation", request.learner_id)
            return JSONResponse(
                status_code=200,
                content={
                    "new_conversation": True,
                    "conversation_id":  new_conv_id,
                    "content": (
                        "📄 **This conversation has reached its context limit.**\n\n"
                        "Sir. Tega has automatically opened a **new chat** for you so we can keep going. "
                        "Your progress and XP are saved. Just continue asking your questions here!"
                    ),
                    "intent": intent,
                    "topic": topic,
                    "level": request.level,
                    "xp_gained": 0,
                    "badge": None,
                    "ask_survey": False,
                }
            )
        logger.error("LLM error after retries: %s", last_exc)
        raise HTTPException(status_code=502, detail="Sir. Tega encountered an issue. Please try again.")

    response_dict  = format_response(content, intent)
    detected_topic = response_dict.get("topic") or topic
    xp, badge      = record_lesson(request.learner_id, detected_topic or "", intent)
    profile        = get_profile(request.learner_id)

    log_activity(request.learner_id, f"chat:{intent}",
                 f"topic={detected_topic or '�'} | msg={request.message[:80]}")

    # -- Persist: SQLite (sync, fast local) --------------------------------
    save_prompt_history(request.learner_id, "user",      request.message, intent, detected_topic or "")
    save_prompt_history(request.learner_id, "assistant", content,         intent, detected_topic or "")

    # -- Supabase writes are background tasks � never block the response ----
    background_tasks.add_task(
        sb_save_message, conv_id, request.learner_id, "user",
        request.message, intent, detected_topic or ""
    )
    background_tasks.add_task(
        sb_save_message, conv_id, request.learner_id, "assistant",
        content, intent, detected_topic or ""
    )

    ask_survey = increment_interaction(request.learner_id)

    return JSONResponse(content={
        "intent":          response_dict["intent"],
        "content":         response_dict["content"],
        "topic":           response_dict["topic"],
        "level":           profile.level,
        "xp_gained":       xp,
        "badge":           badge,
        "ask_survey":      ask_survey,
        "conversation_id": conv_id,
    })

# ---------------------------------------------------------------------------
# Lightweight in-process TTL cache
# Used for static/slow-changing read-only endpoints that are hit on every
# page load.  No external dependency — pure Python dict + timestamp.
# Cache entries expire after TTL_SECONDS; a background sweep is not needed
# because entries are lazily evicted on the next read.
# ---------------------------------------------------------------------------

_cache: dict[str, tuple[float, object]] = {}   # key -> (expires_at, value)
_CACHE_LOCK = threading.Lock()

def _cache_get(key: str):
    """Return cached value or None if missing / expired."""
    with _CACHE_LOCK:
        entry = _cache.get(key)
        if entry and time.monotonic() < entry[0]:
            return entry[1]
        _cache.pop(key, None)
        return None

def _cache_set(key: str, value, ttl: int = 300) -> None:
    """Store value with a TTL (seconds). Default 5 minutes."""
    with _CACHE_LOCK:
        _cache[key] = (time.monotonic() + ttl, value)

def _cache_clear(prefix: str = "") -> None:
    """Invalidate all keys that start with prefix (or all keys if prefix='')."""
    with _CACHE_LOCK:
        keys = [k for k in list(_cache) if k.startswith(prefix)]
        for k in keys:
            _cache.pop(k, None)


# ---------------------------------------------------------------------------
# /topics  /health
# ---------------------------------------------------------------------------

@app.get("/topics")
async def topics() -> dict:
    cached = _cache_get("topics")
    if cached is not None:
        return cached
    result = {"topics": get_topics()}
    _cache_set("topics", result, ttl=600)   # 10-minute TTL — topics never change at runtime
    return result


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/ping")
async def ping() -> dict:
    """
    Lightweight liveness endpoint for UptimeRobot monitoring.
    UptimeRobot setup:
      1. Sign up free at uptimerobot.com
      2. Add Monitor ? HTTP(s) ? URL: https://mypytutor.onrender.com/ping
      3. Check interval: 5 minutes (keeps Render free tier awake)
      4. Alert contacts: add your email / Telegram
    Returns 200 OK in <5ms � no DB or Supabase calls.
    """
    return {"ok": True}


@app.get("/favicon.ico", include_in_schema=False)
async def favicon() -> HTMLResponse:
    """Serve favicon.ico with no-cache headers to force browsers to pick up logo changes."""
    import os as _os2
    fav_path = _os2.path.join("static", "favicon.ico")
    if not _os2.path.exists(fav_path):
        raise HTTPException(status_code=404, detail="favicon not found")
    with open(fav_path, "rb") as f:
        data = f.read()
    from fastapi.responses import Response as _Resp
    return _Resp(
        content=data,
        media_type="image/x-icon",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma":        "no-cache",
            "Expires":       "0",
        },
    )


# ---------------------------------------------------------------------------
# Auth � Google OAuth
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
        frontend_url = _os.getenv("FRONTEND_URL", app_url)
        return RedirectResponse(url=f"{frontend_url}/?auth=error&msg=Google+Sign-In+not+configured")

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
    frontend_url  = _os.getenv("FRONTEND_URL", app_url)
    client_id     = _os.getenv("GOOGLE_CLIENT_ID", "")
    client_secret = _os.getenv("GOOGLE_CLIENT_SECRET", "")
    redirect_uri  = f"{app_url}/auth/google/callback"  # must match Google Console + Render URL

    if error or not code:
        msg = urllib.parse.quote(error or "Google sign-in was cancelled")
        return RedirectResponse(url=f"{frontend_url}/?auth=error&msg={msg}")

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
                return RedirectResponse(url=f"{frontend_url}/?auth=error&msg=Token+exchange+failed")

            tokens   = token_res.json()
            id_token = tokens.get("id_token", "")

        payload = verify_google_token(id_token)
        user    = get_or_create_user(payload)
        token   = create_session_token(user.learner_id)
        # Store email + name in the LearnerProfile so admin can see them
        lp = get_profile(user.learner_id)
        if not lp.email or not lp.display_name:
            lp.email        = user.email
            lp.display_name = user.name
            from app.progress import save_profile as _sp
            _sp(lp)
        # Mirror to Supabase � non-blocking (fire-and-forget)
        threading.Thread(
            target=sb_upsert_profile,
            args=(user.learner_id, user.email, user.name),
            daemon=False,
        ).start()

        import urllib.parse as _up
        is_new    = not bool(get_profile(user.learner_id).topics_seen)

        # Greeting email + automation row (fire-and-forget)
        def _google_redirect_emails(_lid, _em, _nm, _new):
            try:
                from app.services.email_service import send_signin_greeting_email
                from app.db import upsert_email_automation
                upsert_email_automation(_lid, _em, _nm)
                if _new:
                    from app.services.email_service import send_welcome_email
                    send_welcome_email(_nm, _em)
                send_signin_greeting_email(
                    name=_nm, email=_em,
                    greeting=_wat_greeting(_nm, _new), is_new_user=_new)
            except Exception:
                pass
        threading.Thread(
            target=_google_redirect_emails,
            args=(user.learner_id, user.email, user.name, is_new),
            daemon=False).start()

        user_data = _up.quote(json.dumps({
            "token":      token,
            "learner_id": user.learner_id,
            "name":       user.name,
            "email":      user.email,
            "picture":    user.picture,
            "greeting":   _wat_greeting(user.name, is_new),
            "is_new_user": is_new,
        }))
        return RedirectResponse(url=f"{frontend_url}/?auth=google_success&user={user_data}")

    except Exception as exc:
        logger.error("Google OAuth callback error: %s", exc)
        return RedirectResponse(url=f"{frontend_url}/?auth=error&msg=Google+sign-in+failed")


@app.post("/auth/google", response_model=AuthResponse)
async def auth_google(request: GoogleAuthRequest) -> AuthResponse:
    """One-Tap / GSI token submitted directly from client � uses strict signature verification."""
    payload  = await verify_google_token_strict(request.credential)
    user     = get_or_create_user(payload)
    is_new   = not bool(get_profile(user.learner_id).topics_seen)
    token    = create_session_token(user.learner_id)
    # Mirror to Supabase non-blocking
    threading.Thread(target=sb_upsert_profile,
                   args=(user.learner_id, user.email, user.name),
                   daemon=False).start()

    # Greeting email + automation row (fire-and-forget)
    def _google_onetap_emails(_lid, _email, _name, _new):
        try:
            from app.services.email_service import send_signin_greeting_email
            from app.db import upsert_email_automation
            upsert_email_automation(_lid, _email, _name)
            if _new:
                from app.services.email_service import send_welcome_email
                send_welcome_email(_name, _email)
            send_signin_greeting_email(
                name=_name, email=_email,
                greeting=_wat_greeting(_name, _new), is_new_user=_new)
        except Exception:
            pass
    threading.Thread(
        target=_google_onetap_emails,
        args=(user.learner_id, user.email, user.name, is_new),
        daemon=False).start()

    return AuthResponse(
        token=token, learner_id=user.learner_id,
        name=user.name, email=user.email, picture=user.picture,
        greeting=_wat_greeting(user.name, is_new), is_new_user=is_new,
    )

@app.get("/auth/me", response_model=AuthResponse)
async def auth_me(user=Depends(require_user)) -> AuthResponse:
    token = create_session_token(user.learner_id)
    # If picture is empty (user reconstructed after restart), load from DB
    picture = user.picture or ""
    if not picture:
        try:
            from app.db import get_db as _gdb
            with _gdb() as _conn:
                with _conn.cursor(cursor_factory=_pge.RealDictCursor) as _cur:
                    _cur.execute(
                        "SELECT photo_url FROM user_profiles WHERE learner_id=%s",
                        (user.learner_id,)
                    )
                    row = _cur.fetchone()
                if row and row["photo_url"]:
                    picture = row["photo_url"]
                    user.picture = picture
        except Exception:
            pass
    profile = get_user_profile_db(user.learner_id)
    picture = profile.get("photo_url", "") or picture
    return AuthResponse(
        token=token, learner_id=user.learner_id,
        name=user.name, email=user.email, picture=picture,
    )


# ---------------------------------------------------------------------------
# Auth � GitHub OAuth
# ---------------------------------------------------------------------------

@app.get("/auth/github/login")
async def auth_github_login() -> JSONResponse:
    """Redirect the user to GitHub's OAuth authorization page."""
    from fastapi.responses import RedirectResponse
    import urllib.parse, secrets as _sec

    client_id    = _os.getenv("GITHUB_CLIENT_ID", "")
    app_url      = _os.getenv("APP_URL", "https://mypytutor.onrender.com")
    redirect_uri = f"{app_url}/auth/github/callback"
    frontend_url = _os.getenv("FRONTEND_URL", app_url)

    if not client_id:
        return RedirectResponse(
            url=f"{frontend_url}/?auth=error&msg=GitHub+Sign-In+not+configured"
        )

    state  = _sec.token_hex(16)   # CSRF token
    params = urllib.parse.urlencode({
        "client_id":    client_id,
        "redirect_uri": redirect_uri,
        "scope":        "read:user user:email",
        "state":        state,
    })
    return RedirectResponse(
        url=f"https://github.com/login/oauth/authorize?{params}"
    )


@app.get("/auth/github/callback")
async def auth_github_callback(code: str = None, error: str = None,
                                state: str = None) -> JSONResponse:
    """Handle GitHub OAuth callback � exchange code for token, fetch profile, sign in."""
    from fastapi.responses import RedirectResponse
    import urllib.parse, json

    app_url       = _os.getenv("APP_URL", "https://mypytutor.onrender.com")
    frontend_url  = _os.getenv("FRONTEND_URL", app_url)
    client_id     = _os.getenv("GITHUB_CLIENT_ID", "")
    client_secret = _os.getenv("GITHUB_CLIENT_SECRET", "")
    redirect_uri  = f"{app_url}/auth/github/callback"

    if error or not code:
        msg = urllib.parse.quote(error or "GitHub sign-in was cancelled")
        return RedirectResponse(url=f"{frontend_url}/?auth=error&msg={msg}")

    if not client_id or not client_secret:
        return RedirectResponse(
            url=f"{frontend_url}/?auth=error&msg=GitHub+OAuth+not+configured"
        )

    try:
        import httpx as _httpx

        async with _httpx.AsyncClient(timeout=10) as hc:
            # 1. Exchange code for access token
            token_res = await hc.post(
                "https://github.com/login/oauth/access_token",
                data={
                    "client_id":     client_id,
                    "client_secret": client_secret,
                    "code":          code,
                    "redirect_uri":  redirect_uri,
                },
                headers={"Accept": "application/json"},
            )
            if token_res.status_code != 200:
                logger.error("GitHub token exchange failed: %s", token_res.text)
                return RedirectResponse(
                    url=f"{frontend_url}/?auth=error&msg=GitHub+token+exchange+failed"
                )
            access_token = token_res.json().get("access_token", "")
            if not access_token:
                return RedirectResponse(
                    url=f"{frontend_url}/?auth=error&msg=GitHub+access+token+missing"
                )

            # 2. Fetch GitHub user profile
            user_res = await hc.get(
                "https://api.github.com/user",
                headers={"Authorization": f"Bearer {access_token}",
                         "Accept": "application/vnd.github+json"},
            )
            if user_res.status_code != 200:
                return RedirectResponse(
                    url=f"{frontend_url}/?auth=error&msg=GitHub+profile+fetch+failed"
                )
            gh_user = user_res.json()

            # 3. Fetch primary email if not public
            email = gh_user.get("email") or ""
            if not email:
                email_res = await hc.get(
                    "https://api.github.com/user/emails",
                    headers={"Authorization": f"Bearer {access_token}",
                             "Accept": "application/vnd.github+json"},
                )
                if email_res.status_code == 200:
                    for e in email_res.json():
                        if e.get("primary") and e.get("verified"):
                            email = e.get("email", "")
                            break

        # 4. Build a stable learner_id from the GitHub numeric user id
        github_id  = str(gh_user.get("id", ""))
        learner_id = f"gh_{github_id}"
        name       = gh_user.get("name") or gh_user.get("login") or email.split("@")[0]
        picture    = gh_user.get("avatar_url") or ""

        # 5. Upsert UserAccount in memory
        from app.models import UserAccount
        from app.auth import _users, create_session_token as _cst
        if learner_id not in _users:
            _users[learner_id] = UserAccount(
                learner_id=learner_id,
                email=email,
                name=name,
                picture=picture,
                google_sub=github_id,   # repurposed field � stores GitHub id
            )
            logger.info("New GitHub user: %s (%s)", name, email)
        else:
            u = _users[learner_id]
            u.name    = name
            u.email   = email
            u.picture = picture

        # 6. Persist email/name/picture to learner profile + Supabase
        lp = get_profile(learner_id)
        changed = False
        if not lp.email and email:
            lp.email = email; changed = True
        if not lp.display_name and name:
            lp.display_name = name; changed = True
        if changed:
            from app.progress import save_profile as _sp
            _sp(lp)
        if picture:
            try:
                from app.db import get_db as _gdb
                with _gdb() as _conn:
                    with _conn.cursor() as _cur:
                        _cur.execute("""
                            INSERT INTO user_profiles (learner_id, display_name, photo_url)
                            VALUES (%s, %s, %s)
                            ON CONFLICT(learner_id) DO UPDATE SET
                              photo_url    = CASE WHEN EXCLUDED.photo_url <> '' THEN EXCLUDED.photo_url
                                                  ELSE user_profiles.photo_url END,
                              display_name = CASE WHEN EXCLUDED.display_name <> '' THEN EXCLUDED.display_name
                                                  ELSE user_profiles.display_name END
                        """, (learner_id, name or "", picture))
            except Exception:
                pass
        # Non-blocking Supabase mirror
        threading.Thread(target=sb_upsert_profile, args=(learner_id, email, name), daemon=False).start()

        # 7. Create session token and redirect to frontend
        token     = _cst(learner_id)
        is_new    = not bool(get_profile(learner_id).topics_seen)

        # Greeting email + automation row (fire-and-forget)
        def _github_emails(_lid, _em, _nm, _new):
            try:
                from app.services.email_service import send_signin_greeting_email
                from app.db import upsert_email_automation
                upsert_email_automation(_lid, _em, _nm)
                if _new:
                    from app.services.email_service import send_welcome_email
                    send_welcome_email(_nm, _em)
                send_signin_greeting_email(
                    name=_nm, email=_em,
                    greeting=_wat_greeting(_nm, _new), is_new_user=_new)
            except Exception:
                pass
        threading.Thread(
            target=_github_emails,
            args=(learner_id, email, name, is_new),
            daemon=False).start()

        user_data = urllib.parse.quote(json.dumps({
            "token":      token,
            "learner_id": learner_id,
            "name":       name,
            "email":      email,
            "picture":    picture,
            "greeting":   _wat_greeting(name, is_new),
            "is_new_user": is_new,
        }))
        return RedirectResponse(
            url=f"{frontend_url}/?auth=github_success&user={user_data}"
        )

    except Exception as exc:
        logger.error("GitHub OAuth callback error: %s", exc)
        return RedirectResponse(
            url=f"{frontend_url}/?auth=error&msg=GitHub+sign-in+failed"
        )


# ---------------------------------------------------------------------------
# Email auth routes
# ---------------------------------------------------------------------------

@app.post("/auth/validate-code")
async def validate_code_endpoint(request: Request) -> dict:
    """
    Validate an access or referral code before signup.
    Returns the tier, discount_pct, and a human-readable label so the
    frontend can show 'Beginner Bundle unlocked!' or '5% discount applied'.
    """
    body = await request.json()
    raw  = (body.get("code") or "").strip().upper()
    if not raw:
        return {"valid": False, "message": "Please enter a code."}

    # Check access codes first
    try:
        code_rec = validate_access_code(raw)
        if code_rec:
            tier_labels = {
                "tier1": "Beginner Bundle",
                "tier2": "Intermediate Bundle",
                "tier3": "Advanced Bundle",
                "tier4": "Premium Bundle",
            }
            tier  = code_rec.get("tier", "")
            disc  = int(code_rec.get("discount_pct") or 0)
            label = tier_labels.get(tier, tier)
            msg   = f"Access code valid! Grants {label} access"
            if disc:
                msg += f" with {disc}% discount"
            msg += " on email confirmation."
            return {
                "valid":        True,
                "code_type":    "access",
                "tier":         tier,
                "tier_label":   label,
                "discount_pct": disc,
                "message":      msg,
            }
    except Exception:
        pass

    # Check referral codes
    try:
        ref_rec = get_referral_code(raw)
        if ref_rec and ref_rec.get("uses", 0) < ref_rec.get("max_uses", 50):
            return {
                "valid":        True,
                "code_type":    "referral",
                "tier":         None,
                "tier_label":   None,
                "discount_pct": 5,
                "message":      "Referral code valid! You'll receive a 5% discount on your first purchase.",
            }
    except Exception:
        pass

    # Check coupon codes � these are applied at checkout, not signup
    try:
        coupon = validate_coupon_db(raw, "any")
        if coupon:
            disc_pct  = int(coupon.get("discount_pct") or 0)
            disc_flat = float(coupon.get("discount_flat") or 0.0)
            uses_left = coupon["max_uses"] - coupon["uses"]
            if disc_pct:
                msg = f"Coupon valid! {disc_pct}% discount will be applied at checkout. ({uses_left} uses left)"
            elif disc_flat:
                msg = f"Coupon valid! \u20a6{disc_flat:,.0f} off will be applied at checkout. ({uses_left} uses left)"
            else:
                msg = f"Coupon valid! Discount will be applied at checkout."
            return {
                "valid":         True,
                "code_type":     "coupon",
                "tier":          None,
                "tier_label":    None,
                "discount_pct":  disc_pct,
                "discount_flat": disc_flat,
                "message":       msg,
            }
    except Exception:
        pass

    return {"valid": False, "message": "Invalid or expired code."}


@app.post("/auth/signup")
async def auth_signup(request: EmailSignUpWithCode) -> dict:
    """
    Register with email + password.
    Optional code field accepts BOTH:
    - Access codes (admin-generated, grant a tier after email confirmation)
    - Referral codes (user-generated, track discount, credited after payment)
    If the code is invalid, signup still proceeds � we just skip the reward.
    """
    pw_hash = hash_password(request.password)

    # Validate code � check access_codes table first, then referrals
    access_code = request.access_code.strip().upper() if request.access_code else ""
    code_rec      = None   # access code record
    referral_rec  = None   # referral code record
    coupon_rec    = None   # coupon record
    code_type     = None   # "access" | "referral" | "coupon"

    if access_code:
        code_rec = validate_access_code(access_code)
        if code_rec:
            code_type = "access"
        else:
            # Try as a referral code
            referral_rec = get_referral_code(access_code)
            if referral_rec and referral_rec.get("uses", 0) < referral_rec.get("max_uses", 50):
                code_type = "referral"
            else:
                # Try as a coupon code � valid coupons are stored and shown at checkout
                try:
                    coupon_rec = validate_coupon_db(access_code, "any")
                    if coupon_rec:
                        code_type = "coupon"
                    else:
                        logger.info("Unrecognised code at signup: %s � proceeding without reward", access_code)
                        access_code = ""
                except Exception:
                    logger.info("Unrecognised code at signup: %s � proceeding without reward", access_code)
                    access_code = ""

    success, message = register_email(request.email, request.name, pw_hash)
    if not success:
        raise HTTPException(status_code=400, detail=message)

    from app.email_auth import _make_learner_id, _pending, _confirmed
    learner_id = _make_learner_id(request.email)

    # Store code info in pending � applied on email confirmation.
    # IMPORTANT: register_email() may auto-confirm (dev/no-SMTP mode), in which
    # case _pending[email] is deleted by confirm_email_token(). We must check
    # _pending still has the entry before writing to it, and apply codes directly
    # to the already-confirmed user if auto-confirm happened.
    email_lower = request.email.lower()
    if access_code and code_type == "access" and code_rec:
        if email_lower in _pending:
            _pending[email_lower]["access_code"]    = access_code
            _pending[email_lower]["access_tier"]    = code_rec["tier"]
            _pending[email_lower]["access_disc_pct"] = int(code_rec.get("discount_pct") or 0)
        elif email_lower in _confirmed:
            # Auto-confirmed path � apply access code directly now
            try:
                from app.db import validate_access_code as _vac, redeem_access_code as _rac, upgrade_tier_db
                from app.progress import apply_tier_upgrade
                vcode = _vac(access_code)
                if vcode:
                    _rac(access_code, email_lower, learner_id)
                    upgrade_tier_db(learner_id, code_rec["tier"])       # SQLite + Supabase
                    apply_tier_upgrade(learner_id, code_rec["tier"])    # in-memory cache
                    logger.info("Access code %s applied directly (auto-confirm) for %s", access_code, email_lower)
            except Exception as exc:
                logger.warning("Direct access code apply failed: %s", exc)
    elif access_code and code_type == "referral" and referral_rec:
        if email_lower in _pending:
            _pending[email_lower]["referral_code"] = access_code
        elif email_lower in _confirmed:
            # Auto-confirmed � record referral use directly
            try:
                from app.db import use_referral_code as _urc
                _urc(access_code, email_lower, learner_id, discount_pct=5, payment_amount=0)
            except Exception as exc:
                logger.warning("Direct referral record failed: %s", exc)
    elif access_code and code_type == "coupon" and coupon_rec:
        # Store the coupon code so it survives to checkout � applied at payment time
        if email_lower in _pending:
            _pending[email_lower]["coupon_code"]     = access_code
            _pending[email_lower]["coupon_disc_pct"] = int(coupon_rec.get("discount_pct") or 0)
            _pending[email_lower]["coupon_disc_flat"] = float(coupon_rec.get("discount_flat") or 0.0)
        # For already-confirmed users (auto-confirm dev path), record use immediately
        elif email_lower in _confirmed:
            try:
                use_coupon_db(access_code, learner_id, email_lower, 0.0)
            except Exception as exc:
                logger.warning("Direct coupon record failed: %s", exc)

    # Mirror to Supabase
    threading.Thread(
        target=sb_upsert_profile,
        args=(learner_id, request.email, request.name),
        daemon=False,
    ).start()

    response = {"ok": True, "message": message}
    if code_type == "access" and code_rec:
        tier_labels = {"tier1": "Beginner Bundle", "tier2": "Intermediate Bundle", "tier3": "Advanced Bundle", "tier4": "Premium Bundle"}
        disc = int(code_rec.get("discount_pct") or 0)
        response["code_accepted"]   = True
        response["code_type"]       = "access"
        response["tier_on_confirm"] = tier_labels.get(code_rec["tier"], code_rec["tier"])
        response["tier"]            = code_rec["tier"]
        if disc:
            response["discount_pct"] = disc
            response["discount_msg"] = f"{disc}% discount applied to your account!"
    elif code_type == "referral":
        response["code_accepted"] = True
        response["code_type"]     = "referral"
        response["discount_pct"]  = 5
    elif code_type == "coupon" and coupon_rec:
        disc_pct  = int(coupon_rec.get("discount_pct") or 0)
        disc_flat = float(coupon_rec.get("discount_flat") or 0.0)
        response["code_accepted"]  = True
        response["code_type"]      = "coupon"
        response["coupon_code"]    = access_code
        if disc_pct:
            response["discount_pct"] = disc_pct
            response["discount_msg"] = f"Coupon saved! {disc_pct}% discount will be applied at checkout."
        elif disc_flat:
            response["discount_flat"] = disc_flat
            response["discount_msg"]  = f"Coupon saved! ?{disc_flat:,.0f} off will be applied at checkout."
    return response


@app.post("/auth/signin", response_model=AuthResponse)
async def auth_signin(request: EmailSignInRequest) -> AuthResponse:
    success, user_data, message = sign_in_email(request.email, request.password)
    if not success or not user_data:
        raise HTTPException(status_code=401, detail=message)
    token = create_session_token(user_data["learner_id"])
    # Ensure Supabase profile row exists before any conversation inserts (Bug 4 fix)
    threading.Thread(
        target=sb_upsert_profile,
        args=(user_data["learner_id"], user_data["email"], user_data["name"]),
        daemon=False,
    ).start()
    profile = get_user_profile_db(user_data["learner_id"])
    picture = profile.get("photo_url", "") or ""
    is_new  = not bool(get_profile(user_data["learner_id"]).topics_seen)

    # Fire greeting email + ensure email_automation row exists (non-blocking)
    def _signin_emails(_lid, _email, _name, _is_new):
        try:
            from app.services.email_service import send_signin_greeting_email
            from app.db import upsert_email_automation
            upsert_email_automation(_lid, _email, _name)
            send_signin_greeting_email(
                name=_name, email=_email,
                greeting=_wat_greeting(_name, _is_new),
                is_new_user=_is_new,
            )
        except Exception as _se:
            pass  # non-fatal — never block sign-in
    threading.Thread(
        target=_signin_emails,
        args=(user_data["learner_id"], user_data["email"],
              user_data["name"], is_new),
        daemon=False,
    ).start()

    return AuthResponse(
        token=token, learner_id=user_data["learner_id"],
        name=user_data["name"], email=user_data["email"], picture=picture,
        greeting=_wat_greeting(user_data["name"], is_new), is_new_user=is_new,
    )


@app.get("/auth/confirm")
async def auth_confirm(token: str) -> JSONResponse:
    from fastapi.responses import RedirectResponse
    import urllib.parse as _up
    success, message = confirm_email_token(token)
    status      = "confirmed" if success else "error"
    msg_encoded = _up.quote(message)
    greeting    = ""
    if success:
        # Decode the token directly to get the just-confirmed user's email —
        # never iterate _confirmed (that picks up a random user in multi-user deploys).
        try:
            from app.email_auth import _confirmed as _conf_store, _get_token_serializer, CONFIRM_MAX_AGE
            _confirmed_name  = ""
            _confirmed_email = ""
            _confirmed_lid   = ""
            try:
                # token payload IS the email address
                _confirmed_email = _get_token_serializer().loads(
                    token, salt="email-confirm", max_age=CONFIRM_MAX_AGE
                )
            except Exception:
                pass
            if _confirmed_email:
                _entry = _conf_store.get(_confirmed_email.lower(), {})
                _confirmed_name = _entry.get("name", "")
                _confirmed_lid  = _entry.get("learner_id", "")
            if _confirmed_name:
                greeting = _up.quote(_wat_greeting(_confirmed_name, is_new=True))
                # Fire greeting + welcome emails non-blocking
                def _send_confirm_emails(_n, _e, _lid):
                    try:
                        from app.services.email_service import (
                            send_welcome_email, send_signin_greeting_email)
                        from app.db import upsert_email_automation
                        send_welcome_email(_n, _e)
                        send_signin_greeting_email(
                            _n, _e,
                            greeting=_wat_greeting(_n, is_new=True),
                            is_new_user=True,
                        )
                        upsert_email_automation(_lid, _e, _n)
                    except Exception as _ee:
                        logger.debug("Confirm emails failed (non-fatal): %s", _ee)
                threading.Thread(
                    target=_send_confirm_emails,
                    args=(_confirmed_name, _confirmed_email, _confirmed_lid),
                    daemon=False,
                ).start()
        except Exception:
            pass
    base_url = _os.getenv('FRONTEND_URL', _os.getenv('APP_URL', 'https://mypytutor.onrender.com'))
    redirect  = f"{base_url}/?auth={status}&msg={msg_encoded}"
    if greeting:
        redirect += f"&greeting={greeting}"
    return RedirectResponse(url=redirect, status_code=302)


@app.post("/auth/resend-confirmation")
async def resend_confirmation(request: Request) -> dict:
    """
    Re-send the confirmation email for a pending (unconfirmed) account.
    Rate-limited: max 3 resend requests per email per 15 minutes to prevent
    using this endpoint to spam confirmation emails at a victim address.
    Always returns 200 to prevent email enumeration.
    """
    # Per-email rate limit stored in the auth store (reuses existing infra)
    from app.security import _check_rate, _auth_store, _get_ip
    ip = _get_ip(request)
    if not _check_rate(_auth_store, f"resend_{ip}", 3, 900):  # 3 per 15 min per IP
        return {"ok": True, "message": "If an account exists, a confirmation link has been sent."}

    body = await request.json()
    email = body.get("email", "").lower().strip()
    if not email or "@" not in email:
        return {"ok": False, "message": "Please enter a valid email address."}

    from app.email_auth import _pending, _confirmed, _get_token_serializer, _send_email_async
    import time as _t

    # Already confirmed � tell them to just sign in
    if email in _confirmed:
        return {"ok": True, "message": "Your email is already confirmed. Please sign in."}

    pending = _pending.get(email)
    if not pending:
        # Not pending and not confirmed � account doesn't exist or was lost on restart
        return {
            "ok":     True,
            "message": (
                "If an account with that email is awaiting confirmation, "
                "a new link has been sent. If you haven't signed up yet, "
                "please create a new account."
            ),
        }

    # Generate a fresh token (old one may have expired)
    new_token = _get_token_serializer().dumps(email, salt="email-confirm")
    pending["token"]      = new_token
    pending["created_at"] = _t.time()
    _pending[email]       = pending

    app_url     = _os.getenv("APP_URL", "https://mypytutor.onrender.com")
    confirm_url = f"{app_url}/auth/confirm?token={new_token}"
    name        = pending.get("name", "Learner")

    # Send via email_service (Resend → SMTP fallback, branded template)
    try:
        from app.services.email_service import send_resend_confirmation_email as _src_email
        _src_email(name, email, confirm_url)
    except Exception:
        # Absolute fallback: plain SMTP
        text_body = (
            f"Hi {name},\n\nConfirm your MyPy Tutor account:\n{confirm_url}\n\n"
            f"This link expires in 24 hours.\n— MyPy Tutor Team"
        )
        _send_email_async(email, "Confirm your MyPy Tutor account",
                          f"<p>Hi {name},</p><p>Confirm your account: <a href='{confirm_url}'>{confirm_url}</a></p>",
                          text_body)

    # Check if email is actually configured � if not, auto-confirm instead
    from app.email_auth import confirm_email_token as _cet
    email_user = _os.getenv("EMAIL_USER", "")
    email_pass = _os.getenv("EMAIL_PASS", "")
    if not email_user or not email_pass or email_user == "your-gmail@gmail.com":
        success, msg = _cet(new_token)
        if success:
            return {"ok": True, "auto_confirmed": True,
                    "message": "Account confirmed! You can now sign in."}

    log_activity("system", "auth:resend_confirmation", f"email={email}")
    return {
        "ok":     True,
        "message": (
            f"A new confirmation link has been sent to {email}. "
            "Please check your inbox and spam folder."
        ),
    }


@app.post("/admin/users/confirm-email")
async def admin_confirm_email(request: Request) -> dict:
    """Admin: manually confirm a user's email (useful when SMTP is broken or after restart)."""
    _require_admin(request)
    body  = await request.json()
    email = body.get("email", "").lower().strip()
    if not email:
        raise HTTPException(status_code=400, detail="email required")

    from app.email_auth import _pending, _confirmed, confirm_email_token as _cet

    # Already confirmed — nothing to do
    if email in _confirmed:
        return {"ok": True, "message": f"{email} is already confirmed. They can sign in now."}

    pending = _pending.get(email)
    if pending:
        # In-memory path — works when the user signed up in this process lifetime
        success, message = _cet(pending["token"])
        log_activity("admin", "admin:manual_confirm", f"email={email}")
        return {"ok": success, "message": message}

    # After a Render restart _pending is empty — fall back to the DB
    try:
        from app.db import get_db as _gdb, confirm_email_db, load_email_account
        acct = load_email_account(email)
        if not acct:
            raise HTTPException(
                status_code=404,
                detail=f"No account found for {email}. The user must sign up first."
            )
        if int(acct.get("confirmed", 0)) == 1:
            # Already confirmed in DB but not in memory — re-load into memory
            from app.email_auth import _by_id
            _confirmed[email] = {
                "name":       acct.get("name", ""),
                "email":      email,
                "learner_id": acct["learner_id"],
                "password_hash": acct.get("password_hash", ""),
            }
            _by_id[acct["learner_id"]] = _confirmed[email]
            return {"ok": True, "message": f"{email} was already confirmed in the database."}

        # Mark confirmed in PostgreSQL
        confirm_email_db(email)

        # Sync into in-memory store so the user can sign in immediately
        from app.email_auth import _by_id
        entry = {
            "name":          acct.get("name", ""),
            "email":         email,
            "learner_id":    acct["learner_id"],
            "password_hash": acct.get("password_hash", ""),
        }
        _confirmed[email]           = entry
        _by_id[acct["learner_id"]]  = entry

        # Send welcome email now that they're confirmed
        try:
            from app.services.email_service import send_welcome_email
            send_welcome_email(acct.get("name", "Learner"), email)
        except Exception as _we:
            logger.debug("Welcome email after admin confirm failed (non-fatal): %s", _we)

        log_activity("admin", "admin:manual_confirm", f"email={email} (DB path)")
        return {"ok": True, "message": f"✅ {email} has been confirmed. They can now sign in."}

    except HTTPException:
        raise
    except Exception as _db_exc:
        logger.error("admin_confirm_email DB fallback failed: %s", _db_exc)
        raise HTTPException(status_code=500, detail=f"Confirmation failed: {_db_exc}")




@app.post("/feedback/message")
async def message_feedback(fb: MessageFeedback, req: Request) -> dict:
    validate_learner_id(fb.learner_id)
    # Feedback-specific rate limit: 20 ratings per minute per IP
    # Prevents bulk fake-review flooding of admin satisfaction metrics
    from app.security import _check_rate, _general_store, _get_ip
    ip = _get_ip(req)
    if not _check_rate(_general_store, f"fb_{ip}", 20, 60):
        raise HTTPException(status_code=429, detail="Too many feedback submissions. Please slow down.")
    record_message_feedback(fb)
    return {"ok": True}


@app.post("/feedback/survey")
async def survey_feedback(fb: SurveyFeedback, req: Request) -> dict:
    validate_learner_id(fb.learner_id)
    # Survey rate limit: max 5 surveys per hour per IP
    from app.security import _check_rate, _enquiry_store, _get_ip
    ip = _get_ip(req)
    if not _check_rate(_enquiry_store, f"surv_{ip}", 5, 3600):
        raise HTTPException(status_code=429, detail="Too many survey submissions. Please wait before submitting again.")
    record_survey(fb)
    return {"ok": True, "message": "Thank you for your feedback! ??"}


@app.get("/feedback/summary", response_model=FeedbackSummary)
async def feedback_summary(request: Request) -> FeedbackSummary:
    """Internal business KPIs � admin only."""
    _require_admin(request)
    return get_summary()


# ---------------------------------------------------------------------------
# Enquiry / Support Contact
# ---------------------------------------------------------------------------

class _EnquiryRequest(_BM):
    name:       str = _Field(..., min_length=1, max_length=80)
    email:      str = _Field(..., min_length=5, max_length=254)
    category:   str = _Field(..., min_length=1, max_length=60)
    subject:    str = _Field(..., min_length=1, max_length=200)
    message:    str = _Field(..., min_length=10, max_length=4000)
    learner_id: str = _Field(default="guest", max_length=64)


@app.post("/enquiry")
async def submit_enquiry(body: _EnquiryRequest) -> dict:
    """
    User support enquiry � forwarded to support@mypytutor.com.ng
    which is linked to tega.com.ng@gmail.com via ADMIN_EMAIL env var.
    Also persists to SQLite for admin visibility.
    """
    import re as _re
    if not _re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", body.email):
        raise HTTPException(status_code=400, detail="Invalid email address.")

    # Persist to PostgreSQL
    try:
        from app.db import get_db as _gdb
        with _gdb() as _conn:
            with _conn.cursor() as _cur:
                _cur.execute(
                    "INSERT INTO enquiries (learner_id,name,email,category,subject,message) "
                    "VALUES (%s,%s,%s,%s,%s,%s)",
                    (body.learner_id, body.name, body.email,
                     body.category, body.subject, body.message)
                )
    except Exception as _e:
        logger.debug("Enquiry DB save failed (non-fatal): %s", _e)

    # Send email to support inbox + confirmation to user
    try:
        from app.services.email_service import send_enquiry_email
        send_enquiry_email(
            name=body.name,
            email=body.email,
            category=body.category,
            subject=body.subject,
            message=body.message,
            learner_id=body.learner_id,
        )
    except Exception as _e:
        logger.warning("Enquiry email dispatch failed (non-fatal): %s", _e)

    log_activity(body.learner_id, "enquiry:submitted",
                 f"category={body.category} | {body.subject[:60]}")
    return {"ok": True, "message": "Your enquiry has been sent. We'll respond within 24 hours."}

# ---------------------------------------------------------------------------
# Certificate routes
# ---------------------------------------------------------------------------

@app.get("/certificate/{level}", response_class=HTMLResponse)
async def get_certificate(
    level: str,
    name: str = "Learner",
    learner_id: str = "default",
    admin_view: bool = False,
    request: Request = None,
    user=Depends(get_current_user),
) -> HTMLResponse:
    if level not in CERT_CONFIGS:
        raise HTTPException(status_code=400, detail="Invalid certificate level.")

    # Admin preview: skip eligibility � admin token required
    if admin_view and request:
        try:
            _require_admin(request)
        except HTTPException:
            admin_view = False   # invalid token � fall through to normal check

    # When a real user is authenticated, always use their session identity.
    # This prevents name spoofing: supply ?name=FakeName&learner_id=victim_id.
    # Anonymous / public certificate pages (e.g. from email link) are still
    # allowed � they go through the normal eligibility check below.
    if user is not None:
        learner_id = user.learner_id   # always use session learner_id
        # Resolve display name from session user � ignore client-supplied ?name=
        session_name = (user.name or "").strip()
        if not session_name:
            # Fallback: load from profile
            _prof = get_profile(learner_id)
            session_name = _prof.display_name or _prof.email.split("@")[0] if _prof.email else "Learner"
        name = session_name or "Learner"

    # Certificate eligibility: check EITHER tier bundle purchase OR relevant courses completed
    CERT_TIER_REQUIRED = {
        "basic":     {"tier1", "tier2", "tier3"},
        "advanced":  {"tier2", "tier3"},
        "executive": {"tier3"},
    }
    CERT_COURSES_REQUIRED = {
        "basic":     {"python-fundamentals", "python-strings", "python-collections", "python-control-flow"},
        "advanced":  {"python-functions-advanced", "python-oop", "python-modules-stdlib"},
        "executive": {"python-dsa", "numpy-mastery", "pandas-mastery", "data-science-python",
                      "machine-learning", "ai-prompt-engineering"},
    }

    profile            = get_profile(learner_id)
    allowed_tiers      = CERT_TIER_REQUIRED.get(level, set())
    required_courses   = CERT_COURSES_REQUIRED.get(level, set())
    completed          = set(profile.completed_projects)
    # One DB query for all purchased courses instead of one-per-course N+1
    purchased_courses  = get_course_purchases_for_learner(learner_id) & required_courses
    courses_ok         = required_courses.issubset(completed | purchased_courses)
    tier_ok            = profile.tier in allowed_tiers

    if not admin_view and not tier_ok and not courses_ok:
        tier_names = {
            "basic":     "Beginner Bundle (₦30,000) or complete all 4 beginner courses",
            "advanced":  "Intermediate Bundle (₦60,000) or complete all 7 courses",
            "executive": "Advanced Bundle (₦100,000) or complete all advanced courses",
        }
        import os as _os_cert_lock
        _lock_path = _os_cert_lock.path.join("static", "certificate-locked.html")
        try:
            with open(_lock_path, "r", encoding="utf-8") as _f:
                _lock_html = _f.read()
        except FileNotFoundError:
            # Minimal fallback if static file is missing
            _lock_html = (
                "<html><body style='font-family:sans-serif;text-align:center;padding:40px'>"
                "<h2>Certificate Locked</h2>"
                "<p>Purchase {{PLAN_NAME}} to unlock your {{LEVEL_TITLE}} certificate.</p>"
                "<a href='https://paystack.shop/pay/vt_re4d3h52'>Upgrade Now</a>"
                "</body></html>"
            )
        _frontend_url_lock = _os.getenv("FRONTEND_URL", _os.getenv("APP_URL", "https://mypytutor.com.ng"))
        _lock_html = (
            _lock_html
            .replace("{{LEVEL_TITLE}}", level.title())
            .replace("{{PLAN_NAME}}", tier_names.get(level, "an appropriate plan"))
            .replace("{{FRONTEND_URL}}", _frontend_url_lock)
        )
        return HTMLResponse(content=_lock_html, status_code=402)

    import re as _re
    clean_name = _re.sub(r'[<>&"\']', '', name).strip()[:80] or "Learner"
    cert_id    = get_cert_id(learner_id, level)
    log_certificate(cert_id, learner_id, clean_name, level)
    # Non-blocking Supabase write — cert HTML is generated immediately
    threading.Thread(
        target=sb_save_certificate,
        args=(cert_id, learner_id, clean_name, level),
        daemon=False,
    ).start()
    html_doc   = generate_certificate_html(
        learner_name=clean_name,
        level=level,
        cert_id=cert_id,
        course_name=profile.current_course or (profile.completed_projects[-1] if profile.completed_projects else None),
    )

    # Send certificate email via email_service (non-blocking)
    try:
        from app.services.email_service import send_certificate_email as _svc_cert
        _email_for_cert = profile.email or ""
        if not _email_for_cert:
            from app.auth import _users as _au
            _eu = _au.get(learner_id)
            if _eu:
                _email_for_cert = _eu.email
        if not _email_for_cert:
            from app.email_auth import get_email_user_by_id as _geuid
            _edu = _geuid(learner_id)
            if _edu:
                _email_for_cert = _edu.get("email", "")
        if _email_for_cert:
            _svc_cert(clean_name, _email_for_cert, level, cert_id)
    except Exception as _cert_email_exc:
        logger.warning("Certificate email dispatch failed (non-fatal): %s", _cert_email_exc)

    return HTMLResponse(content=html_doc)


# ---------------------------------------------------------------------------
# Certificate verification � public endpoint linked from cert emails
# ---------------------------------------------------------------------------

@app.get("/verify/{cert_id}", response_class=HTMLResponse)
async def verify_certificate(cert_id: str) -> HTMLResponse:
    """
    Public certificate verification page.
    Linked from every certificate email as: /verify/{cert_id}
    Returns a branded HTML page confirming the certificate is genuine.
    """
    import re as _re3
    # cert_id is safe-hex, but validate just in case
    if not _re3.match(r'^[a-zA-Z0-9_\-]{4,80}$', cert_id):
        raise HTTPException(status_code=400, detail="Invalid certificate ID.")

    record = None
    try:

        from app.db import get_db as _gdb
        with _gdb() as _conn:
            with _conn.cursor(cursor_factory=_pge.RealDictCursor) as _cur:
                _cur.execute(
                    "SELECT * FROM certificates WHERE cert_id=%s", (cert_id,)
                )
                row = _cur.fetchone()
            if row:
                record = dict(row)
    except Exception as exc:
        logger.warning("Cert verify DB error: %s", exc)

    frontend_url = _os.getenv("FRONTEND_URL", _os.getenv("APP_URL", "https://mypytutor.com.ng"))

    # ── Helper: load a static template and substitute placeholders ──────────
    def _load_verify_tpl(filename: str, subs: dict) -> str:
        import os as _osv
        path = _osv.path.join("static", filename)
        try:
            with open(path, "r", encoding="utf-8") as _fv:
                content = _fv.read()
            for k, v in subs.items():
                content = content.replace(k, str(v))
            return content
        except FileNotFoundError:
            return f"<html><body><h2>{filename} template missing</h2></body></html>"

    if not record:
        html = _load_verify_tpl("certificate-not-found.html", {
            "{{CERT_ID}}":      cert_id,
            "{{FRONTEND_URL}}": frontend_url,
        })
        return HTMLResponse(content=html, status_code=404)

    import datetime as _dtt
    try:
        issued_str = _dtt.datetime.fromtimestamp(
            float(record["issued_at"])
        ).strftime("%d %B %Y")
    except Exception:
        issued_str = str(record.get("issued_at", ""))

    level_label  = str(record.get("level", "")).title()
    learner_name = record.get("learner_name", "Learner")

    html = _load_verify_tpl("certificate-verified.html", {
        "{{CERT_ID}}":      cert_id,
        "{{LEARNER_NAME}}": learner_name,
        "{{LEVEL_LABEL}}":  level_label,
        "{{ISSUED_STR}}":   issued_str,
        "{{FRONTEND_URL}}": frontend_url,
    })
    return HTMLResponse(content=html)

@app.get("/progress/{learner_id}", response_model=ProgressResponse)
async def get_progress(learner_id: str,
                       credentials=Depends(_bearer_optional)) -> ProgressResponse:
    validate_learner_id(learner_id)
    profile = get_profile(learner_id)
    gaps    = get_knowledge_gaps(learner_id)
    # Read updated_at from SQLite so the frontend can detect admin-driven tier changes
    # without waiting for the 60-second progress cache to expire.
    updated_at = 0.0
    try:
        from app.db import load_profile as _lp
        row = _lp(learner_id)
        if row:
            updated_at = float(row.get("updated_at") or 0)
    except Exception:
        pass

    # Only expose tier to the owner of the profile (matching session token)
    # or unauthenticated requests for the learner's OWN data.
    # We expose tier freely here because the frontend needs it for XP display �
    # but we strip the tier from any request where the token belongs to a
    # DIFFERENT learner (cross-user enumeration).
    exposed_tier = profile.tier
    if credentials:
        try:
            from app.auth import verify_session_token
            token_lid = verify_session_token(credentials.credentials)
            if token_lid != learner_id:
                exposed_tier = ""   # different user � hide tier
        except Exception:
            exposed_tier = ""

    return ProgressResponse(
        learner_id=profile.learner_id,
        level=profile.level,
        tier=exposed_tier,
        xp=profile.xp,
        badges=profile.badges,
        topics_seen=profile.topics_seen,
        knowledge_gaps=gaps,
        current_course=profile.current_course,
        current_course_step=profile.current_course_step,
        completed_projects=profile.completed_projects,
        topic_progress=profile.topic_progress,
        updated_at=updated_at,
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
    cache_key = f"courses:{level}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached
    courses = get_courses_for_level(level)
    result = {
        "level": level,
        "courses": [
            {"name": c.name, "description": c.description,
             "level": c.level, "total_steps": len(c.steps)}
            for c in courses
        ],
    }
    _cache_set(cache_key, result, ttl=600)
    return result


@app.get("/courses/catalog")
async def courses_catalog() -> dict:
    """
    Full course catalog with per-course pricing, tier bundles, and prompt plans.
    Frontend uses this to render the separated pricing panels.
    """
    cached = _cache_get("courses:catalog")
    if cached is not None:
        return cached
    from app.courses import COURSE_CATALOG, TIER_PLANS, PROMPT_PLANS, COURSES
    courses_detail = []
    for name, meta in COURSE_CATALOG.items():
        course = COURSES.get(name)
        if course:
            courses_detail.append({
                "name":         name,
                "display_name": course.description.split(" � ")[0] if " � " in course.description else name.replace("-", " ").title(),
                "description":  course.description,
                "level":        course.level,
                "total_steps":  len(course.steps),
                "price_ngn":    meta["price_ngn"],
                "tier_unlocks": meta["tier_unlocks"],
                "category":     meta["category"],
                "badge":        meta["badge"],
                "paystack_url": "https://paystack.shop/pay/vt_re4d3h52",
            })
    result = {
        "courses":       courses_detail,
        "tier_plans":    list(TIER_PLANS.values()),
        "prompt_plans":  list(PROMPT_PLANS.values()),
    }
    _cache_set("courses:catalog", result, ttl=600)
    return result


@app.get("/courses/catalog/{course_name}/price")
async def course_price(course_name: str) -> dict:
    """Get the price and access details for a specific course."""
    from app.courses import COURSE_CATALOG, COURSES
    validate_course_name(course_name)
    meta = COURSE_CATALOG.get(course_name)
    course = COURSES.get(course_name)
    if not meta or not course:
        raise HTTPException(status_code=404, detail="Course not found.")
    return {
        "name":         course_name,
        "price_ngn":    meta["price_ngn"],
        "tier_unlocks": meta["tier_unlocks"],
        "category":     meta["category"],
        "paystack_url": "https://paystack.shop/pay/vt_re4d3h52",
        "total_steps":  len(course.steps),
    }


@app.get("/learner/courses/{learner_id}")
async def learner_courses(learner_id: str,
                          user=Depends(get_current_user)) -> dict:
    """Return all courses a learner has access to (tier bundle + individually purchased)."""
    validate_learner_id(learner_id)
    # Owner check: only the authenticated user can see their own course access list
    if user is None:
        raise HTTPException(status_code=401, detail="Sign in to view your courses.")
    if user.learner_id != learner_id:
        raise HTTPException(status_code=403, detail="You can only view your own courses.")
    from app.courses import COURSE_CATALOG
    profile = get_profile(learner_id)
    purchased = get_learner_courses(learner_id)
    accessible = []
    for name, meta in COURSE_CATALOG.items():
        has_tier   = profile.tier in meta["tier_unlocks"]
        has_bought = name in purchased
        accessible.append({
            "name":       name,
            "badge":      meta["badge"],
            "category":   meta["category"],
            "price_ngn":  meta["price_ngn"],
            "unlocked":   has_tier or has_bought,
            "via":        "tier" if has_tier else ("purchase" if has_bought else "none"),
        })
    return {"learner_id": learner_id, "tier": profile.tier, "courses": accessible}


@app.post("/course/start")
async def start_course(learner_id: str, course_name: str,
                       user=Depends(get_current_user)) -> dict:
    validate_learner_id(learner_id)
    validate_course_name(course_name)

    # Enforce: the authenticated user can only start courses for themselves.
    # Unauthenticated callers are rejected outright.
    if user is None:
        raise HTTPException(status_code=401, detail="Sign in to access courses.")
    if user.learner_id != learner_id:
        raise HTTPException(status_code=403, detail="You can only manage your own courses.")

    course  = get_course(course_name)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found.")

    profile = get_profile(learner_id)

    # Dynamic access check � driven by COURSE_CATALOG tier_unlocks
    from app.courses import COURSE_CATALOG
    meta = COURSE_CATALOG.get(course_name, {})
    allowed_tiers = set(meta.get("tier_unlocks", []))

    # Also check if the user has individually purchased this course
    from app.db import has_course_purchase
    individually_purchased = has_course_purchase(learner_id, course_name)

    if not individually_purchased and profile.tier not in allowed_tiers:
        price = meta.get("price_ngn", 0)
        badge = meta.get("badge", "??")
        category = meta.get("category", "Course")
        tier_needed = "tier1" if "tier1" in allowed_tiers else \
                      "tier2" if "tier2" in allowed_tiers else "tier3"
        tier_names = {"tier1": "Beginner Bundle (?30,000)", "tier2": "Intermediate Bundle (?60,000)", "tier3": "Advanced Bundle (?100,000)"}
        return JSONResponse(status_code=402, content={
            "error":              "upgrade_required",
            "course_name":        course_name,
            "course_price_ngn":   price,
            "course_badge":       badge,
            "course_category":    category,
            "bundle_option":      tier_names.get(tier_needed, "Premium"),
            "paystack_url":       "https://paystack.shop/pay/vt_re4d3h52",
            "message": (
                f"{badge} **{course.description.split(' � ')[0]}** costs ?{price:,} "
                f"(or unlock with the {tier_names.get(tier_needed, 'Premium')}). "
                f"Use the Courses & Plans section to purchase."
            ),
        })

    profile.current_course      = course_name
    profile.current_course_step = 1

    from app.progress import save_profile
    save_profile(profile)

    step          = course.steps[0]
    system_prompt = build_system_prompt(step.intent, topic=step.title, level=profile.level)
    messages      = [{"role": "user", "content": f"Teach me: {step.description}"}]

    # Retry up to 2 times on transient LLM errors (Groq cold start / rate limit)
    content = None
    last_exc: Exception | None = None
    for _attempt in range(2):
        try:
            content = get_completion(system_prompt, messages, intent="course")
            break
        except Exception as exc:
            last_exc = exc
            exc_type = type(exc).__name__.lower()
            if any(k in exc_type for k in ("ratelimit", "timeout", "serviceunavailable")):
                await asyncio.sleep(1)

    if content is None:
        logger.error("Course start LLM error after retries: %s", last_exc)
        raise HTTPException(
            status_code=503,
            detail="Sir. Tega is warming up. Please wait a moment and try again.",
        )

    xp, badge = record_lesson(learner_id, step.title, step.intent)
    return {
        "course":      course_name,
        "step":        step.step,
        "title":       step.title,
        "total_steps": len(course.steps),
        "content":     content,
        "xp_gained":   xp,
        "badge":       badge,
    }


@app.post("/course/next")
async def next_course_step(learner_id: str,
                           user=Depends(get_current_user)) -> dict:
    validate_learner_id(learner_id)

    if user is None:
        raise HTTPException(status_code=401, detail="Sign in to continue your course.")
    if user.learner_id != learner_id:
        raise HTTPException(status_code=403, detail="You can only manage your own courses.")

    profile = get_profile(learner_id)
    if not profile.current_course:
        raise HTTPException(status_code=400, detail="No active course. Start a course first.")

    course = get_course(profile.current_course)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found.")

    profile  = get_profile(learner_id)
    # Read the current step index BEFORE advancing — so on LLM failure the
    # position is not lost (advance only happens on success below).
    step_idx = profile.current_course_step   # 0-indexed: current_course_step starts at 1 after /course/start

    if step_idx >= len(course.steps):
        # All steps already delivered — mark course complete
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

    # Retry up to 2 times on transient LLM errors
    content = None
    last_exc2: Exception | None = None
    for _attempt2 in range(2):
        try:
            content = get_completion(system_prompt, messages, intent="course")
            break
        except Exception as exc2:
            last_exc2 = exc2
            exc_type2 = type(exc2).__name__.lower()
            if any(k in exc_type2 for k in ("ratelimit", "timeout", "serviceunavailable")):
                await asyncio.sleep(1)
                continue
            break

    if content is None:
        logger.error("Course next LLM error after retries: %s", last_exc2)
        raise HTTPException(
            status_code=503,
            detail="Sir. Tega is warming up. Please wait a moment and try again.",
        )

    # Advance position AFTER successful LLM call — prevents step loss on failure
    advance_course(learner_id)
    xp, badge = record_lesson(learner_id, step.title, step.intent)
    return {
        "completed": False, "course": course.name,
        "step": step.step, "title": step.title,
        "total_steps": len(course.steps), "content": content,
        "xp_gained": xp, "badge": badge,
    }


# ---------------------------------------------------------------------------
# Course � previous lesson (re-deliver the previous step without advancing)
# ---------------------------------------------------------------------------

@app.post("/course/prev")
async def prev_course_step(learner_id: str,
                           user=Depends(get_current_user)) -> dict:
    """Go back one step in the current course without losing progress."""
    validate_learner_id(learner_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Sign in to continue your course.")
    if user.learner_id != learner_id:
        raise HTTPException(status_code=403, detail="You can only manage your own courses.")

    profile = get_profile(learner_id)
    if not profile.current_course:
        raise HTTPException(status_code=400, detail="No active course. Start a course first.")

    course = get_course(profile.current_course)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found.")

    # Step back � minimum is step 1
    if profile.current_course_step > 1:
        from app.progress import save_profile as _sp
        profile.current_course_step -= 1
        _sp(profile)

    step_idx = profile.current_course_step - 1
    if step_idx < 0 or step_idx >= len(course.steps):
        step_idx = 0

    step = course.steps[step_idx]
    system_prompt = build_system_prompt(step.intent, topic=step.title, level=profile.level)
    messages = [{"role": "user", "content": f"Teach me: {step.description}"}]

    content = None
    for _attempt in range(2):
        try:
            content = get_completion(system_prompt, messages, intent="course")
            break
        except Exception as exc:
            exc_type = type(exc).__name__.lower()
            if any(k in exc_type for k in ("ratelimit", "timeout", "serviceunavailable")):
                await asyncio.sleep(1)
                continue
            break

    if content is None:
        raise HTTPException(status_code=503, detail="Sir. Tega is warming up. Please try again.")

    return {
        "completed": False, "course": course.name,
        "step": step.step, "title": step.title,
        "total_steps": len(course.steps), "content": content,
        "xp_gained": 0, "badge": None,
    }

# ---------------------------------------------------------------------------
# Quiz & Exercise
# ---------------------------------------------------------------------------

@app.post("/quiz/generate", response_model=QuizResponse)
async def generate_quiz(request: QuizRequest, req: Request,
                        user=Depends(get_current_user)) -> QuizResponse:
    validate_topic(request.topic)
    # If a token is provided, enforce it matches the learner_id in the body.
    # Anonymous (no token) quiz requests are still allowed � they use IP-based
    # rate limiting and the free daily limit just like anonymous chat.
    if user is not None and user.learner_id != request.learner_id:
        raise HTTPException(status_code=403, detail="learner_id does not match your session.")
    # Enforce free-tier daily limit for quiz generation (counts the same as a chat prompt)
    profile = get_profile(request.learner_id)
    if profile.tier == "free":
        ip = _get_ip(req)
        allowed, used = check_free_prompt_limit(request.learner_id, ip)
        if not allowed:
            from app.security import FREE_DAILY_LIMIT
            return JSONResponse(
                status_code=402,
                content={
                    "error": "free_limit_reached",
                    "message": f"You've used your {FREE_DAILY_LIMIT} free daily prompts. Upgrade to Premium!",
                    "used": used, "limit": FREE_DAILY_LIMIT,
                },
            )
        increment_free_prompt_count(request.learner_id, ip)
    system_prompt = build_system_prompt("quiz", topic=request.topic, level=request.level)
    messages = [{"role": "user", "content": f"Generate a quiz question about: {request.topic}"}]
    try:
        content = get_completion(system_prompt, messages, intent="quiz")
    except Exception as exc:
        logger.error("Quiz generate LLM error: %s", exc)
        raise HTTPException(status_code=502, detail="AI service error. Please try again.")
    question, options = _parse_quiz(content)
    return QuizResponse(question=question, options=options, topic=request.topic, level=request.level)


@app.post("/quiz/answer", response_model=QuizAnswerResponse)
async def evaluate_quiz_answer(request: QuizAnswerRequest,
                               user=Depends(get_current_user)) -> QuizAnswerResponse:
    validate_topic(request.topic)
    # If authenticated, enforce learner_id matches token � prevents XP farming
    # for other users. Anonymous quiz answers (free-tier) are still accepted.
    if user is not None and user.learner_id != request.learner_id:
        raise HTTPException(status_code=403, detail="learner_id does not match your session.")
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
        content = get_completion(system_prompt, messages, intent="quiz_eval")
    except Exception as exc:
        logger.error("Quiz answer LLM error: %s", exc)
        raise HTTPException(status_code=502, detail="AI service error. Please try again.")
    correct = bool(re.search(r'\bcorrect\s*:\s*true\b', content, re.IGNORECASE))
    score   = 100 if correct else 0
    xp, _   = record_quiz(request.learner_id, request.topic, score)
    # Persist full quiz attempt record
    save_quiz_attempt(request.learner_id, request.topic,
                      request.question, request.answer, correct, score)
    return QuizAnswerResponse(correct=correct, explanation=content, score=score, xp_gained=xp)


@app.post("/exercise/generate")
async def generate_exercise(learner_id: str, topic: str,
                            user=Depends(get_current_user)) -> dict:
    validate_learner_id(learner_id)
    validate_topic(topic)
    # Authenticated users must match their own learner_id.
    # Anonymous users (no token) are allowed � free-tier discovery via chat.
    if user is not None and user.learner_id != learner_id:
        raise HTTPException(status_code=403, detail="learner_id does not match your session.")
    profile  = get_profile(learner_id)
    gaps     = get_knowledge_gaps(learner_id)
    is_gap   = topic in gaps
    system_prompt = build_system_prompt("exercise", topic=topic, level=profile.level, is_gap_topic=is_gap)
    messages = [{"role": "user", "content": f"Give me a Python exercise on: {topic}"}]
    try:
        content = get_completion(system_prompt, messages, intent="exercise")
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
    if not options or len(options) < 2:
        # LLM returned a malformed response -- surface a clean 422 instead of
        # sending dummy placeholder options that confuse the frontend.
        raise HTTPException(
            status_code=422,
            detail="Quiz question could not be parsed. Please try again.",
        )
    return question, options

# ---------------------------------------------------------------------------
# Paystack webhook � handles tier bundles, individual course purchases, prompt plans
# ---------------------------------------------------------------------------

# Map Paystack plan name (lowercase) ? internal tier
_PAYSTACK_PLAN_TIER: dict[str, str] = {
    # New 4-tier bundle names
    "beginner bundle":      "tier1",
    "intermediate bundle":  "tier2",
    "advanced bundle":      "tier3",
    "premium bundle":       "tier4",
    # Legacy names kept for backwards compatibility
    "elite bundle":         "tier4",
    "elite":                "tier4",
    "pro learner":          "tier1",
    "career builder":       "tier2",
    "tier1":                "tier1",
    "tier 1":               "tier1",
    "tier2":                "tier2",
    "tier 2":               "tier2",
    "tier3":                "tier3",
    "tier 3":               "tier3",
    "tier4":                "tier4",
    "tier 4":               "tier4",
    "plan_tier1":           "tier1",
    "plan_tier2":           "tier2",
    "plan_tier3":           "tier3",
    "plan_tier4":           "tier4",
}

# Prompt plan names ? prompt tier key
_PAYSTACK_PROMPT_PLAN: dict[str, str] = {
    "prompt starter":   "prompt-starter",
    "prompt pro":       "prompt-pro",
    "prompt unlimited": "prompt-unlimited",
    "prompt_starter":   "prompt-starter",
    "prompt_pro":       "prompt-pro",
    "prompt_unlimited": "prompt-unlimited",
}


@app.post("/webhooks/paystack")
async def paystack_webhook(request: Request) -> dict:
    """
    Paystack sends a POST with a JSON body and an X-Paystack-Signature header.
    Handles three payment types:
    1. Tier bundle purchase  ? upgrade learner.tier
    2. Individual course     ? record_course_purchase(learner_id, course_name)
    3. Prompt plan purchase  ? upgrade prompt daily limit (stored on learner profile)
    """
    secret_key = _os.getenv("PAYSTACK_SECRET_KEY", "")
    body_bytes  = await request.body()

    # -- CRITICAL: always verify the HMAC signature.
    # If PAYSTACK_SECRET_KEY is not set we reject the request entirely �
    # accepting unsigned webhooks would let anyone fake a payment.
    if not secret_key:
        logger.error(
            "PAYSTACK_SECRET_KEY env var is not set � rejecting webhook. "
            "Add it to Render ? Environment immediately."
        )
        raise HTTPException(status_code=400, detail="Webhook not configured")

    sig_header = request.headers.get("x-paystack-signature", "")
    expected   = hmac.new(
        secret_key.encode(), body_bytes, hashlib.sha512
    ).hexdigest()
    if not hmac.compare_digest(sig_header, expected):
        logger.warning("Paystack webhook signature mismatch � ignored")
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
        amount_kob = data.get("amount", 0)
        amount_ngn = amount_kob / 100
        reference  = str(data.get("reference", "")).strip()

        # -- IDEMPOTENCY: skip if this reference was already processed --------
        # Paystack retries webhooks on non-200 responses. Without this check,
        # a network blip could cause double tier upgrades / double bonus credits.
        if reference:
            try:
                from app.db import get_db as _gdb_idem
                with _gdb_idem() as _idem_conn:
                    with _idem_conn.cursor() as _idem_cur:
                        _idem_cur.execute(
                            "SELECT 1 FROM processed_webhooks WHERE reference=%s",
                            (reference,)
                        )
                        existing = _idem_cur.fetchone()
                        if existing:
                            logger.info("Paystack webhook: duplicate reference %s � skipped", reference)
                            return {"ok": True}
                        _idem_cur.execute(
                            "INSERT INTO processed_webhooks (reference) VALUES (%s)",
                            (reference,)
                        )
            except Exception as _idem_exc:
                logger.warning("Webhook idempotency check failed (proceeding): %s", _idem_exc)

        # Get learner_id from email
        from app.db import load_email_account
        acct       = load_email_account(email)
        learner_id = acct["learner_id"] if acct else email

        # -- Determine payment type from metadata -------------------------
        plan_meta    = str(meta.get("plan", "") or meta.get("tier", "")).lower().strip()
        course_meta  = str(meta.get("course_name", "") or meta.get("course", "")).lower().strip()
        coupon_code  = str(meta.get("coupon_code", "") or meta.get("coupon", "")).upper().strip()

        # -- Apply coupon savings if a coupon was attached to this payment -
        if coupon_code and learner_id and email:
            try:
                from app.db import validate_coupon_db, use_coupon_db
                coupon = validate_coupon_db(coupon_code, plan_meta or "any")
                if coupon:
                    disc_pct  = int(coupon.get("discount_pct") or 0)
                    disc_flat = float(coupon.get("discount_flat") or 0.0)
                    savings   = disc_flat if disc_flat > 0 else round(amount_ngn * disc_pct / 100, 2)
                    use_coupon_db(coupon_code, learner_id, email, savings)
                    logger.info(
                        "Paystack webhook: coupon %s applied for %s � savings ?%.2f",
                        coupon_code, email, savings
                    )
            except Exception as _coupon_exc:
                logger.debug("Coupon apply in webhook failed (non-fatal): %s", _coupon_exc)

        # -- TYPE 1: Individual course purchase ----------------------------
        if course_meta and course_meta in (c.name for c in get_all_courses()):
            import secrets as _sec
            record_course_purchase(learner_id, course_meta, amount_ngn,
                                   data.get("reference", ""))
            payment = add_payment(email, customer.get("name", email),
                                  amount_ngn, f"Course: {course_meta}", "paystack")
            # Paystack charge.success means the payment IS confirmed � mark it immediately
            confirm_payment(payment.id)
            invoice_id = f"INV-{_sec.token_hex(5).upper()}"
            create_invoice_db(invoice_id, payment.id, learner_id, email,
                              customer.get("name", email),
                              f"Course: {course_meta}", amount_ngn)
            # Non-blocking Supabase mirror
            threading.Thread(
                target=sb_save_payment,
                args=(payment.id, email, customer.get("name", email),
                      amount_ngn, f"Course: {course_meta}", "paystack"),
                daemon=False,
            ).start()
            # Send payment receipt email (non-blocking)
            try:
                from app.services.email_service import send_payment_receipt_email as _svc_pay
                _svc_pay(
                    name=customer.get("name", email),
                    email=email,
                    amount=amount_ngn,
                    plan=f"Course: {course_meta}",
                    payment_id=payment.id,
                )
            except Exception as _ep:
                logger.debug("Payment receipt email failed (non-fatal): %s", _ep)
            log_activity(learner_id, "payment:course",
                         f"course={course_meta} | ?{amount_ngn:.0f}")
            logger.info("Paystack webhook: course purchase %s for %s | invoice=%s",
                        course_meta, email, invoice_id)

        # -- TYPE 2: Tier bundle purchase ----------------------------------
        else:
            tier = _PAYSTACK_PLAN_TIER.get(plan_meta)

            if not tier:
                # Infer tier from amount using canonical bundle prices:
                # Premium ₦150,000 (tier4) | Advanced ₦100,000 (tier3) | Intermediate ₦60,000 (tier2) | Beginner ₦30,000 (tier1)
                if amount_ngn >= 140000:
                    tier = "tier4"   # Premium Bundle — ₦150,000 (all 17 courses)
                elif amount_ngn >= 100000:
                    tier = "tier3"   # Advanced Bundle — ₦100,000 (14 courses)
                elif amount_ngn >= 50000:
                    tier = "tier2"   # Intermediate Bundle ₦60,000
                elif amount_ngn >= 25000:
                    tier = "tier1"   # Beginner Bundle ₦30,000

            # -- TYPE 3: Prompt plan (parallel check) ---------------------
            prompt_plan = _PAYSTACK_PROMPT_PLAN.get(plan_meta)
            if prompt_plan:
                from app.courses import PROMPT_PLANS
                plan_info = PROMPT_PLANS.get(prompt_plan, {})
                daily_limit = plan_info.get("daily_limit", 50)
                from app.progress import get_profile as _gp, save_profile as _sp
                p = _gp(learner_id)
                import datetime as _dtt
                today = _dtt.date.today().isoformat()
                from app.security import _daily_prompt_store
                _daily_prompt_store[learner_id] = (today, 0)
                # Persist prompt plan on learner profile as a special tier prefix
                # so the daily limit is restored on Render restart
                try:
                    from app.db import get_db as _gdb2
                    with _gdb2() as _pc:
                        with _pc.cursor() as _pcc:
                            _pcc.execute("""
                                INSERT INTO learner_profiles (learner_id, tier, prompt_plan)
                                VALUES (%s, %s, %s)
                                ON CONFLICT(learner_id) DO UPDATE SET
                                  prompt_plan = EXCLUDED.prompt_plan,
                                  updated_at  = EXTRACT(EPOCH FROM NOW())
                            """, (learner_id, prompt_plan, prompt_plan))
                except Exception:
                    pass  # non-fatal � in-memory reset still applied
                log_activity(learner_id, "payment:prompt_plan",
                             f"plan={prompt_plan} limit={daily_limit} | ?{amount_ngn:.0f}")

            if tier:
                upgrade_tier_db(learner_id, tier)        # SQLite + Supabase
                from app.progress import apply_tier_upgrade
                apply_tier_upgrade(learner_id, tier)     # in-memory cache sync

                tier_labels = {
                    "tier1": "Beginner Bundle — ₦30,000 (4 courses)",
                    "tier2": "Intermediate Bundle — ₦60,000 (7 courses)",
                    "tier3": "Advanced Bundle — ₦100,000 (14 courses)",
                    "tier4": "Premium Bundle — ₦150,000 (all 17 courses)",
                }
                plan_label = tier_labels.get(tier, tier)
                import secrets as _sec
                payment    = add_payment(email, customer.get("name", email),
                                         amount_ngn, plan_label, "paystack")
                # Paystack charge.success = payment IS confirmed � mark immediately
                confirm_payment(payment.id)
                invoice_id = f"INV-{_sec.token_hex(5).upper()}"
                create_invoice_db(invoice_id, payment.id, learner_id, email,
                                  customer.get("name", email), plan_label, amount_ngn)
                # Non-blocking Supabase mirror � webhook must return 200 fast
                threading.Thread(
                    target=sb_save_payment,
                    args=(payment.id, email, customer.get("name", email),
                          amount_ngn, plan_label, "paystack"),
                    daemon=False,
                ).start()
                threading.Thread(
                    target=sb_update_tier,
                    args=(learner_id, tier),
                    daemon=False,
                ).start()

                # Send payment receipt email to the user (non-blocking)
                try:
                    from app.services.email_service import send_payment_receipt_email as _svc_pay
                    _svc_pay(
                        name=customer.get("name", email),
                        email=email,
                        amount=amount_ngn,
                        plan=plan_label,
                        payment_id=payment.id,
                    )
                except Exception as _ep:
                    logger.debug("Payment receipt email failed (non-fatal): %s", _ep)

                # Credit referral bonus
                try:
                    from app.db import get_db as _gdb
                    with _gdb() as _conn:
                        with _conn.cursor(cursor_factory=_pge.RealDictCursor) as _cur:
                            _cur.execute(
                                "SELECT code FROM referral_uses "
                                "WHERE used_by_id=%s OR used_by_email=%s LIMIT 1",
                                (learner_id, email)
                            )
                            ref_use = _cur.fetchone()
                    if ref_use:
                        _ref_code = ref_use["code"]
                        bonus = round(amount_ngn * 0.15, 2)
                        with _gdb() as _conn:
                            with _conn.cursor() as _cur:
                                _cur.execute(
                                    "UPDATE referrals SET bonus_balance=bonus_balance+%s WHERE code=%s",
                                    (bonus, _ref_code)
                                )
                        logger.info("Credited ?%s referral bonus (15%%) for code %s", bonus, _ref_code)
                except Exception as rb_exc:
                    logger.debug("Referral bonus credit failed: %s", rb_exc)

                log_activity(learner_id, "payment:webhook",
                             f"tier={tier} | ?{amount_ngn:.0f} | invoice={invoice_id}")
                logger.info("Paystack webhook: upgraded %s ? %s | ?%.0f",
                            email, tier, amount_ngn)

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


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Standardise ALL HTTPException responses to {"error": "..."} shape.
    FastAPI's default emits {"detail": "..."} which is inconsistent with the
    custom handlers below that already use {"error": "..."}."""
    detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    return JSONResponse(status_code=exc.status_code, content={"error": detail})


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
    email:    str = _Field(..., min_length=5,  max_length=254)
    password: str = _Field(..., min_length=1,  max_length=128)


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


class _ReferralWithdraw(_BM):
    learner_id: str
    email: str
    amount: float
    bank_name: str
    account_name: str
    account_num: str


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

    # -- Pull everything directly from SQLite for real-time accuracy ----------
    # Never rely on in-memory stores (_store, _payments, etc.) since Render
    # free tier wipes memory on restart. SQLite is the canonical source.
    import datetime as _dt

    today_str    = _dt.date.today().isoformat()
    wat_today    = _dt.date.today().isoformat()   # already computed above

    try:

        from app.db import get_db as _gdb, get_all_confirmed_emails, get_certificates_db

        with _gdb() as _conn:
            with _conn.cursor() as _cur:
                from app.security import _wat_date_key
                wat_date = _wat_date_key()

                _cur.execute("SELECT COUNT(*) FROM email_accounts WHERE confirmed=1")
                email_count = _cur.fetchone()[0]
                _cur.execute("SELECT COUNT(*) FROM learner_profiles")
                profile_count = _cur.fetchone()[0]
                total_users = max(email_count, profile_count)

                _cur.execute(
                    "SELECT COUNT(DISTINCT key) FROM daily_prompt_counts WHERE date_str=%s AND count>0",
                    (wat_date,)
                )
                active_today = _cur.fetchone()[0]

                tier_counts: dict = {}
                for _tier in ["free", "tier1", "tier2", "tier3", "tier4"]:
                    _cur.execute(
                        "SELECT COUNT(*) FROM learner_profiles WHERE tier=%s", (_tier,)
                    )
                    tier_counts[_tier] = _cur.fetchone()[0]

                _cur.execute("SELECT SUM(amount), COUNT(*) FROM payments WHERE status='confirmed'")
                rev_rows = _cur.fetchone()
                total_revenue  = float(rev_rows[0] or 0)
                confirmed_pmts = int(rev_rows[1] or 0)

                _cur.execute("SELECT COUNT(*) FROM payments WHERE status='pending'")
                pending_pmts = _cur.fetchone()[0]
                _cur.execute("SELECT COUNT(*) FROM payments")
                total_pmts = _cur.fetchone()[0]

                _cur.execute(
                    "SELECT plan, SUM(amount) FROM payments WHERE status='confirmed' GROUP BY plan"
                )
                by_plan = {r[0]: float(r[1]) for r in _cur.fetchall()}

                # PostgreSQL: convert epoch to date using to_timestamp()
                _cur.execute(
                    "SELECT COALESCE(SUM(amount),0) FROM payments "
                    "WHERE status='confirmed' AND DATE(to_timestamp(created_at))=%s",
                    (today_str,)
                )
                today_rev = _cur.fetchone()[0]

                _cur.execute("SELECT COUNT(*) FROM certificates")
                cert_count = _cur.fetchone()[0]

                _cur.execute("SELECT COUNT(*) FROM tasks")
                task_total = _cur.fetchone()[0]
                _cur.execute("SELECT COUNT(*) FROM tasks WHERE status='open'")
                task_open = _cur.fetchone()[0]
                _cur.execute("SELECT COUNT(*) FROM tasks WHERE status='in_progress'")
                task_inprog = _cur.fetchone()[0]
                _cur.execute("SELECT COUNT(*) FROM tasks WHERE status='done'")
                task_done = _cur.fetchone()[0]

                _cur.execute("SELECT COUNT(*) FROM team_members")
                team_size = _cur.fetchone()[0]

                _cur.execute(
                    "SELECT COUNT(*) FROM referral_withdrawals WHERE status='pending'"
                )
                wd_pending = _cur.fetchone()[0]
                cutoff_24h = time.time() - 86400
                _cur.execute(
                    "SELECT COUNT(*) FROM email_accounts WHERE confirmed=1 AND created_at>=%s",
                    (cutoff_24h,)
                )
                new_users_24h = _cur.fetchone()[0]

    except Exception as e:
        logger.error("admin_dashboard DB error: %s", e)
        # Fallback to memory
        from app.progress import _store as _ls
        total_users   = len(_ls)
        active_today  = 0
        tier_counts   = {t: sum(1 for p in _ls.values() if p.tier == t) for t in ["free","tier1","tier2","tier3","tier4"]}
        total_revenue = 0; confirmed_pmts = 0; pending_pmts = 0; total_pmts = 0
        by_plan = {}; today_rev = 0; cert_count = 0
        task_total = task_open = task_inprog = task_done = team_size = wd_pending = new_users_24h = 0

    # Feedback (always in-memory, refreshed per chat)
    feedback_data = get_summary().model_dump()

    return {
        "users": {
            "total":       total_users,
            "active_today":active_today,
            "new_24h":     new_users_24h,
        },
        "users_by_tier": tier_counts,
        "revenue": {
            "total_revenue": total_revenue,
            "today_revenue": float(today_rev or 0),
            "total_payments": total_pmts,
            "confirmed":     confirmed_pmts,
            "pending":       pending_pmts,
            "by_plan":       by_plan,
        },
        "payments":        total_pmts,
        "certificates":    cert_count,
        "tasks": {
            "total": task_total, "open": task_open,
            "in_progress": task_inprog, "done": task_done,
        },
        "feedback":        feedback_data,
        "team_size":       team_size,
        "withdrawals_pending": wd_pending,
    }

@app.get("/admin/users")
async def admin_list_users(request: Request) -> dict:
    """
    Return all users sourced primarily from PostgreSQL (persistent, survives restarts).
    Merges data from:
      - learner_profiles table (all users who ever chatted / upgraded)
      - email_accounts table (all email sign-ups, including those who never chatted)
      - in-memory _store (live XP / course data that hasn't been flushed yet)
      - auth._users (Google sign-in users)
    Returns joined_at (real signup date) for each user.
    """
    _require_admin(request)
    from app.db import get_db as _gdb
    from app.progress import _store as ls
    from app.auth import _users as _auth_users
    import datetime as _dt

    users_map: dict = {}   # learner_id ? user dict

    # 1. Seed from PostgreSQL learner_profiles (canonical persistent store)
    #    Also pull created_at from email_accounts in one JOIN for real signup dates
    try:

        with _gdb() as _conn:
            with _conn.cursor(cursor_factory=_pge.RealDictCursor) as _cur:
                _cur.execute("""
                    SELECT lp.learner_id, lp.email, lp.display_name, lp.tier,
                           lp.level, lp.xp, lp.topics_seen, lp.completed_projects,
                           lp.badges, lp.current_course, lp.updated_at,
                           ea.created_at AS joined_ts, ea.name AS ea_name
                    FROM learner_profiles lp
                    LEFT JOIN email_accounts ea ON ea.learner_id = lp.learner_id
                    WHERE lp.display_name != '[deleted]'
                      AND lp.tier != 'deleted'
                """)
                rows = _cur.fetchall()
            for r in rows:
                lid = r["learner_id"]
                try:
                    topics  = len(__import__("json").loads(r["topics_seen"] or "[]"))
                    courses = len(__import__("json").loads(r["completed_projects"] or "[]"))
                    badges  = len(__import__("json").loads(r["badges"] or "[]"))
                except Exception:
                    topics = courses = badges = 0
                # Prefer email_accounts.created_at (real signup time)
                # Fall back to learner_profiles.updated_at (first activity time)
                joined_ts = r.get("joined_ts") or r.get("updated_at")
                try:
                    joined_at = _dt.datetime.fromtimestamp(float(joined_ts)).strftime("%Y-%m-%d %H:%M") if joined_ts else ""
                except Exception:
                    joined_at = ""
                users_map[lid] = {
                    "learner_id":    lid,
                    "email":         r["email"] or "",
                    "name":          r["display_name"] or r.get("ea_name") or "",
                    "tier":          r["tier"] or "free",
                    "level":         r["level"] or "beginner",
                    "xp":            int(r["xp"] or 0),
                    "topics_seen":   topics,
                    "courses_done":  courses,
                    "badges":        badges,
                    "current_course": r["current_course"],
                    "joined_at":     joined_at,
                    "joined_ts":     float(joined_ts) if joined_ts else 0.0,
                }
    except Exception as _e:
        logger.warning("admin_list_users learner_profiles error: %s", _e)

    # 2. Overlay live in-memory data (fresher XP/tier if not yet flushed)
    for lid, profile in ls.items():
        # Skip deleted/terminated accounts
        if profile.tier == "deleted" or getattr(profile, "display_name", "") == "[deleted]":
            continue
        auth_info = _auth_users.get(lid)
        existing  = users_map.get(lid, {})
        users_map[lid] = {
            "learner_id":    lid,
            "email":         existing.get("email") or profile.email or (auth_info.email if auth_info else "") or "",
            "name":          existing.get("name")  or profile.display_name or (auth_info.name  if auth_info else "") or "",
            "tier":          profile.tier,
            "level":         profile.level,
            "xp":            profile.xp,
            "topics_seen":   len(profile.topics_seen),
            "courses_done":  len(profile.completed_projects),
            "badges":        len(profile.badges),
            "current_course": profile.current_course,
            "joined_at":     existing.get("joined_at", ""),
            "joined_ts":     existing.get("joined_ts", 0.0),
        }

    # 3. Add email-account-only users (signed up but never chatted, not yet in learner_profiles)
    # Also build a set of deleted learner_ids so we don't re-add them from email_accounts
    deleted_ids: set = set()
    try:
        from app.db import get_db as _gdb3
        with _gdb3() as _c3:
            with _c3.cursor() as _cur3:
                _cur3.execute(
                    "SELECT learner_id FROM learner_profiles "
                    "WHERE display_name='[deleted]' OR tier='deleted'"
                )
                deleted_ids = {row[0] for row in _cur3.fetchall()}
    except Exception:
        pass

    try:
        db_emails = get_all_confirmed_emails()
    except Exception:
        from app.email_auth import _confirmed
        db_emails = [
            {"email": e, "name": u["name"], "learner_id": u["learner_id"]}
            for e, u in _confirmed.items()
        ]

    for r in db_emails:
        lid = r["learner_id"]
        # Skip deleted accounts
        if lid in deleted_ids:
            continue
        # Format join date from email_accounts.created_at
        try:
            joined_at = _dt.datetime.fromtimestamp(float(r.get("created_at", 0))).strftime("%Y-%m-%d %H:%M") if r.get("created_at") else ""
            joined_ts = float(r.get("created_at", 0))
        except Exception:
            joined_at = ""
            joined_ts = 0.0
        if lid not in users_map:
            users_map[lid] = {
                "learner_id":    lid,
                "email":         r["email"],
                "name":          r["name"],
                "tier":          "free",
                "level":         "beginner",
                "xp":            0,
                "topics_seen":   0,
                "courses_done":  0,
                "badges":        0,
                "current_course": None,
                "joined_at":     joined_at,
                "joined_ts":     joined_ts,
            }
        else:
            # Fill in missing email/name from email_accounts
            if not users_map[lid]["email"]:
                users_map[lid]["email"] = r["email"]
            if not users_map[lid]["name"]:
                users_map[lid]["name"] = r["name"]
            # Use email account creation date if we don't have a join date yet
            if not users_map[lid].get("joined_at") and joined_at:
                users_map[lid]["joined_at"] = joined_at
                users_map[lid]["joined_ts"] = joined_ts

    users = sorted(
        [u for u in users_map.values() if u.get("name") != "[deleted]" and u.get("tier") != "deleted"],
        key=lambda u: u.get("joined_ts", 0.0), reverse=True
    )

    return {
        "learner_profiles": users,
        "email_accounts":   [{"email": r["email"], "name": r["name"],
                               "learner_id": r["learner_id"], "type": "email"}
                              for r in db_emails],
        "total":         len(users),
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

# set-tier � uses apply_tier_upgrade for atomic memory+SQLite+Supabase consistency
@app.post("/admin/users/{learner_id}/set-tier")
async def admin_set_tier(learner_id: str, request: Request) -> dict:
    _require_admin(request)
    validate_learner_id(learner_id)
    body = await request.json()
    tier = body.get("tier", "free")
    if tier not in ("free", "tier1", "tier2", "tier3", "tier4"):
        raise HTTPException(status_code=400, detail="Invalid tier. Must be free, tier1, tier2, tier3, or tier4.")

    from app.progress import apply_tier_upgrade
    apply_tier_upgrade(learner_id, tier)   # updates _store + SQLite atomically
    upgrade_tier_db(learner_id, tier)      # also writes Supabase via upgrade_tier_db
    log_activity(learner_id, "admin:set-tier", f"tier set to {tier}")
    return {"ok": True, "learner_id": learner_id, "tier": tier}


@app.post("/admin/users/{learner_id}/terminate")
async def admin_terminate_user(learner_id: str, request: Request) -> dict:
    """Soft-terminate: reset tier to free, clear active course. Account remains."""
    _require_admin(request)
    validate_learner_id(learner_id)
    from app.progress import apply_tier_upgrade
    # Reset tier + clear course progress atomically
    p = get_profile(learner_id)
    p.tier                = "free"
    p.current_course      = None
    p.current_course_step = 0
    from app.progress import save_profile as _sp
    _sp(p)
    upgrade_tier_db(learner_id, "free")   # also writes Supabase
    apply_tier_upgrade(learner_id, "free")
    log_activity(learner_id, "admin:terminate", "subscription terminated by admin")
    return {"ok": True, "message": f"Subscription terminated for {learner_id}"}


@app.delete("/admin/users/{learner_id}")
async def admin_delete_user(learner_id: str, request: Request) -> dict:
    """
    Hard-delete a user account (admin-only).

    Permanently removes all PII and anonymises learning data.
    Payment records are retained for 7 years (Nigerian tax law).
    Works even when no email is on record (Google/GitHub OAuth users).
    """
    _require_admin(request)
    validate_learner_id(learner_id)

    # Try every source to find the user's email — it is only needed for
    # the payments anonymisation step; deletion itself works without it.
    email = ""

    # 1. learner_profiles table (fastest — already pooled)
    try:
        from app.db import load_profile as _lp_db
        row = _lp_db(learner_id)
        if row:
            email = (row.get("email") or "").strip()
    except Exception:
        pass

    # 2. email_accounts table (email-signup users)
    if not email:
        try:
            from app.db import get_db as _gdb2
            with _gdb2() as _c2:
                with _c2.cursor(cursor_factory=_pge.RealDictCursor) as _cur2:
                    _cur2.execute(
                        "SELECT email FROM email_accounts WHERE learner_id=%s LIMIT 1",
                        (learner_id,)
                    )
                    _row2 = _cur2.fetchone()
                    if _row2:
                        email = (_row2["email"] or "").strip()
        except Exception:
            pass

    # 3. In-memory progress store (Google/GitHub users)
    if not email:
        try:
            p = get_profile(learner_id)
            email = (p.email or "").strip()
        except Exception:
            pass

    # 4. In-memory auth store (Google/GitHub users after restart)
    if not email:
        try:
            from app.auth import _users as _au
            au = _au.get(learner_id)
            if au:
                email = (au.email or "").strip()
        except Exception:
            pass

    # If we still have no email, check whether the learner even exists
    # before proceeding (avoid silently deleting a ghost ID)
    if not email:
        try:
            from app.db import load_profile as _lp2
            if _lp2(learner_id) is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"User '{learner_id}' not found in the database."
                )
            # Learner exists but has no email (e.g. imported via access code with no auth)
            # Proceed with deletion using an empty email — DB function handles it safely.
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(
                status_code=404,
                detail=f"User '{learner_id}' not found."
            )

    try:
        from app.db import delete_account as _del_db
        summary = _del_db(learner_id, email)
    except Exception as exc:
        logger.error("Admin account deletion failed for %s: %s", learner_id, exc)
        raise HTTPException(status_code=500, detail=f"Deletion failed: {exc}")

    # Remove from all in-memory caches immediately
    from app.progress import _store as _prog_store
    _prog_store.pop(learner_id, None)
    try:
        from app.auth import _users as _auth_users
        _auth_users.pop(learner_id, None)
    except Exception:
        pass
    try:
        from app.email_auth import _confirmed as _conf, _by_id as _bid
        if email:
            _conf.pop(email, None)
        _bid.pop(learner_id, None)
    except Exception:
        pass

    # Mirror deletion to Supabase (non-blocking, best-effort)
    try:
        from app.supabase_client import get_supabase, sb_enabled
        if sb_enabled():
            def _sb_delete():
                try:
                    sb = get_supabase()
                    sb.table("email_accounts").delete().eq("learner_id", learner_id).execute()
                    sb.table("profiles").delete().eq("id", learner_id).execute()
                    sb.table("learner_progress").delete().eq("learner_id", learner_id).execute()
                except Exception as _se:
                    logger.debug("Supabase delete failed (non-fatal): %s", _se)
            threading.Thread(target=_sb_delete, daemon=True).start()
    except Exception:
        pass

    label = email or learner_id
    log_activity("admin", "admin:delete-account", f"learner_id={learner_id} email={label}")
    return {
        "ok": True,
        "learner_id": learner_id,
        "summary": summary,
        "message": f"Account for {label} permanently deleted.",
    }


@app.get("/admin/payments")
async def admin_payments(request: Request) -> dict:
    """Return all payments including bank transfer proof-of-payment submissions."""
    _require_admin(request)
    payments = get_payments()
    # Also fetch bank transfer proofs pending review
    try:

        from app.db import get_db as _gdb
        import datetime as _dt2
        with _gdb() as _conn:
            with _conn.cursor(cursor_factory=_pge.RealDictCursor) as _cur:
                _cur.execute("""
                    SELECT * FROM bank_transfer_proofs
                    ORDER BY submitted_at DESC LIMIT 200
                """)
                proofs = [dict(r) for r in _cur.fetchall()]
        for p in proofs:
            try:
                p["submitted_at_fmt"] = _dt2.datetime.fromtimestamp(
                    float(p["submitted_at"])
                ).strftime("%Y-%m-%d %H:%M")
            except Exception:
                pass
    except Exception:
        proofs = []
    return {
        "payments":            payments,
        "bank_transfer_proofs": proofs,
        "summary":             get_revenue_summary(),
    }


@app.post("/admin/payments/add")
async def admin_add_payment(body: _PaymentAdd, request: Request) -> dict:
    _require_admin(request)
    p = add_payment(body.user_email, body.user_name, body.amount,
                    body.plan, body.method, body.notes)
    return {"ok": True, "payment_id": p.id}


@app.post("/admin/payments/confirm/{payment_id}")
async def admin_confirm_payment(payment_id: str, request: Request) -> dict:
    """Confirm a payment and auto-upgrade the learner's tier."""
    _require_admin(request)
    ok = confirm_payment(payment_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Payment not found.")
    # Auto-upgrade tier based on the confirmed payment's plan
    try:

        from app.db import get_db as _gdb, load_email_account
        with _gdb() as _conn:
            with _conn.cursor(cursor_factory=_pge.RealDictCursor) as _cur:
                _cur.execute(
                    "SELECT user_email, user_name, amount, plan, currency, id FROM payments WHERE id=%s",
                    (payment_id,)
                )
                row = _cur.fetchone()
        if row:
            # Infer tier from plan label
            plan_lower = (row["plan"] or "").lower()
            _plan_tier_map = {
                "beginner bundle": "tier1", "intermediate bundle": "tier2",
                "advanced bundle": "tier3", "premium bundle": "tier4",
                "pro learner": "tier1", "career builder": "tier2",
                "tier1": "tier1", "tier2": "tier2", "tier3": "tier3", "tier4": "tier4",
            }
            tier = None
            for k, v in _plan_tier_map.items():
                if k in plan_lower:
                    tier = v
                    break
            if not tier:
                amt = float(row["amount"] or 0)
                if amt >= 140000: tier = "tier4"
                elif amt >= 100000: tier = "tier3"
                elif amt >= 50000: tier = "tier2"
                elif amt >= 25000: tier = "tier1"
            if tier:
                acct = load_email_account(row["user_email"])
                lid  = acct["learner_id"] if acct else row["user_email"]
                from app.db import upgrade_tier_db
                from app.progress import apply_tier_upgrade
                upgrade_tier_db(lid, tier)
                apply_tier_upgrade(lid, tier)
                log_activity("admin", "payment:manual-confirm",
                             f"id={payment_id} tier={tier} email={row['user_email']}")
            # Send receipt
            from app.services.email_service import send_payment_receipt_email as _svc_pay
            _svc_pay(
                name=row["user_name"] or row["user_email"],
                email=row["user_email"],
                amount=float(row["amount"]),
                plan=row["plan"],
                payment_id=row["id"],
                currency=row["currency"] or "NGN",
            )
            from app.services.email_service import send_admin_notification as _svc_adm
            _svc_adm(
                subject=f"Payment confirmed: ?{float(row['amount']):,.0f} � {row['plan']}",
                body=f"User: {row['user_name']} ({row['user_email']})\n"
                     f"Amount: {row['currency']} {float(row['amount']):,.0f}\n"
                     f"Plan: {row['plan']}\nPayment ID: {row['id']}"
                     + (f"\nTier upgraded to: {tier}" if tier else ""),
            )
    except ImportError:
        pass   # circular import guard � tier upgrade still succeeded via upgrade_tier_db
    except Exception as _pay_exc:
        logger.warning("Post-confirm actions failed (non-fatal): %s", _pay_exc)
    return {"ok": True}


# ---------------------------------------------------------------------------
# Bank transfer proof-of-payment � upload, admin review, approve/reject
# ---------------------------------------------------------------------------

@app.get("/payments/bank-details")
async def get_bank_details() -> dict:
    """
    Return the bank account details for manual bank transfer payments.
    Reads from env vars so the admin can update them without a code deploy.
    """
    return {
        "bank_name":      _os.getenv("BANK_NAME",    "Zenith Bank Plc"),
        "account_name":   _os.getenv("BANK_ACCOUNT_NAME", "Teamsamikoko Global Academy"),
        "account_number": _os.getenv("BANK_ACCOUNT_NUMBER", "1228732577"),
        "instructions": [
            "Transfer the exact amount for your chosen plan to the account above.",
            "Use your email address as the payment reference/narration.",
            "Upload your payment receipt below immediately after transfer.",
            "Your account will be upgraded within 24 hours of admin approval.",
        ],
        "plans": [
            {"name": "Beginner Bundle",      "price": 30000,  "tier": "tier1"},
            {"name": "Intermediate Bundle",  "price": 60000,  "tier": "tier2"},
            {"name": "Advanced Bundle",      "price": 100000, "tier": "tier3"},
            {"name": "Premium Bundle",       "price": 150000, "tier": "tier4"},
        ],
    }


@app.post("/payments/bank-transfer/submit")
async def submit_bank_transfer_proof(
    request: Request,
    user=Depends(get_current_user),
) -> dict:
    """
    Learner submits bank transfer proof-of-payment.
    Accepts JSON with: plan, amount, reference, proof_image_base64 (optional),
    proof_url (optional � if hosted elsewhere), notes.
    Creates a pending bank_transfer_proofs record and notifies admin.
    """
    if not user:
        raise HTTPException(status_code=401, detail="Sign in to submit payment proof.")

    body = await request.json()
    plan    = str(body.get("plan", "")).strip()
    amount  = float(body.get("amount", 0) or 0)
    ref     = str(body.get("reference", "") or body.get("ref", "")).strip()
    proof_b64 = str(body.get("proof_image_base64", "") or "").strip()
    proof_url = str(body.get("proof_url", "") or "").strip()
    notes     = str(body.get("notes", "") or "").strip()[:500]

    if not plan:
        raise HTTPException(status_code=400, detail="Plan is required.")
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be greater than zero.")
    if not proof_b64 and not proof_url:
        raise HTTPException(status_code=400, detail="Please upload your payment receipt (image or URL).")

    # Validate proof_b64 is actually a data URL if provided
    if proof_b64 and not proof_b64.startswith("data:image/"):
        raise HTTPException(status_code=400,
            detail="proof_image_base64 must be a base64 data:image/... string.")
    if len(proof_b64) > 5_000_000:
        raise HTTPException(status_code=400, detail="Receipt image too large. Max 3.5MB.")

    import time as _t, secrets as _sec
    proof_id    = _sec.token_hex(6).upper()
    submitted_at = _t.time()
    learner_id  = user.learner_id
    email       = user.email or ""

    # Insert proof record
    try:
        from app.db import get_db as _gdb
        with _gdb() as _conn:
            with _conn.cursor() as _cur:
                _cur.execute("""
                    INSERT INTO bank_transfer_proofs
                      (id, learner_id, email, plan, amount, reference,
                       proof_b64, proof_url, notes, submitted_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """, (proof_id, learner_id, email, plan, amount,
                      ref, proof_b64, proof_url, notes, submitted_at))
    except Exception as exc:
        logger.error("Bank transfer proof save failed: %s", exc)
        raise HTTPException(status_code=500, detail="Could not save payment proof. Try again.")

    log_activity(learner_id, "payment:bank-transfer-submitted",
                 f"id={proof_id} plan={plan} amount={amount:.0f} ref={ref or 'none'}")

    # Notify admin immediately
    try:
        from app.services.email_service import send_admin_notification
        import datetime as _dt3
        send_admin_notification(
            subject=f"Bank Transfer Proof Submitted � ?{amount:,.0f} ({plan})",
            body=(
                f"Learner: {user.name} ({email})\n"
                f"Learner ID: {learner_id}\n"
                f"Plan: {plan}\n"
                f"Amount: ?{amount:,.0f}\n"
                f"Reference: {ref or '�'}\n"
                f"Notes: {notes or '�'}\n"
                f"Proof ID: {proof_id}\n"
                f"Submitted: {_dt3.datetime.fromtimestamp(submitted_at).strftime('%Y-%m-%d %H:%M UTC')}\n\n"
                f"Review and approve at: {_os.getenv('FRONTEND_URL', 'https://mypytutor.com.ng')}/admin"
                + (f"\n\nProof URL: {proof_url}" if proof_url else "")
            ),
        )
    except Exception as _ne:
        logger.debug("Admin notification for bank proof failed (non-fatal): %s", _ne)

    return {
        "ok":         True,
        "proof_id":   proof_id,
        "status":     "pending",
        "message":    "Payment proof submitted successfully! Your account will be upgraded within 24 hours after admin review.",
    }


@app.get("/payments/bank-transfer/status/{learner_id}")
async def get_bank_transfer_status(
    learner_id: str,
    user=Depends(get_current_user),
) -> dict:
    """Return all bank transfer proof submissions for a learner."""
    validate_learner_id(learner_id)
    if not user:
        raise HTTPException(status_code=401, detail="Sign in to check payment status.")
    if user.learner_id != learner_id:
        raise HTTPException(status_code=403, detail="You can only view your own payment status.")
    try:

        import datetime as _dt4
        from app.db import get_db as _gdb
        with _gdb() as _conn:
            with _conn.cursor(cursor_factory=_pge.RealDictCursor) as _cur:
                _cur.execute("""
                    SELECT id, plan, amount, reference, proof_url, status,
                           admin_notes, submitted_at, reviewed_at
                    FROM bank_transfer_proofs
                    WHERE learner_id=%s
                    ORDER BY submitted_at DESC
                """, (learner_id,))
                rows = _cur.fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d.pop("proof_b64", None)   # never return raw base64 in list
            try:
                d["submitted_at_fmt"] = _dt4.datetime.fromtimestamp(
                    float(d["submitted_at"])).strftime("%Y-%m-%d %H:%M")
            except Exception:
                pass
            if d.get("reviewed_at"):
                try:
                    d["reviewed_at_fmt"] = _dt4.datetime.fromtimestamp(
                        float(d["reviewed_at"])).strftime("%Y-%m-%d %H:%M")
                except Exception:
                    pass
            result.append(d)
        return {"proofs": result, "total": len(result)}
    except Exception as exc:
        logger.warning("get_bank_transfer_status error: %s", exc)
        return {"proofs": [], "total": 0}


@app.post("/admin/payments/bank-transfer/{proof_id}/approve")
async def admin_approve_bank_transfer(
    proof_id: str,
    request: Request,
) -> dict:
    """
    Admin approves a bank transfer proof � upgrades the learner's tier
    and sends a confirmation email.
    """
    _require_admin(request)
    body        = await request.json()
    admin_notes = str(body.get("notes", "") or "").strip()[:500]

    import time as _t2, psycopg2.extras as _pge, datetime as _dt5
    from app.db import get_db as _gdb, load_email_account, upgrade_tier_db
    from app.progress import apply_tier_upgrade

    try:
        with _gdb() as _conn:
            with _conn.cursor(cursor_factory=_pge.RealDictCursor) as _cur:
                _cur.execute(
                    "SELECT * FROM bank_transfer_proofs WHERE id=%s", (proof_id,)
                )
                proof = _cur.fetchone()
        if not proof:
            raise HTTPException(status_code=404, detail="Proof not found.")
        proof = dict(proof)
        if proof["status"] == "approved":
            return {"ok": True, "message": "Already approved.", "already_approved": True}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"DB error: {exc}")

    # Mark approved
    try:
        with _gdb() as _conn:
            with _conn.cursor() as _cur:
                _cur.execute("""
                    UPDATE bank_transfer_proofs
                    SET status='approved', admin_notes=%s, reviewed_at=%s
                    WHERE id=%s
                """, (admin_notes, _t2.time(), proof_id))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Could not update proof: {exc}")

    # Infer tier from plan
    plan_lower = (proof["plan"] or "").lower()
    tier_map   = {
        "beginner":     "tier1", "tier1": "tier1",
        "intermediate": "tier2", "tier2": "tier2",
        "advanced":     "tier3", "tier3": "tier3",
        "premium":      "tier4", "tier4": "tier4",
    }
    tier = next((v for k, v in tier_map.items() if k in plan_lower), None)
    if not tier:
        amt = float(proof.get("amount") or 0)
        if amt >= 140000: tier = "tier4"
        elif amt >= 100000: tier = "tier3"
        elif amt >= 50000: tier = "tier2"
        elif amt >= 25000: tier = "tier1"
        else: tier = "tier1"

    learner_id = proof["learner_id"]
    upgrade_tier_db(learner_id, tier)
    apply_tier_upgrade(learner_id, tier)

    # Record in payments table too
    from app.admin import add_payment, confirm_payment as _cfp
    import secrets as _sec2
    p = add_payment(
        user_email=proof["email"],
        user_name=proof.get("email", "").split("@")[0],
        amount=float(proof["amount"]),
        plan=proof["plan"],
        method="bank_transfer",
        notes=f"Proof ID: {proof_id}" + (f" | {admin_notes}" if admin_notes else ""),
    )
    _cfp(p.id)

    log_activity("admin", "payment:bank-transfer-approved",
                 f"proof={proof_id} learner={learner_id} tier={tier}")

    # Notify learner
    try:
        from app.services.email_service import send_payment_receipt_email
        send_payment_receipt_email(
            name=proof["email"].split("@")[0],
            email=proof["email"],
            amount=float(proof["amount"]),
            plan=proof["plan"],
            payment_id=p.id,
            currency="NGN",
        )
    except Exception as _ne2:
        logger.debug("Approval email failed (non-fatal): %s", _ne2)

    tier_labels = {"tier1": "Beginner Bundle", "tier2": "Intermediate Bundle",
                   "tier3": "Advanced Bundle", "tier4": "Premium Bundle"}
    return {
        "ok":        True,
        "proof_id":  proof_id,
        "tier":      tier,
        "tier_label": tier_labels.get(tier, tier),
        "message":   f"Bank transfer approved. {proof['email']} upgraded to {tier_labels.get(tier, tier)}.",
    }


@app.post("/admin/payments/bank-transfer/{proof_id}/reject")
async def admin_reject_bank_transfer(
    proof_id: str,
    request: Request,
) -> dict:
    """Admin rejects a bank transfer proof with a reason."""
    _require_admin(request)
    body        = await request.json()
    reason      = str(body.get("reason", "Payment proof could not be verified.")).strip()[:500]

    import time as _t3, psycopg2.extras as _pge2
    from app.db import get_db as _gdb

    try:
        with _gdb() as _conn:
            with _conn.cursor(cursor_factory=_pge2.RealDictCursor) as _cur:
                _cur.execute("SELECT * FROM bank_transfer_proofs WHERE id=%s", (proof_id,))
                proof = _cur.fetchone()
        if not proof:
            raise HTTPException(status_code=404, detail="Proof not found.")
        proof = dict(proof)
        with _gdb() as _conn:
            with _conn.cursor() as _cur:
                _cur.execute("""
                    UPDATE bank_transfer_proofs
                    SET status='rejected', admin_notes=%s, reviewed_at=%s
                    WHERE id=%s
                """, (reason, _t3.time(), proof_id))
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"DB error: {exc}")

    log_activity("admin", "payment:bank-transfer-rejected",
                 f"proof={proof_id} reason={reason[:80]}")

    # Notify learner of rejection
    try:
        from app.services.email_service import _dispatch_async, _shell, _box, PRIMARY
        body_html = (
            f"<p style='color:#1e293b;margin:0 0 12px;'>Hi,</p>"
            f"<h2 style='color:#DC2626;font-size:1.1rem;margin:0 0 12px;'>&#10060; Bank Transfer Not Verified</h2>"
            f"<p style='color:#475569;line-height:1.7;margin:0 0 16px;'>"
            f"We were unable to verify your bank transfer for <strong>{proof['plan']}</strong>.</p>"
            + _box(f"<strong>Reason:</strong> {reason}", bg="#fff1f2", border="#DC2626")
            + f"<p style='color:#475569;line-height:1.7;margin:0;'>"
              f"Please transfer again and re-upload your receipt, or contact support.</p>"
        )
        html = _shell(body_html, "Bank transfer could not be verified.")
        text = (f"Hi,\n\nYour bank transfer for {proof['plan']} could not be verified.\n"
                f"Reason: {reason}\n\nPlease try again or contact support.\n\n� MyPy Tutor Team")
        _dispatch_async(proof["email"],
                        "Bank Transfer � Action Required",
                        html, text, "bank_transfer_rejected")
    except Exception as _ne3:
        logger.debug("Rejection email failed (non-fatal): %s", _ne3)

    return {
        "ok":       True,
        "proof_id": proof_id,
        "message":  f"Proof {proof_id} rejected. Learner notified.",
    }


@app.get("/admin/certificates")
async def admin_certificates(request: Request) -> dict:
    """Return certificates from SQLite with correct issue dates."""
    _require_admin(request)
    from app.admin import get_certificates as _get_certs
    certs = _get_certs()   # always returns list[dict] with ISO issued_at
    return {"certificates": certs, "total": len(certs)}

@app.get("/admin/team")
async def admin_team(request: Request) -> dict:
    """Return team members and tasks � both from SQLite (persistent)."""
    _require_admin(request)
    from app.admin import get_team as _get_team, get_tasks as _get_tasks
    return {
        "members": _get_team(),   # list[dict] from SQLite
        "tasks":   _get_tasks(),  # list[dict] from SQLite
    }


@app.post("/admin/team/invite")
async def admin_invite_team(body: _TeamInvite, request: Request) -> dict:
    _require_admin(request)
    m = invite_team_member(body.email, body.name, body.role)
    try:
        from app.services.email_service import _dispatch_async, _shell, _cta, _box, PRIMARY, GOLD
        frontend_url = _os.getenv("FRONTEND_URL", "https://mypytutor.com.ng")
        role_label   = body.role.replace("_", " ").title()
        body_html = (
            f"<p style='color:#1e293b;margin:0 0 12px;'>Hi <strong>{body.name}</strong>,</p>"
            f"<h2 style='color:{PRIMARY};font-size:1.2rem;margin:0 0 12px;'>&#127881; You've been invited to the MyPy Tutor Team!</h2>"
            f"<p style='color:#475569;line-height:1.7;margin:0 0 16px;'>"
            f"The admin has added you as a <strong style='color:{GOLD};'>{role_label}</strong> "
            f"on the <strong>MyPy Tutor</strong> platform powered by TeamTega Technologies Limited.</p>"
            + _box(
                f"<strong>Your role:</strong> {role_label}<br/>"
                f"<strong>Platform:</strong> MyPy Tutor Admin Dashboard<br/>"
                f"<strong>Access:</strong> Sign in with this email address to manage assigned features.",
                bg="#f0fdf4", border="#16A34A"
            )
            + _cta("&#128640; Access the Admin Dashboard", frontend_url)
            + f"<p style='color:#64748b;font-size:0.82rem;margin:0;'>"
              f"Questions? Reply to this email.<br/>"
              f"<strong style='color:{PRIMARY};'>The MyPy Tutor Team</strong></p>"
        )
        html = _shell(body_html, f"You've been invited to the MyPy Tutor team as {role_label}.")
        text = (
            f"Hi {body.name},\n\n"
            f"You've been invited to the MyPy Tutor team as {role_label}.\n\n"
            f"Access the platform at: {frontend_url}\n\n"
            f"Sign in with this email address to manage your assigned features.\n\n"
            f"� The MyPy Tutor Team\nPowered by TeamTega Technologies Limited"
        )
        _dispatch_async(
            body.email,
            f"You're invited to join the MyPy Tutor team as {role_label}",
            html, text,
            "team_invite",
        )
        logger.info("Team invite email sent to %s (%s)", body.email, role_label)
    except Exception as e:
        logger.warning("Team invite email failed: %s", e)
    return {"ok": True, "member": {"email": m.email, "name": m.name, "role": m.role}}


@app.post("/admin/tasks/create")
async def admin_create_task(body: _TaskCreate, request: Request) -> dict:
    _require_admin(request)
    t = create_task(body.title, body.description, body.assigned_to, body.priority, body.due_date)
    try:
        from app.services.email_service import send_task_assigned_email as _ste
        _frontend_url = _os.getenv("FRONTEND_URL", _os.getenv("APP_URL", "https://mypytutor.com.ng"))
        _ste(
            assigned_to=body.assigned_to,
            title=body.title,
            description=body.description,
            priority=body.priority,
            due_date=body.due_date or "",
            platform_url=_frontend_url,
        )
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
    from app.feedback import get_summary as _gs
    from app.db import get_db as _gdb

    # Always read from PostgreSQL so data survives Render restarts.
    # In-memory _ratings / _surveys lists are empty after every restart.
    recent_ratings: list[dict] = []
    recent_surveys: list[dict] = []
    try:
        with _gdb() as _conn:
            with _conn.cursor(cursor_factory=_pge.RealDictCursor) as _cur:
                _cur.execute(
                    "SELECT learner_id, rating, intent, topic, comment "
                    "FROM feedback_ratings ORDER BY id DESC LIMIT 20"
                )
                recent_ratings = [dict(r) for r in _cur.fetchall()]

                _cur.execute(
                    "SELECT learner_id, overall, clarity, helpfulness, "
                    "suggestion, would_recommend "
                    "FROM feedback_surveys ORDER BY id DESC LIMIT 20"
                )
                recent_surveys = [dict(r) for r in _cur.fetchall()]
    except Exception as _fe:
        logger.warning("admin_feedback DB query failed (non-fatal): %s", _fe)

    return {
        "summary":        _gs().model_dump(),
        "recent_ratings": recent_ratings,
        "recent_surveys": recent_surveys,
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


@app.get("/admin/referrals")
async def admin_referrals(request: Request) -> dict:
    """Admin: all referral codes with usage stats and bonus balances."""
    _require_admin(request)
    from app.db import get_db as _gdb, get_referral_uses

    import datetime as _dt
    with _gdb() as _conn:
        with _conn.cursor(cursor_factory=_pge.RealDictCursor) as _cur:
            _cur.execute("SELECT * FROM referrals ORDER BY uses DESC")
            refs = _cur.fetchall()
    result = []
    for r in refs:
        d = dict(r)
        d["created_at_fmt"] = _dt.datetime.fromtimestamp(d["created_at"]).strftime("%Y-%m-%d")
        d["bonus_balance"]  = round(d.get("bonus_balance", 0), 2)
        uses = get_referral_uses(d["code"])
        total_referee_discount = sum(u.get("referee_discount", 0) for u in uses)
        total_referrer_bonus   = sum(u.get("referrer_bonus", 0) for u in uses)
        d["total_referee_discount"] = round(total_referee_discount, 2)
        d["total_referrer_bonus"]   = round(total_referrer_bonus, 2)
        d["recent_uses"] = uses[:5]
        result.append(d)
    total_bonus_outstanding = sum(r["bonus_balance"] for r in result)
    return {
        "referrals":               result,
        "total":                   len(result),
        "total_bonus_outstanding": round(total_bonus_outstanding, 2),
        "split_info":              "5% discount to referee � 15% bonus to referrer",
    }


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


@app.get("/admin/announce/history")
async def admin_announce_history(request: Request) -> dict:
    """Return all sent announcements from SQLite (persistent across restarts)."""
    _require_admin(request)
    from app.admin import get_announcements
    announcements = get_announcements()
    return {"announcements": announcements, "total": len(announcements)}


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
    Test email delivery. Tries Resend then SMTP, each with a hard 12s timeout.
    Returns per-provider results so you can see exactly which one failed and why.
    POST body: { "to": "recipient@email.com" }
    """
    _require_admin(request)
    body = await request.json()
    to   = body.get("to", "").strip()
    if not to or "@" not in to:
        raise HTTPException(status_code=400, detail="Provide a valid 'to' email address.")

    resend_key = _os.getenv("RESEND_API_KEY", "")
    email_user = _os.getenv("EMAIL_USER", "")
    email_pass = _os.getenv("EMAIL_PASS", "")
    email_from = _os.getenv("EMAIL_FROM", "")
    email_host = _os.getenv("EMAIL_HOST", "smtp.gmail.com")
    email_port = _os.getenv("EMAIL_PORT", "587")
    app_url    = _os.getenv("APP_URL", "not set")

    # -- Email_FROM diagnostic -----------------------------------------------
    # Common misconfiguration: EMAIL_FROM="MyPy Tutor" (no angle-bracket address)
    from_has_address = "<" in email_from and "@" in email_from
    from_warning = "" if from_has_address else (
        "EMAIL_FROM is missing the email address. "
        "Set it to: MyPy Tutor <noreply@mypytutor.com.ng>"
    )

    config_status = {
        "RESEND_API_KEY": f"? set ({len(resend_key)} chars)" if resend_key else "? NOT SET",
        "EMAIL_FROM":     email_from if email_from else "? NOT SET",
        "EMAIL_FROM_OK":  "? valid format" if from_has_address else "?? " + from_warning,
        "EMAIL_USER":     email_user if email_user else "? NOT SET",
        "EMAIL_PASS":     f"? set ({len(email_pass)} chars)" if email_pass else "? NOT SET",
        "EMAIL_HOST":     email_host,
        "EMAIL_PORT":     email_port,
        "APP_URL":        app_url,
        "provider_chain": "Resend ? SMTP fallback",
    }

    import queue as _q, threading as _thr

    # Build test email HTML/text once
    test_html = (
        "<h2 style='color:#0D47A1;margin:0 0 12px;'>&#129514; Email Delivery Test</h2>"
        "<p style='color:#16A34A;font-weight:700;font-size:1.05rem;'>&#9989; Email delivery is working!</p>"
        "<p style='color:#475569;margin-top:8px;'>Sent to: " + to + "</p>"
    )
    try:
        from app.services.email_service import _shell
        test_html_full = _shell(test_html, "MyPy Tutor - email delivery is working!")
    except Exception:
        test_html_full = "<html><body>" + test_html + "</body></html>"
    test_txt = "MyPy Tutor email delivery test - sent to: " + to

    results = {}

    # -- 1. Test Resend (12s hard timeout, NO retry) -------------------------
    if resend_key:
        resend_q: _q.Queue = _q.Queue()
        def _try_resend():
            try:
                import httpx
                r = httpx.post(
                    "https://api.resend.com/emails",
                    headers={"Authorization": "Bearer " + resend_key,
                             "Content-Type": "application/json"},
                    json={
                        "from":     email_from if from_has_address else "MyPy Tutor <onboarding@resend.dev>",
                        "to":       [to],
                        "subject":  "MyPy Tutor � Email Delivery Test",
                        "html":     test_html_full,
                        "text":     test_txt,
                    },
                    timeout=10,
                )
                if r.status_code in (200, 201):
                    resend_q.put((True, ""))
                else:
                    resend_q.put((False, f"HTTP {r.status_code}: {r.text[:300]}"))
            except Exception as exc:
                resend_q.put((False, str(exc)[:300]))

        rt = _thr.Thread(target=_try_resend, daemon=True)
        rt.start()
        rt.join(timeout=12)
        if not resend_q.empty():
            ok_r, err_r = resend_q.get()
            results["resend"] = {"ok": ok_r, "error": err_r if not ok_r else ""}
        else:
            results["resend"] = {"ok": False, "error": "Timed out after 12s"}
    else:
        results["resend"] = {"ok": False, "error": "RESEND_API_KEY not set"}

    # If Resend succeeded, return immediately � no need to test SMTP
    if results["resend"]["ok"]:
        return {
            "ok": True, "sent": True, "provider_used": "resend",
            "to": to, "config": config_status, "results": results,
        }

    # -- 2. Test SMTP fallback (12s hard timeout) ----------------------------
    smtp_q: _q.Queue = _q.Queue()
    def _try_smtp():
        if not email_user or not email_pass:
            smtp_q.put((False, "EMAIL_USER or EMAIL_PASS not set"))
            return
        import smtplib
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        # Auto-repair EMAIL_FROM if malformed
        ef = email_from.strip()
        if not from_has_address:
            ef = f"MyPy Tutor <{email_user}>"
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = "MyPy Tutor � Email Delivery Test"
            msg["From"]    = ef
            msg["To"]      = to
            msg["Reply-To"] = email_user
            msg.attach(MIMEText(test_txt, "plain", "utf-8"))
            msg.attach(MIMEText(test_html_full, "html", "utf-8"))
            with smtplib.SMTP(email_host, int(email_port), timeout=10) as server:
                server.ehlo(); server.starttls(); server.ehlo()
                server.login(email_user, email_pass)
                server.sendmail(email_user, [to], msg.as_string())
            smtp_q.put((True, ""))
        except smtplib.SMTPAuthenticationError as exc:
            smtp_q.put((False,
                f"AUTH FAILED: {exc} � "
                "EMAIL_PASS must be a Gmail App Password (16 chars). "
                "Create at myaccount.google.com/apppasswords"))
        except smtplib.SMTPException as exc:
            smtp_q.put((False, f"SMTP error: {exc}"))
        except Exception as exc:
            smtp_q.put((False, f"{type(exc).__name__}: {exc}"))

    st = _thr.Thread(target=_try_smtp, daemon=True)
    st.start()
    st.join(timeout=12)
    if not smtp_q.empty():
        ok_s, err_s = smtp_q.get()
        results["smtp"] = {"ok": ok_s, "error": err_s if not ok_s else ""}
    else:
        results["smtp"] = {"ok": False, "error": "Timed out after 12s � check EMAIL_HOST/PORT"}

    if results["smtp"]["ok"]:
        return {
            "ok": True, "sent": True, "provider_used": "smtp",
            "to": to, "config": config_status, "results": results,
        }

    # -- Both failed � return detailed per-provider errors -------------------
    # Build a human-readable diagnosis
    resend_err = results["resend"]["error"]
    smtp_err   = results["smtp"]["error"]

    diagnosis = []
    if "domain" in resend_err.lower() or "not verified" in resend_err.lower():
        diagnosis.append("Resend: your sending domain is not verified. "
                         "Go to resend.com/domains and add mypytutor.com.ng")
    elif "api" in resend_err.lower() or "401" in resend_err or "403" in resend_err:
        diagnosis.append("Resend: API key is invalid or revoked. "
                         "Re-copy it from resend.com/api-keys")
    elif resend_err:
        diagnosis.append("Resend: " + resend_err)

    if "auth failed" in smtp_err.lower():
        diagnosis.append("SMTP: Gmail App Password is wrong � re-create at "
                         "myaccount.google.com/apppasswords")
    elif smtp_err:
        diagnosis.append("SMTP: " + smtp_err)

    if not diagnosis:
        diagnosis = ["Both providers failed. Check Render logs for more detail."]

    return {
        "ok": False, "sent": False,
        "to": to, "config": config_status, "results": results,
        "error": " | ".join(diagnosis),
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
async def prompt_history(learner_id: str, limit: int = 20,
                         user=Depends(get_current_user)) -> dict:
    validate_learner_id(learner_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Sign in to view your learning history.")
    if user.learner_id != learner_id:
        raise HTTPException(status_code=403, detail="You can only view your own history.")
    limit   = max(1, min(limit, 50))
    history = get_prompt_history(learner_id, limit)
    return {"learner_id": learner_id, "history": history, "count": len(history)}


@app.get("/history/{learner_id}/quiz")
async def quiz_history(learner_id: str, limit: int = 50,
                       user=Depends(get_current_user)) -> dict:
    validate_learner_id(learner_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Sign in to view your quiz history.")
    if user.learner_id != learner_id:
        raise HTTPException(status_code=403, detail="You can only view your own quiz history.")
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
async def generate_assignment(learner_id: str, topic: str,
                              user=Depends(get_current_user)) -> dict:
    validate_learner_id(learner_id)
    validate_topic(topic)
    if user is None:
        raise HTTPException(status_code=401, detail="Sign in to generate assignments.")
    if user.learner_id != learner_id:
        raise HTTPException(status_code=403, detail="learner_id does not match your session.")
    import secrets as _sec
    profile = get_profile(learner_id)

    system_prompt = build_system_prompt("exercise", topic=topic, level=profile.level)
    messages = [{"role": "user", "content": (
        f"Create a detailed coding assignment on '{topic}'. "
        f"Include: title, clear description, requirements (3-5 bullet points), "
        f"expected output, and evaluation criteria. Format it clearly."
    )}]
    try:
        content = get_completion(system_prompt, messages, intent="exercise")
    except Exception as exc:
        logger.error("Assignment gen error: %s", exc)
        raise HTTPException(status_code=502, detail="AI service error. Please try again.")

    assignment_id = _sec.token_hex(8).upper()
    title = f"{topic} � Coding Assignment"
    create_assignment_db(assignment_id, learner_id, title, content)
    log_activity(learner_id, "assignment:generated", f"topic={topic}")
    return {"assignment_id": assignment_id, "learner_id": learner_id,
            "topic": topic, "title": title, "content": content}


@app.post("/assignments/{assignment_id}/submit")
async def submit_assignment(assignment_id: str, body: AssignmentSubmit,
                            user=Depends(get_current_user)) -> dict:
    validate_learner_id(body.learner_id)
    # Owner check: prevent submitting assignments on behalf of another user
    if user is None:
        raise HTTPException(status_code=401, detail="Sign in to submit assignments.")
    if user.learner_id != body.learner_id:
        raise HTTPException(status_code=403, detail="You can only submit your own assignments.")
    ok = submit_assignment_db(assignment_id, body.learner_id, body.submission)
    if not ok:
        raise HTTPException(status_code=404, detail="Assignment not found.")
    log_activity(body.learner_id, "assignment:submitted", f"id={assignment_id}")
    return {"ok": True, "message": "Assignment submitted successfully."}


@app.post("/assignments/{assignment_id}/review")
async def ai_review_assignment(assignment_id: str, learner_id: str,
                               user=Depends(get_current_user)) -> dict:
    validate_learner_id(learner_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Sign in to request assignment review.")
    if user.learner_id != learner_id:
        raise HTTPException(status_code=403, detail="You can only review your own assignments.")
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
        content = get_completion(system_prompt, messages, intent="debug")
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
async def list_assignments(learner_id: str,
                           user=Depends(get_current_user)) -> dict:
    validate_learner_id(learner_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Sign in to view assignments.")
    if user.learner_id != learner_id:
        raise HTTPException(status_code=403, detail="You can only view your own assignments.")
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
                                      {"type":"article", "label":"Real Python � Variables",           "url":"https://realpython.com/python-variables/"}],
    "Python Data Types":             [{"type":"docs",    "label":"W3Schools Data Types",              "url":"https://www.w3schools.com/python/python_datatypes.asp"}],
    "Python Strings":                [{"type":"docs",    "label":"W3Schools Strings",                 "url":"https://www.w3schools.com/python/python_strings.asp"},
                                      {"type":"article", "label":"Real Python � Strings",             "url":"https://realpython.com/python-strings/"}],
    "Python Lists":                  [{"type":"docs",    "label":"W3Schools Lists",                   "url":"https://www.w3schools.com/python/python_lists.asp"}],
    "Python Dictionaries":           [{"type":"docs",    "label":"W3Schools Dictionaries",            "url":"https://www.w3schools.com/python/python_dictionaries.asp"}],
    "Python Functions":              [{"type":"docs",    "label":"W3Schools Functions",               "url":"https://www.w3schools.com/python/python_functions.asp"},
                                      {"type":"article", "label":"Real Python � Functions",           "url":"https://realpython.com/defining-your-own-python-function/"}],
    "Classes and Objects":           [{"type":"docs",    "label":"W3Schools OOP",                     "url":"https://www.w3schools.com/python/python_classes.asp"},
                                      {"type":"article", "label":"Real Python � OOP",                 "url":"https://realpython.com/python3-object-oriented-programming/"}],
    "Python Inheritance":            [{"type":"docs",    "label":"W3Schools Inheritance",             "url":"https://www.w3schools.com/python/python_inheritance.asp"}],
    "Python RegEx":                  [{"type":"docs",    "label":"W3Schools RegEx",                   "url":"https://www.w3schools.com/python/python_regex.asp"},
                                      {"type":"tool",    "label":"Regex101 � Live tester",            "url":"https://regex101.com/"}],
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
    {"type":"tool",  "label":"Python Tutor � Visualiser",     "url":"https://pythontutor.com/"},
]


@app.get("/lessons/resources")
async def lesson_resources(topic: str = "") -> dict:
    resources = _LESSON_RESOURCES.get(topic, _DEFAULT_RESOURCES)
    return {"topic": topic, "resources": resources, "count": len(resources)}


# ---------------------------------------------------------------------------
# COUPON routes
# ---------------------------------------------------------------------------

@app.post("/coupons/validate")
async def validate_coupon(body: CouponValidate,
                          user=Depends(get_current_user)) -> dict:
    """
    Validate a coupon code. Works authenticated or unauthenticated.
    Unauthenticated calls get valid/invalid + discount info only (no use recorded).
    """
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
async def apply_coupon(body: CouponValidate,
                       user=Depends(get_current_user)) -> dict:
    """Apply a coupon to a learner. Requires authentication."""
    if not user:
        raise HTTPException(status_code=401, detail="Sign in to apply a coupon.")
    if not body.learner_id or not body.email:
        raise HTTPException(status_code=400, detail="learner_id and email required.")
    # Prevent recording a coupon use on behalf of another learner
    if user.learner_id != body.learner_id:
        raise HTTPException(status_code=403, detail="learner_id does not match your session.")
    coupon = validate_coupon_db(body.code, body.plan)
    if not coupon:
        raise HTTPException(status_code=404, detail="Coupon is invalid or exhausted.")

    # Calculate real savings � handle both flat and percentage discounts
    disc_pct   = int(coupon.get("discount_pct") or 0)
    disc_flat  = float(coupon.get("discount_flat") or 0.0)
    # For percentage coupons, savings is recorded as 0 until applied to an actual
    # payment amount (the webhook will record the real value). For flat coupons
    # we store the flat amount immediately.
    savings = disc_flat if disc_flat > 0 else 0.0

    use_coupon_db(body.code, body.learner_id, body.email, savings)
    log_activity(body.learner_id, "coupon:applied", f"code={body.code} disc_pct={disc_pct}% disc_flat={disc_flat}")

    msg = "Coupon applied!"
    if disc_pct:
        msg = f"Coupon applied! {disc_pct}% discount will be deducted at checkout."
    elif disc_flat:
        msg = f"Coupon applied! ?{disc_flat:,.0f} discount will be deducted at checkout."

    return {
        "ok":            True,
        "code":          coupon["code"],
        "discount_pct":  disc_pct,
        "discount_flat": disc_flat,
        "message":       msg,
    }


# ---------------------------------------------------------------------------
# REFERRAL routes
# ---------------------------------------------------------------------------

# REFERRAL routes � specific paths BEFORE dynamic /{learner_id}
@app.get("/referral/balance/{learner_id}")
async def referral_balance(learner_id: str,
                           user=Depends(get_current_user)) -> dict:
    """Return referral bonus balance and earnings history. Owner-only."""
    validate_learner_id(learner_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Sign in to view your referral balance.")
    if user.learner_id != learner_id:
        raise HTTPException(status_code=403, detail="You can only view your own referral balance.")
    return get_referral_bonus_balance(learner_id)


@app.get("/referral/{learner_id}")
async def get_my_referral(learner_id: str,
                          user=Depends(get_current_user)) -> dict:
    validate_learner_id(learner_id)
    # Referral code and earnings are owner-only data
    if user is None:
        raise HTTPException(status_code=401, detail="Sign in to view your referral code.")
    if user.learner_id != learner_id:
        raise HTTPException(status_code=403, detail="You can only view your own referral code.")
    existing = get_learner_referral_code(learner_id)
    if existing:
        uses = get_referral_uses(existing["code"])
        # Use the authoritative `uses` counter from the referrals table.
        # It is incremented atomically by use_referral_code() on every signup.
        # len(uses) from referral_uses rows can be lower if rows weren't written.
        authoritative_total = existing.get("uses", 0)
        paid_uses   = [u for u in uses if (u.get("referrer_bonus") or 0) > 0]
        unpaid_uses = [u for u in uses if (u.get("referrer_bonus") or 0) == 0]
        # Reconcile: if SQLite rows > authoritative counter, the counter needs updating
        if len(uses) > authoritative_total:
            authoritative_total = len(uses)
        paid_count   = len(paid_uses)
        unpaid_count = authoritative_total - paid_count
        if unpaid_count < 0:
            unpaid_count = 0
        return {
            "code":             existing["code"],
            "uses":             authoritative_total,
            "max_uses":         existing["max_uses"],
            "bonus_balance":    round(existing.get("bonus_balance", 0), 2),
            "paid_referrals":   paid_count,
            "unpaid_referrals": unpaid_count,
            "total_referrals":  authoritative_total,
            "recent_uses":      uses[:20],
        }
    import secrets as _sec
    code    = _sec.token_hex(4).upper()
    profile = get_profile(learner_id)
    email   = profile.email or learner_id
    create_referral_code(code, learner_id, email)
    threading.Thread(
        target=_mirror_referral_code_to_supabase,
        args=(code, learner_id, email),
        daemon=False,
    ).start()
    return {
        "code": code, "uses": 0, "max_uses": 50, "bonus_balance": 0.0,
        "paid_referrals": 0, "unpaid_referrals": 0, "total_referrals": 0,
        "recent_uses": [],
    }


@app.post("/referral/use")
async def use_referral(body: ReferralUse,
                       user=Depends(get_current_user)) -> dict:
    """
    Record that a new user signed up with a referral code.
    Requires auth � learner_id in body must match session token to prevent
    fake referral use records.
    """
    # Require auth: only the signed-up user can record their own referral use
    if user is None:
        raise HTTPException(status_code=401, detail="Sign in to apply a referral code.")
    if user.learner_id != body.learner_id:
        raise HTTPException(status_code=403, detail="learner_id does not match your session.")
    ref = get_referral_code(body.code)
    if not ref or ref["uses"] >= ref["max_uses"]:
        raise HTTPException(status_code=404, detail="Referral code is invalid or exhausted.")
    payment_amount = getattr(body, 'payment_amount', 0) or 0
    ok = use_referral_code(body.code, body.email, body.learner_id,
                           discount_pct=5, payment_amount=payment_amount)
    if not ok:
        raise HTTPException(status_code=400, detail="Could not apply referral code.")
    log_activity(body.learner_id, "referral:used", f"code={body.code}")
    return {
        "ok": True,
        "discount_pct": 5,
        "message": "Referral applied! You get 5% off your first payment.",
    }


@app.post("/referral/withdraw")
async def request_referral_withdrawal(body: _ReferralWithdraw,
                                       user=Depends(get_current_user)) -> dict:
    """Create a referral payout request. Requires authentication as the owner."""
    if user is None:
        raise HTTPException(status_code=401, detail="Sign in to request a withdrawal.")
    if user.learner_id != body.learner_id:
        raise HTTPException(status_code=403, detail="You can only withdraw your own referral balance.")

    validate_learner_id(body.learner_id)
    balance = get_referral_bonus_balance(body.learner_id).get("balance", 0.0)

    if body.amount <= 0:
        raise HTTPException(status_code=400, detail="Withdrawal amount must be greater than zero.")
    if body.amount > balance:
        raise HTTPException(status_code=400, detail="Withdrawal amount exceeds available referral balance.")

    if not body.bank_name.strip() or not body.account_name.strip() or not body.account_num.strip():
        raise HTTPException(status_code=400, detail="Bank name, account name, and account number are required.")

    try:
        withdrawal_id = create_withdrawal_request(
            learner_id=body.learner_id,
            email=body.email,
            amount=float(body.amount),
            bank_name=body.bank_name.strip(),
            account_name=body.account_name.strip(),
            account_num=body.account_num.strip(),
        )
    except ValueError as _ve:
        # DB-level race guard: concurrent requests depleted the balance
        raise HTTPException(status_code=400, detail=str(_ve))
    if not withdrawal_id:
        raise HTTPException(status_code=500, detail="Could not create withdrawal request.")
    log_activity(body.learner_id, "referral:withdraw-request", f"amount={body.amount}")
    return {
        "ok": True,
        "withdrawal_id": withdrawal_id,
        "message": "Withdrawal request submitted successfully.",
    }


@app.get("/referral/withdrawals/{learner_id}")
async def get_referral_withdrawals(learner_id: str,
                                   user=Depends(get_current_user)) -> dict:
    validate_learner_id(learner_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Sign in to view withdrawals.")
    if user.learner_id != learner_id:
        raise HTTPException(status_code=403, detail="You can only view your own withdrawal history.")
    rows = get_withdrawals_for_learner(learner_id)
    return {"learner_id": learner_id, "withdrawals": rows, "total": len(rows)}


# ---------------------------------------------------------------------------
# INVOICE routes
# ---------------------------------------------------------------------------

@app.get("/invoice/{invoice_id}", response_class=HTMLResponse)
async def get_invoice(invoice_id: str,
                      user=Depends(get_current_user)) -> HTMLResponse:
    """Return a printable invoice. Requires authentication � owner or admin only."""
    import re as _re4
    if not _re4.match(r'^[A-Z0-9\-]{4,30}$', invoice_id):
        raise HTTPException(status_code=400, detail="Invalid invoice ID.")
    if user is None:
        raise HTTPException(status_code=401, detail="Sign in to view invoices.")
    inv = get_invoice_db(invoice_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found.")
    # Ensure the requester owns this invoice (learner_id match)
    if inv.get("learner_id") and inv["learner_id"] != user.learner_id:
        raise HTTPException(status_code=403, detail="You can only view your own invoices.")
    return HTMLResponse(content=_render_invoice(inv))


@app.get("/invoices/{learner_id}")
async def list_invoices(learner_id: str,
                        user=Depends(get_current_user)) -> dict:
    validate_learner_id(learner_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Sign in to view invoices.")
    if user.learner_id != learner_id:
        raise HTTPException(status_code=403, detail="You can only view your own invoices.")
    invoices = get_invoices_by_learner(learner_id)
    return {"learner_id": learner_id, "invoices": invoices, "total": len(invoices)}


def _render_invoice(inv: dict) -> str:
    """Render an invoice by loading the static HTML template and substituting data fields.

    Falls back to a minimal inline HTML string if the template file is missing
    (e.g. during a unit test run without the static/ directory).
    """
    import os as _os_inv
    template_path = _os_inv.path.join("static", "invoice-template.html")
    try:
        with open(template_path, "r", encoding="utf-8") as _f:
            tpl = _f.read()
    except FileNotFoundError:
        # Minimal fallback — no CSS, just the essential data
        tpl = (
            "<!DOCTYPE html><html><head><meta charset='UTF-8'/>"
            "<title>Invoice #{{INV_ID}}</title></head><body>"
            "<h1>Invoice #{{INV_ID}}</h1>"
            "<p>{{INV_NAME}} · {{INV_EMAIL}}</p>"
            "<p>Plan: {{INV_PLAN}} · Amount: ₦{{INV_AMOUNT}} {{INV_CURRENCY}}</p>"
            "<p>Date: {{INV_DATE}} · Payment ID: {{INV_PAYMENT_ID}}</p>"
            "</body></html>"
        )

    # Format amount as comma-separated (no decimal for whole numbers)
    try:
        amount_fmt = f"{float(inv.get('amount', 0)):,.0f}"
    except (TypeError, ValueError):
        amount_fmt = str(inv.get("amount", "0"))

    return (
        tpl
        .replace("{{INV_ID}}",         str(inv.get("id", "")))
        .replace("{{INV_DATE}}",        str(inv.get("issued_at_fmt", "")))
        .replace("{{INV_NAME}}",        str(inv.get("name", "")))
        .replace("{{INV_EMAIL}}",       str(inv.get("email", "")))
        .replace("{{INV_PAYMENT_ID}}", str(inv.get("payment_id", "")))
        .replace("{{INV_PLAN}}",        str(inv.get("plan", "")))
        .replace("{{INV_AMOUNT}}",      amount_fmt)
        .replace("{{INV_CURRENCY}}",    str(inv.get("currency", "NGN")))
    )


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


@app.delete("/admin/coupons/{code}")
async def admin_delete_coupon(code: str, request: Request) -> dict:
    """Permanently delete a coupon code. Irreversible."""
    _require_admin(request)
    import re as _re6
    if not _re6.match(r'^[A-Z0-9_\-]{2,32}$', code.upper()):
        raise HTTPException(status_code=400, detail="Invalid coupon code format.")
    try:

        from app.db import get_db as _gdb
        with _gdb() as _conn:
            with _conn.cursor() as _cur:
                _cur.execute("DELETE FROM coupons WHERE code=%s", (code.upper(),))
                deleted = _cur.rowcount
        if deleted == 0:
            raise HTTPException(status_code=404, detail=f"Coupon '{code.upper()}' not found.")
        log_activity("admin", "coupon:deleted", f"code={code.upper()}")
        return {"ok": True, "code": code.upper(), "message": f"Coupon {code.upper()} deleted."}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("admin_delete_coupon error: %s", exc)
        raise HTTPException(status_code=500, detail="Could not delete coupon.")


@app.put("/admin/coupons/{code}/deactivate")
async def admin_deactivate_coupon(code: str, request: Request) -> dict:
    """Deactivate a coupon (soft disable � preserves usage history)."""
    _require_admin(request)
    try:

        from app.db import get_db as _gdb
        with _gdb() as _conn:
            with _conn.cursor() as _cur:
                _cur.execute(
                    "UPDATE coupons SET active=0 WHERE code=%s",
                    (code.upper(),)
                )
                updated = _cur.rowcount
        if updated == 0:
            raise HTTPException(status_code=404, detail=f"Coupon '{code.upper()}' not found.")
        log_activity("admin", "coupon:deactivated", f"code={code.upper()}")
        return {"ok": True, "code": code.upper(), "message": f"Coupon {code.upper()} deactivated."}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("admin_deactivate_coupon error: %s", exc)
        raise HTTPException(status_code=500, detail="Could not deactivate coupon.")


@app.put("/admin/coupons/{code}/activate")
async def admin_activate_coupon(code: str, request: Request) -> dict:
    """Re-activate a previously deactivated coupon."""
    _require_admin(request)
    try:
        from app.db import get_db as _gdb
        with _gdb() as _conn:
            with _conn.cursor() as _cur:
                _cur.execute(
                    "UPDATE coupons SET active=1 WHERE code=%s",
                    (code.upper(),)
                )
                updated = _cur.rowcount
        if updated == 0:
            raise HTTPException(status_code=404, detail=f"Coupon '{code.upper()}' not found.")
        log_activity("admin", "coupon:activated", f"code={code.upper()}")
        return {"ok": True, "code": code.upper(), "message": f"Coupon {code.upper()} activated."}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("admin_activate_coupon error: %s", exc)
        raise HTTPException(status_code=500, detail="Could not activate coupon.")

# ---------------------------------------------------------------------------
# ACCESS CODE routes � DEPRECATED
# Access codes have been removed. Use coupon codes for discounts and
# referral codes for user rewards. Any existing access codes in the DB
# will continue to be honoured at signup for backwards compatibility,
# but the admin can no longer create new ones.
# ---------------------------------------------------------------------------

@app.get("/admin/access-codes")
async def admin_list_access_codes(request: Request) -> dict:
    """Deprecated � access codes removed. Returns empty list."""
    _require_admin(request)
    return {
        "codes":      [],
        "total":      0,
        "deprecated": True,
        "message":    "Access codes have been removed. Use Coupon Codes for discounts or Referral Codes for user rewards.",
    }


@app.post("/admin/access-codes/generate")
async def admin_generate_access_code(request: Request) -> dict:
    """Deprecated � access code generation removed."""
    _require_admin(request)
    raise HTTPException(
        status_code=410,
        detail=(
            "Access codes have been removed. "
            "Create a Coupon Code at /admin/coupons/create for discounts, "
            "or share a Referral Code for user rewards."
        ),
    )


@app.get("/admin/invoices")
async def admin_invoices(request: Request) -> dict:
    _require_admin(request)
    invoices      = get_all_invoices_db()
    total_revenue = sum(i["amount"] for i in invoices)
    return {"invoices": invoices, "total": len(invoices), "total_revenue": total_revenue}


@app.get("/admin/withdrawals")
async def admin_withdrawals(request: Request) -> dict:
    """Admin: all referral withdrawal requests."""
    _require_admin(request)
    from app.db import get_all_withdrawal_requests
    rows = get_all_withdrawal_requests()
    pending = sum(1 for r in rows if r["status"] == "pending")
    return {"withdrawals": rows, "total": len(rows), "pending": pending}


@app.post("/admin/withdrawals/{withdrawal_id}/status")
async def admin_update_withdrawal(withdrawal_id: int, request: Request) -> dict:
    """Admin: approve or reject a withdrawal request."""
    _require_admin(request)
    body   = await request.json()
    status = body.get("status", "")
    notes  = body.get("notes", "")
    if status not in ("approved", "paid", "rejected"):
        raise HTTPException(status_code=400, detail="Status must be 'approved', 'paid', or 'rejected'.")
    from app.db import update_withdrawal_status
    ok = update_withdrawal_status(withdrawal_id, status, notes)
    if not ok:
        raise HTTPException(status_code=404, detail="Withdrawal request not found.")
    log_activity("admin", "withdrawal:status-update", f"id={withdrawal_id} status={status}")
    return {"ok": True, "withdrawal_id": withdrawal_id, "status": status}


@app.get("/admin/enquiries")
async def admin_enquiries_list(request: Request) -> dict:
    """Admin: list all support enquiries."""
    _require_admin(request)
    import datetime as _dt

    try:
        from app.db import get_db as _gdb
        with _gdb() as _conn:
            with _conn.cursor(cursor_factory=_pge.RealDictCursor) as _cur:
                _cur.execute("SELECT * FROM enquiries ORDER BY id DESC LIMIT 500")
                rows = _cur.fetchall()
        result = []
        for r in rows:
            d = dict(r)
            try:
                d["created_at"] = _dt.datetime.fromtimestamp(float(d["created_at"])).isoformat()
            except Exception:
                pass
            result.append(d)
        total  = len(result)
        open_  = sum(1 for x in result if x.get("status") == "open")
        closed = total - open_
        return {"enquiries": result, "total": total, "open": open_, "closed": closed}
    except Exception as e:
        logger.warning("admin_enquiries_list failed: %s", e)
        return {"enquiries": [], "total": 0, "open": 0, "closed": 0}


@app.post("/admin/enquiries/{enquiry_id}/resolve")
async def admin_resolve_enquiry(enquiry_id: int, request: Request) -> dict:
    """Admin: mark an enquiry as resolved."""
    _require_admin(request)
    try:
        from app.db import get_db as _gdb
        with _gdb() as _conn:
            with _conn.cursor() as _cur:
                _cur.execute(
                    "UPDATE enquiries SET status='resolved' WHERE id=%s", (enquiry_id,)
                )
                if _cur.rowcount == 0:
                    raise HTTPException(status_code=404, detail="Enquiry not found.")
        log_activity("admin", "enquiry:resolved", f"id={enquiry_id}")
        return {"ok": True, "enquiry_id": enquiry_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("admin_resolve_enquiry failed: %s", e)
        raise HTTPException(status_code=500, detail="Could not update enquiry.")


@app.get("/admin/history/{learner_id}")
async def admin_learner_history(learner_id: str, request: Request) -> dict:
    _require_admin(request)
    validate_learner_id(learner_id)
    history  = get_prompt_history(learner_id, 50)
    attempts = get_quiz_attempts(learner_id, 50)
    # Pull from Supabase non-blocking via thread executor
    sb_msgs: list = []
    if sb_enabled():
        try:
            import asyncio as _aio_adm
            loop = _aio_adm.get_running_loop()
            sb_msgs = await loop.run_in_executor(
                None, lambda: sb_load_messages(f"local_{learner_id}", limit=50)
            )
        except Exception:
            pass
    return {"learner_id": learner_id,
            "prompt_history": history,
            "supabase_messages": sb_msgs,
            "quiz_attempts": attempts}


# ---------------------------------------------------------------------------
# SUPABASE � Conversation & history routes
# ---------------------------------------------------------------------------

@app.get("/conversations/{learner_id}")
async def list_conversations(learner_id: str,
                             user=Depends(get_current_user)) -> dict:
    """
    Return all conversation sessions for a learner.
    Owner-only: chat history may contain sensitive personal information.
    """
    validate_learner_id(learner_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Sign in to view your conversation history.")
    if user.learner_id != learner_id:
        raise HTTPException(status_code=403, detail="You can only view your own conversations.")
    if sb_enabled():
        import asyncio as _aio_conv
        loop = _aio_conv.get_running_loop()
        convs = await loop.run_in_executor(
            None, lambda: sb_load_all_conversations(learner_id)
        )
        return {"learner_id": learner_id, "conversations": convs,
                "source": "supabase", "total": len(convs)}
    # Fallback: group SQLite history by day
    history = get_prompt_history(learner_id, 50)
    return {"learner_id": learner_id,
            "conversations": [{"id": f"local_{learner_id}", "messages": history}],
            "source": "sqlite", "total": len(history)}


@app.get("/conversations/{learner_id}/{conversation_id}")
async def get_conversation(learner_id: str, conversation_id: str,
                            limit: int = 50,
                            user=Depends(get_current_user)) -> dict:
    """
    Load all messages from a specific conversation. Owner-only.
    """
    validate_learner_id(learner_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Sign in to view conversation messages.")
    if user.learner_id != learner_id:
        raise HTTPException(status_code=403, detail="You can only view your own conversations.")
    if sb_enabled():
        import asyncio as _aio_msg
        loop = _aio_msg.get_running_loop()
        messages = await loop.run_in_executor(
            None, lambda: sb_load_messages(conversation_id, limit=min(limit, 100))
        )
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
async def new_conversation(learner_id: str, background_tasks: BackgroundTasks,
                           user=Depends(get_current_user)) -> dict:
    """Start a fresh conversation. Owner-only � requires auth."""
    validate_learner_id(learner_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Sign in to start a conversation.")
    if user.learner_id != learner_id:
        raise HTTPException(status_code=403, detail="You can only create your own conversations.")
    import secrets as _sec
    conv_id = f"local_{_sec.token_hex(8)}"
    # Fire-and-forget Supabase insert � does NOT block the response
    if sb_enabled():
        real_id = _sec.token_hex(16)
        def _insert_conv():
            try:
                from app.supabase_client import get_supabase
                sb = get_supabase()
                if sb:
                    sb.table("conversations").insert({
                        "id": real_id, "learner_id": learner_id,
                        "title": "New Conversation"
                    }).execute()
            except Exception as exc:
                logger.debug("Background conversation insert failed: %s", exc)
        background_tasks.add_task(_insert_conv)
        conv_id = real_id
    return {"conversation_id": conv_id, "learner_id": learner_id}


# ---------------------------------------------------------------------------
# SUPABASE � Status & health check
# ---------------------------------------------------------------------------

@app.get("/supabase/status")
async def supabase_status(request: Request) -> dict:
    """Check whether Supabase is configured and reachable. Admin-only � leaks infra URL."""
    _require_admin(request)
    if not sb_enabled():
        return {"enabled": False,
                "message": "Supabase not configured. Add SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in Render env vars."}
    try:
        from app.supabase_client import get_supabase
        sb = get_supabase()
        sb.table("profiles").select("id").limit(1).execute()
        return {"enabled": True, "status": "connected"}
    except Exception as exc:
        # Return generic error � do NOT expose internal connection details
        logger.warning("Supabase status check failed: %s", exc)
        return {"enabled": True, "status": "error",
                "detail": "Connection test failed � check Render logs for details."}


# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Email automation jobs
# Five targeted email jobs managed by a single unified background scheduler.
# Each job has its own cooldown tracked in the email_automation table, so
# running the scheduler every hour never causes duplicate sends.
# ---------------------------------------------------------------------------

def _run_reengagement_job() -> dict:
    """Inactive 7+ days: personalised re-engagement email. Cooldown: 6 days."""
    import time as _t, json as _json
    from app.db import get_email_automation_candidates, mark_email_sent, upsert_email_automation
    from app.services.email_service import send_reengagement_email as _re_email

    INACTIVITY_DAYS = 7
    COOLDOWN_DAYS   = 6

    sent = skipped = errors = 0
    try:
        candidates = get_email_automation_candidates("reengagement", COOLDOWN_DAYS)
    except Exception as exc:
        logger.warning("Re-engagement DB query failed: %s", exc)
        return {"sent": 0, "skipped": 0, "errors": 1, "error": str(exc)}

    cutoff = _t.time() - (INACTIVITY_DAYS * 86400)
    for row in candidates:
        try:
            email = (row.get("email") or "").strip().lower()
            name  = (row.get("name")  or email.split("@")[0]).strip()
            if not email or "@" not in email:
                skipped += 1; continue

            last_activity = row.get("last_activity_at")
            if last_activity and float(last_activity) >= cutoff:
                skipped += 1; continue

            days_inactive = int((_t.time() - float(last_activity)) / 86400) if last_activity else 8
            last_topic = ""
            try:
                topics = _json.loads(row.get("topics_seen") or "[]")
                last_topic = topics[-1] if topics else ""
            except Exception:
                pass

            upsert_email_automation(row["learner_id"], email, name)
            _re_email(name=name, email=email,
                      days_inactive=days_inactive, last_topic=last_topic,
                      xp=int(row.get("xp") or 0))
            mark_email_sent(row["learner_id"], "reengagement")
            sent += 1
            log_activity("system", "email:reengagement",
                         f"{email} ({days_inactive}d inactive)")
        except Exception as exc:
            logger.warning("Re-engagement email failed for %s: %s", row.get("email", "?"), exc)
            errors += 1

    logger.info("Re-engagement job: sent=%d skipped=%d errors=%d", sent, skipped, errors)
    return {"sent": sent, "skipped": skipped, "errors": errors, "candidates": len(candidates)}


def _run_course_reminder_job() -> dict:
    """Incomplete course + idle 3+ days: course progress nudge. Cooldown: 4 days."""
    import time as _t
    from app.db import get_email_automation_candidates, mark_email_sent, upsert_email_automation
    from app.services.email_service import send_course_reminder_email as _cr_email
    from app.progress import get_profile as _gp
    from app.courses import get_course as _gc

    IDLE_DAYS = 3; COOLDOWN_DAYS = 4
    sent = skipped = errors = 0
    cutoff = _t.time() - (IDLE_DAYS * 86400)

    try:
        candidates = get_email_automation_candidates("course_reminder", COOLDOWN_DAYS)
    except Exception as exc:
        logger.warning("Course reminder DB query failed: %s", exc)
        return {"sent": 0, "skipped": 0, "errors": 1, "error": str(exc)}

    for row in candidates:
        try:
            email = (row.get("email") or "").strip().lower()
            name  = (row.get("name")  or email.split("@")[0]).strip()
            if not email or "@" not in email:
                skipped += 1; continue

            last_activity = row.get("last_activity_at")
            if last_activity and float(last_activity) >= cutoff:
                skipped += 1; continue

            current_course = row.get("current_course") or ""
            if not current_course:
                skipped += 1; continue

            days_since = int((_t.time() - float(last_activity)) / 86400) if last_activity else IDLE_DAYS
            step = total_steps = 0
            try:
                prof  = _gp(row["learner_id"])
                step  = prof.current_course_step or 0
                co    = _gc(current_course)
                total_steps = len(co.steps) if co else 0
            except Exception:
                pass

            upsert_email_automation(row["learner_id"], email, name)
            _cr_email(name=name, email=email, course_name=current_course,
                      step=step, total_steps=total_steps, days_since_last=days_since)
            mark_email_sent(row["learner_id"], "course_reminder")
            sent += 1
            log_activity("system", "email:course_reminder", f"{email} course={current_course}")
        except Exception as exc:
            logger.warning("Course reminder failed for %s: %s", row.get("email", "?"), exc)
            errors += 1

    logger.info("Course reminder job: sent=%d skipped=%d errors=%d", sent, skipped, errors)
    return {"sent": sent, "skipped": skipped, "errors": errors, "candidates": len(candidates)}


def _run_assignment_reminder_job() -> dict:
    """Pending unsubmitted assignments: reminder email. Cooldown: 3 days."""
    import time as _t
    from app.db import (get_email_automation_candidates, mark_email_sent,
                        upsert_email_automation, get_assignments_db)
    from app.services.email_service import send_assignment_reminder_email as _ar_email

    COOLDOWN_DAYS = 3
    sent = skipped = errors = 0
    try:
        candidates = get_email_automation_candidates("assignment_reminder", COOLDOWN_DAYS)
    except Exception as exc:
        logger.warning("Assignment reminder DB query failed: %s", exc)
        return {"sent": 0, "skipped": 0, "errors": 1, "error": str(exc)}

    for row in candidates:
        try:
            email = (row.get("email") or "").strip().lower()
            name  = (row.get("name")  or email.split("@")[0]).strip()
            if not email or "@" not in email:
                skipped += 1; continue
            try:
                assignments = get_assignments_db(row["learner_id"])
                pending = [a for a in assignments if a.get("status") == "pending"]
            except Exception:
                pending = []
            if not pending:
                skipped += 1; continue

            titles = [a.get("title", "Untitled") for a in pending]
            upsert_email_automation(row["learner_id"], email, name)
            _ar_email(name=name, email=email,
                      pending_count=len(pending), assignment_titles=titles)
            mark_email_sent(row["learner_id"], "assignment_reminder")
            sent += 1
            log_activity("system", "email:assignment_reminder", f"{email} pending={len(pending)}")
        except Exception as exc:
            logger.warning("Assignment reminder failed for %s: %s", row.get("email", "?"), exc)
            errors += 1

    logger.info("Assignment reminder job: sent=%d skipped=%d errors=%d", sent, skipped, errors)
    return {"sent": sent, "skipped": skipped, "errors": errors, "candidates": len(candidates)}


def _run_weekend_job(force: bool = False) -> dict:
    """Saturday morning (WAT) motivation email. Cooldown: 6 days."""
    import datetime as _dtt
    from app.db import (get_email_automation_candidates, mark_email_sent,
                        upsert_email_automation)
    from app.services.email_service import send_weekend_motivation_email as _wk_email

    wat_now = _dtt.datetime.utcnow() + _dtt.timedelta(hours=1)
    if not force and wat_now.weekday() != 5:
        return {"sent": 0, "skipped": 0, "reason": "not_saturday"}

    COOLDOWN_DAYS = 6 if not force else 0
    sent = skipped = errors = 0
    try:
        candidates = get_email_automation_candidates("weekend", COOLDOWN_DAYS)
    except Exception as exc:
        logger.warning("Weekend job DB query failed: %s", exc)
        return {"sent": 0, "skipped": 0, "errors": 1, "error": str(exc)}

    for row in candidates:
        try:
            email = (row.get("email") or "").strip().lower()
            name  = (row.get("name")  or email.split("@")[0]).strip()
            if not email or "@" not in email:
                skipped += 1; continue
            upsert_email_automation(row["learner_id"], email, name)
            _wk_email(name=name, email=email,
                      xp=int(row.get("xp") or 0),
                      current_course=row.get("current_course") or "")
            mark_email_sent(row["learner_id"], "weekend")
            sent += 1
            log_activity("system", "email:weekend_motivation", email)
        except Exception as exc:
            logger.warning("Weekend email failed for %s: %s", row.get("email", "?"), exc)
            errors += 1

    logger.info("Weekend job: sent=%d skipped=%d errors=%d", sent, skipped, errors)
    return {"sent": sent, "skipped": skipped, "errors": errors, "candidates": len(candidates)}


def _run_new_month_job(force: bool = False) -> dict:
    """1st of the month (WAT) kickoff email. Cooldown: 27 days."""
    import datetime as _dtt, json as _json_nm
    from app.db import (get_email_automation_candidates, mark_email_sent,
                        upsert_email_automation)
    from app.services.email_service import send_new_month_email as _nm_email

    wat_now = _dtt.datetime.utcnow() + _dtt.timedelta(hours=1)
    if not force and wat_now.day != 1:
        return {"sent": 0, "skipped": 0, "reason": "not_first_of_month"}

    month_name    = wat_now.strftime("%B %Y")
    COOLDOWN_DAYS = 27 if not force else 0
    sent = skipped = errors = 0
    try:
        candidates = get_email_automation_candidates("new_month", COOLDOWN_DAYS)
    except Exception as exc:
        logger.warning("New-month job DB query failed: %s", exc)
        return {"sent": 0, "skipped": 0, "errors": 1, "error": str(exc)}

    for row in candidates:
        try:
            email = (row.get("email") or "").strip().lower()
            name  = (row.get("name")  or email.split("@")[0]).strip()
            if not email or "@" not in email:
                skipped += 1; continue
            xp = int(row.get("xp") or 0)
            raw = row.get("completed_projects") or "[]"
            try:
                c_done = len(_json_nm.loads(raw)) if isinstance(raw, str) else len(raw)
            except Exception:
                c_done = 0
            upsert_email_automation(row["learner_id"], email, name)
            _nm_email(name=name, email=email, month_name=month_name,
                      xp=xp, courses_done=c_done)
            mark_email_sent(row["learner_id"], "new_month")
            sent += 1
            log_activity("system", "email:new_month", f"{email} month={month_name}")
        except Exception as exc:
            logger.warning("New-month email failed for %s: %s", row.get("email", "?"), exc)
            errors += 1

    logger.info("New-month job: sent=%d skipped=%d errors=%d", sent, skipped, errors)
    return {"sent": sent, "skipped": skipped, "errors": errors, "candidates": len(candidates)}


# ---------------------------------------------------------------------------
# Unified email automation scheduler — runs hourly, each job self-guards
# ---------------------------------------------------------------------------

def _email_automation_scheduler() -> None:
    """Hourly background thread. Waits 60 s on first boot (lets uvicorn fully
    start), then checks all email jobs every hour. Each job has its own
    day/cooldown guard so running hourly never causes duplicate sends."""
    import time as _t
    _t.sleep(60)  # brief startup pause — removed 6h delay that blocked all emails after restart
    while True:
        for _jname, _jfn in [
            ("reengagement",        _run_reengagement_job),
            ("course_reminder",     _run_course_reminder_job),
            ("assignment_reminder", _run_assignment_reminder_job),
            ("weekend_motivation",  _run_weekend_job),
            ("new_month",           _run_new_month_job),
        ]:
            try:
                _r = _jfn()
                if _r.get("sent", 0) > 0 or _r.get("errors", 0) > 0:
                    logger.info("Email scheduler [%s]: %s", _jname, _r)
            except Exception as _exc:
                logger.warning("Email scheduler [%s] error: %s", _jname, _exc)
        _t.sleep(3600)


threading.Thread(
    target=_email_automation_scheduler,
    daemon=True,
    name="email-automation-scheduler",
).start()


# ---------------------------------------------------------------------------
# Admin trigger endpoints
# ---------------------------------------------------------------------------

@app.post("/admin/reengagement/trigger")
async def admin_trigger_reengagement(request: Request) -> dict:
    """Manually trigger the 7-day re-engagement email job."""
    _require_admin(request)
    result = await asyncio.get_running_loop().run_in_executor(None, _run_reengagement_job)
    log_activity("admin", "email:reengagement:manual",
                 f"sent={result.get('sent')} errors={result.get('errors')}")
    return {"ok": True, "job": "reengagement",
            "message": f"{result.get('sent')} re-engagement emails sent.", **result}


@app.post("/admin/email/course-reminder/trigger")
async def admin_trigger_course_reminder(request: Request) -> dict:
    """Manually trigger the course-reminder email job."""
    _require_admin(request)
    result = await asyncio.get_running_loop().run_in_executor(None, _run_course_reminder_job)
    log_activity("admin", "email:course_reminder:manual",
                 f"sent={result.get('sent')} errors={result.get('errors')}")
    return {"ok": True, "job": "course_reminder",
            "message": f"{result.get('sent')} course reminder emails sent.", **result}


@app.post("/admin/email/assignment-reminder/trigger")
async def admin_trigger_assignment_reminder(request: Request) -> dict:
    """Manually trigger the assignment-reminder email job."""
    _require_admin(request)
    result = await asyncio.get_running_loop().run_in_executor(None, _run_assignment_reminder_job)
    log_activity("admin", "email:assignment_reminder:manual",
                 f"sent={result.get('sent')} errors={result.get('errors')}")
    return {"ok": True, "job": "assignment_reminder",
            "message": f"{result.get('sent')} assignment reminder emails sent.", **result}


@app.post("/admin/email/weekend/trigger")
async def admin_trigger_weekend(request: Request) -> dict:
    """Manually trigger the weekend motivation email job (bypasses day-of-week guard)."""
    _require_admin(request)
    result = await asyncio.get_running_loop().run_in_executor(
        None, lambda: _run_weekend_job(force=True))
    log_activity("admin", "email:weekend:manual",
                 f"sent={result.get('sent')} errors={result.get('errors')}")
    return {"ok": True, "job": "weekend_motivation",
            "message": f"{result.get('sent')} weekend motivation emails sent.", **result}


@app.post("/admin/email/new-month/trigger")
async def admin_trigger_new_month(request: Request) -> dict:
    """Manually trigger the new-month kickoff email job."""
    _require_admin(request)
    result = await asyncio.get_running_loop().run_in_executor(
        None, lambda: _run_new_month_job(force=True))
    log_activity("admin", "email:new_month:manual",
                 f"sent={result.get('sent')} errors={result.get('errors')}")
    import datetime as _dtt_nm
    wat_now    = _dtt_nm.datetime.utcnow() + _dtt_nm.timedelta(hours=1)
    month_name = wat_now.strftime("%B %Y")
    return {"ok": True, "job": "new_month",
            "message": f"{result.get('sent')} new-month emails sent for {month_name}.", **result}


@app.post("/admin/email/unsubscribe")
async def admin_unsubscribe_learner(request: Request) -> dict:
    """Admin: opt a learner out of all automated emails."""
    _require_admin(request)
    body       = await request.json()
    learner_id = str(body.get("learner_id", "")).strip()
    if not learner_id:
        raise HTTPException(status_code=400, detail="learner_id required")
    from app.db import set_email_opted_out
    set_email_opted_out(learner_id, opted_out=True)
    log_activity("admin", "email:unsubscribe", f"learner_id={learner_id}")
    return {"ok": True, "learner_id": learner_id,
            "message": "Learner opted out of all automated emails."}


# ---------------------------------------------------------------------------
# STARTUP � Supabase data recovery on Render restart
# ---------------------------------------------------------------------------

def _mirror_referral_code_to_supabase(code: str, owner_id: str, owner_email: str,
                                        max_uses: int = 50, reward_tier: str = "tier1") -> None:
    """Mirror a newly-created referral code to Supabase referral_codes table."""
    try:
        from app.supabase_client import sb_mirror_referral_code
        sb_mirror_referral_code(code, owner_id, owner_email, max_uses, reward_tier)
    except Exception as exc:
        logger.debug("Referral code Supabase mirror failed (non-fatal): %s", exc)

def _recover_from_supabase() -> None:
    """
    CRITICAL STARTUP RECOVERY � runs on every boot.

    Render free tier wipes the filesystem on every deploy.
    This function:
    1. Pulls ALL email accounts from Supabase ? writes to PostgreSQL + in-memory
    2. Logs exactly what was recovered so we can debug

    Called AFTER init_db() and _load_confirmed_from_db().
    Safe to call even when Supabase is not configured (no-ops gracefully).
    Now uses PostgreSQL as the primary store � learner_progress recovery
    is skipped (already in PostgreSQL). Only email accounts and referral
    codes need Supabase recovery.
    """
    import time as _t
    _t.sleep(10)  # Give uvicorn 10s to fully start before making any network calls

    from app.supabase_client import sb_enabled, get_supabase
    from app.db import save_email_account, get_all_confirmed_emails
    from app.email_auth import _confirmed, _by_id

    if not sb_enabled():
        logger.info("Supabase not configured � skipping cloud recovery")
        return

    sb = get_supabase()
    if not sb:
        return

    # -- Step 1: Recover email accounts --------------------------------------
    # Pull from Supabase only accounts not already in PostgreSQL.
    try:
        # Get emails already in our PostgreSQL DB to skip duplicates
        try:
            existing = {r["email"] for r in get_all_confirmed_emails()}
        except Exception:
            existing = set()

        res = sb.table("email_accounts") \
                .select("email,learner_id,full_name,password_hash,confirmed") \
                .eq("confirmed", True) \
                .execute()
        accounts = res.data or []
        new_count = 0
        for acct in accounts:
            email = acct.get("email", "").lower()
            lid   = acct.get("learner_id", "")
            name  = acct.get("full_name", "")
            pw    = acct.get("password_hash", "")
            if not email or not lid:
                continue
            # Add to memory cache regardless
            if email not in _confirmed:
                user = {"name": name, "email": email,
                        "learner_id": lid, "password_hash": pw, "token": ""}
                _confirmed[email] = user
                _by_id[lid]       = user
            # Only write to PostgreSQL if not already there
            if email not in existing:
                try:
                    save_email_account(email=email, name=name, learner_id=lid,
                                       password_hash=pw, token="", confirmed=True)
                    new_count += 1
                except Exception:
                    pass
        if accounts:
            logger.info("Supabase recovery: %d email accounts (%d new to PostgreSQL)",
                        len(accounts), new_count)
    except Exception as exc:
        logger.warning("Supabase email recovery failed: %s", exc)

    # -- Step 2: Learner progress ---------------------------------------------
    # Skipped � PostgreSQL is now the primary store. Progress is already there.
    # No need to pull from Supabase on every boot.

    # -- Step 3: Recover referral codes --------------------------------------
    # User-generated referral codes live in PostgreSQL.
    # Recover any that exist in Supabase but not yet in PostgreSQL.
    try:
        res = sb.table("referral_codes") \
                .select("code,owner_id,owner_email,max_uses,reward_tier,uses,bonus_balance") \
                .execute()
        ref_rows = res.data or []
        recovered_refs = 0
        for rr in ref_rows:
            code = rr.get("code", "").upper()
            if not code:
                continue
            try:
                from app.db import create_referral_code as _crc, get_referral_code as _grc, get_db as _gdb
                # Only insert if not already present in PostgreSQL
                if not _grc(code):
                    _crc(
                        code=code,
                        owner_id=rr.get("owner_id", ""),
                        owner_email=rr.get("owner_email", ""),
                        max_uses=rr.get("max_uses", 50),
                        reward_tier=rr.get("reward_tier", "tier1"),
                    )
                    # Restore uses and bonus_balance
                    with _gdb() as _conn:
                        with _conn.cursor() as _cur:
                            _cur.execute(
                                "UPDATE referrals SET uses=%s, bonus_balance=%s WHERE code=%s",
                                (rr.get("uses", 0), rr.get("bonus_balance", 0), code)
                            )
                    recovered_refs += 1
            except Exception as rr_exc:
                logger.debug("Referral code restore failed for %s: %s", code, rr_exc)
        if recovered_refs:
            logger.info("Supabase recovery: %d referral codes restored", recovered_refs)
    except Exception as exc:
        logger.debug("Supabase referral code recovery failed (non-fatal): %s", exc)


# Run recovery in a background thread.
# daemon=True � never blocks Render's uvicorn worker from completing startup.
threading.Thread(
    target=_recover_from_supabase,
    daemon=True,
    name="startup-recovery",
).start()


# ---------------------------------------------------------------------------
# FIX: Editable User Profile routes
# ---------------------------------------------------------------------------

@app.get("/auth/profile/{learner_id}")
async def get_profile_data(learner_id: str,
                           user=Depends(get_current_user)) -> dict:
    """Get editable profile fields. Returns full data to the profile owner,
    public-safe data only to others."""
    validate_learner_id(learner_id)
    db_profile = get_user_profile_db(learner_id)
    lp = get_profile(learner_id)

    is_owner = (user is not None and user.learner_id == learner_id)

    # Base data � safe to return to anyone (no tier/email exposure to non-owners)
    result = {
        "learner_id":   learner_id,
        "display_name": db_profile.get("display_name") or lp.display_name or "",
        "bio":          db_profile.get("bio", ""),
        "location":     db_profile.get("location", ""),
        "website":      db_profile.get("website", ""),
        "photo_url":    db_profile.get("photo_url", ""),
        "level":        lp.level,
        "xp":           lp.xp,
        "badges":       lp.badges,
    }
    # Owner-only fields
    if is_owner:
        result["email"] = lp.email or ""
        result["tier"]  = lp.tier
    return result


@app.post("/auth/profile/{learner_id}")
async def update_profile(learner_id: str, body: UserProfileUpdate,
                         user=Depends(get_current_user)) -> dict:
    """Update editable profile fields. Requires authentication as the profile owner."""
    validate_learner_id(learner_id)

    # Must be authenticated and be the owner of the profile
    if user is None:
        raise HTTPException(status_code=401, detail="Sign in to update your profile.")
    if user.learner_id != learner_id:
        raise HTTPException(status_code=403, detail="You can only edit your own profile.")

    # Sanitise photo_url � accept only https:// URLs or base64 data URLs for images.
    # Reject javascript: URIs, plain strings, and other non-image content.
    import re as _re2
    photo = body.photo_url.strip() if body.photo_url else ""
    if photo:
        is_data_url  = _re2.match(r'^data:image/(jpeg|png|gif|webp);base64,', photo)
        is_https_url = _re2.match(r'^https://', photo)
        if not is_data_url and not is_https_url:
            raise HTTPException(status_code=400,
                detail="photo_url must be an https:// URL or a base64 data:image/... URL.")
        # Enforce size limit on base64 images (max 2MB decoded � ~2.7MB base64)
        if is_data_url and len(photo) > 2_800_000:
            raise HTTPException(status_code=400,
                detail="Profile picture too large. Maximum size is 2MB.")

    update_user_profile_db(
        learner_id,
        display_name=body.display_name,
        bio=body.bio,
        location=body.location,
        website=body.website,
        photo_url=photo,
    )
    # Mirror display_name to LearnerProfile in memory + SQLite
    lp = get_profile(learner_id)
    if body.display_name:
        lp.display_name = body.display_name
    from app.progress import save_profile as _sp
    _sp(lp)
    # Mirror to Supabase
    if body.display_name or lp.email:
        threading.Thread(
            target=sb_upsert_profile,
            args=(learner_id, lp.email, body.display_name or lp.display_name),
            daemon=False,
        ).start()
    log_activity(learner_id, "profile:updated", f"name={body.display_name}")
    return {"ok": True, "message": "Profile updated successfully."}


# ---------------------------------------------------------------------------
# Account deletion � NDPR/GDPR right to erasure (Article 17)
# ---------------------------------------------------------------------------

class _DeleteAccountRequest(_BM):
    password: str = _Field(..., min_length=1, max_length=128,
                           description="Current password � confirms the user's identity")
    confirm:  str = _Field(..., min_length=1, max_length=20,
                           description="Must equal 'DELETE' to confirm intent")


@app.delete("/auth/account")
async def delete_account(body: _DeleteAccountRequest,
                         user=Depends(require_user)) -> dict:
    """
    Permanently delete the authenticated user's account.
    NDPR/GDPR right to erasure � permanently removes PII, anonymises
    learning data, retains payment records for 7 years (Nigerian tax law).
    Requires: current password + confirmation string 'DELETE'.
    """
    if body.confirm.upper() != "DELETE":
        raise HTTPException(
            status_code=400,
            detail="Confirmation must be the word DELETE to proceed."
        )

    # For email users: verify password before deleting
    from app.email_auth import _confirmed, verify_password
    email = user.email.lower().strip() if user.email else ""
    if email and email in _confirmed:
        stored_hash = _confirmed[email].get("password_hash", "")
        if stored_hash and not verify_password(body.password, stored_hash):
            raise HTTPException(
                status_code=401,
                detail="Incorrect password. Account deletion cancelled."
            )
    # OAuth users (Google/GitHub): no password to verify � identity already proved by session token

    try:
        from app.db import delete_account as _delete_account_db
        summary = _delete_account_db(user.learner_id, email)
    except Exception as exc:
        logger.error("Account deletion failed for %s: %s", user.learner_id, exc)
        raise HTTPException(
            status_code=500,
            detail="Account deletion failed. Please contact support@mypytutor.com.ng"
        )

    # Remove from in-memory caches
    try:
        from app.email_auth import _confirmed as _ec, _by_id as _bi
        _ec.pop(email, None)
        _bi.pop(user.learner_id, None)
        from app.auth import _users as _au
        _au.pop(user.learner_id, None)
        from app.progress import _store as _ps
        _ps.pop(user.learner_id, None)
    except Exception:
        pass  # Non-fatal � caches will expire naturally

    # Clean up Supabase asynchronously
    try:
        def _supabase_cleanup():
            try:
                from app.supabase_client import get_supabase
                sb = get_supabase()
                if sb:
                    sb.table("email_accounts").delete().eq("learner_id", user.learner_id).execute()
                    sb.table("profiles").delete().eq("id", user.learner_id).execute()
                    sb.table("learner_progress").delete().eq("learner_id", user.learner_id).execute()
            except Exception as _se:
                logger.debug("Supabase cleanup after deletion failed (non-fatal): %s", _se)
        threading.Thread(target=_supabase_cleanup, daemon=False).start()
    except Exception:
        pass

    log_activity(user.learner_id, "account:deleted", f"email={email}")
    logger.info("Account deleted: learner_id=%s email=%s", user.learner_id, email)

    return {
        "ok":      True,
        "message": "Your account has been permanently deleted. We're sorry to see you go.",
        "summary": summary,
    }


# ---------------------------------------------------------------------------
# FIX: Invoice PDF generation (ReportLab � no weasyprint, free tier safe)
# ---------------------------------------------------------------------------

@app.get("/invoice/{invoice_id}/pdf")
async def get_invoice_pdf(invoice_id: str,
                          user=Depends(get_current_user)) -> JSONResponse:
    """Generate a downloadable PDF invoice. Requires auth � owner only."""
    import re as _re5
    if not _re5.match(r'^[A-Z0-9\-]{4,30}$', invoice_id):
        raise HTTPException(status_code=400, detail="Invalid invoice ID.")
    if user is None:
        raise HTTPException(status_code=401, detail="Sign in to download invoices.")
    inv = get_invoice_db(invoice_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found.")
    if inv.get("learner_id") and inv["learner_id"] != user.learner_id:
        raise HTTPException(status_code=403, detail="You can only download your own invoices.")
    try:
        import io
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from fastapi.responses import StreamingResponse

        buf    = io.BytesIO()
        doc    = SimpleDocTemplate(buf, pagesize=A4,
                                   rightMargin=2*cm, leftMargin=2*cm,
                                   topMargin=2*cm, bottomMargin=2*cm)
        styles = getSampleStyleSheet()
        navy   = colors.HexColor("#0d2b6e")
        grey   = colors.HexColor("#718096")
        story  = []

        # Header
        story.append(Paragraph("<b>?? MyPy Tutor</b>", ParagraphStyle(
            "hdr", parent=styles["Title"], textColor=navy, fontSize=22, spaceAfter=4)))
        story.append(Paragraph(
            "Powered by TeamTega Technologies Limited<br/>"
            "Certified by Teamsamikoko Global Academy � Reg No: 3508656",
            ParagraphStyle("sub", parent=styles["Normal"], textColor=grey, fontSize=9, spaceAfter=16)))

        # Invoice title + meta
        story.append(Paragraph(f"<b>INVOICE #{inv['id']}</b>",
                                ParagraphStyle("inv", parent=styles["Heading2"], textColor=navy, spaceAfter=4)))
        story.append(Paragraph(f"Date: {inv.get('issued_at_fmt', '')}", styles["Normal"]))
        story.append(Spacer(1, 0.4*cm))

        # Bill to
        story.append(Paragraph("<b>Bill To</b>", ParagraphStyle(
            "billt", parent=styles["Normal"], textColor=grey, fontSize=9, spaceBefore=8)))
        story.append(Paragraph(f"<b>{inv['name']}</b><br/>{inv['email']}",
                                ParagraphStyle("billa", parent=styles["Normal"], fontSize=11, spaceAfter=12)))

        # Line items table
        data = [
            ["Description", "Amount"],
            [inv["plan"], f"\u20a6{inv['amount']:,.0f}"],
            ["", ""],
            ["Total Paid", f"\u20a6{inv['amount']:,.0f} {inv['currency']}"],
        ]
        tbl = Table(data, colWidths=[12*cm, 5*cm])
        tbl.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (-1,0), navy),
            ("TEXTCOLOR",     (0,0), (-1,0), colors.white),
            ("FONTNAME",      (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE",      (0,0), (-1,0), 10),
            ("ALIGN",         (1,0), (1,-1), "RIGHT"),
            ("BACKGROUND",    (0,-1), (-1,-1), colors.HexColor("#f0f7ff")),
            ("FONTNAME",      (0,-1), (-1,-1), "Helvetica-Bold"),
            ("LINEBELOW",     (0,0), (-1,-2), 0.5, grey),
            ("ROWBACKGROUNDS",(0,1), (-1,-2), [colors.white, colors.HexColor("#f7fafc")]),
            ("TOPPADDING",    (0,0), (-1,-1), 6),
            ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ]))
        story.append(tbl)
        story.append(Spacer(1, 0.5*cm))
        story.append(Paragraph(
            "Status: <b>PAID</b> &nbsp;&nbsp; Payment Ref: " + inv.get("payment_id", ""),
            ParagraphStyle("status", parent=styles["Normal"], textColor=colors.HexColor("#276749"), fontSize=10)))
        story.append(Spacer(1, 1*cm))
        story.append(Paragraph(
            '"Learn Smarter. Code Better. Build the Future."',
            ParagraphStyle("tag", parent=styles["Normal"], textColor=grey, fontSize=9, fontName="Helvetica-Oblique")))

        doc.build(story)
        buf.seek(0)
        filename = f"MyPyTutor_Invoice_{inv['id']}.pdf"
        return StreamingResponse(
            buf,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except ImportError:
        raise HTTPException(status_code=503, detail="PDF generation not available � install reportlab.")
    except Exception as exc:
        logger.error("PDF generation error: %s", exc)
        raise HTTPException(status_code=500, detail="Could not generate PDF invoice.")


# ---------------------------------------------------------------------------
# FIX: Paystack metadata � store learner_id in payment so Google users
#      can be auto-upgraded via webhook (no email-matching required)
# ---------------------------------------------------------------------------

@app.get("/payments/metadata/{learner_id}")
async def get_payment_metadata(learner_id: str,
                               user=Depends(get_current_user)) -> dict:
    """
    Returns Paystack metadata for embedding in a payment link.
    Includes learner_id, email, and any pending coupon code so the
    webhook can apply the discount automatically on payment success.
    """
    validate_learner_id(learner_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Sign in to generate payment metadata.")
    if user.learner_id != learner_id:
        raise HTTPException(status_code=403, detail="You can only generate metadata for your own account.")
    lp    = get_profile(learner_id)
    email = lp.email or ""

    # Check if this learner has an unused coupon recorded (applied but not yet
    # consumed by a webhook). Pass it through to Paystack metadata so the
    # webhook can credit the correct savings amount on charge.success.
    coupon_code = ""
    try:

        from app.db import get_db as _gdb
        with _gdb() as _conn:
            with _conn.cursor(cursor_factory=_pge.RealDictCursor) as _cur:
                _cur.execute(
                    "SELECT code FROM coupon_uses WHERE learner_id=%s ORDER BY ts DESC LIMIT 1",
                    (learner_id,)
                )
                row = _cur.fetchone()
                if row:
                    coupon_code = row["code"]
    except Exception:
        pass

    custom_fields = [
        {"display_name": "Learner ID",  "variable_name": "learner_id",  "value": learner_id},
        {"display_name": "User Email",  "variable_name": "user_email",  "value": email},
    ]
    if coupon_code:
        custom_fields.append(
            {"display_name": "Coupon Code", "variable_name": "coupon_code", "value": coupon_code}
        )

    return {
        "metadata": {
            "learner_id":  learner_id,
            "email":       email,
            "coupon_code": coupon_code,
            "custom_fields": custom_fields,
        }
    }


# ---------------------------------------------------------------------------
# TTS — text-to-speech via browser Web Speech API (zero extra dependencies)
# Returns clean plain-text for the frontend to speak using speechSynthesis.
# /tts/prepare — strip markdown, return speakable text
# /tts/voices  — return ordered list of preferred English voice names
# ---------------------------------------------------------------------------

@app.post("/tts/prepare")
async def tts_prepare(request: Request) -> dict:
    """
    Prepare text for browser TTS.
    Strips markdown, code blocks, URLs and excess whitespace so the browser's
    speechSynthesis reads naturally. No audio file is generated server-side —
    the frontend calls window.speechSynthesis.speak() with the returned text.
    """
    import re as _re_tts
    body = await request.json()
    raw_text: str = body.get("text", "")
    if not raw_text or not raw_text.strip():
        raise HTTPException(status_code=400, detail="No text provided.")
    if len(raw_text) > 20_000:
        raise HTTPException(status_code=400, detail="Text too long. Maximum 20,000 characters.")

    # Strip fenced code blocks
    text = _re_tts.sub(r"```[a-z]*\n?[\s\S]*?```", " [code block] ", raw_text)
    # Strip inline code — keep the readable content
    text = _re_tts.sub(r"`([^`\n]{1,120})`", r"\1", text)
    # Strip markdown bold/italic (handle nested safely)
    text = _re_tts.sub(r"\*\*\*(.+?)\*\*\*", r"\1", text)
    text = _re_tts.sub(r"\*\*(.+?)\*\*",     r"\1", text)
    text = _re_tts.sub(r"\*(.+?)\*",          r"\1", text)
    text = _re_tts.sub(r"___(.+?)___",        r"\1", text)
    text = _re_tts.sub(r"__(.+?)__",          r"\1", text)
    text = _re_tts.sub(r"_(.+?)_",            r"\1", text)
    # Strip ATX headings
    text = _re_tts.sub(r"^#{1,6}\s+", "", text, flags=_re_tts.MULTILINE)
    # Strip markdown links — keep label
    text = _re_tts.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    # Strip bare URLs
    text = _re_tts.sub(r"https?://\S+", "", text)
    # Strip blockquotes and horizontal rules
    text = _re_tts.sub(r"^>\s+", "", text, flags=_re_tts.MULTILINE)
    text = _re_tts.sub(r"^[-*_]{3,}\s*$", "", text, flags=_re_tts.MULTILINE)
    # Convert list bullets to natural pauses
    text = _re_tts.sub(r"^[\*\-\+\u2022]\s+", ". ", text, flags=_re_tts.MULTILINE)
    text = _re_tts.sub(r"^\d+\.\s+",           ". ", text, flags=_re_tts.MULTILINE)
    # Strip table pipes
    text = _re_tts.sub(r"\|", " ", text)
    # Collapse excess whitespace
    text = _re_tts.sub(r"\n{3,}", "\n\n", text)
    text = _re_tts.sub(r"[ \t]{2,}", " ", text)
    text = text.strip()

    # Truncate to 5000 chars — browser TTS engines vary in their limits
    truncated = len(text) > 5000
    if truncated:
        text = text[:4997] + "..."

    return {"text": text, "char_count": len(text), "truncated": truncated}


@app.get("/tts/voices")
async def tts_voices() -> dict:
    """
    Return a curated priority-ordered list of English voice names.
    The Web Speech API only exposes voices client-side; this endpoint lets
    the JS picker find the best available option without trial-and-error.
    Voice names match SpeechSynthesisVoice.name in the browser.
    """
    return {
        "preferred": [
            "Google UK English Female",
            "Google UK English Male",
            "Microsoft Hazel Desktop - English (Great Britain)",
            "Microsoft George Desktop - English (Great Britain)",
            "Google US English",
            "Microsoft Zira Desktop - English (United States)",
            "Microsoft David Desktop - English (United States)",
            "Alex",
            "Samantha",
            "Karen",
            "Daniel",
        ],
        "language_priority": ["en-NG", "en-GB", "en-US", "en-AU", "en-ZA", "en"],
        "fallback": "Use the first voice whose lang starts with 'en'",
    }


# ---------------------------------------------------------------------------
# FIX: Render persistent disk � DB_PATH env var documented in render.yaml
#      (no code change needed � db.py already reads DB_PATH env var)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Static assets � icons, manifest, certificates (NOT the full frontend app)
# The HTML frontend is served by Vercel (github.com/tegaconsults-cloud/mypytutor)
# Render serves only the API + certificate HTML generation + static assets
# ---------------------------------------------------------------------------

# Serve icons, manifest, premium.css, sw.js etc. under /static/
app.mount("/static", StaticFiles(directory="static"), name="static_assets")


@app.get("/", include_in_schema=False)
async def root() -> dict:
    """API root � confirms the backend is alive. Frontend is on Vercel."""
    return {
        "service": "MyPy Tutor API",
        "status":  "ok",
        "version": "2.0.0",
        "docs":    "API-only endpoint. Frontend: https://mypytutor.com.ng",
    }


@app.get("/admin.html", response_class=HTMLResponse, include_in_schema=False)
async def serve_admin_html() -> HTMLResponse:
    """Serve the admin dashboard HTML directly from /admin.html"""
    import os as _os2
    path = _os2.path.join("static", "admin.html")
    if not _os2.path.exists(path):
        raise HTTPException(status_code=404, detail="Admin panel not found.")
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    return HTMLResponse(content=content)


@app.get("/admin", include_in_schema=False)
async def redirect_admin():
    """Redirect /admin → /admin.html"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/admin.html", status_code=302)


@app.get("/voice", response_class=HTMLResponse, include_in_schema=False)
async def serve_voice_integration() -> HTMLResponse:
    """Serve the voice feature integration guide at /voice"""
    import os as _os3
    path = _os3.path.join("static", "voice-integration.html")
    if not _os3.path.exists(path):
        raise HTTPException(status_code=404, detail="Voice integration guide not found.")
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    return HTMLResponse(content=content)


# ---------------------------------------------------------------------------
# AI Automation course landing page
# ---------------------------------------------------------------------------

@app.get("/courses/ai-automation", response_class=HTMLResponse, include_in_schema=False)
async def serve_ai_automation_landing() -> HTMLResponse:
    """Serve the AI Automation course landing page."""
    import os as _os_aia
    path = _os_aia.path.join("static", "courses", "ai-automation.html")
    if not _os_aia.path.exists(path):
        raise HTTPException(status_code=404, detail="AI Automation landing page not found.")
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    return HTMLResponse(content=content)


@app.get("/courses/ai-automation/", response_class=HTMLResponse, include_in_schema=False)
async def serve_ai_automation_landing_slash() -> HTMLResponse:
    """Trailing-slash redirect for the AI Automation landing page."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/courses/ai-automation", status_code=301)


# Serve icons under /icons/ directly (shortcut used in admin.html)
try:
    import os as _os3
    if _os3.path.isdir("static/icons"):
        app.mount("/icons", StaticFiles(directory="static/icons"), name="icons")
except Exception:
    pass


