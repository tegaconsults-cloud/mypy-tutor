"""
Security middleware and utilities for MyPy Tutor.

Covers:
- Rate limiting (per-IP, sliding window, in-memory)
- Input sanitisation and size guards
- Security response headers
- learner_id / param validation
"""

import re
import time
import logging
from collections import defaultdict, deque

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Rate limit: max requests per window per IP
RATE_LIMIT_REQUESTS = 30          # max calls
RATE_LIMIT_WINDOW   = 60          # per 60 seconds

# Strict limits for expensive LLM endpoints
LLM_RATE_LIMIT_REQUESTS = 10      # max LLM calls
LLM_RATE_LIMIT_WINDOW   = 60      # per 60 seconds

LLM_ENDPOINTS = {"/chat", "/quiz/generate", "/quiz/answer",
                 "/course/start", "/course/next", "/exercise/generate"}

# Input size limits
MAX_MESSAGE_LEN   = 4_000         # characters in a single user message
MAX_CODE_LEN      = 8_000         # characters of pasted code (embedded in message)
MAX_HISTORY_ITEMS = 20            # max conversation turns sent per request
MAX_HISTORY_MSG_LEN = 12_000       # characters per history message (AI responses are long)

# Allowed field values
ALLOWED_LEVELS    = {"beginner", "intermediate", "advanced"}
LEARNER_ID_RE     = re.compile(r"^[a-zA-Z0-9_\-]{1,64}$")
COURSE_NAME_RE    = re.compile(r"^[a-zA-Z0-9_\-]{1,80}$")
TOPIC_RE          = re.compile(r"^[a-zA-Z0-9 _\-&/]{1,100}$")

# Free tier daily prompt limit
FREE_DAILY_LIMIT = 20

# ---------------------------------------------------------------------------
# In-memory rate limit store
# ---------------------------------------------------------------------------

# { ip: deque of timestamps } — capped at 10k unique IPs to prevent memory growth
_general_store: dict[str, deque] = defaultdict(deque)
_llm_store:     dict[str, deque] = defaultdict(deque)
_RATE_STORE_MAX = 10_000   # evict oldest IPs when over this size


def _evict_rate_store(store: dict) -> None:
    """Drop the 20% oldest entries when the store exceeds capacity."""
    if len(store) > _RATE_STORE_MAX:
        evict_count = _RATE_STORE_MAX // 5
        for key in list(store.keys())[:evict_count]:
            store.pop(key, None)


def _check_rate(store: dict, ip: str, limit: int, window: int) -> bool:
    """Return True if request is allowed, False if rate-limited."""
    now = time.monotonic()
    dq  = store[ip]
    # Evict old timestamps outside the window
    while dq and dq[0] < now - window:
        dq.popleft()
    if len(dq) >= limit:
        return False
    dq.append(now)
    _evict_rate_store(store)
    return True


# ---------------------------------------------------------------------------
# Free-tier daily prompt counter (per learner_id OR ip, whichever is provided)
# ---------------------------------------------------------------------------

import datetime as _dt

# { key -> (date_str, count) }
_daily_prompt_store: dict[str, tuple[str, int]] = {}


def check_free_prompt_limit(learner_id: str, ip: str) -> tuple[bool, int]:
    """
    Check if a free-tier user has exceeded their 20 prompts/day limit.
    Returns (allowed: bool, used_count: int).
    Key is learner_id if not 'default', otherwise ip.
    """
    key = learner_id if learner_id and learner_id != "default" else ip
    today = _dt.date.today().isoformat()
    existing = _daily_prompt_store.get(key)
    if existing is None or existing[0] != today:
        # New day or first time — evict yesterday's stale keys while we're here
        if len(_daily_prompt_store) > 5000:
            stale = [k for k, (d, _) in _daily_prompt_store.items() if d != today]
            for k in stale:
                del _daily_prompt_store[k]
        _daily_prompt_store[key] = (today, 0)
        return True, 0
    _, count = existing
    if count >= FREE_DAILY_LIMIT:
        return False, count
    return True, count


def increment_free_prompt_count(learner_id: str, ip: str) -> int:
    """Increment the daily prompt counter. Returns new count."""
    key = learner_id if learner_id and learner_id != "default" else ip
    today = _dt.date.today().isoformat()
    existing = _daily_prompt_store.get(key)
    if existing is None or existing[0] != today:
        _daily_prompt_store[key] = (today, 1)
        return 1
    date_str, count = existing
    new_count = count + 1
    _daily_prompt_store[key] = (date_str, new_count)
    return new_count


def get_free_prompt_count(learner_id: str, ip: str) -> int:
    """Get current daily prompt count for a learner/IP."""
    key = learner_id if learner_id and learner_id != "default" else ip
    today = _dt.date.today().isoformat()
    existing = _daily_prompt_store.get(key)
    if existing is None or existing[0] != today:
        return 0
    return existing[1]


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

class SecurityMiddleware(BaseHTTPMiddleware):
    """
    Single middleware that applies:
    1. General rate limiting (all routes)
    2. Stricter LLM rate limiting (AI endpoints)
    3. Security response headers
    """

    async def dispatch(self, request: Request, call_next):
        ip = _get_ip(request)

        # 1. General rate limit
        if not _check_rate(_general_store, ip, RATE_LIMIT_REQUESTS, RATE_LIMIT_WINDOW):
            logger.warning("General rate limit hit: %s", ip)
            return JSONResponse(
                status_code=429,
                content={"error": "Too many requests. Please slow down."},
                headers={"Retry-After": str(RATE_LIMIT_WINDOW)},
            )

        # 2. LLM-endpoint rate limit
        if request.url.path in LLM_ENDPOINTS:
            if not _check_rate(_llm_store, ip, LLM_RATE_LIMIT_REQUESTS, LLM_RATE_LIMIT_WINDOW):
                logger.warning("LLM rate limit hit: %s %s", ip, request.url.path)
                return JSONResponse(
                    status_code=429,
                    content={"error": "Too many AI requests. Wait a moment before trying again."},
                    headers={"Retry-After": str(LLM_RATE_LIMIT_WINDOW)},
                )

        response = await call_next(request)

        # 3. Security headers on every response
        response.headers["X-Content-Type-Options"]    = "nosniff"
        response.headers["X-Frame-Options"]           = "DENY"
        response.headers["X-XSS-Protection"]          = "1; mode=block"
        response.headers["Referrer-Policy"]           = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"]        = "geolocation=(), microphone=(), camera=()"
        response.headers["Content-Security-Policy"]   = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://accounts.google.com https://www.googletagmanager.com https://www.google-analytics.com; "
            "style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com; "
            "font-src 'self' https://cdnjs.cloudflare.com; "
            "img-src 'self' data: https://www.google-analytics.com https://www.googletagmanager.com; "
            "connect-src 'self' https://www.google-analytics.com https://analytics.google.com https://region1.google-analytics.com; "
            "worker-src 'self';"
        )
        # Remove server fingerprint
        if "server" in response.headers:
            del response.headers["server"]
        if "x-powered-by" in response.headers:
            del response.headers["x-powered-by"]

        return response


def _get_ip(request: Request) -> str:
    """Extract real client IP, respecting Render's forwarded headers."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        # Take the first IP (the real client) from the chain
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# ---------------------------------------------------------------------------
# Input validators — called inside route handlers
# ---------------------------------------------------------------------------

def validate_learner_id(learner_id: str) -> str:
    """Sanitise and validate learner_id. Raises 400 on bad input."""
    if not LEARNER_ID_RE.match(learner_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid learner_id. Use only letters, numbers, hyphens, underscores (max 64 chars).",
        )
    return learner_id


def validate_level(level: str) -> str:
    """Validate level field. Raises 400 on unknown value."""
    if level not in ALLOWED_LEVELS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid level '{level}'. Must be one of: beginner, intermediate, advanced.",
        )
    return level


def validate_course_name(name: str) -> str:
    """Validate course name param."""
    if not COURSE_NAME_RE.match(name):
        raise HTTPException(status_code=400, detail="Invalid course name.")
    return name


def validate_topic(topic: str) -> str:
    """Validate topic param."""
    if not TOPIC_RE.match(topic):
        raise HTTPException(status_code=400, detail="Invalid topic.")
    return topic


def validate_chat_request(message: str, history: list, level: str, learner_id: str) -> None:
    """
    Full validation of a /chat request payload.
    Raises HTTPException 400 on any violation.
    """
    # Message length
    if len(message) > MAX_MESSAGE_LEN:
        raise HTTPException(
            status_code=400,
            detail=f"Message too long. Maximum {MAX_MESSAGE_LEN} characters.",
        )

    # History size
    if len(history) > MAX_HISTORY_ITEMS:
        raise HTTPException(
            status_code=400,
            detail=f"History too long. Maximum {MAX_HISTORY_ITEMS} messages.",
        )

    # Each history message length
    for i, msg in enumerate(history):
        if len(msg.content) > MAX_HISTORY_MSG_LEN:
            raise HTTPException(
                status_code=400,
                detail=f"History message {i} too long. Maximum {MAX_HISTORY_MSG_LEN} characters.",
            )
        if msg.role not in {"user", "assistant", "system"}:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid role '{msg.role}' in history.",
            )

    validate_level(level)
    validate_learner_id(learner_id)
